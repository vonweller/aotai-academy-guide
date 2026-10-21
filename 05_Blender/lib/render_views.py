import bpy, os, math, json, mathutils
BASE = r'C:\\Users\\52953\\Desktop\\智能博物一一粤地非遗物语之东莞熬台书院'
GLB = os.path.join(BASE, '05_Blender', 'out', 'aotai_academy.glb')
OUT = os.path.join(BASE, '05_Blender', 'qc')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x = 1600
sc.render.resolution_y = 1000
sc.eevee.taa_render_samples = 96
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.60, 0.74, 0.92, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 1.4
bpy.ops.object.light_add(type='SUN', location=(20, -52, 46))
sun = bpy.context.object
sun.data.energy = 4.5
sun.rotation_euler = (math.radians(38), math.radians(10), math.radians(18))
bpy.ops.object.light_add(type='AREA', location=(-24, -28, 22))
f = bpy.context.object
f.data.energy = 1000
f.data.size = 30
bpy.ops.object.camera_add(location=(0, 0, 5))
cam = bpy.context.object
sc.camera = cam
def shot(name, pos, tgt, lens):
    cam.location = pos
    d = mathutils.Vector(tgt) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    sc.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.render.render(write_still=True)
    print('[render]', name)
# 工坊：从院内侧（+y 方向）看进去；大门：正对面 -y
shot('render_workshop', (2.0, -6.0, 3.2), (10.5, -10.0, 1.8), 26)
shot('render_gate', (0, -52, 3.2), (0, -31.0, 4.0), 28)
shot('render_hall_inside', (0, -9.0, 2.6), (0, -3.0, 1.4), 22)
shot('render_overview', (38, -58, 32), (2, -20, 2), 40)
print('HEADLESS ' + json.dumps({'ok': True}))