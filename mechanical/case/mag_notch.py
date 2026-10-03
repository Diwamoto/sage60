"""one-shot (applied 2026-10-03): semicircular notch in the PCB / plate edge between the right column and the outermost thumb key,
so a bottom-case post and a top-case boss can meet there with a phi6 magnet pair (casegeo MAG_NOTCH).
Left PCB (ROW4 B.Cu was rerouted by hand first to clear it), left plate (= the shared plate) and the right plate (mirror).
The right PCB is not notched (the right case has room for phi6 elsewhere). Running it again adds a second notch."""
import re, uuid, math
from geo import B
from casegeo import MAG_NOTCH, C2, MAG_D, MAG_WALL, CLR, OPEN_CLR

BOSS_R = MAG_D / 2 + MAG_WALL
JOBS = [('mx_main/mx.kicad_pcb', MAG_NOTCH, BOSS_R + 0.3),                         # PCB clears the post by 0.3 (cavity = PCB + 0.3)
        ('mx_plate/mx_plate.kicad_pcb', MAG_NOTCH, BOSS_R + 1.0),                  # plate clears the boss by open_clr (MX 1.0)
        ('mx_right_tb_plate/mx_right_tb_plate.kicad_pcb', (C2 - MAG_NOTCH[0], MAG_NOTCH[1]), BOSS_R + 1.0)]

def notch(path, c, r):
    s = open(path).read(); cx, cy = c[0], -c[1]           # KiCad y is down
    best = None
    for m in re.finditer(r'\n\t\(gr_line\n\t\t\(start ([-\d.]+) ([-\d.]+)\)\n\t\t\(end ([-\d.]+) ([-\d.]+)\)(.*?)\n\t\)', s, re.S):
        if '"Edge.Cuts"' not in m.group(5): continue
        x1, y1, x2, y2 = map(float, m.groups()[:4]); dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy)
        if L < 2 * r + 1: continue
        t = ((cx - x1) * dx + (cy - y1) * dy) / L**2; d = abs((cx - x1) * dy - (cy - y1) * dx) / L
        if r / L < t < 1 - r / L and (best is None or d < best[0]): best = (d, m, (x1, y1, x2, y2), t)
    d, m, (x1, y1, x2, y2), t = best
    assert d < 0.05, 'centre is %.3f off the edge' % d
    ux, uy = (x2 - x1) / math.hypot(x2 - x1, y2 - y1), (y2 - y1) / math.hypot(x2 - x1, y2 - y1)
    px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
    p1, p2 = (px - ux * r, py - uy * r), (px + ux * r, py + uy * r)
    inside = lambda q: point_in(s, q)
    nx, ny = -uy, ux
    if not inside((px + nx * 1.0, py + ny * 1.0)): nx, ny = -nx, -ny      # bite into the board
    mid = (px + nx * r, py + ny * r)
    body = m.group(5)
    line = lambda a, b: '\n\t(gr_line\n\t\t(start %.6f %.6f)\n\t\t(end %.6f %.6f)%s\n\t)' % (a[0], a[1], b[0], b[1], re.sub(r'\(uuid "[^"]+"\)', '(uuid "%s")' % uuid.uuid4(), body))
    arc = '\n\t(gr_arc\n\t\t(start %.6f %.6f)\n\t\t(mid %.6f %.6f)\n\t\t(end %.6f %.6f)%s\n\t)' % (p1 + mid + p2 + (re.sub(r'\(uuid "[^"]+"\)', '(uuid "%s")' % uuid.uuid4(), body),))
    s = s[:m.start()] + line((x1, y1), p1) + arc + line(p2, (x2, y2)) + s[m.end():]
    open(path, 'w').write(s)
    print('%s: notch r %.2f at (%.2f, %.2f) on edge (%.1f,%.1f)-(%.1f,%.1f)' % (path.split('/')[-1], r, px, py, x1, y1, x2, y2))

def point_in(s, q):
    from geo import outline
    import tempfile, os
    with tempfile.NamedTemporaryFile('w', suffix='.kicad_pcb', delete=False) as f: f.write(s)
    try:
        o, _ = outline(f.name)
    finally:
        os.unlink(f.name)
    from shapely.geometry import Point
    return o.contains(Point(q[0], -q[1]))

if __name__ == '__main__':
    for f, c, r in JOBS: notch(B + f, c, r)
