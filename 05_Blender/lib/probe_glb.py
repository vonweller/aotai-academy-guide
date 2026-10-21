import bpy, os, math, json, mathutils
GLB = r'C:\\Users\\52953\\Desktop\\智能博物一一粤地非遗物语之东莞熬台书院\\05_Blender\\out\\aotai_academy.glb'
print('exists', os.path.exists(GLB))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
print('meshes', len(meshes))
allv = []
for o in meshes:
    allv += [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
xs = [v.x for v in allv]; ys = [v.y for v in allv]; zs = [v.z for v in allv]
print('BBOX x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f' % (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)))
print('HEADLESS ' + json.dumps({'ok': True}))