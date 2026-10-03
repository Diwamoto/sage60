"""plates (KiCad Edge.Cuts, board thickness 1.5) -> case/sage60_{left,right}_plate.3mf for test prints.
Needs kicad-cli (KiCad 10). Checks the mesh is closed and its volume matches the KiCad outline x thickness."""
import subprocess, tempfile, zipfile, os
import numpy as np
from geo import outline, B
from shapely.ops import unary_union

OUT = '/Users/daiki/Projects/sage60/case/'
PLATES = {'left': 'mx_plate/mx_plate.kicad_pcb', 'right': 'mx_right_tb_plate/mx_right_tb_plate.kicad_pcb'}
T = 1.5

def read_ascii_stl(p):
    v = [list(map(float, l.split()[1:4])) for l in open(p) if l.strip().startswith('vertex')]
    return np.array(v).reshape(-1, 3, 3)

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
    with tempfile.TemporaryDirectory() as d:
        stl = os.path.join(d, 'p.stl')
        subprocess.run(['kicad-cli', 'pcb', 'export', 'stl', '--board-only', '--cut-vias-in-body', '-f', '-o', stl, B + f], check=True, capture_output=True)
        tris = read_ascii_stl(stl)
    z0, z1 = tris[..., 2].min(), tris[..., 2].max()      # KiCad's board body is the dielectric only (1.43): stretch to the plate thickness
    tris[..., 2] = (tris[..., 2] - z0) * T / (z1 - z0)
    vol, lo, hi = write_3mf(tris, OUT + 'sage60_%s_plate.3mf' % side)
    _, polys = outline(B + f)
    outer = polys[0]; holes = unary_union([p for p in polys[1:] if outer.contains(p.representative_point())])
    want = (outer.area - holes.area) * T     # ponytail: assumes cutouts are Edge.Cuts loops only (no NPTH pads)
    print('%-5s size %.1f x %.1f x %.2f mm  volume %.1f mm3 (KiCad outline %.1f, %+.2f%%)' % (side, *(hi - lo), vol, want, 100 * (vol / want - 1)))
    assert abs(hi[2] - lo[2] - T) < 0.01 and abs(vol / want - 1) < 0.01
