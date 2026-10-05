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
OUTER_R = 2.0 if LP else 3.3   # plan-view corner radius of the case outline (top wall gets OUTER_R + clr + wall); MX 3.3: the skirt's inner corners (OUTER_R + clr) run the full ~30 mm where the ring is open over the MCU -> JLCCNC R >= H/10 + 0.5
CLR, WALL, OPEN_CLR = (0.2, 1.5, 0.5) if LP else (0.3, 2.0, 1.0)
# z stack (plate top = 0); must match the Fusion parameters plate_t / pcb_gap / xiao_t
PLATE_T, PCB_GAP = (1.2, 1.0) if LP else (1.2, 3.8)   # MX also uses the 1.2 mm shared plate (2026-10-04); PCB top stays at -5.0
XIAO_T = 1.4         # XIAO board 1.2 + 0.17 lifted by solder (Seeed STEP on the PCB, 2026-10-03; 1.0 put the receptacle 0.05 into the wall)
PCB_TOP = -(PLATE_T + PCB_GAP)
MAG_D, MAG_WALL, N_MAG = 6.1, 0.8, 4     # Daiso phi6 magnets (2026-10-03; was phi2 x 10); wall 0.6 -> 0.8 = JLCCNC recommended minimum for metal (2026-10-05)
STEP_FILL = (84.0, -125.0, 106.0, -100.0)   # left: region whose convex hull fills the outer step at the thumb cluster
MAG_STEP = (91.4, -109.4)        # left: magnet at the thumb step (front left), the outline grows round it if needed (2026-10-05)
MAG_NOTCH = (187.06, -105.78)    # left: PCB/plate edge notch for a magnet post between the right column and the outermost thumb key (mag_notch.py)
FOOT_D = 10.5
INS_D, INS_WALL = 1.6, 0.9     # M2 tapped / self-tapping hole for the MCU cover
POCKET_W, POCKET_IN, POCKET_OUT = 17.0, -2.0, CASE_OFF + 0.2   # gasket pocket: width along edge, extent along the tab normal
POCKET_R = 1.0      # its corners (the top case slot ends inside the ring: ~3.7 deep -> R >= 0.9)
POCKET_OUT_B = CASE_OFF + 12.0  # bottom pockets run out past the outline (the back arc is up to ~10 out; their R corners stay outside)
C2 = 245.84         # right = left mirrored about x = 122.92
# MCU / USB / slide switch (left side, from mx_main KiCad)
XIAO_X, USB_FACE_Y = 180.9985, -28.5525 + 1.5
USB_W = 15.0        # recess for the plug overmold (outer surface -> flush wall at the port face); since 2026-10-05 USB_PLUG_W + 2 R
USB_PLUG_W = 12.7   # plug overmold 12.5 + 0.2
USB_H, USB_R = (8.0 if LP else 9.0), 2.0   # recess cross-section (rounded rectangle, x-z plane); plug overmold <= 7
USB_RCPT_W, USB_RCPT_H, USB_RCPT_R = 9.8, 4.0, 1.6   # opening around the USB-C receptacle (8.94 x 3.26) in the flush wall
USB_ZC = PCB_TOP + XIAO_T + 3.26 / 2    # receptacle centre z = XIAO top + usb_h_c / 2
# slide switch (knob faces +x, on the PCB top z -5.0 .. -3.6): finger scoop in the outer wall + opening through to the knob.
# Both are cut along x through the bottom AND the top case, so their front/back faces are single planes.
SW_Y, SW_ZC = -52.3, PCB_TOP + 0.7
SW_OPEN = (11.0, 6.0, 1.5)      # y-width, z-height, corner R of the opening at the knob (fingernail + knob travel 2.0); 12 -> 11 (2026-10-05): its side ran into a cavity relief (0.7 mm wedge)
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
            off = abs((a2[0] - a1[0]) * d1[1] - (a2[1] - a1[1]) * d1[0]) / np.linalg.norm(d1)
            if off < 1e-3: pts += [tuple(b1), tuple(a2)]; continue          # collinear (a notch in a straight edge): straight across
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
    # notches (mag_notch.py, notch_fillet.py): an arc of r > 3 plus the fillets touching it -> cut the real notch back out
    from shapely.geometry import MultiPoint
    arcs = []
    for x in e:
        if 'mid' not in x: continue
        A, M, Bq = (x['start'][0], -x['start'][1]), (x['mid'][0], -x['mid'][1]), (x['end'][0], -x['end'][1])
        cx, cy, r = _circ(A, M, Bq)
        a0, a1_, a2_ = (math.atan2(q[1] - cy, q[0] - cx) for q in (A, M, Bq))
        d13 = (a2_ - a0) % (2 * math.pi); d12 = (a1_ - a0) % (2 * math.pi)
        if d12 > d13: d13 -= 2 * math.pi
        arcs.append((A, Bq, r, [(cx + r * math.cos(a0 + d13 * i / 40), cy + r * math.sin(a0 + d13 * i / 40)) for i in range(41)]))
    board = outline(path)[0]
    for A, Bq, r, smp in arcs:
        if r <= 3.0: continue
        chain = smp + sum([o[3] for o in arcs if o[2] <= 3.0 and min(math.dist(o[0], q) for q in (A, Bq)) < 1e-3 or o[2] <= 3.0 and min(math.dist(o[1], q) for q in (A, Bq)) < 1e-3], [])
        poly = poly.difference(MultiPoint(chain).convex_hull.difference(board).buffer(0.001))
    poly = Polygon(max(getattr(poly, 'geoms', [poly]), key=lambda g: g.area).exterior)
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

def gasket_pockets(info, out_r=None):
    """gasket pockets along each tab; out_r: how far past the body they run (bottom: past the outline so their R corners are
    outside; top slot: CASE_OFF + 0.2, ending inside the ring)"""
    out_r = POCKET_OUT if out_r is None else out_r
    out = []
    for t in info:
        a, n, d, m = t['a'], t['n'], t['d'], t['mid']
        P = lambda s, r: tuple(a + d * s + n * r)
        w = max(POCKET_W, t['width'] + 0.6)
        s0, s1 = m - w / 2, m + w / 2
        out.append(Polygon([P(s0, POCKET_IN), P(s1, POCKET_IN), P(s1, out_r), P(s0, out_r)]).buffer(-POCKET_R, quad_segs=16).buffer(POCKET_R, quad_segs=16))
    return out

def round_poly(p, r, rc=None):
    rc = r if rc is None else rc
    p = p.buffer(-r, quad_segs=32).buffer(r, quad_segs=32)      # convex corners
    p = p.buffer(rc, quad_segs=32).buffer(-rc, quad_segs=32)    # concave corners
    return Polygon(max(getattr(p, 'geoms', [p]), key=lambda g: g.area).exterior)

def back_arc_outline(base_off):
    """base_off with the whole back replaced by one circular arc through the two back corners"""
    x0, _, x1, _ = base_off.bounds
    def top_at(x):
        g = base_off.intersection(LineString([(x, -500), (x, 500)]))
        return max(c[1] for gg in getattr(g, 'geoms', [g]) for c in gg.coords) if not g.is_empty else None
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
GUARD_MIN = 3.0     # drop guard parts narrower than this (the strip along the wall); 3 = the R1.5 tool (2026-10-05: the 2 mm strip met the gasket slots in slivers)

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

# ---- CNC (JLCCNC, 3-axis): solid inner corners R >= H / 10 + 0.5, H = depth of the wall (2026-10-05) ----
def cnc_r(h):
    return h / 10 + 0.5

# z model (must match the Fusion parameters): desk plane, cavity floor, tops of the bottom case
TILT_DEG = 0.0 if LP else 5.0
CAV_Z, FLOOR_T = (11.6, 1.5) if LP else (11.0, 2.0)
TOP_H, MCU_COVER_Z = (2.0, 0.8) if LP else (7.0, 3.9)
def desk_z(y):
    return -(CAV_Z + FLOOR_T) - (y - TILT_Y) * math.tan(math.radians(TILT_DEG))
def in_mcu(p):
    return MCU_RING[0] <= p.x <= MCU_RING[2] and MCU_RING[1] <= p.y <= MCU_RING[3]
def cav_depth(p, side=1):
    """cavity wall height at p (left coords: side=-1 mirrors x back): from the bottom case's top there down to the floor"""
    q = Point(C2 - p.x, p.y) if side < 0 else p
    top = MCU_COVER_Z if in_mcu(q) else -PLATE_T
    return top - max(-CAV_Z, desk_z(p.y) + FLOOR_T) if LP else top - (desk_z(p.y) + FLOOR_T)
DESK_MIN = desk_z(-12.0)             # the top case ends at y ~ -12.3 at the back
SKIRT_H = -PLATE_T - DESK_MIN                 # top case skirt inside: ring underside -> desk (deepest at the back)
OUTER_H = TOP_H - DESK_MIN                    # top case outside, full height
CONCAVE_R = math.ceil((CLR + WALL + cnc_r(OUTER_H)) * 2) / 2   # concave corners of the case outline: the top wall's are CONCAVE_R - clr - wall
RING_R = max(1.5, cnc_r(TOP_H + PLATE_T))     # through the top ring (opening, gasket slots, MCU opening)
assert OUTER_R + CLR >= cnc_r(OUTER_H) - 0.02, 'OUTER_R too small for the skirt depth (full height at the MCU)'

def relieve(X, R, keep=None, forbid=None, step=0.1):
    """X plus dog-bone reliefs: discs of radius R(p) (centres in X) wherever an end mill of that radius cannot reach `keep`
    (default X) -- i.e. every convex corner of the pocket X (= inner corner of the solid) gets a tool-radius arc without
    shrinking the pocket.  R: number or function of a point.  forbid: region a relief must not touch (magnet walls ...)."""
    import shapely
    keep = X if keep is None else keep
    Rf = R if callable(R) else (lambda p, R=R: R)
    out = X
    for it in range(4):
        rmax = max(Rf(Point(c)) for k in getattr(keep, 'geoms', [keep]) for c in k.exterior.coords)
        res0 = keep.difference(out.buffer(-rmax, quad_segs=32).buffer(rmax, quad_segs=32))
        pieces, cache = [], {}
        for g in getattr(res0, 'geoms', [res0]):
            if g.is_empty or g.area < 1e-3: continue
            r = round(Rf(g.centroid) + 0.049, 1)
            if r not in cache: cache[r] = out.buffer(-r, quad_segs=32).buffer(r, quad_segs=32)
            loc = keep.intersection(g.buffer(0.2)).difference(cache[r])
            for h in getattr(loc, 'geoms', [loc]):
                if h.geom_type == "Polygon" and h.buffer(-0.01).area > 0: pieces.append((h, r))
        if not pieces: return out
        discs = []
        for g, r in pieces:
            gp = np.array(g.exterior.coords)
            x0, y0, x1, y1 = g.buffer(r).bounds
            xs, ys = np.meshgrid(np.arange(x0, x1, step), np.arange(y0, y1, step))
            P = np.c_[xs.ravel(), ys.ravel()]
            far = np.max(np.linalg.norm(P[:, None, :] - gp[None, :, :], axis=2), axis=1)
            P = P[far <= r - 0.02]
            pts = shapely.points(P)
            P = P[shapely.contains(out, pts)]
            if forbid is not None and len(P):
                P = P[shapely.distance(forbid, shapely.points(P)) > r + 0.06]
            assert len(P), 'no relief centre for the corner at (%.1f, %.1f) R%.1f' % (g.centroid.x, g.centroid.y, r)
            depth = shapely.distance(out.boundary, shapely.points(P))     # deepest centre = least material removed
            c = P[int(np.argmax(depth))]
            discs.append(Point(*c).buffer(r + 0.05, quad_segs=32))     # a hair over the tool radius: the opening test must keep it
        out = unary_union([out] + discs).buffer(0)
    raise AssertionError('relieve did not converge')

def round_corner_box(x0, y0, x1, y1, corner, r):
    """box with one corner (its xy) rounded by r (convex), the others sharp"""
    b = box(x0, y0, x1, y1)
    cx = corner[0] + (r if corner[0] == x0 else -r); cy = corner[1] + (r if corner[1] == y0 else -r)
    sq = box(min(corner[0], cx), min(corner[1], cy), max(corner[0], cx), max(corner[1], cy))
    return unary_union([b.difference(sq), Point(cx, cy).buffer(r, quad_segs=32).intersection(sq)])

def plan_slot(x0, y0, x1, y1, r, rounded_side):
    """slot rectangle in plan with the two corners on `rounded_side` ('y0'|'y1'|'x0'|'x1') rounded by r (concave corners of the
    solid where the slot ends inside the wall); the other end runs out into free space"""
    p = box(x0, y0, x1, y1).buffer(-r, quad_segs=16).buffer(r, quad_segs=16)
    ext = {'y0': box(x0, (y0 + y1) / 2, x1, y1), 'y1': box(x0, y0, x1, (y0 + y1) / 2),
           'x0': box((x0 + x1) / 2, y0, x1, y1), 'x1': box(x0, y0, (x0 + x1) / 2, y1)}[rounded_side]
    return unary_union([p, ext])

THIN = 0.8          # JLCCNC metal: recommended minimum wall

def mcu_regions(case):
    """left: top-ring cut over the MCU (a plain box: Fusion fillets its concave junctions with the skirt and its inner corner
    R RING_R after the skirt is joined) and the raised MCU wall block of the bottom case: CLR inside the box, its corners at
    (166, -63) and where it meets the outline rounded RING_R - CLR (concentric with those fillets -> CLR everywhere)"""
    cut = box(*TOP_MCU_OPEN)
    r = RING_R - CLR
    b = box(TOP_MCU_OPEN[0] + CLR, TOP_MCU_OPEN[1] + CLR, MCU_RING[2], MCU_RING[3])
    inside = b.intersection(case).buffer(-r, quad_segs=32).buffer(r, quad_segs=32)
    block = unary_union([inside, b.difference(case.buffer(-1.0))])
    return cut, Polygon(max(getattr(block, 'geoms', [block]), key=lambda g: g.area).exterior)

def port_slots(case):
    """left: USB and slide switch openings as plan slots cut from their bottom z straight up through both cases (open at the
    top -> machinable from the top; the MCU cover closes the bottom case's).  -> {name: (poly, z_bottom)}"""
    y_out = case.bounds[3] + 5; x_out = case.bounds[2] + 5
    z_usb = USB_ZC - USB_H / 2; z_rcpt = USB_ZC - USB_RCPT_H / 2
    z_scoop = SW_ZC - SW_SCOOP[1] / 2; z_open = SW_ZC - SW_OPEN[1] / 2
    r_usb = math.ceil(max(1.5, cnc_r(MCU_COVER_Z - z_usb)) * 10) / 10
    usb_w = USB_PLUG_W + 2 * r_usb                   # the back corners' R stays outside the plug's path
    r_sw = math.ceil(max(1.5, cnc_r(MCU_COVER_Z - z_scoop)) * 2) / 2
    return {
        'USB_RECESS': (plan_slot(XIAO_X - usb_w / 2, USB_FACE_Y, XIAO_X + usb_w / 2, y_out, r_usb, 'y0'), z_usb),
        'USB_RCPT': (box(XIAO_X - USB_RCPT_W / 2, USB_FACE_Y - 3.0, XIAO_X + USB_RCPT_W / 2, USB_FACE_Y + 0.5), z_rcpt),
        'SW_SCOOP': (plan_slot(SW_X_FLOOR, SW_Y - SW_SCOOP[0] / 2, x_out, SW_Y + SW_SCOOP[0] / 2, r_sw, 'x0'), z_scoop),
        'SW_OPEN': (box(SW_X_IN, SW_Y - SW_OPEN[0] / 2, SW_X_FLOOR + 1.0, SW_Y + SW_OPEN[0] / 2), z_open),
    }

def guard_fill(hole, g, r=None):
    """the opening left above the guard (hole - g) = what an end mill of radius r reaches from it; everything else in the hole
    becomes guard (junction corners, hairline gaps, slots narrower than the tool); guard fins thinner than THIN go"""
    r = RING_R if r is None else r
    for it in range(8):
        h = hole.difference(g)
        h = h.buffer(-r - 0.05, quad_segs=32).buffer(r + 0.05, quad_segs=32)
        fill = hole.difference(h).difference(g)
        add = [p for p in getattr(fill, 'geoms', [fill]) if not p.is_empty and (p.area > 0.05 or p.distance(g) < 0.01)]
        g2 = unary_union([g] + [p.buffer(0.02) for p in add]).difference(h).buffer(0)
        solid = unary_union([g2, hole.buffer(5.0).difference(hole)])            # guard + the ring round it
        g2 = g2.difference(unary_union([q.buffer(0.02) for q in fins(solid)])).buffer(0)
        g2 = unary_union([p for p in getattr(g2, 'geoms', [g2]) if p.area > 0.5])
        if g2.symmetric_difference(g).area < 0.05: return g2
        g = g2
    raise AssertionError('guard did not converge')

def thin_parts(solid, t=THIN):
    return solid.difference(solid.buffer(-t / 2, quad_segs=16).buffer(t / 2, quad_segs=16))

def fins(solid, t=THIN):
    """material thinner than t that lies between two separate stretches of the boundary (a wall / fin / pinch), not the tip of
    a convex corner (whose thin part touches one continuous stretch)"""
    from shapely.ops import linemerge
    out = []
    edge = solid.boundary
    for q in getattr(thin_parts(solid, t), 'geoms', [thin_parts(solid, t)]):
        if q.is_empty or q.area < 0.005: continue
        shared = q.boundary.intersection(edge.buffer(1e-3))
        shared = linemerge(shared) if shared.geom_type == 'MultiLineString' else shared
        n = len(getattr(shared, 'geoms', [shared])) if not shared.is_empty else 0
        if shared.geom_type in ('MultiLineString', 'GeometryCollection', 'MultiPolygon') and n >= 2: out.append(q)
    return out

def fix_pockets(pockets, layers, r=POCKET_R):
    """grow each gasket pocket over the material it leaves thinner than THIN next to it (in every layer it is cut through)"""
    pockets = list(pockets)
    for it in range(6):
        grown = False
        for L in layers:
            solid = L.difference(unary_union(pockets))
            for piece in getattr(thin_parts(solid), 'geoms', [thin_parts(solid)]):
                if piece.is_empty or piece.area < 1e-3: continue
                i = min(range(len(pockets)), key=lambda k: pockets[k].distance(piece))
                if pockets[i].distance(piece) > 0.05: continue
                p = unary_union([pockets[i], piece.buffer(0.05)])
                pockets[i] = Polygon(p.buffer(r, quad_segs=8).buffer(-r, quad_segs=8).buffer(-r, quad_segs=8).buffer(r, quad_segs=8).exterior); grown = True
        if not grown: return pockets
    raise AssertionError('pocket slivers did not converge')

def magnet_bump(case0, inner, cavity, keep, target, search=10.0, step=0.25):
    """a magnet spot near `target` where the top ring (inner .. case) and the bottom shelf (cavity .. case) leave MAG_WALL round
    the hole; the outline grows by the convex hull of the hole's boss and the local outline (straight sides) -- the least area"""
    import shapely
    rr = MAG_D / 2 + MAG_WALL + 0.05
    free = unary_union([inner, cavity, keep]).buffer(rr)
    xs, ys = np.meshgrid(np.arange(target[0] - search, target[0] + search, step), np.arange(target[1] - search, target[1] + search, step))
    P = np.c_[xs.ravel(), ys.ravel()]
    P = P[~shapely.contains(free, shapely.points(P))]
    assert len(P), 'no magnet spot near %s' % (target,)
    best = None
    for p in P:
        disc = Point(*p).buffer(rr, quad_segs=32)
        patch = unary_union([case0.intersection(disc.buffer(6.0)), disc]).convex_hull
        add = patch.difference(case0).area + 0.3 * math.dist(p, target)      # stay near the asked spot (0.3 mm2 per mm)
        if best is None or add < best[0]: best = (add, tuple(map(float, p)), patch)
    return best[1], unary_union([case0, best[2]]).buffer(0)

def fit(name, poly, tol=0.08):
    """lines/arcs for a polygon's exterior: the coarsest fit that stays within tol"""
    for simp, short in ((0.005, 0.6), (0.005, 0.3), (0.01, 0.3), (0.005, 0.2), (0.01, 0.15), (0.002, 0.1), (0.002, 0.05)):
        c = curves_of(poly.simplify(simp), short=short)
        pts = []
        for cc in c: pts += sample(cc)
        if poly.exterior.hausdorff_distance(LineString(pts)) < tol: return check(name, poly, c, tol)
    raise AssertionError('no fit for %s' % name)

def fix_cuts(cuts, base, r=0.0):
    """grow each cut (plan region) over the real fins (< THIN) it leaves in `base` (material) -> no thin walls between the cut and
    nearby features; cuts: {name: poly}"""
    cuts = dict(cuts)
    for it in range(6):
        grown = False
        solid = base.difference(unary_union(list(cuts.values())))
        for q in fins(solid):
            k = min(cuts, key=lambda n: cuts[n].distance(q))
            if cuts[k].distance(q) > 0.05: continue
            g = unary_union([cuts[k], q.buffer(0.05)])
            cuts[k] = Polygon(max(getattr(g, 'geoms', [g]), key=lambda x: x.area).exterior); grown = True
        if not grown: return cuts
    raise AssertionError('cut fins did not converge')

def ensure_boss(case0, c):
    """a fixed magnet (PCB notch) keeps MAG_WALL to the outside too: grow the outline by the hull of its boss and the local outline"""
    rr = MAG_D / 2 + MAG_WALL + 0.05
    disc = Point(c).buffer(rr, quad_segs=32)
    if case0.buffer(-0.01).contains(disc): return case0
    return unary_union([case0, unary_union([case0.intersection(disc.buffer(6.0)), disc]).convex_hull]).buffer(0)
