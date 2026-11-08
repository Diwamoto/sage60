# reference PCB + parts + switches + keycaps (models/<side>[_lp]_pcb.step from pcb_step.py) as occurrence PCB_REF, PCB top at -(plate_t + pcb_gap)
exec(open('/Users/daiki/Projects/sage60/case/fusion/fx.py').read())

def run(_c):
    d = design(DOC); r = d.rootComponent
    for o in [o for o in r.occurrences if o.component.name.startswith('PCB_REF')]: o.deleteMe()
    v = lambda n: d.userParameters.itemByName(n).value          # cm
    m = adsk.core.Matrix3D.create()
    m.translation = adsk.core.Vector3D.create(0, 0, -(v('plate_t') + v('pcb_gap')) - 0.151)   # STEP board: bottom 0, top 1.51 mm
    # import into an occurrence that is already in place (moving the imported occurrence afterwards leaves some parts behind)
    occ = r.occurrences.addNewComponent(m); occ.component.name = 'PCB_REF'
    app.importManager.importToTarget(app.importManager.createSTEPImportOptions(SCR + 'models/%s%s_pcb.step' % (SIDE, SFX)), occ.component)
    bb = occ.boundingBox
    print(SIDE, 'PCB_REF bbox mm', [round(c * 10, 1) for c in (bb.minPoint.x, bb.minPoint.y, bb.minPoint.z, bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z)])

# SW32 = Switronic ISH-1260-HA-G (Akizuki 115370; KiCad has a pin header in its place): body 9.1 x 2.6 x 3.5 standing on its pins,
# the pin row 0.3 in from its back face, knob 2.0 out of the front face (toward the outer wall), 1.5 wide + travel 2, centred on the
# middle pin; z from the PCB top (knob height from the datasheet's front view, approximate)
    pin_x, sgn = (188.428, 1) if SIDE == 'left' else (245.84 - 188.428, -1)
    def xs(a, b): return tuple(sorted((pin_x + sgn * a, pin_x + sgn * b)))
    boxes = {'SW_BODY': (xs(-0.3, 2.3), (-54.864 - 4.55, -54.864 + 4.55), (0.0, 3.5)),
             'SW_KNOB': (xs(2.3, 4.3), (-54.864 - 1.75, -54.864 + 1.75), (1.0, 2.5))}
    for o in [o for o in r.occurrences if o.component.name.startswith('SW_REF')]: o.deleteMe()
    top = -(v('plate_t') + v('pcb_gap')) * 10
    so = r.occurrences.addNewComponent(adsk.core.Matrix3D.create()); c = so.component; c.name = 'SW_REF'
    tbm = adsk.fusion.TemporaryBRepManager.get(); bf = c.features.baseFeatures.add(); bf.startEdit()
    for name, ((x0, x1), (y0, y1), (z0, z1)) in boxes.items():
        ob = adsk.core.OrientedBoundingBox3D.create(P3(((x0 + x1) / 2, (y0 + y1) / 2), top + (z0 + z1) / 2), adsk.core.Vector3D.create(1, 0, 0),
                                                    adsk.core.Vector3D.create(0, 1, 0), (x1 - x0) / 10, (y1 - y0) / 10, (z1 - z0) / 10)
        c.bRepBodies.add(tbm.createBox(ob), bf).name = name
    bf.finishEdit()
