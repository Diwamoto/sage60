import numpy as np,struct
def load(p='trackballcase.stl'):
    d=open(p,'rb').read(); n=struct.unpack('<I',d[80:84])[0]
    a=np.frombuffer(d[84:84+50*n],dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]))
    return a['v'].reshape(-1,3,3).astype(float)
def slice_segs(t,z):
    segs=[]
    for tri in t:
        d=tri[:,2]-z
        if (d>0).all() or (d<0).all(): continue
        pts=[]
        for i in range(3):
            a,b=tri[i],tri[(i+1)%3]; da,db=d[i],d[(i+1)%3]
            if da==0: pts.append(a[:2])
            if (da<0<db) or (db<0<da):
                s=da/(da-db); pts.append((a+(b-a)*s)[:2])
        if len(pts)>=2: segs.append(pts[:2])
    return segs
