# -*- coding: utf-8 -*-
"""双语语音播报：本地 mp3 优先，缺失时在线 TTS 生成并存本地。

板端调用顺序：
  1) /data/aotai/audio/{lang}/{id}.mp3 存在 -> aplay 播放
  2) 不存在 -> 调 DashScope qwen-tts 合成（需 API Key）-> 存本地 -> 播放
  3) 在线也失败 -> 返回 False，由界面显示字幕兜底
"""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time

try:
    from . import config
except Exception:
    import config

# 可选在线 TTS 配置（不填则只用本地）
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
DASHSCOPE_TTS_MODEL = "qwen-tts"
DASHSCOPE_TTS_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
)
# 粤语优先用粤语音色；若无权限自动退回普通话音色
VOICE_BY_LANG = {
    "zh": os.environ.get("AOTAI_VOICE_ZH", "Cherry"),
    "yue": os.environ.get("AOTAI_VOICE_YUE", "Serena"),
}
_TTS_VOICE_FALLBACK = ["Cherry", "Serena", "Ethan", "Chelsie"]


def _log(*a):
    print("[audio]", *a)


def audio_path(lang, line_id):
    return os.path.join(config.AUDIO_DIR, lang, "%s.mp3" % line_id)


def ensure_dirs():
    for lang in config.LANGS:
        try:
            os.makedirs(os.path.join(config.AUDIO_DIR, lang), exist_ok=True)
        except Exception as e:
            _log("mkdir fail", e)


def _which(name):
    return shutil.which(name)


class Player(object):
    """后台播放，不阻塞 UI 主循环。"""

    def __init__(self):
        self._proc = None
        self._ff = None
        self._lock = threading.Lock()
        self._last_err = ""

    @property
    def busy(self):
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    def stop(self):
        with self._lock:
            procs = (self._proc, self._ff)
        for p in procs:
            if p is None:
                continue
            try:
                if p.poll() is None:
                    try:
                        os.killpg(p.pid, 15)
                    except Exception:
                        p.terminate()
            except Exception:
                pass
            try:
                # 关键：杀完必须 wait 回收，否则留僵尸进程，越堆越多最后放不出声
                p.wait(timeout=1.0)
            except Exception:
                try:
                    if p.poll() is None:
                        try:
                            os.killpg(p.pid, 9)
                        except Exception:
                            p.kill()
                    p.wait(timeout=1.0)
                except Exception:
                    pass

    def _spawn(self, cmd, stdin=None):
        return subprocess.Popen(
            cmd, stdin=stdin, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def play_file(self, path, on_done=None):
        if not path or not os.path.exists(path):
            self._last_err = "missing file %s" % path
            return False
        # aplay 只会播 WAV。mp3 直接塞进去就是杂音，先用 ffmpeg 解开。
        if str(path).lower().endswith(".mp3") and _which("ffmpeg"):
            return self._play_mp3(path, on_done)
        cmd = list(config.AUDIO_CMD) + [path]
        try:
            with self._lock:
                self._proc = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            if on_done:
                t = threading.Thread(target=self._wait_and_cb, args=(self._proc, on_done))
                t.daemon = True
                t.start()
            return True
        except Exception as e:
            self._last_err = str(e)
            _log("aplay fail:", e)
            # 兜底：mpv / ffplay
            return self._play_with_fallback(path)

    def _play_mp3(self, path, on_done=None):
        ff_cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-i", path, "-f", "wav", "-acodec", "pcm_s16le",
            "-ar", "22050", "-ac", "1", "pipe:1",
        ]
        try:
            ff = subprocess.Popen(
                ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            play = self._spawn(list(config.AUDIO_CMD) + ["-"], stdin=ff.stdout)
            if ff.stdout is not None:
                ff.stdout.close()
            with self._lock:
                self._ff = ff
                self._proc = play
            # 播放结束时把 ffmpeg 也回收掉，避免僵尸进程占着声卡
            def _reap(proc=play, enc=ff):
                try:
                    proc.wait()
                except Exception:
                    pass
                try:
                    if enc.poll() is None:
                        enc.terminate()
                    enc.wait(timeout=1.0)
                except Exception:
                    pass
            threading.Thread(target=_reap, daemon=True).start()
            if on_done:
                t = threading.Thread(target=self._wait_and_cb, args=(play, on_done))
                t.daemon = True
                t.start()
            return True
        except Exception as e:
            self._last_err = str(e)
            _log("mp3 play fail:", e)
            return self._play_with_fallback(path)

    def _play_with_fallback(self, path):
        for cmd in (["mpv", "--no-video", "--really-quiet", path],
                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path]):
            if not _which(cmd[0]):
                continue
            try:
                with self._lock:
                    self._proc = subprocess.Popen(
                        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                continue
        return False

    def _wait_and_cb(self, proc, cb):
        try:
            proc.wait()
        except Exception:
            pass
        try:
            cb()
        except Exception as e:
            _log("on_done err", e)


class Speaker(object):
    def __init__(self, content=None):
        self.content = content
        self.player = Player()
        ensure_dirs()

    # ---------- 在线合成 ----------
    def synthesize_online(self, text, lang, out_path):
        if not DASHSCOPE_API_KEY:
            return False
        try:
            import requests
        except Exception:
            return False
        voice = VOICE_BY_LANG.get(lang, "Cherry")
        payload = {
            "model": DASHSCOPE_TTS_MODEL,
            "input": {"text": text, "voice": voice},
        }
        headers = {
            "Authorization": "Bearer " + DASHSCOPE_API_KEY,
            "Content-Type": "application/json",
        }
        try:
            r = requests.post(DASHSCOPE_TTS_URL, json=payload, headers=headers, timeout=20)
            data = r.json()
            url = (
                (data.get("output") or {}).get("audio", {}).get("url")
                or (data.get("output") or {}).get("audio_url")
            )
            if not url:
                _log("tts no url", str(data)[:200])
                return False
            audio_resp = requests.get(url, timeout=30)
            if audio_resp.status_code != 200 or len(audio_resp.content) < 800:
                return False
            tmp = out_path + ".part"
            with open(tmp, "wb") as f:
                f.write(audio_resp.content)
            os.replace(tmp, out_path)
            _log("tts saved", out_path, len(audio_resp.content))
            return True
        except Exception as e:
            _log("tts err", e)
            return False

    # ---------- 对外 ----------
    def say(self, line_id, lang=None, text=None, on_done=None):
        """播报一条 line；返回 True 表示已开始播放。"""
        lang = lang or config.FALLBACK_LANG
        if lang not in config.LANGS:
            lang = config.FALLBACK_LANG
        if text is None:
            if self.content is not None:
                text, _ = self.content.text(line_id, lang)
            else:
                text = ""
        text = (text or "").strip()
        path = audio_path(lang, line_id)
        # 新的一条要说话，先把上一条掐掉。否则抢答时两条抢声卡，会两边都没声。
        self.player.stop()
        time.sleep(0.06)
        if os.path.exists(path) and os.path.getsize(path) > 512:
            return self.player.play_file(path, on_done)
        # 本地没有 -> 在线合成（后台线程，避免卡 UI）
        if text and DASHSCOPE_API_KEY:
            def _job():
                ok = self.synthesize_online(text, lang, path)
                if ok:
                    self.player.play_file(path, on_done)
            t = threading.Thread(target=_job)
            t.daemon = True
            t.start()
            return True
        _log("no audio & no api key:", lang, line_id)
        return False

    def say_text(self, text, lang=None, on_done=None):
        """直接朗读一段文本（无 line id 时用它，缓存按文本 md5）。"""
        lang = lang or config.FALLBACK_LANG
        hid = hashlib.md5(text.encode("utf-8")).hexdigest()[:10]
        return self.say("tts_" + hid, lang, text=text, on_done=on_done)

    def stop(self):
        self.player.stop()
