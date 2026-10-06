# case bodies -> case/sage60_<side>{,_lp}_{bottom,top,cover}.3mf for test prints (as modelled: plate top z=0; turn the top
# case over in the slicer).  globals: SIDE, LP.  Hidden bodies export as empty files, so each body is shown first and the
# file size checked.
exec(open('/Users/daiki/Projects/sage60/mechanical/case/fusion/fx.py').read())
import os
OUT = '/Users/daiki/Projects/sage60/case/'

def run(_c):
    d = design(DOC); r = d.rootComponent; em = d.exportManager
    for name, part in (('%s_bottom' % SIDE, 'bottom'), ('MOCK_A', 'top'), ('MCU_COVER', 'cover')):
        b = r.bRepBodies.itemByName(name); b.isLightBulbOn = True
        path = OUT + 'sage60_%s%s_%s.3mf' % (SIDE, '_lp' if LP else '', part)
        em.execute(em.createC3MFExportOptions(b, path))
        size = os.path.getsize(path)
        assert size > 5000, (path, size)
        print(os.path.basename(path), size // 1024, 'KB', round(b.volume, 2), 'cm3')
