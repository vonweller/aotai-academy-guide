# -*- coding: utf-8 -*-
"""扩建件二：前院碑廊、讲堂内景、后园曲水与陈设。

对应真实书院的空间层次：
  前院（大门内）——碑廊、香炉、古井、树池
  讲堂内 —— 讲案、蒲团、书架、烛台、落地罩
  后园 —— 曲水、拱桥、石灯、廊架

坐标与 build_academy.py 一致：Blender Z-up，+Y 为门前方向。
大门 y=17.6，前院 y≈9.5，讲堂 y=-6.5，后园 y≈-13.5。
"""
import bpy
import math
import random


def _mat(name, color, rough=0.85, metal=0.05, emit=None):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (emit[0], emit[1], emit[2], 1.0)
        b.inputs['Emission Strength'].default_value = 1.4
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


def _box(name, r, h, loc, material, verts=8):
    bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r * 0.02, depth=h,
                                    vertices=verts, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(material)
    return ob


def build_forecourt(cx=0.0, cy=10.0):
    """前院：碑廊 + 香炉 + 古井 + 树池。"""
    objs = []
    STONE = _mat('FcStone', (0.36, 0.38, 0.36), 0.95)
    STD = _mat('FcStoneDark', (0.22, 0.24, 0.23), 0.95)
    WOOD = _mat('FcWood', (0.26, 0.15, 0.07), 0.8)
    TILE = _mat('FcTile', (0.17, 0.18, 0.19), 0.88)
    BRONZE = _mat('FcBronze', (0.34, 0.26, 0.12), 0.45, 0.7)
    WATER = _mat('FcWater', (0.08, 0.22, 0.24), 0.12, 0.3)

    # ---- 碑廊：东西两列，每列 4 块碑 ----
    for side in (-1, 1):
        bx = side * 6.4
        # 廊柱
        for i in range(5):
            by = cy - 5.6 + i * 2.8
            objs.append(_cyl('fc_pillar', 0.13, 2.9, (bx, by, 1.45), WOOD, verts=10))
        # 廊顶
        objs.append(_cube('fc_corridor_roof', (1.9, 12.4, 0.16),
                          (bx, cy, 3.02), TILE))
        # 碑
        for i in range(4):
            by = cy - 4.2 + i * 2.8
            px = bx - side * 0.34
            objs.append(_cube('fc_stele_base', (0.62, 0.9, 0.24),
                              (px, by, 0.12), STD))
            objs.append(_cube('fc_stele', (0.16, 0.72, 1.5),
                              (px, by, 1.02), STONE))
            objs.append(_cube('fc_stele_top', (0.22, 0.8, 0.12),
                              (px, by, 1.82), STD))

    # ---- 香炉（鼎式，中轴偏前）----
    fx, fy = cx, cy + 3.2
    objs.append(_cyl('fc_censer_base', 0.62, 0.22, (fx, fy, 0.11), STD, verts=16))
    objs.append(_cyl('fc_censer_body', 0.46, 0.62, (fx, fy, 0.53), BRONZE, verts=16))
    objs.append(_cyl('fc_censer_rim', 0.54, 0.10, (fx, fy, 0.89), BRONZE, verts=16))
    for i in range(3):
        a = i * math.tau / 3
        objs.append(_cyl('fc_censer_leg', 0.07, 0.42,
                         (fx + math.cos(a) * 0.34, fy + math.sin(a) * 0.34, 0.21),
                         BRONZE, verts=8))
    for i in range(2):
        objs.append(_cyl('fc_censer_ear', 0.06, 0.30,
                         (fx + (-0.42 if i == 0 else 0.42), fy, 1.06), BRONZE, verts=8,
                         rot=(0, math.pi / 2, 0)))

    # ---- 古井 ----
    jx, jy = cx - 3.4, cy + 2.6
    objs.append(_cyl('fc_well_rim', 0.72, 0.44, (jx, jy, 0.22), STONE, verts=20))
    objs.append(_cyl('fc_well_water', 0.60, 0.05, (jx, jy, 0.40), WATER, verts=20))
    # 井架
    for s in (-1, 1):
        objs.append(_cyl('fc_well_post', 0.07, 1.7, (jx + s * 0.7, jy, 0.85), WOOD, verts=8))
    objs.append(_cube('fc_well_beam', (1.6, 0.09, 0.09), (jx, jy, 1.68), WOOD))
    objs.append(_cyl('fc_well_roller', 0.09, 1.2, (jx, jy, 1.52), WOOD,
                     verts=10, rot=(0, math.pi / 2, 0)))

    # ---- 树池（四角）----
    for i, (px, py) in enumerate(((cx - 5.4, cy - 6.2), (cx + 5.4, cy - 6.2),
                                   (cx - 5.4, cy + 5.6), (cx + 5.4, cy + 5.6))):
        objs.append(_cube('fc_planter', (1.5, 1.5, 0.42), (px, py, 0.21), STD))
        objs.append(_cyl('fc_planter_soil', 0.62, 0.10, (px, py, 0.44),
                         _mat('FcSoil', (0.18, 0.13, 0.09), 1.0), verts=14))

    return objs


def build_hall_inside(cx=0.0, cy=-6.5):
    """讲堂内景：讲案、蒲团、书架、烛台、落地罩。"""
    objs = []
    WOOD = _mat('HiWood', (0.28, 0.16, 0.08), 0.8)
    WDL = _mat('HiWoodLight', (0.46, 0.30, 0.15), 0.75)
    CLOTH = _mat('HiCloth', (0.42, 0.10, 0.08), 0.9)
    PAPER = _mat('HiPaper', (0.88, 0.84, 0.74), 0.95)
    CANDLE = _mat('HiCandle', (0.95, 0.80, 0.45), 0.6, 0.0, emit=(0.9, 0.6, 0.2))
    BRONZE = _mat('HiBronze', (0.34, 0.26, 0.12), 0.45, 0.7)

    # ---- 讲案（中央高台）----
    objs.append(_cube('hi_platform', (5.2, 2.6, 0.28), (cx, cy + 1.2, 0.88), WOOD))
    objs.append(_cube('hi_desk_top', (4.4, 1.5, 0.12), (cx, cy + 1.2, 1.14), WDL))
    objs.append(_cube('hi_desk_apron', (4.2, 0.10, 0.42), (cx, cy + 0.48, 0.96), WOOD))
    # 案上：笔架、砚、卷册
    objs.append(_cube('hi_brush_rest', (0.62, 0.20, 0.10), (cx - 1.2, cy + 1.2, 1.26), WDL))
    objs.append(_cyl('hi_inkstone', 0.22, 0.09, (cx + 0.3, cy + 1.2, 1.25), WOOD, verts=12))
    for k in range(3):
        objs.append(_cube('hi_book', (0.56, 0.38, 0.07),
                          (cx + 1.3, cy + 1.05 + k * 0.09, 1.24 + k * 0.07), PAPER))

    # ---- 蒲团（听课位，两列）----
    for row in range(3):
        for col in (-1, 1):
            px = cx + col * 1.5
            py = cy - 0.6 - row * 1.5
            objs.append(_cyl('hi_cushion', 0.42, 0.14, (px, py, 0.81), CLOTH, verts=16))

    # ---- 书架（后墙两列）----
    for s in (-1, 1):
        bx = cx + s * 3.4
        by = cy - 3.9
        objs.append(_cube('hi_shelf_body', (1.5, 0.42, 2.2), (bx, by, 1.84), WOOD))
        for k in range(3):
            objs.append(_cube('hi_shelf_board', (1.42, 0.46, 0.06),
                              (bx, by, 1.02 + k * 0.62), WDL))
            for t in range(4):
                objs.append(_cube('hi_shelf_book', (0.10, 0.28, 0.34),
                                  (bx - 0.56 + t * 0.34, by - 0.02, 1.25 + k * 0.62),
                                  PAPER if t % 2 else CLOTH))

    # ---- 烛台（讲案两侧）----
    for s in (-1, 1):
        lx = cx + s * 2.6
        ly = cy + 1.4
        objs.append(_cyl('hi_stand_base', 0.24, 0.10, (lx, ly, 0.80), BRONZE, verts=12))
        objs.append(_cyl('hi_stand_pole', 0.055, 1.5, (lx, ly, 1.55), BRONZE, verts=8))
        objs.append(_cyl('hi_candle', 0.075, 0.36, (lx, ly, 2.42), CANDLE, verts=10))

    # ---- 落地罩（讲堂与后室之间的隔断）----
    for s in (-1, 1):
        ox = cx + s * 3.0
        objs.append(_cube('hi_screen_frame', (0.14, 0.16, 3.0), (ox, cy - 4.4, 2.2), WOOD))
        for k in range(4):
            objs.append(_cube('hi_screen_bar', (1.1, 0.10, 0.08),
                              (ox + s * 0.6, cy - 4.4, 1.0 + k * 0.62), WDL))

    return objs


def build_back_garden(cx=-6.5, cy=-13.5):
    """后园：曲水 + 拱桥 + 石灯 + 廊架。"""
    objs = []
    WATER = _mat('BgWater', (0.07, 0.21, 0.23), 0.10, 0.35)
    STD = _mat('BgStoneDark', (0.24, 0.26, 0.25), 0.95)
    STONE = _mat('BgStone', (0.38, 0.40, 0.38), 0.95)
    WOOD = _mat('BgWood', (0.28, 0.16, 0.08), 0.8)
    TILE = _mat('BgTile', (0.17, 0.18, 0.19), 0.88)
    GREEN = _mat('BgGreen', (0.16, 0.30, 0.12), 0.95)

    # ---- 曲水：折线形水面（用多段略带角度的长条拼）----
    segments = [
        (-14.0, -9.0, -8.5, -9.0),
        (-8.5, -9.0, -4.0, -11.2),
        (-4.0, -11.2, 0.5, -11.2),
        (0.5, -11.2, 4.5, -9.4),
    ]
    for i, (x0, y0, x1, y1) in enumerate(segments):
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        ang = math.atan2(dy, dx)
        objs.append(_cube('bg_stream', (length, 1.5, 0.06), (mx, my, 0.05), WATER,
                          rot=(0, 0, ang)))
        # 两岸石沿
        for side in (-1, 1):
            ox = mx + math.sin(ang) * side * 0.82
            oy = my - math.cos(ang) * side * 0.82
            objs.append(_cube('bg_bank', (length, 0.16, 0.20), (ox, oy, 0.10), STD,
                              rot=(0, 0, ang)))

    # ---- 拱桥（跨在水面最宽处）----
    bx, by = -8.5, -9.0
    for i in range(7):
        t = i / 6.0
        h = 0.30 + math.sin(t * math.pi) * 0.78
        objs.append(_cube('bg_bridge_step', (0.62, 1.9, 0.10),
                          (bx - 1.9 + i * 0.63, by, h), STONE))
    for side in (-1, 1):
        objs.append(_cube('bg_bridge_rail', (4.4, 0.10, 0.10),
                          (bx, by + side * 0.95, 1.28), STD))
        for i in range(5):
            objs.append(_cyl('bg_bridge_post', 0.06, 0.44,
                             (bx - 1.8 + i * 0.9, by + side * 0.95, 1.10),
                             STD, verts=8))

    # ---- 石灯（沿水布置）----
    for i, (lx, ly) in enumerate(((-3.2, -9.6), (2.0, -9.8), (-12.0, -8.2))):
        objs.append(_cyl('bg_lamp_base', 0.26, 0.30, (lx, ly, 0.15), STD, verts=8))
        objs.append(_cyl('bg_lamp_pole', 0.10, 1.1, (lx, ly, 0.85), STONE, verts=8))
        objs.append(_cube('bg_lamp_house', (0.42, 0.42, 0.36), (lx, ly, 1.58), STONE))
        objs.append(_box('bg_lamp_cap', 0.34, 0.28, (lx, ly, 1.90), TILE, verts=4))

    # ---- 廊架（西侧）----
    px = -13.5
    for i in range(4):
        py = cy - 1.0 + i * 2.6
        for s in (-1, 1):
            objs.append(_cyl('bg_pergola_post', 0.11, 2.7,
                             (px + s * 1.1, py, 1.35), WOOD, verts=8))
        objs.append(_cube('bg_pergola_beam', (2.6, 0.12, 0.14), (px, py, 2.76), WOOD))
    for i in range(2):
        objs.append(_cube('bg_pergola_top', (0.12, 8.0, 0.10),
                          (px - 0.55 + i * 1.1, cy + 2.9, 2.88), WOOD))
    # 藤蔓（绿色团块）
    for i in range(7):
        vt = i / 6.0
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=1, radius=0.36,
            location=(px + random.uniform(-0.9, 0.9),
                      cy - 1.0 + vt * 7.8, 2.9 + random.uniform(-0.2, 0.25)))
        ob = bpy.context.object
        ob.name = 'bg_vine'
        ob.data.materials.append(GREEN)
        objs.append(ob)

    return objs