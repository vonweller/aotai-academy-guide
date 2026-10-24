# -*- coding: utf-8 -*-
"""积分与兑换：每位游客一份档案，存在 /data/aotai/points.json。"""
import json
import os
import time

try:
    from . import config
except Exception:
    import config

POINTS_PATH = os.path.join(config.DATA_DIR, "points.json")

# 奖励规则：语义清晰，网页和板子共用
REWARDS = {
    "face": 10,
    "stage_clear": 10,
    "quiz_right": 15,
    "relic_recognize": 8,
    "relic_quiz_right": 20,
    "finish": 50,
}

# 兑换品：名字与所需积分（网页与板子一致）
SHOP = [
    {"id": "pin_xiangyunsha", "name": "项目纪念徽章", "cost": 30, "icon": "badge"},
    {"id": "pin_guancao", "name": "导览纪念书签", "cost": 45, "icon": "bookmark"},
    {"id": "pin_qianjiaodeng", "name": "展陈主题挂饰", "cost": 60, "icon": "lantern"},
    {"id": "figure_xiangyunsha", "name": "数字导览摆件", "cost": 90, "icon": "figure"},
    {"id": "figure_qianjiaodeng", "name": "项目纪念摆件", "cost": 120, "icon": "figure"},
]


def _load():
    try:
        with open(POINTS_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            d.setdefault("visitors", {})
            d.setdefault("last", "")
            return d
    except Exception:
        pass
    return {"visitors": {}, "last": ""}


def _save(d):
    try:
        os.makedirs(os.path.dirname(POINTS_PATH), exist_ok=True)
        tmp = POINTS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, POINTS_PATH)
    except Exception as e:
        print("[points] save fail", e)


class Points(object):
    def __init__(self, who="预约访客"):
        self.data = _load()
        self.who = who or "预约访客"
        self.stage_done = set()
        self.quiz_done = set()
        self.relic_done = set()
        self.bind(self.who)

    def _rec(self):
        v = self.data["visitors"].setdefault(
            self.who,
            {"score": 0, "log": [], "first": int(time.time())},
        )
        v.setdefault("score", 0)
        v.setdefault("log", [])
        return v

    def bind(self, who):
        who = who or "预约访客"
        if who != self.who:
            self.who = who
            self.stage_done = set()
            self.quiz_done = set()
            self.relic_done = set()
        self.data["last"] = self.who
        rec = self._rec()
        _save(self.data)
        return rec.get("score", 0)

    @property
    def score(self):
        return self._rec().get("score", 0)

    def add(self, kind, note="", uniq=None):
        """记一笔；uniq 用来防止重复加分。返回 (当前总分, 本次加了多少)"""
        if kind in ("relic_recognize", "relic_quiz_right") and not config.RELIC_REWARDS_ENABLED:
            return self.score, 0
        v = self._rec()
        if uniq and uniq in v.get("log_keys", []):
            return v.get("score", 0), 0
        gain = int(REWARDS.get(kind, 0))
        if gain <= 0:
            return v.get("score", 0), 0
        v["score"] = int(v.get("score", 0)) + gain
        v.setdefault("log", []).append({"k": kind, "n": note, "p": gain, "t": int(time.time())})
        v["log"] = v["log"][-40:]
        if uniq:
            v.setdefault("log_keys", []).append(uniq)
            v["log_keys"] = v["log_keys"][-200:]
        _save(self.data)
        return v["score"], gain

    def snapshot(self):
        v = self._rec()
        return {
            "who": self.who,
            "score": int(v.get("score", 0)),
            "shop": SHOP,
            "log": list(v.get("log", []))[-8:],
        }

    def redeem(self, item_id):
        item = None
        for it in SHOP:
            if it["id"] == item_id:
                item = it
                break
        if not item:
            return False, "没有这个兑换品"
        v = self._rec()
        if int(v.get("score", 0)) < item["cost"]:
            return False, "积分不够"
        v["score"] = int(v["score"]) - int(item["cost"])
        v.setdefault("redeemed", []).append({"id": item_id, "t": int(time.time())})
        _save(self.data)
        return True, "兑换成功：" + item["name"]
