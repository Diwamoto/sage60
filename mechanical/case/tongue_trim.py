"""one-shot (2026-10-06): the trackball sensor board touched the right PCB's J1 tongue, ~1 mm clearance needed (user).  The
tongue's left edge (trackball side) x 158.9 -> 159.9; J1 and the trackball stay.  J1's pads (1.7) are then 0.245 from the edge,
so SDIO / MOTION, which ran down that edge, go down the right of J1: SDIO on F.Cu outside, MOTION inside it and through a via
to B.Cu for the last stretch into pad 7 (on one layer they would cross).  Exact-text replacements, so running it again fails
(asserts) instead of trimming twice.  The F.Cu GND pour reached B.Cu only through J1 pad 3, which the new runs fence in, so two
GND stitching vias join the pours where both are filled (else the F.Cu pour is dropped as an island).
Then: kicad-cli pcb drc --refill-zones --save-board."""
from geo import B

PCB = B + 'mx_right_tb/mx_right_tb.kicad_pcb'
X_M, X_S, VIA_Y = 162.45, 163.3, 124.0       # MOTION / SDIO verticals right of J1 (pads to x 161.845), MOTION's via
GND_VIAS = [(166.43, 109.75), (89.0, 37.33)]  # inside both pours (0.6 in from the fill edges)
P6, P7 = (160.995, 127.475), (160.995, 130.015)
YS, YM = 103.791493, 104.141493              # their rows along the main board's edge

def f(v): return ('%.6f' % v).rstrip('0').rstrip('.')

def via(p, net):
    return '\t(via\n\t\t(at %s %s)\n\t\t(size 0.8)\n\t\t(drill 0.4)\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "%s")\n\t)\n' % (f(p[0]), f(p[1]), net)

def seg(a, b, layer, net, w=0.25):
    return ('\t(segment\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(width %s)\n\t\t(layer "%s")\n\t\t(net "%s")\n\t)\n'
            % (f(a[0]), f(a[1]), f(b[0]), f(b[1]), f(w), layer, net))

def main():
    s = open(PCB).read()
    subs = [  # Edge.Cuts: the edge left of the tongue, its concave arc, the left edge, the bottom-left arc, the bottom edge
        ('(start 157.9 104.775)\n\t\t(end 152.495 104.775)', '(start 158.9 104.775)\n\t\t(end 152.495 104.775)'),
        ('(start 157.9 104.775)\n\t\t(mid 158.607107 105.067893)\n\t\t(end 158.9 105.775)',
         '(start 158.9 104.775)\n\t\t(mid 159.607107 105.067893)\n\t\t(end 159.9 105.775)'),
        ('(start 158.9 105.775)\n\t\t(end 158.9 131.315)', '(start 159.9 105.775)\n\t\t(end 159.9 131.315)'),
        ('(start 159.9 132.315)\n\t\t(mid 159.192893 132.022107)\n\t\t(end 158.9 131.315)',
         '(start 160.9 132.315)\n\t\t(mid 160.192893 132.022107)\n\t\t(end 159.9 131.315)'),
        ('(start 165.931632 132.315)\n\t\t(end 159.9 132.315)', '(start 165.931632 132.315)\n\t\t(end 160.9 132.315)'),
    ]
    for a, b in subs:
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    # drop the old runs down the left edge (whole segment blocks, uuid included)
    old = ['(start 158.795 103.791493)\n\t\t(end 159.815 104.811493)', '(start 159.815 104.811493)\n\t\t(end 159.815 126.295)',
           '(start 159.815 126.295)\n\t\t(end 160.995 127.475)', '(start 158.3 104.141493)\n\t\t(end 159.465 105.306493)',
           '(start 159.465 105.306493)\n\t\t(end 159.465 128.485)', '(start 159.465 128.485)\n\t\t(end 160.995 130.015)']
    for o in old:
        assert s.count(o) == 1, o
        i = s.rindex('\t(segment\n', 0, s.index(o)); j = s.index('\n\t)\n', i) + 4
        s = s[:i] + s[j:]
    # new runs right of J1
    d = P6[0] + P6[1]                         # SDIO's last 45 deg run into pad 6: x + y = const
    new = (seg((158.795, YS), (X_S - 1.0, YS), 'F.Cu', 'SDIO') + seg((X_S - 1.0, YS), (X_S, YS + 1.0), 'F.Cu', 'SDIO')
           + seg((X_S, YS + 1.0), (X_S, d - X_S), 'F.Cu', 'SDIO') + seg((X_S, d - X_S), P6, 'F.Cu', 'SDIO')
           + seg((158.3, YM), (X_M - 0.7, YM), 'F.Cu', 'MOTION') + seg((X_M - 0.7, YM), (X_M, YM + 0.7), 'F.Cu', 'MOTION')
           + seg((X_M, YM + 0.7), (X_M, VIA_Y), 'F.Cu', 'MOTION')
           + via((X_M, VIA_Y), 'MOTION') + ''.join(via(p, 'GND') for p in GND_VIAS)
           + seg((X_M, VIA_Y), (X_M, P7[1] - (X_M - P7[0])), 'B.Cu', 'MOTION') + seg((X_M, P7[1] - (X_M - P7[0])), P7, 'B.Cu', 'MOTION'))
    k = s.index('\t(segment\n')
    s = s[:k] + new + s[k:]
    open(PCB, 'w').write(s)
    print('tongue left edge 158.9 -> 159.9; SDIO / MOTION rerouted right of J1')

if __name__ == '__main__':
    main()
