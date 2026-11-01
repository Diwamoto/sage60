"""one-shot (2026-11-01): XIAO nRF52840 Plus footprint and symbol drawn for this repo, replacing Seeed's (CC BY-SA 4.0), so the repository
can be MIT.  Writes the library (pcb/modules/footprint/sage60.pretty, pcb/modules/symbol/sage60.kicad_sym) and swaps U2 on pcb/mx/right and
pcb/ec/main.  What the module fixes stays: pad numbers, positions, sizes and drills, pin names, and the Edge.Cuts window under the battery
pads (each board keeps its own copy of the pads, nets and window; so does its model list, case/pcb_step.py reads it).  What is new:
silkscreen, fab, courtyard and the symbol body.  The symbol's pins stay where they are, so the wires still meet them.
Refuses to run while KiCad has a project open.  Running it again finds nothing to change (asserts).
Usage: xiao_own.py [root holding mx/right, ec/main, modules]"""
import sys, os, re, uuid; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))   # case/ (casegeo, geo, ...)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from j1_stock import sexp_end

OLD_FP, OLD_SYM = '0_Seeed Studio XIAO Series Library:XIAO-nRF52840-Plus-DIP', '0_Seeed_Studio_XIAO_Series:XIAO-nRF52840_Plus_SMD'
NAME = 'XIAO_nRF52840_Plus'; NEW = 'sage60:' + NAME
BOARDS = (('mx/right', 'mx_right'), ('ec/main', 'ec'))
ROT = 90        # U2 sits at 90 on both boards; the board file stores pad angles with that added


def rect(x0, y0, x1, y1, layer, w):
    return '(fp_rect\n\t\t\t(start %g %g)\n\t\t\t(end %g %g)\n\t\t\t(stroke\n\t\t\t\t(width %g)\n\t\t\t\t(type solid)\n\t\t\t)\n\t\t\t(fill no)\n\t\t\t(layer "%s")\n\t\t\t(uuid "%s")\n\t\t)' % (x0, y0, x1, y1, w, layer, uuid.uuid4())


def dot(x, y, layer):
    return '(fp_circle\n\t\t\t(center %g %g)\n\t\t\t(end %g %g)\n\t\t\t(stroke\n\t\t\t\t(width 0.5)\n\t\t\t\t(type solid)\n\t\t\t)\n\t\t\t(fill yes)\n\t\t\t(layer "%s")\n\t\t\t(uuid "%s")\n\t\t)' % (x, y, x + 0.25, y, layer, uuid.uuid4())


def graphics():
    """+x is the USB end; the dot marks pin 1"""
    return [rect(-10.5, -8.9, 10.5, 8.9, 'F.SilkS', 0.12), rect(10.5, -4.5, 12, 4.5, 'F.SilkS', 0.12), dot(9.4, -7.8, 'F.SilkS'),
            rect(-10.5, -8.9, 10.5, 8.9, 'F.Fab', 0.1), rect(-10.6, -9, 12.1, 9, 'F.CrtYd', 0.05)]


def children(b, names):
    """spans of b's direct children named names"""
    return [(m.start() + 3, sexp_end(b, m.start() + 3)) for m in re.finditer(r'\n\t\t\((?:%s)\b' % names, b)]


def footprint(t):
    i = t.index('(footprint "%s"' % OLD_FP); e = sexp_end(t, i); b = t[i:e].replace(OLD_FP, NEW, 1)
    spans = children(b, 'fp_line|fp_arc|fp_circle|fp_rect'); out = b[:spans[0][0]]; keep = []; last = spans[0][0]
    for s, z in spans:
        out += b[last:s].strip('\n\t ') if last != spans[0][0] else ''
        if '(layer "Edge.Cuts")' in b[s:z]: keep.append(b[s:z])
        last = z
    assert len(keep) == 8, 'expected the 8 window edges'
    out += '\n\t\t'.join(graphics() + keep) + b[last:]
    return t[:i] + out + t[e:], keep


def lib_footprint(t, keep):
    """the library copy, from the board's pads less what belongs to the board"""
    i = t.index('(footprint "%s"' % NEW); b = t[i:sexp_end(t, i)]; pads = []
    for s, z in children(b, 'pad'):
        p = b[s:z]
        p = re.sub(r'\n\t+\((?:net|pinfunction|uuid) [^\n]*', '', p)
        p = re.sub(r'\(at ([-\d.]+) ([-\d.]+) (-?[\d.]+)\)', lambda m: '(at %s %s %g)' % (m[1], m[2], (float(m[3]) - ROT) % 360), p, count=1)
        pads.append(p)
    assert len(pads) == 43
    field = lambda n, v, y, l, h='': '(property "%s" "%s"\n\t\t\t(at 0 %g 0)\n\t\t\t(layer "%s")%s\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1 1)\n\t\t\t\t\t(thickness 0.15)\n\t\t\t\t)\n\t\t\t)\n\t\t)' % (n, v, y, l, h)
    body = [field('Reference', 'REF**', -11.5, 'F.SilkS'), field('Value', NAME, 11.5, 'F.Fab'), '(attr smd)'] + graphics() + [re.sub(r'\n\t+\(uuid [^\n]*', '', k) for k in keep] + pads
    return ('(footprint "%s"\n\t(version 20260206)\n\t(generator "sage60")\n\t(layer "F.Cu")\n\t(descr "Seeed Studio XIAO nRF52840 Plus, top side")\n\t\t' % NAME + '\n\t\t'.join(body) +
            '\n\t\t(model "${AMZPATH}/3dmodels/AMz3D.3dshapes/XIAO-nRF52840 v15.step"\n\t\t\t(offset\n\t\t\t\t(xyz -1.778 -6.096 0.381)\n\t\t\t)\n\t\t\t(scale\n\t\t\t\t(xyz 1 1 1)\n\t\t\t)\n\t\t\t(rotate\n\t\t\t\t(xyz -90 0 0)\n\t\t\t)\n\t\t)\n)\n')


def symbol(name, pins):
    """the body: a plain box; pins (x y angle, pin name, number) as the wires expect them"""
    font = '(effects (font (size 1.27 1.27)))'
    p = ''.join('\n\t\t\t\t(pin passive line (at %s) (length 2.54) (name "%s" %s) (number "%s" %s))' % (a, n, font, k, font) for a, n, k in pins)
    short = name.split(':')[-1]
    return ('(symbol "%s"\n\t\t\t(exclude_from_sim no)\n\t\t\t(in_bom yes)\n\t\t\t(on_board yes)'
            '\n\t\t\t(property "Reference" "U" (at 21.59 5.08 0) %s)\n\t\t\t(property "Value" "" (at 21.59 -58.42 0) %s)'
            '\n\t\t\t(property "Footprint" "%s" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))'
            '\n\t\t\t(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))'
            '\n\t\t\t(property "Description" "XIAO nRF52840 Plus" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))'
            '\n\t\t\t(symbol "%s_1_1"\n\t\t\t\t(rectangle (start 0 0) (end 43.18 -52.07) (stroke (width 0.254) (type solid)) (fill (type background)))%s\n\t\t\t)\n\t\t)'
            % (name, font, font, NEW, short, p))


def schematic(t):
    i = t.index('(symbol "%s"' % OLD_SYM); e = sexp_end(t, i); b = t[i:e]
    pins = re.findall(r'\(pin passive line\s*\(at ([^)]+)\).*?\(name "([^"]*)".*?\(number "([^"]*)"', b, re.S); assert len(pins) == 29
    t = t[:i] + symbol(NEW, pins) + t[e:]
    a = '(lib_id "%s")' % OLD_SYM; assert t.count(a) == 1
    t = t.replace(a, '(lib_id "%s")' % NEW)
    a = '(property "Footprint" "%s"' % OLD_FP; assert t.count(a) == 1
    return t.replace(a, '(property "Footprint" "%s"' % NEW), pins


def main():
    from geo import B
    root = sys.argv[1] if len(sys.argv) > 1 else B
    for sub, _ in BOARDS:
        assert not [f for f in os.listdir(os.path.join(root, sub)) if f.endswith('.lck')], 'close KiCad first: it would overwrite this'
    fpdir = os.path.join(root, 'modules/footprint/sage60.pretty'); symdir = os.path.join(root, 'modules/symbol')
    os.makedirs(fpdir, exist_ok=True); os.makedirs(symdir, exist_ok=True)
    made = False
    for sub, name in BOARDS:
        p = os.path.join(root, sub, name + '.kicad_pcb'); t = open(p).read(); assert OLD_FP in t, 'already applied'
        t, keep = footprint(t); open(p, 'w').write(t)
        if not made: open(os.path.join(fpdir, NAME + '.kicad_mod'), 'w').write(lib_footprint(t, keep))
        p = os.path.join(root, sub, name + '.kicad_sch'); t, pins = schematic(open(p).read()); open(p, 'w').write(t)
        if not made:
            open(os.path.join(symdir, 'sage60.kicad_sym'), 'w').write('(kicad_symbol_lib\n\t(version 20241209)\n\t(generator "sage60")\n\t%s\n)\n' % symbol(NAME, pins).replace('\n\t\t', '\n\t').replace('\n\t\t\t', '\n\t\t'))
        made = True
        lib = "(lib (name \"sage60\")(type \"KiCad\")(uri \"${KIPRJMOD}/../../modules/%s\")(options \"\")(descr \"\"))"
        open(os.path.join(root, sub, 'fp-lib-table'), 'w').write('(fp_lib_table\n  (version 7)\n  %s\n)\n' % (lib % 'footprint/sage60.pretty'))
        open(os.path.join(root, sub, 'sym-lib-table'), 'w').write('(sym_lib_table\n  (version 7)\n  %s\n)\n' % (lib % 'symbol/sage60.kicad_sym'))
    print('U2 ->', NEW)


if __name__ == '__main__': main()
