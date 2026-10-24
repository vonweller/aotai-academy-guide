import time
import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.10.62', username='pi', password='pi', timeout=15, banner_timeout=25, auth_timeout=25, allow_agent=False, look_for_keys=False)
def run(cmd, t=25):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read()+e.read()).decode('utf-8','ignore')
# 启动前先清干净，避免多个进程抢摄像头
ps = run('ps -eo pid,cmd')
for line in ps.splitlines():
    parts = line.split(None, 1)
    if len(parts) == 2 and parts[1].strip().startswith('python3 -u main.py'):
        run('kill -9 ' + parts[0])
time.sleep(1)
chan = c.get_transport().open_session()
chan.exec_command('cd /data/app/aotai && setsid python3 -u main.py >/tmp/app.log 2>&1 < /dev/null')
time.sleep(0.4); chan.close()
time.sleep(9)
print('进程:'); print(run('ps -eo pid,pcpu,etime,cmd | grep "python3 -u main.py" | grep -v grep') or '  未启动')
print('摄像头:', run('grep -a 摄像头 /tmp/app.log | tail -2') or '  无')
print('错误:', run('grep -a -E "Traceback|Error" /tmp/app.log | tail -3') or '  无')
print('日志尾:'); print(run('tail -c 600 /tmp/app.log'))
c.close()