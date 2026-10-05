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
MAG_A2 = (C2 - MAG_NOTCH[0], MAG_NOTCH[1])     # magnet in the right PCB's notch = the shared plate's notch flipped (notch_fillet.py)
MAG_B = (185.5, -110.5)                       # magnet at the right front corner; the outline grows round it (2026-10-05)
import os
DEBUG = os.environ.get('DEBUG') == '1'
THIN_TOP, THIN_BOT = 3.0, 2.0       # around the trackball, top / bottom case parts narrower than this are cut away (slivers where the cuts meet the outline)
TB_SCREWS = [(TBX + 9.59, TBY - 7.72), (TBX + 9.59, TBY + 8.48)]   # hex bosses of the trackball case
TB_CB_D = 3.6
FRONT_LOW_R = 2.0                   # lowered frame in front of the trackball: corner R
FRONT_N = ((-0.431, -0.902), (0.888, -0.459))   # outward normals of the outline's left / right edges beside the trackball

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
    # top ring opening: plate body + open_clr, keycaps + KEY_CLR, trackball hole -> the top case covers the bare PCB around the trackball
    caps = unary_union(keycaps(B + 'mx_right_tb/mx_right_tb.kicad_pcb')).buffer(2.5, join_style=2).buffer(-2.5, join_style=2)
    keyhole = opening_rounded(unary_union([body.buffer(OPEN_CLR, quad_segs=16), caps.buffer(KEY_CLR - GUARD_R, join_style=2).buffer(GUARD_R, quad_segs=16)]), 1.5)
    keyhole, tbhole = relieve(keyhole, RING_R), relieve(tbhole, RING_R)
    opening = unary_union([keyhole, tbhole]).buffer(0)          # each rounded on its own: rounding the union pinched off the sensor housing
    opening = MultiPolygon([Polygon(g.exterior) for g in getattr(opening, 'geoms', [opening])]) if opening.geom_type == 'MultiPolygon' else Polygon(opening.exterior)   # two loops once the top case runs between them (2026-10-04)
    # cavity: PCB + 0.3 / plate body + open_clr, with CNC reliefs for its depth; the A2 magnet post (PCB notch) stays whole
    post = Point(MAG_A2).buffer(MAG_D / 2 + MAG_WALL)
    inner = inner_outline(cav, body.buffer(OPEN_CLR, quad_segs=16), pcb)
    assert inner.contains(pcb.buffer(0.1)) and inner.contains(body.buffer(OPEN_CLR / 2))
    cavity = relieve(inner, lambda p: cnc_r(cav_depth(p, side=-1)), forbid=post)
    # outline: mirrored left (before its thumb-step magnet) + the trackball envelope.  Tight to the keys and the trackball
    # (2026-10-05): the case's own outline, the envelope (its hull in front of the ball centre: the only curves) and PCB + 3;
    # straight lines elsewhere, R CONCAVE_R where they meet (the top wall outside is ~31 mm tall)
    case_m = mirror_poly(L['case_base'])
    front_y = case_m.bounds[1]
    enc = unary_union([pocket.buffer(THIN_BOT + 0.2, quad_segs=16), tbhole.buffer(max(THIN_TOP - CLR - WALL, 0) + 0.2, quad_segs=16)])
    encf = enc.intersection(box(0, -250, 250, TBY)).convex_hull
    # the notch between the thumb cluster's right edge and the trackball: bridged by a straight line (it left a top case strip
    # under the thumb access that the sliver cut ate down the trackball hole)
    notch = unary_union([case_m.intersection(box(100, -130, 112, -115)), encf.intersection(box(110, -145, 121, -120))]).convex_hull
    ext = unary_union([case_m, encf, notch, pcb.buffer(3.0, join_style=2)])   # PCB at least 3 inside: bottom wall >= THIN_BOT outside the cavity
    ext = ext.buffer(CONCAVE_R, quad_segs=16).buffer(-CONCAVE_R, quad_segs=16)
    ext = ensure_boss(ext, MAG_A2)
    pockets = gasket_pockets(info)                       # top slots
    pockets_b = gasket_pockets(info, POCKET_OUT_B)       # bottom pockets (run out past the wall)
    # thumb access region (no top case, lowered deck)
    a, b = np.array((104.957, -117.72)), np.array((100.95, -102.81))      # thumb cluster right edge (PCB)
    d = (b - a) / np.linalg.norm(b - a); n = np.array((-d[1], d[0]))
    if n[0] < 0: n = -n
    c = a + n * RIM; top = c + d * ((-95 - c[1]) / d[1])
    access = opening_rounded(Polygon([tuple(top), tuple(c), (c[0], -220), (X_R, -220), (X_R, -95)]), 2.0)
    # magnet B at the right front corner (2026-10-05, user: a bump just big enough for it is fine)
    keep0 = unary_union([p.buffer(1.0) for p in pockets + pockets_b] + [access.buffer(3.0), tbhole.buffer(1.0), pocket.buffer(1.0), post.buffer(10)])
    mag_b, ext = magnet_bump(ext, opening, cavity, keep0, MAG_B)
    case = round_poly(ext, OUTER_R, CONCAVE_R)
    protrude = case.bounds[1] - fp_all.bounds[1]
    # top case cut / lowered deck: the thumb access behind the ball centre.  (2026-10-03 the top case covered the PCB in it; between
    # the trackball and row 4 that left 2-4 mm strips, hard to print -> dropped 2026-10-04, the PCB edge shows there.)
    # In front of the ball centre the case encloses the trackball case (2026-10-04).
    access_cut = opening_rounded(access.intersection(box(0, TBY, 250, 0)), 2.0)
    # cut away what is left thinner than THIN near the trackball: top case (ring + skirt) and the bottom above the deck share TB_ACCESS,
    # the bottom below the deck goes into TB_POCKET.  CNC: TB_ACCESS goes through the whole top case (R for its height), the pocket
    # is ~8 deep (RING_R), and where the pocket meets the cavity the corners get reliefs too.
    near = access.buffer(8.0)
    def slivers(solid, w):
        t = solid.difference(solid.buffer(-w / 2, quad_segs=16).buffer(w / 2, quad_segs=16)).intersection(near)
        return unary_union([q.buffer(0.05) for q in getattr(t, 'geoms', [t]) if q.area > 0.5])
    acc_r = lambda p: RING_R if case.buffer(-0.5).contains(p) else cnc_r(TOP_H - desk_z(p.y))    # inside the skirt only the ring (8.2) is cut
    for it in range(10):
        sl = unary_union([slivers(case.buffer(CLR + WALL).difference(opening).difference(access_cut), THIN_TOP), slivers(case.difference(cavity).difference(pocket).difference(access_cut), THIN_BOT)])
        sp = slivers(case.difference(cavity).difference(pocket), THIN_BOT)
        u = unary_union([cavity, pocket])
        rp = relieve(Polygon(u.exterior) if u.geom_type == 'Polygon' else u, RING_R, forbid=post).difference(u)
        ua = unary_union([access_cut, opening]).buffer(0)         # the top case's openings together: its inner corners are their convex corners
        ra = relieve(ua, acc_r).difference(ua)
        if DEBUG: print(it, 'sl', [(round(q.centroid.x,1), round(q.centroid.y,1), round(q.area,2)) for q in getattr(sl,'geoms',[sl]) if not q.is_empty], 'sp', [(round(q.centroid.x,1), round(q.centroid.y,1), round(q.area,2)) for q in getattr(sp,'geoms',[sp]) if not q.is_empty], 'rp', round(rp.area,3), [(round(q.centroid.x,1), round(q.centroid.y,1)) for q in getattr(rp,'geoms',[rp]) if not q.is_empty][:4], 'ra', round(ra.area,3), [(round(q.centroid.x,1), round(q.centroid.y,1)) for q in getattr(ra,'geoms',[ra]) if not q.is_empty][:4])
        if sl.is_empty and sp.is_empty and rp.area < 1e-3 and ra.area < 1e-3: break
        access_cut = unary_union([access_cut, sl, ra]).buffer(0)
        pocket = unary_union([pocket, sp, rp]).buffer(0)
        pocket = Polygon(max(getattr(pocket, 'geoms', [pocket]), key=lambda g: g.area).exterior) if pocket.geom_type == 'MultiPolygon' and min(g.area for g in pocket.geoms) < 0.01 else pocket
    else:
        raise AssertionError('slivers did not converge')
    # small detached access pieces (the rim's tip at the key opening) overlap the opening a little: no hairline material between
    access_cut = unary_union([g if g.area > 5.0 else g.buffer(0.15) for g in getattr(access_cut, 'geoms', [access_cut])]).buffer(0)
    ua = unary_union([access_cut, opening]).buffer(0)
    access_cut = unary_union([access_cut, relieve(ua, acc_r).difference(ua)]).buffer(0)      # the corners that join made
    ring = case.buffer(CLR + WALL).difference(opening).difference(access_cut)
    islands = [g for g in getattr(ring, 'geoms', [ring]) if g.area < 0.5 * ring.area and g.area < 20.0]
    if islands: access_cut = unary_union([access_cut] + [g.buffer(0.05) for g in islands]).buffer(0)   # loose specks of top case go too
    # in front of the ball centre the frame round the trackball case is lowered by tb_front_drop (2026-10-05, user: keep the frame,
    # take its top off where it hugs the cup).  A pocket from the top whose sides cross the wall square to it (the outline's outward
    # normals FRONT_N), starting where the thumb access's front corners face the same way (square to them too: no wedges)
    acc = max(getattr(access_cut, 'geoms', [access_cut]), key=lambda g: g.area)
    ap = np.array(acc.exterior.coords)
    ends = []
    for n in map(np.array, FRONT_N):
        p = ap[np.argmax(ap @ n)]
        ends.append((tuple(p - 5 * n), tuple(p + 60 * n)))
    (l0, l1), (r0, r1) = ends
    front_low = opening_rounded(Polygon([l0, l1, (l1[0], -250), (r1[0], -250), r1, r0]), FRONT_LOW_R)
    # MCU / USB / switch: mirrored from the left
    usb = mirror_poly(L['usb']); sw = mirror_poly(L['sw']); mcu = mirror_poly(L['mcu']); mcu_open = mirror_poly(L['mcu_open'])
    screws = [(C2 - x, y) for x, y in L['screws']]
    keep = unary_union([p.buffer(1.0) for p in pockets + pockets_b] + [mcu_open, usb, sw, access_cut.buffer(1.0), tbhole.buffer(1.0), pocket.buffer(1.0), post.buffer(10), Point(mag_b).buffer(10)])
    mags, band = magnet_spots(case, opening, cavity, keep, N_MAG - 2)
    mags = [MAG_A2, mag_b] + mags
    guard = guard_fill(keyhole, guard_region(keyhole, keycaps(B + 'mx_right_tb/mx_right_tb.kicad_pcb'), mirror_poly(box(*GUARD_BOX)).difference(unary_union([tbhole, access]).buffer(3.0))))
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
    spec['CAVITY'] = fit('CAVITY', G['cavity'])
    spec['TOP_RING_INNER'] = sum([fit('TOP_RING_INNER', g) for g in getattr(G['opening'], 'geoms', [G['opening']])], [])
    spec['TB_POCKET'] = fit('TB_POCKET', G['pocket'], 0.15)
    spec['TOP_GUARD'] = sum([fit('TOP_GUARD', g) for g in getattr(G['guard'], 'geoms', [G['guard']])], [])
    spec['TB_ACCESS'] = sum([fit('TB_ACCESS', g) for g in getattr(G['access_cut'], 'geoms', [G['access_cut']])], [])
    spec['TB_FRONT_LOW'] = fit('TB_FRONT_LOW', G['front_low'])
    spec['TB_SCREWS'] = [('circle', p, 1.0) for p in TB_SCREWS]
    spec['GASKET_POCKET'] = sum([fit('GASKET_POCKET', p) for p in G['pockets_b']], [])
    spec['TOP_GASKET_SLOT'] = sum([fit('TOP_GASKET_SLOT', p) for p in G['pockets']], [])
    spec['MAGNETS'] = [('circle', m, MAG_D / 2) for m in G['mags']]
    spec['TOP_MAG'] = spec['MAGNETS']
    spec['MCU_SCREWS'] = [('circle', s, INS_D / 2) for s in G['screws']]
    spec['FEET'] = [('circle', f, FOOT_D / 2) for f in G['feet']]
    Ls = json.load(open('left%s_spec.json' % SFX))
    for k in ('USB_RECESS', 'USB_RCPT', 'SW_SCOOP', 'SW_OPEN', 'MCU_RING', 'TOP_MCU_OPEN'):
        spec[k] = mirror_curves(Ls[k])
    spec['_slot_z'] = Ls['_slot_z']
    spec['TILT_AXIS'] = Ls['TILT_AXIS']        # not mirrored: its direction sets the sense of the tilt
    spec['_rings'] = {'case': list(G['case'].exterior.coords), 'cav': list(G['cavity'].exterior.coords), 'pocket': list(G['pocket'].exterior.coords)}
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
    pl(G['case'].buffer(CLR + WALL), 'purple'); pl(G['case'], 'k', 2); pl(G['plate'], 'g'); pl(G['cavity'], 'b'); pl(G['opening'], 'c'); [pl(g, 'orange', 2) for g in getattr(G['guard'], 'geoms', [G['guard']])]
    pl(G['pocket'], 'm'); pl(G['fp_all'], 'm', 0.5)
    x, y = G['access'].exterior.xy; ax.fill(x, y, color='orange', alpha=.25)
    x, y = G['front_low'].exterior.xy; ax.fill(x, y, color='cyan', alpha=.25)
    for p in G['pockets']: pl(p, 'brown')
    pl(G['usb'], 'orange'); pl(G['sw'], 'orange')
    for m in G['mags']: ax.add_patch(plt.Circle(m, MAG_D / 2, color='r'))
    for s in G['screws']: ax.add_patch(plt.Circle(s, INS_D / 2, color='m'))
    for f in G['feet']: ax.add_patch(plt.Circle(f, FOOT_D / 2, fill=False, color='gray', ls='--'))
    for s in TB_SCREWS: ax.add_patch(plt.Circle(s, TB_CB_D / 2, color='k'))
    ax.set_aspect('equal'); ax.grid(True); ax.set_ylim(-150, 0)
    plt.savefig('right%s_geo.png' % SFX, dpi=50, bbox_inches='tight')
