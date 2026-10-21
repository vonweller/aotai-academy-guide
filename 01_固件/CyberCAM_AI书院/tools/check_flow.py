# -*- coding: utf-8 -*-
import os, sys, time
APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
import content_loader, relic
c = content_loader.Content()
print('--- 古物配置检查 ---')
for rel in c.relics():
    rid = rel.get('id')
    q = rel.get('quiz') or {}
    print(rel.get('key'), 'id=', rid, '音频=', (rel.get('zh') or '')[:8],
          '有题=', bool(q), '答案=', q.get('answer'))
print()
print('--- 每件古物的题目与音频是否存在 ---')
import os as _os
AUD = _os.path.join(APP, '..', '..', '02_数据', 'audio')
for rel in c.relics():
    rid = rel.get('id')
    for suffix in ('', '_q', '_ok', '_no'):
        ok = []
        for lang in ('zh', 'yue'):
            p = _os.path.join(AUD, lang, rid + suffix + '.mp3')
            ok.append(_os.path.exists(p))
        if not all(ok):
            print('  缺音频', rid + suffix, ok)
print('音频检查完成')
print()
print('--- 识别引擎 ---')
eng = relic.RelicEngine()
print('模型原型', len(eng.labels), '阈值', eng.threshold, 'margin', eng.margin)
print('CONFIRM_HITS', eng.CONFIRM_HITS, 'HIT_WINDOW', eng.HIT_WINDOW)