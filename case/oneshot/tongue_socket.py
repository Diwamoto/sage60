"""one-shot (2026-10-27): the L conthrough (sold out, user threw theirs away) is replaced by an Akizuki 1-row right-angle pin
header (PH-1x40RG, horizontal pins 1.25 above the PCB) soldered into J1, and a pin socket (FH-1x7SG/RH, 8.5 long) on the
sensor board's +x face, plugged in sideways (user decision, plan A).  The sensor board stays centred in the trackball case's
slot (x 156.94..159.34, board +x face 158.94), so J1 moves to x 158.94 + 8.5 (socket) + 2.54 (header housing) + 1.5 (bend to
lead) = 171.48.  The tongue grows to x 174 (bottom edge, R1 convex corner, R1 concave corner where it meets the diagonal edge).
J1's six nets are rerouted from the rows where they enter the tongue:
  B.Cu  SCLK (pad 1) down, 45 deg, into pad 1 from the left; 3.3V (pad 4, 0.5) down the right of the pads (x 173);
        CS leaves B.Cu through a via right after the main board edge
  F.Cu  CS (pad 2), SDIO (pad 6), MOTION (pad 7) nested verticals into their pads from the left (MOTION's B.Cu via goes)
Coordinates are KiCad (y down).  Items are matched by their coordinates, so running it again fails (asserts).
Then: kicad-cli pcb drc --refill-zones --save-board."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))   # case/ (casegeo, geo, ...)
import re, uuid, math
import numpy as np
from geo import B

PCB = B + 'mx/right_tb/mx_right_tb.kicad_pcb'
J0, J = (160.995, 122.395), (171.48, 122.395)
XR, R = 174.0, 1.0                                  # new right edge of the tongue, corner radius
BOT, DIAG_TOP = 132.315, (180.06647, 104.779824)
PAD = lambda n: (J[0], J[1] + (n - 4) * 2.54)       # pad 1 at the top (y 114.775)
VIA_CS = (164.71835, 107.5)                         # 45 deg from (162.495, 105.27665)

def f(v): return ('%.6f' % v).rstrip('0').rstrip('.')

def seg(a, b, layer, net, w=0.25):
    return ('\t(segment\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(width %s)\n\t\t(layer "%s")\n\t\t(net "%s")\n\t\t(uuid "%s")\n\t)\n'
            % (f(a[0]), f(a[1]), f(b[0]), f(b[1]), f(w), layer, net, uuid.uuid4()))

def path(pts, layer, net, w=0.25):
    return ''.join(seg(a, b, layer, net, w) for a, b in zip(pts, pts[1:]))

def via(p, net):
    return ('\t(via\n\t\t(at %s %s)\n\t\t(size 0.8)\n\t\t(drill 0.4)\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "%s")\n\t\t(uuid "%s")\n\t)\n'
            % (f(p[0]), f(p[1]), net, uuid.uuid4()))

EDGE = '\t\t(stroke\n\t\t\t(width 0.1)\n\t\t\t(type default)\n\t\t)\n\t\t(layer "Edge.Cuts")\n\t\t(uuid "%s")\n\t)\n'
def eline(a, b): return '\t(gr_line\n\t\t(start %s %s)\n\t\t(end %s %s)\n' % (f(a[0]), f(a[1]), f(b[0]), f(b[1])) + EDGE % uuid.uuid4()
def earc(a, m, b): return ('\t(gr_arc\n\t\t(start %s %s)\n\t\t(mid %s %s)\n\t\t(end %s %s)\n' % tuple(map(f, a + m + b))) + EDGE % uuid.uuid4()

def items(s, tag):
    """top-level (tag ...) blocks -> [(start, end, text)]"""
    out = []
    for m in re.finditer(r'\n\t\(%s\b' % tag, s):
        i = m.start() + 1; d = 0; k = i
        while True:
            if s[k] == '(': d += 1
            elif s[k] == ')':
                d -= 1
                if d == 0: break
            k += 1
        out.append((i, k + 2, s[i:k + 2]))        # + ')\n'
    return out

def ends(t):
    p = [tuple(map(float, q)) for q in re.findall(r'\((?:start|end|at) ([-\d.]+) ([-\d.]+)', t)]
    return p

def near(p, q, e=1e-3): return math.dist(p, q) < e

def concave_fillet(P, u1, u2, r):
    """R r arc in the corner P between the edges leaving P along u1 and u2 (the board is outside that wedge)"""
    u1, u2 = np.array(u1) / np.linalg.norm(u1), np.array(u2) / np.linalg.norm(u2)
    th = math.acos(np.clip(np.dot(u1, u2), -1, 1)) / 2
    b = (u1 + u2) / np.linalg.norm(u1 + u2)
    C = np.array(P) + b * r / math.sin(th)
    t = r / math.tan(th)
    return tuple(np.array(P) + u1 * t), tuple(C - b * r), tuple(np.array(P) + u2 * t)

def main():
    s = open(PCB).read()
    drop = []
    # tracks / via of J1's nets inside the tongue (rows on the main board side stay)
    old = [((160.995, 114.775), (160.995, 105.775)),                                     # SCLK
           ((162.495, 105.27665), (162.495, 115.815)), ((162.495, 115.815), (160.995, 117.315)),   # CS
           ((160.995, 122.395), (170.495, 112.895)), ((170.495, 112.895), (170.495, 101.775)),     # 3.3V
           ((163.3, 104.791493), (163.3, 125.17)), ((163.3, 125.17), (160.995, 127.475)),          # SDIO
           ((162.45, 104.841493), (162.45, 124.0)), ((162.45, 124.0), (162.45, 128.56)),           # MOTION
           ((162.45, 128.56), (160.995, 130.015))]
    for a, b in old:
        hit = [it for it in items(s, 'segment') if (lambda p: (near(p[0], a) and near(p[1], b)) or (near(p[0], b) and near(p[1], a)))(ends(it[2]))]
        assert len(hit) == 1, (a, b, len(hit)); drop.append(hit[0])
    hit = [it for it in items(s, 'via') if near(ends(it[2])[0], (162.45, 124.0))]
    assert len(hit) == 1; drop.append(hit[0])
    # Edge.Cuts: the bottom edge and the diagonal edge of the tongue
    for a, b in (((165.931632, BOT), (160.9, BOT)), (DIAG_TOP, (165.931632, BOT))):
        hit = [it for it in items(s, 'gr_line') if 'Edge.Cuts' in it[2] and near(ends(it[2])[0], a) and near(ends(it[2])[1], b)]
        assert len(hit) == 1, (a, b); drop.append(hit[0])
    for i, k, _ in sorted(drop, reverse=True): s = s[:i] + s[k:]
    # J1
    assert s.count('(at %s %s)' % J0) == 1
    s = s.replace('(at %s %s)' % J0, '(at %s %s)' % (f(J[0]), f(J[1])))
    # new outline: bottom edge to XR - R, R corner, up x = XR, R concave corner into the diagonal
    d = np.array(DIAG_TOP) - np.array((165.931632, BOT))
    yd = BOT + (XR - 165.931632) / d[0] * d[1]                              # x = XR meets the diagonal
    T1, M, T2 = concave_fillet((XR, yd), (0, 1), d, R)
    new = (eline((XR - R, BOT), (160.9, BOT)) + earc((XR - R, BOT), (XR - R + R / math.sqrt(2), BOT - R + R / math.sqrt(2)), (XR, BOT - R))
           + eline((XR, BOT - R), T1) + earc(T1, M, T2) + eline(DIAG_TOP, T2))
    sclk_knee = (PAD(1)[0] - 4.01, PAD(1)[1]); sclk_top = (160.995, PAD(1)[1] - (sclk_knee[0] - 160.995))    # 45 deg, (160.995, 108.3)
    new += path([(160.995, 105.775), sclk_top, sclk_knee, PAD(1)], 'B.Cu', 'SCLK')
    new += path([(162.495, 105.27665), VIA_CS], 'B.Cu', 'CS') + via(VIA_CS, 'CS')
    new += path([VIA_CS, (VIA_CS[0], PAD(2)[1]), PAD(2)], 'F.Cu', 'CS')
    new += path([(170.495, 101.775), (170.495, 105.3), (173.0, 107.805), (173.0, PAD(4)[1]), PAD(4)], 'B.Cu', '3.3V', 0.5)
    new += path([(163.3, 104.791493), (163.3, PAD(6)[1]), PAD(6)], 'F.Cu', 'SDIO')
    new += path([(162.45, 104.841493), (162.45, PAD(7)[1]), PAD(7)], 'F.Cu', 'MOTION')
    k = s.rstrip().rfind(')')
    s = s[:k] + new + s[k:]
    open(PCB, 'w').write(s)
    print('J1 -> (%.3f, %.3f), tongue edge x %.1f (meets the diagonal at y %.3f), %d items replaced' % (J + (XR, yd, len(drop))))

if __name__ == '__main__':
    main()
