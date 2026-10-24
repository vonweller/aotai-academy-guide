# -*- coding: utf-8 -*-
"""鳌台书院 AI 非遗导览 · Flask 后端

一个进程干三件事：
  1) 静态网站：03_网页3D（Three.js 五关交互）
  2) REST/SSE：网页 <-> 后端 的实时状态（/api/state、/api/stream、/api/cmd）
  3) MQTT 桥：订阅 aotai/#（CyberCAM / K10 发来的事件），转发给网页；
     网页动作再 publish 回 aotai/cmd 或 aotai/web

启动：
  python 03_网页3D/bridge/app.py            # 默认 0.0.0.0:8000
  python 03_网页3D/bridge/app.py --port 8080 --mqtt 127.0.0.1:1883
（不装 paho-mqtt 或 broker 不通时自动降级为纯本地模式，网页照常演示）
"""
import argparse
import json
import os
import queue
import threading
import time

from flask import Flask, jsonify, request, send_from_directory, Response

try:
    import paho.mqtt.client as mqtt
    HAS_PAHO = True
except Exception:
    mqtt = None
    HAS_PAHO = False

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.dirname(HERE)          # 03_网页3D
WS_ROOT = os.path.dirname(WEB_ROOT)       # 项目根
DATA_ROOT = os.path.join(WS_ROOT, "02_数据")

app = Flask(__name__, static_folder=None)

# ---------------- 全局状态 ----------------
STATE = {
    "stage": 1,
    "lang": "zh",
    "face_ok": False,
    "visitor": "",
    "updated": 0,
    "mqtt": False,
    "device": {"cybercam": False, "k10": False},
}
BUS = queue.Queue(maxsize=512)
CAM_JPEG = {"buf": None, "ts": 0.0}
SUBSCRIBERS = []
LOCK = threading.Lock()


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def broadcast(event):
    """SSE 广播（非阻塞）。"""
    dead = []
    for q in SUBSCRIBERS:
        try:
            q.put_nowait(event)
        except Exception:
            dead.append(q)
    for q in dead:
        try:
            SUBSCRIBERS.remove(q)
        except ValueError:
            pass


def merge_state(patch):
    with LOCK:
        STATE.update(patch or {})
        STATE["updated"] = int(time.time())
        return dict(STATE)


# ---------------- MQTT ----------------
class Bridge(object):
    def __init__(self, host="159.75.137.223", port=1883, user="siot", pwd="dfrobot"):
        self.host = host
        self.port = port
        self.user = user
        self.pwd = pwd
        self.client = None
        self.connected = False

    def start(self):
        if not HAS_PAHO:
            print("[bridge] paho-mqtt 未安装 -> 纯本地模式")
            return False
        try:
            c = None
            for kwargs in ({"client_id": "pc-bridge", "clean_session": True},
                           {"client_id": "pc-bridge"}):
                try:
                    c = mqtt.Client(**kwargs)
                    break
                except Exception:
                    c = None
            if c is None:
                c = mqtt.Client()
            if self.user:
                c.username_pw_set(self.user, self.pwd)
            c.on_connect = self._on_connect
            c.on_disconnect = self._on_disconnect
            c.on_message = self._on_message
            c.reconnect_delay_set(min_delay=2, max_delay=15)
            self.client = c
            c.connect_async(self.host, self.port, 30)
            c.loop_start()
            print("[bridge] MQTT 连接中:", self.host, self.port)
            return True
        except Exception as e:
            print("[bridge] MQTT 启动失败:", e)
            return False

    def _on_connect(self, client, userdata, flags, rc, *a):
        self.connected = (rc == 0)
        print("[bridge] MQTT on_connect rc=", rc)
        if self.connected:
            for t in ("aotai/state", "aotai/event", "aotai/k10", "aotai/web", "aotai/cmd",
                      "aotai/points"):
                try:
                    client.subscribe(t, qos=0)
                except Exception:
                    pass
            merge_state({"mqtt": True})

    def _on_disconnect(self, client, userdata, rc, *a):
        self.connected = False
        merge_state({"mqtt": False})

    def _on_message(self, client, userdata, msg):
        try:
            raw = msg.payload.decode("utf-8", "ignore")
        except Exception:
            raw = ""
        try:
            data = json.loads(raw) if raw else {}
        except Exception:
            data = {"raw": raw}
        payload = {"topic": msg.topic, "data": data, "ts": int(time.time())}
        print("[bridge] <-", msg.topic, raw[:160])
        # 状态合并
        if msg.topic == "aotai/state":
            merge_state({
                "stage": int(data.get("stage", STATE["stage"])),
                "lang": data.get("lang", STATE["lang"]),
                "face_ok": bool(data.get("face_ok", STATE["face_ok"])),
                "visitor": data.get("visitor", STATE.get("visitor", "")),
            })
        elif msg.topic == "aotai/k10":
            dev = dict(STATE.get("device") or {})
            dev["k10"] = True
            dev["k10_ts"] = int(time.time())
            merge_state({"device": dev})
            if data.get("type") == "voice_cmd":
                broadcast({"topic": "k10/voice", "data": data, "ts": int(time.time())})
            elif data.get("type") == "wake":
                broadcast({"topic": "k10/wake", "data": data, "ts": int(time.time())})
        elif msg.topic == "aotai/event":
            dev = dict(STATE.get("device") or {})
            if data.get("type", "").startswith("face") or data.get("source") == "cybercam":
                dev["cybercam"] = True
                dev["cybercam_ts"] = int(time.time())
            merge_state({"device": dev})
        elif msg.topic == "aotai/points":
            # 相机自己记的积分，网页同步显示
            if data.get("who"):
                merge_state({"visitor": data["who"]})
        broadcast(payload)

    def publish(self, topic, obj):
        if not self.client or not self.connected:
            return False
        try:
            body = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
            self.client.publish(topic, body, qos=0, retain=(topic == "aotai/state"))
            return True
        except Exception as e:
            print("[bridge] publish fail", e)
            return False

    def stop(self):
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
        except Exception:
            pass


BRIDGE = None

# ---------------- 静态资源 ----------------
@app.route("/")
def index():
    return send_from_directory(WEB_ROOT, "index.html")


@app.route("/assets/<path:p>")
def assets(p):
    return send_from_directory(os.path.join(WEB_ROOT, "assets"), p)


@app.route("/audio/<path:p>")
def audio(p):
    return send_from_directory(os.path.join(DATA_ROOT, "audio"), p)


@app.route("/data/<path:p>")
def data(p):
    return send_from_directory(DATA_ROOT, p)


@app.route("/qc/<path:p>")
def qc(p):
    return send_from_directory(os.path.join(WEB_ROOT, "qc"), p)


@app.route("/fw/<path:p>")
def fw(p):
    """只读暴露固件源码目录，供同网段设备拉取部署（不含任何密钥）。"""
    return send_from_directory(os.path.join(WS_ROOT, "01_固件", "CyberCAM_AI书院"), p)


# ---------------- API ----------------
@app.route("/favicon.ico")
def favicon():
    from flask import Response
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
           '<rect width="64" height="64" rx="12" fill="#0d1214"/>'
           '<text x="32" y="45" font-size="36" text-anchor="middle" fill="#d9b45b" font-family="serif">鰲</text></svg>')
    return Response(svg, mimetype="image/svg+xml")


@app.route("/api/camera", methods=["POST"])
def api_camera_post():
    data = request.get_data(cache=False) or b""
    if len(data) < 500 or len(data) > 800000:
        return jsonify({"ok": False}), 400
    CAM_JPEG["buf"] = data
    CAM_JPEG["ts"] = time.time()
    dev = dict(STATE.get("device") or {})
    dev["cybercam"] = True
    dev["cybercam_ts"] = int(time.time())
    dev["camera"] = True
    merge_state({"device": dev})
    return jsonify({"ok": True, "n": len(data)})


@app.route("/api/camera.jpg")
def api_camera_jpg():
    buf = CAM_JPEG.get("buf")
    if not buf or time.time() - float(CAM_JPEG.get("ts") or 0) > 15:
        return Response(status=404)
    return Response(buf, mimetype="image/jpeg", headers={"Cache-Control": "no-store"})


@app.route("/api/health")
def api_health():
    dev = dict(STATE.get("device") or {})
    now = int(time.time())
    dev["k10_online"] = bool(dev.get("k10_ts") and now - dev["k10_ts"] < 60)
    dev["cybercam_online"] = bool(dev.get("cybercam_ts") and now - dev["cybercam_ts"] < 300)
    return jsonify({
        "ok": True,
        "mqtt": bool(BRIDGE and BRIDGE.connected),
        "state": STATE,
        "device": dev,
        "web_root": WEB_ROOT,
        "data_root": DATA_ROOT,
    })


@app.route("/api/state", methods=["GET", "POST"])
def api_state():
    if request.method == "POST":
        patch = request.get_json(silent=True) or {}
        st = merge_state(patch)
        if BRIDGE:
            BRIDGE.publish("aotai/state", st)
        broadcast({"topic": "web/state", "data": patch, "ts": int(time.time())})
        return jsonify(st)
    return jsonify(STATE)


@app.route("/api/cmd", methods=["POST"])
def api_cmd():
    """网页按钮 -> 后端 -> MQTT。cmd 结构见 06_文档/协议.md §4.3"""
    body = request.get_json(silent=True) or {}
    print("[bridge] web cmd", body)
    ok = False
    if BRIDGE:
        if body.get("cmd"):
            ok = BRIDGE.publish("aotai/cmd", body)
        if body.get("action"):
            ok = BRIDGE.publish("aotai/web", body) or ok
    # 本地也更新状态，网页离线时也能推进
    if body.get("cmd") == "goto_stage":
        merge_state({"stage": int(body.get("stage", STATE["stage"]))})
    elif body.get("cmd") == "set_lang":
        merge_state({"lang": body.get("lang", STATE["lang"])})
    broadcast({"topic": "web/cmd", "data": body, "ts": int(time.time())})
    return jsonify({"ok": True, "forwarded": ok, "state": STATE})


@app.route("/api/say", methods=["POST"])
def api_say():
    body = request.get_json(silent=True) or {}
    line_id = body.get("id")
    lang = body.get("lang", STATE.get("lang", "zh"))
    text = body.get("text", "")
    path = os.path.join(DATA_ROOT, "audio", lang, "%s.mp3" % line_id) if line_id else ""
    exists = bool(path and os.path.exists(path))
    if BRIDGE:
        BRIDGE.publish("aotai/cmd", {"cmd": "speak", "id": line_id, "lang": lang, "text": text})
    return jsonify({"ok": True, "file": "/audio/%s/%s.mp3" % (lang, line_id) if exists else None,
                    "text": text})


@app.route("/api/content")
def api_content():
    p = os.path.join(DATA_ROOT, "content.json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------- 积分与兑换 ----------------
POINTS_PATH = os.path.join(DATA_ROOT, "points.json")
EXPECTED_RELIC_KEYS = ("houjie_yuexiu", "houjie_shuangshou_hongquan",
                       "aotai_aoyu_brick", "guancao", "qingxi_qilin_zhazuo")
POINTS_LOCK = threading.Lock()
RELIC_REWARD_KINDS = frozenset(("relic_recognize", "relic_quiz_right"))
# No authenticated camera-to-ledger event protocol exists yet; recognition rewards stay disabled.
RELIC_REWARDS_ENABLED = False

POINT_REWARDS = {
    "face": 10, "stage_clear": 10, "quiz_right": 15,
    "relic_recognize": 8, "relic_quiz_right": 20, "finish": 50,
}
# 兑换品使用东莞本地非遗主题；下架香云纱/千角灯摆件卡片。
SHOP_ITEMS = [
    {"id": "pin_yuexiu", "name": "粤绣纹样徽章", "cost": 30, "icon": "badge"},
    {"id": "pin_guancao", "name": "莞草编织书签", "cost": 45, "icon": "bookmark"},
    {"id": "pin_qilin", "name": "麒麟扎作挂饰", "cost": 60, "icon": "lantern"},
    {"id": "pin_hongquan", "name": "洪拳纹样徽章", "cost": 90, "icon": "badge"},
    {"id": "pin_aoyu", "name": "鳌鱼砖纹样摆件", "cost": 120, "icon": "figure"},
]


def _points_load():
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


def _points_save(d):
    try:
        os.makedirs(os.path.dirname(POINTS_PATH), exist_ok=True)
        tmp = POINTS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, POINTS_PATH)
    except Exception as e:
        print("[points] save fail", e)


def relic_rewards_ready():
    if not RELIC_REWARDS_ENABLED:
        return False
    try:
        with open(os.path.join(DATA_ROOT, "content.json"), "r", encoding="utf-8") as f:
            content = json.load(f)
        fire_eyes = content.get("fireEyes") or {}
        order = fire_eyes.get("order") or []
        if tuple(order) != EXPECTED_RELIC_KEYS:
            return False
        raw_items = content.get("relics")
        if not isinstance(raw_items, list) or len(raw_items) != len(EXPECTED_RELIC_KEYS):
            return False
        if any(not isinstance(row, dict) or not isinstance(row.get("key"), str) for row in raw_items):
            return False
        items = {r.get("key"): r for r in raw_items}
        if len(items) != len(EXPECTED_RELIC_KEYS) or set(items) != set(EXPECTED_RELIC_KEYS):
            return False
        def item_ready(key):
            item = items.get(key) or {}
            recognition = item.get("recognition") or {}
            quiz = item.get("quiz") or {}
            options = quiz.get("options") or []
            option_keys = [op.get("key") for op in options if isinstance(op, dict) and isinstance(op.get("key"), str) and op.get("key")]
            question = quiz.get("q")
            refs = item.get("source_refs") or []
            rights_refs = item.get("media_rights_refs") or []
            report = (item.get("model_validation") or {}).get("independent_test_report") or {}
            deployment = (item.get("model_validation") or {}).get("deployment_report") or {}
            source_refs_ok = (isinstance(refs, list) and bool(refs) and all(
                isinstance(ref, dict) and all(isinstance(ref.get(k), str) and ref[k].strip()
                    for k in ("institution", "citation", "access_date")) for ref in refs))
            rights_refs_ok = (isinstance(rights_refs, list) and bool(rights_refs) and all(
                isinstance(ref, dict) and all(isinstance(ref.get(k), str) and ref[k].strip()
                    for k in ("rights_holder", "permission_ref")) for ref in rights_refs))
            validation = item.get("model_validation") or {}
            return (item.get("source_status") == "verified" and source_refs_ok and rights_refs_ok and
                    item.get("media_rights_status") == "authorized" and
                    recognition.get("status") == "verified" and
                    recognition.get("enabled") is True and
                    validation.get("status") == "passed" and
                    validation.get("independent_test_report") and
                    isinstance(report, dict) and all(isinstance(report.get(k), str) and report[k].strip()
                        for k in ("report_ref", "test_set_id")) and
                    validation.get("deployment_validation") == "passed" and
                    isinstance(deployment, dict) and all(isinstance(deployment.get(k), str) and deployment[k].strip()
                        for k in ("report_ref", "device_model", "firmware_version")) and
                    isinstance(question, dict) and
                    all(isinstance(question.get(lang), str) and question[lang].strip() for lang in ("zh", "yue")) and
                    isinstance(options, list) and len(options) >= 2 and
                    len(option_keys) == len(options) and len(set(option_keys)) == len(option_keys) and
                    all(all(isinstance(op.get(lang), str) and op[lang].strip() for lang in ("zh", "yue"))
                        for op in options if isinstance(op, dict)) and
                    quiz.get("answer") in option_keys)
        return (fire_eyes.get("status") == "verified" and bool(order) and
                all(item_ready(key) for key in order))
    except Exception as e:
        print("[points] relic readiness unavailable -> disabled", e)
        return False


def _points_rec(d, who):
    v = d["visitors"].setdefault(
        who, {"score": 0, "log": [], "redeemed": [], "first": int(time.time())}
    )
    v.setdefault("score", 0)
    v.setdefault("log", [])
    v.setdefault("redeemed", [])
    return v


def points_snapshot():
    d = _points_load()
    who = STATE.get("visitor") or d.get("last") or "预约访客"
    v = _points_rec(d, who)
    return {
        "who": who,
        "score": int(v.get("score", 0)),
        "shop": SHOP_ITEMS,
        "redeemed": list(v.get("redeemed", []))[-20:],
        "log": list(v.get("log", []))[-10:],
        "rewards": {**POINT_REWARDS, **{k: 0 for k in RELIC_REWARD_KINDS}},
    }


def points_add(kind, note="", who=None, event_id=None, trusted_event=False):
    # Browser POSTs cannot prove a camera classification; only a future trusted server-side event may award it.
    if not isinstance(kind, str):
        return 0
    if kind in RELIC_REWARD_KINDS and (not trusted_event or not relic_rewards_ready()):
        return None
    gain = int(POINT_REWARDS.get(kind, 0))
    if gain <= 0:
        return 0
    if kind in RELIC_REWARD_KINDS and (not isinstance(event_id, str) or
            not event_id.startswith("relic:") or len(event_id) < 14 or len(event_id) > 128):
        return None
    with POINTS_LOCK:
        d = _points_load()
        name = who or STATE.get("visitor") or d.get("last") or "预约访客"
        v = _points_rec(d, name)
        if kind in RELIC_REWARD_KINDS:
            events = v.setdefault("events", [])
            if not isinstance(events, list):
                return None
            if event_id in events:
                return int(v.get("score", 0))
            events.append(event_id)
        v["score"] = int(v.get("score", 0)) + gain
        v["log"].append({"k": kind, "n": note, "p": gain, "t": int(time.time())})
        v["log"] = v["log"][-40:]
        d["last"] = name
        _points_save(d)
        score = v["score"]
    broadcast({"topic": "aotai/points",
               "data": {"who": name, "score": score, "gain": gain, "k": kind},
               "ts": int(time.time())})
    return score


@app.route("/api/points")
def api_points():
    return jsonify(points_snapshot())


@app.route("/api/add", methods=["POST"])
def api_add_points():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"ok": False, "msg": "请求格式错误"}), 400
    kind = body.get("kind")
    if not isinstance(kind, str) or kind not in POINT_REWARDS:
        return jsonify({"ok": False, "msg": "未知积分事件"}), 400
    score = points_add(kind, body.get("note", ""), event_id=body.get("event_id"))
    if score is None:
        return jsonify({"ok": False, "msg": "火眼金睛识别奖励尚未启用"}), 409
    return jsonify({"ok": True, "score": score})


@app.route("/api/redeem", methods=["POST"])
def api_redeem():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"ok": False, "msg": "请求格式错误"}), 400
    item_id = body.get("id")
    item = next((it for it in SHOP_ITEMS if it["id"] == item_id), None)
    if not item:
        return jsonify({"ok": False, "msg": "没有这个兑换品"}), 404
    with POINTS_LOCK:
        d = _points_load()
        name = STATE.get("visitor") or d.get("last") or "预约访客"
        v = _points_rec(d, name)
        if int(v.get("score", 0)) < item["cost"]:
            lack = item["cost"] - int(v.get("score", 0))
            return jsonify({"ok": False, "msg": "还差 %d 积分，继续闯关吧" % lack})
        v["score"] = int(v.get("score", 0)) - int(item["cost"])
        v["redeemed"].append({"id": item_id, "t": int(time.time())})
        d["last"] = name
        _points_save(d)
        score = v["score"]
    return jsonify({"ok": True, "msg": "兑换成功：" + item["name"], "score": score})


@app.route("/api/stream")
def api_stream():
    """SSE：把 MQTT 事件实时推给网页。"""
    q = queue.Queue(maxsize=64)
    SUBSCRIBERS.append(q)

    def gen():
        try:
            yield "retry: 3000\n\n"
            last = time.time()
            while True:
                try:
                    ev = q.get(timeout=15)
                    yield "data: %s\n\n" % json.dumps(ev, ensure_ascii=False)
                except queue.Empty:
                    if time.time() - last > 60:
                        break
                    yield ": keep-alive\n\n"
        finally:
            try:
                SUBSCRIBERS.remove(q)
            except ValueError:
                pass

    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/ping", methods=["POST"])
def api_ping():
    body = request.get_json(silent=True) or {}
    dev = dict(STATE.get("device") or {})
    dev[body.get("device", "web")] = True
    merge_state({"device": dev})
    return jsonify({"ok": True})


def main():
    global BRIDGE
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--mqtt", default="159.75.137.223:1883")
    ap.add_argument("--mqtt-user", default="siot")
    ap.add_argument("--mqtt-pass", default="dfrobot")
    ap.add_argument("--no-mqtt", action="store_true")
    a = ap.parse_args()
    if not a.no_mqtt:
        host, _, port = a.mqtt.partition(":")
        BRIDGE = Bridge(host or "159.75.137.223", int(port or 1883), a.mqtt_user, a.mqtt_pass)
        BRIDGE.start()
    print("[bridge] 服务: http://%s:%d/  （网页根目录 %s）" % (a.host, a.port, WEB_ROOT))
    app.run(host=a.host, port=a.port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
