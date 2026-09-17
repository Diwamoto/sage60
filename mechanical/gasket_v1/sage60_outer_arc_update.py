"""Convert the four sage60 plate outlines to native lines and circular arcs.

The source outlines are the same tessellated rings used to make the plate
sketches.  Only the outer ring is recreated here: straight portions remain
lines and runs that are circular in the source become native SketchArcs.
"""

import adsk.core
import adsk.fusion
import json
import sys

sys.path.append('/Users/daiki/Projects/sage60/mechanical/gasket_v1')
import fusion_plate_surface_simplify as simplify


LEFT_GEOMETRY = '/Users/daiki/Projects/sage60/pcb/mx_plate/gasket_v1/mx_plate_gasket_geometry.json'
RIGHT_GEOMETRY = '/Users/daiki/Projects/sage60/pcb/mx_plate_right_tb/gasket_v1/mx_plate_right_tb_gasket_geometry.json'


def make_outer_sketch(root, geometry_path, sketch_name):
    geometry = json.load(open(geometry_path))
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = sketch_name

    outer_segments = simplify.fit_ring(geometry['rings_pcb_mm'][0])
    for start, middle, end, kind in outer_segments:
        if kind == 'arc':
            simplify.add_arc(sketch, start, middle, end)
        else:
            simplify.add_line(sketch, start, end)
    sketch.isVisible = True
    return sketch, len(outer_segments)


def find_document(app, base_name):
    # Fusion appends the revision (for example, " v1") to saved names.
    for i in range(app.documents.count):
        doc = app.documents.item(i)
        if doc.name == base_name or doc.name.startswith(base_name + ' v'):
            return doc
    return None


def run(_context):
    app = adsk.core.Application.get()
    original = app.activeDocument
    targets = [
        ('sage60_right_bottom', RIGHT_GEOMETRY, 'RIGHT_TB_PLATE_SURFACE'),
        ('sage60_left_bottom', LEFT_GEOMETRY, 'LEFT_PLATE_SURFACE'),
        ('sage60_right_top', RIGHT_GEOMETRY, 'RIGHT_TB_PLATE_SURFACE'),
        ('sage60_left_top', LEFT_GEOMETRY, 'LEFT_PLATE_SURFACE'),
    ]
    result = []

    for base_name, geometry_path, sketch_name in targets:
        doc = find_document(app, base_name)
        if doc is None:
            result.append({'document': base_name, 'error': 'document not open'})
            continue

        doc.activate()
        design = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
        root = design.rootComponent

        # Remove only the old outline sketch.  No source mx_* document is
        # touched, and no switch-hole geometry is introduced.
        for i in range(root.sketches.count - 1, -1, -1):
            if root.sketches.item(i).name == sketch_name:
                root.sketches.item(i).deleteMe()

        sketch, segment_count = make_outer_sketch(root, geometry_path, sketch_name)
        result.append({
            'document': doc.name,
            'sketch': sketch.name,
            'outer_segments': segment_count,
            'line_count': sketch.sketchCurves.sketchLines.count,
            'arc_count': sketch.sketchCurves.sketchArcs.count,
            'profile_count': sketch.profiles.count,
        })

    if original is not None:
        original.activate()
    print(json.dumps(result, ensure_ascii=False))
