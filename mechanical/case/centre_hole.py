"""one-shot (applied 2026-10-04): widen the switch centre hole of CherryMX_Choc_Hotswap_v2 from phi 4.1 to phi D on both PCBs,
so the Kailh Choc v2 centre post (phi 5) fits; the MX post (phi 4) still goes in, with play (the plate holes and the socket locate it).
Board copies only (the 0_kbd library is not in this repo). Running it again finds nothing to change (asserts)."""
import re
from geo import B

D = 5.0
PCBS = ['mx_main/mx.kicad_pcb', 'mx_right_tb/mx_right_tb.kicad_pcb']
PAD = re.compile(r'(\(pad "" np_thru_hole circle\s*\(at 0 0(?: [-\d.]+)?\)\s*\(size )4\.1 4\.1(\)\s*\(drill )4\.1\)')

def main():
    for f in PCBS:
        s = open(B + f).read()
        s, n = PAD.subn(r'\g<1>%g %g\g<2>%g)' % (D, D, D), s)
        assert n == s.count('CherryMX_Choc_Hotswap_v2"'), (f, n)
        open(B + f, 'w').write(s)
        print('%s: %d centre holes -> phi %g' % (f, n, D))

if __name__ == '__main__':
    main()
