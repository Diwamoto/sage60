import adsk.core, adsk.fusion, json, math
SCR = '/Users/daiki/Projects/sage60/mechanical/case/'
LP = globals().get('LP', False)          # low-profile variant: its own documents and *_lp_spec.json
SFX = '_lp' if LP else ''
DOC = ('sage60_lp_%s' if LP else 'sage60_%s_bottom') % globals().get('SIDE', '')
app = adsk.core.Application.get()
VI = adsk.core.ValueInput
FO = adsk.fusion.FeatureOperations
def doc_by(prefix):
    return [d for d in app.documents if d.name.startswith(prefix)][0]
def design(prefix):
    doc = doc_by(prefix)
    doc.activate()
    return adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
def P3(p, z=0.0):
    return adsk.core.Point3D.create(p[0] / 10, p[1] / 10, z / 10)
def oc(items):
    c = adsk.core.ObjectCollection.create()
    for i in items: c.add(i)
    return c

def draw(sk, curves, z=0.0):
    """curves in mm (world XY); sketch must be parallel to XY with identity orientation"""
    pts = {}
    def sp(p):
        k = (round(p[0], 3), round(p[1], 3))
        return pts.get(k)
    def keep(p, skp):
        pts[(round(p[0], 3), round(p[1], 3))] = skp
    # sketch-space z: world z minus sketch origin z
    zz = z
    out = []
    for c in curves:
        t = c[0]
        if t == 'line':
            a, b = c[1], c[2]
            l = sk.sketchCurves.sketchLines.addByTwoPoints(sp(a) or P3(a, zz), sp(b) or P3(b, zz))
            keep(a, l.startSketchPoint); keep(b, l.endSketchPoint); out.append(l)
        elif t == 'arc':
            a, m, b = c[1], c[2], c[3]
            ar = sk.sketchCurves.sketchArcs.addByThreePoints(sp(a) or P3(a, zz), P3(m, zz), sp(b) or P3(b, zz))
            # arc start/end may be swapped by Fusion; register both by geometry
            for q in (ar.startSketchPoint, ar.endSketchPoint):
                g = q.geometry; keep((g.x * 10, g.y * 10), q)
            out.append(ar)
        elif t == 'spline':
            ps = c[1]
            col = adsk.core.ObjectCollection.create()
            for i, p in enumerate(ps):
                if i in (0, len(ps) - 1) and sp(p): col.add(sp(p))
                else: col.add(P3(p, zz))
            s = sk.sketchCurves.sketchFittedSplines.add(col)
            keep(ps[0], s.startSketchPoint); keep(ps[-1], s.endSketchPoint); out.append(s)
        elif t == 'circle':
            ci = sk.sketchCurves.sketchCircles.addByCenterRadius(P3(c[1], zz), c[2] / 10)
            out.append(ci)
    return out

def new_sketch(r, name, plane, curves=None):
    sk = r.sketches.add(plane)
    sk.name = name
    sk.isComputeDeferred = True
    if curves:
        z = sk.origin.z * 10
        draw(sk, curves, 0.0 if True else z)
    sk.isComputeDeferred = False
    return sk

def profiles(sk):
    return [sk.profiles.item(i) for i in range(sk.profiles.count)]
def largest_profile(sk):
    return max(profiles(sk), key=lambda p: p.areaProperties().area)
def profile_containing(sk, xy, exclude_xy=None):
    """profile whose region contains point xy (mm)"""
    res = []
    for p in profiles(sk):
        bb = p.boundingBox
        x, y = xy[0] / 10, xy[1] / 10
        if not (bb.minPoint.x <= x <= bb.maxPoint.x and bb.minPoint.y <= y <= bb.maxPoint.y): continue
        res.append(p)
    return res

def vertical_edges(body, zmin=None, zmax=None):
    out = []
    for e in body.edges:
        g = e.geometry
        if not isinstance(g, adsk.core.Line3D): continue
        s, t = e.startVertex.geometry, e.endVertex.geometry
        L = s.distanceTo(t)
        if L < 1e-4: continue
        if abs(abs(t.z - s.z) - L) > 1e-5 * max(1, L): continue  # not vertical
        if e.faces.count != 2 or e.faces.item(0) == e.faces.item(1): continue
        lo, hi = min(s.z, t.z) * 10, max(s.z, t.z) * 10
        if zmin is not None and hi < zmin - 1e-3: continue
        if zmax is not None and lo > zmax + 1e-3: continue
        out.append(e)
    return out

def edge_info(e, body):
    s, t = e.startVertex.geometry, e.endVertex.geometry
    m = adsk.core.Point3D.create((s.x + t.x) / 2, (s.y + t.y) / 2, (s.z + t.z) / 2)
    f1, f2 = e.faces.item(0), e.faces.item(1)
    ok1, n1 = f1.evaluator.getNormalAtPoint(m)
    ok2, n2 = f2.evaluator.getNormalAtPoint(m)
    dot = n1.dotProduct(n2)
    eps = 0.02
    p = adsk.core.Point3D.create(m.x + eps * (n1.x - n2.x), m.y + eps * (n1.y - n2.y), m.z + eps * (n1.z - n2.z))
    concave = body.pointContainment(p) == adsk.fusion.PointContainment.PointInsidePointContainment
    return {'xy': (m.x * 10, m.y * 10), 'tangent': dot > 0.995, 'concave': concave,
            'z': (round(min(s.z, t.z) * 10, 2), round(max(s.z, t.z) * 10, 2))}

def fillet(r, edges, rexpr, name):
    """one fillet feature; if it fails as a whole, retry per edge and skip failures"""
    if not edges: return [], []
    fs = r.features.filletFeatures
    def mk(es, nm):
        inp = fs.createInput()
        inp.addConstantRadiusEdgeSet(oc(es), VI.createByString(rexpr), False)
        f = fs.add(inp); f.name = nm; return f
    try:
        mk(edges, name); return edges, []
    except Exception:
        pass
    ok, bad = [], []
    # edges become invalid after each feature -> re-identify by midpoint
    keys = []
    for e in edges:
        s, t = e.startVertex.geometry, e.endVertex.geometry
        keys.append(((s.x + t.x) / 2, (s.y + t.y) / 2, (s.z + t.z) / 2))
    body = edges[0].body
    for i, k in enumerate(keys):
        cand = None
        for e in body.edges:
            if not isinstance(e.geometry, adsk.core.Line3D): continue
            s, t = e.startVertex.geometry, e.endVertex.geometry
            if abs((s.x + t.x) / 2 - k[0]) < 1e-4 and abs((s.y + t.y) / 2 - k[1]) < 1e-4 and abs((s.z + t.z) / 2 - k[2]) < 1e-4:
                cand = e; break
        if cand is None: bad.append((round(k[0]*10,2), round(k[1]*10,2), 'gone')); continue
        try:
            mk([cand], '%s_%d' % (name, i)); ok.append(k)
        except Exception as ex:
            bad.append((round(k[0]*10,2), round(k[1]*10,2), str(ex)[:60]))
    return ok, bad

def near_any(xy, pts, tol=0.05):
    return any(abs(xy[0] - p[0]) < tol and abs(xy[1] - p[1]) < tol for p in pts)

def on_ring(xy, ring_pts, tol=0.05):
    # distance from point to polyline ring (mm)
    best = 1e9
    n = len(ring_pts)
    for i in range(n):
        a, b = ring_pts[i], ring_pts[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else max(0, min(1, ((xy[0] - a[0]) * dx + (xy[1] - a[1]) * dy) / L2))
        d = math.hypot(a[0] + u * dx - xy[0], a[1] + u * dy - xy[1])
        best = min(best, d)
    return best < tol


def usb_plane(r, y_mm):
    """construction plane parallel to XZ through y = y_mm; returns (plane, sign) where sign * distance moves toward +y"""
    xz = r.constructionPlanes.itemByName('USB_FACE')
    n = r.xZConstructionPlane.geometry.normal.y
    if xz is None:
        i = r.constructionPlanes.createInput(); i.setByOffset(r.xZConstructionPlane, adsk.core.ValueInput.createByString('%.4f mm' % (y_mm * n)))
        xz = r.constructionPlanes.add(i); xz.name = 'USB_FACE'; xz.isLightBulbOn = False
    return xz, (1 if n > 0 else -1)

def draw_xz(sk, curves, y_mm):
    """curves given as (x, z) in mm on the plane y = y_mm"""
    def m(p):
        q = sk.modelToSketchSpace(adsk.core.Point3D.create(p[0] / 10, y_mm / 10, p[1] / 10)); return (q.x * 10, q.y * 10)
    out = []
    for c in curves:
        if c[0] == 'line': out.append(('line', m(c[1]), m(c[2])))
        elif c[0] == 'arc': out.append(('arc', m(c[1]), m(c[2]), m(c[3])))
    return draw(sk, out)

def sw_plane(r, x_mm):
    """construction plane parallel to YZ through x = x_mm; returns (plane, sign) where sign * distance moves toward +x"""
    p = r.constructionPlanes.itemByName('SW_FLOOR')
    n = r.yZConstructionPlane.geometry.normal.x
    if p is None:
        i = r.constructionPlanes.createInput(); i.setByOffset(r.yZConstructionPlane, adsk.core.ValueInput.createByString('%.4f mm' % (x_mm * n)))
        p = r.constructionPlanes.add(i); p.name = 'SW_FLOOR'; p.isLightBulbOn = False
    return p, (1 if n > 0 else -1)

def draw_yz(sk, curves, x_mm):
    """curves given as (y, z) in mm on the plane x = x_mm"""
    def m(p):
        q = sk.modelToSketchSpace(adsk.core.Point3D.create(x_mm / 10, p[0] / 10, p[1] / 10)); return (q.x * 10, q.y * 10)
    out = []
    for c in curves:
        if c[0] == 'line': out.append(('line', m(c[1]), m(c[2])))
        elif c[0] == 'arc': out.append(('arc', m(c[1]), m(c[2]), m(c[3])))
    return draw(sk, out)

def sw_cuts(r, spec, bodies, tag, names=('SW_SCOOP', 'SW_OPEN')):
    """slide switch: scoop from the floor plane outwards, opening from inside the cavity outwards; same sketches for every body"""
    ex = r.features.extrudeFeatures; sw = spec['_sw']
    _, sg = sw_plane(r, sw['x']); o = sw['out'] * sg
    for n, start, dist in (('SW_SCOOP', 0.0, 12.0), ('SW_OPEN', -sw['in'], sw['in'] + 12.0)):
        if n not in names: continue
        i = ex.createInput(r.sketches.itemByName(n).profiles.item(0), FO.CutFeatureOperation)
        i.startExtent = adsk.fusion.OffsetStartDefinition.create(VI.createByString('%.2f mm' % (start * o)))
        i.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByString('%.2f mm' % (dist * o))), adsk.fusion.ExtentDirections.PositiveExtentDirection)
        i.participantBodies = bodies; ex.add(i).name = n + '_CUT' + tag
