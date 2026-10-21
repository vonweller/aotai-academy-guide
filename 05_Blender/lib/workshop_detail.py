# -*- coding: utf-8 -*-
"""非遗工坊内部与周边陈设（扩建件）。

参考：岭南书院工坊 / 织机 / 靛蓝染缸 / 草编工位（Wikimedia Commons 参照图）。
坐标与 build_academy.py 一致：Blender Z-up，+Y 为门前方向。
"""
import bpy
import math
import random


def _mat(name, color, rough=0.85, metal=0.05):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m


def _cube(name, size, loc, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    ob.rotation_euler = rot
    ob.data.materials.append(material)
    return ob


def _cyl(name, r, h, loc, material, verts=12, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler = rot
    ob.data.materials.append(material)
    return ob


def build_workshop_detail(cx=8.2, cy=9.5):
    """在工坊盒子内部与门口补陈设，让它看起来真的在用。"""
    objs = []
    W = _mat('WsWood', (0.30, 0.18, 0.09), 0.8)
    WL = _mat('WsWoodLight', (0.48, 0.31, 0.16), 0.75)
    ROPE = _mat('WsRope', (0.55, 0.45, 0.28), 0.9)
    CLOTH = _mat('WsCloth', (0.12, 0.10, 0.09), 0.92)
    CLOTHB = _mat('WsClothBrown', (0.30, 0.17, 0.10), 0.92)
    POT = _mat('WsPot', (0.22, 0.20, 0.18), 0.9)
    BLUE = _mat('WsIndigo', (0.05, 0.09, 0.22), 0.85)
    STRAW = _mat('WsStraw', (0.62, 0.50, 0.24), 0.95)
    GREEN = _mat('WsGreen', (0.16, 0.30, 0.12), 0.95)

    inner_x = cx - 0.4

    # ---- 1) 门口两侧：晾晒架（挂丝绸与草编）----
    for side, sx in (('L', cx - 3.9), ('R', cx + 3.9)):
        for i, yy in enumerate((cy - 2.6, cy + 2.6)):
            objs.append(_cyl('wsrack_pole_%s%d' % (side, i), 0.06, 2.6,
                             (sx, yy, 1.3), W, verts=8))
        objs.append(_cube('wsrack_bar_%s' % side, (5.7, 0.09, 0.09),
                          (sx, cy, 2.5), W))
        # 挂在架上的布
        for k in range(4):
            yy = cy - 2.0 + k * 1.35
            mat = CLOTH if k % 2 == 0 else CLOTHB
            objs.append(_cube('wscloth_%s%d' % (side, k), (0.06, 0.92, 1.15),
                              (sx, yy, 1.85), mat))

    # ---- 2) 左侧：靛蓝染缸（三个，带木架）----
    for i in range(3):
        px = inner_x - 2.2 + i * 1.5
        py = cy - 2.4
        objs.append(_cyl('wsdye_vat_%d' % i, 0.62, 0.95, (px, py, 0.48), POT, verts=18))
        objs.append(_cyl('wsdye_liquid_%d' % i, 0.54, 0.10, (px, py, 0.92), BLUE, verts=18))
        objs.append(_cyl('wsdye_rim_%d' % i, 0.66, 0.10, (px, py, 0.98), W, verts=18))
        # 缸边木棍
        objs.append(_cyl('wsdye_stick_%d' % i, 0.035, 1.5,
                         (px + 0.42, py + 0.18, 1.25), WL, verts=6,
                         rot=(0.25, 0.0, 0.4)))

    # ---- 3) 右侧：草编工位（矮凳 + 草料堆 + 半成品篮）----
    for i in range(2):
        bx = cx + 1.4 + i * 1.7
        by = cy - 1.6
        objs.append(_cyl('wsstool_%d' % i, 0.26, 0.42, (bx, by, 0.21), WL, verts=10))
        # 未编完的草束
        objs.append(_cube('wsstraw_%d' % i, (0.55, 0.85, 0.16),
                          (bx, by + 0.55, 0.46), STRAW,
                          rot=(0, 0, random.uniform(-0.2, 0.2))))
        # 成品篮
        objs.append(_cyl('wsbasket_%d' % i, 0.30, 0.34, (bx + 0.95, by + 0.2, 0.17),
                         STRAW, verts=14))

    # ---- 4) 靠墙：织机（简化立式）----
    loom_x = cx + 2.9
    loom_y = cy + 1.3
    # 四根立柱
    for dx, dy in ((-0.55, -0.45), (0.55, -0.45), (-0.55, 0.55), (0.55, 0.55)):
        objs.append(_cyl('wsloom_leg', 0.055, 1.75,
                         (loom_x + dx, loom_y + dy, 0.87), W, verts=8))
    # 上横梁 / 下横梁
    objs.append(_cube('wsloom_top', (1.3, 0.09, 0.09), (loom_x, loom_y, 1.72), W))
    objs.append(_cube('wsloom_bottom', (1.3, 0.09, 0.09), (loom_x, loom_y, 0.42), W))
    # 经线（细密竖条）
    for k in range(14):
        lx = loom_x - 0.55 + k * 0.084
        objs.append(_cube('wsloom_warp_%d' % k, (0.010, 0.010, 1.22),
                          (lx, loom_y - 0.02, 1.05), ROPE))
    # 卷布轴
    objs.append(_cyl('wsloom_roll', 0.10, 1.25, (loom_x, loom_y + 0.30, 0.62),
                     WL, verts=12, rot=(0, math.pi / 2, 0)))
    objs.append(_cube('wsloom_cloth', (1.05, 0.02, 0.52),
                      (loom_x, loom_y + 0.30, 0.95), CLOTH))

    # ---- 5) 工坊后墙：工具挂板 + 匾额感小牌 ----
    backy = cy + 3.35
    objs.append(_cube('wstool_board', (3.4, 0.08, 1.1),
                      (cx, backy, 2.05), WL))
    for k in range(6):
        hx = cx - 1.4 + k * 0.56
        objs.append(_cube('wstool_hang_%d' % k, (0.05, 0.05, 0.55),
                          (hx, backy - 0.08, 2.0), W,
                          rot=(0, 0, 0)))

    # ---- 6) 中央：工作台（草编/裁剪用）----
    objs.append(_cube('wstable_top', (2.6, 1.15, 0.09),
                      (inner_x - 0.3, cy + 0.6, 0.86), WL))
    for dx, dy in ((-1.15, -0.45), (1.15, -0.45), (-1.15, 0.45), (1.15, 0.45)):
        objs.append(_cube('wstable_leg', (0.09, 0.09, 0.82),
                          (inner_x - 0.3 + dx, cy + 0.6 + dy, 0.41), W))
    # 台面上的布卷与工具
    objs.append(_cyl('wstable_roll', 0.13, 1.0, (inner_x - 0.9, cy + 0.6, 1.05),
                     CLOTH, verts=12, rot=(0, math.pi / 2, 0)))
    objs.append(_cube('wstable_cut', (0.5, 0.36, 0.03),
                      (inner_x + 0.2, cy + 0.55, 0.92), STRAW))

    # ---- 7) 坊前小院：石桌 + 四个石凳 + 盆栽 ----
    tx, ty = cx - 1.0, cy - 5.2
    objs.append(_cyl('wsyard_table', 0.72, 0.10, (tx, ty, 0.78),
                     bpy.data.materials.get('Stone', POT), verts=20))
    objs.append(_cyl('wsyard_pedestal', 0.28, 0.74, (tx, ty, 0.37),
                     bpy.data.materials.get('Stone', POT), verts=14))
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        objs.append(_cyl('wsyard_stool_%d' % k, 0.22, 0.42,
                         (tx + math.cos(a) * 1.25, ty + math.sin(a) * 1.25, 0.21),
                         bpy.data.materials.get('Stone', POT), verts=12))

    # 盆栽（陶盆 + 绿植球）
    for i, (px, py) in enumerate(((cx - 4.0, cy - 4.2), (cx + 4.0, cy - 4.2),
                                   (cx - 4.2, cy + 4.2), (cx + 4.2, cy + 4.2))):
        objs.append(_cyl('wspot_%d' % i, 0.30, 0.46, (px, py, 0.23), POT, verts=14))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.42,
                                              location=(px, py, 0.78))
        ob = bpy.context.object
        ob.name = 'wsbush_%d' % i
        ob.scale = (1.0, 1.0, 0.85)
        ob.data.materials.append(GREEN)
        objs.append(ob)

    # ---- 8) 檐下灯笼（门口两侧）----
    LM = bpy.data.materials.get('Lantern')
    if LM is None:
        LM = _mat('Lantern', (0.60, 0.10, 0.04), 0.6)
    for sx in (cx - 3.3, cx + 3.3):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.24, segments=14, ring_count=8,
                                            location=(sx, cy - 4.1, 3.6))
        ob = bpy.context.object
        ob.name = 'wslantern'
        ob.scale = (1.0, 1.0, 1.25)
        ob.data.materials.append(LM)
        objs.append(ob)

    return objs