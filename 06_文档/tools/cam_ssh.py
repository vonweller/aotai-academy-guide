# -*- coding: utf-8 -*-
"""CyberCAM 串口执行器（COM20 @115200）

登录：WalnutPi login: 输入 pi  ->  Password: 输入 pi（输入不回显）

用法：
  python _cam_ssh.py "uname -a"
  python _cam_ssh.py --debug "ls /data/app"
"""
import argparse
import re
import sys
import time

import serial


ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07")


def clean(s):
    return ANSI.sub("", s).replace("\r", "")


class Cam(object):
    def __init__(self, port="COM20", baud=115200):
        self.ser = serial.Serial(port, baud, timeout=0.25)
        time.sleep(0.5)
        self.ser.reset_input_buffer()

    def _read(self, t):
        end = time.time() + t
        out = ""
        while time.time() < end:
            ch = self.ser.read(4096)
            if ch:
                out += ch.decode("utf-8", "ignore")
            else:
                time.sleep(0.03)
        return clean(out)

    def wait_for(self, pattern, timeout=10):
        out = ""
        end = time.time() + timeout
        while time.time() < end:
            ch = self.ser.read(4096)
            if ch:
                out += ch.decode("utf-8", "ignore")
                if re.search(pattern, clean(out), re.I):
                    return True, clean(out)
            else:
                time.sleep(0.03)
        return False, clean(out)

    def send(self, line, wait=0.35):
        self.ser.write((line + "\n").encode())
        self.ser.flush()
        time.sleep(wait)

    def ensure_login(self, user="pi", pwd="pi", debug=False):
        self.send("", 0.4)
        for _ in range(3):
            ok, out = self.wait_for(r"login:", timeout=6)
            if debug:
                print("[dbg] prompt:", repr(out[-120:]))
            if not ok:
                self.send("", 0.5)
                continue
            self.send(user, 0.8)
            ok2, out2 = self.wait_for(r"[Pp]assword[:：]|密码[:：]", timeout=6)
            if debug:
                print("[dbg] pwd prompt:", repr(out2[-120:]), ok2)
            if ok2:
                self.ser.write((pwd + "\n").encode())
                self.ser.flush()
                ok3, out3 = self.wait_for(r"pi@[\w.-]+:[^\n]*\$\s*$|root@[\w.-]+:[^\n]*#\s*$|\$\s*$", timeout=10)
                if debug:
                    print("[dbg] after pwd:", repr(out3[-160:]), ok3)
                if ok3 or "Login incorrect" not in out3:
                    return True
            else:
                return True
        return False

    def run(self, cmd, timeout=60):
        self.send(cmd, 0.2)
        # 命令结果以提示符结尾
        out = ""
        end = time.time() + timeout
        while time.time() < end:
            ch = self.ser.read(4096)
            if ch:
                out += ch.decode("utf-8", "ignore")
                c = clean(out)
                if re.search(r"\$\s*$", c) and len(c.strip()) > 0:
                    break
            else:
                time.sleep(0.04)
        c = clean(out)
        # 去掉回显的第一行（命令本身）
        lines = c.split("\n")
        if lines and cmd.strip() in lines[0]:
            lines = lines[1:]
        return "\n".join(lines)

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmds", nargs="*")
    ap.add_argument("--port", default="COM20")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    cam = Cam(a.port)
    try:
        ok = cam.ensure_login(debug=a.debug)
        if not ok:
            print("[login] FAILED")
            return 1
        for c in a.cmds:
            print("$ " + c)
            print(cam.run(c))
        return 0
    finally:
        cam.close()


if __name__ == "__main__":
    sys.exit(main())
