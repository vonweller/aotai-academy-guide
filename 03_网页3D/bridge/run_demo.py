# -*- coding: utf-8 -*-
"""一键演示：同时起 MQTT broker + Flask 网页后端，并打印可访问地址

  python 03_网页3D/bridge/run_demo.py
  python 03_网页3D/bridge/run_demo.py --port 8000 --mqtt-port 1883
"""
import argparse
import os
import socket
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--mqtt-port", type=int, default=1883)
    ap.add_argument("--mqtt-host", default="159.75.137.223")
    ap.add_argument("--local-broker", action="store_true",
                    help="本地起一个 broker（默认连现场公共 MQTT）")
    a = ap.parse_args()

    if a.local_broker:
        import broker
        b = broker.Broker("0.0.0.0", a.mqtt_port)
        t = threading.Thread(target=b.serve, daemon=True)
        t.start()
        time.sleep(0.6)
        print("[demo] MQTT broker 已启动 tcp://0.0.0.0:%d" % a.mqtt_port)

    ip = lan_ip()
    print("=" * 66)
    print("  鳌台书院 AI 非遗导览")
    print("  网页   : http://127.0.0.1:%d/" % a.port)
    print("  局域网 : http://%s:%d/   （投影/平板用这个）" % (ip, a.port))
    print("  MQTT   : %s:%d   （%s）" % (a.mqtt_host, a.mqtt_port,
          "本地 broker" if a.local_broker else "现场公共 broker"))
    print("=" * 66)

    import app as flask_app
    flask_app.BRIDGE = flask_app.Bridge(
        "127.0.0.1" if a.local_broker else a.mqtt_host, a.mqtt_port, "siot", "dfrobot")
    flask_app.BRIDGE.start()
    time.sleep(1.2)
    print("[demo] MQTT 已连接:", flask_app.BRIDGE.connected)
    flask_app.app.run(host="0.0.0.0", port=a.port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
