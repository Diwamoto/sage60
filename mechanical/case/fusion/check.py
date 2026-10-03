# interference checks for both sides (run after stage3/4; needs checkpts.json from make_checkpts.py)
import adsk.core, adsk.fusion, json, struct
LP = globals().get('LP', False)                 # set LP=True in the exec globals for the low-profile documents
DOCN = 'sage60_lp_%s' if LP else 'sage60_%s_bottom'
def zs(r):
    """z stack from the document's parameters (mm): plate_t, pcb top, USB receptacle centre, trackball seat"""
    v = lambda n: r.parentDesign.userParameters.itemByName(n).value * 10
    pt, gap = v('plate_t'), v('pcb_gap'); top = -(pt + gap)
    seat = top - (v('tb_gap') + v('tb_leg_h')) if r.parentDesign.userParameters.itemByName('tb_gap') else None
    return pt, top, top + v('xiao_t') + v('usb_h_c') / 2, seat, v('mcu_cover_z'), v('usb_h')

def run(_c):
    app = adsk.core.Application.get()
    P = json.load(open('/Users/daiki/Projects/sage60/mechanical/case/checkpts.json'))
    IN = adsk.fusion.PointContainment.PointInsidePointContainment
    for side in globals().get('SIDES', ('left', 'right')):
        doc = [d for d in app.documents if d.name.startswith(DOCN % side)][0]
        r = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType')).rootComponent
        bodies = [r.bRepBodies.itemByName(n) for n in ('%s_bottom' % side, 'MOCK_A')]
        pt, top, zc, seat, _, _ = zs(r)
        res = {}
        for b in bodies:
            n_pcb = sum(1 for (x, y) in P[side]['pcb'] for z in (top - 0.1, top - 0.8, top - 1.5) if b.pointContainment(adsk.core.Point3D.create(x / 10, y / 10, z / 10)) == IN)
            n_pl = sum(1 for (x, y) in P[side]['plate'] for z in (-0.2, -pt / 2, -pt + 0.2) if b.pointContainment(adsk.core.Point3D.create(x / 10, y / 10, z / 10)) == IN)
            res[b.name] = (n_pcb, n_pl)
        tbm = adsk.fusion.TemporaryBRepManager.get(); ov = {}
        for m in bodies[1:]:
            a = tbm.copy(m); bb = tbm.copy(bodies[0]); tbm.booleanOperation(a, bb, adsk.fusion.BooleanTypes.IntersectionBooleanType)
            ov[m.name] = round(a.volume * 1000, 4) if a.faces.count else 0
        print(side, 'PCB/plate points inside (pcb, plate):', res, ' mock∩bottom mm3:', ov)
        # USB plug overmold corridor (12.5 x 7, from the port face outwards). The 15 x 9 recess has R1.5 in its back corners.
        x0 = 174.75 if side == 'left' else 245.84 - 187.25
        hit = sum(1 for b in bodies for i in range(26) for k in range(15) for j in range(30)
                  if b.pointContainment(adsk.core.Point3D.create((x0 + i * 0.5) / 10, (-27.0 + j * 0.5) / 10, (zc - 3.5 + k * 0.5) / 10)) == IN)
        print(side, 'USB corridor hits', hit)
        if side == 'right':
            data = open('/Users/daiki/Projects/sage60/mechanical/case/tb_placed%s.stl' % ('_lp' if LP else ''), 'rb').read(); n = struct.unpack('<I', data[80:84])[0]
            pts = set()
            for i in range(n):
                v = struct.unpack('<9f', data[84 + 50 * i + 12:84 + 50 * i + 48])
                for k in range(3): pts.add((v[3 * k], v[3 * k + 1], v[3 * k + 2]))
            hits = {b.name: sum(1 for p in pts if b.pointContainment(adsk.core.Point3D.create(p[0] / 10, p[1] / 10, (p[2] + 0.05) / 10)) == IN) for b in bodies}
            feet = [p for p in pts if abs(p[2] - seat) < 0.01]
            sup = sum(1 for p in feet if bodies[0].pointContainment(adsk.core.Point3D.create(p[0] / 10, p[1] / 10, (seat - 0.05) / 10)) == IN)
            print('right trackball verts inside', hits, 'of', len(pts), '; feet supported', sup, '/', len(feet))

def run_openings(_c):
    """USB flush wall + receptacle opening, slide-switch window"""
    app = adsk.core.Application.get(); IN = adsk.fusion.PointContainment.PointInsidePointContainment
    for side in globals().get('SIDES', ('left', 'right')):
        doc = [d for d in app.documents if d.name.startswith(DOCN % side)][0]
        r = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType')).rootComponent
        bodies = [r.bRepBodies.itemByName(n) for n in ('%s_bottom' % side, 'MOCK_A')]
        _, top, zc, _, mcz, uh = zs(r); dz = top + 5.0       # the numbers below are for the MX stack (PCB top -5.0)
        X = (lambda x: x) if side == 'left' else (lambda x: 245.84 - x)
        inside = lambda pts, bs: sum(1 for (x, y, z) in pts for b in bs if b.pointContainment(adsk.core.Point3D.create(X(x) / 10, y / 10, z / 10)) == IN)
        rng = lambda a, b, n: [a + (b - a) * i / (n - 1) for i in range(n)]
        import math   # receptacle body: stadium 8.94 x 3.26 centred (181.0, -2.37)
        rcpt = [(x, y, z) for x in rng(176.6, 185.4, 12) for y in rng(-34.3, -27.1, 10) for z in rng(zc - 1.58, zc + 1.57, 6)
                if math.hypot(max(abs(x - 181.0) - (4.47 - 1.63), 0), z - zc) <= 1.6]
        wall = [(x, y, z) for x in rng(174.0, 175.8, 4) + rng(186.2, 188.0, 4) for y in rng(-28.1, -27.2, 3) for z in rng(zc - 4.1, zc + 0.8, 6)]   # flush wall beside it
        knob = [(x, y, z) for x in rng(191.5, 197.0, 10) for y in rng(-52.3 - 1.6, -52.3 + 1.6, 6) for z in rng(top, top + 1.4, 4)]       # knob travel
        fill = [(194.0, y, -4.3 + dz) for y in (-61.0, -43.6)] + [(192.0, y, -4.3 + dz) for y in (-59.0, -45.6)] + [(192.0, -52.3, z + dz) for z in (-8.3, -0.3)]   # around scoop / opening
        reach = [(x, y, z) for x in (193.5, 196.0, 198.0) for y in (-58.3, -46.3) for z in (-8.5 + dz, -0.1 + dz)]                                           # scoop is empty (top + bottom)
        roof = [(x, y, z) for x in (178.0, 181.0, 184.0) for y in (-27.9, -27.4) for z in rng(zc + 2.15, mcz - 0.2, 3)] if mcz - 0.2 > zc + 2.15 else []   # closed above the receptacle opening
        roof += [(x, y, mcz - 0.2) for x in (176.0, 181.0, 186.0) for y in (-25.5, -23.5)] if mcz - 0.2 > zc + uh / 2 else []        # closed above the plug recess (LP: open notch)                                                 # closed above the plug recess
        print(side, 'receptacle hits', inside(rcpt, bodies), '| flush wall solid %d/%d' % (inside(wall, bodies[:1]), len(wall)),
              '| knob path hits', inside(knob, bodies), '| filled around switch %d/%d' % (inside(fill, bodies[:1]), len(fill)), '| scoop hits', inside(reach, bodies), '| closed above USB %d/%d' % (inside(roof, bodies[:1]), len(roof)))
