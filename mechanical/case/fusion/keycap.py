# simple keycap mocks (tapered box, R on the side edges) -> models/keycap_{mx,lp}.step; origin = centre of the rim, z up.
# ponytail: no dish / profile per row; replace the STEP with a real keycap model if the look matters
import adsk.core, adsk.fusion
SCR = '/Users/daiki/Projects/sage60/mechanical/case/'
# bottom w, bottom d, top w, top d, height, side-edge R (mm)
KEYCAPS = {'mx': (18.0, 18.0, 12.7, 14.5, 7.5, 1.5),     # Cherry-profile-ish (R3)
           'lp': (18.0, 18.0, 15.5, 15.5, 3.5, 1.5)}     # low-profile MX-stem cap for Choc v2

def run(_c):
    app = adsk.core.Application.get()
    for name, (bw, bd, tw, td, h, rr) in KEYCAPS.items():
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        r = adsk.fusion.Design.cast(app.activeProduct).rootComponent
        def rect(plane, w, d):
            sk = r.sketches.add(plane)
            sk.sketchCurves.sketchLines.addCenterPointRectangle(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(w / 20, d / 20, 0))
            return sk.profiles.item(0)
        pi = r.constructionPlanes.createInput(); pi.setByOffset(r.xYConstructionPlane, adsk.core.ValueInput.createByReal(h / 10))
        li = r.features.loftFeatures.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        li.loftSections.add(rect(r.xYConstructionPlane, bw, bd)); li.loftSections.add(rect(r.constructionPlanes.add(pi), tw, td))
        body = r.features.loftFeatures.add(li).bodies.item(0)
        side = adsk.core.ObjectCollection.create()
        for e in body.edges:
            s, t = e.startVertex.geometry, e.endVertex.geometry
            if abs(s.z - t.z) > 1e-4: side.add(e)
        fi = r.features.filletFeatures.createInput(); fi.addConstantRadiusEdgeSet(side, adsk.core.ValueInput.createByReal(rr / 10), True)
        r.features.filletFeatures.add(fi)
        em = adsk.fusion.Design.cast(app.activeProduct).exportManager
        em.execute(em.createSTEPExportOptions(SCR + 'models/keycap_%s.step' % name, r))
        doc.close(False)
        print(name, 'ok')
