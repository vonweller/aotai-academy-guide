import hashlib, os, time
import paramiko
APP = os.path.join('01_固件', 'CyberCAM_AI书院')
def md5(p): return hashlib.md5(open(p,'rb').read()).hexdigest()
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.10.62', username='pi', password='pi', timeout=15, banner_timeout=25, auth_timeout=25, allow_agent=False, look_for_keys=False)
def run(cmd, t=25):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read()+e.read()).decode('utf-8','ignore')
ps = run('ps -eo pid,cmd')
for line in ps.splitlines():
    parts = line.split(None, 1)
    if len(parts) == 2 and parts[1].strip().startswith('python3 -u main.py'):
        run('kill ' + parts[0]); print('stopped', parts[0])
time.sleep(1.5)
sftp = c.open_sftp()
files = [f for f in sorted(os.listdir(APP)) if f.endswith(('.py','.txt','.sh'))]
for fn in files:
    sftp.put(os.path.join(APP, fn), '/data/app/aotai/' + fn)
sftp.close()
run('rm -rf /data/app/aotai/__pycache__; chown -R pi:pi /data/app/aotai; sync')
time.sleep(1)
remote = run('md5sum ' + ' '.join('/data/app/aotai/'+f for f in files))
print('mismatch', [f for f in files if md5(os.path.join(APP,f)) not in remote])
chan = c.get_transport().open_session()
chan.exec_command('cd /data/app/aotai && setsid python3 -u main.py >/tmp/app.log 2>&1 < /dev/null')
time.sleep(0.4); chan.close()
time.sleep(8)
print('PROC', run('ps -eo pid,pcpu,cmd | grep "python3 -u main.py" | grep -v grep'))
print('ERR', run('grep -a -E "Traceback|KeyError" /tmp/app.log | tail -3') or 'none')
c.close()