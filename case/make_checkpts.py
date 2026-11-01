"""points just inside the PCB and plate outlines, for fusion/check.py"""
import json
from casegeo import outline, plate_outline, B
out = {}
for side, pc in [('left', 'mx/left/mx.kicad_pcb'),
                     ('right', 'mx/right/mx_right.kicad_pcb')]:
    plate, _ = plate_outline(side); pcb, _ = outline(B + pc)
    out[side] = {'pcb': list(pcb.buffer(-0.05).exterior.segmentize(0.5).coords),
                 'plate': list(plate.buffer(-0.05).exterior.segmentize(0.5).coords)}
json.dump(out, open('checkpts.json', 'w'))
