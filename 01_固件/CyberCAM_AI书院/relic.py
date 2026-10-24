# -*- coding: utf-8 -*-
"""火眼金睛：非遗古物识别。

模型是离线训好的原型向量（model.npz），板上只做特征比对，不依赖 KPU。
认准之后由 main 播报对应历史。置信度不够就保持沉默。
"""
import os

import cv2
import numpy as np

try:
    from . import config
except Exception:
    import config

# 标签顺序必须与训练输出 names 完全一致。新旧 schema 不兼容；旧 model.npz 会被拒绝加载。
CLASS_ORDER = ("houjie_yuexiu", "houjie_shuangshou_hongquan",
               "aotai_aoyu_brick", "guancao",
               "qingxi_qilin_zhazuo", "other")


def center_crop(bgr, keep=0.72):
    h, w = bgr.shape[:2]
    dh, dw = int(h * (1 - keep) / 2), int(w * (1 - keep) / 2)
    return bgr[dh:h - dh, dw:w - dw]


def embed(bgr):
    """返回 (单位向量, 颜色比例)。"""
    im = center_crop(bgr, 0.72)
    if im.size == 0:
        im = bgr
    im = cv2.resize(im, (96, 96))
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 4, 4], [0, 180, 0, 256, 0, 256])
    hist = hist.flatten().astype(np.float32)
    hist /= np.linalg.norm(hist) + 1e-6
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    ang = (np.arctan2(gy, gx) + np.pi) / (2 * np.pi)
    tex, _ = np.histogram(ang, bins=12, range=(0, 1), weights=mag)
    tex = tex.astype(np.float32)
    tex /= np.linalg.norm(tex) + 1e-6
    H, S, V = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    red = float((((H < 12) | (H > 168)) & (S > 70) & (V > 50)).mean())
    straw = float(((H >= 8) & (H <= 32) & (S > 25) & (V > 80) & (V < 230)).mean())
    dark = float(((V < 80) & (S < 70)).mean())
    brown = float(((H >= 4) & (H <= 22) & (S > 35) & (V > 25) & (V < 160)).mean())
    extra = np.array([red, straw, dark, brown, float(S.mean()) / 255.0, float(V.mean()) / 255.0], np.float32) * 3.0
    vec = np.concatenate([hist * 0.6, tex * 0.45, extra]).astype(np.float32)
    vec /= np.linalg.norm(vec) + 1e-6
    return vec, {"red": red, "straw": straw, "dark": dark, "brown": brown}


def gate(cls, ratios):
    """Accept only configured keys; no unvalidated legacy color heuristics remain."""
    return cls in config.RELIC_KEYS


class RelicEngine(object):
    def __init__(self, path=None):
        self.path = path or getattr(config, "RELIC_MODEL", "")
        self.prototypes = None
        self.labels = None
        self.names = list(CLASS_ORDER)
        self.threshold = 0.78
        self.margin = 0.035
        self._hits = {}
        self._hit_t = {}
        self.CONFIRM_HITS = 2      # 命中几次就播报（原来 3 次太严，手持会断）
        self.HIT_WINDOW = 2.5      # 秒；超过这个时间的旧命中不算
        self._last = 0.0
        self.announced = ""
        self.last = {"id": "", "score": 0.0, "level": "none", "speak": False}
        self._load()

    def _load(self):
        if not self.path or not os.path.isfile(self.path):
            print("[relic] 没有模型", self.path)
            return
        try:
            z = np.load(self.path, allow_pickle=False)
            if "schema_version" not in z or int(z["schema_version"]) != 2:
                raise ValueError("缺少新类别模型 schema_version=2；拒绝使用旧模型")
            self.prototypes = z["prototypes"].astype(np.float32)
            self.labels = z["labels"].astype(np.int32)
            raw = z["names"]
            self.names = [str(x) for x in raw.tolist()]
            if self.names != list(CLASS_ORDER):
                raise ValueError("类别 schema 过期: %s; 需要 %s" % (self.names, list(CLASS_ORDER)))
            if self.prototypes.ndim != 2 or self.labels.ndim != 1 or len(self.labels) != len(self.prototypes):
                raise ValueError("原型/标签维度不匹配")
            if self.labels.size == 0 or int(self.labels.min()) < 0 or int(self.labels.max()) >= len(self.names):
                raise ValueError("标签索引越界或为空")
            self.threshold = float(z["threshold"])
            self.margin = float(z["margin"])
            print("[relic] 模型", self.path, "原型", len(self.labels), "阈值", round(self.threshold, 3))
        except Exception as e:
            print("[relic] 模型读取失败", e)
            self.prototypes = None
            self.labels = None
            self.names = list(CLASS_ORDER)

    def reset_announce(self):
        self.announced = ""
        self._hits = {}

    def predict(self, bgr):
        if not getattr(config, "RELIC_RECOGNITION_ENABLED", False):
            return "", 0.0, {}
        if self.prototypes is None or bgr is None:
            return "", 0.0, {}
        vec, ratios = embed(bgr)
        sims = self.prototypes.dot(vec)
        score = {}
        for i, name in enumerate(self.names):
            sel = sims[self.labels == i]
            if sel.size == 0:
                score[name] = -1.0
                continue
            sel = np.sort(sel)[-3:]
            score[name] = float(sel.mean())
        ranked = sorted(score.items(), key=lambda kv: kv[1], reverse=True)
        best, best_s = ranked[0]
        second = ranked[1] if len(ranked) > 1 else ("", -1.0)
        second_s = second[1]
        gap = best_s - second_s
        # 判据放宽：分数够高，或领先够明显，都算认到。
        # 现场拍实物时同类分数普遍在 0.95+，但类间差距会缩到 0.02 左右。
        if best == "other":
            return "", best_s, ratios
        if not (best_s >= self.threshold or gap >= self.margin):
            return "", best_s, ratios
        if best_s < 0.55:
            return "", best_s, ratios
        if not gate(best, ratios):
            return "", best_s, ratios
        return best, best_s, ratios

    def step(self, frame, now):
        if now - self._last < 0.28:
            out = dict(self.last)
            out["speak"] = False
            return out
        self._last = now
        cid, score, ratios = self.predict(frame)
        speak = False
        # 用"时间窗内的命中次数"，而不是严格连续。手持抖动不该把进度清零。
        if cid:
            self._hits[cid] = self._hits.get(cid, 0) + 1
            self._hit_t = getattr(self, "_hit_t", {})
            self._hit_t[cid] = now
            for k in list(self._hits):
                if k != cid and now - self._hit_t.get(k, 0) > self.HIT_WINDOW:
                    self._hits[k] = 0
            if self._hits[cid] >= self.CONFIRM_HITS and cid != self.announced:
                self.announced = cid
                self._hits[cid] = 0
                speak = True
            level = "hit"
        else:
            # 没认到：只有窗外的旧命中才清，别一抖动就归零
            self._hit_t = getattr(self, "_hit_t", {})
            for k in list(self._hits):
                if now - self._hit_t.get(k, 0) > self.HIT_WINDOW:
                    self._hits[k] = 0
            level = "look"
            if score < 0.6:
                self.announced = ""
        self.last = {"id": cid, "score": score, "level": level, "speak": speak, "ratios": ratios}
        return dict(self.last)