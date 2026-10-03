# bottom case features.  globals: SIDE
exec(open('/Users/daiki/Projects/sage60/mechanical/case/fusion/fx.py').read())

def run(_c):
    spec = json.load(open(SCR + '%s%s_spec.json' % (SIDE, SFX))); R = spec['_rings']
    mags = [c[1] for c in spec['MAGNETS']]
    d = design(DOC); r = d.rootComponent
    ex = r.features.extrudeFeatures
    sk = lambda n: r.sketches.itemByName(n)
    pl = lambda n: r.constructionPlanes.itemByName(n)
    allp = lambda n: oc(profiles(sk(n)))
    def extrude(name, prof, op, start=None, dist=None, to=None, bodies=None):
        i = ex.createInput(prof, op)
        if start is not None: i.startExtent = start
        if to is not None:
            i.setOneSideExtent(adsk.fusion.ToEntityExtentDefinition.create(to, False), adsk.fusion.ExtentDirections.PositiveExtentDirection)
        else:
            i.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByString(dist)), adsk.fusion.ExtentDirections.PositiveExtentDirection)
        if bodies is not None: i.participantBodies = bodies
        f = ex.add(i); f.name = name; return f
    fromE = lambda n, off='0 mm': adsk.fusion.FromEntityStartDefinition.create(pl(n), VI.createByString(off))
    offS = lambda expr: adsk.fusion.OffsetStartDefinition.create(VI.createByString(expr))
    bname = '%s_bottom' % SIDE
    get = lambda: r.bRepBodies.itemByName(bname)
    log = []
    f = extrude('CASE_BLOCK', sk('CASE_OUTER').profiles.item(0), FO.NewBodyFeatureOperation, start=fromE('SHELF_TOP'), to=pl('DESK_PLANE'))
    f.bodies.item(0).name = bname
    extrude('CAVITY_CUT', sk('CAVITY').profiles.item(0), FO.CutFeatureOperation, start=fromE('SHELF_TOP'), dist='-( cav_z - shelf_d )')
    # no fillet on the cavity wall: CAVITY already has R1.5 on the solid's inner corners and must stay identical to the top ring
    # MCU walls = (CASE_OUTER - CAVITY) within MCU_RING, shelf .. mcu_cover_z
    f = extrude('MCU_WALL', sk('CASE_OUTER').profiles.item(0), FO.NewBodyFeatureOperation, start=fromE('SHELF_TOP'), dist='shelf_d + mcu_cover_z')
    ring = f.bodies.item(0)
    extrude('MCU_WALL_CAV', sk('CAVITY').profiles.item(0), FO.CutFeatureOperation, start=fromE('SHELF_TOP'), dist='shelf_d + mcu_cover_z', bodies=[ring])
    extrude('MCU_WALL_CLIP', sk('MCU_RING').profiles.item(0), FO.IntersectFeatureOperation, start=fromE('SHELF_TOP'), dist='shelf_d + mcu_cover_z', bodies=[ring])
    ci = r.features.combineFeatures.createInput(get(), oc([ring])); ci.operation = FO.JoinFeatureOperation
    r.features.combineFeatures.add(ci).name = 'MCU_WALL_JOIN'
    extrude('MAGNET_CUT', allp('MAGNETS'), FO.CutFeatureOperation, dist='-( mag_h )')
    extrude('MCU_SCREW_CUT', allp('MCU_SCREWS'), FO.CutFeatureOperation, dist='-( ins_h )')
    if d.userParameters.itemByName('tilt').value > 1e-6:     # flat (tilt 0): CAVITY_CUT already reaches the floor
        extrude('CAVITY_DEEP', sk('CAVITY').profiles.item(0), FO.CutFeatureOperation, start=fromE('SHELF_TOP'), to=pl('FLOOR_TOP'))
    body = get()
    es = [e for e in vertical_edges(body) if (lambda i: not i['tangent'] and not near_any(i['xy'], mags, 2.0) and not on_ring(i['xy'], R['cav'], 0.05))(edge_info(e, body))]
    log.append(('F_inner at', [tuple(round(v, 1) for v in edge_info(e, body)['xy']) for e in es]))
    ok, bad = fillet(r, es, 'inner_r', 'FILLET_INNER'); log.append(('F_inner', len(es), bad))
    sw_cuts(r, spec, [get()], '')
    # USB: recess for the plug overmold from the port face outwards, then the receptacle opening through the flush wall
    _, sg = usb_plane(r, spec['_usb_face_y'])
    extrude('USB_TUNNEL_CUT', sk('USB_TUNNEL').profiles.item(0), FO.CutFeatureOperation, dist='%d mm' % (20 * sg), bodies=[get()])
    extrude('USB_RCPT_CUT', sk('USB_RCPT').profiles.item(0), FO.CutFeatureOperation, start=offS('%.1f mm' % (0.3 * sg)), dist='%.1f mm' % (-2.5 * sg), bodies=[get()])
    extrude('GASKET_POCKET_CUT', allp('GASKET_POCKET'), FO.CutFeatureOperation, start=offS('-( plate_t + gasket_t + gasket_pocket )'), dist='gasket_pocket + plate_t + gasket_t - shelf_d')
    v0 = get().volume
    up_into_body = pl('DESK_PLANE').geometry.normal.z > 0
    extrude('FEET_CUT', allp('FEET'), FO.CutFeatureOperation, dist='foot_t' if up_into_body else '-foot_t', bodies=[get()])
    log.append(('feet removed cm3', round(v0 - get().volume, 4)))
    if SIDE == 'right':
        extrude('TB_POCKET_CUT', sk('TB_POCKET').profiles.item(0), FO.CutFeatureOperation, start=fromE('SHELF_TOP'), to=pl('TB_SEAT'))
        extrude('TB_SCREW_CUT', allp('TB_SCREWS'), FO.CutFeatureOperation, dist='-30 mm')
        extrude('TB_SCREW_CB_CUT', allp('TB_SCREW_CB'), FO.CutFeatureOperation, start=offS('-tb_cb_t'), dist='-30 mm')
        bf = r.features.baseFeatures.add(); bf.name = 'TB_CASE_REF'
        bf.startEdit()
        r.meshBodies.add(SCR + 'tb_placed%s.stl' % SFX, adsk.fusion.MeshUnits.MillimeterMeshUnit, bf)
        bf.finishEdit()
        r.meshBodies.item(0).name = 'trackballcase'
    body = get(); bb = body.boundingBox
    print('body bbox', [round(v * 10, 2) for v in (bb.minPoint.x, bb.minPoint.y, bb.minPoint.z, bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z)], 'vol', round(body.volume, 2), 'lumps', body.lumps.count)
    for l in log: print(l)
    print('health', [(d.timeline.item(i).name, d.timeline.item(i).healthState) for i in range(d.timeline.count) if d.timeline.item(i).healthState != 0])
