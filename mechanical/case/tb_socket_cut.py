"""one-shot (2026-10-28): trackball case for the J1 pin socket (tongue_socket.py; since 2026-10-28 the round-pin socket of fusion/stage6.py).  Two cuts in case/trackballcase_low.3mf (the
print file; trackballcase_low.stl = it with z + 2):
  - the sensor hood's back wall (x 162.64..164.16) is cut from below to z -2.2 over the pocket's width (y -131.695..-113.095),
    so the pin socket on the sensor board (z -5.0..-2.5) passes through and the hood still drops on from above
  - the hood's underside over the PCB tongue (x >= 159.6) is raised from z -5.3 to -4.7: it sat 0.3 into the PCB (TB_SEAT puts
    the sensor box 0.3 below the PCB top instead of above it); now it is tb_gap 0.3 above, the rest of the case unchanged
  - (2026-10-29) the two screw bosses grow to r MAG_BOSS_R up to MAG_H + 0.8 and take a phi6x3 magnet from below (MAG_D x MAG_H),
    facing one in the bottom case (fusion/stage2.py TB_MAG_CUT) instead of the M1.7 screws
Coordinates below are Fusion (MX); 3MF = (x - TBX, y - TBY, z + TB_ZREL0 - 2).  Then checks the cut case against the PCB, the
socket, the header and the sensor board.  Running it again re-cuts the already cut file (no change)."""
import re, zipfile
import numpy as np
import manifold3d as mf
from shapely.geometry.polygon import orient
from tb import TBX, TBY
from make_right import TB_ZREL0, TB_SCREWS
from geo import B, outline

SRC = '../../case/trackballcase_low.3mf'
STL = 'trackballcase_low.stl'
CUTS = [((162.3, -131.695, -8.0), (166.0, -113.095, -2.2)),      # back wall, for the socket
        ((159.6, -140.0, -8.0), (166.0, -100.0, -4.7))]          # underside over the tongue
MAG_D, MAG_H, MAG_BOSS_R = 6.1, 3.1, 3.75     # boss: 0.41 to the pocket wall at the back one (make_right.py TB_POCKET)
# parts at assembly (fusion/stage6.py): board centred in its slot, round-pin socket 6604S on its +x face, thin-pin header
# PHA-1x40RG (pins 1.0 above the PCB, cut to 2.5) in J1 (x 166.64), its housing against the socket
YC, PCB_TOP = -122.395, -5.0
PARTS = {'socket 6604S-7': ((158.94, YC - 8.89, -5.27), (163.14, YC + 8.89, -2.73)),
         'header PHA-1x7RG': ((163.14, YC - 8.89, -5.0), (165.14, YC + 8.89, -3.0)),
         'header leads': ((165.14, YC - 8.57, -4.25), (166.9, YC + 8.57, -3.75)),
         'sensor board': ((157.34, YC - 11.0, -9.0), (158.94, YC + 11.0, 14.5))}

def read3mf(p):
    x = zipfile.ZipFile(p).read('3D/3dmodel.model').decode()
    v = np.array(re.findall(r'<vertex x="([-\d.eE]+)" y="([-\d.eE]+)" z="([-\d.eE]+)"', x), float)
    t = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', x), np.uint32)
    return v, t

def write3mf(p, v, t):
    verts = ''.join('<vertex x="%.6f" y="%.6f" z="%.6f" />' % tuple(q) for q in v)
    tris = ''.join('<triangle v1="%d" v2="%d" v3="%d" />' % tuple(q) for q in t)
    model = ('<?xml version="1.0" encoding="utf-8"?>\n<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" unit="millimeter">'
             '<resources><object id="1" name="trackballcase_low" type="model"><mesh><vertices>%s</vertices><triangles>%s</triangles>'
             '</mesh></object></resources><build><item objectid="1" /></build></model>' % (verts, tris))
    with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml" /></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" /></Relationships>')
        z.writestr('3D/3dmodel.model', model)

def write_stl(p, v, t):
    tri = v[t].astype(np.float32)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    a = np.zeros(len(t), dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))
    a['n'] = n; a['v'] = tri.reshape(-1, 9)
    open(p, 'wb').write(b'trackballcase_low (tb_socket_cut.py)'.ljust(80, b' ') + np.uint32(len(t)).tobytes() + a.tobytes())

OFF = np.array([TBX, TBY, -TB_ZREL0 + 2.0])          # 3MF -> Fusion

def cube(lo, hi):
    lo, hi = np.array(lo) - OFF, np.array(hi) - OFF
    return mf.Manifold.cube(hi - lo).translate(lo)

def main():
    v, t = read3mf(SRC)
    m = mf.Manifold(mf.Mesh(vert_properties=v.astype(np.float32), tri_verts=t))
    assert m.status() == mf.Error.NoError, m.status()
    vol0 = m.volume()
    z0 = m.bounding_box()[2]
    cyl = lambda c, r, h: mf.Manifold.cylinder(h, r, r, 96).translate((c[0] - TBX, c[1] - TBY, z0))
    for c in TB_SCREWS: m = m + cyl(c, MAG_BOSS_R, MAG_H + 0.8)
    for lo, hi in CUTS: m = m - cube(lo, hi)
    for c in TB_SCREWS: m = m - cyl(c, MAG_D / 2, MAG_H).translate((0, 0, -0.01))
    out = m.to_mesh(); v2, t2 = np.array(out.vert_properties)[:, :3].astype(float), np.array(out.tri_verts)
    print('trackball case: volume %.1f -> %.1f mm3 (%.1f removed), %d triangles' % (vol0, m.volume(), vol0 - m.volume(), len(t2)))
    # checks (Fusion coordinates)
    pcb = orient(outline(B + 'mx_right_tb/mx_right_tb.kicad_pcb')[0])
    xy = [tuple(q) for q in pcb.exterior.coords[:-1]]
    ext = mf.CrossSection([xy]).extrude(1.6).translate((0, 0, PCB_TOP - 1.6))
    case = m.translate(tuple(OFF))
    for name, body in [('PCB', ext)] + [(k, mf.Manifold.cube(np.array(hi) - lo).translate(lo)) for k, (lo, hi) in PARTS.items()]:
        print('  %-16s overlap %.3f mm3' % (name, (case ^ body).volume()))
    write3mf(SRC, v2, t2)
    write_stl(STL, v2 + [0, 0, 2.0], t2)

if __name__ == '__main__':
    main()
