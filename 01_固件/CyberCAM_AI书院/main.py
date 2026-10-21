# -*- coding: utf-8 -*-
"""鳌台书院 AI 非遗导览 · CyberCAM 主程序。

重构版，按 CyberCAM 的硬约束组织：
  1. 摄像头只有一个入口 camera.Camera，进出页面时明确 acquire/release
  2. 界面按需重绘（脏标记），不每帧全画，省 CPU
  3. 播报有队列，页一换就停，不叠音、不留僵尸进程
  4. 所有退出路径都走 cleanup：释放摄像头 + 停播报 + 恢复桌面

按键：K 键 = 确认/学习/下一关；1 普通话，2 粤语；
      N 下一关，P 上一关，R 重播，Q 退出
"""
import argparse
import os
import signal
import sys
import threading
import time

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import config
import content_loader
import audio as audio_mod
import bus as bus_mod
import camera as camera_mod
import display as display_mod
import face as face_mod
import points as points_mod
import relic as relic_mod
import touch as touch_mod
import ui as ui_mod

RUNNING = True
SHOW_WINDOW = False


def log(*a):
    print("[main]", *a)


class App(object):
    def __init__(self, demo=False, use_touch=True, use_display=True, show_window=False):
        self.demo = demo
        self.use_display = use_display
        self.show_window = show_window

        # ---- 状态机 ----
        self.state = "lang"
        self.lang = "zh"
        self.prev_state = "lang"

        # ---- 关卡 ----
        self.stage = 1
        self.quiz_state = {}

        # ---- 人脸 ----
        self.face_ok = False
        self.visitor = None
        self.face_res = {}
        self.dets = []
        self.learning = False
        self._learn_ends = 0.0
        self._learn_grays = []

        # ---- 火眼金睛 ----
        self.relic_phase = "recognize"
        self.relic_key = ""
        self.relic_quiz = None
        self.relic_quiz_state = {}
        self.relic_view = {}
        self.relic_done = []

        # ---- 界面 ----
        self.frame = None
        self.subtitle = ""
        self.dirty = True
        self._img = None
        self._tap = None
        self._tap_t = 0.0
        self._calib_step = 0
        self._calib_pts = []
        self._calib_t = 0.0
        self.calib_targets = [(120, 210), (520, 210), (200, 400), (440, 390)]
        self.calib_msg = ""

        # ---- 组件 ----
        self.content = content_loader.Content()
        self.speaker = audio_mod.Speaker(self.content)
        self.cam = camera_mod.Camera()
        self.face = face_mod.Face()
        self.relic = relic_mod.RelicEngine()
        self.ui = ui_mod.UI()
        self.touch = None
        self.btn = None
        self.bus = bus_mod.Bus(on_cmd=self.on_cmd)
        self.points = points_mod.Points("预约访客")
        self.score = 0
        self._pusher = None
        self._push_t = 0.0
        self._key_prev = False
        self._key_t = 0.0

    # ================= 生命周期 ==================
    def start(self):
        global SHOW_WINDOW
        SHOW_WINDOW = self.show_window
        display_mod.init(use_display=self.use_display)
        self.open_touch()
        self.open_button()
        try:
            self.bus.start()
        except Exception as e:
            log("MQTT 启动失败", e)
        self.go_lang()
        self.mark_dirty()

    def cleanup(self):
        log("退出清理开始")
        try:
            self.speaker.stop()
        except Exception:
            pass
        try:
            self.bus.stop()
        except Exception:
            pass
        try:
            if self.touch:
                self.touch.stop()
        except Exception:
            pass
        try:
            self.cam.release()
        except Exception:
            pass
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        try:
            import subprocess
            subprocess.run("pkill -9 -x aplay; pkill -9 -x ffmpeg; true",
                           shell=True, timeout=4)
        except Exception:
            pass
        if self.use_display:
            try:
                display_mod.start_desktop()
            except Exception:
                pass
        log("退出清理完成")

    # ================= 输入 ==================
    def open_touch(self):
        if self.demo:
            return
        try:
            self.touch = touch_mod.Touch(on_tap=self.on_tap)
            if not self.touch.start():
                self.touch = None
        except Exception as e:
            log("触摸不可用", e)

    def open_button(self):
        if self.demo:
            return
        try:
            import board
            import digitalio
            d = digitalio.DigitalInOut(board.KEY)
            d.direction = digitalio.Direction.INPUT
            d.pull = digitalio.Pull.UP
            self.btn = d
            log("K 键就绪")
        except Exception as e:
            log("K 键不可用", e)
            self.btn = None

    def poll_key(self):
        if self.btn is None:
            return
        now = time.time()
        try:
            pressed = not self.btn.value
        except Exception:
            return
        if pressed and not self._key_prev and now - self._key_t > 0.45:
            self._key_t = now
            self._key_prev = True
            self.on_key()
        if not pressed:
            self._key_prev = False

    def on_tap(self, x, y, rx=None, ry=None):
        if self.state == "calib":
            self._tap_calib(rx, ry)
            return
        xi, yi = int(round(x)), int(round(y))
        self._tap = (max(0, min(config.SCREEN_W - 1, xi)),
                     max(0, min(config.SCREEN_H - 1, yi)))
        self._tap_t = time.time()
        self.mark_dirty()
        bid = self.ui.hit(xi, yi)
        if bid:
            self.on_button(bid)

    def on_button(self, bid):
        log("按键", bid)
        if bid == "lang_zh":
            self.set_lang("zh")
        elif bid == "lang_yue":
            self.set_lang("yue")
        elif bid == "mode_tour":
            self.demo = False
            self.go_face()
        elif bid == "mode_demo":
            self.demo = True
            self.go_face()
        elif bid == "mode_relic":
            self.go_relic()
        elif bid == "btn_learn":
            self.start_learn()
        elif bid == "btn_next":
            self.next_stage()
        elif bid == "btn_prev":
            self.prev_stage()
        elif bid == "btn_repeat":
            self.repeat()
        elif bid == "btn_lang":
            self.set_lang("yue" if self.lang == "zh" else "zh")
        elif bid == "btn_home":
            self.go_lang()
        elif bid == "btn_mode":
            self.go_mode()
        elif bid == "btn_restart":
            self.reset()
        elif bid.startswith("opt_"):
            self.answer_quiz(bid.split("_", 1)[1])
        elif bid.startswith("ropt_"):
            self.answer_relic(bid.split("_", 1)[1])
        elif bid == "btn_relic_try":
            self.relic_phase = "recognize"
            self.relic_key = ""
            self.relic.reset_announce()
            self.say("p_relic_intro")
            self.mark_dirty()

    def on_key(self):
        if self.state == "calib":
            return
        if self.state == "lang":
            self.set_lang(self.lang)
        elif self.state == "mode":
            self.go_face()
        elif self.state == "face":
            self.next_stage()
        elif self.state == "relic":
            if self.relic_key:
                self.say_relic(self.relic_key)
            else:
                self.go_mode()
        else:
            self.next_stage()
    # ================= 状态流转 ==================
    def set_lang(self, lang):
        if lang not in config.LANGS:
            return
        self.lang = lang
        self.bus.event("lang_changed", lang=lang)
        self.bus.state(self.stage, lang, face_ok=self.face_ok)
        if self.state == "lang":
            self.go_mode()
        else:
            self.mark_dirty()

    def go_calib(self, msg=""):
        self.stop_audio()
        self.state = "calib"
        self._calib_step = 0
        self._calib_pts = []
        self.calib_msg = msg
        self.subtitle = "请点圆点校准"
        self.mark_dirty()

    def go_lang(self):
        self._auto_at = 0.0
        self.stop_audio()
        self.state = "lang"
        self.subtitle = "请选择讲解语言"
        self.mark_dirty()

    def go_mode(self):
        self.stop_audio()
        self.state = "mode"
        self.subtitle = "请选择功能"
        self.mark_dirty()

    def go_face(self):
        self.stop_audio()
        self.state = "face"
        self.stage = 1
        self.face_ok = False
        self.face_res = {}
        self.face.last_hit = None
        if not self.demo:
            self.cam.ensure()
        self.say("s1_prompt")
        self.bus.event("tour_start", stage=1, lang=self.lang)
        self.bus.event("stage_enter", stage=1, lang=self.lang)
        self.bus.state(1, self.lang, face_ok=False)
        self.mark_dirty()

    def go_relic(self):
        self.stop_audio()
        self.demo = False
        self.state = "relic"
        self.relic_phase = "recognize"
        self.relic_key = ""
        self.relic_quiz = None
        self.relic_quiz_state = {}
        self.relic_view = {}
        self.relic_done = []
        self.relic.reset_announce()
        self.cam.ensure()
        self.say("p_relic_intro")
        self.bus.event("relic_mode", lang=self.lang, done=list(self.relic_done),
                       need=list(config.RELIC_KEYS))
        self.mark_dirty()

    def go_stage(self, stage):
        self._auto_at = 0.0
        self.stop_audio()
        stage = max(1, min(config.STAGE_MAX, int(stage)))
        self.stage = stage
        self.state = "stage"
        self.quiz_state = {}
        self.bus.event("stage_enter", stage=stage, lang=self.lang)
        self.bus.state(stage, self.lang, face_ok=self.face_ok)
        st = self.content.stage(stage)
        lines = st.get("lines") or []
        entry = st.get("entry") or (lines[0].get("id") if lines else None)
        if entry:
            self.say(entry)
        self.mark_dirty()

    def next_stage(self):
        if self.state == "face":
            self.go_stage(2)
        elif self.state == "stage":
            if self.stage >= config.STAGE_MAX:
                self.go_end()
            else:
                self.go_stage(self.stage + 1)
        elif self.state == "end":
            self.reset()

    def prev_stage(self):
        if self.state == "stage" and self.stage > 2:
            self.go_stage(self.stage - 1)
        elif self.state == "stage" and self.stage == 2:
            self.go_face()

    def go_end(self):
        self.stop_audio()
        self.state = "end"
        self.award("finish", "走完全程", uniq="finish")
        self.bus.event("stage_done", stage=config.STAGE_MAX, ok=True)
        self.bus.state(config.STAGE_MAX, self.lang, face_ok=self.face_ok)
        self.mark_dirty()

    def reset(self):
        log("重置")
        self.stage = 1
        self.face_ok = False
        self.visitor = None
        self.quiz_state = {}
        self.bus.event("reset")
        self.bus.state(1, self.lang, face_ok=False)
        self.go_lang()

    # ================= 播报 ==================
    def stop_audio(self):
        try:
            self.speaker.stop()
        except Exception:
            pass
        try:
            self.bus.event("speak_stop")
        except Exception:
            pass

    def say(self, line_id, default="", fallback=None):
        text, _ = self.content.text(line_id, self.lang)
        if not text and fallback:
            text = fallback.get(self.lang) or fallback.get("zh", "")
        if not text:
            text = default
        if text:
            self.subtitle = text
        ok = self.speaker.say(line_id, self.lang, text=text) if line_id else False
        if not ok and text:
            ok = self.speaker.say_text(text, self.lang)
        self.bus.event("speak", id=line_id, text=text, lang=self.lang)
        self.mark_dirty()
        return ok

    def repeat(self):
        if self.state == "relic":
            if self.relic_key:
                self.say_relic(self.relic_key)
            else:
                self.say("p_relic_intro")
        elif self.state == "stage":
            st = self.content.stage(self.stage)
            lines = st.get("lines") or []
            if lines:
                self.say(st.get("entry") or lines[0].get("id"), fallback=lines[0])
        elif self.state == "face":
            self.say("s1_prompt", default="请正对摄像头，让我先认一认你。")
        elif self.state == "end":
            self.say("s5_bye")

    # ================= 积分 ==================
    def award(self, kind, note="", uniq=None):
        try:
            score, gain = self.points.add(kind, note, uniq=uniq)
        except Exception as e:
            log("积分失败", e)
            return 0
        self.score = score
        if gain > 0:
            self.bus.publish("aotai/points", {
                "who": self.points.who, "score": score,
                "gain": gain, "k": kind})
            log("积分 +".replace("+", "+%d" % gain), score)
        return gain

    def bind_visitor(self, name):
        self.visitor = name or "预约访客"
        try:
            self.score = self.points.bind(self.visitor)
        except Exception:
            self.score = 0
        self.bus.publish("aotai/points", {
            "who": self.visitor, "score": self.score, "gain": 0, "k": "bind"})
    # ================= 答题 ==================
    def answer_quiz(self, key):
        quiz = self.content.quiz(self.stage)
        if not quiz or self.quiz_state.get("answered"):
            return
        correct = quiz.get("answer")
        ok = (key == correct)
        self.quiz_state = {"answered": True, "picked": key,
                            "answer": correct, "ok": ok}
        qid = quiz.get("qid") or ""
        if ok:
            explain = self.content.quiz_explain(quiz, self.lang)
            self.say(qid + "_a", default=explain)
            self.award("quiz_right", "第%d关答对" % self.stage, uniq="q_%s" % qid)
        else:
            wrong = quiz.get("explain_wrong") or {}
            explain = wrong.get(self.lang) or wrong.get("zh") or ""
            line_id = qid + "_wrong"
            if not self.content.text(line_id, self.lang)[0]:
                line_id = ""
            if not explain:
                explain = "没关系，再想一想。"
            self.say(line_id, default=explain) if line_id else self.say("", default=explain)
            # 答错允许重答
            self.quiz_state = {"answered": False, "picked": key,
                               "answer": correct, "ok": False}
        self.bus.event("quiz_answered", stage=self.stage, qid=qid,
                        answer=key, ok=ok)
        self.bus.event("stage_done", stage=self.stage, ok=ok)
        self.mark_dirty()

    # ================= 火眼金睛 ==================
    def _relic_of(self, key):
        for rel in self.content.relics():
            if rel.get("key") == key or rel.get("id") == key:
                return rel
        return None

    def say_relic(self, key):
        rel = self._relic_of(key)
        if not rel:
            return
        name = (rel.get("name") or {}).get(self.lang) or ""
        text = rel.get(self.lang) or rel.get("zh") or ""
        self.subtitle = text
        self.speaker.say(rel.get("id"), self.lang, text=text)
        self.bus.event("relic", id=rel.get("id"), key=key,
                        name=name, lang=self.lang)
        quiz = rel.get("quiz")
        if quiz:
            self.bus.event("relic_quiz", key=key, quiz={
                "q": quiz.get("q"), "options": quiz.get("options"),
                "answer": quiz.get("answer")}, lang=self.lang)
        self.mark_dirty()

    def answer_relic(self, key):
        quiz = self.relic_quiz or {}
        if not quiz or self.relic_quiz_state.get("answered"):
            return
        correct = quiz.get("answer")
        ok = (key == correct)
        self.relic_quiz_state = {"answered": True, "picked": key,
                                 "answer": correct, "ok": ok}
        rel = self._relic_of(self.relic_key) or {}
        rid = rel.get("id") or ""
        if ok:
            gain = self.award("relic_quiz_right", "火眼金睛答对",
                              uniq="rq_%s" % self.relic_key)
            self.say(rid + "_ok", default="答对啦，积分加 %d。" % gain)
            self.relic_phase = "again"
            self.relic.reset_announce()
        else:
            self.say(rid + "_no", default="再想想。")
            self.relic_quiz_state = {"answered": False}
        self.bus.event("relic_quiz_result", key=self.relic_key,
                        ok=ok, lang=self.lang)
        self.mark_dirty()

    def pass_relic(self, key):
        """一件过关。记进已完成列表，然后自动进入下一件的识别。"""
        self.award("relic_quiz_right", "复认通过", uniq="rp_%s" % key)
        self.say("p_relic_pass")
        if key not in self.relic_done:
            self.relic_done.append(key)
        self.bus.event("relic_pass", key=key, lang=self.lang,
                       done=list(self.relic_done),
                       all=(len(self.relic_done) >= len(config.RELIC_KEYS)))
        self.mark_dirty()
        if len(self.relic_done) >= len(config.RELIC_KEYS):
            self.finish_relic_all()
        else:
            # 还有没认的 -> 回到识别态，等他拿下一件
            self.relic_phase = "recognize"
            self.relic_key = ""
            self.relic_quiz = None
            self.relic_quiz_state = {}
            self.relic.reset_announce()
            left = [k for k in config.RELIC_KEYS if k not in self.relic_done]
            self.subtitle = "还剩 %d 件，请拿下一件放到镜头前" % len(left)
            self.say("p_relic_next", default="还剩%d件，请拿下一件放到镜头前。" % len(left))
            self.mark_dirty()

    def finish_relic_all(self):
        """三件都认完 -> 告诉网页，可以出兑换了。"""
        self.relic_phase = "all_done"
        self.say("p_all_done", default="所有任务都完成了，快去看看能换什么。")
        self.bus.event("relic_all_done", lang=self.lang, done=list(self.relic_done))
        self.subtitle = "全部认完！快去看兑换"
        self.mark_dirty()

    def update_relic(self, frame):
        if self.relic_phase == "answer":
            return
        if frame is None:
            self.relic_view = {"level": "nocam"}
            return
        hit = self.relic.step(frame, time.time())
        self.relic_view = hit
        if not hit.get("id"):
            return
        if self.relic_phase == "recognize" and hit.get("speak"):
            self.relic_key = hit["id"]
            rel = self._relic_of(self.relic_key) or {}
            self.relic_quiz = rel.get("quiz")
            self.say_relic(self.relic_key)
            self.relic_phase = "explain"
            self._quiz_at = time.time() + 9.0
        elif self.relic_phase == "explain" and time.time() >= getattr(self, "_quiz_at", 0):
            self.relic_phase = "answer"
            self.mark_dirty()
        elif self.relic_phase == "again" and hit.get("speak"):
            if hit["id"] == self.relic_key:
                self.pass_relic(hit["id"])
            else:
                self.say("p_relic_bring")

    # ================= 人脸 ==================
    def start_learn(self):
        if self.state != "face":
            return
        if not self.cam.ensure():
            self.subtitle = "摄像头没打开，学不了"
            self.mark_dirty()
            return
        self.learning = True
        self._learn_ends = time.time() + 2.5
        self._learn_grays = []
        self.subtitle = "正在学习你的脸，请正对镜头…"
        log("开始学习人脸")
        self.mark_dirty()

    def learn_feed(self, frame):
        if not self.learning:
            return
        if time.time() > self._learn_ends or len(self._learn_grays) >= 15:
            self.finish_learn()
            return
        if frame is None:
            return
        dets = self.face.detect(frame)
        if not dets:
            return
        d = max(dets, key=lambda x: x["w"] * x["h"])
        if d["w"] < config.FACE_MIN_SIZE:
            return
        g = self.cam.crop_face(frame, d)
        if g is not None:
            self._learn_grays.append(g)

    def finish_learn(self):
        self.learning = False
        grays = self._learn_grays or []
        self._learn_grays = []
        if not grays:
            self.subtitle = "没看清，靠近一点再来"
            self.speaker.say_text("没看清，请靠近一点再来一次。", self.lang)
            self.mark_dirty()
            return
        name = self.visitor or "预约访客"
        n = self.face.learn(grays, name)
        if n:
            self.face_ok = True
            self.bind_visitor(name)
            self.award("face", "人脸学习", uniq="face_%s" % name)
            self.subtitle = "学好了，现在能认出你"
            self.say("s1_welcome_ok")
            self.bus.event("face_enrolled", visitor=name,
                            samples=n, lang=self.lang)
            self.bus.state(1, self.lang, face_ok=True, visitor=name)
            self.schedule_next_stage()      # 学完也自动进第二关
        else:
            self.subtitle = "学习失败，请再试一次"
        self.mark_dirty()

    def schedule_next_stage(self, delay=0.0):
        """欢迎语播完自动进第二关，网页同步走 stage_enter。"""
        if delay <= 0:
            # 按音频实际长度估：普通话 ~7.7s，粤语 ~9.6s，留 1.2s 余量
            delay = 9.8 if self.lang == "yue" else 8.0
        self._auto_at = time.time() + delay
        self._auto_to = 2
        log("人脸通过，%.1fs 后自动进第二关" % delay)

    def tick_auto(self):
        """主循环每帧调用：到点就进下一关。"""
        at = getattr(self, "_auto_at", 0.0)
        if not at or time.time() < at:
            return
        self._auto_at = 0.0
        to = getattr(self, "_auto_to", 0)
        if self.state == "face" and to:
            log("自动进入第%d关" % to)
            self.go_stage(to)

    def update_face(self, frame):
        if frame is None:
            self.face_res = {"level": "nocam"}
            return
        res = self.face.step(frame, time.time())
        self.face_res = res
        level = res.get("level")
        self.dets = [res["box"]] if res.get("box") else []
        if level == "recognized" and not self.face_ok:
            name = res.get("name") or "预约访客"
            self.face_ok = True
            self.bind_visitor(name)
            self.award("face", "人脸识别", uniq="face_%s" % name)
            self.say("s1_welcome_ok")
            self.bus.event("face_recognized", stage=1, visitor=name, lang=self.lang)
            self.bus.state(1, self.lang, face_ok=True, visitor=name)
            self.schedule_next_stage()      # 欢迎语播完自动进第二关
            self.mark_dirty()
        elif level == "detected":
            self.mark_dirty()
    # ================= 画面 ==================
    def mark_dirty(self):
        self.dirty = True

    def render(self):
        ui = self.ui
        if self.state == "calib":
            return ui.screen_calib(self._calib_step, self.calib_targets, self.calib_msg)
        if self.state == "lang":
            return ui.screen_language()
        if self.state == "mode":
            return ui.screen_mode(self.lang)
        if self.state == "relic":
            rel = self._relic_of(self.relic_key) or {}
            name = (rel.get("name") or {}).get(self.lang) or ""
            hist = rel.get(self.lang) or rel.get("zh") or ""
            return ui.screen_relic(
                self.frame, name, hist,
                self.relic_view.get("level", "none"),
                self.lang, self.mqtt_ok(),
                phase=self.relic_phase,
                quiz=self.relic_quiz if self.relic_phase == "answer" else None,
                quiz_state=self.relic_quiz_state,
                score=self.score)
        if self.state == "face":
            return ui.screen_face(
                self.frame,
                self.face_res.get("level", "none"),
                self.visitor if self.face_ok else None,
                self.lang, 1, self.mqtt_ok(),
                dets=self.dets, face_ok=self.face_ok,
                learning=self.learning,
                cam_err=self.cam.last_err)
        if self.state == "stage":
            st = self.content.stage(self.stage)
            lines = [ln.get(self.lang) or ln.get("zh", "")
                     for ln in (st.get("lines") or [])]
            quiz = self.content.quiz(self.stage)
            qv = None
            if quiz:
                qv = {"q": self.content.quiz_text(quiz, self.lang),
                      "options": self.content.quiz_options(quiz, self.lang),
                      "answer": quiz.get("answer")}
            return ui.screen_stage(
                self.stage, self.content.stage_name(self.stage, self.lang),
                lines, qv, self.quiz_state, self.lang, self.mqtt_ok(),
                speak_state=self.subtitle[:38] if self.subtitle else "")
        return ui.screen_end(self.lang, self.mqtt_ok())

    def mqtt_ok(self):
        return bool(getattr(self.bus, "connected", False))

    def show(self, img):
        if self._tap and time.time() - self._tap_t < 0.4:
            cv2.circle(img, self._tap, 13, (80, 220, 255), 3)
        display_mod.show(img)
        if SHOW_WINDOW:
            try:
                cv2.imshow("Aotai", img)
                cv2.waitKey(1)
            except Exception:
                pass

    # ================= 推送到网页 ==================
    def push_frame(self, frame):
        if self.demo or frame is None or self.state not in ("face", "relic"):
            return
        now = time.time()
        if now - self._push_t < 0.5:
            return
        self._push_t = now
        try:
            ok, buf = cv2.imencode(".jpg", cv2.resize(frame, (320, 240)),
                                   [int(cv2.IMWRITE_JPEG_QUALITY), 55])
            if not ok:
                return
            payload = buf.tobytes()
        except Exception:
            return
        url = config.WEB_PUSH

        def send():
            try:
                import urllib.request
                req = urllib.request.Request(url, data=payload,
                                             headers={"Content-Type": "image/jpeg"})
                urllib.request.urlopen(req, timeout=1.5).read()
            except Exception:
                pass

        threading.Thread(target=send, daemon=True).start()

    # ================= 校准 ==================
    def _tap_calib(self, rx, ry):
        now = time.time()
        if rx is None or now - self._calib_t < 0.5:
            return
        self._calib_t = now
        if self._calib_step < 3:
            tx, ty = self.calib_targets[self._calib_step]
            self._calib_pts.append((float(rx), float(ry), float(tx), float(ty)))
            self._calib_step += 1
            log("校准点", self._calib_step, int(rx), int(ry))
            self.mark_dirty()
            return
        try:
            mx, my = self.touch.map_with(self._calib_pts, float(rx), float(ry))
        except Exception as e:
            self.go_calib("算不准，请重来")
            return
        tx, ty = self.calib_targets[3]
        err = ((mx - tx) ** 2 + (my - ty) ** 2) ** 0.5
        log("校准误差", round(err, 1))
        if self.touch.save_calib(self._calib_pts):
            self._did_calib = True
            self.go_lang()
        else:
            self.go_calib("保存失败，请重来")

    # ================= 主循环 ==================
    def step(self):
        t0 = time.time()
        if not self.demo and self.state in ("face", "relic"):
            self.cam.ensure()
        frame = self.cam.read() if not self.demo else None
        self.frame = frame
        self.push_frame(frame)
        if self.learning:
            self.learn_feed(frame)
        elif self.state == "face" and not self.demo:
            self.update_face(frame)
        elif self.state == "relic" and not self.demo:
            self.update_relic(frame)
        self.tick_auto()
        # 只在"脏了"时重画：静态页几乎不耗 CPU，视频页跟着相机刷新
        live = self.state in ("face", "relic") and not self.demo
        if live or self.dirty or self._img is None:
            self._img = self.render()
            self.dirty = False
            self.show(self._img)
        self.poll_key()
        try:
            k = cv2.waitKey(1) & 0xFF
        except Exception:
            k = 255
        if k != 255:
            self.on_kb(k)
        fps = config.UI_FPS if live else config.UI_FPS_IDLE
        dt = time.time() - t0
        if dt < 1.0 / fps:
            time.sleep(1.0 / fps - dt)

    def on_kb(self, k):
        global RUNNING
        if k in (ord("q"), 27):
            RUNNING = False
        elif k == ord("n"):
            self.next_stage()
        elif k == ord("p"):
            self.prev_stage()
        elif k == ord("r"):
            self.repeat()
        elif k == ord("l"):
            self.set_lang("yue" if self.lang == "zh" else "zh")
        elif k == ord("1"):
            self.set_lang("zh")
        elif k == ord("2"):
            self.set_lang("yue")
        elif k == ord("k"):
            self.on_key()
        elif k in (ord("a"), ord("b"), ord("c")):
            if self.state == "relic":
                self.answer_relic(chr(k).upper())
            else:
                self.answer_quiz(chr(k).upper())

    def on_cmd(self, data):
        cmd = (data or {}).get("cmd")
        log("MQTT", cmd)
        if cmd == "set_lang":
            self.set_lang(data.get("lang", "zh"))
        elif cmd == "next":
            self.next_stage()
        elif cmd == "prev":
            self.prev_stage()
        elif cmd == "repeat":
            self.repeat()
        elif cmd == "reset":
            self.reset()
        elif cmd == "goto_stage":
            st = int(data.get("stage", 1))
            self.go_face() if st <= 1 else self.go_stage(st)
        elif cmd == "relic_answer":
            if self.state == "relic":
                self.answer_relic(str(data.get("answer", "")).upper())


def main():
    global RUNNING
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--no-touch", action="store_true")
    ap.add_argument("--no-display", action="store_true")
    ap.add_argument("--window", action="store_true")
    a = ap.parse_args()

    def term(signum, frame):
        global RUNNING
        RUNNING = False
        log("收到退出信号", signum)

    signal.signal(signal.SIGTERM, term)
    signal.signal(signal.SIGINT, term)
    # 桌面用 app-launcher 拉起 APP，滑动退出会给 SIGTERM。
    # 但如果这个进程是被 setsid/脱离方式启动的，父进程会变成 1，
    # 桌面退出时没人通知它 —— 于是它继续占着摄像头、继续往网页推画面。
    # 这里检测到「自己成了孤儿」就主动退出，避免后台残留。
    signal.signal(signal.SIGHUP, term)

    app = App(demo=a.demo, use_touch=not a.no_touch,
              use_display=not a.no_display, show_window=a.window)

    # 记下最初的父进程：桌面 app-launcher 拉起时父进程不是 1。
    # 若中途发现父进程变成 1（被 reparent，说明启动它的进程已退出），
    # 就主动收工，别在后台占着摄像头。
    try:
        ppid0 = os.getppid()
    except Exception:
        ppid0 = 0

    def orphaned():
        if ppid0 == 1:
            return False        # 本身就是开机自启场景，不判定
        try:
            return os.getppid() == 1
        except Exception:
            return False

    try:
        app.start()
        tick = 0
        while RUNNING:
            app.step()
            tick += 1
            if tick % 30 == 0 and orphaned():
                log("父进程已退出，APP 收工（避免后台占摄像头）")
                break
    except KeyboardInterrupt:
        log("Ctrl-C")
    finally:
        app.cleanup()
    log("已退出")


if __name__ == "__main__":
    main()
