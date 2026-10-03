from stl import load, slice_segs
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union, polygonize
from shapely import affinity
import numpy as np
TBX,TBY=160.995-25.94, -122.395-0.08   # ball centre (Fusion XY)
def tb_tris():
    t=load(__file__.rsplit('/', 1)[0] + '/trackballcase.stl')
    t=t.copy(); t[:,:,0]+=TBX; t[:,:,1]+=TBY; return t
def footprint(t, zmin=-1e9, zmax=1e9):
    # union of projected triangles with any vertex in z range (approx)
    m=(t[:,:,2].max(1)>=zmin)&(t[:,:,2].min(1)<=zmax)
    polys=[Polygon(tr[:,:2]) for tr in t[m]]
    polys=[p.buffer(0.01) for p in polys if p.area>1e-6]
    return unary_union(polys).buffer(-0.01)
