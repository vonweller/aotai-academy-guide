# -*- coding: utf-8 -*-
"""朗读文案与关卡数据：本地 content.json 优先，缺失时用内置兜底。"""
import json
import os

try:
    from . import config
except Exception:
    import config

_FALLBACK = {
    "project": "鳌台书院 AI 非遗导览",
    "stages": [
        {
            "id": 1, "key": "gate",
            "name": {"zh": "第一关 · 门口迎宾", "yue": "第一關 · 門口迎賓"},
            "lines": [
                {"id": "s1_welcome_ok", "zh": "预约访客，欢迎您来到非遗博物馆AI鳌台书院。",
                 "yue": "預約訪客，歡迎您嚟到非遺博物館AI鰲台書院。"},
                {"id": "s1_welcome_new", "zh": "欢迎光临鳌台书院，我是您的AI导览员小鳌。",
                 "yue": "歡迎光臨鰲台書院，我係你嘅AI導覽員小鰲。"},
            ],
            "quiz": [],
        },
        {
            "id": 2, "key": "front_yard",
            "name": {"zh": "第二关 · 鳌台溯源", "yue": "第二關 · 鰲台溯源"},
            "lines": [
                {"id": "s2_intro", "zh": "我们现在来到前院。鳌台书院位于东莞厚街，是岭南书院的代表。",
                 "yue": "我哋而家嚟到前院。鰲台書院位於東莞厚街，係嶺南書院嘅代表。"},
            ],
            "quiz": [{
                "qid": "q1",
                "q": {"zh": "鳌台书院坐落在哪个镇？", "yue": "鰲台書院坐落喺邊個鎮？"},
                "options": [
                    {"key": "A", "zh": "虎门", "yue": "虎門"},
                    {"key": "B", "zh": "厚街", "yue": "厚街"},
                    {"key": "C", "zh": "长安", "yue": "長安"},
                ],
                "answer": "B",
                "explain": {"zh": "答对了！鳌台书院在东莞厚街。", "yue": "答啱喇！鰲台書院喺東莞厚街。"},
            }],
        },
        {"id": 3, "key": "hall", "name": {"zh": "第三关 · 讲堂楹联", "yue": "第三關 · 講堂楹聯"},
         "lines": [{"id": "s3_intro", "zh": "这里是讲堂，旧时学子在此诵读经史。",
                    "yue": "呢度係講堂，舊時學子喺度誦讀經史。"}], "quiz": []},
        {"id": 4, "key": "workshop", "name": {"zh": "第四关 · 非遗工坊", "yue": "第四關 · 非遺工坊"},
         "lines": [{"id": "s4_intro", "zh": "东莞的非遗有莞草编织、千角灯，还有香云纱。",
                    "yue": "東莞嘅非遺有莞草編織、千角燈，仲有香雲紗。"}], "quiz": []},
        {"id": 5, "key": "pavilion", "name": {"zh": "第五关 · 留墨寄愿", "yue": "第五關 · 留墨寄願"},
         "lines": [{"id": "s5_outro", "zh": "参观到这里就结束啦，愿你把书院的书香带回家。",
                    "yue": "參觀到呢度就完喇，願你將書院嘅書香帶返屋企。"}], "quiz": []},
    ],
}


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


class Content(object):
    def __init__(self, path=None):
        self.path = path or config.CONTENT_PATH
        self.data = _load_json(self.path)
        if not self.data:
            # IDE 调试：脚本同级或 ../../02_数据/content.json
            here = os.path.dirname(os.path.abspath(__file__))
            for cand in (
                os.path.join(here, "content.json"),
                os.path.join(here, "..", "..", "02_数据", "content.json"),
                os.path.join(here, "..", "..", "02_数据", "content.json".lower()),
            ):
                self.data = _load_json(os.path.abspath(cand))
                if self.data:
                    self.path = os.path.abspath(cand)
                    break
        self.data = self.data or _FALLBACK
        self.stages = {}
        for st in self.data.get("stages", []):
            try:
                self.stages[int(st.get("id", 0))] = st
            except Exception:
                continue
        # 兼容：content.json 放在 APP 目录（IDE 调试时）
        if not self.stages:
            self.data = _FALLBACK
            self.stages = {int(s["id"]): s for s in _FALLBACK["stages"]}

    # ---------- 查询 ----------
    def stage(self, stage):
        return self.stages.get(int(stage)) or {}

    def entry_id(self, stage):
        st = self.stage(stage)
        if st.get("entry"):
            return st["entry"]
        lines = st.get("lines") or []
        return lines[0].get("id") if lines else None

    def stage_name(self, stage, lang):
        st = self.stage(stage)
        n = st.get("name") or {}
        return n.get(lang) or n.get("zh") or config.STAGE_NAMES.get(stage, {}).get(lang, "第%d关" % stage)

    def lines(self, stage):
        return self.stage(stage).get("lines", [])

    def line(self, line_id):
        for st in self.stages.values():
            for ln in st.get("lines", []):
                if ln.get("id") == line_id:
                    return ln
            # 题目的 q / a / wrong 也当成可朗读条目
            for q in st.get("quiz") or []:
                qid = q.get("qid") or ""
                if line_id == qid + "_q":
                    return {"id": line_id, "zh": (q.get("q") or {}).get("zh"),
                            "yue": (q.get("q") or {}).get("yue")}
                if line_id == qid + "_a":
                    return {"id": line_id, "zh": (q.get("explain") or {}).get("zh"),
                            "yue": (q.get("explain") or {}).get("yue")}
                if line_id == qid + "_wrong":
                    w = q.get("explain_wrong") or {}
                    return {"id": line_id, "zh": w.get("zh"), "yue": w.get("yue")}
        for rel in self.data.get("relics") or []:
            if rel.get("id") == line_id:
                return rel
        return None

    def text(self, line_id, lang):
        """返回 (朗读文本, 字幕文本)。粤语缺字时回退普通话。"""
        ln = self.line(line_id)
        if not ln:
            return "", ""
        t = ln.get(lang) or ln.get("zh") or ""
        return t, t

    def relics(self):
        return list(self.data.get("relics") or [])

    def quiz(self, stage):
        qs = self.stage(stage).get("quiz") or []
        return qs[0] if qs else None

    def quiz_text(self, quiz, lang):
        q = quiz or {}
        return (q.get("q") or {}).get(lang) or (q.get("q") or {}).get("zh", "")

    def quiz_options(self, quiz, lang):
        out = []
        for op in (quiz or {}).get("options", []):
            out.append({"key": op.get("key"), "text": op.get(lang) or op.get("zh", "")})
        return out

    def quiz_explain(self, quiz, lang):
        e = (quiz or {}).get("explain") or {}
        return e.get(lang) or e.get("zh", "")
