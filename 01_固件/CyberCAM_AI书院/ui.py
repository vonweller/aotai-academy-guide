# -*- coding: utf-8 -*-
"""CyberCAM 自绘 UI：640x480，中文用文泉驿，控件命中用触摸/按键坐标。

不依赖 LVGL/Qt：OpenCV 画图 + freetype 中文 + 缓存文字 mask。
"""
import os
import time

import cv2
import numpy as np

try:
    from . import config
except Exception:
    import config

# ---------------- 配色（岭南书院：黛瓦白墙木色） ----------------
C_BG = (32, 30, 28)          # BGR 深墨
C_PANEL = (52, 48, 44)
C_PANEL2 = (68, 62, 55)
C_GOLD = (120, 190, 235)     # 金
C_JADE = (140, 190, 160)     # 青玉
C_TEXT = (238, 236, 230)
C_TEXT_DIM = (170, 168, 160)
C_RED = (70, 70, 200)
C_GREEN = (120, 200, 120)
C_LINE = (96, 92, 84)

_FONT = None
_FONT_READY = False
_MASK_CACHE = {}
_MAX_CACHE = 400


def _ensure_font():
    global _FONT, _FONT_READY
    if _FONT_READY:
        return _FONT
    _FONT_READY = True
    try:
        ft = cv2.freetype.createFreeType2()
        ft.loadFontData(config.FONT_PATH, 0)
        _FONT = ft
        print("[ui] freetype loaded", config.FONT_PATH)
    except Exception as e:
        print("[ui] freetype 不可用，中文将退化:", e)
        _FONT = None
    return _FONT


def text_size(text, size):
    ft = _ensure_font()
    if ft is not None:
        (w, h), _ = ft.getTextSize(text, size, thickness=-1)
        return int(w), int(h)
    return int(len(text) * size * 0.62), int(size * 1.2)


_PIL_FONT_CACHE = {}


def _pil_mask(text, size, color):
    """PC 兜底：用 Pillow + 系统字体渲染中文（板上用 cv2.freetype）。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None
    font = _PIL_FONT_CACHE.get(size)
    if font is None:
        for fp in (config.FONT_PATH,
                   "C:/Windows/Fonts/msyh.ttc",
                   "C:/Windows/Fonts/simhei.ttf",
                   "C:/Windows/Fonts/simsun.ttc"):
            try:
                font = ImageFont.truetype(fp, int(size))
                _PIL_FONT_CACHE[size] = font
                break
            except Exception:
                font = None
        if font is None:
            return None
    tmp = Image.new("RGB", (2, 2), (0, 0, 0))
    d = ImageDraw.Draw(tmp)
    try:
        box = d.textbbox((0, 0), text, font=font)
    except Exception:
        box = (0, 0, len(text) * size, size + 4)
    w = max(1, box[2] - box[0] + 6)
    h = max(1, box[3] - box[1] + 8)
    im = Image.new("RGB", (w, h), (0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.text((3 - box[0], 4 - box[1]), text, font=font, fill=(color[2], color[1], color[0]))
    arr = np.array(im)
    return arr[:, :, ::-1].copy()


def _mask(text, size, color):
    key = (text, size, color)
    m = _MASK_CACHE.get(key)
    if m is not None:
        return m
    ft = _ensure_font()
    w, h = text_size(text, size)
    w, h = max(1, w), max(1, h)
    canvas = None
    if ft is not None:
        canvas = np.zeros((h + 4, w + 4, 3), np.uint8)
        ft.putText(canvas, text, (2, h + 1), size, color, -1, 8, True)
    else:
        canvas = _pil_mask(text, size, color)
        if canvas is None:
            canvas = np.zeros((h + 4, w + 4, 3), np.uint8)
            cv2.putText(canvas, text, (2, h), cv2.FONT_HERSHEY_SIMPLEX, size / 32.0, color, 1, cv2.LINE_AA)
    if len(_MASK_CACHE) > _MAX_CACHE:
        _MASK_CACHE.clear()
    _MASK_CACHE[key] = canvas
    return canvas


def draw_text(img, text, pos, size=22, color=C_TEXT, anchor="lt"):
    """anchor: lt / ct / rt / lm / cm / rm"""
    if text is None:
        return
    text = str(text)
    if not text:
        return
    m = _mask(text, size, color)
    h, w = m.shape[:2]
    x, y = pos
    if anchor[0] == "c":
        x -= w // 2
    elif anchor[0] == "r":
        x -= w
    if anchor[1] == "t":
        y0 = y
    elif anchor[1] == "m":
        y0 = y - h // 2
    else:
        y0 = y - h
    x0 = int(x)
    y0 = int(y0)
    H, W = img.shape[:2]
    if y0 >= H or x0 >= W:
        return
    sx = max(0, -x0)
    sy = max(0, -y0)
    ex = min(m.shape[1], W - x0)
    ey = min(m.shape[0], H - y0)
    if ex <= sx or ey <= sy:
        return
    roi = m[sy:ey, sx:ex]
    dst = img[y0 + sy:y0 + ey, x0 + sx:x0 + ex]
    if dst.shape[:2] != roi.shape[:2]:
        return
    mask = (roi.max(axis=2) > 16)
    dst[mask] = roi[mask]
    img[y0 + sy:y0 + ey, x0 + sx:x0 + ex] = dst


def fill_rect(img, rect, color):
    x0, y0, x1, y1 = [int(v) for v in rect]
    H, W = img.shape[:2]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)
    if x1 > x0 and y1 > y0:
        img[y0:y1, x0:x1] = color


def rect_outline(img, rect, color, t=2):
    x0, y0, x1, y1 = [int(v) for v in rect]
    cv2.rectangle(img, (x0, y0), (x1, y1), color, t)


def round_rect(img, rect, color, radius=12, thickness=-1):
    x0, y0, x1, y1 = [int(v) for v in rect]
    r = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)
    if thickness < 0:
        cv2.rectangle(img, (x0 + r, y0), (x1 - r, y1), color, -1)
        cv2.rectangle(img, (x0, y0 + r), (x1, y1 - r), color, -1)
        for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
            cv2.circle(img, (cx, cy), r, color, -1)
    else:
        # 只画 4 段直线 + 4 段弧，避免重复叠加
        cv2.line(img, (x0 + r, y0), (x1 - r, y0), color, thickness)
        cv2.line(img, (x0 + r, y1), (x1 - r, y1), color, thickness)
        cv2.line(img, (x0, y0 + r), (x0, y1 - r), color, thickness)
        cv2.line(img, (x1, y0 + r), (x1, y1 - r), color, thickness)
        for cx, cy, a0 in ((x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270),
                           (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90)):
            cv2.ellipse(img, (cx, cy), (r, r), 0, a0, a0 + 90, color, thickness)


class Button(object):
    def __init__(self, bid, rect, label, size=22, style="normal"):
        self.id = bid
        self.rect = rect
        self.label = label
        self.size = size
        self.style = style
        self.enabled = True
        self.pressed = False
        self.press_t = 0.0

    def hit(self, x, y):
        if not self.enabled:
            return False
        x0, y0, x1, y1 = self.rect
        m = 12
        return (x0 - m) <= x <= (x1 + m) and (y0 - m) <= y <= (y1 + m)

    def draw(self, img, now=None):
        x0, y0, x1, y1 = self.rect
        if not self.enabled:
            bg, fg = (48, 46, 42), C_TEXT_DIM
        elif self.style == "primary":
            bg, fg = (92, 74, 40), C_GOLD
        elif self.style == "danger":
            bg, fg = (60, 44, 44), (150, 120, 200)
        elif self.style == "ghost":
            bg, fg = (44, 42, 38), C_TEXT_DIM
        else:
            bg, fg = C_PANEL2, C_TEXT
        if self.pressed and now and now - self.press_t < 0.18:
            bg = tuple(min(255, c + 40) for c in bg)
        round_rect(img, self.rect, bg, radius=10)
        round_rect(img, self.rect, C_LINE, radius=10, thickness=1)
        draw_text(img, self.label, ((x0 + x1) // 2, (y0 + y1) // 2), self.size, fg, anchor="cm")


class UI(object):
    def __init__(self):
        self.W = config.SCREEN_W
        self.H = config.SCREEN_H
        self.buttons = []
        self.footer = ""

    # ---------- 公共 ----------
    def begin(self):
        img = np.zeros((self.H, self.W, 3), np.uint8)
        img[:] = C_BG
        # 顶部装饰线
        fill_rect(img, (0, 0, self.W, 6), (70, 60, 40))
        fill_rect(img, (0, 6, self.W, 8), C_GOLD)
        return img

    def header(self, img, title, subtitle="", lang="zh", stage=0, mqtt_ok=False):
        fill_rect(img, (0, 8, self.W, 66), C_PANEL)
        # 左侧标题
        draw_text(img, title, (18, 18), 22, C_GOLD)
        # 关卡圆点：固定在第二行左侧（标题下方，不与之重叠）
        x = 20
        y_dot = 52
        for i in range(1, config.STAGE_MAX + 1):
            active = (i == stage)
            done = (stage > i)
            col = C_GOLD if active else (C_JADE if done else C_PANEL2)
            cv2.circle(img, (x, y_dot), 4, col, -1 if (active or done) else 1)
            if active:
                cv2.circle(img, (x, y_dot), 8, C_GOLD, 1)
            x += 18
        # 右上角第一行：MQTT 状态
        rx = self.W - 16
        mqtt_txt = "MQTT已连" if mqtt_ok else "MQTT离线"
        mw, _ = text_size(mqtt_txt, 12)
        draw_text(img, mqtt_txt, (rx, 22), 12, C_GREEN if mqtt_ok else (110, 110, 200), anchor="rt")
        dot_col = C_GREEN if mqtt_ok else (110, 110, 200)
        cv2.circle(img, (rx - mw - 10, 16), 4, dot_col, -1)
        # 右上角第二行：语言
        lang_txt = "语言 " + config.LANG_NAME.get(lang, lang)
        draw_text(img, lang_txt, (rx, 44), 12, C_JADE, anchor="rt")
        if subtitle:
            draw_text(img, subtitle, (rx - mw - 22, 22), 12, C_TEXT_DIM, anchor="rt")

    def footer_bar(self, img, text, hint=""):
        fill_rect(img, (0, self.H - 34, self.W, self.H), C_PANEL)
        draw_text(img, text, (16, self.H - 17), 16, C_TEXT_DIM, anchor="lm")
        if hint:
            draw_text(img, hint, (self.W - 16, self.H - 17), 16, C_GOLD, anchor="rm")

    # ---------- 场景 1：语言选择 ----------
    def screen_language(self):
        img = self.begin()
        self.header(img, "鳌台书院 · AI非遗导览", "语言 / Language", lang="zh", stage=0)
        draw_text(img, "请选择讲解语言", (self.W // 2, 110), 30, C_TEXT, anchor="ct")
        draw_text(img, "点左边普通话，点右边粤语", (self.W // 2, 152), 18, C_TEXT_DIM, anchor="ct")
        self.buttons = [
            Button("lang_zh", (24, 180, 312, 400), "普通话", size=44, style="primary"),
            Button("lang_yue", (328, 180, 616, 400), "粤语", size=44),
        ]
        for b in self.buttons:
            b.draw(img, time.time())
        self.footer_bar(img, "直接点按钮。按 K 键默认普通话", "选题也在这块屏幕上")
        return img

    def screen_calib(self, step, targets, hint=""):
        img = self.begin()
        self.header(img, "先校准触摸", "点圆点正中心", lang="zh", stage=0)
        step = max(0, min(len(targets) - 1, int(step)))
        title = "请再点一次，检查准不准" if step >= 3 else "请点金色圆点的正中心  %d / 3" % (step + 1)
        draw_text(img, title, (self.W // 2, 92), 26, C_TEXT, anchor="ct")
        if hint:
            draw_text(img, hint, (self.W // 2, 128), 20, (80, 180, 255), anchor="ct")
        x, y = targets[step]
        cv2.circle(img, (int(x), int(y)), 54, C_GOLD, 3)
        cv2.circle(img, (int(x), int(y)), 8, C_GOLD, -1)
        cv2.line(img, (int(x) - 70, int(y)), (int(x) + 70, int(y)), C_GOLD, 2)
        cv2.line(img, (int(x), int(y) - 70), (int(x), int(y) + 70), C_GOLD, 2)
        self.buttons = []
        self.footer_bar(img, "一次只出现一个点，点完再出现下一个", "点偏了会要求重来")
        return img

    # ---------- 功能选择：畅游书院 / 火眼金睛 ----------
    def screen_mode(self, lang):
        img = self.begin()
        self.header(img, "鳌台书院 · 两个功能", "请选择", lang=lang, stage=0)
        draw_text(img, "跟着小鳌，先选要做的事", (self.W // 2, 100), 26, C_TEXT, anchor="ct")
        self.buttons = [
            Button("mode_tour", (36, 150, 310, 300), "畅游书院", size=32, style="primary"),
            Button("mode_relic", (330, 150, 604, 300), "火眼金睛", size=32),
        ]
        for b in self.buttons:
            b.draw(img, time.time())
        draw_text(img, "功能一  跟着 AI 走一遍书院", (173, 330), 16, C_TEXT_DIM, anchor="ct")
        draw_text(img, "功能二  认出非遗古物就讲历史", (467, 330), 16, C_GOLD, anchor="ct")
        draw_text(img, "香云纱 · 莞草编织 · 千角灯", (self.W // 2, 360), 18, C_TEXT, anchor="ct")
        self.buttons.append(Button("lang_zh", (36, 390, 168, 446), "普通话", size=18,
                                   style="primary" if lang == "zh" else "ghost"))
        self.buttons.append(Button("lang_yue", (180, 390, 312, 446), "粤语", size=18,
                                   style="primary" if lang == "yue" else "ghost"))
        self.buttons.append(Button("mode_demo", (328, 390, 616, 446), "演示(不启摄像头)", size=16, style="ghost"))
        for b in self.buttons[2:]:
            b.draw(img, time.time())
        self.footer_bar(img, "K 键进入畅游", "H 键进入火眼金睛")
        return img

    def screen_relic(self, frame, relic_name, history, level, lang, mqtt_ok,
                     phase="recognize", quiz=None, quiz_state=None, score=0):
        img = self.begin()
        title = {
            "recognize": "火眼金睛 · 对准古物",
            "explain": "火眼金睛 · 讲解中",
            "answer": "火眼金睛 · 答题",
            "again": "火眼金睛 · 再认一次",
            "done": "火眼金睛 · 过关",
        }.get(phase, "火眼金睛 · 非遗识物")
        sub = "积分 %d" % int(score or 0)
        self.header(img, title, sub, lang=lang, stage=0, mqtt_ok=mqtt_ok)
        view = (16, 76, 400, 400)
        if frame is not None:
            H, W = frame.shape[:2]
            x0, y0, x1, y1 = view
            vw, vh = x1 - x0, y1 - y0
            scale = min(vw / float(W), vh / float(H))
            nw, nh = max(1, int(W * scale)), max(1, int(H * scale))
            small = cv2.resize(frame, (nw, nh))
            ox, oy = x0 + (vw - nw) // 2, y0 + (vh - nh) // 2
            img[oy:oy + nh, ox:ox + nw] = small
            rect_outline(img, view, C_GOLD if level == "hit" else C_LINE, 2)
        else:
            fill_rect(img, view, (24, 22, 20))
            draw_text(img, "摄像头未连接", ((view[0] + view[2]) // 2, (view[1] + view[3]) // 2), 22, C_TEXT_DIM, anchor="cm")
        draw_text(img, relic_name or "请把古物放在画面中间", (416, 92), 22, C_GOLD if relic_name else C_TEXT_DIM)
        y = 132
        for seg in _wrap(history or "可以认：香云纱、莞草编织、千角灯。认准了就用你选的语言讲它的历史。", 12)[:8]:
            draw_text(img, seg, (416, y), 16, C_TEXT)
            y += 24
        # 答题阶段：整屏重排，选项放在 footer 之上，保证看得见点得到
        if phase == "answer" and quiz:
            def _loc(v):
                """题目是 {zh:..., yue:...} 字典，也可能是纯字符串。"""
                if isinstance(v, dict):
                    return v.get(lang) or v.get("zh") or ""
                return str(v or "")

            qtext = _loc(quiz.get("q"))
            # 左侧上方：题干（两行）
            for i, seg in enumerate(_wrap(qtext, 16)[:2]):
                draw_text(img, ("问：" if i == 0 else "    ") + seg, (16, 336 + i * 26),
                          17, C_GOLD)
            self.buttons = []
            # 三个选项：竖排紧凑，屏高 480、底栏占 446 起
            # 392 / 418 / 444 过高会溢出，改成 366 起步、每项 26 高
            for i, op in enumerate((quiz.get("options") or [])[:3]):
                by = 364 + i * 28
                style = "ghost"
                if quiz_state and quiz_state.get("answered"):
                    if op.get("key") == quiz_state.get("answer"):
                        style = "primary"
                    elif op.get("key") == quiz_state.get("picked"):
                        style = "danger"
                txt = str(op.get("key")) + ". " + _loc(op.get("text") or op.get(lang))[:11]
                b = Button("ropt_" + str(op.get("key")), (12, by, 470, by + 26),
                           txt, size=15, style=style)
                b.enabled = not (quiz_state or {}).get("answered")
                self.buttons.append(b)
                b.draw(img, time.time())
            # 右侧「返回」按钮，与选项同高
            rb = Button("btn_mode", (484, 364, 624, 416), "返回", size=16, style="ghost")
            self.buttons.append(rb)
            rb.draw(img, time.time())
            self.footer_bar(img, "点上面的选项答题", "答对再认一次")
            return img
        self.buttons = [
            Button("btn_repeat", (412, 340, 624, 386), "再讲一次", size=20, style="ghost"),
            Button("btn_mode", (412, 396, 624, 446), "返回功能", size=20, style="primary"),
        ]
        if phase in ("again", "done"):
            self.buttons[0] = Button("btn_relic_try", (412, 340, 624, 386), "再认一次", size=20, style="ghost")
        for b in self.buttons:
            b.draw(img, time.time())
        hint = {
            "recognize": "认准后自动讲解，再出题考你",
            "explain": "听完讲解就出题",
            "again": "把刚才那件再拿近一点",
            "done": "这一件过关了，积分已记上",
        }.get(phase, "")
        self.footer_bar(img, hint, "K 键重听")
        return img

    # ---------- 场景 2：人脸识别 ----------
    def screen_face(self, frame, level, name, lang, stage, mqtt_ok, dets=None,
                    face_ok=False, learning=False, cam_err=""):
        img = self.begin()
        self.header(img, "第一关 · 门口迎宾", "人脸识别", lang=lang, stage=stage, mqtt_ok=mqtt_ok)
        # 摄像头预览区
        view = (16, 76, 448, 412)
        if frame is not None:
            H, W = frame.shape[:2]
            x0, y0, x1, y1 = view
            vw, vh = x1 - x0, y1 - y0
            scale = min(vw / float(W), vh / float(H))
            nw, nh = int(W * scale), int(H * scale)
            small = cv2.resize(frame, (nw, nh))
            ox, oy = x0 + (vw - nw) // 2, y0 + (vh - nh) // 2
            img[oy:oy + nh, ox:ox + nw] = small
            if dets:
                for d in dets:
                    rx0 = ox + int(d["x"] * scale)
                    ry0 = oy + int(d["y"] * scale)
                    rx1 = ox + int((d["x"] + d["w"]) * scale)
                    ry1 = oy + int((d["y"] + d["h"]) * scale)
                    ok = (d.get("score", 1.0) >= 0.6)
                    cv2.rectangle(img, (rx0, ry0), (rx1, ry1), (80, 220, 120) if ok else (60, 160, 240), 2)
            rect_outline(img, view, C_LINE, 1)
        else:
            fill_rect(img, view, (24, 22, 20))
            draw_text(img, "摄像头没有画面", (view[0] + 216, view[1] + 158), 24, C_TEXT_DIM, anchor="cm")
            hint = ("正在重新打开…" if not cam_err else ("原因：" + cam_err))[:26]
            draw_text(img, hint, (view[0] + 216, view[1] + 196), 16, (120, 118, 110), anchor="cm")
            draw_text(img, "先点「学习这张脸」，或按 K 键", (view[0] + 216, view[1] + 226), 16,
                      (110, 108, 100), anchor="cm")
        # 右侧信息
        px = 470
        draw_text(img, "识别状态", (px, 92), 20, C_GOLD)
        status_map = {
            "none": ("等待访客", C_TEXT_DIM),
            "detected": ("检测到人脸…", C_JADE),
            "recognized": ("识别成功", C_GREEN),
            "unknown": ("未注册访客", (120, 160, 230)),
        }
        st_text, st_col = status_map.get(level, ("等待访客", C_TEXT_DIM))
        draw_text(img, st_text, (px, 130), 26, st_col)
        if name:
            draw_text(img, "欢迎", (px, 176), 18, C_TEXT_DIM)
            draw_text(img, name, (px, 206), 28, C_GOLD)
        if face_ok:
            draw_text(img, "已确认", (px, 246), 22, C_GREEN)
        if learning:
            draw_text(img, "学习中…", (px, 246), 22, C_GOLD)
        self.buttons = [
            Button("btn_next", (468, 396, 624, 446), "进入下一关", size=22, style="primary"),
            Button("btn_learn", (468, 344, 624, 390), "学习这张脸", size=20),
            Button("btn_lang", (468, 296, 624, 338), "切换语言", size=18, style="ghost"),
            Button("btn_repeat", (468, 252, 624, 290), "重播", size=17, style="ghost"),
        ]
        for b in self.buttons:
            b.draw(img, time.time())
        if learning:
            self.footer_bar(img, "保持正对镜头 2 秒，正在采集", "别动")
        else:
            self.footer_bar(img, "点「学习这张脸」让相机记住你", "距离 40–80cm · K 键也能学")
        return img

    # ---------- 场景 3：关卡内容 ----------
    def screen_stage(self, stage, stage_title, lines, quiz, quiz_state, lang, mqtt_ok, speak_state=""):
        img = self.begin()
        self.header(img, stage_title, "AI 导览", lang=lang, stage=stage, mqtt_ok=mqtt_ok)
        # 正文卡片
        card = (16, 78, 624, 322)
        round_rect(img, card, C_PANEL, radius=14)
        round_rect(img, card, C_LINE, radius=14, thickness=1)
        y = 92
        for i, ln in enumerate(lines[:2]):
            if y > 190:
                break
            txt = ln
            # 自动换行（按字数粗切）
            for seg in _wrap(txt, 22):
                if y > 208:
                    break
                draw_text(img, seg, (34, y), 20 if i == 0 else 18, C_TEXT if i == 0 else C_TEXT_DIM)
                y += 27
            y += 4
        # 问答
        self.buttons = []
        if quiz:
            qtext = quiz.get("q", "")
            draw_text(img, "问：" + qtext[:36], (34, 232), 17, C_GOLD, anchor="lt")
            opts = quiz.get("options", [])
            bw = 176
            for i, op in enumerate(opts[:3]):
                bx = 30 + i * (bw + 12)
                style = "ghost"
                if quiz_state.get("answered"):
                    if op["key"] == quiz_state.get("answer"):
                        style = "primary"
                    elif op["key"] == quiz_state.get("picked"):
                        style = "danger"
                b = Button("opt_" + op["key"], (bx, 268, bx + bw, 320), op["key"] + ". " + op["text"], size=17, style=style)
                b.enabled = not quiz_state.get("answered")
                self.buttons.append(b)
                b.draw(img, time.time())
        # 底部控制
        ctrl = [
            ("btn_prev", "上一关", 16, 128, "ghost"),
            ("btn_repeat", "重播", 140, 244, "ghost"),
            ("btn_lang", "语言", 256, 346, "ghost"),
            ("btn_next", "下一关", 358, 470, "primary"),
            ("btn_home", "回首页", 482, 624, "ghost"),
        ]
        for bid, label, x0, x1, style in ctrl:
            b = Button(bid, (x0, 406, x1, 452), label, size=20, style=style)
            self.buttons.append(b)
            b.draw(img, time.time())
        if speak_state:
            draw_text(img, speak_state[:30], (34, 336), 14, C_JADE)
        self.footer_bar(img, "点选项答题，点下一关继续", "重播可再听一遍")
        return img

    # ---------- 场景 4：结束 ----------
    def screen_end(self, lang, mqtt_ok):
        img = self.begin()
        self.header(img, "参观结束 · 留墨寄愿", "谢谢", lang=lang, stage=5, mqtt_ok=mqtt_ok)
        draw_text(img, "感谢您的到访", (self.W // 2, 150), 40, C_GOLD, anchor="ct")
        draw_text(img, "鳌台书院 · 粤地非遗物语", (self.W // 2, 205), 24, C_TEXT, anchor="ct")
        draw_text(img, "愿书香与非遗，被更多人看见", (self.W // 2, 248), 20, C_TEXT_DIM, anchor="ct")
        self.buttons = [
            Button("btn_restart", (170, 300, 470, 356), "重新开始", size=24, style="primary"),
        ]
        for b in self.buttons:
            b.draw(img, time.time())
        self.footer_bar(img, "点下面按钮重新开始", "")
        return img

    # ---------- 命中 ----------
    def hit(self, x, y):
        for b in self.buttons:
            if b.hit(x, y):
                b.pressed = True
                b.press_t = time.time()
                return b.id
        return None

    def any_button(self, bid):
        for b in self.buttons:
            if b.id == bid:
                return b
        return None


def _wrap(text, n):
    text = str(text or "")
    if len(text) <= n:
        return [text] if text else []
    out, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= n or ch in "。！？；":
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out
