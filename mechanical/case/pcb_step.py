"""PCB + parts (XIAO, sockets, diodes, JST, switch) + key switches + keycaps -> models/{left,right}{,_lp}_pcb.step
for the Fusion mocks (fusion/stage5.py). MX: Cherry MX + keycap_mx, LP: Kailh Choc + keycap_lp (keycap STEPs from fusion/keycap.py).
The footprints point at other people's paths, so the model paths are rewritten to models/ and the KiCad library first.
Origin = KiCad (0,0), so STEP x = KiCad x, y = -KiCad y (= Fusion), board bottom z = 0, top z = 1.51."""
import os, re, subprocess, tempfile
from geo import B

HERE = os.path.dirname(os.path.abspath(__file__)) + '/models/'
KLIB = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels'
PCBS = {'left': 'mx_main/mx.kicad_pcb', 'right': 'mx_right_tb/mx_right_tb.kicad_pcb'}
LOCAL = {'XIAO-nRF52840 v15.step', 'Kailh-CherryMX-Socket.step'}
# switch model (origin = PCB top), keycap model, keycap rim height above the PCB top (mm)
# MX: plate top = PCB + 5.0, stem top = plate + 10.2, rim = plate + 6.0 (4 mm travel leaves 2.0 above the plate)
# LP: plate top = PCB + 2.2, stem top = plate + 5.8 (Choc v1 model; v2 not measured), rim = plate + 3.3
VARIANTS = {'': ('cherry_mx.step', 'keycap_mx.step', 5.0 + 6.0), '_lp': ('kailh_choc.step', 'keycap_lp.step', 2.2 + 3.3)}

def fix(m):
    path = m.group(1); name = os.path.basename(path)
    if name in LOCAL: return '(model "%s"' % (HERE + name)
    if 'XIAO' in name or 'Seeed' in name: return '(model "/nonexistent/%s"' % name   # the right footprint stacks 5 XIAO variants
    return m.group(0)

def model(f, z=0.0):
    return '\n\t\t(model "%s"\n\t\t\t(offset\n\t\t\t\t(xyz 0 0 %g)\n\t\t\t)\n\t\t\t(scale\n\t\t\t\t(xyz 1 1 1)\n\t\t\t)\n\t\t\t(rotate\n\t\t\t\t(xyz 0 0 0)\n\t\t\t)\n\t\t)' % (HERE + f, z)

env = dict(os.environ, KIGITHUB3D=KLIB, KICAD9_3DMODEL_DIR=KLIB, KICAD10_3DMODEL_DIR=KLIB)
for side, f in PCBS.items():
    txt = re.sub(r'\(model "([^"]*)"', fix, open(B + f).read())
    txt = re.sub(r'(\(model "[^"]*XIAO-nRF52840 v15.step")\s*\(hide yes\)', r'\1', txt)   # right: the nRF model is hidden
    txt = re.sub(r'(XIAO-nRF52840 v15.step"\s*\(offset\s*\(xyz 6 -12.2) 6\)', r'\1 0.381)', txt)  # left: z 6 floats it 5.6 mm; 0.381 as on the right
    for sfx, (sw, cap, rim) in VARIANTS.items():
        n = [0]
        def add(m):
            n[0] += 1; return m.group(1) + model(sw) + model(cap, rim) + m.group(2)
        t = re.sub(r'(\n\t\(footprint "[^"]*Hotswap[^"]*".*?)(\n\t\))', add, txt, flags=re.S)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'pcb.kicad_pcb'); open(p, 'w').write(t)
            out = HERE + '%s%s_pcb.step' % (side, sfx)
            r = subprocess.run(['kicad-cli', 'pcb', 'export', 'step', '--subst-models', '--user-origin', '0x0mm', '-f', '-o', out, p],
                               env=env, capture_output=True, text=True)
        miss = [l for l in (r.stdout + r.stderr).splitlines() if 'not found' in l.lower() or 'cannot' in l.lower()]
        assert r.returncode == 0 and os.path.getsize(out) > 1e6, r.stderr[-2000:]
        print(side + sfx, '%d keys' % n[0], '%.1f MB' % (os.path.getsize(out) / 1e6), 'missing:', len(miss))
        for l in miss: print('  ', l)
