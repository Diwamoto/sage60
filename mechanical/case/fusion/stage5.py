# reference PCB + parts + switches + keycaps (models/<side>[_lp]_pcb.step from pcb_step.py) as occurrence PCB_REF, PCB top at -(plate_t + pcb_gap)
exec(open('/Users/daiki/Projects/sage60/mechanical/case/fusion/fx.py').read())

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
