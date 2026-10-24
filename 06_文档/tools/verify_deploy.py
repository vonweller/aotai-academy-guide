import hashlib, os
import paramiko
APP = os.path.join('01_固件', 'CyberCAM_AI书院')
def md5(p): return hashlib.md5(open(p,'rb').read()).hexdigest()
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.10.62', username='pi', password='pi', timeout=15, banner_timeout=25, auth_timeout=25, allow_agent=False, look_for_keys=False)
def run(cmd, t=20):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read()+e.read()).decode('utf-8','ignore')
pairs = ['main.py','config.py','relic.py','ui.py','camera.py','face.py','audio.py','content_loader.py','points.py']
print('文件哈希比对:')
bad = []
for f in pairs:
    lp = os.path.join(APP, f)
    if not os.path.exists(lp):
        print('  本地缺', f); continue
    lm = md5(lp)
    rm = run('md5sum /data/app/aotai/%s 2>/dev/null' % f).strip().split()
    rm = rm[0] if rm else 'MISSING'
    ok = (lm == rm)
    if not ok:
        bad.append(f)
    print('  %-20s %s' % (f, 'OK' if ok else 'DIFF  本地%s 板子%s' % (lm[:8], rm[:8])))
print()
print('不一致:', bad if bad else '无')
print()
print('=== 关键内容核对 ===')
print('RELIC_KEYS:', run('grep -a RELIC_KEYS /data/app/aotai/config.py'))
print('模型大小:', run('ls -l /data/aotai/relics/model.npz'))
print('新音频:', run('ls /data/aotai/audio/zh/p_congrats.mp3 /data/aotai/audio/zh/p_summary.mp3 2>&1'))
print('run.sh:', run('cat /data/app/aotai/run.sh'))
c.close()