# right only: thumb access to the trackball (no top case, lowered deck), the frame in front of the trackball lowered
exec(open('/Users/daiki/Projects/sage60/mechanical/case/fusion/fx.py').read())
def run(_c):
    spec = json.load(open(SCR + 'right%s_spec.json' % SFX))
    d = design(DOC); r = d.rootComponent; up = d.userParameters
    cp = r.constructionPlanes
    i = cp.createInput(); i.setByOffset(r.xYConstructionPlane, VI.createByString('-( shelf_d + tb_deck_d )')); deck = cp.add(i); deck.name = 'TB_DECK'
    deck.isLightBulbOn = False
    sk = new_sketch(r, 'TB_ACCESS', r.xYConstructionPlane, spec['TB_ACCESS']); sk.isVisible = False
    ex = r.features.extrudeFeatures
    bot = r.bRepBodies.itemByName('right_bottom')
    inp = ex.createInput(oc(profiles(sk)), FO.CutFeatureOperation)
    inp.startExtent = adsk.fusion.FromEntityStartDefinition.create(deck, VI.createByString('0 mm'))
    inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByString('20 mm')), adsk.fusion.ExtentDirections.PositiveExtentDirection)
    inp.participantBodies = [bot]
    f = ex.add(inp); f.name = 'TB_DECK_CUT'
    mocks = [r.bRepBodies.itemByName('MOCK_A')]
    inp = ex.createInput(oc(profiles(sk)), FO.CutFeatureOperation)
    inp.startExtent = adsk.fusion.OffsetStartDefinition.create(VI.createByString('-30 mm'))
    inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByString('60 mm')), adsk.fusion.ExtentDirections.PositiveExtentDirection)
    inp.participantBodies = mocks
    f = ex.add(inp); f.name = 'TB_ACCESS_TOP_CUT'
    # in front of the ball centre the frame round the trackball case is lowered by tb_front_drop (the frame stays)
    sk = new_sketch(r, 'TB_FRONT_LOW', r.xYConstructionPlane, spec['TB_FRONT_LOW']); sk.isVisible = False
    inp = ex.createInput(oc(profiles(sk)), FO.CutFeatureOperation)
    inp.startExtent = adsk.fusion.OffsetStartDefinition.create(VI.createByString('top_h - tb_front_drop'))
    inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(VI.createByString('tb_front_drop + 1 mm')), adsk.fusion.ExtentDirections.PositiveExtentDirection)
    inp.participantBodies = mocks
    f = ex.add(inp); f.name = 'TB_FRONT_LOW_CUT'
    for b in [b for b in r.bRepBodies if b.name.startswith('MOCK_A ') and b.volume < 1e-3]:   # zero-thickness specks the cut can leave where its edge meets the key opening's
        r.features.removeFeatures.add(b).name = 'DROP_SPECK'
    for b in r.bRepBodies:
        bb = b.boundingBox
        print(b.name, [round(v * 10, 2) for v in (bb.minPoint.x, bb.minPoint.y, bb.minPoint.z, bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z)], round(b.volume, 2), 'lumps', b.lumps.count)
    print('health', [(d.timeline.item(i).name, d.timeline.item(i).healthState) for i in range(d.timeline.count) if d.timeline.item(i).healthState != 0])
