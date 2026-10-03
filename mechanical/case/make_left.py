"""left case geometry -> left_spec.json (+ left_geo.png for review)"""
import json, pickle
from casegeo import *

def build_left():
    plate, _ = outline(B + 'mx_plate/mx_plate.kicad_pcb')
    pcb, _ = outline(B + 'mx_main/mx.kicad_pcb')
    spcb = sharp_pcb(B + 'mx_main/mx.kicad_pcb')
    tabs, body, info = tabs_and_body(plate, pcb)
    off = unary_union([spcb, body]).buffer(CASE_OFF, join_style=2, mitre_limit=10).buffer(2, join_style=2, mitre_limit=10).buffer(-2, join_style=2, mitre_limit=10)   # closing: no dimple from the magnet notch
    case0, arcinfo = back_arc_outline(off)
    case0 = unary_union([case0, case0.intersection(box(*STEP_FILL)).convex_hull])   # fill the outer step at the thumb cluster -> room for a phi6 magnet
    case = round_poly(case0, OUTER_R)
    # sharp corners where the PCB is convex, the PCB's own fillets where it is concave
    cav = Polygon(unary_union([spcb.buffer(0.3, join_style=2, mitre_limit=10), pcb.buffer(0.3, quad_segs=16)]).exterior).simplify(0.002)
    assert cav.contains(pcb.buffer(0.1)), 'cavity does not clear the PCB'
    opening = body.buffer(OPEN_CLR, quad_segs=16)
    inner = inner_outline(cav, opening, pcb)
    assert inner.contains(pcb.buffer(0.1)) and inner.contains(body.buffer(OPEN_CLR / 2))
    pockets = gasket_pockets(info)
    cx1 = case.bounds[2]; cy1 = case.bounds[3]
    usb = box(XIAO_X - USB_W / 2, USB_FACE_Y, XIAO_X + USB_W / 2, cy1 + 5)          # stops at the port face -> flush wall remains
    sw = box(SW_X_IN, SW_Y - SW_SCOOP[0] / 2, cx1 + 2, SW_Y + SW_SCOOP[0] / 2)
    mcu = box(*MCU_RING)
    walls = case.difference(cav).intersection(mcu).difference(usb.buffer(1.0)).difference(sw.buffer(1.0))
    screws = screw_spots(walls, 3)
    mags, band = magnet_spots(case, opening, cav, unary_union([p.buffer(1.0) for p in pockets] + [mcu, usb, sw, Point(MAG_NOTCH).buffer(10)]), N_MAG - 1)
    mags = [MAG_NOTCH] + mags          # the notch is cut to fit the magnet post exactly
    feet = feet_spots(case)
    guard = guard_region(inner, keycaps(B + 'mx_main/mx.kicad_pcb'), box(*GUARD_BOX))
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
    inner = G['inner']      # same curves for the cavity and the top ring -> flush inner wall
    spec['CAVITY'] = spec['TOP_RING_INNER'] = check('INNER', inner, curves_of(inner.simplify(0.005), short=0.6))
    spec['GASKET_POCKET'] = sum([curves_of(p, 0.05) for p in G['pockets']], [])
    spec['MAGNETS'] = [('circle', m, MAG_D / 2) for m in G['mags']]
    spec['TOP_MAG'] = spec['MAGNETS']
    spec['MCU_SCREWS'] = [('circle', s, INS_D / 2) for s in G['screws']]
    spec['FEET'] = [('circle', f, FOOT_D / 2) for f in G['feet']]
    x0, y0, x1, y1 = G['usb'].bounds
    # USB: sketched in the x-z plane at the port face (y = USB_FACE_Y); u = x, v = z
    spec['USB_TUNNEL'] = rrect(XIAO_X, USB_ZC, USB_W, USB_H, USB_R)
    spec['USB_RCPT'] = rrect(XIAO_X, USB_ZC, USB_RCPT_W, USB_RCPT_H, USB_RCPT_R)
    spec['_usb_face_y'] = USB_FACE_Y
    # slide switch: sketched in the y-z plane at the scoop floor (x = SW_X_FLOOR); u = y, v = z; outward = +x
    spec['SW_OPEN'] = rrect(SW_Y, SW_ZC, *SW_OPEN)
    spec['SW_SCOOP'] = rrect(SW_Y, SW_ZC, *SW_SCOOP)
    spec['_sw'] = {'x': SW_X_FLOOR, 'out': 1, 'in': SW_X_FLOOR - SW_X_IN}
    spec['TOP_GUARD'] = sum([check('TOP_GUARD', g, curves_of(g.simplify(0.005), short=0.6)) for g in getattr(G['guard'], 'geoms', [G['guard']])], [])
    spec['MCU_RING'] = rect(*MCU_RING)
    spec['TOP_MCU_OPEN'] = rect(*TOP_MCU_OPEN)
    spec['TILT_AXIS'] = [('line', (30, TILT_Y), (220, TILT_Y))]
    spec['_rings'] = {'case': list(case.exterior.coords), 'cav': list(G['inner'].exterior.coords)}
    json.dump(spec, open('left%s_spec.json' % SFX, 'w'))
    pickle.dump(G, open('left%s_geo.pkl' % SFX, 'wb'))
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(18, 14))
    def pl(g, c, lw=1):
        for gg in getattr(g, 'geoms', [g]):
            x, y = gg.exterior.xy; ax.plot(x, y, c, lw=lw)
    pl(case.buffer(CLR + WALL), 'purple'); pl(case, 'k', 2); pl(G['plate'], 'g'); pl(cav, 'b'); pl(opening, 'c'); pl(G['inner'], 'r'); [pl(g, 'orange', 2) for g in getattr(G['guard'], 'geoms', [G['guard']])]
    for p in G['pockets']: pl(p, 'brown')
    pl(G['usb'], 'orange'); pl(G['sw'], 'orange')
    for m in G['mags']: ax.add_patch(plt.Circle(m, MAG_D / 2, color='r'))
    for s in G['screws']: ax.add_patch(plt.Circle(s, INS_D / 2, color='m'))
    for f in G['feet']: ax.add_patch(plt.Circle(f, FOOT_D / 2, fill=False, color='gray', ls='--'))
    ax.axhline(USB_FACE_Y, color='orange', ls=':')
    ax.set_aspect('equal'); ax.grid(True)
    plt.savefig('left%s_geo.png' % SFX, dpi=50, bbox_inches='tight')
