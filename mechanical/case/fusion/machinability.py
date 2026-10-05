# CNC (JLCCNC, 3-axis, two setups) check on the B-Rep.  globals: SIDE, LP
#   setups: bottom case = plate normal from the top + desk normal from below; top case = plate normal from the top and from below
#   1 undercut   : every face sample must be reachable along one setup axis (ray to infinity clear of the same body)
#   2 sharp      : no sharp concave edge parallel to a setup axis (an end mill leaves its radius there)
#   3 radius     : concave walls parallel to an axis: R >= H / 10 + 0.5 (H = wall height along the axis, JLCCNC guideline)
#   4 holes      : full cylinders (drilled): depth <= 4 x diameter
#   5 thin       : wall thickness >= THIN_MIN (JLCCNC metal: 0.8 recommended, 0.5 minimum)
exec(open('/Users/daiki/Projects/sage60/mechanical/case/fusion/fx.py').read())
THIN_MIN = 0.8
LEFT_MAX = 0.05      # material a tool of the required radius leaves in a concave corner (JLCCNC default tolerance +-0.1)
P3c = adsk.core.Point3D.create
V3 = adsk.core.Vector3D.create

def run(_c):
    d = design(DOC); r = d.rootComponent
    desk = r.constructionPlanes.itemByName('DESK_PLANE').geometry.normal.copy()
    if desk.z > 0: desk.scaleBy(-1)                     # pointing out of the bottom (towards the tool of setup 2)
    up = V3(0, 0, 1); dn = V3(0, 0, -1)
    report = {}
    which = globals().get('BODIES', ('%s_bottom' % SIDE, 'MOCK_A'))
    for bname, dirs in (('%s_bottom' % SIDE, (up, desk)), ('MOCK_A', (up, dn))):
        if bname not in which: continue
        src = r.bRepBodies.itemByName(bname)
        occ = r.occurrences.addNewComponent(adsk.core.Matrix3D.create()); occ.component.name = 'CNC_CHECK'
        body = src.copyToComponent(occ); comp = occ.component
        for b in r.bRepBodies: b.isLightBulbOn = False
        res = {'undercut': [], 'sharp': [], 'radius': [], 'holes': [], 'thin': []}
        mm = lambda p: (round(p.x * 10, 1), round(p.y * 10, 1), round(p.z * 10, 1))
        def blocked(p, v):
            hits = adsk.core.ObjectCollection.create(); pts = adsk.core.ObjectCollection.create()
            ents = comp.findBRepUsingRay(p, v, adsk.fusion.BRepEntityTypes.BRepFaceEntityType, 0.00001, False, pts)
            for i in range(ents.count):
                f = ents.item(i)
                if pts.item(i).distanceTo(p) > 0.0005: return True      # CNC_CHECK holds only this body
            return False
        def outward(p, nn):
            q = p.copy(); t = nn.copy(); t.scaleBy(0.0003); q.translateBy(t)
            if body.pointContainment(q) == adsk.fusion.PointContainment.PointInsidePointContainment: nn = nn.copy(); nn.scaleBy(-1)
            return nn
        def samples(f, n=3):
            ev = f.evaluator; rng = ev.parametricRange()
            out = []
            for a in [(i + 0.5) / n for i in range(n)]:
                for b in [(j + 0.5) / n for j in range(n)]:
                    uv = adsk.core.Point2D.create(rng.minPoint.x + a * (rng.maxPoint.x - rng.minPoint.x), rng.minPoint.y + b * (rng.maxPoint.y - rng.minPoint.y))
                    if not ev.isParameterOnFace(uv): continue
                    _, p = ev.getPointAtParameter(uv); _, nn = ev.getNormalAtParameter(uv)
                    out.append((uv, p, outward(p, nn)))
            return out
        for f in body.faces:
            S = samples(f)
            # 1 undercut
            bad = 0
            for uv, p, nn in S:
                q = p.copy(); t = nn.copy(); t.scaleBy(0.001); q.translateBy(t)
                if not any(nn.dotProduct(v) > -1e-3 and not blocked(q, v) for v in dirs): bad += 1
            if bad: res['undercut'].append((mm(S[0][1]), bad, len(S), f.geometry.objectType.split('::')[-1]))
            # 3/4 concave walls parallel to an axis
            for v in dirs:
                if not S or any(abs(nn.dotProduct(v)) > 0.02 for _, _, nn in S): continue
                if f.geometry.objectType.endswith('Plane'): continue
                bb = f.boundingBox
                cs = [P3c(x, y, z) for x in (bb.minPoint.x, bb.maxPoint.x) for y in (bb.minPoint.y, bb.maxPoint.y) for z in (bb.minPoint.z, bb.maxPoint.z)]
                h = (max(c.x * v.x + c.y * v.y + c.z * v.z for c in cs) - min(c.x * v.x + c.y * v.y + c.z * v.z for c in cs)) * 10
                # curvature from neighbouring samples across the wall (same height): concave if the normal turns against the motion
                ev = f.evaluator; rng = ev.parametricRange(); rads = []
                for a in (0.2, 0.5, 0.8):
                    for b in (0.1, 0.3, 0.5, 0.7, 0.9):
                        for uvs in ((adsk.core.Point2D.create(rng.minPoint.x + a * (rng.maxPoint.x - rng.minPoint.x), rng.minPoint.y + (b - 0.04) * (rng.maxPoint.y - rng.minPoint.y)),
                                     adsk.core.Point2D.create(rng.minPoint.x + a * (rng.maxPoint.x - rng.minPoint.x), rng.minPoint.y + (b + 0.04) * (rng.maxPoint.y - rng.minPoint.y))),
                                    (adsk.core.Point2D.create(rng.minPoint.x + (b - 0.04) * (rng.maxPoint.x - rng.minPoint.x), rng.minPoint.y + a * (rng.maxPoint.y - rng.minPoint.y)),
                                     adsk.core.Point2D.create(rng.minPoint.x + (b + 0.04) * (rng.maxPoint.x - rng.minPoint.x), rng.minPoint.y + a * (rng.maxPoint.y - rng.minPoint.y)))):
                            if not all(ev.isParameterOnFace(u) for u in uvs): continue
                            (_, p1), (_, p2) = ev.getPointAtParameter(uvs[0]), ev.getPointAtParameter(uvs[1])
                            (_, n1), (_, n2) = ev.getNormalAtParameter(uvs[0]), ev.getNormalAtParameter(uvs[1])
                            n1, n2 = outward(p1, n1), outward(p2, n2)
                            dp = p1.vectorTo(p2); dn_ = V3(n2.x - n1.x, n2.y - n1.y, n2.z - n1.z)
                            # only the component across the axis
                            k = dp.dotProduct(v); dp = V3(dp.x - v.x * k, dp.y - v.y * k, dp.z - v.z * k)
                            if dp.length < 1e-5 or dn_.length < 1e-6: continue
                            if dp.dotProduct(dn_) < 0: rads.append(dp.length / dn_.length * 10)
                if not rads: continue
                rr = min(rads)
                ns = [V3(nn.x - v.x * nn.dotProduct(v), nn.y - v.y * nn.dotProduct(v), nn.z - v.z * nn.dotProduct(v)) for _, _, nn in S]
                for q in ns: q.normalize()
                span = max(math.acos(max(-1.0, min(1.0, a.dotProduct(b)))) for a in ns for b in ns) if len(ns) > 1 else 0
                span *= 1.5          # samples sit inside the face (1/6 .. 5/6 of its range)
                if f.loops.count >= 2 and f.geometry.objectType.endswith('Cylinder'):      # full cylinder: drilled hole
                    if h > 4 * 2 * rr + 0.01: res['holes'].append((mm(S[0][1]), 'D%.2f depth %.1f' % (2 * rr, h)))
                elif rr < h / 10 + 0.5 - 0.05:
                    Rq = h / 10 + 0.5
                    left = (Rq - rr) * (1 / math.cos(min(span, 3.1) / 2) - 1)
                    if left > LEFT_MAX: res['radius'].append((mm(S[0][1]), 'R%.2f < R%.2f (H %.1f) span %.0fdeg left %.2f' % (rr, Rq, h, math.degrees(span), left)))
            # 5 thin walls (tiny faces from curve fitting at corners are skipped)
            bbf = f.boundingBox; span_f = max(bbf.maxPoint.x - bbf.minPoint.x, bbf.maxPoint.y - bbf.minPoint.y, bbf.maxPoint.z - bbf.minPoint.z) * 10
            for uv, p, nn in (S if f.area * 100 / max(span_f, 1e-6) > 0.2 else []):     # faces narrower than 0.2 mm: curve-fit specks below the tolerance
                q = p.copy(); t = nn.copy(); t.scaleBy(-0.0005); q.translateBy(t)
                inn = nn.copy(); inn.scaleBy(-1)
                pts = adsk.core.ObjectCollection.create()
                ents = comp.findBRepUsingRay(q, inn, adsk.fusion.BRepEntityTypes.BRepFaceEntityType, 0.00001, False, pts)
                def facing(i):        # a wall has two opposite faces; a ray leaving through a side face is a convex corner, not a wall
                    h = ents.item(i); _, uvh = h.evaluator.getParameterAtPoint(pts.item(i)); _, nh = h.evaluator.getNormalAtParameter(uvh)
                    return abs(nh.dotProduct(nn)) > 0.5
                ds = [pts.item(i).distanceTo(q) * 10 for i in range(ents.count) if pts.item(i).distanceTo(q) > 0.001 and ents.item(i).tempId != f.tempId and facing(i)]      # not the face itself (its own surface, e.g. a tiny corner cylinder)
                if ds and min(ds) < THIN_MIN - 0.01:
                    res['thin'].append((mm(p), round(min(ds), 2))); break
        # 2 sharp concave edges parallel to an axis
        for e in body.edges:
            g = e.geometry
            if not g.objectType.endswith('Line3D') or e.faces.count != 2: continue
            dvec = g.startPoint.vectorTo(g.endPoint)
            if dvec.length < 0.005: continue
            dvec.normalize()
            if not any(abs(dvec.dotProduct(v)) > 0.995 for v in dirs): continue
            mid = P3c((g.startPoint.x + g.endPoint.x) / 2, (g.startPoint.y + g.endPoint.y) / 2, (g.startPoint.z + g.endPoint.z) / 2)
            f1, f2 = e.faces.item(0), e.faces.item(1)
            width = lambda f: f.area / max(e.length, 1e-6) * 10       # mm, across the edge
            if min(width(f1), width(f2)) < 0.2: continue                 # curve-fit specks (micro arcs) below the tolerance
            _, n1 = f1.evaluator.getNormalAtPoint(mid); _, n2 = f2.evaluator.getNormalAtPoint(mid)
            # outward: test a little inside each face away from the edge
            def side(f, nn):                       # orient nn like the outward normal found on the face just next to the edge
                ev = f.evaluator
                v = mid.vectorTo(f.pointOnFace); v.normalize(); v.scaleBy(0.001)
                q = mid.copy(); q.translateBy(v)
                _, uv = ev.getParameterAtPoint(q); _, pq = ev.getPointAtParameter(uv); _, nq = ev.getNormalAtParameter(uv)
                if outward(pq, nq).dotProduct(nq) < 0: nn = nn.copy(); nn.scaleBy(-1)
                return nn
            n1, n2 = side(f1, n1), side(f2, n2)
            th = math.acos(max(-1.0, min(1.0, n1.dotProduct(n2))))
            Rq = (g.startPoint.distanceTo(g.endPoint) * 10) / 10 + 0.5
            left = Rq * (1 / math.cos(th / 2) - 1) if th < math.pi * 0.999 else 99
            if left < LEFT_MAX: continue      # a kink: the tool (R for this wall height) leaves less than LEFT_MAX there
            q = mid.copy(); t = V3(n2.x - n1.x, n2.y - n1.y, n2.z - n1.z); t.normalize(); t.scaleBy(0.0003); q.translateBy(t)   # 3 um: below the micro arcs curve fitting leaves at corners
            if body.pointContainment(q) == adsk.fusion.PointContainment.PointInsidePointContainment:
                res['sharp'].append((mm(mid), round(g.startPoint.distanceTo(g.endPoint) * 10, 1), '%.0fdeg left %.2f' % (math.degrees(th), left)))
        nf = body.faces.count
        occ.deleteMe()
        for b in r.bRepBodies: b.isLightBulbOn = True
        report[bname] = res
        print('==', DOC, bname, 'faces', nf, {k: len(v) for k, v in res.items()})
        for k, v in res.items():
            for it in v[:40]: print('  ', k, it)
    globals()['REPORT'] = report
    json.dump(report, open(SCR + 'cnc_%s%s.json' % (SIDE, SFX), 'w'), indent=0)
