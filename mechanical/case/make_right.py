"""right case geometry = left mirrored (x' = 245.84 - x) + trackball changes -> right_spec.json, tb_placed.stl, right_geo.png"""
import json, pickle, struct
from casegeo import *
from shapely.geometry import MultiPolygon
from make_left import build_left
from tb import tb_tris, footprint, TBX, TBY

TB_ZREL0 = 2.0 + PLATE_T + PCB_GAP + 0.3 + 3.7   # Fusion z = STL z_rel - this (case bottom z_rel 2 -> TB_SEAT = -(plate_t+pcb_gap+tb_gap+tb_leg_h))
TB_CLR, BALL_R = 0.5, 17.0
SHELF_REL = TB_ZREL0 - PLATE_T          # z_rel of the shelf top (-shelf_d)
X_R, RIM = 168.0, 5.5               # thumb access: right limit, rim kept along the thumb cluster (4 -> 5.5: the top case rim was < 3 mm beside the keycaps)
THIN_TOP, THIN_BOT = 3.0, 2.0       # around the trackball, top / bottom case parts narrower than this are cut away (slivers where the cuts meet the outline)
TB_SCREWS = [(TBX + 9.59, TBY - 7.72), (TBX + 9.59, TBY + 8.48)]   # hex bosses of the trackball case
TB_CB_D = 3.6

def opening_rounded(p, r):
    p = p.buffer(-r, quad_segs=16).buffer(r, quad_segs=16)
    return Polygon(max(getattr(p, 'geoms', [p]), key=lambda g: g.area).exterior)

def build_right():
    L = build_left()
    plate, _ = outline(B + 'mx_right_tb_plate/mx_right_tb_plate.kicad_pcb')
    pcb, _ = outline(B + 'mx_right_tb/mx_right_tb.kicad_pcb')
    spcb = sharp_pcb(B + 'mx_right_tb/mx_right_tb.kicad_pcb')
    tabs, body, info = tabs_and_body(plate, pcb)
    # sharp corners where the PCB is convex, the PCB's own fillets where it is concave
    cav = Polygon(unary_union([spcb.buffer(0.3, join_style=2, mitre_limit=10), pcb.buffer(0.3, quad_segs=16)]).exterior).simplify(0.002)
    assert cav.contains(pcb.buffer(0.1)), 'cavity does not clear the PCB'
    # trackball case footprints
    t = tb_tris()
    fp_all = footprint(t)
    fp_lo = footprint(t, zmax=SHELF_REL)
    fp_hi = footprint(t, zmin=SHELF_REL)
    # top case hole (above the shelf) and bottom pocket (shelf -> seat) for the trackball case, R1.5 on the solid's inner corners
    h = unary_union([fp_hi, Point(TBX, TBY).buffer(BALL_R, quad_segs=32)])
    h = Polygon(max(getattr(h, 'geoms', [h]), key=lambda g: g.area).exterior)
    tbhole = opening_rounded(h.buffer(TB_CLR, quad_segs=16).buffer(2, quad_segs=16).buffer(-2, quad_segs=16), 1.5)
    pocket = opening_rounded(fp_lo.buffer(TB_CLR, quad_segs=16).buffer(1.5, quad_segs=16).buffer(-1.5, quad_segs=16), 1.5)
    # outline: mirrored left + the trackball case's hull, cut by one straight front edge at the thumb-tip level,
    # pushed forward around the trackball so the case encloses it: bottom wall >= THIN_BOT round the pocket, top case (ring + skirt)
    # >= THIN_TOP round the hole (it stuck out ~2.8 mm before 2026-10-04)
    case_m = mirror_poly(L['case'])
    front_y = case_m.bounds[1]
    hull = unary_union([case_m, fp_all.convex_hull]).convex_hull
    enc = unary_union([pocket.buffer(THIN_BOT + 0.2, quad_segs=16), tbhole.buffer(max(THIN_TOP - CLR - WALL, 0) + 0.2, quad_segs=16)])
    # one straight front edge from under the thumb cluster to the pinky side (2026-10-04: pushing out only the trackball part looked odd):
    # the thumb-side edge is extended along its own direction down to the new front, the right side runs into the diagonal edge
    new_front = min(front_y, enc.bounds[1])
    def left_x(y):
        seg = case_m.intersection(LineString([(0, y), (250, y)]))
        return seg.bounds[0]
    y1, y2 = front_y + 3.0, front_y + 18.0
    x1, x2 = left_x(y1), left_x(y2)
    corner = (x1 + (x1 - x2) * (y1 - new_front) / (y2 - y1), new_front)
    base = unary_union([case_m, hull.intersection(box(40, front_y, 200, -96))])
    lower = base.intersection(box(0, -250, 250, front_y + 25))
    ext = unary_union([lower, Point(corner).buffer(0.01), box(corner[0], new_front, enc.bounds[2], new_front + 0.01), enc.intersection(box(0, -250, 250, front_y))]).convex_hull
    case = round_poly(unary_union([base, ext, pcb.buffer(3.0, join_style=2)]).buffer(0), OUTER_R)   # PCB at least 3 inside: bottom wall >= THIN_BOT outside the cavity (LP: the tongue corner was 0.35 out)
    protrude = case.bounds[1] - fp_all.bounds[1]
    # top ring opening: keys + trackball hole, merged in front
    keys = inner = inner_outline(cav, body.buffer(OPEN_CLR, quad_segs=16), pcb)   # cavity = top ring inner except at the trackball hole
    assert inner.contains(pcb.buffer(0.1)) and inner.contains(body.buffer(OPEN_CLR / 2))
    # top ring opening: plate body + open_clr, keycaps + KEY_CLR, trackball hole -> the top case covers the bare PCB around the trackball
    caps = unary_union(keycaps(B + 'mx_right_tb/mx_right_tb.kicad_pcb')).buffer(2.5, join_style=2).buffer(-2.5, join_style=2)
    keyhole = opening_rounded(unary_union([body.buffer(OPEN_CLR, quad_segs=16), caps.buffer(KEY_CLR - GUARD_R, join_style=2).buffer(GUARD_R, quad_segs=16)]), 1.5)
    opening = unary_union([keyhole, tbhole]).buffer(0)          # each rounded on its own: rounding the union pinched off the sensor housing
    opening = MultiPolygon([Polygon(g.exterior) for g in getattr(opening, 'geoms', [opening])]) if opening.geom_type == 'MultiPolygon' else Polygon(opening.exterior)   # two loops once the top case runs between them (2026-10-04)
    # thumb access region (no top case, lowered deck)
    a, b = np.array((104.957, -117.72)), np.array((100.95, -102.81))      # thumb cluster right edge (PCB)
    d = (b - a) / np.linalg.norm(b - a); n = np.array((-d[1], d[0]))
    if n[0] < 0: n = -n
    c = a + n * RIM; top = c + d * ((-95 - c[1]) / d[1])
    access = opening_rounded(Polygon([tuple(top), tuple(c), (c[0], -220), (X_R, -220), (X_R, -95)]), 2.0)
    # top case cut / lowered deck: the thumb access behind the ball centre.  (2026-10-03 the top case covered the PCB in it; between
    # the trackball and row 4 that left 2-4 mm strips, hard to print -> dropped 2026-10-04, the PCB edge shows there.)
    # In front of the ball centre the case encloses the trackball case (2026-10-04).
    access_cut = opening_rounded(access.intersection(box(0, TBY, 250, 0)), 2.0)
    # cut away what is left thinner than THIN near the trackball: top case (ring + skirt) and the bottom above the deck share TB_ACCESS,
    # the bottom below the deck goes into TB_POCKET.  Removing by morphological opening leaves R w/2 on the new inner corners.
    near = access.buffer(8.0)
    def slivers(solid, w):
        t = solid.difference(solid.buffer(-w / 2, quad_segs=16).buffer(w / 2, quad_segs=16)).intersection(near)
        return unary_union([q.buffer(0.05) for q in getattr(t, 'geoms', [t]) if q.area > 0.5])
    for it in range(8):
        sl = unary_union([slivers(case.buffer(CLR + WALL).difference(opening).difference(access_cut), THIN_TOP), slivers(case.difference(inner).difference(pocket).difference(access_cut), THIN_BOT)])
        sp = slivers(case.difference(inner).difference(pocket), THIN_BOT)
        if sl.is_empty and sp.is_empty: break
        access_cut = unary_union([access_cut, sl]).buffer(0)
        pocket = unary_union([pocket, sp]).buffer(0)
    else:
        raise AssertionError('slivers did not converge')
    assert pocket.geom_type == 'Polygon', [(round(g.centroid.x, 1), round(g.centroid.y, 1), round(g.area, 2)) for g in getattr(pocket, 'geoms', [pocket])]          # access_cut may get a small detached piece (the rim's tip at the key opening)
    pockets = gasket_pockets(info)
    # MCU / USB / switch: mirrored from the left
    usb = mirror_poly(L['usb']); sw = mirror_poly(L['sw']); mcu = mirror_poly(box(*MCU_RING))
    screws = [(C2 - x, y) for x, y in L['screws']]
    keep = unary_union([p.buffer(1.0) for p in pockets] + [mcu, usb, sw, access_cut.buffer(1.0), tbhole.buffer(1.0), pocket.buffer(1.0)])
    mags, band = magnet_spots(case, opening, cav, keep)
    guard = guard_region(keyhole, keycaps(B + 'mx_right_tb/mx_right_tb.kicad_pcb'), mirror_poly(box(*GUARD_BOX)).difference(unary_union([tbhole, access]).buffer(3.0)))
    cb = unary_union([Point(p).buffer(TB_CB_D / 2 + 1.5) for p in TB_SCREWS])
    feet = feet_spots(case, keepout=cb.buffer(FOOT_D / 2))
    return locals()

if __name__ == '__main__':
    G = build_right(); L = G['L']
    print('magnets', [tuple(round(v, 2) for v in m) for m in G['mags']])
    print('feet', [tuple(round(v, 2) for v in f) for f in G['feet']])
    print('pocket clr to TB', round(G['pocket'].exterior.distance(G['fp_lo']), 3), ' tbhole clr', round(G['tbhole'].exterior.distance(G['h']), 3))
    print('front edge y %.2f -> %.2f around the trackball, case in front of the trackball case %.2f mm' % (G['front_y'], G['case'].bounds[1], -G['protrude']))
    front = box(0, -250, 250, TBY)
    print('in front of the ball centre: bottom wall %.2f, top case (ring + skirt) %.2f' % (G['case'].exterior.distance(G['pocket'].intersection(front)), G['case'].exterior.distance(G['tbhole'].intersection(front)) + CLR + WALL))
    spec = {}
    spec['PLATE_SURFACE'] = check('PLATE_SURFACE', G['plate'], curves_of(G['plate'].simplify(0.01), short=0.0))
    spec['CASE_OUTER'] = check('CASE_OUTER', G['case'], curves_of(G['case']))
    spec['CAVITY'] = check('CAVITY', G['inner'], curves_of(G['inner'].simplify(0.005), short=0.6))
    spec['TOP_RING_INNER'] = sum([check('TOP_RING_INNER', g, curves_of(g.simplify(0.005), short=0.6)) for g in getattr(G['opening'], 'geoms', [G['opening']])], [])
    spec['TB_POCKET'] = check('TB_POCKET', G['pocket'], curves_of(G['pocket'].simplify(0.01)), 0.15)
    spec['TOP_GUARD'] = sum([check('TOP_GUARD', g, curves_of(g.simplify(0.005), short=0.6)) for g in getattr(G['guard'], 'geoms', [G['guard']])], [])
    spec['TB_ACCESS'] = sum([check('TB_ACCESS', g, curves_of(g.simplify(0.005), short=0.6)) for g in getattr(G['access_cut'], 'geoms', [G['access_cut']])], [])
    spec['TB_SCREWS'] = [('circle', p, 1.0) for p in TB_SCREWS]
    spec['GASKET_POCKET'] = sum([curves_of(p, 0.05) for p in G['pockets']], [])
    spec['MAGNETS'] = [('circle', m, MAG_D / 2) for m in G['mags']]
    spec['TOP_MAG'] = spec['MAGNETS']
    spec['MCU_SCREWS'] = [('circle', s, INS_D / 2) for s in G['screws']]
    spec['FEET'] = [('circle', f, FOOT_D / 2) for f in G['feet']]
    Ls = json.load(open('left%s_spec.json' % SFX))
    spec['_usb_face_y'] = Ls['_usb_face_y']
    for k in ('USB_TUNNEL', 'USB_RCPT', 'MCU_RING', 'TOP_MCU_OPEN'):
        spec[k] = mirror_curves(Ls[k])
    spec['SW_OPEN'], spec['SW_SCOOP'] = Ls['SW_OPEN'], Ls['SW_SCOOP']          # (y, z): unchanged by the mirror
    spec['_sw'] = dict(Ls['_sw'], x=C2 - Ls['_sw']['x'], out=-1)
    spec['TILT_AXIS'] = Ls['TILT_AXIS']        # not mirrored: its direction sets the sense of the tilt
    spec['_rings'] = {'case': list(G['case'].exterior.coords), 'cav': list(G['inner'].exterior.coords), 'pocket': list(G['pocket'].exterior.coords)}
    json.dump(spec, open('right%s_spec.json' % SFX, 'w'))
    # trackball case STL placed in case coordinates (reference mesh / interference checks)
    d = bytearray(open('trackballcase.stl', 'rb').read()); n = struct.unpack('<I', d[80:84])[0]
    a = np.frombuffer(bytes(d[84:84 + 50 * n]), dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')])).copy()
    v = a['v'].reshape(-1, 3); v += np.array([TBX, TBY, -TB_ZREL0], dtype=np.float32); a['v'] = v.reshape(-1, 9)
    open('tb_placed%s.stl' % SFX, 'wb').write(bytes(d[:84]) + a.tobytes())
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(18, 14))
    def pl(g, c, lw=1):
        for gg in getattr(g, 'geoms', [g]):
            x, y = gg.exterior.xy; ax.plot(x, y, c, lw=lw)
    pl(G['case'].buffer(CLR + WALL), 'purple'); pl(G['case'], 'k', 2); pl(G['plate'], 'g'); pl(G['cav'], 'b'); pl(G['opening'], 'c'); [pl(g, 'orange', 2) for g in getattr(G['guard'], 'geoms', [G['guard']])]
    pl(G['pocket'], 'm'); pl(G['fp_all'], 'm', 0.5)
    x, y = G['access'].exterior.xy; ax.fill(x, y, color='orange', alpha=.25)
    for p in G['pockets']: pl(p, 'brown')
    pl(G['usb'], 'orange'); pl(G['sw'], 'orange')
    for m in G['mags']: ax.add_patch(plt.Circle(m, MAG_D / 2, color='r'))
    for s in G['screws']: ax.add_patch(plt.Circle(s, INS_D / 2, color='m'))
    for f in G['feet']: ax.add_patch(plt.Circle(f, FOOT_D / 2, fill=False, color='gray', ls='--'))
    for s in TB_SCREWS: ax.add_patch(plt.Circle(s, TB_CB_D / 2, color='k'))
    ax.set_aspect('equal'); ax.grid(True); ax.set_ylim(-150, 0)
    plt.savefig('right%s_geo.png' % SFX, dpi=50, bbox_inches='tight')
