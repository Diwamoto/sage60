"""one-shot (applied 2026-10-04): narrow the right PCB's J1 tongue so the trackball case's "[" leg arm (reaches KiCad x 158.54
at y 109.5-110.7, in the PCB's thickness band) clears it. The tongue's left edge x 158.0 -> EDGE_X, and the two F.Cu traces
running down that edge (SDIO x 159.495, MOTION x 159.145) move right by DX, keeping their 0.1 mm gap; J1 stays.
Exact-text replacements, so running it again fails (asserts) instead of moving twice. Refill zones + DRC afterwards."""
from geo import B

PCB = B + 'mx_right_tb/mx_right_tb.kicad_pcb'
EDGE_X, DX = 158.9, 0.32                      # edge to arm 0.36, trace to edge 0.44, trace to J1 pads 0.2 (GND class)
XM = 158.3                                    # MOTION turns down here: its 45 deg run stays 1.4 from the fillet centre (EDGE_X-1, 105.775)
XS = XM + 0.495                               # SDIO's 45 deg run keeps the 0.35 pitch (x - y offset 0.495)

def f(v): return ('%.6f' % v).rstrip('0').rstrip('.')

def main():
    s = open(PCB).read()
    e0, e1 = 157.9965, 158.058367             # current left edge, top and bottom x
    sh = EDGE_X - e0
    subs = [  # Edge.Cuts: top concave arc, left edge, bottom-left corner arc, bottom edge, the horizontal edge left of the tongue
        ('(start 156.9965 104.775)\n\t\t(mid 157.703607 105.067893)\n\t\t(end 157.9965 105.775)',
         '(start %s 104.775)\n\t\t(mid %s 105.067893)\n\t\t(end %s 105.775)' % (f(156.9965 + sh), f(157.703607 + sh), f(EDGE_X))),
        ('(start 157.9965 105.775)\n\t\t(end 158.058367 131.315)', '(start %s 105.775)\n\t\t(end %s 131.315)' % (f(EDGE_X), f(EDGE_X))),
        ('(start 159.058367 132.315)\n\t\t(mid 158.35126 132.022107)\n\t\t(end 158.058367 131.315)',
         '(start %s 132.315)\n\t\t(mid %s 132.022107)\n\t\t(end %s 131.315)' % (f(EDGE_X + 1), f(EDGE_X + 1 - 0.707107), f(EDGE_X))),
        ('(start 165.931632 132.315)\n\t\t(end 159.058367 132.315)', '(start 165.931632 132.315)\n\t\t(end %s 132.315)' % f(EDGE_X + 1)),
        ('(start 156.9965 104.775)\n\t\t(end 152.495 104.775)', '(start %s 104.775)\n\t\t(end 152.495 104.775)' % f(156.9965 + sh)),
        # SDIO: along the main board's edge to XS, 45 deg in (clear of the inner-corner fillet), down the edge, 45 deg into pad 6
        ('(start 155.511493 103.791493)\n\t\t(end 157.511493 103.791493)', '(start 155.511493 103.791493)\n\t\t(end %s 103.791493)' % f(XS)),
        ('(start 157.511493 103.791493)\n\t\t(end 159.495 105.775)', '(start %s 103.791493)\n\t\t(end %s %s)' % (f(XS), f(159.495 + DX), f(103.791493 + 159.495 + DX - XS))),
        ('(start 159.495 105.775)\n\t\t(end 159.495 125.975)', '(start %s %s)\n\t\t(end %s %s)' % (f(159.495 + DX), f(103.791493 + 159.495 + DX - XS), f(159.495 + DX), f(125.975 + DX))),
        ('(start 159.495 125.975)\n\t\t(end 160.995 127.475)', '(start %s %s)\n\t\t(end 160.995 127.475)' % (f(159.495 + DX), f(125.975 + DX))),
        # MOTION: same, into pad 7
        ('(start 155.361493 104.141493)\n\t\t(end 157.366519 104.141493)', '(start 155.361493 104.141493)\n\t\t(end %s 104.141493)' % f(XM)),
        ('(start 157.366519 104.141493)\n\t\t(end 159.145 105.919974)', '(start %s 104.141493)\n\t\t(end %s %s)' % (f(XM), f(159.145 + DX), f(104.141493 + 159.145 + DX - XM))),
        ('(start 159.145 105.919974)\n\t\t(end 159.145 128.165)', '(start %s %s)\n\t\t(end %s %s)' % (f(159.145 + DX), f(104.141493 + 159.145 + DX - XM), f(159.145 + DX), f(128.165 + DX))),
        ('(start 159.145 128.165)\n\t\t(end 160.995 130.015)', '(start %s %s)\n\t\t(end 160.995 130.015)' % (f(159.145 + DX), f(128.165 + DX))),
    ]
    for a, b in subs:
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    open(PCB, 'w').write(s)
    print('tongue edge x %.4f -> %.2f, traces +%.3f' % (e0, EDGE_X, DX))

if __name__ == '__main__':
    main()
