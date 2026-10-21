# -*- coding: utf-8 -*-
"""摄像头：唯一的开关入口。

这个模块回答一个问题：什么时候该开、什么时候该关、开不出来怎么办。
全程序只有这里调用 Sensor.Sensor，别处一律用 Camera.acquire()/release()。

规则来自 CyberCAM 的硬约束：
  - 摄像头独占，同时只能有一路；第二路会 Device or resource busy
  - 退出必须 release，否则下次启动打不开
  - 打开失败要退避重试，不能每帧都试（会拖慢主循环）
"""
import time

import cv2

try:
    from . import config
except Exception:
    import config

try:
    from walnutpi import Sensor
    HAS_HW = True
except Exception:
    Sensor = None
    HAS_HW = False


def log(*a):
    print("[cam]", *a)


class Camera(object):
    def __init__(self, width=None, height=None):
        self.w = width or config.SCREEN_W
        self.h = height or config.SCREEN_H
        self.cap = None
        self.live = False
        self.last_err = ""
        self._next_try = 0.0
        self._fail = 0

    # ---------- 状态 ----------
    @property
    def is_open(self):
        return self.cap is not None

    def ensure(self, now=None):
        """需要画面时调用。已开就什么都不做；打不开则按退避重试。"""
        if self.cap is not None:
            return True
        now = now or time.time()
        if now < self._next_try:
            return False
        self._open()
        if self.cap is None:
            # 每次失败把重试间隔翻倍，上限 5 秒，避免拖慢主循环
            self._fail += 1
            self._next_try = now + min(5.0, 0.4 * (2 ** min(self._fail, 4)))
        return self.cap is not None

    def _open(self):
        if not HAS_HW:
            self.last_err = "非硬件环境"
            return
        try:
            cap = Sensor.Sensor(self.w, self.h)
        except Exception as e:
            self.last_err = str(e)[:60]
            self.cap = None
            log("打开异常", self.last_err)
            return
        try:
            if not cap.isOpened():
                try:
                    cap.release()
                except Exception:
                    pass
                self.cap = None
                self.last_err = "isOpened 返回 False"
                log("打开失败：被别的进程占用？")
                return
            self.cap = cap
            self._fail = 0
            self.last_err = ""
            self._mirror()
            log("摄像头就绪 %dx%d" % (self.w, self.h))
        except Exception as e:
            self.last_err = str(e)[:60]
            self.cap = None

    def _mirror(self):
        """翻转屏要镜像，只做一次。"""
        try:
            from walnutpi import direction
            if direction.get_lcd() == 2:
                self.cap.set_hmirror(1)
        except Exception:
            pass

    def read(self):
        """读一帧。失败时自动标记，下一次 ensure 会重开。"""
        if self.cap is None:
            self.live = False
            return None
        try:
            ret, frame = self.cap.read()
        except Exception as e:
            self.last_err = str(e)[:60]
            self.release()
            return None
        if not ret or frame is None:
            self.live = False
            return None
        self.live = True
        return frame

    def release(self):
        cap = self.cap
        self.cap = None
        self.live = False
        if cap is None:
            return
        try:
            cap.release()
            log("摄像头已释放")
        except Exception as e:
            log("释放异常", e)

    # ---------- 给别人的小工具 ----------
    def crop_face(self, frame, det, size=96):
        """从检测框里裁一张灰度人脸，统一到 size×size。"""
        if frame is None or not det:
            return None
        H, W = frame.shape[:2]
        x0 = max(0, int(det["x"]))
        y0 = max(0, int(det["y"]))
        x1 = min(W, int(det["x"] + det["w"]))
        y1 = min(H, int(det["y"] + det["h"]))
        if x1 - x0 < 20 or y1 - y0 < 20:
            return None
        gray = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
        return cv2.resize(gray, (size, size))