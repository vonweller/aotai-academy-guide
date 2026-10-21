import bpy, os, math, json, mathutils
BASE = r'C:\\Users\\52953\\Desktop\\智能博物一一粤地非遗物语之东莞熬台书院'
GLB = os.path.join(BASE, '05_Blender', 'out', 'aotai_academy.glb')
OUT = os.path.join(BASE, '05_Blender', 'qc')
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
ob = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
# 工坊：Blender 内 (8.2, 9.5) -> 导入后 y 取反 => (8.2, -9.5)
sel = [v for v in vs if v.x > 3.5 and v.y < -4.0]
print('sel', len(sel))
xs=[v.x for v in sel]; ys=[v.y for v in sel]; zs=[v.z for v in sel]
print('WS x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f' % (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)))
cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2; cz=(min(zs)+max(zs))/2
print('CENTER %.2f %.2f %.2f' % (cx,cy,cz))
sc = bpy.context.scene
try:
    sc.render.engine = 'BLENDER_EEVEE'
except Exception:
    sc.render.engine = 'BLENDER_WORKBENCH'
sc.render.resolution_x = 1400; sc.render.resolution_y = 900
sc.eevee.taa_render_samples = 64
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.52, 0.66, 0.86, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 1.2
bpy.ops.object.light_add(type='SUN', location=(25, -18, 34))
sun = bpy.context.object; sun.data.energy = 3.6
sun.rotation_euler = (math.radians(46), math.radians(10), math.radians(38))
bpy.ops.object.light_add(type='AREA', location=(-16, -8, 14))
f = bpy.context.object; f.data.energy = 600; f.data.size = 22
bpy.ops.object.camera_add(location=(0,0,10))
cam = bpy.context.object; sc.camera = cam
def aim(pos, tgt, lens):
    cam.location = pos
    d = mathutils.Vector(tgt) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z','Y').to_euler()
    cam.data.lens = lens
# 工坊在 (8.2,-9.5)，从 -y 更远处看它正门
shots = [
    ('ws_front', (cx, cy - 14, cz + 2.5), (cx, cy, cz + 1.2), 30),
    ('ws_angle', (cx - 12, cy - 12, cz + 5.0), (cx, cy, cz), 32),
    ('ws_close', (cx, cy - 9, cz + 1.8), (cx, cy, cz + 1.0), 24),
    ('site_all', (30, -44, 28), (0, -12, 2), 42),
    ('site_front', (0, -46, 10), (0, -8, 3.0), 36),
]
for name, pos, tgt, lens in shots:
    aim(pos, tgt, lens)
    sc.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.render.render(write_still=True)
    print('[render]', name)
print('HEADLESS ' + json.dumps({'ok': True, 'center': [cx, cy, cz]}))