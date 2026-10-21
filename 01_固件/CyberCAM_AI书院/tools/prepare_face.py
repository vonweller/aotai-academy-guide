# -*- coding: utf-8 -*-
"""PC 端准备工具（在电脑上跑，产物拷到 CyberCAM）

1) 合成一张"预约访客"卡通人脸（打印出来给摄像头认）
2) 用 cv2.face.LBPH 生成 lbph_train.yml（若 cv2.face 不可用则跳过，板端会自动重训）
3) 生成 labels.json

用法：
  python tools/prepare_face.py --out ..\..\02_数据\data_pack
"""
import argparse
import json
import os

import cv2
import numpy as np


def imwrite_u(path, img):
    ext = os.path.splitext(path)[1] or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        return False
    buf.tofile(path)
    return True


def imread_u(path, flags=cv2.IMREAD_COLOR):
    buf = np.fromfile(path, dtype=np.uint8)
    if buf.size == 0:
        return None
    return cv2.imdecode(buf, flags)


def make_synthetic_face(path, seed=7, size=(240, 240)):
    img = np.full((size[1], size[0], 3), 236, np.uint8)
    cx, cy = size[0] // 2, size[1] // 2
    cv2.ellipse(img, (cx, cy + 12), (86, 110), 0, 0, 360, (185, 205, 225), -1)   # 脸
    cv2.ellipse(img, (cx, cy - 74), (92, 50), 0, 180, 360, (58, 52, 46), -1)      # 头发
    for sx in (-36, 36):
        cv2.ellipse(img, (cx + sx, cy - 20), (18, 10), 0, 0, 360, (250, 250, 250), -1)
        cv2.circle(img, (cx + sx, cy - 20), 6, (40, 40, 40), -1)
        cv2.ellipse(img, (cx + sx, cy - 42), (20, 5), 0, 0, 360, (40, 40, 40), 2)
    cv2.line(img, (cx, cy - 2), (cx, cy + 26), (150, 165, 185), 3)                # 鼻
    cv2.ellipse(img, (cx, cy + 52), (32, 14), 0, 0, 180, (120, 90, 90), 3)       # 嘴
    cv2.rectangle(img, (cx - 110, cy + 104), (cx + 110, size[1]), (70, 90, 130), -1)
    cv2.putText(img, "AOTAI", (cx - 46, size[1] - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (245, 245, 245), 2)
    imwrite_u(path, img)
    return path


def build_lbph(faces_dir, out_model):
    try:
        rec = cv2.face.LBPHFaceRecognizer_create(
            radius=1, neighbors=8, grid_x=8, grid_y=8, threshold=78.0)
    except Exception as e:
        print("cv2.face 不可用（板端会自己训练）:", e)
        return False
    imgs, ids = [], []
    for fn in sorted(os.listdir(faces_dir)):
        if not fn.lower().endswith((".jpg", ".png")):
            continue
        try:
            idx = int(fn.split("_")[0])
        except Exception:
            continue
        im = imread_u(os.path.join(faces_dir, fn), cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        imgs.append(cv2.resize(im, (96, 96)))
        ids.append(idx)
    if not imgs:
        return False
    rec.train(imgs, np.array(ids))
    # cv2 FileStorage 不支持中文路径：先写临时 ASCII 路径再搬过去
    import tempfile
    import shutil
    tmp = os.path.join(tempfile.gettempdir(), "lbph_tmp_%d.yml" % os.getpid())
    try:
        rec.write(tmp)
        shutil.copyfile(tmp, out_model)
        os.remove(tmp)
        return True
    except Exception as e:
        print("模型写出失败（不影响板端，板端会自训）:", e)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data_pack")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    faces = os.path.join(out, "faces")
    os.makedirs(faces, exist_ok=True)

    # 1) labels
    labels = {"1": "预约访客"}
    with open(os.path.join(faces, "labels.json"), "w", encoding="utf-8") as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)

    # 2) 合成多张角度略有差异的样张，提高现场鲁棒性
    made = []
    for i, seed in enumerate((7, 11, 23)):
        p = os.path.join(faces, "1_%02d.jpg" % (i + 1))
        made.append(make_synthetic_face(p, seed=seed))
    # 3) 训练
    ok = build_lbph(faces, os.path.join(faces, "lbph_train.yml"))
    print("样张:", len(made), "张；LBPH 训练:", ok)
    print("打印用图:", made[0])


if __name__ == "__main__":
    main()
