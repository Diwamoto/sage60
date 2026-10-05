"""left case geometry -> left_spec.json (+ left_geo.png for review)"""
import json, pickle
from casegeo import *

def build_left():
    plate, _ = outline(B + 'mx_plate/mx_plate.kicad_pcb')
    pcb, _ = outline(B + 'mx_main/mx.kicad_pcb')
    spcb = sharp_pcb(B + 'mx_main/mx.kicad_pcb')
    tabs, body, info = tabs_and_body(plate, pcb)
    disc = Point(MAG_NOTCH).buffer(8.0)          # the magnet notch (r 4.45 + fillets since 2026-10-05) filled for the outline
    full = unary_union([spcb, body, spcb.intersection(disc).convex_hull, body.intersection(disc).convex_hull])
    off = full.buffer(CASE_OFF, join_style=2, mitre_limit=10).buffer(2, join_style=2, mitre_limit=10).buffer(-2, join_style=2, mitre_limit=10)
    case0, arcinfo = back_arc_outline(off)
    case0 = unary_union([case0, case0.intersection(box(*STEP_FILL)).convex_hull])   # fill the outer step at the thumb cluster -> room for a phi6 magnet
    # sharp corners where the PCB is convex, the PCB's own fillets where it is concave
    cav = Polygon(unary_union([spcb.buffer(0.3, join_style=2, mitre_limit=10), pcb.buffer(0.3, quad_segs=16)]).exterior).simplify(0.002)
    assert cav.contains(pcb.buffer(0.1)), 'cavity does not clear the PCB'
    opening = body.buffer(OPEN_CLR, quad_segs=16)
    post = Point(MAG_NOTCH).buffer(MAG_D / 2 + MAG_WALL)       # magnet wall in the notch: reliefs keep off it
    # CNC (2026-10-05): the top ring opening gets reliefs where the PCB outline keeps its corners tighter than RING_R; the cavity
    # contains it (flush wall) plus deeper reliefs for its depth (hidden under the ring)
    inner = relieve(inner_outline(cav, opening, pcb), RING_R, forbid=post)
    cavity = relieve(inner, lambda p: cnc_r(cav_depth(p)), forbid=post)
    assert inner.contains(pcb.buffer(0.1)) and inner.contains(body.buffer(OPEN_CLR / 2)), (inner.contains(pcb.buffer(0.1)), inner.contains(body.buffer(OPEN_CLR / 2)))
    assert cavity.buffer(1e-6).contains(inner), inner.difference(cavity).area
    # magnet at the thumb step (front left): MAG_WALL 0.8 (2026-10-05) needs the outline pushed out a little there
    pockets = gasket_pockets(info)                       # top slots (end inside the ring)
    pockets_b = list(fix_cuts({i: p for i, p in enumerate(gasket_pockets(info, POCKET_OUT_B))}, Polygon(case0.exterior).difference(cavity)).values())   # bottom: run out past the wall
    keep0 = unary_union([p.buffer(1.0) for p in pockets + pockets_b] + [Point(MAG_NOTCH).buffer(10)])
    case0 = ensure_boss(case0, MAG_NOTCH)                 # low profile: CASE_OFF 3.5 left 0.6 outside the notch magnet
    case_base = round_poly(case0, OUTER_R, CONCAVE_R)     # before the magnet bump (the right case mirrors this)
    mag_step, case0 = magnet_bump(case0, inner, cavity, keep0, MAG_STEP)
    case = round_poly(case0, OUTER_R, CONCAVE_R)          # concave corners: the top wall outside them is ~31 mm tall (CNC)
    mcu_open, mcu = mcu_regions(case)
    slots = port_slots(case)
    fixed = fix_cuts({k: v[0] for k, v in slots.items()}, case.difference(cavity))      # no fins between the slots and the cavity reliefs
    slots = {k: (fixed[k], slots[k][1]) for k in slots}
    usb = unary_union([slots['USB_RECESS'][0], slots['USB_RCPT'][0]]); sw = unary_union([slots['SW_SCOOP'][0], slots['SW_OPEN'][0]])
    walls = case.difference(cavity).intersection(mcu).difference(usb.buffer(1.0)).difference(sw.buffer(1.0))
    screws = screw_spots(walls, 3)
    mags, band = magnet_spots(case, inner, cavity, unary_union([p.buffer(1.0) for p in pockets + pockets_b] + [mcu_open, usb, sw, Point(MAG_NOTCH).buffer(10), Point(mag_step).buffer(10)]), N_MAG - 2)
    mags = [MAG_NOTCH, mag_step] + mags          # the notch is cut to fit the magnet post exactly
    feet = feet_spots(case)
    guard = guard_fill(inner, guard_region(inner, keycaps(B + 'mx_main/mx.kicad_pcb'), box(*GUARD_BOX)))
    return locals()

if __name__ == '__main__':
    G = build_left()
    case, cav, opening = G['case'], G['cav'], G['opening']
    a = G['arcinfo']; top_at_usb = max(c[1] for c in case.intersection(LineString([(XIAO_X, -100), (XIAO_X, 50)])).coords)
    print('arc r=%.1f sag=%.2f  case back at USB y=%.2f -> top-case outer %.2f, port face %.2f, recess depth %.2f'
          % (a['r'], a['sag'], top_at_usb, top_at_usb + CLR + WALL, USB_FACE_Y, top_at_usb + CLR + WALL - USB_FACE_Y))
    print('bezel (opening edge -> top wall outer) ~', CASE_OFF - OPEN_CLR + CLR + WALL)
    print('screws', [tuple(round(v, 2) for v in s) for s in G['screws']])
    print('magnets', [tuple(round(v, 2) for v in s) for s in G['mags']])
    print('feet', [tuple(round(v, 2) for v in s) for s in G['feet']])
    spec = {}
    spec['PLATE_SURFACE'] = check('PLATE_SURFACE', G['plate'], curves_of(G['plate'].simplify(0.01), short=0.0), 0.08)
    spec['CASE_OUTER'] = check('CASE_OUTER', case, curves_of(case))
    inner = G['inner']      # top ring opening; the cavity = the same + hidden CNC reliefs -> flush inner wall
    spec['TOP_RING_INNER'] = check('TOP_RING_INNER', inner, curves_of(inner.simplify(0.005), short=0.6))
    spec['CAVITY'] = check('CAVITY', G['cavity'], curves_of(G['cavity'].simplify(0.005), short=0.6))
    spec['GASKET_POCKET'] = sum([fit('GASKET_POCKET', p) for p in G['pockets_b']], [])
    spec['TOP_GASKET_SLOT'] = sum([fit('TOP_GASKET_SLOT', p) for p in G['pockets']], [])
    spec['MAGNETS'] = [('circle', m, MAG_D / 2) for m in G['mags']]
    spec['TOP_MAG'] = spec['MAGNETS']
    spec['MCU_SCREWS'] = [('circle', s, INS_D / 2) for s in G['screws']]
    spec['FEET'] = [('circle', f, FOOT_D / 2) for f in G['feet']]
    # USB / slide switch: plan slots cut from z_bottom up through both cases (CNC: no side machining, 2026-10-05)
    for k, (poly, z0) in G['slots'].items():
        spec[k] = check(k, poly, curves_of(poly.simplify(0.005), short=0.3))
    pcbtop = '-( plate_t + pcb_gap )'
    spec['_slot_z'] = {'USB_RECESS': pcbtop + ' + xiao_t + usb_h_c / 2 - usb_h / 2', 'USB_RCPT': pcbtop + ' + xiao_t + usb_h_c / 2 - usb_rcpt_h / 2',
                       'SW_SCOOP': pcbtop + ' + %.2f mm' % (SW_ZC - PCB_TOP - SW_SCOOP[1] / 2), 'SW_OPEN': pcbtop + ' + %.2f mm' % (SW_ZC - PCB_TOP - SW_OPEN[1] / 2)}
    spec['TOP_GUARD'] = sum([fit('TOP_GUARD', g) for g in getattr(G['guard'], 'geoms', [G['guard']])], [])
    spec['MCU_RING'] = fit('MCU_RING', G['mcu'])
    spec['TOP_MCU_OPEN'] = fit('TOP_MCU_OPEN', G['mcu_open'])
    spec['TILT_AXIS'] = [('line', (30, TILT_Y), (220, TILT_Y))]
    spec['_rings'] = {'case': list(case.exterior.coords), 'cav': list(G['cavity'].exterior.coords)}
    json.dump(spec, open('left%s_spec.json' % SFX, 'w'))
    pickle.dump(G, open('left%s_geo.pkl' % SFX, 'wb'))
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(18, 14))
    def pl(g, c, lw=1):
        for gg in getattr(g, 'geoms', [g]):
            x, y = gg.exterior.xy; ax.plot(x, y, c, lw=lw)
    pl(case.buffer(CLR + WALL), 'purple'); pl(case, 'k', 2); pl(G['plate'], 'g'); pl(cav, 'b'); pl(opening, 'c'); pl(G['inner'], 'r'); pl(G['cavity'], 'm'); [pl(g, 'orange', 2) for g in getattr(G['guard'], 'geoms', [G['guard']])]
    for p in G['pockets']: pl(p, 'brown')
    pl(G['usb'], 'orange'); pl(G['sw'], 'orange')
    for m in G['mags']: ax.add_patch(plt.Circle(m, MAG_D / 2, color='r'))
    for s in G['screws']: ax.add_patch(plt.Circle(s, INS_D / 2, color='m'))
    for f in G['feet']: ax.add_patch(plt.Circle(f, FOOT_D / 2, fill=False, color='gray', ls='--'))
    ax.axhline(USB_FACE_Y, color='orange', ls=':')
    ax.set_aspect('equal'); ax.grid(True)
    plt.savefig('left%s_geo.png' % SFX, dpi=50, bbox_inches='tight')
