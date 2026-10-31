# polygon ring -> list of curves: ('line',p,q) / ('arc',p,m,q) / ('spline',[pts])
import math, numpy as np
def _circ(a,b,c):
    (x1,y1),(x2,y2),(x3,y3)=a,b,c
    d=2*(x1*(y2-y3)+x2*(y3-y1)+x3*(y1-y2))
    if abs(d)<1e-9: return None
    ux=((x1*x1+y1*y1)*(y2-y3)+(x2*x2+y2*y2)*(y3-y1)+(x3*x3+y3*y3)*(y1-y2))/d
    uy=((x1*x1+y1*y1)*(x3-x2)+(x2*x2+y2*y2)*(x1-x3)+(x3*x3+y3*y3)*(x2-x1))/d
    return ux,uy,math.hypot(x1-ux,y1-uy)
def ring_curves(coords, short=1.6, tol=0.03, keep=None):
    """keep: list of protected original curves [('line',p,q)|('spline',pts)] emitted verbatim when the run lies on them"""
    P=[tuple(map(float,c)) for c in coords]
    if P[0]==P[-1]: P=P[:-1]
    n=len(P)
    L=[math.dist(P[i],P[(i+1)%n]) for i in range(n)]
    longi=[l>=short for l in L]
    # rotate so that we start at the beginning of a long segment (if any)
    if any(longi):
        s=longi.index(True); P=P[s:]+P[:s]; L=L[s:]+L[:s]; longi=longi[s:]+longi[:s]
    out=[]; i=0
    while i<n:
        if longi[i]:
            out.append(('line',P[i],P[(i+1)%n])); i+=1; continue
        j=i
        while j<n and not longi[j]: j+=1
        pts=[P[k%n] for k in range(i,j+1)]
        out+=_fit(pts,tol)
        i=j
    return out
def _fit(pts,tol):
    if len(pts)==2: return [('line',pts[0],pts[1])]
    # try single arc
    c=_circ(pts[0],pts[len(pts)//2],pts[-1])
    if c and c[2]<200 and max(abs(math.dist(p,c[:2])-c[2]) for p in pts)<tol:
        return [('arc',pts[0],pts[len(pts)//2],pts[-1])] if len(pts)>=3 else [('line',pts[0],pts[1])]
    # split at the point of max curvature change? -> greedy arcs, else spline
    res=[]; s=0
    while s<len(pts)-1:
        e=len(pts)-1
        while e>s+2:
            c=_circ(pts[s],pts[(s+e)//2],pts[e])
            if c and c[2]<200 and max(abs(math.dist(p,c[:2])-c[2]) for p in pts[s:e+1])<tol: break
            e-=1
        if e>s+2: res.append(('arc',pts[s],pts[(s+e)//2],pts[e])); s=e
        else:
            # gather spline run until an arc fits again
            t=s; 
            res.append(('seg',pts[s],pts[s+1])); s+=1
    # merge consecutive 'seg' into splines
    out=[]; buf=[]
    for c in res+[('end',)]:
        if c[0]=='seg':
            if not buf: buf=[c[1]]
            buf.append(c[2])
        else:
            if buf:
                if len(buf)==2: out.append(('line',buf[0],buf[1]))
                else:
                    # thin fit points to >=0.8mm spacing keeping ends
                    th=[buf[0]]
                    for p in buf[1:-1]:
                        if math.dist(p,th[-1])>=0.8: th.append(p)
                    if math.dist(th[-1],buf[-1])<0.4 and len(th)>1: th[-1]=buf[-1]
                    else: th.append(buf[-1])
                    out.append(('spline',th) if len(th)>2 else ('line',th[0],th[-1]))
                buf=[]
            if c[0]!='end': out.append(c)
    return out
