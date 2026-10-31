"""one-shot (2026-10-14): after centre_hole.py widened the switch centre holes to phi 5, reroute the track pieces that
now sit inside the hole clearance. Run with KiCad's Python (pcbnew); numpy + shapely in ./kicad_site (pip install --target kicad_site numpy shapely, with KiCad's python).
For each group of offending segments (same net / layer, connected) the group is ripped up, grown until both open ends
are clear, and rerouted on the same layer by an octilinear A* on a 0.05 mm grid around the obstacles (other-net copper
+ CLR, every drilled hole + HOLE_CLR, board edge + EDGE_CLR). Zones are refilled at the end.
usage: <kicad python> centre_reroute.py <board.kicad_pcb> [--dry]"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))   # case/ (casegeo, geo, ...)
import sys, glob, os, math, heapq
sys.path += [os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kicad_site')]
import numpy as np
import pcbnew
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
import shapely

CLR, HOLE_CLR, EDGE_CLR = 0.2, 0.25, 0.3      # mm (JLC 2-layer: 0.127 / 0.25 / 0.3)
G = 0.05                                       # grid (mm)
MARGIN = 0.03                                  # extra on every obstacle for the grid
M, F = pcbnew.ToMM, pcbnew.FromMM

def holes(b):
    out = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetDrillSize().x > 0:
                q = p.GetPosition(); out.append((M(q.x), M(q.y), M(p.GetDrillSize().x) / 2, p, fp))
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            q = t.GetPosition(); out.append((M(q.x), M(q.y), M(t.GetDrillValue()) / 2, t, None))
    return out

def centres(b):
    return [(M(p.GetPosition().x), M(p.GetPosition().y), M(p.GetDrillSize().x) / 2) for fp in b.GetFootprints()
            if 'Choc_Hotswap' in fp.GetFPIDAsString() for p in fp.Pads()
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH and abs(M(p.GetDrillSize().x) - 5.0) < 1e-3]

def seg(t):
    return (M(t.GetStart().x), M(t.GetStart().y)), (M(t.GetEnd().x), M(t.GetEnd().y))

def offending(b, C):
    bad = []
    for t in b.GetTracks():
        if t.Type() != pcbnew.PCB_TRACE_T: continue
        ls = LineString(seg(t)); w = M(t.GetWidth())
        if any(ls.distance(Point(x, y)) < r + HOLE_CLR + w / 2 - 1e-4 for x, y, r in C): bad.append(t)
    vb = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and any(
        math.hypot(M(t.GetPosition().x) - x, M(t.GetPosition().y) - y) < r + HOLE_CLR + M(t.GetWidth(pcbnew.F_Cu)) / 2 for x, y, r in C)]
    return bad, vb

def uid(o): return o.m_Uuid.AsString()

def key(p): return (round(p[0], 4), round(p[1], 4))

def anchors(b, net, layer):
    """points where the net is held on this layer by something that isn't a track: pads and vias"""
    s = set()
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net and p.IsOnLayer(layer): s.add(key((M(p.GetPosition().x), M(p.GetPosition().y))))
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == net: s.add(key((M(t.GetPosition().x), M(t.GetPosition().y))))
    return s

def obstacles(b, net, layer, w, ignore):
    """union of keep-out areas for a track centreline of width w on layer (net's own copper is free)"""
    geo = []
    for t in b.GetTracks():
        if uid(t) in ignore: continue
        if t.Type() == pcbnew.PCB_VIA_T:
            if t.GetNetname() != net:
                geo.append(Point(M(t.GetPosition().x), M(t.GetPosition().y)).buffer(M(t.GetWidth(pcbnew.F_Cu)) / 2 + CLR + w / 2 + MARGIN, 16))
        elif t.GetLayer() == layer and t.GetNetname() != net:
            geo.append(LineString(seg(t)).buffer(M(t.GetWidth()) / 2 + CLR + w / 2 + MARGIN, 8))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(layer) and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH and p.GetNetname() != net:
                ps = pcbnew.SHAPE_POLY_SET(); p.TransformShapeToPolygon(ps, layer, 0, F(0.005), pcbnew.ERROR_OUTSIDE)
                for i in range(ps.OutlineCount()):
                    o = ps.Outline(i)
                    geo.append(Polygon([(M(o.CPoint(j).x), M(o.CPoint(j).y)) for j in range(o.PointCount())]).buffer(CLR + w / 2 + MARGIN, 8))
    for x, y, r, o, _ in holes(b):
        if uid(o) in ignore: continue
        if o.GetNetname() == net and not (o.Type() == pcbnew.PCB_PAD_T and o.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH): continue
        geo.append(Point(x, y).buffer(r + HOLE_CLR + w / 2 + MARGIN, 24))
    ol = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ol, False)
    rings = [ol.Outline(0)] + [ol.Hole(0, h) for h in range(ol.HoleCount(0))]
    rings = [[(M(r.CPoint(j).x), M(r.CPoint(j).y)) for j in range(r.PointCount())] for r in rings]
    board = Polygon(rings[0], rings[1:])
    return unary_union(geo), board.buffer(-(EDGE_CLR + w / 2 + MARGIN))

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]

def astar(free, s, g):
    H, W = free.shape
    def h(p): dx, dy = abs(p[0] - g[0]), abs(p[1] - g[1]); return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)
    start = (s[0], s[1], -1); pq = [(h(s), 0.0, start)]; best = {start: 0.0}; prev = {}
    while pq:
        f, c, st = heapq.heappop(pq)
        if c > best.get(st, 1e18): continue
        i, j, d = st
        if (i, j) == g:
            path = [(i, j)]
            while st in prev: st = prev[st]; path.append(st[:2])
            return path[::-1]
        for k, (di, dj) in enumerate(DIRS):
            ni, nj = i + di, j + dj
            if not (0 <= ni < H and 0 <= nj < W) or not free[ni, nj]: continue
            if di and dj and not (free[i + di, j] and free[i, j + dj]): continue
            nc = c + (1.4142 if di and dj else 1.0) + (0 if d in (-1, k) else 6.0)    # turns cost 0.3 mm
            ns = (ni, nj, k)
            if nc < best.get(ns, 1e18): best[ns] = nc; prev[ns] = st; heapq.heappush(pq, (nc + h((ni, nj)), nc, ns))
    return None

VIA_D, VIA_DRILL, VIA_COST = 0.8, 0.4, 40.0     # same vias as the rest of the board; a hop costs 2 mm

def astar2(free, via, s, g):
    """free: [F, B] grids, via: cells where a via fits; s, g: (layer, i, j)"""
    H, W = via.shape
    def h(p): dx, dy = abs(p[1] - g[1]), abs(p[2] - g[2]); return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy) + (VIA_COST if p[0] != g[0] else 0)
    start = s + (-1,); pq = [(h(s), 0.0, start)]; best = {start: 0.0}; prev = {}
    while pq:
        f, c, st = heapq.heappop(pq)
        if c > best.get(st, 1e18): continue
        l, i, j, d = st
        if (l, i, j) == g:
            path = [st[:3]]
            while st in prev: st = prev[st]; path.append(st[:3])
            return path[::-1]
        nxt = []
        for k, (di, dj) in enumerate(DIRS):
            ni, nj = i + di, j + dj
            if not (0 <= ni < H and 0 <= nj < W) or not free[l][ni, nj]: continue
            if di and dj and not (free[l][i + di, j] and free[l][i, j + dj]): continue
            nxt.append(((l, ni, nj, k), (1.4142 if di and dj else 1.0) + (0 if d in (-1, k) else 6.0)))
        if via[i, j]: nxt.append(((1 - l, i, j, -1), VIA_COST))
        for ns, dc in nxt:
            nc = c + dc
            if nc < best.get(ns, 1e18): best[ns] = nc; prev[ns] = st; heapq.heappush(pq, (nc + h(ns[:3]), nc, ns))
    return None

def simplify(pts):
    """grid path -> corner points (keep a point only where the step direction changes)"""
    out = [pts[0]]
    for p, q, r in zip(pts, pts[1:], pts[2:]):
        if (q[0] - p[0], q[1] - p[1]) != (r[0] - q[0], r[1] - q[1]): out.append(q)
    return out + [pts[-1]]

def group(bad):
    gs = []
    for t in bad:
        a, e = map(key, seg(t)); hit = [g for g in gs if g['net'] == t.GetNetname() and g['layer'] == t.GetLayer() and (a in g['pts'] or e in g['pts'])]
        ng = {'net': t.GetNetname(), 'layer': t.GetLayer(), 'segs': [t], 'pts': {a, e}}
        for g in hit: ng['segs'] += g['segs']; ng['pts'] |= g['pts']; gs.remove(g)
        gs.append(ng)
    return gs

def ends(segs):
    cnt = {}
    for t in segs:
        for p in map(key, seg(t)): cnt[p] = cnt.get(p, 0) + 1
    return [p for p, n in cnt.items() if n == 1]

def rip(b, g, C):
    """grow the group until both open ends are clear of the new holes, then take it off the board"""
    net, layer = g['net'], g['layer']; segs = g['segs']; w = M(segs[0].GetWidth())
    anc = anchors(b, net, layer)
    hz = unary_union([Point(x, y).buffer(r + HOLE_CLR + w / 2 + MARGIN + G) for x, y, r in C])
    for _ in range(12):
        E = ends(segs)
        if len(E) != 2: raise RuntimeError('%s: %d open ends %s' % (net, len(E), E))
        grown = False
        for p in E:
            if p in anc or not hz.contains(Point(p)): continue
            nb = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T and uid(t) not in {uid(u) for u in segs}
                  and t.GetNetname() == net and t.GetLayer() == layer and p in map(key, seg(t))]
            if len(nb) == 1: segs.append(nb[0]); grown = True
        if not grown: break
    g.update(E=ends(segs), w=w, old=sum(LineString(seg(t)).length for t in segs), n=len(segs))
    for t in segs: b.Remove(t)

def own(b, net, layer, w):
    """the net's own copper on this layer, shrunk so a centreline inside it keeps the track inside it (free to run on)"""
    geo = []
    for t in b.GetTracks():
        if t.GetNetname() != net: continue
        if t.Type() == pcbnew.PCB_VIA_T: geo.append(Point(M(t.GetPosition().x), M(t.GetPosition().y)).buffer(M(t.GetWidth(pcbnew.F_Cu)) / 2, 16))
        elif t.GetLayer() == layer: geo.append(LineString(seg(t)).buffer(M(t.GetWidth()) / 2, 8))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(layer) and p.GetNetname() == net:
                ps = pcbnew.SHAPE_POLY_SET(); p.TransformShapeToPolygon(ps, layer, 0, F(0.005), pcbnew.ERROR_INSIDE)
                for i in range(ps.OutlineCount()):
                    o = ps.Outline(i); geo.append(Polygon([(M(o.CPoint(j).x), M(o.CPoint(j).y)) for j in range(o.PointCount())]))
    return unary_union(geo).buffer(-(w / 2 - G)) if geo else Polygon()

def route(b, g):
    net, layer, E, w = g['net'], g['layer'], g['E'], g['w']
    obs, board = obstacles(b, net, layer, w, set()); mine = own(b, net, layer, w)
    path = None
    for pad in (3.0, 6.0, 10.0):
        xs = [p[0] for p in E]; ys = [p[1] for p in E]
        x0, y0 = min(xs) - pad, min(ys) - pad; x1, y1 = max(xs) + pad, max(ys) + pad
        nx, ny = int((x1 - x0) / G) + 1, int((y1 - y0) / G) + 1
        X, Y = np.meshgrid(x0 + np.arange(nx) * G, y0 + np.arange(ny) * G)
        win = box(x0, y0, x1, y1)
        free = shapely.contains_xy(board.intersection(win), X, Y) & ~shapely.contains_xy(obs.intersection(win), X, Y)
        free |= shapely.contains_xy(mine.intersection(win), X, Y)
        cell = lambda p: (int(round((p[1] - y0) / G)), int(round((p[0] - x0) / G)))
        s, e = cell(E[0]), cell(E[1])
        for c in (s, e):                          # open a small disc at the terminals (they sit on the net's own copper)
            free[max(0, c[0] - 3):c[0] + 4, max(0, c[1] - 3):c[1] + 4] = True
        path = astar(free, s, e)
        if path: break
    if path:
        runs = [(layer, [(x0 + j * G, y0 + i * G) for i, j in simplify(path)])]
    else:
        runs = route2(b, g, x0, y0, X, Y, win, free, s, e)
        if not runs:
            g['dbg'] = (free, s, e, x0, y0); return False
    runs[0][1][0], runs[-1][1][-1] = E[0], E[1]
    for L, pts in runs:
        for a, c in zip(pts, pts[1:]):
            if math.hypot(c[0] - a[0], c[1] - a[1]) < 1e-6: continue
            t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(F(a[0]), F(a[1]))); t.SetEnd(pcbnew.VECTOR2I(F(c[0]), F(c[1])))
            t.SetWidth(F(w)); t.SetLayer(L); t.SetNet(b.FindNet(net)); b.Add(t)
    for (L, pts), _ in zip(runs[1:], runs):
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(F(pts[0][0]), F(pts[0][1]))); v.SetWidth(F(VIA_D)); v.SetDrill(F(VIA_DRILL))
        v.SetNet(b.FindNet(net)); b.Add(v)
    n = sum(len(p) - 1 for _, p in runs)
    g['log'] = '%-8s %s (%.1f,%.1f)-(%.1f,%.1f)  %d segs %.1f mm -> %d segs %.1f mm%s' % (net, pcbnew.LayerName(layer), *E[0], *E[1], g['n'], g['old'],
               n, sum(math.hypot(c[0] - a[0], c[1] - a[1]) for _, p in runs for a, c in zip(p, p[1:])),
               '  + %d vias %s' % (len(runs) - 1, [tuple(round(v, 2) for v in p[0]) for _, p in runs[1:]]) if len(runs) > 1 else '')
    return True

def route2(b, g, x0, y0, X, Y, win, free_l, s, e):
    """same window, both copper layers, vias allowed"""
    net, layer, w = g['net'], g['layer'], g['w']
    other = pcbnew.B_Cu if layer == pcbnew.F_Cu else pcbnew.F_Cu
    obs, board = obstacles(b, net, other, w, set())
    free_o = shapely.contains_xy(board.intersection(win), X, Y) & ~shapely.contains_xy(obs.intersection(win), X, Y)
    free_o |= shapely.contains_xy(own(b, net, other, w).intersection(win), X, Y)
    via = None
    for L in (layer, other):
        ob, bd = obstacles(b, net, L, VIA_D, set())
        v = shapely.contains_xy(bd.intersection(win), X, Y) & ~shapely.contains_xy(ob.intersection(win), X, Y)
        via = v if via is None else via & v
    path = astar2([free_l, free_o], via, (0,) + s, (0,) + e)
    if not path: return None
    runs = []
    for l, i, j in path:
        if not runs or runs[-1][0] != l: runs.append((l, []))
        runs[-1][1].append((i, j))
    return [(layer if l == 0 else other, [(x0 + j * G, y0 + i * G) for i, j in simplify(p) if True]) for l, p in runs]

def main():
    f = sys.argv[1]; b = pcbnew.LoadBoard(f); C = centres(b)
    assert C, 'run centre_hole.py first'
    bad, vb = offending(b, C)
    if vb: raise RuntimeError('vias inside the clearance: %s' % [(t.GetNetname(), M(t.GetPosition().x), M(t.GetPosition().y)) for t in vb])
    gs = group(bad)
    if os.environ.get('REVERSE'): gs = gs[::-1]
    for g in gs: rip(b, g, C)
    todo = gs
    for _ in range(4):                           # a group that can't get through yet is retried after the others
        todo = [g for g in todo if not route(b, g)]
        if not todo: break
    if todo and os.environ.get('DBG'):
        import pickle; pickle.dump([(g['net'], g['E'], g['dbg']) for g in todo], open(os.environ['DBG'], 'wb'))
    if todo: raise RuntimeError('no route: %s' % [(g['net'], g['E']) for g in todo])
    print('\n'.join(g['log'] for g in gs))
    print('total length %.1f mm' % sum(float(g['log'].split('-> ')[1].split(' segs ')[1].split(' mm')[0]) for g in gs))
    bad, vb = offending(b, C); print('left after reroute:', len(bad), len(vb))
    if '--dry' in sys.argv: return
    print('overlapping leftovers removed:', dedupe(b, {g['net'] for g in gs}))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(f); print('saved', f)

def free_end(b, t):
    """one end of t touches nothing but t (no other track end, via or pad of the net)"""
    net = t.GetNetname()
    for p in seg(t):
        q = Point(p); hit = False
        for u in b.GetTracks():
            if uid(u) == uid(t) or u.GetNetname() != net: continue
            if u.Type() == pcbnew.PCB_VIA_T: hit |= q.distance(Point(M(u.GetPosition().x), M(u.GetPosition().y))) < M(u.GetWidth(pcbnew.F_Cu)) / 2
            else: hit |= any(q.distance(Point(e)) < 1e-3 for e in seg(u))
        for fp in b.GetFootprints():
            for pd in fp.Pads():
                if pd.GetNetname() == net: hit |= q.distance(Point(M(pd.GetPosition().x), M(pd.GetPosition().y))) < 0.3
        if not hit: return True
    return False

def dedupe(b, nets):
    """drop a leftover segment that lies entirely on another segment of the same net / layer (a rip-up that stopped
    on a collinear joint leaves one, e.g. MOTION on the right PCB)"""
    n = 0
    while True:
        ts = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() in nets]
        hit = next((t for t in ts for u in ts if uid(t) != uid(u) and t.GetLayer() == u.GetLayer() and t.GetNetname() == u.GetNetname()
                    and LineString(seg(t)).length <= LineString(seg(u)).length
                    and all(LineString(seg(u)).distance(Point(p)) < 1e-3 for p in seg(t)) and free_end(b, t)), None)
        if hit is None: return n
        b.Remove(hit); n += 1

if __name__ == '__main__':
    main()
