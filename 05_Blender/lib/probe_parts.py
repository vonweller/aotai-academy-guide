import sys, os
LIB = r'C:\\Users\\52953\\Desktop\\智能博物一一粤地非遗物语之东莞熬台书院\\05_Blender\\lib'
sys.path.insert(0, LIB)
import bpy, mathutils
bpy.ops.wm.read_factory_settings(use_empty=True)
import build_academy as B
B.purge()
B.build_materials()
def bounds(objs, tag):
    pts = []
    for o in objs:
        if o.type != 'MESH':
            continue
        pts += [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    if not pts:
        print(tag, 'no mesh')
        return
    xs=[p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
    print('%-12s x %6.1f..%6.1f  y %6.1f..%6.1f  z %5.1f..%5.1f' % (tag, min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)))
bounds(B.make_landscape(), 'landscape')
bounds(B.make_gate(), 'gate')
bounds(B.make_hall(), 'hall')
bounds(B.make_workshop(), 'workshop')
bounds(B.make_pavilion(), 'pavilion')
import workshop_detail
bounds(workshop_detail.build_workshop_detail(), 'ws_detail')