# gallery screenshots of one case document.  globals: SIDE, LP, OUT (directory)
# side views use a fixed orthographic scale so MX and LP compare at the same size
exec(open('/Users/daiki/Projects/sage60/mechanical/case/fusion/fx.py').read())

def run(_c):
    d = design(DOC); r = d.rootComponent
    vp = app.activeViewport; VO = adsk.core.ViewOrientations
    bot = r.bRepBodies.itemByName('%s_bottom' % SIDE)
    A, Bm = r.bRepBodies.itemByName('MOCK_A'), [b for b in r.bRepBodies if b.name.startswith('MOCK_B')]
    for s in r.sketches: s.isVisible = False
    for p in r.constructionPlanes: p.isLightBulbOn = False
    def show(a=False, b=False):
        A.isLightBulbOn = a
        for m in Bm: m.isLightBulbOn = b
    bb = bot.boundingBox
    cx, cy = (bb.minPoint.x + bb.maxPoint.x) / 2, (bb.minPoint.y + bb.maxPoint.y) / 2
    iso = VO.IsoTopRightViewOrientation if SIDE == 'left' else VO.IsoTopLeftViewOrientation
    tag = '%s_%s' % ('lp' if LP else 'mx', SIDE)
    def fit(name, ori):
        cam = vp.camera; cam.isSmoothTransition = False; cam.viewOrientation = ori; cam.isFitView = True; vp.camera = cam; vp.fit()
        vp.saveAsImageFile(OUT + '%s_%s.png' % (tag, name), 1600, 1000)
    def ortho(name, dx, dy, ext=13.0, zc=-1.0):
        cam = vp.camera; cam.isSmoothTransition = False; cam.isFitView = False
        cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        t = adsk.core.Point3D.create(cx, cy, zc)
        cam.target = t; cam.eye = adsk.core.Point3D.create(cx + dx * 60, cy + dy * 60, zc)
        cam.upVector = adsk.core.Vector3D.create(0, 0, 1); cam.viewExtents = ext; vp.camera = cam
        cam = vp.camera; cam.viewExtents = ext; vp.camera = cam      # the first set after switching to ortho is dropped
        vp.saveAsImageFile(OUT + '%s_%s.png' % (tag, name), 1600, 1000)
    show(a=True); fit('iso_a', iso)
    show(); fit('iso_bottom', iso)
    fit('desk', VO.BottomViewOrientation)
    show(a=True); fit('top', VO.TopViewOrientation)
    ortho('front', 0, -1)
    ortho('back', 0, 1)
    ortho('side', 1 if SIDE == 'left' else -1, 0)
    show(a=True)
    cam = vp.camera; cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType; cam.viewOrientation = iso; cam.isFitView = True; vp.camera = cam
    print(tag, 'ok')
