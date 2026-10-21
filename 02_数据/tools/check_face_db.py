# -*- coding: utf-8 -*-
"""留一验证：每次留一张做测试，看 LBPH 能不能认回来，并挑阈值。"""
import glob
import os

import cv2
import numpy as np

DB = os.path.join('02_数据', 'data_pack', 'faces')


def load():
    items = []
    for fn in sorted(glob.glob(os.path.join(DB, '*.jpg'))):
        if os.path.basename(fn).startswith('print_'):
            continue
        idx = int(os.path.basename(fn).split('_')[0])
        img = cv2.imdecode(np.fromfile(fn, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        items.append((fn, idx, cv2.resize(img, (96, 96))))
    return items


def main():
    items = load()
    print('样本', len(items))
    dists = []
    for i, (fn, idx, img) in enumerate(items):
        train = [it2 for j, it2 in enumerate(items) if j != i]
        rec = cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)
        rec.train([t[2] for t in train], np.array([t[1] for t in train]))
        pred, dist = rec.predict(img)
        dists.append(dist)
        print('%-12s pred=%d dist=%.1f %s' % (os.path.basename(fn), pred, dist,
                                              'OK' if pred == idx else 'MISS'))
    print('距离 min/mean/max: %.1f / %.1f / %.1f' % (min(dists), sum(dists) / len(dists), max(dists)))
    # 和外人的距离做对照：用另一张脸当陌生人
    others = []
    for cand in ('02_数据/relics/images/other/00.jpg',):
        if os.path.exists(cand):
            im = cv2.imdecode(np.fromfile(cand, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if im is not None:
                others.append(cv2.resize(im, (96, 96)))
    rec = cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)
    rec.train([t[2] for t in items], np.array([t[1] for t in items]))
    for im in others:
        pred, dist = rec.predict(im)
        print('外人 pred=%d dist=%.1f' % (pred, dist))


if __name__ == '__main__':
    main()