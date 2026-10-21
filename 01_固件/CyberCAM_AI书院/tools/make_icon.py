# -*- coding: utf-8 -*-
"""生成 CyberCAM APP 图标 icon.png / icon_100.png"""
import argparse
import os
import cv2
import numpy as np



def imwrite_u(path, img):
    """支持中文路径的 OpenCV 写图（Windows 下 cv2.imwrite 对非 ASCII 路径会失败）。"""
    try:
        import numpy as _np
        ext = os.path.splitext(path)[1] or ".png"
        ok, buf = cv2.imencode(ext, img)
        if not ok:
            return False
        buf.tofile(path)
        return True
    except Exception:
        try:
            return bool(cv2.imwrite(path, img))
        except Exception:
            return False


def imread_u(path, flags=1):
    try:
        import numpy as _np
        buf = _np.fromfile(path, dtype=_np.uint8)
        if buf.size == 0:
            return None
        return cv2.imdecode(buf, flags)
    except Exception:
        return None

DESIGN = "鳌台书院"  # 鳌台书院


def draw_icon(size=512):
    img = np.zeros((size, size, 3), np.uint8)
    # 渐变背景（墨绿->黛青）
    for y in range(size):
        t = y / float(size - 1)
        c = (int(38 + 20 * t), int(52 + 26 * t), int(60 + 30 * t))
        img[y, :] = c
    # 圆角遮罩
    mask = np.zeros((size, size), np.uint8)
    r = int(size * 0.18)
    cv2.rectangle(mask, (r, 0), (size - r, size), 255, -1)
    cv2.rectangle(mask, (0, r), (size, size - r), 255, -1)
    for cx, cy in [(r, r), (size - r, r), (r, size - r), (size - r, size - r)]:
        cv2.circle(mask, (cx, cy), r, 255, -1)
    img = cv2.bitwise_and(img, img, mask=mask)
    # 屋顶（黛瓦）
    pts = np.array([[int(size*0.14), int(size*0.42)], [int(size*0.86), int(size*0.42)],
                    [int(size*0.74), int(size*0.60)], [int(size*0.26), int(size*0.60)]], np.int32)
    cv2.fillPoly(img, [pts], (70, 74, 78))
    cv2.polylines(img, [pts], True, (150, 160, 170), 4)
    # 檐线（金）
    cv2.line(img, (int(size*0.12), int(size*0.42)), (int(size*0.88), int(size*0.42)), (90, 180, 230), 6)
    # 墙体
    cv2.rectangle(img, (int(size*0.24), int(size*0.60)), (int(size*0.76), int(size*0.80)), (222, 216, 200), -1)
    # 门（木色）
    cv2.rectangle(img, (int(size*0.42), int(size*0.64)), (int(size*0.58), int(size*0.80)), (55, 62, 92), -1)
    # 匾额
    cv2.rectangle(img, (int(size*0.38), int(size*0.45)), (int(size*0.62), int(size*0.55)), (48, 60, 120), -1)
    cv2.putText(img, DESIGN, (int(size*0.395), int(size*0.53)), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (110, 200, 240), 2, cv2.LINE_AA)
    # 石阶
    for i, w in enumerate([0.30, 0.36, 0.42]):
        y0 = int(size * (0.80 + i * 0.045))
        cv2.rectangle(img, (int(size * (0.5 - w)), y0),
                      (int(size * (0.5 + w)), y0 + int(size * 0.04)), (120, 126, 130), -1)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".")
    a = ap.parse_args()
    big = draw_icon(512)
    p1 = os.path.join(a.out, "icon.png")
    p2 = os.path.join(a.out, "icon_100.png")
    imwrite_u(p1, big)
    imwrite_u(p2, cv2.resize(big, (100, 100), interpolation=cv2.INTER_AREA))
    print("written", p1, p2)


if __name__ == "__main__":
    main()
