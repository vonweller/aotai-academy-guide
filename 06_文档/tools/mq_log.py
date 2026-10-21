import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.10.62', username='pi', password='pi', timeout=12, banner_timeout=20, auth_timeout=20, allow_agent=False, look_for_keys=False)
_, o, e = c.exec_command('grep -a -E "MQTT|自动进入|摄像头|自动" /tmp/app.log | tail -12', timeout=20)
print((o.read()+e.read()).decode('utf-8','ignore')[:1500])
c.close()