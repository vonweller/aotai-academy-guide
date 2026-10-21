import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.10.62', username='pi', password='pi', timeout=12, banner_timeout=20, auth_timeout=20, allow_agent=False, look_for_keys=False)
def run(cmd, t=20):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read()+e.read()).decode('utf-8','ignore')
pid = run("ps -eo pid,cmd | grep 'python3 -u main.py' | grep -v grep | awk '{print $1}' | tail -1").strip()
print('PID', pid, 'ALIVE' if pid else 'DEAD')
print('CPU/MEM', run('ps -p %s -o pcpu=,pmem=,etime=' % pid).strip())
print('MEM', run('free -m | sed -n 2p'))
print('LOAD', run('uptime'))
print('FILES', run('ls /data/app/aotai/*.py | wc -l'))
c.close()