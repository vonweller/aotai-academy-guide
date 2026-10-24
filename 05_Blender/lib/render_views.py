import bpy
import json
import math
import mathutils
import os
from bpy_extras.object_utils import world_to_camera_view

# This script consumes the GLB only; it never rebuilds or overwrites it.
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_GLB = os.path.join(BASE, 'out', 'aotai_academy.glb')
# Tests can point at a temporary candidate; the default remains the tracked GLB.
GLB = os.environ.get('AOTAI_GLB', DEFAULT_GLB)
DEFAULT_OUT = os.path.join(BASE, 'qc')
# Tests can render to a temporary directory; default project QC path is unchanged.
OUT = os.environ.get('AOTAI_QC_OUT', DEFAULT_OUT)
DRY_RUN = os.environ.get('AOTAI_RENDER_DRY_RUN', '0') == '1'

if not os.path.isfile(GLB):
    raise FileNotFoundError('GLB not found: %s' % GLB)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
sc = bpy.context.scene
mesh_objects = [ob for ob in bpy.data.objects if ob.type == 'MESH']
if not mesh_objects:
    raise RuntimeError('GLB contains no mesh objects')
bpy.context.view_layer.update()

# Blender 4.3+ renamed the Eevee engine; keep the QC script portable.
for engine in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        sc.render.engine = engine
        break
    except (TypeError, ValueError):
        continue
else:
    raise RuntimeError('No Eevee render engine is available')
sc.render.resolution_x = 1600
sc.render.resolution_y = 1000
if hasattr(sc, 'eevee') and hasattr(sc.eevee, 'taa_render_samples'):
    sc.eevee.taa_render_samples = 96

w = bpy.data.worlds.new('AotaiRenderWorld')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes.get('Background')
if bg is None:
    raise RuntimeError('world Background node is missing')
bg.inputs[0].default_value = (0.60, 0.74, 0.92, 1)
bg.inputs[1].default_value = 1.4
bpy.ops.object.light_add(type='SUN', location=(20, -52, 46))
sun = bpy.context.object
sun.data.energy = 4.5
sun.rotation_euler = (math.radians(38), math.radians(10), math.radians(18))
bpy.ops.object.light_add(type='AREA', location=(-24, -28, 22))
fill = bpy.context.object
fill.data.energy = 1000
fill.data.size = 30
bpy.ops.object.camera_add(location=(0, 0, 5))
cam = bpy.context.object
sc.camera = cam


def _bbox(points):
    if not points:
        raise RuntimeError('cannot compute bbox: no points')
    mins = [min(float(point[i]) for point in points) for i in range(3)]
    maxs = [max(float(point[i]) for point in points) for i in range(3)]
    return {
        'min': [round(value, 6) for value in mins],
        'max': [round(value, 6) for value in maxs],
        'dims': [round(maxs[i] - mins[i], 6) for i in range(3)],
    }


def _poly_material_name(ob, poly):
    if poly.material_index >= len(ob.data.materials):
        return None
    material = ob.data.materials[poly.material_index]
    return material.name if material else None


def _points_for_materials(material_names):
    names = set(material_names)
    points = []
    for ob in mesh_objects:
        for poly in ob.data.polygons:
            if _poly_material_name(ob, poly) not in names:
                continue
            points.extend(ob.matrix_world @ ob.data.vertices[index].co for index in poly.vertices)
    return points


def _scene_points():
    # Grass is the 80 m ground plane and would make every detail shot fail coverage.
    points = []
    for ob in mesh_objects:
        for poly in ob.data.polygons:
            if _poly_material_name(ob, poly) == 'Grass':
                continue
            points.extend(ob.matrix_world @ ob.data.vertices[index].co for index in poly.vertices)
    return points


scene_points = _scene_points()
scene_bbox = _bbox(scene_points)
print('[render][scene_bbox] ' + json.dumps(scene_bbox, sort_keys=True))


def _target_region(name, target, material_names):
    points = _points_for_materials(material_names)
    if not points:
        raise RuntimeError('%s target materials missing: %s' % (name, ','.join(material_names)))
    region_bbox = _bbox(points)
    margin = 0.25
    if any(target[i] < region_bbox['min'][i] - margin or
           target[i] > region_bbox['max'][i] + margin for i in range(3)):
        raise RuntimeError(
            '%s target %s is outside material bbox %s; stale GLB or wrong source coordinates'
            % (name, tuple(round(float(value), 3) for value in target), region_bbox)
        )
    return region_bbox, points


def _coverage(points):
    bpy.context.view_layer.update()
    coords = [world_to_camera_view(sc, cam, point) for point in points]
    behind = sum(1 for coord in coords if float(coord.z) <= 0.0)
    xs = [float(coord.x) for coord in coords]
    ys = [float(coord.y) for coord in coords]
    worst = max(
        max(abs(2.0 * value - 1.0) for value in xs),
        max(abs(2.0 * value - 1.0) for value in ys),
    )
    return {
        'ndc_x': [round(min(xs), 5), round(max(xs), 5)],
        'ndc_y': [round(min(ys), 5), round(max(ys), 5)],
        'worst_ndc': round(worst, 5),
        'behind_camera': behind,
        'points': len(points),
    }


receipts = []


def shot(name, pos, tgt, lens, target_materials=None):
    target = mathutils.Vector(tgt)
    if target_materials:
        target_bbox, coverage_points = _target_region(name, target, target_materials)
    else:
        target_bbox, coverage_points = scene_bbox, scene_points
        if any(target[i] < target_bbox['min'][i] - 0.25 or
               target[i] > target_bbox['max'][i] + 0.25 for i in range(3)):
            raise RuntimeError('%s overview target %s is outside scene bbox %s' %
                               (name, tuple(target), target_bbox))
    cam.location = mathutils.Vector(pos)
    direction = target - cam.location
    if direction.length <= 1e-6:
        raise RuntimeError('%s camera and target coincide' % name)
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    coverage = _coverage(coverage_points)
    if coverage['behind_camera'] or coverage['worst_ndc'] > 1.0:
        raise RuntimeError('%s camera coverage failed: %s' % (name, coverage))
    receipt = {
        'name': name,
        'source_space': 'Blender Z-up, +Y front',
        'position': [round(float(value), 4) for value in pos],
        'target': [round(float(value), 4) for value in tgt],
        'lens': lens,
        'target_bbox': target_bbox,
        'coverage': coverage,
    }
    receipts.append(receipt)
    print('[render][receipt] ' + json.dumps(receipt, sort_keys=True))
    if not DRY_RUN:
        os.makedirs(OUT, exist_ok=True)
        sc.render.filepath = os.path.join(OUT, name + '.png')
        bpy.ops.render.render(write_still=True)
        print('[render]', name)


# Source-scene coordinates: the gate faces +Y, the hall entrance faces +Y,
# and the workshop is open on its -Y side. These are not stale shifted-GLB targets.
WORKSHOP_MATERIALS = (
    'WsWood', 'WsCloth', 'WsClothBrown', 'WsPot', 'WsIndigo',
    'WsWoodLight', 'WsStraw', 'WsRope', 'WsGreen',
)
LOOM_MATERIALS = ('WsLoomWood', 'WsLoomWoodLight', 'WsLoomRope', 'WsLoomCloth')
HALL_INSIDE_MATERIALS = (
    'HiWood', 'HiWoodLight', 'HiPaper', 'HiCloth', 'HiBronze', 'HiCandle',
)
GATE_MATERIALS = ('TEX_plaque_text',)
# Close view through the open -Y frontage; unique loom materials keep the target tight.
shot('render_workshop', (9.4, 4.7, 1.65), (10.0, 10.85, 1.3), 52, LOOM_MATERIALS)
shot('render_workshop_wide', (9.65, -3.0, 2.6), (9.65, 10.8, 1.25), 24, WORKSHOP_MATERIALS)
shot('render_gate', (0.0, 34.0, 4.0), (0.0, 17.82, 4.15), 36, GATE_MATERIALS)
shot('render_hall_inside', (0.0, 3.0, 2.8), (0.0, -6.5, 1.6), 24, HALL_INSIDE_MATERIALS)
# Primary overview from the +Y entrance side; retain the former rear view for comparison.
shot('render_overview', (22.0, 50.0, 28.0), (0.0, 2.0, 2.5), 45)
shot('render_overview_back', (38.0, -50.0, 30.0), (0.0, 0.0, 2.5), 45)
print('HEADLESS ' + json.dumps({
    'ok': True,
    'dry_run': DRY_RUN,
    'scene_bbox': scene_bbox,
    'shots': receipts,
}, sort_keys=True))
