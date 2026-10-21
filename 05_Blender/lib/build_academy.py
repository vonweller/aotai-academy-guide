# -*- coding: utf-8 -*-
"""鳌台书院 3D 场景生成器（Blender bpy）

坐标约定（与 02_数据/map.json 一致）：
  Blender Z-up  ->  glTF 导出后 Y-up
  门前朝 +Z（Blender 的 +Y 会变成 glTF 的 -Z，所以这里**用 +Y 当"门前方向"**，
  导出时 yup 转换后正好是 three.js 的 +Z）
本脚本用 Blender 坐标：+Y = 门前方向。

运行：
  blender -b --factory-startup -P lib/build_academy.py -- out/aotai_academy.glb
"""
import bpy
import bmesh
import math
import os
import sys
import random
import tempfile
import mathutils

random.seed(20261020)

OUT_GLB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out", "aotai_academy.glb")

# ------------------------------------------------------------------
# 基础工具
# ------------------------------------------------------------------
def purge():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, rough=0.85, metal=0.05, emit=None):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit:
        bsdf.inputs["Emission Color"].default_value = (emit[0], emit[1], emit[2], 1.0)
        bsdf.inputs["Emission Strength"].default_value = 1.4
    return m


def cube(name, size, loc, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (size[0], size[1], size[2])
    ob.rotation_euler = rot
    ob.data.materials.append(material)
    return ob


def cyl(name, r, h, loc, material, verts=16, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler = rot
    ob.data.materials.append(material)
    return ob


def sphere(name, r, loc, material, scale=(1, 1, 1), seg=16):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg, ring_count=max(8, seg // 2), location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    ob.data.materials.append(material)
    return ob


def cone(name, r1, r2, h, loc, material, verts=8, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=h, vertices=verts, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler = rot
    ob.data.materials.append(material)
    return ob


TEX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tex")


def make_text_png(text, path, size=(768, 192), bg=(0.05, 0.07, 0.09), fg=(0.85, 0.68, 0.30)):
    """用 PIL 生成文字图片（黑底金字），供匾额贴图使用。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return False
    img = Image.new("RGB", size, tuple(int(c * 255) for c in bg))
    d = ImageDraw.Draw(img)
    font = None
    for fp in ("C:/Windows/Fonts/simkai.ttf", "C:/Windows/Fonts/STKAITI.TTF",
               "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msyh.ttc"):
        try:
            font = ImageFont.truetype(fp, int(size[1] * 0.62))
            break
        except Exception:
            font = None
    if font is None:
        return False
    box = d.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    d.text(((size[0] - tw) / 2 - box[0], (size[1] - th) / 2 - box[1]), text,
           font=font, fill=tuple(int(c * 255) for c in fg))
    # 金色边框
    d.rectangle([6, 6, size[0] - 7, size[1] - 7], outline=tuple(int(c * 255) for c in fg), width=4)
    img.save(path)
    return True


def text_plane(name, text, loc, size, rot=(math.pi / 2, 0, math.pi), tex=None):
    """生成一个带文字的平面（图片贴图），正面朝 +Y。

    tex: 05_Blender/tex/ 下的贴图文件名；缺省时用 text 的哈希找。
    """
    tmp = os.path.join(TEX_DIR, tex) if tex else os.path.join(TEX_DIR, "plaque_gate.png")
    if not os.path.exists(tmp):
        return None

    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (size[0], size[1], 1)
    ob.rotation_euler = rot
    m = bpy.data.materials.new("TEX_" + name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(tmp)
    tex.location = (-400, 200)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.55
    bsdf.inputs["Metallic"].default_value = 0.15
    ob.data.materials.append(m)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return ob


def text3d(name, body, loc, material, size=0.6, rot=(math.pi / 2, 0, math.pi), extrude=0.04):
    """中文字（用 Blender 内置字体渲染，导出 GLB 后成为网格）"""
    try:
        bpy.ops.object.text_add(location=loc)
        ob = bpy.context.object
        ob.name = name
        ob.data.body = body
        ob.data.size = size
        ob.data.extrude = extrude
        ob.data.align_x = 'CENTER'
        ob.data.align_y = 'CENTER'
        ob.rotation_euler = rot
        # 找中文字体
        for fp in (
            "C:/Windows/Fonts/simkai.ttf",
            "C:/Windows/Fonts/STKAITI.TTF",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/msyh.ttc",
        ):
            if os.path.exists(fp):
                try:
                    ob.data.font = bpy.data.fonts.load(fp)
                except Exception:
                    pass
                break
        ob.data.materials.append(material)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.convert(target='MESH')
        return bpy.context.object
    except Exception as e:
        print("[warn] text3d fail", name, e)
        return None


def join_all(objs, name):
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.object
    ob.name = name
    return ob


# ------------------------------------------------------------------
# 材质
# ------------------------------------------------------------------
M_TILE = None
def build_materials():
    global M_TILE
    M_TILE = mat("Tile", (0.16, 0.17, 0.18), rough=0.87)
    mat("TileDark", (0.10, 0.11, 0.12), rough=0.9)
    mat("Wall", (0.85, 0.82, 0.75), rough=0.95)
    mat("WallDim", (0.72, 0.69, 0.63), rough=0.95)
    mat("Wood", (0.24, 0.13, 0.06), rough=0.8)
    mat("WoodLight", (0.46, 0.28, 0.14), rough=0.75)
    mat("Stone", (0.36, 0.38, 0.36), rough=0.95)
    mat("StoneDark", (0.22, 0.24, 0.23), rough=0.95)
    mat("Grass", (0.18, 0.30, 0.11), rough=1.0)
    mat("Water", (0.06, 0.22, 0.26), rough=0.1, metal=0.4)
    mat("Gold", (0.62, 0.44, 0.14), rough=0.4, metal=0.5)
    mat("Red", (0.35, 0.05, 0.03), rough=0.7)
    mat("Lantern", (0.60, 0.10, 0.04), rough=0.6, emit=(0.8, 0.2, 0.05))
    mat("Bamboo", (0.20, 0.34, 0.10), rough=0.85)
    mat("Leaf", (0.12, 0.26, 0.08), rough=0.9)
    mat("Plaque", (0.06, 0.09, 0.11), rough=0.6)


# ------------------------------------------------------------------
# 构件
# ------------------------------------------------------------------
def make_roof(group, w, d, h, x, y, z, overhang=1.0):
    """四坡庑殿顶 + 屋脊 + 瓦垄（用挤出三角+细条近似）"""
    objs = []
    W = w + overhang * 2
    D = d + overhang * 2
    # 主坡（用两个斜面楔形）
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z + h * 0.6))
    ob = bpy.context.object
    ob.scale = (W, D, h)          # size=1 立方体半边长 0.5 -> scale 即全尺寸
    ob.name = "roof_body"
    ob.data.materials.append(M_TILE)
    # 用 bmesh 把顶部收成脊
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    for v in bm.verts:
        if v.co.z > 0:
            v.co.x *= 0.06
    bm.to_mesh(me)
    bm.free()
    objs.append(ob)
    # 屋脊（贴合锥顶，宽度略窄于屋面）
    objs.append(cube("ridge", (W * 0.52, 0.26, 0.20), (x, y, z + h * 1.02), M_TILE))


    return objs


def make_gate():
    objs = []
    y = 17.6
    objs.append(cube("gate_base", (11, 3.4, 0.5), (0, y, 0.25), bpy.data.materials["Stone"]))
    for x in (-4.2, -1.4, 1.4, 4.2):
        objs.append(cyl("gate_col", 0.26, 4.0, (x, y - 0.4, 2.5), bpy.data.materials["Red"], verts=12))
    objs.append(cube("gate_beam", (10.4, 0.5, 0.42), (0, y - 0.5, 4.4), bpy.data.materials["Wood"]))
    objs.append(cube("gate_beam2", (10.8, 0.7, 0.28), (0, y - 0.5, 4.8), bpy.data.materials["Red"]))
    # 门叶（两扇，敞开）
    for s in (-1, 1):
        objs.append(cube("gate_leaf", (1.5, 0.12, 3.6), (s * 1.5, y - 1.2, 2.3),
                         bpy.data.materials["WoodLight"], rot=(0, 0, s * 0.9)))
    objs += make_roof(objs, 11.2, 3.4, 2.0, 0, y - 0.6, 5.0, 0.9)
    # 牌匾
    objs.append(cube("plaque_board", (3.6, 0.14, 1.05), (0, y + 0.1, 4.15), bpy.data.materials["Plaque"]))
    t = text_plane("plaque_text", "鰲台書院", (0, y + 0.22, 4.15), (3.3, 0.92), tex="plaque_gate.png")
    if t:
        objs.append(t)
    # 灯笼
    for s in (-1, 1):
        objs.append(sphere("lantern", 0.30, (s * 3.0, y - 0.2, 3.95), bpy.data.materials["Lantern"], scale=(1, 1, 1.3)))
    return objs


def make_lion(x, y, flip):
    objs = []
    S = bpy.data.materials["Stone"]
    SD = bpy.data.materials["StoneDark"]
    objs.append(cube("lion_base", (1.4, 1.6, 0.7), (x, y, 0.35), S))
    objs.append(cube("lion_base2", (1.2, 1.4, 0.22), (x, y, 0.81), SD))
    objs.append(sphere("lion_body", 0.62, (x, y, 1.45), S, scale=(0.85, 1.15, 1.0)))
    objs.append(sphere("lion_head", 0.46, (x, y + 0.36, 2.05), S))
    for i in range(9):
        a = (i / 9.0) * math.tau
        objs.append(sphere("mane_%d" % i, 0.15, (x + math.cos(a) * 0.44, y + 0.30 + math.sin(a) * 0.28, 2.12), SD, seg=8))
    for s in (-1, 1):
        objs.append(sphere("eye", 0.06, (x + s * 0.17, y + 0.76, 2.18), SD, seg=8))
        objs.append(cube("leg", (0.26, 0.3, 0.7), (x + s * 0.3, y + 0.55, 0.85), S))
    objs.append(sphere("ball", 0.22, (x + 0.3 * (1 if flip else -1), y + 0.95, 0.85), SD))
    return objs


def make_cloud_wall(x, y0, y1, segs=12):
    objs = []
    W = bpy.data.materials["Wall"]
    T = bpy.data.materials["Tile"]
    SD = bpy.data.materials["StoneDark"]
    WL = bpy.data.materials["Wood"]
    length = abs(y1 - y0)
    for i in range(segs):
        yc = y0 + (y1 - y0) * (i + 0.5) / segs
        h = 2.4 + math.sin((i / segs) * math.pi * 3.0) * 0.32
        objs.append(cube("wall_%d" % i, (0.5, length / segs + 0.02, h), (x, yc, h / 2), W))
        objs.append(cube("cap_%d" % i, (0.8, length / segs + 0.06, 0.16), (x, yc, h + 0.08), T))
    # 漏窗
    for t in (0.28, 0.72):
        yc = y0 + (y1 - y0) * t
        objs.append(cyl("win_ring", 0.66, 0.10, (x, yc, 1.75), SD, verts=24, rot=(0, math.pi / 2, 0)))
        for i in (-2, -1, 1, 2):
            objs.append(cube("win_bar", (0.06, 0.05, 1.15), (x + 0.02, yc + i * 0.22, 1.75), WL))
    return objs


def make_hall():
    objs = []
    y = -6.5
    S = bpy.data.materials["Stone"]
    Wl = bpy.data.materials["Wall"]
    WD = bpy.data.materials["Wood"]
    R = bpy.data.materials["Red"]
    # 台基 + 台阶
    objs.append(cube("hall_base", (18, 11, 0.7), (0, y, 0.35), S))
    for i in range(3):
        objs.append(cube("hall_step", (7, 0.65, 0.18), (0, 1.2 + i * 0.62, 0.09 + i * 0.18), S))
    # 墙体
    objs.append(cube("hall_back", (16, 0.5, 4.4), (0, y - 4.9, 2.9), Wl))
    for s in (-1, 1):
        objs.append(cube("hall_side", (0.5, 9.6, 4.4), (s * 7.8, y, 2.9), Wl))
    objs.append(cube("hall_front_l", (6.6, 0.5, 4.4), (-4.7, y + 4.8, 2.9), Wl))
    objs.append(cube("hall_front_r", (6.6, 0.5, 4.4), (4.7, y + 4.8, 2.9), Wl))
    objs.append(cube("hall_front_top", (2.9, 0.5, 1.0), (0, y + 4.8, 4.1), Wl))
    # 廊柱
    for x in (-6.2, -2.2, 2.2, 6.2):
        objs.append(cyl("hall_col", 0.27, 3.9, (x, y + 5.1, 2.65), R, verts=12))
        objs.append(cube("col_base", (0.9, 0.9, 0.16), (x, y + 5.1, 0.78), S))
    # 门
    for s in (-1, 1):
        objs.append(cube("hall_door", (1.3, 0.10, 3.4), (s * 1.45, y + 4.8, 2.4), WD))
    # 匾额 + 楹联
    objs.append(cube("hall_plaque", (2.8, 0.12, 0.82), (0, y + 5.05, 4.1), bpy.data.materials["Plaque"]))
    t = text_plane("hall_plaque_text", "講堂", (0, y + 5.02, 4.1), (2.6, 0.76), tex="plaque_hall.png")
    if t:
        objs.append(t)
    t1 = text_plane("couplet_l", "書聲琅琅傳嶺南", (-3.6, y + 5.06, 2.5), (0.5, 3.0), tex="couplet_l.png")
    if t1:
        objs.append(t1)
    t2 = text_plane("couplet_r", "文脈綿綿續鰲臺", (3.6, y + 5.06, 2.5), (0.5, 3.0), tex="couplet_r.png")
    if t2:
        objs.append(t2)
    # 檐 + 屋顶

    objs += make_roof(objs, 17.2, 10.4, 3.4, 0, y, 5.2, 1.2)
    # 室内地面
    objs.append(cube("hall_floor", (15, 9, 0.06), (0, y, 0.74), S))
    for s in (-1, 1):
        objs.append(sphere("hall_lantern", 0.3, (s * 5.4, y + 4.6, 4.3), bpy.data.materials["Lantern"], scale=(1, 1, 1.3)))
    return objs


# 工坊中心：放在院内东侧（云墙之内），从院子看得见
WORKSHOP_X, WORKSHOP_Y = 8.2, 9.5


def make_workshop():
    objs = []
    x, y = WORKSHOP_X, WORKSHOP_Y
    S = bpy.data.materials["Stone"]
    Wd = bpy.data.materials["WallDim"]
    # 台基与地面
    objs.append(cube("ws_base", (7, 8, 0.5), (x, y, 0.25), S))
    # 三面墙（正面敞开，做成作坊铺面）
    objs.append(cube("ws_wall_back", (6.2, 0.4, 3.4), (x, y + 3.4, 2.2), Wd))
    for s in (-1, 1):
        objs.append(cube("ws_wall_side", (0.4, 6.6, 3.4), (x + s * 2.9, y, 2.2), Wd))
    # 敞开的正面留两根柱子支撑
    for s in (-1, 1):
        objs.append(cyl("ws_col", 0.16, 3.4, (x + s * 2.7, y - 3.3, 2.2),
                        bpy.data.materials["Red"], verts=10))
    # 檐下横梁
    objs.append(cube("ws_beam", (6.4, 0.24, 0.26), (x, y - 3.3, 3.75),
                     bpy.data.materials["Wood"]))
    objs += make_roof(objs, 6.6, 7.6, 2.2, x, y, 4.0, 0.8)
    # 室内地面（略高一层）
    objs.append(cube("ws_floor", (5.8, 6.4, 0.08), (x, y, 0.54), S))
    return objs


def make_pavilion():
    objs = []
    x, y = -6.5, -13.5
    S = bpy.data.materials["Stone"]
    R = bpy.data.materials["Red"]
    objs.append(cube("pav_base", (4.6, 4.6, 0.4), (x, y, 0.2), S))
    for i in range(6):
        a = (i / 6.0) * math.tau
        objs.append(cyl("pav_col", 0.17, 3.0, (x + math.cos(a) * 1.55, y + math.sin(a) * 1.55, 1.9), R, verts=10))
    objs.append(cone("pav_roof", 2.9, 0.06, 1.7, (x, y, 4.2), bpy.data.materials["Tile"], verts=6))
    objs.append(sphere("pav_finial", 0.18, (x, y, 5.15), bpy.data.materials["Gold"], seg=10))
    objs.append(sphere("pav_lantern", 0.24, (x, y, 3.3), bpy.data.materials["Lantern"]))
    return objs


def make_landscape():
    objs = []
    G = bpy.data.materials["Grass"]
    S = bpy.data.materials["Stone"]
    SD = bpy.data.materials["StoneDark"]
    WA = bpy.data.materials["Water"]
    B = bpy.data.materials["Bamboo"]
    L = bpy.data.materials["Leaf"]
    # 地面
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    plane = bpy.context.object
    plane.name = "ground"
    plane.data.materials.append(G)
    # 中轴石板路
    objs.append(cube("road", (4.2, 34, 0.04), (0, 3.0, 0.02), S))
    objs.append(cube("yard", (14, 12, 0.03), (0, 9.5, 0.015), S))
    # 台阶（门外）
    for i in range(3):
        objs.append(cube("step", (8 - i * 0.6, 0.7, 0.16), (0, 19.2 + i * 0.6, 0.08 + i * 0.16), S))
    # 池塘
    objs.append(cyl("pond", 2.6, 0.12, (3.6, 10.5, 0.06), WA, verts=40))
    objs.append(cyl("pond_rim", 2.72, 0.18, (3.6, 10.5, 0.09), SD, verts=40))
    # 假山
    for i, (px, py, pz, sc) in enumerate(((-4.2, 10.2, 0.9, 1.4), (-5.1, 9.1, 0.7, 1.0),
                                          (-3.5, 9.4, 0.5, 0.8), (-4.6, 9.8, 1.7, 0.6))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.9, location=(px, py, pz))
        ob = bpy.context.object
        ob.name = "rock_%d" % i
        ob.scale = (sc, sc * 0.9, sc * 0.85)
        ob.rotation_euler = (random.random(), random.random(), random.random())
        ob.data.materials.append(SD)
        objs.append(ob)
    # 竹
    for cx, cy, n in ((-6.4, 6.2, 9), (6.6, 6.6, 7), (-5.6, -8.2, 6), (7.4, -4.0, 5)):
        for i in range(n):
            h = 3.2 + random.random() * 2.2
            bx = cx + (random.random() - 0.5) * 1.8
            by = cy + (random.random() - 0.5) * 1.8
            objs.append(cyl("bamboo_%d_%d" % (int(cx * 10), i), 0.065, h, (bx, by, h / 2), B, verts=6))
            for k in range(4):
                objs.append(cube("leaf", (0.85, 0.22, 0.02),
                                 (bx + random.uniform(-0.5, 0.5), by + random.uniform(-0.5, 0.5),
                                  h * (0.6 + random.random() * 0.35)), L, rot=(random.random(), random.random(), random.random())))
    # 树
    WD = bpy.data.materials["Wood"]
    for tx, ty, s in ((-12, 6, 1.2), (12.5, 7, 1.1), (-11, -6, 1.0), (11.5, -9, 1.15)):
        objs.append(cyl("trunk", 0.22 * s, 2.6 * s, (tx, ty, 1.3 * s), WD, verts=8))
        for i in range(5):
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=(0.95 - i * 0.1) * s,
                                                  location=(tx + random.uniform(-0.6, 0.6), ty + random.uniform(-0.6, 0.6), (2.4 + random.random() * 1.2) * s))
            ob = bpy.context.object
            ob.name = "foliage"
            ob.data.materials.append(mat("Foliage%d" % (i % 3), (0.14 + i * 0.02, 0.30 + i * 0.02, 0.10), rough=0.95))
            objs.append(ob)
    return objs


# ------------------------------------------------------------------
def build():
    purge()
    build_materials()
    all_objs = []
    all_objs += make_landscape()
    all_objs += make_gate()
    all_objs += make_lion(-2.6, 16.3, 1)
    all_objs += make_lion(2.6, 16.3, 0)
    all_objs += make_cloud_wall(-8.4, 7.5, 15.5)
    all_objs += make_cloud_wall(8.4, 7.5, 15.5)
    all_objs += make_hall()
    all_objs += make_workshop()
    all_objs += make_pavilion()

    # 扩建：工坊内部与院落陈设（织机 / 染缸 / 草编工位 / 石桌）
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import workshop_detail
        all_objs += workshop_detail.build_workshop_detail()
        print("[build] workshop detail added")
    except Exception as e:
        print("[build] workshop detail FAILED:", e)

    # 合并成一个对象（减少 draw call，含地面）
    scene_objs = [o for o in bpy.data.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in scene_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = scene_objs[0]
    bpy.ops.object.join()
    joined = bpy.context.object
    joined.name = "AotaiAcademy"

    # 清空变换：所有顶点已在世界坐标，导出即无节点位移
    joined.rotation_euler = (0, 0, 0)
    joined.location = (0, 0, 0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # 法定法线
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    DEBUG_DUMP = os.environ.get("AOTAI_DEBUG_DUMP")
    if DEBUG_DUMP:
        for o in bpy.data.objects:
            if o.type != 'MESH':
                continue
            bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
            xs = [v.x for v in bb]; zs = [v.z for v in bb]; ys = [v.y for v in bb]
            ex = max(xs) - min(xs); ez = max(zs) - min(zs); ey = max(ys) - min(ys)
            if max(zs) > 6.0 and ex > 6.0 and ez < 0.6:
                print("[SUSPECT] %s  size=(%.2f,%.2f,%.2f) z=[%.2f,%.2f] y=%.2f" % (o.name, ex, ey, ez, min(zs), max(zs), (min(ys)+max(ys))/2))

    print("[build] objects:", len(bpy.data.objects), "verts:", len(joined.data.vertices), "polys:", len(joined.data.polygons))

    # 导出 GLB（已在上面应用 180° Z 旋转：Blender +Y(前) -> glTF +Z）
    bpy.ops.object.select_all(action='SELECT')
    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=OUT_GLB,
        export_format='GLB',
        use_selection=False,
        export_yup=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_materials='EXPORT',
    )
    size = os.path.getsize(OUT_GLB)
    print("[build] GLB written: %s (%.2f MB)" % (OUT_GLB, size / 1048576.0))


if __name__ == "__main__":
    build()
