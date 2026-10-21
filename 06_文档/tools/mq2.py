import time
import paho.mqtt.client as mqtt
import json
c = mqtt.Client(client_id='pctest2')
c.username_pw_set('siot', 'dfrobot')
c.connect('159.75.137.223', 1883, 30)
c.loop_start()
time.sleep(1.5)
# 进人脸页
c.publish('aotai/cmd', json.dumps({'cmd': 'goto_stage', 'stage': 1}), qos=0)
print('sent goto_stage 1')
time.sleep(2)
# 模拟识别成功（K 键 = on_key -> next_stage）
c.publish('aotai/cmd', json.dumps({'cmd': 'next'}), qos=0)
print('sent next')
time.sleep(3)
c.loop_stop(); c.disconnect()
print('done')