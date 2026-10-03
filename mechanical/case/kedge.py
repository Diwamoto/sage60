import re,sys,math
def parse(path):
    s=open(path).read(); i=0; n=len(s)
    def tok():
        nonlocal i
        while i<n and s[i] in ' \t\r\n': i+=1
        if s[i] in '()': i+=1; return s[i-1]
        if s[i]=='"':
            j=i+1
            while s[j]!='"':
                j+= 2 if s[j]=='\\' else 1
            v=s[i+1:j]; i=j+1; return ('s',v)
        j=i
        while s[j] not in ' \t\r\n()': j+=1
        v=s[i:j]; i=j; return v
    def expr():
        t=tok()
        if t!='(': return t
        L=[]
        while True:
            while s[i] in ' \t\r\n': globals()['_']=0; break
            t2=peek()
            if t2==')': tok(); return L
            L.append(expr())
    def peek():
        nonlocal i
        while i<n and s[i] in ' \t\r\n': i+=1
        return s[i]
    return expr()
def get(L,k):
    for x in L:
        if isinstance(x,list) and x and x[0]==k: return x
def S(x): return x[1] if isinstance(x,tuple) else x
def edges(path,layer='Edge.Cuts'):
    t=parse(path); out=[]
    for e in t:
        if not isinstance(e,list): continue
        if e[0] in ('gr_line','gr_arc','gr_circle','gr_rect','gr_poly'):
            l=get(e,'layer')
            if l and S(l[1])==layer:
                d={'k':e[0]}
                for k in ('start','mid','end','center'):
                    g=get(e,k)
                    if g: d[k]=(float(g[1]),float(g[2]))
                if e[0]=='gr_poly':
                    d['pts']=[(float(p[1]),float(p[2])) for p in get(e,'pts')[1:]]
                out.append(d)
    return t,out
