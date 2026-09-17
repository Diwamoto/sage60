"""Re-read generated CAD and verify geometry, source alignment and mesh closure."""
import json, math, subprocess, struct, re
from collections import Counter
from pathlib import Path
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize
from shapely.affinity import rotate, translate
import ezdxf
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
KPY='/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3'
extract='''import json,pcbnew as p,sys
b=p.LoadBoard(sys.argv[1])
r={'thickness':p.ToMM(b.GetDesignSettings().GetBoardThickness()),'footprints':len(list(b.GetFootprints())),'tracks':len(list(b.GetTracks())),'zones':len(list(b.Zones())),'edges':[[[p.ToMM(v.x),p.ToMM(v.y)] for v in (d.GetStart(),d.GetEnd())] for d in b.GetDrawings() if d.GetLayer()==p.Edge_Cuts]}
print(json.dumps(r))'''
results={}

def read_stl(path):
    """Read either KiCad's default ASCII STL or a binary STL."""
    raw=path.read_bytes()
    # KiCad writes ASCII STL by default.  A binary STL has an 80-byte header,
    # a triangle count, and an exact 84 + 50*n byte length.
    if len(raw) >= 84:
        n=struct.unpack_from('<I',raw,80)[0]
        if len(raw)==84+50*n:
            faces=[];vertices=[]
            for i in range(n):
                vals=struct.unpack_from('<12fH',raw,84+i*50)
                tri=[tuple(round(v,4) for v in vals[j:j+3]) for j in (3,6,9)]
                faces.append(tri);vertices.extend(tri)
            return faces,vertices,'binary'
    text=raw.decode('ascii')
    values=[]
    for line in text.splitlines():
        m=re.match(r'\s*vertex\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)',line)
        if m:
            values.append(tuple(round(float(x),4) for x in m.groups()))
    assert values and len(values)%3==0,'STL contains no complete ASCII triangles'
    faces=[values[i:i+3] for i in range(0,len(values),3)]
    return faces,values,'ascii'

for side,rel in [('left','pcb/mx_plate/gasket_v1/mx_plate_gasket'),('right','pcb/mx_plate_right_tb/gasket_v1/mx_plate_right_tb_gasket')]:
 stem=ROOT/rel
 expected=json.loads(stem.with_name(stem.name+'_geometry.json').read_text())
 r=subprocess.run([KPY,'-c',extract,str(stem.with_suffix('.kicad_pcb'))],check=True,capture_output=True,text=True)
 saved=json.loads(r.stdout);assert saved['thickness']==1.5
 assert saved['tracks']==saved['zones']==saved['footprints']==0
 polys=list(polygonize([LineString(e) for e in saved['edges']]))
 plate=max(polys,key=lambda p:p.area);target=Polygon(expected['rings_pcb_mm'][0],expected['rings_pcb_mm'][1:])
 assert plate.symmetric_difference(target).area<.001
 assert len(plate.interiors)==len(expected['switches'])
 holes=[Polygon(r) for r in plate.interiors];errors=[]
 for f in expected['switches']:
  h=min(holes,key=lambda h:math.dist(h.centroid.coords[0],f['at']))
  err=math.dist(h.centroid.coords[0],f['at']);assert err<.00001;errors.append(err)
  flat=rotate(translate(h,-f['at'][0],-f['at'][1]),f['angle'],origin=(0,0))
  assert all(abs(a-b)<.00001 for a,b in zip(flat.bounds,[-7,-7,7,7]))
 doc=ezdxf.readfile(stem.with_suffix('.dxf'));entities=list(doc.modelspace())
 assert len(entities)==len(holes)+1 and all(e.closed for e in entities)
 assert doc.units==4
 for ent in entities:
  poly=Polygon([(p[0],-p[1]) for p in ent.get_points()])
  assert min(poly.hausdorff_distance(Polygon(r)) for r in expected['rings_pcb_mm'])<.00001
 faces,vertices,stl_format=read_stl(stem.with_suffix('.stl'));n=len(faces)
 edges=Counter(tuple(sorted([a,b])) for tri in faces for a,b in zip(tri,tri[1:]+tri[:1]))
 assert all(count==2 for count in edges.values()),'Non-watertight STL'
 bounds=[[min(v[i] for v in vertices),max(v[i] for v in vertices)] for i in range(3)]
 # KiCad's STL exporter places the default solder-mask stackup surfaces at
 # z=0 and z=1.43 mm for a 1.50 mm board body.  The authoritative thickness
 # remains the PCB/DXF value (1.50 mm); retain the check so an accidental
 # scale or zero-thickness export still fails.
 stl_thickness=bounds[2][1]-bounds[2][0]
 assert abs(stl_thickness-1.43)<.01
 bx=target.bounds;assert max(abs(a-b) for a,b in zip([*bounds[0],*bounds[1]],[bx[0],bx[2],-bx[3],-bx[1]]))<.001
 results[side]={'kicad_readback':True,'switch_count':len(holes),'max_center_error_mm':max(errors),'rotation_and_14mm_holes_match':True,'dxf_closed_contours_mm_units':True,'stl_watertight':True,'stl_format':stl_format,'stl_triangles':n,'stl_bounds_xyz_mm':bounds,'stl_preview_thickness_mm':stl_thickness,'pcb_authoritative_thickness_mm':1.5,'copper_objects':0}
(HERE/'saved_cad_validation.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
