# -*- coding: utf-8 -*-
"""安全显示层

CyberCAM 的屏幕由桌面进程 lvglsim 占用。直接 Display.init() 会和桌面抢屏，
极端情况下会把整个系统拖进 D 状态（IO 卡死）。本模块：

1) 启动时先探测桌面是否在跑；
2) 在跑 -> 尝试温和地停掉桌面（走官方 desktop 脚本反向操作），失败就**只走 IDE/窗口**；
3) 所有 Display 调用包 try/except + 超时，绝不因屏幕问题卡死主循环；
4) 提供 --no-display 纯逻辑模式（PC/无屏调试）。
"""
import os
import subprocess
import time

try:
    from . import config
except Exception:
    import config

_LCD = None
_IDE = None
_ready = False
_failed = False
_last_err = ""
_fb_fd = None
_fb_mode = False
_fb_w, _fb_h, _fb_stride = 480, 640, 1440
_fb_err = False


def log(*a):
    print("[display]", *a)


def _sh(cmd, timeout=6):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        # 超时的子进程必须收掉，否则留僵尸，堆多了会拖慢甚至卡住
        try:
            subprocess.run("pkill -9 -f 'pgrep|ps -o' >/dev/null 2>&1", shell=True, timeout=3)
        except Exception:
            pass
        return None
    except Exception:
        return None


def desktop_running():
    r = _sh("pgrep -x lvglsim")
    if r is None:
        return False
    return bool(r.stdout.strip())


def _lvgl_stat():
    r = _sh("ps -o stat= -C lvglsim")
    if r is None or not r.stdout:
        return ""
    return r.stdout.decode("utf-8", "ignore").strip().split("\n")[0].strip()


def lvgl_stuck():
    """D 状态 = 卡在内核 canaan_gdma_rotate_sync，杀不掉，再抢屏会把整机拖死。"""
    st = _lvgl_stat()
    return bool(st) and ("D" in st.split()[0] if st.split() else False)


def stop_desktop():
    """先停掉会拉起 lvglsim 的桌面脚本，再停 lvglsim。已经卡死则什么都不碰。"""
    if lvgl_stuck():
        log("lvglsim 卡在 GDMA 旋转（D 状态）。请把 USB 断电 10 秒再上电，不要反复杀进程。")
        return False
    log("停止桌面脚本，避免 lvglsim 被立刻拉起…")
    _sh("echo root | sudo -S pkill -f /usr/lib/walnutpi/cybercam/cybercam-desktop.sh")
    time.sleep(0.4)
    if lvgl_stuck():
        log("桌面进入 D 状态，放弃占屏")
        return False
    _sh("echo root | sudo -S kill $(pgrep -x lvglsim) 2>/dev/null")
    for _ in range(16):
        if lvgl_stuck():
            log("lvglsim 停不下来（D 状态）。请断电重启。")
            return False
        if not desktop_running():
            log("桌面已停止")
            return True
        time.sleep(0.25)
    if desktop_running() and not lvgl_stuck():
        _sh("echo root | sudo -S kill -9 $(pgrep -x lvglsim) 2>/dev/null")
        time.sleep(0.4)
    if lvgl_stuck():
        log("强停后仍是 D 状态。请断电重启。")
        return False
    ok = not desktop_running()
    log("桌面已停止" if ok else "桌面仍在运行")
    return ok


def start_desktop():
    _sh("echo root | sudo -S desktop 2>/dev/null", timeout=10)


def open_fb():
    """桌面卡在 vblank 时，直接写 /dev/fb0。这时原子提交会永远等不到垂直同步。"""
    global _fb_fd, _fb_mode, _fb_w, _fb_h, _fb_stride
    try:
        virt = open("/sys/class/graphics/fb0/virtual_size").read().strip().split(",")
        _fb_w, _fb_h = int(virt[0]), int(virt[1])
        _fb_stride = int(open("/sys/class/graphics/fb0/stride").read().strip())
        _fb_fd = os.open("/dev/fb0", os.O_RDWR)
        _fb_mode = True
        log("改用 /dev/fb0 直接刷屏 %dx%d stride %d" % (_fb_w, _fb_h, _fb_stride))
        return True
    except Exception as e:
        log("无法打开 /dev/fb0", e)
        return False


def _fb_blit(img):
    """把 640x480 界面转 90 度写进 480x640 显存。

    旋转用 numpy 转置，比 cv2.rotate 省一次拷贝；整帧一次 write，别逐行写。
    """
    import numpy as np
    frame = img
    if frame.shape[0] != _fb_w or frame.shape[1] != _fb_h:
        # 顺时针 90 度：把 (h,w,3) 转成 (w,h,3)
        frame = np.ascontiguousarray(frame.transpose(1, 0, 2)[:, ::-1])
    if frame.shape[0] != _fb_h or frame.shape[1] != _fb_w:
        import cv2
        frame = cv2.resize(frame, (_fb_w, _fb_h))
    if not frame.flags["C_CONTIGUOUS"]:
        frame = np.ascontiguousarray(frame)
    row = _fb_w * frame.shape[2]
    if _fb_stride == row:
        os.lseek(_fb_fd, 0, os.SEEK_SET)
        os.write(_fb_fd, frame.tobytes())
        return
    blank = bytes(_fb_stride - row)
    buf = bytearray()
    for y in range(frame.shape[0]):
        buf += frame[y].tobytes()
        buf += blank
    os.lseek(_fb_fd, 0, os.SEEK_SET)
    os.write(_fb_fd, bytes(buf))


def init(use_display=True, timeout=12.0):
    """初始化屏幕。返回 True 表示可以用 Display.show()。"""
    global _LCD, _IDE, _ready, _failed

    # IDE 通道一直可用（不影响屏幕）
    try:
        from walnutpi import IDE
        _IDE = IDE
    except Exception as e:
        log("IDE 不可用:", e)

    if not use_display:
        log("--no-display：跳过屏幕")
        _failed = True
        return False

    if desktop_running() or lvgl_stuck():
        if not stop_desktop():
            log("桌面卡死，不调用 Display.init()（那会一起堵在 vblank）")
            if open_fb():
                _ready = True
                return True
            _failed = True
            return False

    try:
        from walnutpi import Display, direction
    except Exception as e:
        log("walnutpi 不可用:", e)
        _failed = True
        return False

    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            Display.init()
            try:
                if direction.get_lcd() == 2:
                    Display.set_rotation(2)
            except Exception:
                pass
            _LCD = Display
            _ready = True
            log("屏幕就绪（%.1fs）" % (time.time() - t0))
            return True
        except Exception as e:
            _last_err = str(e)
            time.sleep(0.5)
    log("屏幕初始化超时:", _last_err)
    _failed = True
    return False


def show(img):
    """推一帧；任何异常只记一次，不打断主循环。"""
    global _failed
    if _failed:
        return False
    ok = False
    if _fb_mode and _fb_fd is not None:
        global _fb_err
        try:
            _fb_blit(img)
            ok = True
        except Exception as e:
            if not _fb_err:
                _fb_err = True
                log("fb 刷屏失败:", e)
    if _ready and _LCD is not None:
        try:
            _LCD.show(img)
            ok = True
        except Exception as e:
            _failed = True
            log("Display.show 失败，后续只走 IDE:", e)
    if _IDE is not None:
        try:
            _IDE.show(img)
        except Exception:
            pass
    return ok


def cleanup():
    global _ready, _fb_fd, _fb_mode
    _ready = False
    if _fb_fd is not None:
        try:
            os.close(_fb_fd)
        except Exception:
            pass
        _fb_fd = None
        _fb_mode = False
