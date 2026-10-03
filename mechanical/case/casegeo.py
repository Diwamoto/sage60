"""Shared case geometry (Fusion coords: mm, y = -KiCad y, plate top z = 0).
Shape-only numbers live here; numbers that drive Fusion features are user parameters (see params.py)."""
import math, json, os
import numpy as np
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity
from geo import outline, edges, B
from emit import ring_curves, _circ

LP = os.environ.get('SAGE60_LP') == '1'      # low-profile variant (Choc on the same PCB): thinner stack, less margin
SFX = '_lp' if LP else ''                     # output file suffix (left_lp_spec.json ...)
CASE_OFF = 3.5 if LP else 4.0   # case outline = PCB/plate body + this (bezel ~ CASE_OFF - open_clr + clr + wall)
OUTER_R = 2.0       # plan-view corner radius of the case outline (top wall gets OUTER_R + clr + wall)
CLR, WALL, OPEN_CLR = (0.2, 1.5, 0.5) if LP else (0.3, 2.0, 1.0)
# z stack (plate top = 0); must match the Fusion parameters plate_t / pcb_gap / xiao_t
PLATE_T, PCB_GAP = (1.2, 1.0) if LP else (1.2, 3.8)   # MX also uses the 1.2 mm shared plate (2026-10-04); PCB top stays at -5.0
XIAO_T = 1.4         # XIAO board 1.2 + 0.17 lifted by solder (Seeed STEP on the PCB, 2026-10-03; 1.0 put the receptacle 0.05 into the wall)
PCB_TOP = -(PLATE_T + PCB_GAP)
MAG_D, MAG_WALL, N_MAG = 6.1, 0.6, 4     # Daiso phi6 magnets (2026-10-03; was phi2 x 10)
STEP_FILL = (84.0, -125.0, 106.0, -100.0)   # left: region whose convex hull fills the outer step at the thumb cluster
MAG_NOTCH = (187.06, -105.78)    # left: PCB/plate edge notch for a magnet post between the right column and the outermost thumb key (mag_notch.py)
FOOT_D = 10.5
INS_D, INS_WALL = 1.6, 0.9     # M2 tapped / self-tapping hole for the MCU cover
POCKET_W, POCKET_IN, POCKET_OUT = 17.0, -2.0, CASE_OFF + 0.2   # gasket pocket: width along edge, extent along the tab normal
C2 = 245.84         # right = left mirrored about x = 122.92
# MCU / USB / slide switch (left side, from mx_main KiCad)
XIAO_X, USB_FACE_Y = 180.9985, -28.5525 + 1.5
USB_W = 15.0        # recess for the plug overmold (outer surface -> flush wall at the port face)
USB_H, USB_R = (8.0 if LP else 9.0), 2.0   # recess cross-section (rounded rectangle, x-z plane); plug overmold <= 7
USB_RCPT_W, USB_RCPT_H, USB_RCPT_R = 9.8, 4.0, 1.6   # opening around the USB-C receptacle (8.94 x 3.26) in the flush wall
USB_ZC = PCB_TOP + XIAO_T + 3.26 / 2    # receptacle centre z = XIAO top + usb_h_c / 2
# slide switch (knob faces +x, on the PCB top z -5.0 .. -3.6): finger scoop in the outer wall + opening through to the knob.
# Both are cut along x through the bottom AND the top case, so their front/back faces are single planes.
SW_Y, SW_ZC = -52.3, PCB_TOP + 0.7
SW_OPEN = (12.0, 6.0, 1.5)      # y-width, z-height, corner R of the opening at the knob (fingernail + knob travel 2.0)
SW_SCOOP = (16.0, 10.0, 4.0)    # finger scoop in the outer wall
SW_X_IN, SW_X_FLOOR = 190.5, 193.0   # opening starts inside the cavity (cavity wall x 191.39); scoop floor leaves 1.6 mm of wall
MCU_RING = (166.0, -63.0, 210.0, -3.0)
TOP_MCU_OPEN = (166.0, -63.0, 212.0, 0.0)
TILT_Y = -136.171

def rrect(cx, cy, w, h, r):
    """rounded rectangle as lines + arcs"""
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2; k = r * (1 - math.sqrt(0.5))
    return [('line', (x0 + r, y0), (x1 - r, y0)), ('arc', (x1 - r, y0), (x1 - k, y0 + k), (x1, y0 + r)),
            ('line', (x1, y0 + r), (x1, y1 - r)), ('arc', (x1, y1 - r), (x1 - k, y1 - k), (x1 - r, y1)),
            ('line', (x1 - r, y1), (x0 + r, y1)), ('arc', (x0 + r, y1), (x0 + k, y1 - k), (x0, y1 - r)),
            ('line', (x0, y1 - r), (x0, y0 + r)), ('arc', (x0, y0 + r), (x0 + k, y0 + k), (x0 + r, y0))]

def rect(x0, y0, x1, y1):
    return [('line', (x0, y0), (x1, y0)), ('line', (x1, y0), (x1, y1)), ('line', (x1, y1), (x0, y1)), ('line', (x0, y1), (x0, y0))]

def sharp_pcb(path):
    """PCB outline with the corner arcs replaced by sharp corners"""
    _, e = edges(path)
    segs = [((d['start'][0], -d['start'][1]), (d['end'][0], -d['end'][1]), 'mid' in d) for d in e]
    rem = segs[:]; loop = [rem.pop(0)]
    while rem:
        end = loop[-1][1]
        k = min(range(len(rem)), key=lambda i: min(math.dist(end, rem[i][0]), math.dist(end, rem[i][1])))
        a, b, arc = rem.pop(k)
        if math.dist(end, a) > math.dist(end, b): a, b = b, a
        loop.append((a, b, arc))
    lines = [s for s in loop if not s[2]]
    pts = []; jogs = []; n = len(lines)
    for i in range(n):
        (a1, b1, _), (a2, b2, _) = lines[i], lines[(i + 1) % n]
        if math.dist(b1, a2) < 1e-3: pts.append(b1); continue
        d1 = np.subtract(b1, a1); d2 = np.subtract(b2, a2)
        cr = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(cr) < 1e-6 * np.linalg.norm(d1) * np.linalg.norm(d2):      # parallel (S-jog): join the ends with a slanted line
            jogs.append(len(pts)); pts += [tuple(b1), tuple(a2)]
        else:
            s = ((a2[0] - a1[0]) * d2[1] - (a2[1] - a1[1]) * d2[0]) / cr
            pts.append((a1[0] + d1[0] * s, a1[1] + d1[1] * s))
    poly = Polygon(pts)
    for j in jogs:                       # push the slanted jog line 0.25 mm outward so it clears the S-curve
        p, q = np.array(pts[j]), np.array(pts[j + 1]); t = (q - p) / np.linalg.norm(q - p); nn = np.array((t[1], -t[0]))
        if poly.contains(Point(*((p + q) / 2 + nn * 0.5))): nn = -nn
        pts[j], pts[j + 1] = tuple(p + nn * 0.25), tuple(q + nn * 0.25)
    poly = Polygon(pts)
    for a, b, arc in loop:               # large arcs are notches (mag_notch.py), not corners: cut them back out
        if not arc: continue
        d = [x for x in e if 'mid' in x and math.dist((x['start'][0], -x['start'][1]), a) + math.dist((x['end'][0], -x['end'][1]), b) < 1e-3
             or 'mid' in x and math.dist((x['start'][0], -x['start'][1]), b) + math.dist((x['end'][0], -x['end'][1]), a) < 1e-3][0]
        m = (d['mid'][0], -d['mid'][1]); r = math.dist(a, b) / 2
        if r > 3.0: poly = poly.difference(Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2).buffer(r, quad_segs=32))
    return poly

def tabs_and_body(plate, pcb):
    tabs = [g for g in getattr(plate.difference(pcb), 'geoms', []) if g.area > 5]
    body = plate.difference(unary_union([t.buffer(0.02) for t in tabs])).buffer(0.01).buffer(-0.01)
    body = max(getattr(body, 'geoms', [body]), key=lambda g: g.area)
    ring = list(pcb.exterior.coords); info = []
    for t in tabs:                      # base point + outward normal of every tab
        c = np.array(t.centroid.coords[0]); best = None
        for a, b in zip(ring, ring[1:]):
            a, b = np.array(a), np.array(b); d = b - a; L = np.linalg.norm(d)
            if L < 1: continue
            u = np.clip(np.dot(c - a, d) / L**2, 0, 1); dist = np.linalg.norm(a + u * d - c)
            if best is None or dist < best[0]: best = (dist, a, d / L)
        _, a, d = best; n = np.array((d[1], -d[0]))
        if np.dot(c - a, n) < 0: n = -n
        # centre of the tab along the edge, from its outer half
        pts = [np.array(p) for p in t.exterior.coords if np.dot(np.array(p) - a, n) > 1.0]
        s = [np.dot(p - a, d) for p in pts]
        info.append(dict(poly=t, a=a, n=n, d=d, mid=(min(s) + max(s)) / 2, width=max(s) - min(s)))
    return tabs, body, info

def gasket_pockets(info):
    out = []
    for t in info:
        a, n, d, m = t['a'], t['n'], t['d'], t['mid']
        P = lambda s, r: tuple(a + d * s + n * r)
        w = max(POCKET_W, t['width'] + 0.6)
        s0, s1 = m - w / 2, m + w / 2
        out.append(Polygon([P(s0, POCKET_IN), P(s1, POCKET_IN), P(s1, POCKET_OUT), P(s0, POCKET_OUT)]))
    return out

def round_poly(p, r):
    p = p.buffer(-r, quad_segs=32).buffer(r, quad_segs=32)      # convex corners
    p = p.buffer(r, quad_segs=32).buffer(-r, quad_segs=32)      # concave corners
    return Polygon(max(getattr(p, 'geoms', [p]), key=lambda g: g.area).exterior)

def back_arc_outline(base_off):
    """base_off with the whole back replaced by one circular arc through the two back corners"""
    x0, _, x1, _ = base_off.bounds
    def top_at(x):
        g = base_off.intersection(LineString([(x, -500), (x, 500)]))
        return max(c[1] for c in getattr(g, 'coords', [])) if not g.is_empty else None
    yL, yR = top_at(x0 + 1e-3), top_at(x1 - 1e-3)
    xs = np.linspace(x0, x1, 400)
    for sag in np.arange(0.5, 40, 0.05):
        # circle through (x0,yL),(x1,yR) and the mid point raised by sag
        mx, my = (x0 + x1) / 2, (yL + yR) / 2 + sag
        cx, cy, r = _circ((x0, yL), (mx, my), (x1, yR))
        arc_y = cy + np.sqrt(np.maximum(r * r - (xs - cx) ** 2, 0))
        ok = all((top_at(x) or -1e9) <= y + 1e-6 for x, y in zip(xs[2:-2], arc_y[2:-2]))
        if ok: break
    arc = [(x, cy + math.sqrt(r * r - (x - cx) ** 2)) for x in np.linspace(x0, x1, 600)]
    fill = Polygon(arc + [(x1, yR - 25), (x0, yL - 25)])
    return unary_union([base_off, fill]).buffer(0), dict(center=(cx, cy), r=r, sag=sag, yL=yL, yR=yR)

def fps(cands, k, seed=None):
    """farthest point sampling"""
    cands = np.array(cands); chosen = [cands[np.argmax(cands[:, 0] + cands[:, 1]) if seed is None else seed]]
    d = np.linalg.norm(cands - chosen[0], axis=1)
    for _ in range(k - 1):
        i = int(np.argmax(d)); chosen.append(cands[i]); d = np.minimum(d, np.linalg.norm(cands - cands[i], axis=1))
    return [tuple(map(float, c)) for c in chosen]

def grid_points(region, step=0.5):
    x0, y0, x1, y1 = region.bounds; pts = []
    for x in np.arange(x0, x1, step):
        for y in np.arange(y0, y1, step):
            if region.contains(Point(x, y)): pts.append((x, y))
    return pts

def magnet_spots(case, opening, cav, keepout, n=N_MAG):
    """magnets sit where the top ring (opening .. case) overlaps the bottom shelf (cav .. case)"""
    band = case.difference(unary_union([opening, cav, keepout]))
    ok = band.buffer(-(MAG_D / 2 + MAG_WALL))
    cands = grid_points(ok, 0.25)
    for g in getattr(ok, 'geoms', [ok]):          # thin parts of the band: take points on the boundary too
        for r in [g.exterior] + list(g.interiors):
            cands += list(r.segmentize(0.5).coords)
    return fps(cands, n), band

def screw_spots(region, n):
    ok = region.buffer(-(INS_D / 2 + INS_WALL))
    return fps(grid_points(ok, 0.25), n) if not ok.is_empty else []

def feet_spots(case, keepout=None):
    """one foot near each corner of the bounding box"""
    inset = case.buffer(-(FOOT_D / 2 + 2.5))
    if keepout is not None: inset = inset.difference(keepout)
    x0, y0, x1, y1 = case.bounds
    from shapely.ops import nearest_points
    return [tuple(nearest_points(inset, Point(c))[0].coords[0]) for c in ((x0, y1), (x1, y1), (x1, y0), (x0, y0))]

def inner_outline(cav, opening, pcb):
    """one inner wall for the bottom cavity and the top ring (flush across the split), solid's inner corners >= R1.5
    (except where that would come closer than 0.3 to the PCB: there the PCB's own outline + 0.3 wins)"""
    r = unary_union([cav, opening]).buffer(-1.5, quad_segs=16).buffer(1.5, quad_segs=16)
    r = unary_union([r, pcb.buffer(0.3, quad_segs=16)])
    return Polygon(max(getattr(r, 'geoms', [r]), key=lambda g: g.area).exterior)

def hexagon(c, d):
    return [(c[0] + d / math.sqrt(3) * math.cos(math.radians(30 + 60 * i)), c[1] + d / math.sqrt(3) * math.sin(math.radians(30 + 60 * i))) for i in range(6)]

def curves_of(poly, short=1.6):
    return ring_curves(poly.exterior.coords, short=short)

def sample(c):
    if c[0] == 'line': return [c[1], c[2]]
    if c[0] == 'arc':
        ux, uy, r = _circ(c[1], c[2], c[3])
        a1 = math.atan2(c[1][1] - uy, c[1][0] - ux); a2 = math.atan2(c[2][1] - uy, c[2][0] - ux); a3 = math.atan2(c[3][1] - uy, c[3][0] - ux)
        d13 = (a3 - a1) % (2 * math.pi); d12 = (a2 - a1) % (2 * math.pi)
        if d12 > d13: d13 -= 2 * math.pi
        return [(ux + r * math.cos(a1 + d13 * i / 20), uy + r * math.sin(a1 + d13 * i / 20)) for i in range(21)]
    if c[0] == 'spline': return c[1]
    if c[0] == 'circle': return []

def check(name, poly, curves, tol=0.08):
    pts = []
    for c in curves: pts += sample(c)
    h = poly.exterior.hausdorff_distance(LineString(pts))
    print('%-16s curves=%3d hausdorff=%.3f %s' % (name, len(curves), h, {k: sum(1 for c in curves if c[0] == k) for k in ('line', 'arc', 'spline')}))
    assert h < tol, name
    return curves

def mirror_curves(curves):
    M = lambda p: (C2 - p[0], p[1])
    out = []
    for c in curves:
        if c[0] == 'line': out.append(('line', M(c[1]), M(c[2])))
        elif c[0] == 'arc': out.append(('arc', M(c[1]), M(c[2]), M(c[3])))
        elif c[0] == 'spline': out.append(('spline', [M(p) for p in c[1]]))
        elif c[0] == 'circle': out.append(('circle', M(c[1]), c[2]))
    return out
mirror_poly = lambda p: affinity.scale(p, -1, 1, origin=(C2 / 2, 0))

# guard: the top case covers the plate between the outermost thumb key and the MCU (as the old sage60 case did),
# keeping KEY_CLR around every keycap; its underside floats GUARD_Z above the plate (Fusion param guard_z)
KEYCAP, KEY_CLR, GUARD_R = 18.0, 1.0, 1.5
GUARD_BOX = (94.0, -140.0, 200.0, MCU_RING[1])       # left: from the thumb cluster's inner end to the wall, below the MCU; the right uses the mirror
GUARD_MIN = 1.5     # drop guard parts narrower than this (the strip along the wall)

def keycaps(path):
    """keycap squares (KEYCAP) at every switch footprint, Fusion coords"""
    import re
    s = open(path).read(); out = []
    for m in re.finditer(r'\n\t\(footprint "[^"]*Hotswap[^"]*"\n\t\t\(layer "[^"]+"\)(.*?)\n\t\)', s, re.S):
        a = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', m.group(1))
        x, y, rot = float(a.group(1)), -float(a.group(2)), float(a.group(3) or 0)
        out.append(affinity.rotate(box(x - KEYCAP / 2, y - KEYCAP / 2, x + KEYCAP / 2, y + KEYCAP / 2), rot, origin=(x, y)))
    return out

def guard_region(hole, caps, region):
    """part of the top-ring hole that becomes solid: inside region, KEY_CLR away from the keycaps; solid inner corners >= GUARD_R"""
    caps = unary_union(caps).buffer(2.5, join_style=2).buffer(-2.5, join_style=2)     # close the < 5 mm gaps between keycaps -> straight guard edges
    keep = caps.buffer(-GUARD_R + KEY_CLR, join_style=2).buffer(GUARD_R, quad_segs=16)   # keycaps + KEY_CLR, R GUARD_R corners
    g = hole.intersection(region).difference(keep)
    newhole = hole.difference(g).buffer(-GUARD_R, quad_segs=16).buffer(GUARD_R, quad_segs=16)   # round the corners the guard makes
    g = hole.intersection(region).difference(newhole).buffer(-GUARD_MIN / 2).buffer(GUARD_MIN / 2)   # drop slivers
    g = unary_union([p for p in getattr(g, 'geoms', [g]) if p.area > 5.0 and p.distance(hole.exterior) < 0.01])   # only parts joined to the ring
    g = g.buffer(0.4, join_style=2).intersection(hole.buffer(0.4)).difference(keep).buffer(-0.1).buffer(0.1)   # overlap the ring by 0.4 so the join can't leave a gap
    return unary_union([p for p in getattr(g, 'geoms', [g]) if p.area > 5.0])
