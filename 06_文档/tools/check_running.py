import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.10.62', username='pi', password='pi', timeout=15, banner_timeout=25, auth_timeout=25, allow_agent=False, look_for_keys=False)
def run(cmd, t=20):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read()+e.read()).decode('utf-8','ignore')
print('uptime:', run('uptime'))
print('进程:'); print(run('ps -eo pid,ppid,stat,etime,cmd | grep -E "main.py|lvglsim|app-launcher" | grep -v grep') or '  无')
print('摄像头占用:', run('ls -l /proc/*/fd 2>/dev/null | grep -c video7').strip())
print('日志:'); print(run('tail -c 500 /tmp/app.log 2>/dev/null') or '  无日志')
c.close()