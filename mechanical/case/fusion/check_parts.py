# PCB_REF parts (XIAO, JST, header, switches, keycaps; keycaps also pressed by the travel) vs the case bodies.
# globals: SIDE, LP. Sockets / diodes / the board itself are covered by check.py's points. All volumes should be 0.
exec(open('/Users/daiki/Projects/sage60/mechanical/case/fusion/fx.py').read())
import collections
TRAVEL = 0.3 if LP else 0.4      # cm (Choc 3.0, MX 4.0)

def bodies(o):
    out = list(o.bRepBodies)
    for ch in o.childOccurrences: out += bodies(ch)
    return out

def run(_c):
    r = design(DOC).rootComponent; tbm = adsk.fusion.TemporaryBRepManager.get()
    case = [b for b in r.bRepBodies if b.name in ('%s_bottom' % SIDE, 'MOCK_A', 'MCU_COVER') or b.name.startswith('MOCK_B')]
    top = [o for o in r.occurrences if o.component.name.startswith('PCB_REF')][0].childOccurrences.item(0)
    down = adsk.core.Matrix3D.create(); down.translation = adsk.core.Vector3D.create(0, 0, -TRAVEL)
    hits = collections.Counter(); n = collections.Counter()
    for ch in top.childOccurrences:
        name = ch.component.name.split(' (')[0]
        if name == 'pcb_PCB' or 'Socket' in name or 'D_SOD' in name: continue
        for b in bodies(ch):
            n[name] += 1
            for pressed in ((False, True) if 'keycap' in name.lower() else (False,)):
                a = tbm.copy(b)
                if pressed: tbm.transform(a, down)
                for cb in case:
                    if not a.boundingBox.intersects(cb.boundingBox): continue
                    t = tbm.copy(a); tbm.booleanOperation(t, tbm.copy(cb), adsk.fusion.BooleanTypes.IntersectionBooleanType)
                    if t.faces.count and t.volume > 1e-6: hits[(name + (' pressed' if pressed else ''), cb.name)] += round(t.volume * 1000, 3)
    print(SIDE, 'LP' if LP else 'MX', dict(n), 'hits mm3:', dict(hits))
