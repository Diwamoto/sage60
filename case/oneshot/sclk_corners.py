"""one-shot (2026-11-01): right PCB, acute corners and stubs out of the routing, GND stitching vias beside the sensor nets.
  SCLK: the three B.Cu hairpins (45 deg) and the T with a dead end above via (156.795, 96.6416) -> direct, 135 deg corners
  COL4 / Net-(D28-A): the short jog that met another track at a pad centre goes; the track now ends inside the pad
  ROW4: the 0.42 stub doubled over the track at D27 pad 1 goes
  GND: 13 vias within 3 of the sensor nets' layer changes and on the tongue, each inside the F.Cu and the B.Cu pour
Coordinates are KiCad (y down).  Items are matched by their coordinates, so running it again fails (asserts).
Then: kicad-cli pcb drc --refill-zones --save-board."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))   # case/ (casegeo, geo, ...)
from tongue_socket import PCB, items, ends, near, path, via

DROP = [((159.085, 70.275), (157.845, 70.275)), ((158.595, 69.785), (159.085, 70.275)), ((158.595, 69.785), (154.095, 65.275)),      # SCLK
        ((158.295, 88.8416), (159.085, 88.8416)), ((158.795, 88.551624), (159.085, 88.841624)), ((158.795, 80.275), (158.795, 88.551624)),
        ((158.995, 49.775), (159.495, 50.275)), ((158.795, 50.275), (159.495, 50.275)), ((156.995, 52.075), (158.795, 50.275)),
        ((157.995, 94.57665), (157.995, 102.775)), ((157.995, 94.5767), (157.995, 95.4416)), ((157.995, 95.4416), (156.795, 96.6416)),
        ((94.88, 91.5925), (95.57, 92.2825)),                                                                                       # COL4
        ((82.219274, 115.954), (82.7245, 115.954)),                                                                                 # Net-(D28-A)
        ((101.3935, 114.551), (101.3935, 114.968831))]                                                                              # ROW4
SCLK = [[(157.845, 70.275), (157.845, 69.025), (154.095, 65.275)],
        [(158.795, 80.275), (158.795, 88.3416), (158.295, 88.8416)],
        [(158.995, 49.775), (158.995, 50.075), (156.995, 52.075)],
        [(156.795, 96.6416), (157.995, 97.8416), (157.995, 102.775)]]
GND = [(165.1, 118.85), (166.0, 112.05), (139.5, 99.25), (158.85, 98.25), (121.6, 96.1), (158.45, 89.95), (158.0, 71.4),
       (120.15, 54.75), (102.3, 54.65), (106.75, 52.05), (158.1, 52.25), (161.0, 50.15), (142.2, 44.2)]

def main():
    s = open(PCB).read()
    drop = []
    for a, b in DROP:
        hit = [it for it in items(s, 'segment') if (lambda p: (near(p[0], a) and near(p[1], b)) or (near(p[0], b) and near(p[1], a)))(ends(it[2]))]
        assert len(hit) == 1, (a, b, len(hit)); drop.append(hit[0])
    for i, k, _ in sorted(drop, reverse=True): s = s[:i] + s[k:]
    new = ''.join(path(p, 'B.Cu', 'SCLK') for p in SCLK) + ''.join(via(p, 'GND') for p in GND)
    k = s.rstrip().rfind(')')
    s = s[:k] + new + s[k:]
    open(PCB, 'w').write(s)
    print('%d segments removed, %d SCLK paths, %d GND vias' % (len(drop), len(SCLK), len(GND)))

if __name__ == '__main__':
    main()
