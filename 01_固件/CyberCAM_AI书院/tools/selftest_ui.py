# -*- coding: utf-8 -*-
"""CyberCAM 界面自检：把所有页面渲染成 PNG（PC 无硬件也能跑）

  python tools/selftest_ui.py            # 输出到 ./qc/
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import cv2
import numpy as np

import config
import content_loader
import ui as ui_mod

OUT = os.path.join(HERE, "qc")
os.makedirs(OUT, exist_ok=True)


def save(name, img):
    p = os.path.join(OUT, name)
    ok, buf = cv2.imencode(".png", img)
    if ok:
        buf.tofile(p)
    print("saved", p)
    return p


def main():
    content = content_loader.Content()
    u = ui_mod.UI()

    save("01_language.png", u.screen_language())

    # 人脸页（无摄像头 -> 演示占位）
    frame = np.zeros((480, 640, 3), np.uint8)
    frame[:] = (40, 38, 35)
    for y in range(0, 480, 40):
        cv2.line(frame, (0, y), (640, y), (52, 50, 46), 1)
    ui_mod.draw_text(frame, "DEMO CAMERA", (320, 200), 28, (120, 118, 110), anchor="ct")
    save("02_face_wait.png",
         u.screen_face(frame, "none", None, "zh", 1, True, dets=None, face_ok=False))
    save("03_face_ok.png",
         u.screen_face(frame, "recognized", "预约访客", "zh", 1, True, dets=None, face_ok=True))

    # 五关
    for st in range(2, 6):
        lines = [ln.get("zh", "") for ln in content.lines(st) if ln.get("zh")]
        quiz = content.quiz(st)
        quiz_view = None
        if quiz:
            quiz_view = {
                "q": content.quiz_text(quiz, "zh"),
                "options": content.quiz_options(quiz, "zh"),
                "answer": quiz.get("answer"),
            }
        img = u.screen_stage(st, content.stage_name(st, "zh"), lines, quiz_view,
                             {"answered": False}, "zh", True, speak_state="")
        save("stage%d_zh.png" % st, img)
        if quiz:
            img2 = u.screen_stage(st, content.stage_name(st, "yue"),
                                  [ln.get("yue", "") for ln in content.lines(st) if ln.get("yue")],
                                  {"q": content.quiz_text(quiz, "yue"),
                                   "options": content.quiz_options(quiz, "yue"),
                                   "answer": quiz.get("answer")},
                                  {"answered": True, "picked": "A", "answer": quiz.get("answer")},
                                  "yue", False, speak_state="")
            save("stage%d_yue_answered.png" % st, img2)

    save("end.png", u.screen_end("zh", True))
    print("OK")


if __name__ == "__main__":
    main()
