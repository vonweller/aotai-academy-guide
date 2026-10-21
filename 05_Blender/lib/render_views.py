# -*- coding: utf-8 -*-
"""渲染验收图：自动按场景包围盒取景（overview/gate/hall/north）"""
import bpy, os, math, mathutils

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GLB = os.path.join(ROOT, "out", "aotai_academy.glb")
QC = os.path.join(ROOT, "qc")
os.makedirs(QC, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

# FLIP_TEX: GLB 内嵌的匾额贴图是预镜像版（给网页用），Blender 渲染时再翻回来才是正读
TMP_DIR = os.path.join(ROOT, "qc", "_tmp")
os.makedirs(TMP_DIR, exist_ok=True)
for m in bpy.data.materials:
    if not m.name.startswith("TEX_"):
        continue
    try:
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        tex = None
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image:
                tex = n
                break
        if not tex:
            continue
        img = tex.image
        w, h = img.size
        px = list(img.pixels)
        for yy in range(h):
            row = yy * w * 4
            for xx in range(w // 2):
                a = row + xx * 4
                c = row + (w - 1 - xx) * 4
                px[a:a + 4], px[c:c + 4] = px[c:c + 4], px[a:a + 4]
        out = os.path.join(TMP_DIR, img.name.split("/")[-1] or (m.name + ".png"))
        if not out.lower().endswith((".png", ".jpg")):
            out += ".png"
        newimg = bpy.data.images.new(m.name + "_flip", w, h, alpha=False)
        newimg.pixels = px
        newimg.filepath_raw = out
        newimg.file_format = 'PNG'
        newimg.save()
        tex.image = newimg
        print("[flip]", m.name, "->", out)
    except Exception as e:
        print("[warn] flip fail", m.name, e)

# 包围盒（排除大地面）
GROUND_NAMES = {"ground", "Plane", "Plane.001"}
mins = [1e9] * 3
maxs = [-1e9] * 3
for ob in bpy.data.objects:
    if ob.type != 'MESH':
        continue
    if ob.name in GROUND_NAMES or 'ground' in ob.name.lower():
        continue
    for c in ob.bound_box:
        w = ob.matrix_world @ mathutils.Vector(c)
        for i in range(3):
            mins[i] = min(mins[i], w[i])
            maxs[i] = max(maxs[i], w[i])
center = mathutils.Vector(((mins[0]+maxs[0])/2, (mins[1]+maxs[1])/2, (mins[2]+maxs[2])/2))
size = mathutils.Vector((maxs[0]-mins[0], maxs[1]-mins[1], maxs[2]-mins[2]))
print("[bbox] min", ["%.1f" % v for v in mins], "max", ["%.1f" % v for v in maxs])
print("[bbox] center", ["%.1f" % v for v in center], "size", ["%.1f" % v for v in size])

# 灯光
bpy.ops.object.light_add(type='SUN', location=(center.x + 20, center.y + 20, center.z + 40))
sun = bpy.context.object
sun.data.energy = 3.5
sun.rotation_euler = (math.radians(45), math.radians(8), math.radians(20))
bpy.ops.object.light_add(type='AREA', location=(center.x - 25, center.y - 25, center.z + 25))
fill = bpy.context.object
fill.data.energy = 2000
fill.data.size = 40

world = bpy.context.scene.world or bpy.data.worlds.new("W")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = (0.52, 0.63, 0.70, 1)
bg.inputs[1].default_value = 1.15

sc = bpy.context.scene
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else ('BLENDER_EEVEE' if 'BLENDER_EEVEE' in engines else 'CYCLES')
sc.render.resolution_x = 1600
sc.render.resolution_y = 900
try:
    sc.view_settings.view_transform = 'AgX'
except Exception:
    pass

bpy.ops.object.camera_add(location=(0, 0, 0))
cam = bpy.context.object
cam.data.lens = 42
sc.camera = cam

def place(pos, target):
    cam.location = pos
    d = mathutils.Vector(target) - mathutils.Vector(pos)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

R = max(size.x, size.y, size.z) * 0.95
views = {
    # 已知场景布局（Blender 坐标，门前朝 +Y）：门楼 y=17.6，讲堂 y=-6.5，六角亭 (-6.5,-13.5)
    "overview": (mathutils.Vector((24, 34, 30)), mathutils.Vector((0, 4, 3))),
    "gate":     (mathutils.Vector((0.6, 27.5, 5.2)), mathutils.Vector((0, 17.2, 3.6))),
    "hall":     (mathutils.Vector((4.5, 6.5, 7.5)), mathutils.Vector((0, -5.0, 4.0))),
    "north":    (mathutils.Vector((-22, -26, 20)), mathutils.Vector((-2, -6, 3))),
}

for name, (pos, target) in views.items():
    place(pos, target)
    sc.render.filepath = os.path.join(QC, "render_%s.png" % name)
    bpy.ops.render.render(write_still=True)
    print("[render]", name)

# 再看一眼模型朝向：打印门楼（最大 Y）的位置
print("[render] done")
