"""one-shot (2026-11-01): the right PCB's J1 tongue as one symmetric shape on J1's pin axis (x 166.64): parallel sides 3.24 either side (the
left one stays where the socket needs it), a full round tip, the same root fillet on both sides.  golden ratio: length / width
= phi^3, half width / root R = phi.  The new outline is inside the old one.  SDIO / MOTION go down the left on F.Cu, SCLK left
and CS / 3.3V right on B.Cu: no signal via left on the tongue.  Coordinates are KiCad (y down).  Items are matched by their
coordinates, so running it again fails (asserts).  Then: kicad-cli pcb drc --refill-zones --save-board."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))   # case/ (casegeo, geo, ...)
import math
from tongue_socket import PCB, items, ends, near, path, via, eline, earc

PHI = (1 + math.sqrt(5)) / 2
AX, HW, Y = 166.64, 3.24, 104.775                   # J1's pin axis, half width (left edge 163.4), the main board's front edge
RR, BOT = HW / PHI, Y + 2 * HW * PHI ** 3           # root fillet, tip
XL, XR, YC = AX - HW, AX + HW, BOT - HW             # sides, centre of the tip
H = RR / math.sqrt(2)
PAD = lambda n: (AX, 122.395 + (n - 4) * 2.54)
XM, XS, XSC, XCS, XV = 164.0, 164.35, 165.08, 168.2, 169.0   # MOTION, SDIO (F.Cu), SCLK, CS, 3.3V (B.Cu) verticals
YSC, YCS = 104.3, 103.95                            # SCLK / CS rows along the main board's edge (B.Cu)
YS, YM = 103.791493, 104.141493                     # SDIO / MOTION rows (F.Cu, unchanged)
K = lambda x, p: (x, p[1] - abs(p[0] - x))          # where a vertical at x turns 45 deg into pad p
GND_VIAS = [(AX, 107.0), (AX, 109.5), (AX, 112.0)]

DROP_SEG = [((162.3, YS), (163.3, 104.791493)), ((163.3, 104.791493), (163.3, 111.5)), ((163.3, 111.5), (163.95, 112.15)),   # SDIO
            ((163.95, 112.15), (163.95, 124.785)), ((163.95, 124.785), PAD(6)),
            ((161.75, YM), (162.45, 104.841493)), ((162.45, 104.841493), (162.45, 111.3)),                                 # MOTION
            ((162.45, 111.3), (164.2, 113.05)), ((164.2, 113.05), (164.2, 127.575)), ((164.2, 127.575), PAD(7)),
            ((157.995, 102.775), (160.995, 105.775)), ((160.995, 105.775), (160.995, 108.3)),                              # SCLK
            ((160.995, 108.3), (AX, 113.945)), ((AX, 113.945), PAD(1)),
            ((159.145, 101.92665), (162.495, 105.27665)), ((162.495, 105.27665), (164.71835, 107.5)),                      # CS
            ((164.71835, 107.5), (164.71835, 115.39335)), ((164.71835, 115.39335), PAD(2)),
            ((170.495, 101.775), (170.495, 118.54)), ((170.495, 118.54), PAD(4))]                                          # 3.3V
DROP_VIA = [(162.45, 111.3), (164.71835, 107.5), (166.43, 109.75), (166.0, 112.05), (165.1, 118.85)]
DROP_EDGE = [('gr_line', (158.9, Y), (152.495, Y)), ('gr_arc', (158.9, Y), (159.9, 105.775)), ('gr_line', (159.9, 105.775), (159.9, 111.8)),
             ('gr_arc', (160.9, 112.8), (159.9, 111.8)), ('gr_line', (160.9, 112.8), (162.4, 112.8)), ('gr_arc', (162.4, 112.8), (163.4, 113.8)),
             ('gr_line', (163.4, 113.8), (163.4, 131.315)), ('gr_arc', (164.4, 132.315), (163.4, 131.315)), ('gr_line', (173.0, 132.315), (164.4, 132.315)),
             ('gr_arc', (174.0, 131.315), (173.0, 132.315)), ('gr_line', (174.0, 131.315), (174.0, 116.839204)),
             ('gr_arc', (174.0, 116.839204), (174.110369, 116.382524)), ('gr_line', (180.06647, 104.779824), (174.110369, 116.382524)),
             ('gr_line', (180.06647, 104.779824), (188.595, Y))]

def main():
    s = open(PCB).read()
    drop = []
    segs, vias = items(s, 'segment'), items(s, 'via')
    for a, b in DROP_SEG:
        hit = [it for it in segs if (lambda p: (near(p[0], a) and near(p[1], b)) or (near(p[0], b) and near(p[1], a)))(ends(it[2]))]
        assert len(hit) == 1, (a, b, len(hit)); drop.append(hit[0])
    for p in DROP_VIA:
        hit = [it for it in vias if near(ends(it[2])[0], p)]
        assert len(hit) == 1, p; drop.append(hit[0])
    for tag, a, b in DROP_EDGE:
        hit = [it for it in items(s, tag) if 'Edge.Cuts' in it[2] and near(ends(it[2])[0], a) and near(ends(it[2])[-1], b)]
        assert len(hit) == 1, (tag, a, b); drop.append(hit[0])
    for i, k, _ in sorted(drop, reverse=True): s = s[:i] + s[k:]
    new = (eline((XL - RR, Y), (152.495, Y)) + earc((XL - RR, Y), (XL - RR + H, Y + RR - H), (XL, Y + RR)) + eline((XL, Y + RR), (XL, YC))
           + earc((XL, YC), (AX, BOT), (XR, YC)) + eline((XR, YC), (XR, Y + RR))
           + earc((XR, Y + RR), (XR + RR - H, Y + RR - H), (XR + RR, Y)) + eline((XR + RR, Y), (188.595, Y)))
    new += path([(162.3, YS), (XS - 0.905, YS), (XS, YS + 0.905), K(XS, PAD(6)), PAD(6)], 'F.Cu', 'SDIO')
    new += path([(161.75, YM), (XM - 0.7, YM), (XM, YM + 0.7), K(XM, PAD(7)), PAD(7)], 'F.Cu', 'MOTION')
    new += path([(157.995, 102.775), (157.995 + YSC - 102.775, YSC), (XSC - 0.48, YSC), (XSC, YSC + 0.48), K(XSC, PAD(1)), PAD(1)], 'B.Cu', 'SCLK')
    new += path([(159.145, 101.92665), (159.145 + YCS - 101.92665, YCS), (XCS - 0.6, YCS), (XCS, YCS + 0.6), K(XCS, PAD(2)), PAD(2)], 'B.Cu', 'CS')
    new += path([(170.495, 101.775), (170.495, 103.9), (XV, 103.9 + 170.495 - XV), K(XV, PAD(4)), PAD(4)], 'B.Cu', '3.3V', 0.5)
    new += ''.join(via(p, 'GND') for p in GND_VIAS)
    k = s.rstrip().rfind(')')
    s = s[:k] + new + s[k:]
    open(PCB, 'w').write(s)
    print('tongue x %.2f..%.2f, tip y %.3f, root R %.3f, L/W %.3f, %d items replaced' % (XL, XR, BOT, RR, (BOT - Y) / (2 * HW), len(drop)))

if __name__ == '__main__':
    main()
