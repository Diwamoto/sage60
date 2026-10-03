# construction planes + sketches.  globals: SIDE
exec(open('/Users/daiki/Projects/sage60/mechanical/case/fusion/fx.py').read())

def dims(sk, expr):
    for c in sk.sketchCurves.sketchCircles:
        g = c.centerSketchPoint.geometry
        sk.sketchDimensions.addDiameterDimension(c, adsk.core.Point3D.create(g.x + 0.3, g.y + 0.3, 0)).parameter.expression = expr

def run(_c):
    spec = json.load(open(SCR + '%s%s_spec.json' % (SIDE, SFX)))
    d = design(DOC); r = d.rootComponent
    cp = r.constructionPlanes
    def off_plane(name, base, expr):
        i = cp.createInput(); i.setByOffset(base, VI.createByString(expr)); p = cp.add(i); p.name = name; return p
    XY = r.xYConstructionPlane
    new_sketch(r, 'LEFT_PLATE_SURFACE' if SIDE == 'left' else 'RIGHT_TB_PLATE_SURFACE', XY, spec['PLATE_SURFACE'])
    SHELF = off_plane('SHELF_TOP', XY, '-shelf_d')
    FBR = off_plane('FRONT_BOTTOM_REF', XY, '-( cav_z + floor_t )')
    ta = new_sketch(r, 'TILT_AXIS', FBR, spec['TILT_AXIS'])
    i = cp.createInput(); i.setByAngle(ta.sketchCurves.sketchLines.item(0), VI.createByString('-tilt'), FBR)
    DESK = cp.add(i); DESK.name = 'DESK_PLANE'
    new_sketch(r, 'CASE_OUTER', XY, spec['CASE_OUTER'])
    new_sketch(r, 'CAVITY', XY, spec['CAVITY'])
    new_sketch(r, 'MCU_RING', SHELF, spec['MCU_RING'])
    dims(new_sketch(r, 'MAGNETS', SHELF, spec['MAGNETS']), 'mag_d')
    MCUT = off_plane('MCU_RING_TOP', XY, 'mcu_cover_z')
    dims(new_sketch(r, 'MCU_SCREWS', MCUT, spec['MCU_SCREWS']), 'ins_d')
    off_plane('FLOOR_TOP', DESK, 'floor_t')
    xf = spec['_sw']['x']; SWF, _ = sw_plane(r, xf)
    for n in ('SW_SCOOP', 'SW_OPEN'):
        s = r.sketches.add(SWF); s.name = n; draw_yz(s, spec[n], xf)
    yf = spec['_usb_face_y']; UF, _ = usb_plane(r, yf)
    for n in ('USB_TUNNEL', 'USB_RCPT'):
        s = r.sketches.add(UF); s.name = n; draw_xz(s, spec[n], yf)
    new_sketch(r, 'GASKET_POCKET', XY, spec['GASKET_POCKET'])
    # rubber feet on the (tilted) desk face
    sk = r.sketches.add(DESK); sk.name = 'FEET'
    pg = DESK.geometry; o, n = pg.origin, pg.normal
    for c in spec['FEET']:
        x, y = c[1][0] / 10, c[1][1] / 10
        z = o.z - (n.x * (x - o.x) + n.y * (y - o.y)) / n.z
        sk.sketchCurves.sketchCircles.addByCenterRadius(sk.modelToSketchSpace(adsk.core.Point3D.create(x, y, z)), c[2] / 10)
    dims(sk, 'foot_d')
    if SIDE == 'right':
        SEAT = off_plane('TB_SEAT', XY, '-( plate_t + pcb_gap + tb_gap + tb_leg_h )')
        new_sketch(r, 'TB_POCKET', XY, spec['TB_POCKET'])
        dims(new_sketch(r, 'TB_SCREWS', SEAT, spec['TB_SCREWS']), 'tb_scr_d')
        dims(new_sketch(r, 'TB_SCREW_CB', SEAT, spec['TB_SCREWS']), 'tb_cb_d')
    for p in cp: p.isLightBulbOn = False
    for s in r.sketches:
        print(s.name, 'curves', s.sketchCurves.count, 'profiles', s.profiles.count)
