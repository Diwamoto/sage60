"""(2026-11-13) trackball case rebuilt as a smooth cup: even supports, then lips that lock the ball in (like the MX Ergo).

The ball lifted ~1 mm off the sensor on a fast roll away from it and tracking stopped (supports bunched, a 150 deg gap
where the thumb pushes).  (2026-11-16) Drawn from scratch, nothing of trackballcase_low is read: the hood (HOOD, HOOD_VOIDS), below
the frame a plain cone (LOW, the old outline in the PCB hole) and two magnet bosses.  Above it the cup is one solid of
revolution: a steep cone in to R_JOIN at the top case's frame (no flat overhang to print), a 45 deg cone out to a sphere RO, a level top RIM_R rounded on the
outside.  Inside, the old cup's sphere (CUP_R, CUP_DZ above the ball) and three support pockets inside the wall.  S: top at that sphere's equator
(supports only).  L*: the top goes on up to a lip whose opening is NARROW mm narrower than the ball.
Out: production/case_print/trackballcase_collar_<name>.3mf (frame of trackballcase_low.3mf) and all of them on one plate,
trackballcase_collar_all.3mf.  Coordinates: from the ball's resting centre REST (relative to TBX, TBY, Fusion z), from the
old cup's sphere fit and supports (±0.2 mm); the new supports keep it there."""
import sys, os, zipfile; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
import manifold3d as mf
from tb_socket_cut import write3mf, HERE
from tb import TBX, TBY
from tb_socket_cut import MAG_D, MAG_H, MAG_BOSS_R, LID
from make_right import TB_SCREWS

BALL_R = 17.0
REST = np.array([-0.27, 0.21, 8.24])        # resting ball centre (cup fit + rest on the three supports)
# Inside: the old cup's sphere, measured from REST (the old case takes the ball and turns): 0.2 off the ball below, 0.8 at the
# equator, 1.3 above.  (Rev. 1 had 0.05 all round: the ball didn't go in, the one that did didn't turn.)
# Above that it's capped at G_UP off the ball, so the ball can lift at most G_UP and the lip stays low.
CUP_R, CUP_DZ, G_UP = 17.85, 0.75, 0.4
R_JOIN = 16.8                               # cup's waist at Z_FRAME (the frame allows ~17.2 just below it)
# (2026-11-16) Below the frame: one smooth cone instead of the old case (its ribs and slivers), on the old case's outline in
# the PCB hole (r, Fusion z: its smallest radius at each height outside the hood), bottom at Z_BOT; plus the two magnet bosses.
LOW = [(9.8, -9.0)]                         # a straight cone from here up to R_JOIN at Z_FRAME
Z_BOT = -9.0
Z_FRAME = 0.3                               # top case's lowered frame top (0) + 0.3: the cone starts here
RO, RIM_R = 20.5, 1.0                       # outer sphere; round on the top's outer edge
HOOD_X = 17.3                               # the sensor hood (x > HOOD_X) is left as it was
HOOD_CLR = 0.25                             # ball to hood, at least (the window lip)
# Visor: over the sensor the wall goes on up to the hood's top VISOR_Z (Fusion z), so the lens can't be seen (or lit) past
# the ball.  Its edge is the plane x = VISOR_X (a straight chord from above; 6 hides more, 14 lets the ball in easier).
VISOR_X, VISOR_Z = 10.0, 17.7
# Hood (2026-11-16, drawn from scratch: nothing of the old case is read).  It drops on from above over the sensor board standing
# in J1's socket, so every void is open to the bottom.  Fusion coordinates; sizes from the parts (tb_socket_cut.PARTS) + clearance.
HOOD = ((152.4, -135.4), (164.2, -109.5))   # outer box (x, y); z: Z_BOT in the PCB hole, HOOD_Z_TONGUE over the PCB tongue
HOOD_TONGUE_X, HOOD_Z_TONGUE, HOOD_R = 158.5, -4.7, 2.0   # x from which the hood sits on the tongue; corner radius
HOOD_VOIDS = [((153.7, -132.3, -20), (157.4, -112.5, 16.0)),      # IC + lens in front of the board
              ((157.2, -134.3, -20), (159.35, -110.5, 14.8)),     # the sensor board (157.34 .. 158.94, 22 wide, top 14.5)
              ((159.35, -128.4, -20), (162.65, -116.4, 12.0)),    # its back: parts, the socket
              ((158.9, -131.695, -20), (166.0, -113.095, -2.2)),  # the J1 socket (6604S, 17.8 wide) and header pass under the back wall
              ((150.0, -125.3, 6.2), (153.8, -119.3, 12.7))]      # lens window, toward the ball
# Supports (kepeo: https://kepeo.hatenablog.com/entry/2024/09/08/134648): three 120 deg apart, one straight opposite the
# sensor (az 180), SUP_EL below the equator (kepeo: 15 stable .. 25 lighter; 15 keeps them inside the cone), a 2 mm ball
# pressed into a hex pocket (2.0 across flats) from the inside, pocket bottom at BALL_R + 2.
SUP_AZ, SUP_EL = (180, 60, -60), 15
# name: (opening narrower than the ball (mm, diameter; kepeo 0.5 .. 1.0) or None (rim at the equator), ball centre off REST)
# Rev. 2 (S, L2..L8, centre at REST) held the ball but tracked worse than the old case: on the old supports the ball actually
# sits 0.09 nearer the sensor and 0.28 lower than REST (REST was a compromise with the cup fit), so S held it a bit far off.
# Rev. 3 moves the ball (supports + cup) DX toward the sensor; the hood is untouched (the ball touches it at DX ~0.45).
# Rev. 3 printed D1..D3 (DX 0.1/0.2/0.3); D3 tracked best (2026-11-15) and is the one kept.
VARIANTS = {'D3': (None, (0.3, 0, -0.28)), 'D4': (None, (0.4, 0, -0.28))}   # D4: hood contact at ~0.45

def unit(e, a):
    e, a = np.radians(e), np.radians(a)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])

def along(m, u, p):
    """m built along +z from the origin, turned to point along u and moved to start at p"""
    return m.rotate((0, np.degrees(np.arccos(u[2])), 0)).rotate((0, 0, np.degrees(np.arctan2(u[1], u[0])))).translate(tuple(p))

def profile(ztop):
    """outer (r, z) of the cup, z relative to REST, from the axis at Z_BOT round to the axis at ztop"""
    zf = Z_FRAME - REST[2]
    z = np.linspace(zf, ztop - RIM_R, 400)
    k = (R_JOIN - LOW[0][0]) / (Z_FRAME - LOW[0][1])                              # one straight cone from the bottom on up
    r = np.minimum(R_JOIN + k * (z - zf), np.sqrt(np.maximum(RO ** 2 - z ** 2, 0)))   # ..., then the sphere
    rc, zc = r[-1] - RIM_R, ztop - RIM_R                                          # round the top's outer edge
    t = np.linspace(0, np.pi / 2, 12)
    pts = [(0, Z_BOT - REST[2])] + [(lr, lz - REST[2]) for lr, lz in LOW] + list(zip(r, z)) + list(zip(rc + RIM_R * np.cos(t), zc + RIM_R * np.sin(t))) + [(0, ztop)]
    return pts

def fbox(lo, hi):
    """box from Fusion coordinates into the cup's frame"""
    o = np.array([TBX, TBY, 0]) + REST
    lo, hi = np.array(lo, float) - o, np.array(hi, float) - o
    return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))

def hood(x0=None):
    """the sensor hood: a rounded box (from x0 if given), its top edge rounded RIM_R"""
    (hx0, y0), (x1, y1) = HOOD
    x0 = hx0 if x0 is None else x0
    r = HOOD_R
    sq = mf.CrossSection.square((x1 - x0 - 2 * r, y1 - y0 - 2 * r)).translate((x0 + r, y0 + r)).offset(r, mf.JoinType.Round, circular_segments=48)
    o = np.array([TBX, TBY, 0]) + REST
    sq = sq.translate((-o[0], -o[1]))
    zt = VISOR_Z - o[2]
    h = mf.Manifold.extrude(sq, VISOR_Z - RIM_R - Z_BOT).translate((0, 0, Z_BOT - o[2]))
    cap = mf.Manifold.batch_hull([mf.Manifold.extrude(sq.offset(-RIM_R * (1 - np.cos(t)), mf.JoinType.Round), 0.01).translate((0, 0, zt - RIM_R + RIM_R * np.sin(t) - 0.01)) for t in np.linspace(0, np.pi / 2, 6)])
    h = h + cap
    return h - fbox((HOOD_TONGUE_X, -200, -50), (200, 0, HOOD_Z_TONGUE))      # over the tongue it sits higher

def label(text, depth=0.4, size=5.0):
    """text cut into the hood's top (x ~ 20.5, reads from the thumb side, -x), depth deep"""
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    polys = [p for p in TextPath((0, 0), text, size=size, prop=FontProperties(family='DejaVu Sans', weight='bold')).to_polygons() if len(p) > 2]
    pts = np.vstack(polys); c = (pts.min(0) + pts.max(0)) / 2
    cs = mf.CrossSection([[(20.5 + (q[1] - c[1]), -(q[0] - c[0])) for q in p] for p in polys], mf.FillRule.EvenOdd)
    zv = VISOR_Z - REST[2]
    return mf.Manifold.extrude(cs, depth + 1).translate((0, 0, zv - depth))

def build(narrow, off=(0, 0, 0)):
    cupsph = mf.Manifold.sphere(CUP_R, 512).translate((0, 0, CUP_DZ)) ^ mf.Manifold.sphere(BALL_R + G_UP, 512)
    ztop = 0.0 if narrow is None else np.sqrt((BALL_R + G_UP) ** 2 - (BALL_R - narrow / 2) ** 2)
    el = np.degrees(np.arcsin(ztop / BALL_R))
    cup = mf.Manifold.revolve(mf.CrossSection([profile(ztop)]), 360)
    zv = VISOR_Z - REST[2]
    # visor: the hood's box carried on toward the ball to x = VISOR_X, rounded by the cup's outer sphere, above the frame
    visor = (hood(VISOR_X + TBX + REST[0]) ^ mf.Manifold.sphere(RO, 512)).trim_by_plane((0, 0, 1), Z_FRAME - REST[2])
    cup = cup + visor
    parts = case_part('sage60_right_top') + case_part('sage60_right_bottom')
    grow = lambda p, c: [p.translate(d) for d in [(0, 0, 0)] + [tuple(c * np.eye(3)[i] * k) for i in range(3) for k in (1, -1)]]
    # the cases, 0.3 all round; the bottom case only 0.1: its pocket still has a tab (thumb side, z -4) where the old case was
    # open, and 0.3 round it bit a step into the cone
    cases = mf.Manifold.batch_boolean(grow(case_part('sage60_right_top'), 0.3) + grow(case_part('sage60_right_bottom'), 0.1), mf.OpType.Add)
    cup = cup - cases
    zb = Z_BOT - REST[2]
    cyl = lambda c, r, h, z=zb: mf.Manifold.cylinder(h, r, r, 96).translate((c[0], c[1], z))
    mags = [(x - TBX - REST[0], y - TBY - REST[1]) for x, y in TB_SCREWS]
    bosses = [mf.Manifold.batch_hull([cyl(c, MAG_BOSS_R, MAG_H + LID), cyl((HOOD_X + 1.0, c[1]), MAG_BOSS_R, MAG_H + LID)]) for c in mags]
    m = (hood() - parts) + cup + (mf.Manifold.batch_boolean(bosses, mf.OpType.Add) - parts)       # bosses: no 0.3, as the old ears
    m = m - mf.Manifold.batch_boolean([cyl(c, MAG_D / 2, MAG_H, zb - 0.01) for c in mags], mf.OpType.Add)
    m = m - cyl((0, 0), 6.8, 10.0, zb - 1.0)                                              # push-out hole under the ball
    for a in SUP_AZ:
        u = unit(-SUP_EL, a)
        m = m - along(mf.Manifold.cylinder(BALL_R + 2.0 - 15.0, 1.0 / np.cos(np.pi / 6), 1.0 / np.cos(np.pi / 6), 6), u, u * 15.0 + off)
    m = m - cupsph.translate(off) - mf.Manifold.sphere(BALL_R + HOOD_CLR, 256).translate(off)
    m = m - mf.Manifold.batch_boolean([fbox(lo, hi) for lo, hi in HOOD_VOIDS], mf.OpType.Add)
    return m, el, ztop

def case_part(name):
    import re
    x = zipfile.ZipFile(os.path.join(HERE, '../../production/case_print/%s.3mf' % name)).read('3D/3dmodel.model').decode()
    v = np.array(re.findall(r'<vertex x="([-\d.eE]+)" y="([-\d.eE]+)" z="([-\d.eE]+)"', x), float) - [TBX, TBY, 0] - REST
    t = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', x), np.uint32)
    return mf.Manifold(mf.Mesh(vert_properties=v.astype(np.float32), tri_verts=t))

def plate(meshes, path):
    """all variants on one A1 mini plate, 2 x 3, named collar_<name>"""
    objs, items = [], []
    for i, (name, (v, t)) in enumerate(meshes.items(), 1):
        v = v - v.min(0)
        vs = ''.join('<vertex x="%.5f" y="%.5f" z="%.5f"/>' % tuple(q) for q in v)
        ts = ''.join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(q) for q in t)
        objs.append('<object id="%d" name="collar_%s" type="model"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>' % (i, name, vs, ts))
        items.append('<item objectid="%d" transform="1 0 0 0 1 0 0 0 1 %.1f %.1f 0"/>' % (i, 30 + 57 * ((i - 1) % 2), 25 + 47 * ((i - 1) // 2)))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model', '<?xml version="1.0" encoding="utf-8"?>\n<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" unit="millimeter"><resources>%s</resources><build>%s</build></model>' % (''.join(objs), ''.join(items)))

def main():
    top, bot = case_part('sage60_right_top'), case_part('sage60_right_bottom')
    out = {}
    for name, (narrow, off) in VARIANTS.items():
        m, el, zl = build(narrow, off)
        m = m - label(name)
        print('%-4s opening -%.1f (rim %5.1f deg, %4.1f from the top case top) | case overlap %.3f mm3 | ball overlap %.3f | max z %.1f'
              % (name, narrow or 0, el, REST[2] + zl - 7.0, (m ^ top).volume() + (m ^ bot).volume(),
                 (m ^ mf.Manifold.sphere(BALL_R, 256).translate(off)).volume(), m.bounding_box()[5] + REST[2]))
        mesh = m.translate(tuple(REST + [0, 0, 9.0])).to_mesh()
        v, t = np.array(mesh.vert_properties)[:, :3].astype(float), np.array(mesh.tri_verts)
        write3mf(os.path.join(HERE, '../../production/case_print/trackballcase_collar_%s.3mf' % name), v, t)
        out[name] = (v, t)
    plate(out, os.path.join(HERE, '../../production/case_print/trackballcase_collar_all.3mf'))

if __name__ == '__main__':
    main()
