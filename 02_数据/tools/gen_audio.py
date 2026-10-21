# -*- coding: utf-8 -*-
"""双语语音批量生成（双引擎）

普通话 zh：Qwen3-TTS（阿里云 DashScope，音色 Cherry / Serena / Ethan 可选）
粤语   yue：edge-tts zh-HK（HiuMaan 女声 / WanLung 男声）—— 千问暂无粤语音色

用法：
  python gen_audio.py                 # 全部（zh 走千问，yue 走 edge）
  python gen_audio.py --lang zh
  python gen_audio.py --engine qwen --lang zh
  python gen_audio.py --engine edge --lang both   # 全走 edge（离线兜底）
  python gen_audio.py --voice zh:Serena yue:WanLung
"""
import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content.json")
AUDIO = os.path.join(ROOT, "audio")
FFMPEG = r"D:\APP\ffmpeg-7.1-essentials_build\bin\ffmpeg.exe"
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"

KEY_PATH = os.path.join(ROOT, "tools", ".dashscope_key")
QWEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

# 默认音色：普通话女声 Cherry（温柔），粤语 HiuMaan（自然女声）
DEFAULTS = {
    "zh": {"engine": "qwen", "voice": "Cherry"},
    "yue": {"engine": "edge", "voice": "zh-HK-HiuMaanNeural"},
}
EDGE_VOICES = {
    "zh": {"Xiaoxiao": "zh-CN-XiaoxiaoNeural", "Yunxi": "zh-CN-YunxiNeural"},
    "yue": {"HiuMaan": "zh-HK-HiuMaanNeural", "WanLung": "zh-HK-WanLungNeural",
            "HiuGaai": "zh-HK-HiuGaaiNeural"},
}


def read_key():
    try:
        with open(KEY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return os.environ.get("DASHSCOPE_API_KEY", "")


def collect_lines():
    with open(CONTENT, "r", encoding="utf-8") as f:
        data = json.load(f)
    out, seen = [], set()

    def add(lid, zh, yue):
        if not lid or lid in seen:
            return
        seen.add(lid)
        out.append((lid, {"id": lid, "zh": zh, "yue": yue}))

    for st in data.get("stages", []):
        for ln in st.get("lines", []):
            add(ln.get("id"), ln.get("zh"), ln.get("yue"))
        for q in st.get("quiz", []):
            qid = q.get("qid")
            add(qid + "_q", (q.get("q") or {}).get("zh"), (q.get("q") or {}).get("yue"))
            add(qid + "_a", (q.get("explain") or {}).get("zh"), (q.get("explain") or {}).get("yue"))
            wq = q.get("explain_wrong") or {}
            add(qid + "_wrong", wq.get("zh"), wq.get("yue"))
            for op in q.get("options", []):
                add(qid + "_op" + str(op.get("key")), op.get("zh"), op.get("yue"))
    for rel in data.get("relics") or []:
        rid = rel.get("id")
        add(rid, rel.get("zh"), rel.get("yue"))
        q = rel.get("quiz") or {}
        if q:
            add(rid + "_q", (q.get("q") or {}).get("zh"), (q.get("q") or {}).get("yue"))
            add(rid + "_ok", (q.get("ok") or {}).get("zh"), (q.get("ok") or {}).get("yue"))
            add(rid + "_no", (q.get("no") or {}).get("zh"), (q.get("no") or {}).get("yue"))
    # 固定提示语
    fixed = {
        "p_relic_intro": ("火眼金睛开始了。请把香云纱、莞草编织或者千角灯，放到画面中间让我认一认。",
                          "火眼金睛開始喇。請將香雲紗、莞草編織或者千角燈，放喺畫面中間畀我認一認。"),
        "p_relic_ask": ("认出来了。现在我出个题目考考你，请在上面点答案。",
                        "認得喇。而家我出條題目考考你，請喺上面點答案。"),
        "p_relic_bring": ("答完了。请把刚才那件东西拿近一点，我再认一次，认对了就给你加分。",
                          "答完喇。請將啱啱嗰件嘢攞近啲，我再認一次，認啱就同你加分。"),
        "p_relic_pass": ("又认对了，这题过关，积分记上。",
                         "又認啱喇，呢題過關，積分記低。"),
        "p_points": ("积分又多了。", "積分又多咗。"),
    }
    for lid, (zh, yue) in fixed.items():
        add(lid, zh, yue)
    return out


# ---------------- 引擎 ----------------
def synth_qwen(text, voice, out_mp3):
    """Qwen3-TTS（返回 wav 下载链接 -> ffmpeg 转 mp3）"""
    key = read_key()
    if not key:
        return False, "no key"
    try:
        import requests
    except Exception:
        import urllib.request

        class _R(object):
            @staticmethod
            def post(url, json=None, headers=None, timeout=60):
                data = __import__("json").dumps(json).encode()
                req = urllib.request.Request(url, data=data, headers=headers or {})
                resp = urllib.request.urlopen(req, timeout=timeout)
                body = resp.read()

                class _Resp(object):
                    status_code = resp.status
                    content = body

                    @staticmethod
                    def json():
                        return __import__("json").loads(body)
                return _Resp()
        requests = _R()
    payload = {"model": "qwen3-tts-flash",
               "input": {"text": text, "voice": voice, "language_type": "chinese"}}
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    try:
        r = requests.post(QWEN_URL, json=payload, headers=headers, timeout=90)
        data = r.json()
        url = (data.get("output") or {}).get("audio", {}).get("url")
        if not url:
            return False, json.dumps(data, ensure_ascii=False)[:200]
        raw = requests.get(url, timeout=120).content if hasattr(requests, "get") else \
            __import__("urllib.request").request.urlopen(url, timeout=120).read()
        tmp = out_mp3 + ".src.wav"
        with open(tmp, "wb") as f:
            f.write(raw)
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", tmp,
                        "-ac", "1", "-ar", "22050", "-b:a", "48k", out_mp3], check=True)
        os.remove(tmp)
        return True, os.path.getsize(out_mp3)
    except Exception as e:
        return False, str(e)[:160]


def synth_edge(text, voice, out_mp3):
    import edge_tts

    async def go():
        comm = edge_tts.Communicate(text, voice)
        tmp = out_mp3 + ".raw.mp3"
        await comm.save(tmp)
        return tmp

    try:
        tmp = asyncio.run(go())
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", tmp,
                        "-ac", "1", "-ar", "22050", "-b:a", "48k", out_mp3], check=True)
        os.remove(tmp)
        return True, os.path.getsize(out_mp3)
    except Exception as e:
        return False, str(e)[:160]


# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="all", choices=["zh", "yue", "all"])
    ap.add_argument("--engine", default="auto", choices=["auto", "qwen", "edge"])
    ap.add_argument("--voice", action="append", default=[],
                    help="覆盖音色，如 --voice zh:Serena --voice yue:WanLung")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    langs = ["zh", "yue"] if a.lang == "all" else [a.lang]
    cfg = {k: dict(v) for k, v in DEFAULTS.items()}
    if a.engine != "auto":
        for L in langs:
            cfg[L]["engine"] = a.engine
            if a.engine == "edge":
                cfg[L]["voice"] = EDGE_VOICES[L]["Xiaoxiao" if L == "zh" else "HiuMaan"]
    for spec in a.voice:
        L, _, V = spec.partition(":")
        if L in cfg and V:
            cfg[L]["voice"] = EDGE_VOICES.get(L, {}).get(V, V)

    lines = collect_lines()
    manifest_path = os.path.join(AUDIO, "manifest.json")
    old = []
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                old = json.load(f)
        except Exception:
            old = []
    merged = {(m["id"], m["lang"]): m for m in old if isinstance(m, dict)}

    total = 0
    for lang in langs:
        d = os.path.join(AUDIO, lang)
        os.makedirs(d, exist_ok=True)
        engine = cfg[lang]["engine"]
        voice = cfg[lang]["voice"]
        print("[%s] engine=%s voice=%s" % (lang, engine, voice))
        for lid, ln in lines:
            text = (ln.get(lang) or "").strip()
            if not text:
                continue
            path = os.path.join(d, lid + ".mp3")
            need = a.force or (not os.path.exists(path)) or os.path.getsize(path) < 1200
            if not need:
                continue
            ok, info = (synth_qwen(text, voice, path) if engine == "qwen"
                        else synth_edge(text, voice, path))
            if not ok and engine == "qwen":
                # 千问失败自动降级 edge
                ok, info = synth_edge(text, EDGE_VOICES[lang]["Xiaoxiao" if lang == "zh" else "HiuMaan"], path)
                if ok:
                    voice_used = "edge-fallback"
                else:
                    voice_used = voice
            else:
                voice_used = voice
            if not ok:
                print("  [FAIL]", lid, info)
                continue
            size = os.path.getsize(path)
            total += size
            with open(path, "rb") as f:
                md5 = hashlib.md5(f.read()).hexdigest()
            merged[(lid, lang)] = {
                "id": lid, "lang": lang, "engine": engine if voice_used != "edge-fallback" else "edge",
                "voice": voice_used, "text": text,
                "file": "%s/%s.mp3" % (lang, lid), "bytes": size, "md5": md5,
            }
            print("  [OK]", lid, size)

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(sorted(merged.values(), key=lambda x: (x["lang"], x["id"])), f,
                  ensure_ascii=False, indent=1)
    cnt = len(merged)
    total_all = sum(m.get("bytes", 0) for m in merged.values())
    print("DONE lines=%d total=%.2fMB" % (cnt, total_all / 1048576.0))


if __name__ == "__main__":
    main()
