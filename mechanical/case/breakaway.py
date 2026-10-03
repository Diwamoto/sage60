"""one-shot (applied 2026-10-03): make the left plate the shared plate for both halves.
The right plate = the left plate flipped, minus the part around the trackball (2 thumb keys) and the front gasket tab.
Those parts get cut lines that can be snipped with nippers: slots (SLOT_W, on the scrap side so the kept edge is exactly the
right plate's edge) with BRIDGE_W bridges, and mouse-bite holes at the root of the tab (the left half keeps and uses that tab).
Writes Edge.Cuts gr_poly / gr_circle into mx_plate.kicad_pcb. Running it again adds the cuts twice."""
import uuid
from geo import outline
from shapely.ops import linemerge
from casegeo import *

SLOT_W, BRIDGE_W, BRIDGE_PITCH, END_BRIDGE = 1.2, 2.0, 14.0, 1.8
BITE_D, BITE_PITCH = 0.8, 1.5
PLATE = B + 'mx_plate/mx_plate.kicad_pcb'
M = lambda g: affinity.scale(g, -1, 1, origin=(C2 / 2, 0))

def cuts():
    Lo, polys = outline(PLATE); Ro, _ = outline(B + 'mx_right_tb_plate/mx_right_tb_plate.kicad_pcb')
    holes = unary_union([p for p in polys if p.area < 1000])          # switch cutouts
    extra = Lo.difference(M(Ro)).buffer(-0.3).buffer(0.3)                   # drop the < 0.6 mm slivers (left/right drawing noise)
    pieces = sorted([g for g in getattr(extra, 'geoms', [extra]) if g.area > 10], key=lambda g: -g.area)
    slots, bites = [], []
    for k, g in enumerate(pieces):
        g = Lo.intersection(g.buffer(0.3))                                   # back to the exact edge
        cut = g.boundary.difference(Lo.exterior.buffer(0.05))
        cut = linemerge(cut) if cut.geom_type == 'MultiLineString' else cut
        cut = max(getattr(cut, 'geoms', [cut]), key=lambda c: c.length)
        if k == 0:                                                           # trackball part: slots + bridges
            strip = g.intersection(cut.buffer(SLOT_W, cap_style=2)).difference(Lo.exterior.buffer(END_BRIDGE))
            n = max(1, round(cut.length / BRIDGE_PITCH))
            from shapely.ops import substring
            br = unary_union([substring(cut, cut.length * (i + 0.5) / n - BRIDGE_W / 2, cut.length * (i + 0.5) / n + BRIDGE_W / 2).buffer(SLOT_W + 0.2, cap_style=2) for i in range(n)])
            strip = strip.difference(br).difference(holes.buffer(0.6))
            slots += [p for p in getattr(strip, 'geoms', [strip]) if p.area > 0.5]
        else:                                                                # gasket tab: mouse bites along the root
            n = int((cut.length - 2 * END_BRIDGE) / BITE_PITCH)
            off = cut.parallel_offset(BITE_D / 2, 'left'); off = off if g.contains(off.interpolate(0.5, normalized=True)) else cut.parallel_offset(BITE_D / 2, 'right')
            s0 = (off.length - (n - 1) * BITE_PITCH) / 2
            bites += [off.interpolate(s0 + i * BITE_PITCH) for i in range(n)]
    return Lo, pieces, slots, bites

def write(slots, bites):
    s = open(PLATE).read(); add = ''
    for p in slots:
        p = p.simplify(0.01)
        pts = ' '.join('(xy %.4f %.4f)' % (x, -y) for x, y in list(p.exterior.coords)[:-1])
        add += '\n\t(gr_poly\n\t\t(pts %s)\n\t\t(stroke\n\t\t\t(width 0.05)\n\t\t\t(type default)\n\t\t)\n\t\t(fill no)\n\t\t(layer "Edge.Cuts")\n\t\t(uuid "%s")\n\t)' % (pts, uuid.uuid4())
    for c in bites:
        add += '\n\t(gr_circle\n\t\t(center %.4f %.4f)\n\t\t(end %.4f %.4f)\n\t\t(stroke\n\t\t\t(width 0.05)\n\t\t\t(type default)\n\t\t)\n\t\t(fill no)\n\t\t(layer "Edge.Cuts")\n\t\t(uuid "%s")\n\t)' % (c.x, -c.y, c.x + BITE_D / 2, -c.y, uuid.uuid4())
    i = s.rindex('\n)'); open(PLATE, 'w').write(s[:i] + add + s[i:])

if __name__ == '__main__':
    import sys
    Lo, pieces, slots, bites = cuts()
    print('pieces', [round(p.area, 1) for p in pieces], 'slots', len(slots), [round(p.area, 1) for p in slots], 'bites', len(bites))
    if 'write' in sys.argv: write(slots, bites)
