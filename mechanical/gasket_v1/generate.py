"""Generate gasket plate CAD from extracted KiCad geometry.
Python dependencies: shapely>=2, matplotlib, ezdxf.
Coordinates retain source PCB X/Y (Y down). DXF/STEP CAD use X/-Y.
"""
import csv, json, math, hashlib, os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/sage60-plate/mpl')
os.environ.setdefault('XDG_CACHE_HOME','/tmp/sage60-plate/cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely.affinity import affine_transform, rotate, translate
import ezdxf
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).parent
DATA=json.loads((HERE/'source_geometry.json').read_text())
THICKNESS=1.5
GAP_LIMIT=.02

def arc(e):
 a,b,c=[complex(*e[k]) for k in ['start','mid','end']]
 ax,ay=a.real,a.imag; bx,by=b.real,b.imag; cx,cy=c.real,c.imag
 d=2*(ax*(by-cy)+bx*(cy-ay)+cx*(ay-by))
 ux=((ax*ax+ay*ay)*(by-cy)+(bx*bx+by*by)*(cy-ay)+(cx*cx+cy*cy)*(ay-by))/d
 uy=((ax*ax+ay*ay)*(cx-bx)+(bx*bx+by*by)*(ax-cx)+(cx*cx+cy*cy)*(bx-ax))/d
 o=complex(ux,uy); r=abs(a-o)
 t0=math.atan2((a-o).imag,(a-o).real); tm=math.atan2((b-o).imag,(b-o).real); t1=math.atan2((c-o).imag,(c-o).real)
 sweep=(t1-t0)%(2*math.pi)
 if (tm-t0)%(2*math.pi)>sweep: sweep-=2*math.pi
 count=max(2,math.ceil(abs(sweep)/(2*math.acos(1-.001/r))))
 return [(ux+r*math.cos(t0+sweep*i/count),uy+r*math.sin(t0+sweep*i/count)) for i in range(count+1)]

def outline(edges):
 pending=[arc(e) if e['type']=='Arc' else [tuple(e['start']),tuple(e['end'])] for e in edges]
 chain=pending.pop(0); gaps=[]
 while pending:
  dist,i,rev=min((math.dist(chain[-1],v[-1] if rev else v[0]),i,rev) for i,v in enumerate(pending) for rev in [False,True])
  assert dist<GAP_LIMIT,(dist,chain[-1])
  nxt=pending.pop(i)
  if rev:nxt.reverse()
  if dist>1e-6:gaps.append(dist)
  join=tuple((a+b)/2 for a,b in zip(chain[-1],nxt[0]))
  chain[-1]=join; nxt[0]=join
  chain.extend(nxt[1:])
 assert math.dist(chain[-1],chain[0])<GAP_LIMIT
 join=tuple((a+b)/2 for a,b in zip(chain[-1],chain[0])); chain[-1]=join; chain[0]=join
 poly=Polygon(chain)
 assert poly.is_valid, 'Source outer outline self-intersects'
 return poly, gaps

def rounded(x0,y0,x1,y1,r):return box(x0+r,y0+r,x1-r,y1-r).buffer(r,quad_segs=12)
def local(poly,c,u,n):return affine_transform(poly,[u[0],n[0],u[1],n[1],c[0],c[1]])
def rings(poly):return [list(poly.exterior.coords)]+[list(r.coords) for r in poly.interiors]
def num(v):return f'{v:.6f}'
def dxf_write(path,polygons):
 doc=ezdxf.new('R2010');doc.units=4
 for layer,polys in polygons.items():
  doc.layers.new(layer)
  for poly in polys:
   for ring in rings(poly):doc.modelspace().add_lwpolyline([(x,-y) for x,y in ring[:-1]],close=True,dxfattribs={'layer':layer})
 doc.saveas(path)
def kicad(path,solid,switches,pads,pcb):
 lines=['(kicad_pcb (version 20241229) (generator "pcbnew")','(general (thickness 1.5))','(paper "A4")','(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (37 "F.SilkS" user "f.silkscreen") (44 "Edge.Cuts" user) (40 "Dwgs.User" user "user.drawings"))','(setup (pad_to_mask_clearance 0))']
 def add(poly,layer):
  for ring in rings(poly):
   for a,b in zip(ring,ring[1:]):
    if math.dist(a,b)<.000001:continue
    lines.append(f'(gr_line (start {num(a[0])} {num(a[1])}) (end {num(b[0])} {num(b[1])}) (stroke (width 0.05) (type default)) (layer "{layer}"))')
 add(solid,'Edge.Cuts')
 for g in pads:add(g,'Dwgs.User')
 # Annotations never enter manufacturing geometry.
 for f in switches:
  x,y=f['at'];lines.append(f'(gr_text "{f["ref"]}" (at {num(x)} {num(y)}) (layer "Dwgs.User") (effects (font (size 1 1) (thickness 0.15))))')
 lines.append(')');path.write_text('\n'.join(lines)+'\n')

fig,axes=plt.subplots(1,2,figsize=(15,7.5),layout='constrained')
report={}; interface={}; allrows=[]
for side,ax in zip(['left','right'],axes):
 data=DATA[side]; assert hashlib.sha256((ROOT/data['path']).read_bytes()).hexdigest()==data['sha256'],'Source changed: run extract_boards.py first'
 pcb,gaps=outline(data['edges'])
 switches=sorted([f for f in data['footprints'] if f['id']=='CherryMX_Choc_Hotswap_v2'],key=lambda f:int(f['ref'][2:]))
 assert len(switches)==(30 if side=='left' else 28)
 cuts=[translate(rotate(rounded(-7,-7,7,7,.25),-f['angle'],origin=(0,0)),*f['at']) for f in switches]
 # Open the whole controller/power pocket, including socket-height uncertainty.
 control=box(170.545,-100,300,60) if side=='left' else box(-100,-100,75.295,60)
 # Sensor connector tongue belongs to PCB only, not the floating switch plate.
 sensor=box(105,104.775,300,200) if side=='right' else Polygon()
 base=pcb.difference(unary_union([control,sensor]))
 if side=='left':
  a=(159.044426,123.621084); b=(175.732949,130.521094)
  specs=[((75,28.575),(1,0),(0,-1)),((141.97,21.9075),(1,0),(0,-1)),((56.245,74),(0,1),(-1,0)),((191.083,80),(0,1),(1,0)),((75,104.775),(1,0),(0,1))]
  support_ids=['L1','L2','L3','L4','L5','L6']
 else:
  a=(70.107051,130.521094);b=(86.795574,123.621084)
  # R5 is intentionally omitted; retain the R6 name for the diagonal ear.
  specs=[((171,28.575),(1,0),(0,-1)),((103.87,21.9075),(1,0),(0,-1)),((189.595,74),(0,1),(1,0)),((54.758,80),(0,1),(-1,0))]
  support_ids=['R1','R2','R3','R4','R6']
 u=((b[0]-a[0])/math.dist(a,b),(b[1]-a[1])/math.dist(a,b));n=(-u[1],u[0]);c=((a[0]+b[0])/2,(a[1]+b[1])/2)
 specs.append((c,u,n))
 tabs=[]; pads=[]; entries=[]
 for i,(c,u,n) in enumerate(specs):
  tabs.append(local(rounded(-8,-1.2,8,5,1),c,u,n))
  pads.append(local(box(-7,1,7,4),c,u,n))
  pc=(c[0]+2.5*n[0],c[1]+2.5*n[1])
  entry={'id':support_ids[i],'root_center_mm':c,'pad_center_pcb_mm':pc,'pad_center_cad_mm':[pc[0],-pc[1]],'tangent_pcb':u,'outward_normal_pcb':n,'pad_size_mm':[14,3],'tab_width_mm':16,'tab_extension_mm':5,'pad_thickness_uncompressed_mm':1.5,'pad_count':2}
  entries.append(entry);allrows.append([side,entry['id'],*pc,pc[0],-pc[1],math.degrees(math.atan2(-u[1],u[0])),14,3,1.5,2])
 # Closing rounds concave tab roots (~R0.8); source outer shape otherwise retained.
 outer=unary_union([base,*tabs]).buffer(.8,quad_segs=12).buffer(-.8,quad_segs=12).difference(control).simplify(.001,preserve_topology=True)
 assert outer.geom_type=='Polygon' and outer.is_valid
 # Require each cutout to remain enclosed and separated from all other cutouts.
 minedge=min(h.distance(outer.boundary) for h in cuts)
 assert minedge>1.5,minedge
 assert all(outer.contains(h) for h in cuts)
 mingap=min(a.distance(b) for i,a in enumerate(cuts) for b in cuts[i+1:])
 assert mingap>1.5,mingap
 assert all(outer.buffer(.002).covers(g) for g in pads), (side,[(i,g.difference(outer).area) for i,g in enumerate(pads)])
 assert all(g.intersection(pcb).area<.001 for g in pads),'Gasket pads must sit beyond PCB perimeter'
 solid=outer.difference(unary_union(cuts))
 assert solid.geom_type=='Polygon' and solid.is_valid and len(solid.interiors)==len(switches)
 # Eroded connectivity catches narrow necks, including controller/trackball bridges.
 assert solid.buffer(-.75).geom_type=='Polygon','Plate has a neck narrower than 1.5mm'
 name='mx_plate_gasket' if side=='left' else 'mx_plate_right_tb_gasket'
 folder=ROOT/('pcb/mx_plate/gasket_v1' if side=='left' else 'pcb/mx_plate_right_tb/gasket_v1');folder.mkdir(exist_ok=True)
 kicad(folder/(name+'.kicad_pcb'),solid,switches,pads,pcb)
 dxf_write(folder/(name+'.dxf'),{'CUT':[solid]})
 dxf_write(folder/(name+'_case_reference.dxf'),{'PLATE':[outer],'PCB_REFERENCE':[pcb],'GASKET_CONTACT':pads,'SWITCH_CUTOUT':cuts})
 (folder/(name+'_outline.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{outer.bounds[2]-outer.bounds[0]}mm" height="{outer.bounds[3]-outer.bounds[1]}mm" viewBox="{outer.bounds[0]} {outer.bounds[1]} {outer.bounds[2]-outer.bounds[0]} {outer.bounds[3]-outer.bounds[1]}">'+solid.svg(scale_factor=.2,fill_color='#e7dfcb')+'</svg>')
 # Manufacturing coordinates retained separately for independent re-read validation.
 (folder/(name+'_geometry.json')).write_text(json.dumps({'thickness_mm':THICKNESS,'rings_pcb_mm':rings(solid),'switches':switches,'source_sha256':data['sha256']},indent=2)+'\n')
 for poly in [outer]: ax.add_patch(Patch(list(poly.exterior.coords),facecolor='#e7dfcb',edgecolor='#514b40',linewidth=.8))
 for h,f in zip(cuts,switches):
  ax.add_patch(Patch(list(h.exterior.coords),facecolor='white',edgecolor='#514b40',linewidth=.5))
  ax.text(*f['at'],f['ref'],ha='center',va='center',fontsize=6,color='#514b40')
 x,y=pcb.exterior.xy;ax.plot(x,y,color='#718696',linestyle='--',linewidth=.7)
 for e,g in zip(entries,pads):
  ax.add_patch(Patch(list(g.exterior.coords),facecolor='#3c9f92',edgecolor='none'))
  c=e['pad_center_pcb_mm']; n=e['outward_normal_pcb'];ax.text(c[0]+4*n[0],c[1]+4*n[1],e['id'],ha='center',va='center',fontsize=8,color='#23786e',weight='bold')
 ax.text(181 if side=='left' else 64,43,'OPEN\nMCU / power',ha='center',va='center',fontsize=8,color='#637786')
 if side=='right':ax.text(130,118,'OPEN\nTrackball / cable',ha='center',va='center',fontsize=9,color='#637786')
 ax.set_title(f'{"LEFT" if side=="left" else "RIGHT + TRACKBALL"}  /  {len(switches)} switches',loc='left',fontsize=13,weight='bold',pad=15)
 ax.set_aspect('equal');ax.set_xlim(42,204);ax.set_ylim(142,8);ax.set_xlabel('PCB X (mm)');ax.set_ylabel('PCB Y (mm)');ax.spines[['top','right']].set_visible(False);ax.tick_params(labelsize=8)
 report[side]={'source':data['path'],'source_sha256':data['sha256'],'switch_count':len(switches),'closed_holes':len(solid.interiors),'single_connected_plate':True,'neck_check_mm':1.5,'min_switch_to_edge_mm':minedge,'min_switch_to_switch_mm':mingap,'bounds_pcb_mm':outer.bounds,'width_mm':outer.bounds[2]-outer.bounds[0],'height_mm':outer.bounds[3]-outer.bounds[1],'area_mm2':solid.area,'source_endpoint_gaps_bridged_mm':gaps,'all_gaskets_outside_pcb':True,'output':str(folder.relative_to(ROOT)/name)}
 interface[side]=entries
fig.suptitle('SAGE60  /  GASKET PLATES v1',fontsize=19,weight='bold',ha='left',x=.05)
fig.text(.5,.005,'Green = 14 x 3 mm gasket contacts, top + bottom     |     Dashed = current PCB outline     |     FR4 1.5 mm / MX cutout 14 mm R0.25',ha='center',fontsize=9,color='#514b40')
fig.savefig(HERE/'plate_overview.png',dpi=180,bbox_inches='tight');fig.savefig(HERE/'plate_overview.svg',bbox_inches='tight')
(HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/'case_interface.json').write_text(json.dumps({'units':'mm','pcb_coordinates':'X right, Y down; CAD X right, Y up, convert (x,-y)','plate_thickness':THICKNESS,'pad_contact_mm':[14,3],'gasket_uncompressed_each':1.5,'gasket_preload_fraction':.2,'gasket_compressed_each':1.2,'case_contact_face_separation':3.9,'side_clearance_each_initial':.5,'minimum_free_travel_each_initial':.5,'supports':interface},indent=2)+'\n')
with (HERE/'gasket_positions.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['side','id','pcb_x_mm','pcb_y_mm','cad_x_mm','cad_y_mm','cad_angle_deg','length_mm','width_mm','thickness_mm','quantity']);w.writerows(allrows)
print(json.dumps(report,indent=2))
