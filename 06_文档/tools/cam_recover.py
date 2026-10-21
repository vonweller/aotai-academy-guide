# -*- coding: utf-8 -*-
"""CyberCAM 一键恢复/部署/启动（板子重启后跑这个）

  python _cam_recover.py --deploy     # 部署最新代码（含 display.py 安全显示）
  python _cam_recover.py --start      # 启动 APP（安全模式，先停桌面）
  python _cam_recover.py --status
"""
import argparse, os, posixpath, sys, time
import paramiko

WS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
APP = os.path.join(WS, "01_固件", "CyberCAM_AI书院")
DATA = os.path.join(WS, "02_数据")
HOST = os.environ.get("AOTAI_CAM_HOST", "192.168.10.62")


def conn(host, user="pi", pwd="pi", tries=5):
    last = None
    for i in range(tries):
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(host, username=user, password=pwd, timeout=25,
                      banner_timeout=45, auth_timeout=45, allow_agent=False, look_for_keys=False)
            return c
        except Exception as e:
            last = e
            print("  connect try %d fail: %s" % (i + 1, str(e)[:100]))
            time.sleep(5)
    raise last


def run(c, cmd, timeout=120):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    return (o.read().decode("utf-8", "ignore") + e.read().decode("utf-8", "ignore")).strip()


def deploy(c):
    sftp = c.open_sftp()
    run(c, "mkdir -p /data/app/aotai /data/aotai/audio/zh /data/aotai/audio/yue /data/aotai/faces")
    n = 0
    for fn in sorted(os.listdir(APP)):
        lp = os.path.join(APP, fn)
        if os.path.isfile(lp) and fn.endswith((".py", ".sh", ".txt", ".png", ".md")):
            sftp.put(lp, "/data/app/aotai/" + fn)
            n += 1
    for fn in ("content.json", "map.json"):
        sftp.put(os.path.join(DATA, fn), "/data/aotai/" + fn)
    relic_model = os.path.join(DATA, "relics", "model.npz")
    if os.path.isfile(relic_model):
        run(c, "mkdir -p /data/aotai/relics")
        sftp.put(relic_model, "/data/aotai/relics/model.npz")
        n += 1
    for lang in ("zh", "yue"):
        for fn in sorted(os.listdir(os.path.join(DATA, "audio", lang))):
            if fn.endswith(".mp3"):
                sftp.put(os.path.join(DATA, "audio", lang, fn), "/data/aotai/audio/%s/%s" % (lang, fn))
                n += 1
    sftp.close()
    run(c, "chmod +x /data/app/aotai/run.sh; chown -R pi:pi /data/app/aotai /data/aotai")
    print("  deployed", n, "files")


def start(c, extra=""):
    run(c, "pkill -f '/data/app/aotai/main.py' || true")
    time.sleep(0.6)
    # 不在这里杀 lvglsim。占屏交给 display.py：先停桌面脚本，发现 D 状态就放弃。
    run(c, "cd /data/app/aotai && nohup python3 -u main.py %s > /tmp/aotai.log 2>&1 &" % extra)
    time.sleep(8)
    print("  ps:", run(c, "ps aux | grep '[m]ain.py' | head -2"))
    print("  log:", run(c, "tail -25 /tmp/aotai.log")[:1500])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--deploy", action="store_true")
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--no-display", action="store_true", help="启动时不占屏（远程调试）")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()

    c = conn(a.host)
    try:
        print("[board]", run(c, "hostname; uname -r; uptime | head -1"))
        if a.status or not (a.deploy or a.start):
            print("  ps:", run(c, "ps aux | grep -E '[m]ain.py|[l]vglsim' | head -4"))
            print("  ip:", run(c, "ip -4 addr show wlan0 | grep inet"))
            print("  log:", run(c, "tail -15 /tmp/aotai.log 2>/dev/null")[:800])
        if a.deploy:
            print("[deploy]")
            deploy(c)
        if a.start:
            print("[start]")
            start(c, "--no-display" if a.no_display else "")
    finally:
        c.close()


if __name__ == "__main__":
    main()
