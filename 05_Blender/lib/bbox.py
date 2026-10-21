import bpy, os, json, mathutils
BASE = r'C:\\Users\\52953\\Desktop\\智能博物一一粤地非遗物语之东莞熬台书院'
GLB = os.path.join(BASE, '05_Blender', 'out', 'aotai_academy.glb')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
ob = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
print('verts', len(ob.data.vertices), 'polys', len(ob.data.polygons))
vs = [v.co for v in ob.data.vertices]
xs=[v.x for v in vs]; ys=[v.y for v in vs]; zs=[v.z for v in vs]
print('BBOX x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f' % (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)))
# 工坊区顶点数（x>4, -14<y<-4）
ws = [v for v in vs if v.x > 4 and -14 < v.y < -4]
print('workshop zone verts', len(ws))
print('HEADLESS ' + json.dumps({'verts': len(ob.data.vertices), 'polys': len(ob.data.polygons), 'ws_verts': len(ws), 'bbox': [round(min(xs),1),round(max(xs),1),round(min(ys),1),round(max(ys),1),round(min(zs),1),round(max(zs),1)]}))