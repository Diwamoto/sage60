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
    for n in ('USB_RECESS', 'USB_RCPT', 'SW_SCOOP', 'SW_OPEN'):      # plan slots, cut upward from their bottom z (CNC, 2026-10-05)
        new_sketch(r, n, XY, spec[n])
    new_sketch(r, 'GASKET_POCKET', XY, spec['GASKET_POCKET'])          # bottom (runs out past the wall)
    new_sketch(r, 'TOP_GASKET_SLOT', XY, spec['TOP_GASKET_SLOT'])      # top ring (ends inside it)
    # rubber feet on the (tilted) desk face; machined from below along the desk normal (setup 2)
    def desk_circles(name, circles, expr):
        sk = r.sketches.add(DESK); sk.name = name
        pg = DESK.geometry; o, n = pg.origin, pg.normal
        for c in circles:
            x, y = c[1][0] / 10, c[1][1] / 10
            z = o.z - (n.x * (x - o.x) + n.y * (y - o.y)) / n.z
            sk.sketchCurves.sketchCircles.addByCenterRadius(sk.modelToSketchSpace(adsk.core.Point3D.create(x, y, z)), c[2] / 10)
        dims(sk, expr)
    desk_circles('FEET', spec['FEET'], 'foot_d')
    if SIDE == 'right':
        SEAT = off_plane('TB_SEAT', XY, '-( plate_t + pcb_gap + tb_gap + tb_leg_h )')
        new_sketch(r, 'TB_POCKET', XY, spec['TB_POCKET'])
        dims(new_sketch(r, 'TB_SCREWS', SEAT, spec['TB_SCREWS']), 'tb_scr_d')
        desk_circles('TB_SCREW_CB', spec['TB_SCREWS'], 'tb_cb_d')       # counterbores along the desk normal (setup 2); the holes stay plate-normal (from the top)
        off_plane('TB_CB_FLOOR', XY, '-( plate_t + pcb_gap + tb_gap + tb_leg_h + tb_cb_t )')
    for p in cp: p.isLightBulbOn = False
    for s in r.sketches:
        print(s.name, 'curves', s.sketchCurves.count, 'profiles', s.profiles.count)
