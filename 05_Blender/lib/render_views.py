import bpy, os, math, json, mathutils
BASE = r'C:\\Users\\52953\\Desktop\\智能博物一一粤地非遗物语之东莞熬台书院'
GLB = os.path.join(BASE, '05_Blender', 'out', 'aotai_academy.glb')
OUT = os.path.join(BASE, '05_Blender', 'qc')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
sc = bpy.context.scene
try:
    sc.render.engine = 'BLENDER_EEVEE'
except Exception:
    sc.render.engine = 'BLENDER_WORKBENCH'
sc.render.resolution_x = 1600
sc.render.resolution_y = 1000
sc.eevee.taa_render_samples = 96
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.56, 0.70, 0.88, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 1.3
bpy.ops.object.light_add(type='SUN', location=(30, -40, 40))
sun = bpy.context.object
sun.data.energy = 4.2
sun.rotation_euler = (math.radians(42), math.radians(14), math.radians(30))
bpy.ops.object.light_add(type='AREA', location=(-20, -20, 18))
f = bpy.context.object
f.data.energy = 900
f.data.size = 28
bpy.ops.object.camera_add(location=(0, 0, 5))
cam = bpy.context.object
sc.camera = cam
def aim(pos, tgt, lens):
    cam.location = pos
    d = mathutils.Vector(tgt) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
shots = [
    ('render_overview', (34, -52, 30), (2, -16, 2), 44),
    ('render_gate', (0, -44, 6), (0, -30, 3.4), 38),
    ('render_hall', (0, -22, 7), (0, -2, 2.8), 36),
    ('render_workshop', (10.5, -24, 5.0), (10.5, -9, 2.0), 32),
    ('render_pavilion', (-11, -16, 5.0), (-7, -27, 1.6), 34),
]
for name, pos, tgt, lens in shots:
    aim(pos, tgt, lens)
    sc.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.render.render(write_still=True)
    print('[render]', name)
print('HEADLESS ' + json.dumps({'ok': True}))