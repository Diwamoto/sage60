"""points just inside the PCB and plate outlines, for fusion/check.py"""
import json
from casegeo import outline, B
out = {}
for side, pl, pc in [('left', 'mx_plate/mx_plate.kicad_pcb', 'mx_main/mx.kicad_pcb'),
                     ('right', 'mx_right_tb_plate/mx_right_tb_plate.kicad_pcb', 'mx_right_tb/mx_right_tb.kicad_pcb')]:
    plate, _ = outline(B + pl); pcb, _ = outline(B + pc)
    out[side] = {'pcb': list(pcb.buffer(-0.05).exterior.segmentize(0.5).coords),
                 'plate': list(plate.buffer(-0.05).exterior.segmentize(0.5).coords)}
json.dump(out, open('checkpts.json', 'w'))
