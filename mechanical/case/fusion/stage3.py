# top-case mocks A/B.  globals: SIDE
exec(open('/Users/daiki/Projects/sage60/mechanical/case/fusion/fx.py').read())

def run(_c):
    spec = json.load(open(SCR + '%s%s_spec.json' % (SIDE, SFX)))
    d = design(DOC); r = d.rootComponent
    up = d.userParameters
    ex = r.features.extrudeFeatures
    sk = lambda n: r.sketches.itemByName(n)
    pl = lambda n: r.constructionPlanes.itemByName(n)
    XY = r.xYConstructionPlane
    outside = adsk.core.Point3D.create(12.2, 5.0, 0)
    def proj_offset(s, dists):
        prj = s.project(oc([c for c in sk('CASE_OUTER').sketchCurves]))
        for e in prj: e.isConstruction = True
        base = oc([e for e in prj])
        res = []
        for dexpr in dists:
            cur = s.offset(base, outside, up.itemByName('clr').value if dexpr == 'clr' else (up.itemByName('clr').value + up.itemByName('wall').value))
            res.append(cur)
        return res
    # TOP_WALL : CASE_OUTER + clr .. + clr + wall
    s = r.sketches.add(XY); s.name = 'TOP_WALL'; proj_offset(s, ['clr', 'clr+wall'])
    # TOP_RING : outer = CASE_OUTER + clr, inner = keys opening U trackball hole
    s = r.sketches.add(XY); s.name = 'TOP_RING'; proj_offset(s, ['clr']); draw(s, spec['TOP_RING_INNER'])
    for n in ['TOP_MCU_OPEN', 'TOP_MAG']:
        s = new_sketch(r, n, XY, spec[n])
    for c in s.sketchCurves.sketchCircles:
        g = c.centerSketchPoint.geometry
        s.sketchDimensions.addDiameterDimension(c, adsk.core.Point3D.create(g.x + 0.3, g.y + 0.3, 0)).parameter.expression = 'mag_d'
    def widest(s):
        return max(profiles(s), key=lambda p: p.boundingBox.maxPoint.x - p.boundingBox.minPoint.x + p.boundingBox.maxPoint.y - p.boundingBox.minPoint.y)
    for n in ('TOP_WALL', 'TOP_RING'):
        print(n, 'profiles', sk(n).profiles.count, 'curves', sk(n).sketchCurves.count)
    def extrude(name, prof, op, start, dist=None, to=None, bodies=None):
        i = ex.createInput(prof, op)
        i.startExtent = adsk.fusion.OffsetStartDefinition.create(VI.createByString(start))
        if to is not None:
            i.setOneSideExtent(adsk.fusion.ToEntityExtentDefinition.create(to, False), adsk.fusion.ExtentDirections.PositiveExtentDirection)
        else:
            i.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByString(dist)), adsk.fusion.ExtentDirections.PositiveExtentDirection)
        if bodies is not None: i.participantBodies = bodies
        f = ex.add(i); f.name = name; return f
    allp = lambda n: oc(profiles(sk(n)))
    new_sketch(r, 'TOP_GUARD', XY, spec['TOP_GUARD'])
    mocks = []
    for X in ('A',):              # case A decided 2026-10-03 (skirt down to the desk); B dropped
        f = extrude('TOP_RING_' + X, widest(sk('TOP_RING')), FO.NewBodyFeatureOperation, '-shelf_d', 'shelf_d + top_h')
        m = f.bodies.item(0); m.name = 'MOCK_' + X; mocks.append(m)
        extrude('TOP_GUARD_' + X, allp('TOP_GUARD'), FO.JoinFeatureOperation, 'guard_z', 'top_h - guard_z', bodies=[m])
        extrude('TOP_MCU_OPEN_' + X, sk('TOP_MCU_OPEN').profiles.item(0), FO.CutFeatureOperation, '-shelf_d', 'shelf_d + top_h', bodies=[m])
        extrude('TOP_GASKET_SLOT_' + X, allp('TOP_GASKET_SLOT'), FO.CutFeatureOperation, '-shelf_d', 'shelf_d + gasket_t + gasket_pocket', bodies=[m])
        extrude('TOP_MAG_' + X, allp('TOP_MAG'), FO.CutFeatureOperation, '-shelf_d', 'mag_h_top', bodies=[m])
        extrude('TOP_WALL_A', widest(sk('TOP_WALL')), FO.JoinFeatureOperation, 'top_h', to=pl('DESK_PLANE'), bodies=[m])
        m = r.bRepBodies.itemByName('MOCK_' + X)
        # CNC: the ring ends at the MCU opening meet the skirt in concave corners -> R inner_r (the bottom MCU block is rounded to match)
        bx = [p for c in spec['TOP_MCU_OPEN'] if c[0] == 'line' for p in c[1:3]]
        xs, y0 = {round(min(p[0] for p in bx), 3), round(max(p[0] for p in bx), 3)}, min(p[1] for p in bx)
        es = [e for e in vertical_edges(m) if (lambda i: i['concave'] and not i['tangent'] and (any(abs(i['xy'][0] - x) < 0.05 for x in xs) or abs(i['xy'][1] - y0) < 0.05))(edge_info(e, m))]
        ok, bad = fillet(r, es, 'inner_r', 'TOP_MCU_FILLET_' + X)
        print('TOP_MCU_FILLET', len(es), bad)
        m = r.bRepBodies.itemByName('MOCK_' + X)
        slot_cuts(r, spec, [m], '_' + X, ('USB_RECESS', 'SW_SCOOP'))      # USB / switch: notches open at the top through the skirt
    for s in r.sketches:
        s.isVisible = False
    for b in r.bRepBodies:
        bb = b.boundingBox
        print(b.name, [round(v * 10, 2) for v in (bb.minPoint.x, bb.minPoint.y, bb.minPoint.z, bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z)], round(b.volume, 2))
    print('health', [(d.timeline.item(i).name, d.timeline.item(i).healthState) for i in range(d.timeline.count) if d.timeline.item(i).healthState != 0])
