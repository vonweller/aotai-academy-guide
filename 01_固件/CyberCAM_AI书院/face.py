# -*- coding: utf-8 -*-
"""人脸：KPU 检测 + LBPH 识别 + 现场学习。

设计要点：
  - 检测用官方 /data/app/face-det 的 320 模型，不另存一份
  - 识别用 cv2.face.LBPH，人脸库 /data/aotai/faces
  - 识别有最小间隔，避免每帧都跑拖慢主循环
  - 学习由主循环喂帧，绝不自己开摄像头（那会抢设备）
"""
import json
import os
import time

import cv2
import numpy as np

try:
    from . import config
except Exception:
    import config


def log(*a):
    print("[face]", *a)


def _imread(path):
    try:
        buf = np.fromfile(path, dtype=np.uint8)
        if buf.size == 0:
            return None
        return cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    except Exception:
        return None


def _imwrite(path, img):
    try:
        ok, buf = cv2.imencode('.jpg', img)
        if ok:
            buf.tofile(path)
            return True
    except Exception:
        pass
    return False


def _first(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


class Face(object):
    def __init__(self):
        self.detector = None
        self.rec = None
        self.labels = {}
        self.samples = 0
        self.last_try = 0.0
        self.last_hit = None
        self.min_gap = 0.8
        self._init_detector()
        self._init_recognizer()

    # ---------- 初始化 ----------
    def _init_detector(self):
        km = _first(config.FACE_KMODEL_CANDIDATES)
        an = _first(config.FACE_ANCHORS_CANDIDATES)
        if not km or not an:
            log("检测模型缺失")
            return
        try:
            from walnutpi import kpu
            self.detector = kpu.FACE_DETECT(km, an, 320)
            log("KPU 就绪", km)
        except Exception as e:
            log("KPU 失败", e)

    def _init_recognizer(self):
        try:
            self.rec = cv2.face.LBPHFaceRecognizer_create(
                radius=1, neighbors=8, grid_x=8, grid_y=8,
                threshold=config.LBPH_THRESHOLD)
        except Exception as e:
            log("LBPH 不可用", e)
            self.rec = None
            return
        self.train()

    # ---------- 人脸库 ----------
    def _dir(self):
        return config.FACE_DB_DIR

    def train(self):
        if self.rec is None:
            return False
        try:
            os.makedirs(self._dir(), exist_ok=True)
            imgs, ids = [], []
            for fn in sorted(os.listdir(self._dir())):
                if not fn.lower().endswith(('.jpg', '.png')):
                    continue
                try:
                    idx = int(fn.split('_')[0])
                except Exception:
                    continue
                im = _imread(os.path.join(self._dir(), fn))
                if im is None:
                    continue
                imgs.append(cv2.resize(im, (96, 96)))
                ids.append(idx)
            if not imgs:
                log("人脸库为空")
                return False
            self.rec.train(imgs, np.array(ids))
            self.samples = len(imgs)
            self._load_labels()
            log("训练完成 %d 张 / %d 人" % (len(imgs), len(set(ids))))
            return True
        except Exception as e:
            log("训练失败", e)
            return False

    def _load_labels(self):
        try:
            with open(os.path.join(self._dir(), 'labels.json'), encoding='utf-8') as f:
                self.labels = json.load(f)
        except Exception:
            self.labels = {}

    def _save_labels(self):
        try:
            with open(os.path.join(self._dir(), 'labels.json'), 'w', encoding='utf-8') as f:
                json.dump(self.labels, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def clear(self):
        try:
            for fn in os.listdir(self._dir()):
                if fn.lower().endswith(('.jpg', '.png', '.yml')) or fn == 'labels.json':
                    os.remove(os.path.join(self._dir(), fn))
            self.labels = {}
            log("人脸库已清空")
        except Exception as e:
            log("清空失败", e)

    def learn(self, grays, name="预约访客", reset=True):
        """把主循环攒到的人脸样本写进库并重训。"""
        if not grays:
            return 0
        if reset:
            self.clear()
        os.makedirs(self._dir(), exist_ok=True)
        self.labels = {"1": name}
        n = 0
        for g in grays:
            n += 1
            _imwrite(os.path.join(self._dir(), "1_%02d.jpg" % n),
                     cv2.resize(g, (96, 96)))
        self._save_labels()
        self.train()
        log("学习完成 %d 张，目标 %s" % (n, name))
        return n

    # ---------- 检测 / 识别 ----------
    def detect(self, frame):
        if self.detector is None or frame is None:
            return []
        try:
            res = self.detector.run(
                frame,
                reliability_threshold=config.FACE_RELIABILITY,
                nms_threshold=config.FACE_NMS)
        except Exception as e:
            log("检测失败", e)
            return []
        out = []
        for r in res or []:
            out.append({"x": int(r.x), "y": int(r.y),
                        "w": int(r.w), "h": int(r.h),
                        "score": float(getattr(r, 'reliability', 0.0))})
        return out

    def step(self, frame, now=None):
        """返回 {level, name, dist, box, gray}；识别有最小间隔。"""
        now = now or time.time()
        dets = self.detect(frame)
        if not dets:
            self.last_hit = None
            return {"level": "none"}
        det = max(dets, key=lambda d: d["w"] * d["h"])
        if det["w"] < config.FACE_MIN_SIZE:
            return {"level": "detected", "box": det}
        gray = None
        if frame is not None:
            H, W = frame.shape[:2]
            x0, y0 = max(0, det["x"]), max(0, det["y"])
            x1, y1 = min(W, det["x"] + det["w"]), min(H, det["y"] + det["h"])
            if x1 - x0 >= 20 and y1 - y0 >= 20:
                gray = cv2.resize(
                    cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY), (96, 96))
        if self.rec is None or self.samples == 0:
            return {"level": "detected", "box": det, "gray": gray}
        if now - self.last_try < self.min_gap:
            if self.last_hit:
                c = dict(self.last_hit)
                c["box"] = det
                return c
            return {"level": "detected", "box": det, "gray": gray}
        self.last_try = now
        if gray is None:
            return {"level": "detected", "box": det}
        try:
            idx, dist = self.rec.predict(gray)
        except Exception as e:
            log("predict 失败", e)
            return {"level": "detected", "box": det, "gray": gray}
        name = self.labels.get(str(idx))
        ok = dist <= config.LBPH_THRESHOLD
        res = {"level": "recognized" if ok else "unknown",
               "box": det, "gray": gray,
               "name": name if ok else None, "dist": float(dist)}
        if ok:
            self.last_hit = res
        return res