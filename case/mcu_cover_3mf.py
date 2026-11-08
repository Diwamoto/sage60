"""MCU cover for 3D printing (stand-in for the walnut one) -> production/case_print/sage60_{left,right}{,_lp}_cover.3mf.
Same source as mcu_cover_dxf.py: MCU_COVER outline + MCU_DISC recess (phi8.2 x 0.6 on the underside) from {side}{_lp}_spec.json.
Thickness MX 3.0 / low profile 2.5.  z 0 = underside (seat on the MCU wall), Fusion XY."""
import json, math, os
import numpy as np
import manifold3d as m3
from shapely.geometry import LineString
from shapely.geometry.polygon import orient
from shapely.ops import polygonize, unary_union
from mcu_cover_dxf import arc3, HERE
from plate_3mf import write_3mf

OUT = os.path.join(HERE, '..', 'production', 'case_print')
T = {'': 3.0, '_lp': 2.5}
RECESS = 0.6

def segs(curves):
    for c in curves:
        if c[0] == 'line':
            yield LineString(c[1:3])
        elif c[0] == 'arc':
            (cx, cy), r, s, e = arc3(*c[1:4])
            sweep = (e - s) % 360
            pts = [(cx + r * math.cos(math.radians(s + sweep * i / 32)), cy + r * math.sin(math.radians(s + sweep * i / 32))) for i in range(33)]
            # arc3 may swap ends; snap them back onto the spec's endpoints so the loop closes
            if math.dist(pts[0], c[1]) > math.dist(pts[0], c[3]): pts = pts[::-1]
            pts[0], pts[-1] = tuple(c[1]), tuple(c[3])
            yield LineString(pts)
        elif c[0] == 'spline':
            yield LineString(c[1])

if __name__ == '__main__':
    for sfx, t in T.items():
        for side in ('left', 'right'):
            spec = json.load(open(os.path.join(HERE, '%s%s_spec.json' % (side, sfx))))
            poly = max(polygonize(unary_union(list(segs(spec['MCU_COVER'])))), key=lambda p: p.area)
            body = m3.CrossSection([np.array(orient(poly).exterior.coords[:-1])]).extrude(t)
            want = poly.area * t
            for _, (x, y), r in spec['MCU_DISC']:
                body -= m3.Manifold.cylinder(RECESS, r, r, 96).translate((x, y, 0))
                want -= math.pi * r * r * RECESS
            mesh = body.to_mesh()
            vol, lo, hi = write_3mf(np.asarray(mesh.vert_properties)[:, :3][np.asarray(mesh.tri_verts)], os.path.join(OUT, 'sage60_%s%s_cover.3mf' % (side, sfx)))
            print('%-5s%-3s %.1f x %.1f x %.2f mm  recess %d  volume %.1f mm3 (%+.2f%%)' % (side, sfx, *(hi - lo), len(spec['MCU_DISC']), vol, 100 * (vol / want - 1)))
            assert abs(hi[2] - lo[2] - t) < 0.01 and abs(vol / want - 1) < 0.005
