"""Replace the imported, tessellated plate sketches with native line/arc geometry."""

import adsk.core
import adsk.fusion
import json
import math

ROOT = '/Users/daiki/Projects/sage60'
LEFT_GEOMETRY = ROOT + '/pcb/mx_plate/gasket_v1/mx_plate_gasket_geometry.json'
RIGHT_GEOMETRY = ROOT + '/pcb/mx_plate_right_tb/gasket_v1/mx_plate_right_tb_gasket_geometry.json'


def pt(x, y):
    # Source geometry is PCB coordinates (X right, Y down); Fusion is Y up.
    return adsk.core.Point3D.create(x / 10.0, -y / 10.0, 0)


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def line_residual(points):
    if len(points) < 3:
        return 0.0
    a, b = points[0], points[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 1e-12:
        return max(distance(q, a) for q in points)
    return max(abs(dx * (a[1] - q[1]) - (a[0] - q[0]) * dy) / length for q in points)


def circle_from_three(a, b, c):
    ax, ay = a
    bx, by = b
    cx, cy = c
    det = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(det) < 1e-12:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / det
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / det
    return (ux, uy, math.hypot(ax - ux, ay - uy))


def circle_residual(points):
    if len(points) < 3:
        return 1e9, None
    circle = circle_from_three(points[0], points[len(points) // 2], points[-1])
    if circle is None:
        return 1e9, None
    cx, cy, radius = circle
    return max(abs(distance(q, (cx, cy)) - radius) for q in points), circle


def turn_angles(points):
    values = []
    for i in range(1, len(points) - 1):
        a, b, c = points[i - 1], points[i], points[i + 1]
        vx, vy = b[0] - a[0], b[1] - a[1]
        wx, wy = c[0] - b[0], c[1] - b[1]
        values.append(math.degrees(math.atan2(vx * wy - vy * wx, vx * wx + vy * wy)))
    return values


def is_arc(points, tolerance):
    if len(points) < 5:
        return False
    residual, _ = circle_residual(points)
    if residual > tolerance:
        return False
    turns = turn_angles(points)
    # A line/line junction can be fitted by a circle through only a few points.
    # Require a consistent, nonzero turn through the complete candidate.
    if any(abs(turn) <= 0.5 for turn in turns):
        return False
    if min(turns) < -0.5 < max(turns):
        return False
    return max(turns) - min(turns) <= 6.0


def fit_ring(points, tolerance=0.03):
    """Split a tessellated ring into straight runs and circular runs."""
    source = points[:-1] if distance(points[0], points[-1]) < 1e-9 else list(points)
    count = len(source)
    edge_lengths = [distance(source[i], source[(i + 1) % count]) for i in range(count)]
    anchor = (max(range(count), key=lambda i: edge_lengths[i]) + 1) % count
    sequence = [source[(anchor + i) % count] for i in range(count + 1)]
    segments = []
    i = 0
    while i < count:
        best = i + 1
        kind = 'line'
        for k in range(i + 1, min(count, i + 180) + 1):
            candidate = sequence[i:k + 1]
            if line_residual(candidate) <= tolerance:
                candidate_kind = 'line'
            elif is_arc(candidate, tolerance):
                candidate_kind = 'arc'
            else:
                break
            best = k
            kind = candidate_kind
        mid = sequence[(i + best) // 2]
        segments.append((sequence[i], mid, sequence[best], kind))
        i = best
    return segments


def add_line(sketch, a, b):
    return sketch.sketchCurves.sketchLines.addByTwoPoints(pt(a[0], a[1]), pt(b[0], b[1]))


def add_arc(sketch, a, mid, b):
    return sketch.sketchCurves.sketchArcs.addByThreePoints(pt(a[0], a[1]), pt(mid[0], mid[1]), pt(b[0], b[1]))


def rotated(local, center, angle):
    ca, sa = math.cos(angle), math.sin(angle)
    return (center[0] + local[0] * ca - local[1] * sa,
            center[1] + local[0] * sa + local[1] * ca)


def add_rounded_switch(sketch, center, angle_degrees, half=7.0, radius=0.25):
    """Add a 14 mm switch opening as four lines and four R0.25 arcs."""
    theta = -math.radians(angle_degrees)
    h = half
    r = radius
    # Traversal is in the same PCB coordinate frame used by the source plate.
    points = [(-h + r, -h), (h - r, -h), (h, -h + r),
              (h, h - r), (h - r, h), (-h + r, h),
              (-h, h - r), (-h, -h + r)]
    centers = [(h - r, -h + r), (h - r, h - r),
               (-h + r, h - r), (-h + r, -h + r)]
    mids = [(h - r + r / math.sqrt(2), -h + r - r / math.sqrt(2)),
            (h - r + r / math.sqrt(2), h - r + r / math.sqrt(2)),
            (-h + r - r / math.sqrt(2), h - r + r / math.sqrt(2)),
            (-h + r - r / math.sqrt(2), -h + r - r / math.sqrt(2))]
    points = [rotated(q, center, theta) for q in points]
    mids = [rotated(q, center, theta) for q in mids]
    add_line(sketch, points[0], points[1])
    add_arc(sketch, points[1], mids[0], points[2])
    add_line(sketch, points[2], points[3])
    add_arc(sketch, points[3], mids[1], points[4])
    add_line(sketch, points[4], points[5])
    add_arc(sketch, points[5], mids[2], points[6])
    add_line(sketch, points[6], points[7])
    add_arc(sketch, points[7], mids[3], points[0])


def make_sketch(root, geometry_path, sketch_name):
    geometry = json.load(open(geometry_path))
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = sketch_name

    outer_segments = fit_ring(geometry['rings_pcb_mm'][0])
    for start, middle, end, kind in outer_segments:
        if kind == 'arc':
            add_arc(sketch, start, middle, end)
        else:
            add_line(sketch, start, end)

    for switch in geometry['switches']:
        add_rounded_switch(sketch, tuple(switch['at']), switch.get('angle', 0.0))
    sketch.isVisible = True
    return sketch, len(outer_segments)


def run(_context):
    app = adsk.core.Application.get()
    targets = [
        ('sage60_left_plate_surface', LEFT_GEOMETRY, 'LEFT_PLATE_SURFACE'),
        ('sage60_right_tb_plate_surface', RIGHT_GEOMETRY, 'RIGHT_TB_PLATE_SURFACE'),
    ]
    result = []
    for doc_name, geometry_path, sketch_name in targets:
        doc = None
        for i in range(app.documents.count):
            candidate = app.documents.item(i)
            if candidate.name == doc_name:
                doc = candidate
                break
        if doc is None:
            result.append({'document': doc_name, 'error': 'document not open'})
            continue
        doc.activate()
        design = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
        root = design.rootComponent
        for i in range(root.sketches.count - 1, -1, -1):
            if root.sketches.item(i).name == sketch_name:
                root.sketches.item(i).deleteMe()
        sketch, outer_count = make_sketch(root, geometry_path, sketch_name)
        result.append({
            'document': doc.name,
            'sketch': sketch.name,
            'outer_segments': outer_count,
            'line_count': sketch.sketchCurves.sketchLines.count,
            'arc_count': sketch.sketchCurves.sketchArcs.count,
            'circle_count': sketch.sketchCurves.sketchCircles.count,
            'profile_count': sketch.profiles.count,
            'bodies': [body.name for body in root.bRepBodies],
        })
    print(json.dumps(result, ensure_ascii=False))
