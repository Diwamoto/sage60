from kedge import *
import math, numpy as np
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import polygonize, unary_union
from shapely import affinity
B='/Users/daiki/Projects/sage60/pcb/'
def arcpts(s,m,e,n=16):
    (x1,y1),(x2,y2),(x3,y3)=s,m,e
    d=2*(x1*(y2-y3)+x2*(y3-y1)+x3*(y1-y2))
    ux=((x1*x1+y1*y1)*(y2-y3)+(x2*x2+y2*y2)*(y3-y1)+(x3*x3+y3*y3)*(y1-y2))/d
    uy=((x1*x1+y1*y1)*(x3-x2)+(x2*x2+y2*y2)*(x1-x3)+(x3*x3+y3*y3)*(x2-x1))/d
    r=math.hypot(x1-ux,y1-uy)
    a1=math.atan2(y1-uy,x1-ux); a2=math.atan2(y2-uy,x2-ux); a3=math.atan2(y3-uy,x3-ux)
    def norm(a): return a%(2*math.pi)
    # go from a1 to a3 passing a2
    d13=norm(a3-a1); d12=norm(a2-a1)
    if d12>d13: d13=d13-2*math.pi
    return [(ux+r*math.cos(a1+d13*i/n),uy+r*math.sin(a1+d13*i/n)) for i in range(n+1)]
def outline(path):
    _,e=edges(path); reps=[]
    def snap(p):
        for r in reps:
            if abs(r[0]-p[0])<0.05 and abs(r[1]-p[1])<0.05: return r
        reps.append(p); return p
    ls=[]; closed=[]
    for d in e:
        if d['k']=='gr_poly': closed.append(Polygon([(x,-y) for x,y in d['pts']])); continue      # inner cutouts (breakaway.py slots)
        if d['k']=='gr_circle':
            c=d['center']; closed.append(Point(c[0],-c[1]).buffer(math.dist(c,d['end']),quad_segs=8)); continue
        s=snap(d['start']); en=snap(d['end'])
        pts=arcpts(d['start'],d['mid'],d['end']) if 'mid' in d else [s,en]
        pts=[s]+pts[1:-1]+[en]
        ls.append(LineString([(x,-y) for x,y in pts]))
    polys=list(polygonize(unary_union(ls)))+closed
    polys.sort(key=lambda p:-p.area)
    return Polygon(polys[0].exterior), polys
