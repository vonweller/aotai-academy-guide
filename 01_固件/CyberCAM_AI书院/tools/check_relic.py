# -*- coding: utf-8 -*-
"""用训练图本身做一次回测：走 gate + 阈值，看能不能认出。"""
import glob, os, sys
import numpy as np
import cv2
APP = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, APP)
import relic

eng = relic.RelicEngine()
print('threshold', eng.threshold, 'margin', eng.margin)
print('names', eng.names)
print('labels count', len(eng.labels))

ROOT = os.path.abspath(os.path.join(APP, '..', '..', '02_数据', 'relics', 'images'))
for cls in ('xiangyunsha', 'guancao', 'qianjiaodeng', 'other'):
    d = os.path.join(ROOT, cls)
    if not os.path.isdir(d):
        continue
    print('==', cls)
    for f in sorted(glob.glob(os.path.join(d, '*.jpg'))):
        im = cv2.imdecode(np.fromfile(f, dtype=np.uint8), cv2.IMREAD_COLOR)
        if im is None:
            continue
        vec, ratios = relic.embed(im)
        cid, score, _ = eng.predict(im)
        # 手工看各分数
        sims = eng.prototypes.dot(vec)
        per = {}
        for i, nm in enumerate(eng.names):
            sel = sims[eng.labels == i]
            per[nm] = float(np.sort(sel)[-3:].mean()) if sel.size else -1
        ranked = sorted(per.items(), key=lambda kv: kv[1], reverse=True)
        print('  %-22s -> %-13s s=%.3f m=%.3f gate=%s | top:%s' % (
            os.path.basename(f), cid or 'NONE', ranked[0][1],
            ranked[0][1]-ranked[1][1], relic.gate(ranked[0][0], ratios),
            ','.join('%s:%.2f' % (k, v) for k, v in ranked[:3])))