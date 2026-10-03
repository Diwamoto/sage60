"""ONE-OFF (already applied to mx_plate and mx_right_tb_plate on 2026-10-02 -- running it again shortens the tabs again).
Shorten the gasket tabs of a plate (.kicad_pcb, Edge.Cuts) by CUT mm, in place.
Tabs = pieces of (plate - pcb). For every Edge.Cuts point lying more than KEEP mm out from the tab base
(the PCB edge) the point is moved CUT mm back toward the plate.  usage: shorten_tabs.py plate.kicad_pcb pcb.kicad_pcb [cut]"""
import re, sys, math
import numpy as np
from shapely.geometry import Point
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from geo import outline
CUT = float(sys.argv[3]) if len(sys.argv) > 3 else 2.5
KEEP = 2.4            # points nearer than this to the base stay (base fillets)
plate_p, pcb_p = sys.argv[1], sys.argv[2]
plate, _ = outline(plate_p); pcb, _ = outline(pcb_p)          # Fusion coords (y = -ky)
tabs = [g for g in getattr(plate.difference(pcb), 'geoms', []) if g.area > 5]
ring = list(pcb.exterior.coords)
info = []
for t in tabs:
    c = np.array(t.centroid.coords[0])
    # nearest pcb boundary segment -> outward normal
    best = None
    for a, b in zip(ring, ring[1:]):
        a, b = np.array(a), np.array(b); d = b - a; L = np.linalg.norm(d)
        if L < 1: continue
        u = np.clip(np.dot(c - a, d) / L**2, 0, 1); dist = np.linalg.norm(a + u * d - c)
        if best is None or dist < best[0]: best = (dist, a, d / L)
    _, a, d = best
    n = np.array((d[1], -d[0]))
    if np.dot(c - a, n) < 0: n = -n
    info.append((t.buffer(0.05), a, n))
src = open(plate_p).read()
out = []; i = 0; moved = 0
for m in re.finditer(r'\(gr_(line|arc)\s', src):
    pass
def blocks(s):
    k = 0
    while True:
        j = s.find('(gr_', k)
        if j < 0: return
        depth = 0; e = j
        while True:
            if s[e] == '(': depth += 1
            elif s[e] == ')':
                depth -= 1
                if depth == 0: break
            e += 1
        yield j, e + 1
        k = e + 1
res = []; last = 0
for j, e in blocks(src):
    blk = src[j:e]
    if '"Edge.Cuts"' not in blk: continue
    pts = re.findall(r'\((start|mid|end|center) ([-\d.]+) ([-\d.]+)\)', blk)
    new = blk
    for key, xs, ys in pts:
        x, y = float(xs), float(ys); P = np.array((x, -y))
        for poly, a, n in info:
            if poly.contains(Point(P)) or poly.exterior.distance(Point(P)) < 1e-3:
                dist = np.dot(P - a, n)
                if dist > KEEP:
                    Q = P - n * CUT
                    new = new.replace('(%s %s %s)' % (key, xs, ys), '(%s %.6f %.6f)' % (key, Q[0], -Q[1]), 1)
                    moved += 1
                break
    res.append(src[last:j]); res.append(new); last = e
res.append(src[last:])
open(plate_p, 'w').write(''.join(res))
print(plate_p.split('/')[-1], 'tabs', len(tabs), 'points moved', moved)
