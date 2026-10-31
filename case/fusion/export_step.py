# case bodies -> production/case_cnc/sage60_<side>{,_lp}_{bottom,top}.step for the JLCCNC quote (as modelled: plate top z=0).
# globals: SIDE, LP.  The walnut MCU cover is ordered from the DXF, not here.
exec(open('/Users/daiki/Projects/sage60/case/fusion/fx.py').read())
import os
OUT = '/Users/daiki/Projects/sage60/production/case_cnc/'

def run(_c):
    os.makedirs(OUT, exist_ok=True)
    d = design(DOC); r = d.rootComponent; em = d.exportManager
    for name, part in (('%s_bottom' % SIDE, 'bottom'), ('MOCK_A', 'top')):
        b = r.bRepBodies.itemByName(name); b.isLightBulbOn = True
        path = OUT + 'sage60_%s%s_%s.step' % (SIDE, '_lp' if LP else '', part)
        occ = r.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        b.copyToComponent(occ)
        em.execute(em.createSTEPExportOptions(path, occ.component))
        occ.deleteMe()
        size = os.path.getsize(path)
        assert size > 5000, (path, size)
        print(os.path.basename(path), size // 1024, 'KB', round(b.volume, 2), 'cm3')
