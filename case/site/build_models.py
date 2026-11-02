"""production meshes (+ keycaps from the KiCad footprints, PCB from Edge.Cuts) -> site/models/*.txt + manifest.json
for the product site.  Run: ./venv/bin/python site/build_models.py  A .txt is base64 of raw float32 triangles (x y z * 3 per face; artifacts don't serve .bin),
plate top z = 0, as in production/.  ponytail: keycaps are the same tapered mock as fusion/keycap.py, swap in a real model if the look matters"""
import base64, json, os, re, sys, zipfile, xml.etree.ElementTree as ET
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE + '/..')
from geo import outline, arcpts, B
import shapely
from shapely.geometry import LineString
from shapely.ops import polygonize, unary_union
from stl import load
P = HERE + '/../../production/'; OUT = HERE + '/models/'
PCBS = {'left': 'mx/left/mx.kicad_pcb', 'right': 'mx/right/mx_right.kicad_pcb'}
# rim above the plate, keycap (bottom, top, height), PCB top, as in pcb_step.py / fusion/keycap.py / stage0.py
V = {'mx': dict(sfx='', rim=6.0, cap=(18.0, (12.7, 14.5), 7.5), pcb=-5.0, stl='tb_placed.stl', cover=(3.9, 3.0), sw_top=(11.0, 11.0), sw_h=5.5),
     'lp': dict(sfx='_lp', rim=3.3, cap=(18.0, (15.5, 15.5), 3.5), pcb=-2.2, stl='tb_placed_lp.stl', cover=(4.8, 2.5), sw_top=(13.0, 13.0), sw_h=2.8)}
BALL_R = 17.0
# GPL-3.0 mesh: not copied into site/models, the page fetches it from the fork (pinned in trackball/README.md) and moves it
TB_URL = re.search(r'^R=(\S+)', open(HERE + '/../trackball/README.md').read(), re.M)[1] + '/trackballcase_low.stl'

def extrude(poly, t):
    """closed mesh of a plan polygon, z 0..t"""
    poly = shapely.geometry.polygon.orient(poly, 1.0); out = []
    for g in shapely.constrained_delaunay_triangles(poly).geoms:
        a = np.array(g.exterior.coords[:3]); u, v = a[1] - a[0], a[2] - a[0]
        if u[0] * v[1] - u[1] * v[0] < 0: a = a[::-1]
        out += [np.c_[a[::-1], np.zeros(3)], np.c_[a, np.full(3, t)]]
    c = np.array(poly.exterior.coords)
    for p, q in zip(c[:-1], c[1:]):
        out += [[[*p, 0], [*q, 0], [*q, t]], [[*p, 0], [*q, t], [*p, t]]]
    return np.array(out, dtype=float)

def tris_3mf(f):
    out = []
    z = zipfile.ZipFile(f)
    for n in z.namelist():
        if not n.endswith('.model'): continue
        for m in ET.fromstring(z.read(n)).iter():
            if m.tag.endswith('}mesh'):
                v = np.array([[float(e.get(k)) for k in 'xyz'] for e in m.iter() if e.tag.endswith('}vertex')])
                t = np.array([[int(e.get(k)) for k in ('v1', 'v2', 'v3')] for e in m.iter() if e.tag.endswith('}triangle')])
                out.append(v[t])
    return np.vstack(out)

def cover(spec, z, t):
    """from the spec, not the 3MF: an older 3MF can still carry the screw holes"""
    segs = json.load(open(HERE + '/../' + spec))['MCU_COVER']      # ['line', a, b] / ['arc', start, mid, end]
    lines = [LineString(np.round(arcpts(g[1], g[2], g[3], 8) if g[0] == 'arc' else g[1:], 2)) for g in segs]   # rounded so the ends meet
    poly = max(polygonize(unary_union(lines)), key=lambda p: p.area)
    return extrude(poly, t) + [0, 0, z]

def keys(path):
    txt = open(B + path).read(); out = []
    for m in re.finditer(r'\(footprint "[^"]*Hotswap[^"]*"(.*?)\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', txt, re.S):
        out.append((float(m[2]), -float(m[3]), float(m[4] or 0)))
    return out

def rrect(w, d, r, n=5):
    pts = []
    for sx, sy, a in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for i in range(n + 1):
            t = np.radians(a + 90 * i / n)
            pts.append((sx * (w / 2 - r) + r * np.cos(t), sy * (d / 2 - r) + r * np.sin(t)))
    return np.array(pts)

def keycap(bot, top, h):
    """tapered box, rim at z = 0: side, small top bevel, top"""
    rings = [(rrect(bot, bot, 1.5), 0), (rrect(top[0], top[1], 1.5), h - .5), (rrect(top[0] - 1, top[1] - 1, 1.2), h)]
    out = []
    for (a, za), (b, zb) in zip(rings, rings[1:]):
        for i in range(len(a)):
            j = (i + 1) % len(a)
            p, q, r, s = [*a[i], za], [*a[j], za], [*b[j], zb], [*b[i], zb]
            out += [[p, q, r], [p, r, s]]
    c = rings[-1][0]
    out += [[[*c[0], h], [*c[i], h], [*c[i + 1], h]] for i in range(1, len(c) - 1)]
    return np.array(out)

def caps(ks, c, rim):
    base = keycap(*c); out = []
    for x, y, rot in ks:
        t = np.radians(rot); R = np.array([[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]])
        out.append(base @ R.T + [x, y, rim])
    return np.vstack(out)

def tilt_normal(t):
    """unit normal of the largest flat face looking down: the desk plane"""
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]); a = np.linalg.norm(n, axis=1); n = n / np.maximum(a, 1e-9)[:, None]
    k = np.round(n[n[:, 2] < -.9], 3); w = a[n[:, 2] < -.9]
    u, inv = np.unique(k, axis=0, return_inverse=True)
    return u[np.bincount(inv.ravel(), w).argmax()]

def ball_z(t):
    """the cup is a sphere about the ball: pick the z where most vertices sit at one radius just above BALL_R"""
    v = np.unique(t.reshape(-1, 3), axis=0); c = v[:, :2].mean(0)
    from tb import TBX, TBY
    best = (0, 0)
    for z in np.arange(v[:, 2].min(), v[:, 2].max(), .1):
        d = np.linalg.norm(v - [TBX, TBY, z], axis=1)
        n = ((d > BALL_R + .1) & (d < BALL_R + 1.2)).sum()
        if n > best[0]: best = (n, z)
    return round(float(best[1]), 1)

man = {'parts': {}}
for vk, c in V.items():
    for side, sk in (('left', 'L'), ('right', 'R')):
        s = c['sfx']; parts = {
            'bottom': tris_3mf(P + 'case_print/sage60_%s%s_bottom.3mf' % (side, s)),
            'top': tris_3mf(P + 'case_print/sage60_%s%s_top.3mf' % (side, s)),
            'cover': cover('%s%s_spec.json' % (side, s), *c['cover']),
            'plate': tris_3mf(P + 'plate/sage60_%s_plate.3mf' % side) - [0, 0, 1.2],
            'pcb': extrude(outline(B + PCBS[side])[0], 1.6) + [0, 0, c['pcb'] - 1.6],
            'caps': caps(keys(PCBS[side]), c['cap'], c['rim']),
            # ponytail: switch = housing boxes only, no stem or real model
            'sw': np.vstack([caps(keys(PCBS[side]), (15.6, c['sw_top'], c['sw_h']), 0), caps(keys(PCBS[side]), (14.0, (14.0, 14.0), -c['pcb']), c['pcb'])])}
        info ={'n': tilt_normal(parts['bottom']).tolist(), 'parts': {}}
        lo, hi = parts['top'].reshape(-1, 3).min(0), parts['top'].reshape(-1, 3).max(0)
        info['bbox'] = [lo.round(2).tolist(), hi.round(2).tolist()]
        for k, t in parts.items():
            f = '%s_%s_%s.txt' % (vk, side, k)
            open(OUT + f, 'wb').write(base64.b64encode(np.asarray(t, dtype='<f4').tobytes())); info['parts'][k] = f
        if side == 'right':
            from tb import TBX, TBY
            src, placed = load(HERE + '/../trackball/trackballcase_low.stl'), load(HERE + '/../' + c['stl'])
            at = (placed - src)[0, 0].round(3)
            assert np.allclose(src + at, placed, atol=1e-3), 'tb_placed is not a translation of trackballcase_low.stl'
            info['tb'] = {'url': TB_URL, 'at': at.tolist()}
            info['ball'] = [round(TBX, 2), round(TBY, 2), ball_z(placed), BALL_R]
        man['parts'][vk + sk] = info
        print(vk, side, {k: len(v) for k, v in parts.items()}, len(keys(PCBS[side])), info['n'], info.get('ball'), info['bbox'])
json.dump(man, open(OUT + 'manifest.json', 'w'))
