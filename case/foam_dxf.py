"""Bottom case foam (MX) outlines for ordering -> production/case_foam/sage60_{left,right}_foam.dxf (mm, seen from above, Fusion XY).
The foam fills PCB underside -> floor (4.4) and touches the PCB (2026-11-11, user, after Artair-X: damps the PCB and the hollow
cavity), so the MX hot-swap sockets and the B.Cu parts (diodes, JST) are cut out of it.
Shape = CAVITY - CLR to the walls - sockets/diodes - battery/JST pocket - MCU part (XIAO / switch pins) - (right) the trackball case pocket + sensor slot.
Plate foam -> sage60_{left,right}_plate_foam.dxf: between the plate and the PCB (gap 3.8), plate body (no tabs) & PCB, minus the
switch holes + PLATE_HOLE_CLR (MX bottom housing), the MCU part (XIAO, slide switch) and (right) J1 on the tongue.
Run with the venv from case/: venv/bin/python foam_dxf.py"""
import math, os, re
from shapely.geometry import MultiPoint
from shapely.geometry import box
from shapely.ops import unary_union
from casegeo import MCU_RING, C2, LP, B
from geo import plate_outline
from make_right import build_right
from mcu_cover_dxf import dxf

assert not LP, 'MX only (low profile: battery sits loose under the sockets, foam not designed yet)'
CLR = 0.5       # foam edge to the cavity wall / cut-outs
PLATE_HOLE_CLR = 0.25   # switch hole 14 -> 14.5 in the foam
R = 1.0         # round the foam's corners (cutter-friendly, no slivers)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'production', 'case_foam')

def foam(cavity, cuts, clr=CLR):
    f = cavity.buffer(-clr, join_style=2).difference(unary_union(cuts).buffer(CLR, join_style=2))
    f = f.buffer(-R).buffer(2 * R).buffer(-R)          # open then close: drop strips < 2R, round corners
    return max(getattr(f, 'geoms', [f]), key=lambda g: g.area)

MX_SOCKET = [(-7.085, -2.54, 2.55, 2.5), (5.842, -5.08, 2.55, 2.5), (-3.15, -3.85, 5.5, 5.5), (2.0, -4.8, 4.8, 3.6)]   # pads + the body's two lobes (footprint B.SilkS), KiCad local (x, y, w, h)
def underside(path):
    """plan of what hangs under the PCB (Fusion coords): per switch the MX socket (body lobes + pads; the Choc pads are bare copper
    on MX builds), per B.Cu footprint the hull of its SMD pads"""
    out = []
    for m in re.finditer(r'\n\t\(footprint "([^"]*)"\n\t\t\(layer "([^"]+)"\)(.*?)\n\t\)', open(path).read(), re.S):
        name, layer, body = m.groups()
        a = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', body)
        x, y, rot = float(a.group(1)), float(a.group(2)), math.radians(float(a.group(3) or 0))
        if 'Hotswap' in name: rects = MX_SOCKET
        elif layer == 'B.Cu':
            rects = [tuple(map(float, q.group(1).split()[:2] + q.group(2).split())) for q in
                     re.finditer(r'\(pad "[^"]*" smd \w+\s*\(at ([-\d. ]+)\)\s*\(size ([-\d. ]+)\)', body)]
        else: continue
        if not rects: continue
        hull = 'Hotswap' not in name
        parts = []
        for px, py, w, h in rects:
            pts = []
            for dx in (-w / 2, w / 2):
                for dy in (-h / 2, h / 2):
                    u, v = px + dx, py + dy        # KiCad: y down, rotation CCW on screen
                    gx, gy = x + u * math.cos(rot) + v * math.sin(rot), y - u * math.sin(rot) + v * math.cos(rot)
                    pts.append((gx, -gy))
            parts.append(MultiPoint(pts))
        out.append(unary_union(parts).convex_hull if hull else unary_union([q.convex_hull for q in parts]))
    return out

def lines(poly):
    return [('line', p, q) for ring in [poly.exterior, *poly.interiors] for p, q in zip(ring.coords, ring.coords[1:])]

if __name__ == '__main__':
    G = build_right(); L = G['L']
    mcu = box(*MCU_RING)
    mcu_r = box(C2 - MCU_RING[2], MCU_RING[1], C2 - MCU_RING[0], MCU_RING[3])
    foams = {'left': foam(L['cavity'], [L['bat'], mcu] + underside(B + 'mx/left/mx.kicad_pcb')),
             'right': foam(G['cavity'], [G['bat'], mcu_r, G['pocket'], G['sensor_slot'], box(160, -140, 175, -105.5)] + underside(B + 'mx/right/mx_right.kicad_pcb'))}   # last: the J1 tongue (make_right) where the sensor board stands
    tongue = box(160, -140, 175, -105.5)
    for side, g, cuts in (('left', L, [mcu]), ('right', G, [mcu_r, tongue])):
        holes = [h.buffer(PLATE_HOLE_CLR, join_style=2) for h in plate_outline(side)[1][1:]]
        f = g['body'].intersection(g['pcb']).buffer(-R).buffer(R).difference(unary_union(holes + [c.buffer(CLR) for c in cuts]))
        foams[side + '_plate'] = max(getattr(f, 'geoms', [f]), key=lambda q: q.area)
    os.makedirs(OUT, exist_ok=True)
    for side, f in foams.items():
        path = os.path.join(OUT, 'sage60_%s_foam.dxf' % side)
        open(path, 'w').write(dxf(lines(f.simplify(0.02))))
        x0, y0, x1, y1 = f.bounds
        print(os.path.relpath(path), '%.1f x %.1f mm, area %.0f mm2, holes %d' % (x1 - x0, y1 - y0, f.area, len(f.interiors)))

    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 2, figsize=(18, 14))
    for ax, (side, f), g in zip(axs.flat, foams.items(), (L, G, L, G)):
        for poly, c, lw in ((g['case'], 'k', 0.6), (g['cavity'], 'gray', 0.6), (g['pcb'], 'g', 0.8), (f, 'm', 1.5)):
            for gg in getattr(poly, 'geoms', [poly]):
                ax.plot(*gg.exterior.xy, c, lw=lw)
        ax.fill(*f.exterior.xy, 'm', alpha=0.25)
        for h in f.interiors: ax.fill(*h.xy, 'w', ec='m', lw=0.8); ax.set_aspect('equal'); ax.set_title('%s foam (magenta), PCB green, cavity gray' % side)
    fig.savefig(os.path.join(OUT, 'foam_preview.png'), dpi=110, bbox_inches='tight')
