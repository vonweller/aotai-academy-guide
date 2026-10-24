# -*- coding: utf-8 -*-
import os, sys
APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
import ui, content_loader
c = content_loader.Content()
rel = c.relics()[0]
quiz = rel.get('quiz')
u = ui.UI()
cases = []
# 火眼金睛各阶段
for phase in ('recognize', 'explain', 'answer', 'again', 'done'):
    q = quiz if phase == 'answer' else None
    cases.append(('relic-' + phase, lambda ph=phase, qq=q: u.screen_relic(
        None, '厚街粤绣（候选）', '来源与授权待核', 'none', 'zh', True,
        phase=ph, quiz=qq, quiz_state={}, score=20)))
# 答案已选状态
cases.append(('relic-answered', lambda: u.screen_relic(
    None, '候选清单（未启用）', '来源与授权待核', 'none', 'yue', True,
    phase='answer', quiz=quiz, quiz_state={'answered': True, 'picked': 'A', 'answer': 'B'}, score=5)))
# 人脸各状态
for lv in ('none', 'detected', 'recognized', 'unknown', 'nocam'):
    cases.append(('face-' + lv, lambda l=lv: u.screen_face(
        None, l, '预约访客' if l == 'recognized' else None, 'zh', 1, True,
        dets=[], face_ok=(l == 'recognized'), learning=False, cam_err='')))
# 关卡页（带题）
st = c.stage(2)
lines = [ln.get('zh') for ln in st.get('lines', [])]
# History quiz is deliberately unavailable until its source has been verified.
qv = None
cases.append(('stage-zh', lambda: u.screen_stage(2, '第二关', lines, qv, {}, 'zh', True)))
cases.append(('stage-yue', lambda: u.screen_stage(4, '第四关', lines, qv, {}, 'yue', False)))
cases.append(('lang', lambda: u.screen_language()))
cases.append(('mode', lambda: u.screen_mode('yue')))
cases.append(('calib', lambda: u.screen_calib(2, [(120,210),(520,210),(200,400),(440,390)], '提示')))
cases.append(('end', lambda: u.screen_end('zh', True)))
bad = []
for name, fn in cases:
    try:
        im = fn()
        assert im.shape == (480, 640, 3), im.shape
        print('OK', name)
    except Exception as e:
        bad.append((name, repr(e)))
        print('FAIL', name, repr(e)[:120])
print('FAILED' if bad else 'ALL_UI_OK', len(bad))