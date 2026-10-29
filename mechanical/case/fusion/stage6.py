# right only: J1 parts as boxes in occurrence J1_REF (2026-10-29, j1_thin_pin.py), PCB top at -(plate_t + pcb_gap):
# the thin-pin right-angle header PHA-1x40RG in J1 (x 166.64; pins 0.5 sq 1.0 above the PCB, cut to 2.5, all in the socket;
# housing 2.0 x 2.0 against the socket; leads bent down 1.5 behind it, 3.0 from the pin centre), the 1-row round-pin socket on the
# sensor board (Akizuki 6604S, 4.2 out of the board, 2.54 sq round the pin row: 0.27 below the PCB top, over the tongue's cut-out)
# and the vertical sensor board (its +x face 158.94; hole row 5.0 above its bottom edge, so it hangs at the header's pin height)
exec(open('/Users/daiki/Projects/sage60/mechanical/case/fusion/fx.py').read())
YC, JX, PIN, ZP = -122.395, 166.64, 0.5, 1.0
SOCK = 158.94 + 4.2                     # socket face
HX = JX - 1.5 - 2.0                     # header housing's -x face = SOCK
BOXES = {   # name: (x0, x1, y0, y1, z0, z1) mm, z from the PCB top
    'SENSOR_BOARD': (157.34, 158.94, YC - 11.0, YC + 11.0, ZP - 5.0, ZP + 18.5),
    'J1_SOCKET': (158.94, SOCK, YC - 8.89, YC + 8.89, ZP - 1.27, ZP + 1.27),
    'J1_HEADER': (HX, HX + 2.0, YC - 8.89, YC + 8.89, 0.0, 2.0),
}
for n in range(7):
    y = YC + (n - 3) * 2.54
    BOXES['J1_LEAD_%d' % (n + 1)] = (HX + 2.0, JX + PIN / 2, y - PIN / 2, y + PIN / 2, ZP - PIN / 2, ZP + PIN / 2)
    BOXES['J1_TAIL_%d' % (n + 1)] = (JX - PIN / 2, JX + PIN / 2, y - PIN / 2, y + PIN / 2, ZP - 3.0, ZP - PIN / 2)

def run(_c):
    d = design(DOC); r = d.rootComponent
    for o in [o for o in r.occurrences if o.component.name.startswith('J1_REF')]: o.deleteMe()
    pcb_top = -(d.userParameters.itemByName('plate_t').value + d.userParameters.itemByName('pcb_gap').value) * 10
    occ = r.occurrences.addNewComponent(adsk.core.Matrix3D.create()); c = occ.component; c.name = 'J1_REF'
    tbm = adsk.fusion.TemporaryBRepManager.get()
    bf = c.features.baseFeatures.add(); bf.startEdit()
    for name, (x0, x1, y0, y1, z0, z1) in BOXES.items():
        z0, z1 = z0 + pcb_top, z1 + pcb_top
        ob = adsk.core.OrientedBoundingBox3D.create(P3(((x0 + x1) / 2, (y0 + y1) / 2), (z0 + z1) / 2), adsk.core.Vector3D.create(1, 0, 0),
                                                    adsk.core.Vector3D.create(0, 1, 0), (x1 - x0) / 10, (y1 - y0) / 10, (z1 - z0) / 10)
        b = c.bRepBodies.add(tbm.createBox(ob), bf); b.name = name
    bf.finishEdit()
    aps = [l.appearances.item(i) for l in app.materialLibraries for i in range(l.appearances.count)]   # names follow the UI language
    def look(*keys):
        a = [a for a in aps if any(k in a.name.lower() for k in keys)]
        return a and (d.appearances.itemByName(a[0].name) or d.appearances.addByCopy(a[0], a[0].name))
    looks = {'SENSOR_BOARD': look('green', '緑'), 'J1_SOCKET': look('black', '黒'), 'J1_HEADER': look('black', '黒'), 'J1_': look('gold', '金')}
    for b in c.bRepBodies:
        a = looks.get(b.name) or (looks['J1_'] if b.name.startswith('J1_') else None)
        if a: b.appearance = a
    bb = occ.boundingBox
    print('J1_REF', c.bRepBodies.count, 'bodies, bbox mm', [round(v * 10, 2) for v in (bb.minPoint.x, bb.minPoint.y, bb.minPoint.z, bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z)])
