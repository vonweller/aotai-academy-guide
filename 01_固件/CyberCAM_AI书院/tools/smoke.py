# -*- coding: utf-8 -*-
import os, sys
APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
print('APP', os.path.basename(APP))
import content_loader, points, relic, ui, face, camera
c = content_loader.Content()
print('stages', len(c.stages), 'relics', [r['key'] for r in c.relics()])
print('q1wrong', bool((c.quiz(2) or {}).get('explain_wrong')))
print('line q1_wrong', (c.line('q1_wrong') or {}).get('zh','')[:16])
u = ui.UI()
checks = [
  ('calib', u.screen_calib(0, [(120,210),(520,210),(200,400),(440,390)], '')),
  ('lang', u.screen_language()),
  ('mode', u.screen_mode('zh')),
  ('face', u.screen_face(None, 'none', None, 'zh', 1, True, learning=True, cam_err='busy')),
  ('relic', u.screen_relic(None, '香云纱', '历史', 'hit', 'zh', True, phase='answer',
      quiz={'q':'题','options':[{'key':'A','text':'甲'},{'key':'B','text':'乙'},{'key':'C','text':'丙'}],'answer':'B'},
      quiz_state={}, score=15)),
  ('stage', u.screen_stage(2, '第二关', ['讲解一','讲解二'], {'q':'题','options':[{'key':'A','text':'甲'}],'answer':'A'}, {}, 'zh', True)),
  ('end', u.screen_end('zh', True)),
]
for n, im in checks:
    assert im.shape == (480, 640, 3), (n, im.shape)
    print(n, 'ok')
p = points.Points('测试同学')
a1 = p.add('quiz_right','t',uniq='u1')
a2 = p.add('quiz_right','t',uniq='u1')
print('add', a1[1], 'dup', a2[1])
cam = camera.Camera()
print('cam open', cam.is_open, 'read', cam.read())
print('SMOKE_OK')