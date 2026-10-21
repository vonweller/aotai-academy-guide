import hashlib, os
import paramiko
APP = os.path.join('01_固件', 'CyberCAM_AI书院')
def md5(p): return hashlib.md5(open(p,'rb').read()).hexdigest()
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.10.62', username='pi', password='pi', timeout=12, banner_timeout=20, auth_timeout=20, allow_agent=False, look_for_keys=False)
def run(cmd, t=15):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read()+e.read()).decode('utf-8','ignore')
pairs = ['main.py','face.py','config.py','ui.py','points.py','audio.py']
remote = run('md5sum ' + ' '.join('/data/app/aotai/'+f for f in pairs))
allok = all(md5(os.path.join(APP,f)) in remote for f in pairs)
print('HASH_MATCH', allok)
print('BTN_LEARN', run('grep -c btn_learn /data/app/aotai/ui.py'))
print('LEARN_FN', run('grep -c learn_face /data/app/aotai/main.py'))
print('STOP_BEFORE', run('grep -c "先把上一条掐掉" /data/app/aotai/audio.py'))
print('PROC', run('ps -eo pid,etime,cmd | grep aotai/main.py | grep -v grep'))
print('POINTS', run('cat /data/aotai/points.json 2>/dev/null | head -12'))
c.close()