"""plates (KiCad Edge.Cuts) -> case/sage60_shared_plate.3mf for test prints.  MX and Choc v2 share the 1.2 mm plate (2026-10-04);
the right half is the same plate, snipped at the trackball and the front tab, flipped.  The mesh is the Edge.Cuts outline
extruded here (no kicad-cli: it hung, 2026-10-06).  Checks the mesh is closed and its volume matches the outline x thickness."""
import zipfile
import numpy as np
import shapely
from shapely.geometry import Polygon
from geo import outline, B
from shapely.ops import unary_union

OUT = '/Users/daiki/Projects/sage60/case/'
PLATES = {'shared': 'mx_plate/mx_plate.kicad_pcb'}
T = {'shared': 1.2}

def extrude(poly, t):
    """closed triangle mesh (n, 3, 3) of a plan polygon with holes, z 0..t, outward normals"""
    poly = shapely.geometry.polygon.orient(poly, 1.0)                  # exterior CCW, holes CW
    tri = [np.array(g.exterior.coords[:3]) for g in shapely.constrained_delaunay_triangles(poly).geoms]
    out = []
    for a in tri:
        u, v = a[1] - a[0], a[2] - a[0]
        if u[0] * v[1] - u[1] * v[0] < 0: a = a[::-1]                    # CCW seen from +z
        out.append(np.c_[a[::-1], np.zeros(3)]); out.append(np.c_[a, np.full(3, t)])
    for ring in [poly.exterior] + list(poly.interiors):                # walls: ring direction leaves the solid on the left
        c = np.array(ring.coords)
        for p, q in zip(c[:-1], c[1:]):
            P0, Q0, P1, Q1 = [*p, 0], [*q, 0], [*p, t], [*q, t]
            out += [[P0, Q0, Q1], [P0, Q1, P1]]
    return np.array(out, dtype=float)

def write_3mf(tris, path):
    verts, idx = np.unique(np.round(tris.reshape(-1, 3), 5), axis=0, return_inverse=True)
    faces = idx.reshape(-1, 3)
    faces = faces[(faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])]
    # closed + consistently oriented: every directed edge appears once and its reverse once
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    fwd = set(map(tuple, e)); assert len(fwd) == len(e) and all((b, a) in fwd for a, b in fwd), 'mesh not closed'
    vx = '\n'.join('<vertex x="%.5f" y="%.5f" z="%.5f"/>' % tuple(p) for p in verts)
    tx = '\n'.join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in faces)
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<resources><object id="1" type="model"><mesh><vertices>\n%s\n</vertices><triangles>\n%s\n</triangles></mesh></object></resources>'
             '<build><item objectid="1"/></build></model>' % (vx, tx))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model', model)
    t = verts[faces]
    vol = np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6
    return vol, verts.min(0), verts.max(0)

for side, f in PLATES.items():
    t = T[side]
    _, polys = outline(B + f)
    outer = polys[0]; holes = unary_union([p for p in polys[1:] if outer.contains(p.representative_point())])
    plate = outer.difference(holes)                  # outer already carries the switch cutouts; holes = slots, perforations
    assert plate.geom_type == 'Polygon', plate.geom_type
    vol, lo, hi = write_3mf(extrude(plate, t), OUT + 'sage60_%s_plate.3mf' % side)
    want = plate.area * t
    print('%-5s size %.1f x %.1f x %.2f mm  holes %d  volume %.1f mm3 (outline %.1f, %+.3f%%)' % (side, *(hi - lo), len(plate.interiors), vol, want, 100 * (vol / want - 1)))
    assert abs(hi[2] - lo[2] - t) < 0.01 and abs(vol / want - 1) < 0.001
    assert len(plate.interiors) == len(polys) - 1, (len(plate.interiors), len(polys) - 1)    # every Edge.Cuts loop is a hole
