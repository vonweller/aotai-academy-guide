# -*- coding: utf-8 -*-
"""模拟真实摄像头输入：加噪声、抖动、缩放，看识别还剩多少。"""
import glob, os, sys
import numpy as np
import cv2
APP = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, APP)
import relic
eng = relic.RelicEngine()
ROOT = os.path.abspath(os.path.join(APP, '..', '..', '02_数据', 'relics', 'images'))

def degrade(im, rng):
    h, w = im.shape[:2]
    # 模拟手持：轻微旋转 + 缩放 + 明暗 + 噪声 + 模糊
    ang = rng.uniform(-6, 6)
    sc = rng.uniform(0.78, 1.0)
    M = cv2.getRotationMatrix2D((w/2, h/2), ang, sc)
    out = cv2.warpAffine(im, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    out = np.clip(out.astype(np.float32) * rng.uniform(0.72, 1.25) + rng.uniform(-18, 18), 0, 255).astype(np.uint8)
    out = cv2.GaussianBlur(out, (3, 3), 0)
    noise = rng.normal(0, 9, out.shape).astype(np.float32)
    return np.clip(out.astype(np.float32) + noise, 0, 255).astype(np.uint8)

rng = np.random.RandomState(3)
for cls in ('xiangyunsha', 'guancao', 'qianjiaodeng'):
    files = sorted(glob.glob(os.path.join(ROOT, cls, '*.jpg')))
    for f in files[:3]:
        im = cv2.imdecode(np.fromfile(f, dtype=np.uint8), cv2.IMREAD_COLOR)
        if im is None:
            continue
        okc = 0
        bests = []
        for k in range(6):
            d = degrade(im, rng)
            cid, score, ratios = eng.predict(d)
            bests.append(round(score, 2))
            okc += 1 if cid == cls else 0
        print('%-16s %-18s hit %d/6  scores %s' % (cls, os.path.basename(f), okc, bests))