"""one-shot (applied 2026-10-05): magnet notches for CNC.  The magnet wall goes 0.6 -> 0.8 (JLCCNC) and the post / boss must
leave room for a corner relief, so the semicircular notches grow and their junctions with the board edge get fillets
(the case wall there becomes an inner corner: R >= H/10 + 0.5).
  PCB  : r = MAG_D/2 + MAG_WALL + 0.3 (relief) + 0.3 (cavity clearance) = 4.45, fillet R2.0   (left PCB, right PCB new at A2)
  plate: r = MAG_D/2 + MAG_WALL + 0.3 + 1.0 (open_clr)                    = 5.15, fillet R1.0   (shared plate, right plate ref)
Replaces the existing notch (mag_notch.py) or cuts a new one into the straight edge through the centre.  Running it again
re-cuts the same notch (it finds the notch arc by its centre)."""
import re, uuid, math
import numpy as np
from geo import B, outline
from shapely.geometry import Point
from casegeo import MAG_NOTCH, C2, MAG_D, MAG_WALL

PCB_R, PCB_F = MAG_D / 2 + MAG_WALL + 0.6, 2.0
PLATE_R, PLATE_F = MAG_D / 2 + MAG_WALL + 1.3, 1.0
A2 = (C2 - MAG_NOTCH[0], MAG_NOTCH[1])       # right case, left edge = the shared plate's notch flipped
JOBS = [('mx_main/mx.kicad_pcb', MAG_NOTCH, PCB_R, PCB_F),
        ('mx_right_tb/mx_right_tb.kicad_pcb', A2, PCB_R, PCB_F),
        ('mx_plate/mx_plate.kicad_pcb', MAG_NOTCH, PLATE_R, PLATE_F),
        ('mx_right_tb_plate/mx_right_tb_plate.kicad_pcb', A2, PLATE_R, PLATE_F)]

ITEM = r'\n\t\((gr_line|gr_arc)\n\t\t\(start ([-\d.]+) ([-\d.]+)\)\n(?:\t\t\(mid ([-\d.]+) ([-\d.]+)\)\n)?\t\t\(end ([-\d.]+) ([-\d.]+)\)(.*?)\n\t\)'

def fmt_line(a, b, body):
    return '\n\t(gr_line\n\t\t(start %.6f %.6f)\n\t\t(end %.6f %.6f)%s\n\t)' % (a[0], a[1], b[0], b[1], newid(body))

def fmt_arc(a, m, b, body):
    return '\n\t(gr_arc\n\t\t(start %.6f %.6f)\n\t\t(mid %.6f %.6f)\n\t\t(end %.6f %.6f)%s\n\t)' % (a[0], a[1], m[0], m[1], b[0], b[1], newid(body))

def newid(body):
    return re.sub(r'\(uuid "[^"]+"\)', '(uuid "%s")' % uuid.uuid4(), body)

def chain(A, Bp, C, n, r, f, body):
    A, Bp, C, n = map(np.array, (A, Bp, C, n))
    u = (Bp - A) / np.linalg.norm(Bp - A)
    s = math.sqrt((r + f) ** 2 - f ** 2)
    T1, T2 = C - u * s, C + u * s
    F1, F2 = T1 + n * f, T2 + n * f
    P1, P2 = C + (F1 - C) * r / (r + f), C + (F2 - C) * r / (r + f)
    mid = lambda F, a, b: F + f * ((a - F) + (b - F)) / np.linalg.norm((a - F) + (b - F))
    return (fmt_line(A, T1, body) + fmt_arc(T1, mid(F1, T1, P1), P1, body) + fmt_arc(P1, C + n * r, P2, body)
            + fmt_arc(P2, mid(F2, P2, T2), T2, body) + fmt_line(T2, Bp, body))

def apply(path, cf, r, f):
    s = open(B + path).read(); cx, cy = cf[0], -cf[1]          # KiCad y is down
    items = [m for m in re.finditer(ITEM, s, re.S) if '"Edge.Cuts"' in m.group(8)]
    P = lambda m, i: (float(m.group(i)), float(m.group(i + 1)))
    board = outline(B + path)[0]
    inside = lambda q: board.contains(Point(q[0], -q[1]))
    # existing notch: an arc (with or without fillets) centred on the magnet -> remove the chain between the two straight lines
    arcs = [m for m in items if m.group(1) == 'gr_arc' and abs(math.dist(P(m, 2), (cx, cy)) - math.dist(P(m, 6), (cx, cy))) < 0.05
            and math.dist(P(m, 2), (cx, cy)) > 3]
    if arcs:
        drop = set()
        ends = {}
        for m in items:                      # the notch chain = arcs within r + 3 of the centre
            if m.group(1) == 'gr_arc' and max(math.dist(P(m, 2), (cx, cy)), math.dist(P(m, 6), (cx, cy))) < 7: drop.add(m.start())
        print('  replacing', len(drop), 'arcs')
        pts = [p for m in items if m.start() in drop for p in (P(m, 2), P(m, 6))]
        lines = [m for m in items if m.group(1) == 'gr_line' and any(math.dist(P(m, i), q) < 1e-3 for i in (2, 6) for q in pts)]
        assert len(lines) == 2, (path, len(lines))
        far = [P(m, 6) if any(math.dist(P(m, 2), q) < 1e-3 for q in pts) else P(m, 2) for m in lines]
        A, Bp = far
        body = lines[0].group(8)
        cut = sorted([m for m in items if m.start() in drop] + lines, key=lambda m: m.start())
        new = chain(A, Bp, *foot(A, Bp, (cx, cy), inside), r, f, body)
        for m in reversed(cut[1:]): s = s[:m.start()] + s[m.end():]
        s = s[:cut[0].start()] + new + s[cut[0].end():]
    else:                                    # straight edge through the centre
        best = None
        for m in items:
            if m.group(1) != 'gr_line': continue
            a, b = np.array(P(m, 2)), np.array(P(m, 6)); d = b - a; L = np.linalg.norm(d)
            t = np.dot((cx, cy) - a, d) / L ** 2; q = np.array((cx, cy)) - a; dist = abs(d[0] * q[1] - d[1] * q[0]) / L
            if 0 < t < 1 and (best is None or dist < best[0]): best = (dist, m)
        dist, m = best
        assert dist < 0.05, 'centre %.3f off the edge' % dist
        new = chain(P(m, 2), P(m, 6), *foot(P(m, 2), P(m, 6), (cx, cy), inside), r, f, m.group(8))
        s = s[:m.start()] + new + s[m.end():]
    open(B + path, 'w').write(s)
    print('%s: notch r %.2f + fillets R%.1f at (%.2f, %.2f)' % (path, r, f, cx, cy))

def foot(A, Bp, c, inside):
    A, Bp, c = map(np.array, (A, Bp, c)); u = (Bp - A) / np.linalg.norm(Bp - A)
    C = A + u * np.dot(c - A, u)
    n = np.array((-u[1], u[0]))
    if not inside(C + u * 9.0 + n * 1.0): n = -n          # into the board (tested beyond any old notch)
    return C, n

if __name__ == '__main__':
    for job in JOBS: apply(*job)
