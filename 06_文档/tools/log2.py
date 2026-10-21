import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.10.62', username='pi', password='pi', timeout=12, banner_timeout=20, auth_timeout=20, allow_agent=False, look_for_keys=False)
def run(cmd, t=20):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read()+e.read()).decode('utf-8','ignore')
print('LOG'); print(run('tail -c 1200 /tmp/app.log'))
print('ALIVE', run("ps -eo pid,pcpu,etime,cmd | grep 'python3 -u main.py' | grep -v grep"))
c.close()