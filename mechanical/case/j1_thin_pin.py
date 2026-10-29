"""one-shot (2026-10-29): J1 for the thin-pin right-angle header (Akizuki PHA-1x40RG: pins 0.5 sq 1.0 above the PCB, housing
2.0 x 2.0, lead 1.5 behind it; user: the thin pins worked in the round-pin socket before), pins cut to 2.5, housing against the
round-pin socket 6604S on the sensor board (face x 163.14).  J1 167.18 -> 166.64.  The sensor board hangs 0.25 lower, so the
socket's 2.54 sq body (pins 1.0 above the PCB -> bottom 0.27 below the PCB top) would sit in the tongue: the tongue's left edge
goes 159.9 -> 163.4 below y 112.8 (R1 corners).  SDIO moves right to x 163.95 (F.Cu), MOTION goes through a via above the cut to
B.Cu x 164.2.  Coordinates are KiCad (y down).  Items are matched by their coordinates, so running it again fails (asserts).
Then: kicad-cli pcb drc --refill-zones --save-board."""
import math
from tongue_socket import PCB, items, ends, near, f, path, via, eline, earc

J0, J = (167.18, 122.395), (166.64, 122.395)
PAD = lambda n: (J[0], J[1] + (n - 4) * 2.54)
XE, YN, R = 163.4, 112.8, 1.0                       # new left edge below YN
LEFT, BOT = 159.9, 132.315
VIA_M = (162.45, 111.3)
H = R / math.sqrt(2)

def main():
    s = open(PCB).read()
    drop = []
    old = [((160.995, 108.3), (167.47, 114.775)), ((167.47, 114.775), (167.18, 114.775)),        # SCLK
           ((164.71835, 117.315), (167.18, 117.315)),                                           # CS
           ((173.0, 122.395), (167.18, 122.395)),                                               # 3.3V
           ((163.3, 104.791493), (163.3, 127.475)), ((163.3, 127.475), (167.18, 127.475)),       # SDIO
           ((162.45, 104.841493), (162.45, 130.015)), ((162.45, 130.015), (167.18, 130.015))]    # MOTION
    for a, b in old:
        hit = [it for it in items(s, 'segment') if (lambda p: (near(p[0], a) and near(p[1], b)) or (near(p[0], b) and near(p[1], a)))(ends(it[2]))]
        assert len(hit) == 1, (a, b, len(hit)); drop.append(hit[0])
    for tag, a, b in (('gr_line', (LEFT, 105.775), (LEFT, BOT - R)), ('gr_arc', (LEFT + R, BOT), (LEFT, BOT - R)),
                      ('gr_line', (173.0, BOT), (LEFT + R, BOT))):
        hit = [it for it in items(s, tag) if 'Edge.Cuts' in it[2] and near(ends(it[2])[0], a) and near(ends(it[2])[-1], b)]
        assert len(hit) == 1, (tag, a, b); drop.append(hit[0])
    for i, k, _ in sorted(drop, reverse=True): s = s[:i] + s[k:]
    assert s.count('(at %s %s)' % tuple(map(f, J0))) == 1
    s = s.replace('(at %s %s)' % tuple(map(f, J0)), '(at %s %s)' % tuple(map(f, J)))
    # outline: down x = LEFT, R round into y = YN, R concave into x = XE, down, R round into the bottom edge
    new = (eline((LEFT, 105.775), (LEFT, YN - R)) + earc((LEFT, YN - R), (LEFT + R - H, YN - R + H), (LEFT + R, YN))
           + eline((LEFT + R, YN), (XE - R, YN)) + earc((XE - R, YN), (XE - R + H, YN + R - H), (XE, YN + R))
           + eline((XE, YN + R), (XE, BOT - R)) + earc((XE, BOT - R), (XE + R - H, BOT - R + H), (XE + R, BOT))
           + eline((173.0, BOT), (XE + R, BOT)))
    knee =(J[0], 108.3 + (J[0] - 160.995))                                                        # 45 deg from (160.995, 108.3)
    new += path([(160.995, 108.3), knee, PAD(1)], 'B.Cu', 'SCLK')
    new += path([(164.71835, 117.315), PAD(2)], 'F.Cu', 'CS')
    new += path([(173.0, 122.395), PAD(4)], 'B.Cu', '3.3V', 0.5)
    new += path([(163.3, 104.791493), (163.3, 111.5), (163.95, 112.15), (163.95, PAD(6)[1]), PAD(6)], 'F.Cu', 'SDIO')
    new += path([(162.45, 104.841493), VIA_M], 'F.Cu', 'MOTION') + via(VIA_M, 'MOTION')
    new += path([VIA_M, (164.2, VIA_M[1] + 164.2 - VIA_M[0]), (164.2, PAD(7)[1]), PAD(7)], 'B.Cu', 'MOTION')
    k = s.rstrip().rfind(')')
    s = s[:k] + new + s[k:]
    open(PCB, 'w').write(s)
    print('J1 -> (%.3f, %.3f), tongue left edge x %.1f below y %.1f, %d items replaced' % (J + (XE, YN, len(drop))))

if __name__ == '__main__':
    main()
