"""Run with KiCad's Python; reads source PCBs without modifying them."""
import json, hashlib
from pathlib import Path
import pcbnew as p
ROOT=Path(__file__).resolve().parents[2]
def pt(v): return [p.ToMM(v.x),p.ToMM(v.y)]
def shape(d):
 s={'type':d.GetShapeStr(),'start':pt(d.GetStart()),'end':pt(d.GetEnd())}
 if d.GetShape()==p.S_ARC: s['mid']=pt(d.GetArcMid())
 return s
out={}
for name,rel in [('left','pcb/mx_main/mx.kicad_pcb'),('right','pcb/mx_right_tb/mx_right.kicad_pcb')]:
 b=p.LoadBoard(str(ROOT/rel)); fps=[]
 for f in b.GetFootprints():
  fps.append({'ref':f.GetReference(),'id':str(f.GetFPID().GetLibItemName()),'at':pt(f.GetPosition()),'angle':f.GetOrientationDegrees(), 'holes':[{'at':pt(x.GetPosition()),'size':pt(x.GetDrillSize())} for x in f.Pads() if x.GetDrillSize().x]})
 out[name]={'path':rel,'sha256':hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),'footprints':fps,'edges':[shape(d) for d in b.GetDrawings() if d.GetLayer()==p.Edge_Cuts]}
Path(__file__).with_name('source_geometry.json').write_text(json.dumps(out,indent=2)+'\n')
