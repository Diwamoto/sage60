"""Generate the V3 split cases with controller and battery clearance bays.

The implementation remains shared with the previous case generator so the
plate offsets, gasket supports, magnet pockets, and trackball lip stay
identical.  V3 adds the controller-edge windows before exporting the bodies.
"""

exec(open('/Users/daiki/Projects/sage60/mechanical/gasket_v1/fusion_case_v2.py').read(), globals())
