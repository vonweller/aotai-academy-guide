# -*- coding: utf-8 -*-
"""触摸：裸解析 /dev/input/event0。

物理面板 480x640 竖屏，界面 640x480。画面顺时针转 90 度写入 /dev/fb0，
默认按这个方向把原始坐标换成界面坐标。有三点标定文件时以标定为准。
"""
import json
import os
import select
import struct
import threading
import time

try:
    from . import config
except Exception:
    import config

EV_SYN = 0
EV_KEY = 1
EV_ABS = 3
ABS_X = 0
ABS_Y = 1
ABS_MT_POSITION_X = 0x35
ABS_MT_POSITION_Y = 0x36
ABS_MT_TRACKING_ID = 0x39
BTN_TOUCH = 0x14A
SYN_REPORT = 0

EVENT_FMT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FMT)

CALIB_PATH = os.path.join(config.DATA_DIR, "touch_calib.json")


class Touch(object):
    def __init__(self, device="/dev/input/event0", on_tap=None):
        self.device = device
        self.on_tap = on_tap
        self.fd = None
        self._thread = None
        self._stop = False
        self.x = 0
        self.y = 0
        self.touching = False
        self.reported_down = False
        self.calib = self._load_calib()
        print("[touch] event %d bytes, calib=%s" % (EVENT_SIZE, "yes" if self.calib else "no"))

    def _load_calib(self):
        try:
            with open(CALIB_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
            m = d.get("m")
            if m and len(m) == 6:
                return [float(v) for v in m]
        except Exception:
            pass
        return None

    def save_calib(self, points):
        try:
            (rx0, ry0, sx0, sy0), (rx1, ry1, sx1, sy1), (rx2, ry2, sx2, sy2) = points
            a, b, c = _solve3(
                [(rx0, ry0, 1.0), (rx1, ry1, 1.0), (rx2, ry2, 1.0)],
                [sx0, sx1, sx2],
            )
            d, e, f = _solve3(
                [(rx0, ry0, 1.0), (rx1, ry1, 1.0), (rx2, ry2, 1.0)],
                [sy0, sy1, sy2],
            )
            m = [a, b, c, d, e, f]
            os.makedirs(os.path.dirname(CALIB_PATH), exist_ok=True)
            with open(CALIB_PATH, "w", encoding="utf-8") as fp:
                json.dump({"m": m, "points": points}, fp)
            self.calib = m
            print("[touch] calib saved", [round(v, 2) for v in m])
            return True
        except Exception as e:
            print("[touch] calib fail", e)
            return False

    def map_with(self, points, rx, ry):
        """用刚采到的三个点临时换算，校准检查时还没存盘。"""
        (rx0, ry0, sx0, sy0), (rx1, ry1, sx1, sy1), (rx2, ry2, sx2, sy2) = points
        a, b, c = _solve3(
            [(rx0, ry0, 1.0), (rx1, ry1, 1.0), (rx2, ry2, 1.0)],
            [sx0, sx1, sx2],
        )
        d, e, f = _solve3(
            [(rx0, ry0, 1.0), (rx1, ry1, 1.0), (rx2, ry2, 1.0)],
            [sy0, sy1, sy2],
        )
        return a * rx + b * ry + c, d * rx + e * ry + f

    def raw_to_screen(self, rx, ry):
        if self.calib:
            a, b, c, d, e, f = self.calib
            return a * rx + b * ry + c, d * rx + e * ry + f
        sx = float(ry) / 639.0 * (config.SCREEN_W - 1)
        sy = float(rx) / 479.0 * (config.SCREEN_H - 1)
        return sx, sy

    def start(self):
        try:
            self.fd = os.open(self.device, os.O_RDONLY | os.O_NONBLOCK)
        except Exception as e:
            print("[touch] open fail", e)
            return False
        self._thread = threading.Thread(target=self._loop)
        self._thread.daemon = True
        self._thread.start()
        print("[touch] started", self.device)
        return True

    def _loop(self):
        while not self._stop:
            try:
                ready, _, _ = select.select([self.fd], [], [], 0.2)
            except Exception:
                time.sleep(0.05)
                continue
            if not ready:
                continue
            try:
                data = os.read(self.fd, EVENT_SIZE * 64)
            except Exception:
                continue
            if not data:
                continue
            for i in range(0, len(data) - EVENT_SIZE + 1, EVENT_SIZE):
                try:
                    _sec, _usec, etype, code, value = struct.unpack(EVENT_FMT, data[i:i + EVENT_SIZE])
                except Exception:
                    continue
                self._handle(etype, code, value)

    def _handle(self, etype, code, value):
        if etype == EV_KEY and code == BTN_TOUCH:
            self.touching = bool(value)
        elif etype == EV_ABS:
            if code in (ABS_X, ABS_MT_POSITION_X):
                self.x = int(value)
            elif code in (ABS_Y, ABS_MT_POSITION_Y):
                self.y = int(value)
            elif code == ABS_MT_TRACKING_ID:
                self.touching = value >= 0
        elif etype == EV_SYN and code == SYN_REPORT:
            if self.touching and not self.reported_down:
                self.reported_down = True
            elif (not self.touching) and self.reported_down:
                self.reported_down = False
                self._emit_tap()

    def _emit_tap(self):
        rx, ry = self.x, self.y
        x, y = self.raw_to_screen(rx, ry)
        print("[touch] tap raw=%d,%d ui=%d,%d" % (rx, ry, int(x), int(y)))
        if not self.on_tap:
            return
        try:
            self.on_tap(x, y, rx, ry)
        except TypeError:
            try:
                self.on_tap(x, y)
            except Exception as e:
                print("[touch] tap cb err", e)
        except Exception as e:
            print("[touch] tap cb err", e)

    def stop(self):
        self._stop = True
        try:
            if self.fd is not None:
                os.close(self.fd)
        except Exception:
            pass


def _solve3(A, b):
    import numpy as np
    a = np.array(A, dtype=np.float64)
    bb = np.array(b, dtype=np.float64)
    return tuple(np.linalg.solve(a, bb).tolist())
