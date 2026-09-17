import adsk.core, adsk.fusion, json, math, os

ROOT = '/Users/daiki/Projects/sage60'
SIMPLIFY_EPS = 1.5
LOWER_OUTER_OFFSET = 2.8
UPPER_OUTER_OFFSET = 4.2
SKIRT_INNER_OFFSET = 3.1
PLATE_CLEARANCE = 0.5
LOWER_HEIGHT = 8.0
LOWER_FLOOR = 2.5
UPPER_FRAME_BOTTOM = 7.9
UPPER_FRAME_TOP = 11.6
SKIRT_BOTTOM = 6.4
SKIRT_TOP = 8.1
MAGNET_HOLE_RADIUS = 1.7
MAGNET_DEPTH = 2.2
MAGNET_EDGE_INSET = 0.8

# The plate deliberately opens the controller edge of each PCB.  The first
# case revision used a convex outer silhouette, which filled that opening in
# the case.  Keep the opening as a simple rectangular service bay so the
# XIAO module, its USB side, and the battery JST have a defined clearance.
# Coordinates are PCB mm (X right, Y down); each rectangle extends past the
# case silhouette on the open side.
CONTROL_BAY = {
    'left': (167.5, 22.0, 202.0, 61.0),
    'right': (43.5, 25.0, 78.5, 61.0),
}
CASE_REVISION = 'v3'

def point(x, y):
    return adsk.core.Point3D.create(x, y, 0)

def pcb_to_cad(x, y):
    return (x / 10.0, -y / 10.0)

def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

def point_in_polygon(q, poly):
    x, y = q
    inside = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside

def convex_hull(points):
    pts = sorted(set((round(x, 5), round(y, 5)) for x, y in points))
    lower = []
    for q in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(q)
    upper = []
    for q in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(q)
    return lower[:-1] + upper[:-1]

def rdp(poly, epsilon):
    a, b = poly[0], poly[-1]
    def distance(q):
        x, y = a
        X, Y = b
        dx, dy = X - x, Y - y
        if dx == 0 and dy == 0:
            return math.hypot(q[0] - x, q[1] - y)
        t = max(0, min(1, ((q[0] - x) * dx + (q[1] - y) * dy) / (dx * dx + dy * dy)))
        return math.hypot(q[0] - (x + t * dx), q[1] - (y + t * dy))
    if len(poly) <= 2:
        return poly
    k = max(range(1, len(poly) - 1), key=lambda i: distance(poly[i]))
    if distance(poly[k]) > epsilon:
        return rdp(poly[:k + 1], epsilon)[:-1] + rdp(poly[k:], epsilon)
    return [a, b]

def simple_outline(ring):
    hull = convex_hull(ring[:-1] if ring[0] == ring[-1] else ring)
    simple = rdp(hull + [hull[0]], SIMPLIFY_EPS)[:-1]
    if len(simple) < 8:
        raise RuntimeError('simplified outline is too small')
    return simple

def make_polygon_sketch(root, name, poly, plane):
    sk = root.sketches.add(plane)
    sk.name = name
    lines = sk.sketchCurves.sketchLines
    for a, b in zip(poly, poly[1:] + poly[:1]):
        ax, ay = pcb_to_cad(a[0], a[1])
        bx, by = pcb_to_cad(b[0], b[1])
        lines.addByTwoPoints(point(ax, ay), point(bx, by))
    return sk

def make_offset_sketch(root, name, poly, plane, offset_mm):
    source = make_polygon_sketch(root, name + '_SOURCE', poly, plane)
    profile = source.profiles.item(0)
    box = profile.boundingBox
    curves = adsk.core.ObjectCollection.create()
    loop = profile.profileLoops.item(0)
    for i in range(loop.profileCurves.count):
        curves.add(loop.profileCurves.item(i).sketchEntity)
    outside = adsk.core.Point3D.create(box.minPoint.x - 1, box.minPoint.y - 1, 0)
    result = source.offset(curves, outside, offset_mm / 10.0)
    if not result or result.count < 1:
        raise RuntimeError('offset failed: ' + name)
    target = root.sketches.add(plane)
    target.name = name
    projected = target.project2([entity for entity in result], False)
    if not projected or len(projected) < 1 or target.profiles.count < 1:
        raise RuntimeError('projection failed: ' + name)
    source.isVisible = False
    target.isVisible = False
    return target

def make_exact_offset_sketch(root, name, ring, plane, offset_mm):
    poly = ring[:-1] if ring[0] == ring[-1] else ring
    return make_offset_sketch(root, name, poly, plane, offset_mm)

def new_body_from_profile(root, sketch, distance_mm, name):
    feature = root.features.extrudeFeatures.addSimple(
        sketch.profiles.item(0),
        adsk.core.ValueInput.createByReal(distance_mm / 10.0),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    feature.name = name
    body = root.bRepBodies.item(root.bRepBodies.count - 1)
    body.name = name
    return body

def cut_body(root, sketch, distance_mm, body, name):
    extrudes = root.features.extrudeFeatures
    input_obj = extrudes.createInput(
        sketch.profiles.item(0),
        adsk.fusion.FeatureOperations.CutFeatureOperation)
    input_obj.setDistanceExtent(False, adsk.core.ValueInput.createByReal(distance_mm / 10.0))
    input_obj.participantBodies = [body]
    feature = extrudes.add(input_obj)
    feature.name = name
    return feature

def combine_join(root, target, tool, name):
    tools = adsk.core.ObjectCollection.create()
    tools.add(tool)
    input_obj = root.features.combineFeatures.createInput(target, tools)
    input_obj.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
    input_obj.isKeepToolBodies = False
    feature = root.features.combineFeatures.add(input_obj)
    feature.name = name
    return target

def offset_plane(root, z_mm):
    input_obj = root.constructionPlanes.createInput()
    input_obj.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(z_mm / 10.0))
    return root.constructionPlanes.add(input_obj)

def circle_cut(root, plane, x_mm, y_mm, radius_mm, distance_mm, body, name):
    sketch = root.sketches.add(plane)
    sketch.name = name + '_SKETCH'
    sketch.sketchCurves.sketchCircles.addByCenterRadius(
        point(x_mm / 10.0, -y_mm / 10.0), radius_mm / 10.0)
    cut_body(root, sketch, distance_mm, body, name)
    sketch.isVisible = False

def rectangle_cut(root, plane, bounds_mm, distance_mm, body, name):
    x0, y0, x1, y1 = bounds_mm
    sketch = root.sketches.add(plane)
    sketch.name = name + '_SKETCH'
    lines = sketch.sketchCurves.sketchLines
    corners = [
        point(x0 / 10.0, -y0 / 10.0),
        point(x1 / 10.0, -y0 / 10.0),
        point(x1 / 10.0, -y1 / 10.0),
        point(x0 / 10.0, -y1 / 10.0),
    ]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        lines.addByTwoPoints(a, b)
    cut_body(root, sketch, distance_mm, body, name)
    sketch.isVisible = False

def magnet_points(simple, plate_ring, edge_indices):
    area = sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(simple, simple[1:] + simple[:1]))
    result = []
    for index in edge_indices:
        a = simple[index]
        b = simple[(index + 1) % len(simple)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        nx, ny = ((dy / length, -dx / length) if area > 0 else (-dy / length, dx / length))
        q = ((a[0] + b[0]) / 2 + nx * MAGNET_EDGE_INSET,
             (a[1] + b[1]) / 2 + ny * MAGNET_EDGE_INSET)
        if point_in_polygon(q, plate_ring):
            raise RuntimeError('magnet point is inside plate outline: ' + str(q))
        result.append(q)
    return result

def oriented_rectangle(sketch, center, tangent, normal, width_mm, height_mm):
    cx, cy = center[0] / 10.0, center[1] / 10.0
    width, height = width_mm / 10.0, height_mm / 10.0
    corners = []
    for a, b in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        corners.append(point(
            cx + tangent[0] * a * width / 2 + normal[0] * b * height / 2,
            cy + tangent[1] * a * width / 2 + normal[1] * b * height / 2))
    for i in range(4):
        sketch.sketchCurves.sketchLines.addByTwoPoints(corners[i], corners[(i + 1) % 4])

def build_case(side, geometry_path, interface_path, stem, magnet_edges):
    app = adsk.core.Application.get()
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType, True)
    design = adsk.fusion.Design.cast(document.products.itemByProductType('DesignProductType'))
    root = design.rootComponent
    geometry = json.load(open(geometry_path))
    plate_ring = geometry['rings_pcb_mm'][0]
    simple = simple_outline(plate_ring)
    interface = json.load(open(interface_path))
    supports = interface['supports'][side]
    xy = root.xYConstructionPlane

    lower_outer = make_offset_sketch(root, side.upper() + '_LOWER_OUTER', simple, xy, LOWER_OUTER_OFFSET)
    lower = new_body_from_profile(root, lower_outer, LOWER_HEIGHT, side.upper() + '_LOWER_CASE')
    lower_cavity = make_exact_offset_sketch(root, side.upper() + '_LOWER_CAVITY', plate_ring, xy, PLATE_CLEARANCE)
    cut_body(root, lower_cavity, LOWER_HEIGHT - LOWER_FLOOR, lower, side.upper() + '_LOWER_CAVITY_CUT')

    # The lower half receives a full-height service bay.  The controller and
    # the B.Cu battery JST sit at the open PCB edge, so leaving a lower-case
    # wall above the floor would still trap the assembly.  The rectangular
    # bay opens only the already-unused controller edge; gasket supports and
    # magnet bosses remain outside it.
    rectangle_cut(root, xy, CONTROL_BAY[side], LOWER_HEIGHT, lower,
                  side.upper() + '_LOWER_CONTROL_BAY_CUT')

    for entry in supports:
        center = entry['pad_center_cad_mm']
        tangent = (entry['tangent_pcb'][0], -entry['tangent_pcb'][1])
        normal = (entry['outward_normal_pcb'][0], -entry['outward_normal_pcb'][1])
        pad_sketch = root.sketches.add(xy)
        pad_sketch.name = side.upper() + '_LOWER_GASKET_' + entry['id']
        oriented_rectangle(pad_sketch, center, tangent, normal,
                           entry['pad_size_mm'][0], entry['pad_size_mm'][1])
        pad = new_body_from_profile(root, pad_sketch, LOWER_HEIGHT,
                                    side.upper() + '_LOWER_GASKET_' + entry['id'])
        combine_join(root, lower, pad, side.upper() + '_LOWER_JOIN_' + entry['id'])
        pad_sketch.isVisible = False

    if side == 'right':
        circle_cut(root, xy, 160.995, 114.535, 18.5, LOWER_HEIGHT, lower, 'RIGHT_LOWER_TRACKBALL_CUT')
        lip_sketch = root.sketches.add(xy)
        lip_sketch.name = 'RIGHT_LOWER_TRACKBALL_LIP_SKETCH'
        lip_sketch.sketchCurves.sketchCircles.addByCenterRadius(point(16.0995, -11.4535), 2.10)
        lip_sketch.sketchCurves.sketchCircles.addByCenterRadius(point(16.0995, -11.4535), 1.85)
        lip = new_body_from_profile(root, lip_sketch, 2.0, 'RIGHT_LOWER_TRACKBALL_LIP')
        combine_join(root, lower, lip, 'RIGHT_LOWER_TRACKBALL_JOIN')
        lip_sketch.isVisible = False

    magnets = magnet_points(simple, plate_ring, magnet_edges)
    lower_plane = offset_plane(root, LOWER_HEIGHT)
    for index, (x, y) in enumerate(magnets, 1):
        circle_cut(root, lower_plane, x, y, MAGNET_HOLE_RADIUS,
                   -MAGNET_DEPTH, lower, 'LOWER_MAGNET_' + str(index))

    base = os.path.join(ROOT, 'mechanical/gasket_v1')
    manager = design.exportManager
    bottom_stl = os.path.join(base, stem + '_bottom.stl')
    bottom_step = os.path.join(base, stem + '_bottom.step')
    bottom_stl_ok = manager.execute(manager.createSTLExportOptions(lower, bottom_stl))
    bottom_step_ok = manager.execute(manager.createSTEPExportOptions(bottom_step, root))

    skirt_plane = offset_plane(root, SKIRT_BOTTOM)
    skirt_outer = make_offset_sketch(root, side.upper() + '_UPPER_SKIRT_OUTER', simple, skirt_plane, UPPER_OUTER_OFFSET)
    skirt_inner = make_offset_sketch(root, side.upper() + '_UPPER_SKIRT_INNER', simple, skirt_plane, SKIRT_INNER_OFFSET)
    skirt = new_body_from_profile(root, skirt_outer, SKIRT_TOP - SKIRT_BOTTOM, side.upper() + '_UPPER_SKIRT')
    cut_body(root, skirt_inner, SKIRT_TOP - SKIRT_BOTTOM, skirt, side.upper() + '_UPPER_SKIRT_INNER_CUT')

    frame_plane = offset_plane(root, UPPER_FRAME_BOTTOM)
    frame_outer = make_offset_sketch(root, side.upper() + '_UPPER_FRAME_OUTER', simple, frame_plane, UPPER_OUTER_OFFSET)
    frame_inner = make_exact_offset_sketch(root, side.upper() + '_UPPER_KEY_OPENING', plate_ring, frame_plane, PLATE_CLEARANCE)
    upper = new_body_from_profile(root, frame_outer, UPPER_FRAME_TOP - UPPER_FRAME_BOTTOM, side.upper() + '_UPPER_FRAME')
    cut_body(root, frame_inner, UPPER_FRAME_TOP - UPPER_FRAME_BOTTOM, upper, side.upper() + '_UPPER_KEY_OPENING_CUT')
    combine_join(root, upper, skirt, side.upper() + '_UPPER_SKIRT_JOIN')
    upper.name = side.upper() + '_UPPER_CASE'

    # The XIAO module is on F.Cu, so the upper half also needs a through
    # window.  Starting at the skirt plane clears both the skirt and the
    # upper frame in one feature and leaves a simple, printable rectangular
    # opening at the controller edge.
    rectangle_cut(root, skirt_plane, CONTROL_BAY[side],
                  UPPER_FRAME_TOP - SKIRT_BOTTOM, upper,
                  side.upper() + '_UPPER_CONTROL_WINDOW_CUT')

    upper_plane = offset_plane(root, UPPER_FRAME_BOTTOM)
    for index, (x, y) in enumerate(magnets, 1):
        circle_cut(root, upper_plane, x, y, MAGNET_HOLE_RADIUS,
                   MAGNET_DEPTH, upper, 'UPPER_MAGNET_' + str(index))
    for sketch in root.sketches:
        sketch.isVisible = False

    top_stl = os.path.join(base, stem + '_top.stl')
    complete_step = os.path.join(base, stem + '_complete.step')
    top_stl_ok = manager.execute(manager.createSTLExportOptions(upper, top_stl))
    complete_step_ok = manager.execute(manager.createSTEPExportOptions(complete_step, root))
    document.activate()
    app.activeViewport.fit()
    screenshot = '/tmp/' + stem + '_assembled.png'
    screenshot_ok = app.activeViewport.saveAsImageFile(screenshot, 1600, 1000)
    return {
        'side': side,
        'simpleEdges': len(simple),
        'magnetPointsPcbMm': magnets,
        'bodies': [body.name for body in root.bRepBodies],
        'bottomStl': bool(bottom_stl_ok),
        'bottomStep': bool(bottom_step_ok),
        'topStl': bool(top_stl_ok),
        'completeStep': bool(complete_step_ok),
        'screenshot': screenshot,
        'screenshotSaved': bool(screenshot_ok)
    }

def run(_context):
    base = ROOT
    results = []
    results.append(build_case(
        'left',
        os.path.join(base, 'pcb/mx_plate/gasket_v1/mx_plate_gasket_geometry.json'),
        os.path.join(base, 'mechanical/gasket_v1/case_interface.json'),
        'sage60_left_case_' + CASE_REVISION,
        [0, 3, 5, 9]))
    results.append(build_case(
        'right',
        os.path.join(base, 'pcb/mx_plate_right_tb/gasket_v1/mx_plate_right_tb_gasket_geometry.json'),
        os.path.join(base, 'mechanical/gasket_v1/case_interface.json'),
        'sage60_right_tb_case_' + CASE_REVISION,
        [0, 2, 5, 7]))
    print(json.dumps(results))
