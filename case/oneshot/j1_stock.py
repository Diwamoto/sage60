"""one-shot (2026-11-01): right PCB's J1 -> KiCad's stock PinHeader_1x07 footprint and Conn_01x07 symbol, replacing roBa's (GPL-3.0),
so the repository can be MIT.  Pads (absolute positions, size, drill, nets) and the schematic's wire ends stay where they are; the pin
order is the sensor board's (1 SCLK, 2 CS, 3 GND, 4 3.3V, 5 NC, 6 SDIO, 7 MOTION).  No 3D model: J1 is an L header, see fusion/stage6.py.
Refuses to run while KiCad has the project open.  Running it again finds nothing to change (asserts).
Usage: j1_stock.py [dir holding mx_right.kicad_*]"""
import sys, os, re, uuid; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))   # case/ (casegeo, geo, ...)

K = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/'
OLD_FP, NEW_FP = '0_sora:pmw3610_connector', 'Connector_PinHeader_2.54mm:PinHeader_1x07_P2.54mm_Vertical'
OLD_SYM, NEW_SYM = 'my:pmw3610_breakout', 'Connector_Generic:Conn_01x07'
DY = 7.62       # stock origin is pin 1, the old one pin 4


def sexp_end(t, i):
    """index just past the s-expression opening at t[i]"""
    d, s = 0, False
    while True:
        c = t[i]
        if c == '"' and t[i - 1] != '\\': s = not s
        elif not s:
            d += (c == '(') - (c == ')')
            if d == 0: return i + 1
        i += 1


def blocks(t, start):
    """top-level children of the s-expression t[start:] named fp_line / fp_text"""
    out, i = [], t.index('(', start + 1)
    while True:
        m = re.compile(r'\(fp_(?:line|text)\b').search(t, i)
        if not m: return out
        e = sexp_end(t, m.start()); out.append(t[m.start():e]); i = e


def footprint(t):
    i = t.index('(footprint "%s"' % OLD_FP); e = sexp_end(t, i); b = t[i:e]
    m = re.search(r'\(at 166\.64 ([\d.]+)\)', b); assert m, 'J1 moved'
    b = b.replace('"%s"' % OLD_FP, '"%s"' % NEW_FP).replace(m[0], '(at 166.64 %.3f)' % (float(m[1]) - DY), 1)
    # the fields keep their place on the board; the old graphics go
    p = b.index('(path ')
    head = re.sub(r'\(at ([-\d.]+) ([-\d.]+)( -?\d+)?\)', lambda q: '(at %s %.2f%s)' % (q[1], float(q[2]) + DY, q[3] or ''), b[:p][b.index('(property'):])
    b = b[:b.index('(property')] + head + b[p:]
    a = b.index('(fp_line'); z = b.index('(pad "1"')
    src = open(K + 'footprints/Connector_PinHeader_2.54mm.pretty/PinHeader_1x07_P2.54mm_Vertical.kicad_mod').read()
    g = ''
    for x in blocks(src, 0):
        if '(uuid' not in x: x = x[:-1].rstrip() + '\n\t\t(uuid "%s")\n\t)' % uuid.uuid4()
        g += x.replace('\n', '\n\t') + '\n\t\t'
    b = b[:a] + g + b[z:]
    pads = b.index('(pad "1"')
    def pad(q):
        n = int(q[1]); return '(pad "%d" thru_hole %s\n\t\t\t(at 0 %.2f)' % (n, 'rect' if n == 1 else 'circle', float(q[2]) + DY)
    tail, c = re.subn(r'\(pad "(\d)" thru_hole \w+\s*\(at 0 ([-\d.]+)\)', pad, b[pads:]); assert c == 7
    tail, c = re.subn(r'\(pinfunction "\w+_(\d)"\)', r'(pinfunction "Pin_\1")', tail); assert c == 7
    return t[:i] + b[:pads] + tail + t[e:]


def schematic(t):
    i = t.index('(symbol "%s"' % OLD_SYM); e = sexp_end(t, i)
    src = open(K + 'symbols/Connector_Generic.kicad_sym').read()
    j = src.index('(symbol "Conn_01x07"'); s = src[j:sexp_end(src, j)]
    s = s.replace('(symbol "Conn_01x07"', '(symbol "%s"' % NEW_SYM, 1).replace('\n', '\n\t')
    t = t[:i] + s + t[e:]
    # mirrored so the pins stay on the right: pin 1 at (182.88, 97.79) as before
    a = '(lib_id "%s")\n\t\t(at 177.8 95.25 0)' % OLD_SYM; assert t.count(a) == 1
    t = t.replace(a, '(lib_id "%s")\n\t\t(at 177.8 105.41 0)\n\t\t(mirror y)' % NEW_SYM)
    a = '(property "Footprint" "%s"' % OLD_FP; assert t.count(a) == 1
    return t.replace(a, '(property "Footprint" "%s"' % NEW_FP)


def main():
    from geo import B
    d = sys.argv[1] if len(sys.argv) > 1 else B + 'mx/right'
    assert not [f for f in os.listdir(d) if f.endswith('.lck')], 'close KiCad first: it would overwrite this'
    for name, fn in (('mx_right.kicad_pcb', footprint), ('mx_right.kicad_sch', schematic)):
        p = os.path.join(d, name); t = open(p).read(); assert OLD_FP in t, 'already applied'
        open(p, 'w').write(fn(t))
    print('J1 ->', NEW_FP, NEW_SYM)


if __name__ == '__main__': main()
