import bpy, json, sys, os
sys.path.insert(0, r'05_Blender/lib')
# 直接量：讲堂 roof 中心与工坊 roof 中心
print('hall  center y = -6.5, size 18x11 -> y range', -6.5-5.2, 'to', -6.5+5.2)
print('hall  roof w=17.2 d=10.4 overhang 1.2 -> half', (17.2+2.4)/2, (10.4+2.4)/2)
print('hall  roof y range', -6.5-(10.4+2.4)/2, 'to', -6.5+(10.4+2.4)/2)
print('ws    center y = 8.5, roof d=7.6 overhang 0.8 -> half', (7.6+1.6)/2)
print('ws    roof y range', 8.5-(7.6+1.6)/2, 'to', 8.5+(7.6+1.6)/2)
print('=> 需要工坊中心 y 至少 >', -6.5+(10.4+2.4)/2 + (7.6+1.6)/2 + 1.0)