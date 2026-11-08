"""Magnetic tent wedge (MX) -> production/case_print/sage60_{left,right}_tent.3mf  (2026-11-07)
Top face = the case's desk face: TOP_WALL_OUTER footprint (the skirt reaches the desk too), a phi8.2 x 0.6 steel-disc recess under
each TENT_MAG and a relief under each rubber foot.  The bottom tilts TENT_DEG about the front-back axis, thin on the outer side.
Built in the desk frame (u = x, v along the tilted desk, w = desk normal, w 0 = the desk face); TENT_PLACED=1 also writes
tent_placed_<side>.stl in Fusion coords for a look in the case document."""
import json, math, os, struct
import numpy as np
import manifold3d as m3
from shapely.affinity import scale, translate
from shapely.geometry.polygon import orient
from shapely.ops import polygonize, unary_union
from casegeo import TILT_DEG, TILT_Y, desk_z
from mcu_cover_3mf import segs, OUT, HERE
from plate_3mf import write_3mf

TENT_DEG = 12.0     # user OK 2026-11-07
T0 = 3.0            # thickness at the outer edge
FOOT_RELIEF = (11.5, 1.5)   # phi, depth: room for a foot that stands proud of its 1 mm recess
DISC = (8.2, 0.6)

def to_desk(y): return (y - TILT_Y) / math.cos(math.radians(TILT_DEG))

def tent(spec, side):
    poly = max(polygonize(unary_union(list(segs(spec['TOP_WALL_OUTER'])))), key=lambda p: p.area)
    poly = translate(scale(poly, 1, 1 / math.cos(math.radians(TILT_DEG)), origin=(0, TILT_Y)), 0, -TILT_Y)   # v = to_desk(y)
    x0, _, x1, _ = poly.bounds
    hmax = T0 + (x1 - x0) * math.tan(math.radians(TENT_DEG))
    body = m3.CrossSection([np.array(orient(poly).exterior.coords[:-1])]).extrude(hmax + 1).translate((0, 0, -hmax - 1))
    # keep w >= -(T0 + d * tan) where d is the distance from the outer edge (left: x0, right: x1)
    s = math.sin(math.radians(TENT_DEG)); c = math.cos(math.radians(TENT_DEG))
    if side == 'left': n, off = (s, 0, c), s * x0 - c * T0       # n . p >= off
    else:              n, off = (-s, 0, c), -s * x1 - c * T0
    body = body.trim_by_plane(n, off)
    for (d, t), key in ((FOOT_RELIEF, 'FEET'), (DISC, 'TENT_MAG')):
        for _, (x, y), _r in spec[key]:
            body -= m3.Manifold.cylinder(t + 1, d / 2, d / 2, 96).translate((x, to_desk(y), -t))
    return body, hmax

def tris(body):
    mesh = body.to_mesh()
    return np.asarray(mesh.vert_properties)[:, :3][np.asarray(mesh.tri_verts)]

def placed(t):
    """desk frame -> Fusion coords (mm)"""
    a = math.radians(TILT_DEG); x, v, w = t[..., 0], t[..., 1], t[..., 2]
    return np.stack([x, TILT_Y + v * math.cos(a) + w * math.sin(a), desk_z(TILT_Y) - v * math.sin(a) + w * math.cos(a)], -1)

if __name__ == '__main__':
    for side in ('left', 'right'):
        spec = json.load(open(os.path.join(HERE, '%s_spec.json' % side)))
        body, hmax = tent(spec, side)
        t = tris(body)
        vol, lo, hi = write_3mf(t, os.path.join(OUT, 'sage60_%s_tent.3mf' % side))
        print('%-5s %.1f x %.1f x %.1f mm  volume %.0f mm3  genus %d' % (side, *(hi - lo), vol, body.genus()))
        assert body.genus() == 0 and abs(hi[2] - lo[2] - hmax) < 0.5
        if os.environ.get('TENT_PLACED'):
            p = placed(t).astype('<f4')
            with open(os.path.join(HERE, 'tent_placed_%s.stl' % side), 'wb') as f:
                f.write(b'\0' * 80 + struct.pack('<I', len(p)))
                for tri in p: f.write(struct.pack('<12fH', 0, 0, 0, *tri.ravel(), 0))
