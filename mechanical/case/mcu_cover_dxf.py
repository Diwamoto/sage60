"""MCU cover (walnut) outlines for ordering -> case/sage60_{left,right}{,_lp}_mcu_cover.dxf (mm, seen from above, Fusion XY).
Reads MCU_COVER from {side}{_lp}_spec.json (make_left.py / make_right.py first): outline lines/arcs + the M2 holes.
Thickness: MX 3.0 mm, low profile 1.2 mm (cover_t).  Countersink the M2 holes for flat heads."""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'case')

def arc3(a, m, b):
    """centre, radius, start/end angles (deg, CCW from start to end) of the arc a -> m -> b"""
    (x1, y1), (x2, y2), (x3, y3) = a, m, b
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    ux = ((x1 * x1 + y1 * y1) * (y2 - y3) + (x2 * x2 + y2 * y2) * (y3 - y1) + (x3 * x3 + y3 * y3) * (y1 - y2)) / d
    uy = ((x1 * x1 + y1 * y1) * (x3 - x2) + (x2 * x2 + y2 * y2) * (x1 - x3) + (x3 * x3 + y3 * y3) * (x2 - x1)) / d
    ang = lambda p: math.degrees(math.atan2(p[1] - uy, p[0] - ux)) % 360
    s, t, e = ang(a), ang(m), ang(b)
    if (t - s) % 360 > (e - s) % 360: s, e = e, s          # clockwise a -> b: swap so DXF's CCW sweep goes through m
    return (ux, uy), math.hypot(x1 - ux, y1 - uy), s, e

def dxf(curves):
    out = ['0', 'SECTION', '2', 'HEADER', '9', '$INSUNITS', '70', '4', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES']
    ent = lambda kind, *kv: out.extend(['0', kind, '8', '0'] + [str(v) for v in kv])
    for c in curves:
        if c[0] == 'line':
            ent('LINE', 10, c[1][0], 20, c[1][1], 30, 0.0, 11, c[2][0], 21, c[2][1], 31, 0.0)
        elif c[0] == 'arc':
            (cx, cy), r, s, e = arc3(c[1], c[2], c[3])
            ent('ARC', 10, cx, 20, cy, 30, 0.0, 40, r, 50, s, 51, e)
        elif c[0] == 'circle':
            ent('CIRCLE', 10, c[1][0], 20, c[1][1], 30, 0.0, 40, c[2])
        elif c[0] == 'spline':
            for p, q in zip(c[1], c[1][1:]):
                ent('LINE', 10, p[0], 20, p[1], 30, 0.0, 11, q[0], 21, q[1], 31, 0.0)
    return '\n'.join(out + ['0', 'ENDSEC', '0', 'EOF']) + '\n'

if __name__ == '__main__':
    for sfx in ('', '_lp'):
        for side in ('left', 'right'):
            spec = json.load(open(os.path.join(HERE, '%s%s_spec.json' % (side, sfx))))
            cv = spec['MCU_COVER']
            path = os.path.join(OUT, 'sage60_%s%s_mcu_cover.dxf' % (side, sfx))
            open(path, 'w').write(dxf(cv))
            pts = [p for c in cv if c[0] in ('line', 'arc') for p in c[1:] if isinstance(p, list)]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            print(os.path.relpath(path, os.path.join(HERE, '..', '..')), '%.1f x %.1f mm' % (max(xs) - min(xs), max(ys) - min(ys)),
                  'holes', sum(1 for c in cv if c[0] == 'circle'))
