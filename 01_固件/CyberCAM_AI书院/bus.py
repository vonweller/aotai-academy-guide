# -*- coding: utf-8 -*-
"""MQTT 总线：断网/无 broker 时自动降级为离线模式，界面不报错。"""
import json
import threading
import time

try:
    from . import config
except Exception:
    import config

try:
    import paho.mqtt.client as mqtt
    HAS_PAHO = True
except Exception:
    mqtt = None
    HAS_PAHO = False


class Bus(object):
    def __init__(self, on_cmd=None, on_msg=None):
        self.client = None
        self.connected = False
        self.on_cmd = on_cmd          # 收到 aotai/cmd 回调
        self.on_msg = on_msg          # 任意消息回调 (topic, payload)
        self._t0 = time.time()
        self._last_try = 0
        self._lock = threading.Lock()

    # ---------- 连接 ----------
    def start(self):
        if not HAS_PAHO:
            print("[mqtt] paho-mqtt 未安装，离线模式")
            return False
        c = None
        for kwargs in ({"client_id": config.CLIENT_ID, "clean_session": True},
                       {"client_id": config.CLIENT_ID},
                       {"client_id": config.CLIENT_ID, "protocol": getattr(mqtt, "MQTTv311", 4)}):
            try:
                c = mqtt.Client(**kwargs)
                break
            except Exception:
                c = None
        if c is None:
            try:
                c = mqtt.Client()
            except Exception as e:
                print("[mqtt] 创建客户端失败:", e)
                return False
        if config.MQTT_USER:
            c.username_pw_set(config.MQTT_USER, config.MQTT_PASS)
        c.on_connect = self._on_connect
        c.on_disconnect = self._on_disconnect
        c.on_message = self._on_message
        c.reconnect_delay_set(min_delay=2, max_delay=10)
        self.client = c
        self._try_connect()
        try:
            c.loop_start()
        except Exception as e:
            print("[mqtt] loop_start fail", e)
        return self.connected

    def _try_connect(self):
        if self.client is None:
            return
        try:
            self.client.connect_async(config.MQTT_HOST, config.MQTT_PORT, 30)
            print("[mqtt] connect_async ->", config.MQTT_HOST, config.MQTT_PORT)
        except Exception as e:
            print("[mqtt] connect fail", e)

    def _on_connect(self, client, userdata, flags, rc, *args):
        self.connected = int(rc) == 0 if isinstance(rc, int) else True
        print("[mqtt] on_connect rc=", rc)
        if self.connected:
            for t in (config.TOPIC_CMD, config.TOPIC_STATE, config.TOPIC_K10, config.TOPIC_WEB):
                try:
                    client.subscribe(t, qos=0)
                except Exception as e:
                    print("[mqtt] sub fail", t, e)

    def _on_disconnect(self, client, userdata, rc, *args):
        self.connected = False
        print("[mqtt] disconnect rc=", rc)

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8", "ignore")
        except Exception:
            payload = ""
        topic = msg.topic
        if self.on_msg:
            try:
                self.on_msg(topic, payload)
            except Exception as e:
                print("[mqtt] on_msg err", e)
        if topic == config.TOPIC_CMD and self.on_cmd:
            try:
                data = json.loads(payload) if payload else {}
            except Exception:
                data = {}
            try:
                self.on_cmd(data)
            except Exception as e:
                print("[mqtt] on_cmd err", e)

    # ---------- 发送 ----------
    def publish(self, topic, obj, retain=False):
        if self.client is None:
            return False
        try:
            payload = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
            self.client.publish(topic, payload, qos=0, retain=retain)
            return True
        except Exception as e:
            print("[mqtt] publish err", e)
            return False

    def event(self, etype, **kw):
        d = {"type": etype, "ts": int(time.time())}
        d.update(kw)
        return self.publish(config.TOPIC_EVENT, d)

    def state(self, stage, lang, **kw):
        d = {"stage": stage, "lang": lang}
        d.update(kw)
        return self.publish(config.TOPIC_STATE, d, retain=True)

    def stop(self):
        try:
            if self.client is not None:
                self.client.loop_stop()
                self.client.disconnect()
        except Exception:
            pass
