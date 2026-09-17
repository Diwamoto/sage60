# SAGE60 gasket plate v1

This revision derives the plate geometry from the current boards:

- `pcb/mx_main/mx.kicad_pcb` — left, 30 Choc/MX switch cutouts
- `pcb/mx_right_tb/mx_right.kicad_pcb` — right, 28 Choc/MX switch cutouts and trackball area

The plate is intended as a 1.5 mm FR4 or similar laser/CNC-cut part. There is no copper, no electrical net, and no component data in the generated plate boards. The square switch openings are 14 mm with R0.25 corners and retain each source switch's position and rotation. The current switch footprints do not contain a manufacturing plate cutout, so this v1 keeps the 14 x 14 mm cutout convention from the existing `mx_plate` / `SW_Hole` design; confirm the actual switch body before ordering a batch.

## Files

The production-facing files are:

- `../../pcb/mx_plate/gasket_v1/mx_plate_gasket.dxf`
- `../../pcb/mx_plate_right_tb/gasket_v1/mx_plate_right_tb_gasket.dxf`
- `../../pcb/mx_plate/gasket_v1/mx_plate_gasket.step`
- `../../pcb/mx_plate_right_tb/gasket_v1/mx_plate_right_tb_gasket.step`

The `.kicad_pcb` files are useful for opening the geometry in KiCad and checking the switch holes. The `_case_reference.dxf` files include the plate outline, current PCB outline, gasket contacts, and switch cutouts on separate layers for case design.

## Case interface

The left half has six external gasket ears and the right trackball half has five; R5 is intentionally omitted on the right. Each ear has a 14 x 3 mm contact face; use two contacts per ear, one above and one below the plate. The initial case model uses:

- 1.5 mm plate thickness
- 1.5 mm gasket thickness before compression
- 20% initial compression, giving 1.2 mm per gasket
- 3.9 mm between the upper and lower case contact faces
- 0.5 mm lateral clearance between the plate and case pocket
- at least 0.5 mm free movement before the plate touches the case wall

The exact ear centers, tangent directions, and CAD coordinates are in `case_interface.json` and `gasket_positions.csv`. CAD coordinates use X right and Y up; PCB coordinates use X right and Y down.

Keep the right trackball holder, sensor board, and cable supported from the case. The plate intentionally leaves the trackball/cable area open so the ball assembly does not become a moving load on the switch plate.

## Regeneration and checks

Run `extract_boards.py` with KiCad's Python when the source PCB changes, then run `generate.py`. The generator stops if the source switch count, outline continuity, hole clearance, connectivity, or gasket-ear placement fails.

`verify_saved.py` reopens the generated KiCad boards, checks the DXF contours and rotated holes, and verifies that the exported STL is watertight. KiCad's STL preview uses its default stackup surface and reports approximately 1.43 mm for a 1.50 mm board body; the authoritative manufacturing thickness is the 1.50 mm value in the PCB/DXF design.

The latest checks are recorded in `validation.json`, `saved_cad_validation.json`, `drc_left.json`, and `drc_right.json`.

## If the plate is 3D printed

Do not simply change the whole plate from 1.5 mm to 5.0 mm. The current footprint is named `CherryMX_Choc_Hotswap_v2`; a flat 5 mm switch rim can prevent the switch retention features from engaging and can move the PCB 3.5 mm farther from the switch. Use a 5 mm structural frame with an underside relief around each switch so the local switch rim remains about 1.5–1.6 mm thick, or make the frame clear the switches and let the PCB retain them.

With 5 mm ears and two 1.5 mm gaskets compressed to 1.2 mm each, the case contact-face separation becomes 7.4 mm. The 3.9 mm value above applies only to the 1.5 mm plate version.

## Fusion case prototype

Fusion 360 was used to create optional, non-saved split-case fit-check bodies from the plate references. The plate interface itself has six raised supports on the left and five on the right; R5 is intentionally omitted on the right. The right half adds a 37 mm trackball opening from the current PMW3610 connector center and a 42 mm support lip. These case prototypes are not required for the plate handoff.

- `sage60_left_case_bottom.step` / `.stl`
- `sage60_left_case_top.stl`
- `sage60_left_case_complete.step`
- `sage60_right_tb_case_bottom.step` / `.stl`
- `sage60_right_tb_case_top.stl`
- `sage60_right_tb_case_complete.step`

The complete STEP files contain both case bodies for each half; the separate STL files are convenient for printing one body at a time. The rectangular shell is intentionally a first fit-check envelope. Keycap clearance, typing angle, battery pocket, antenna clearance, cable exits, and the final trackball holder should be set after the plate and holder are physically checked. The Fusion document was intentionally left unsaved; the exported files are the handoff artifacts.

### Contour-following case revision

The contour revision follows the generated plate exterior rather than the old rectangular bounding box. The case exterior is offset 2.0 mm outward from the plate, and the internal pocket is offset 0.5 mm outward to leave a small fit clearance; the resulting nominal wall is about 1.5 mm. The gasket ears and the right trackball-side outline are therefore retained in the case perimeter.

- `sage60_left_case_contour_bottom.step` / `.stl`
- `sage60_left_case_contour_top.stl`
- `sage60_left_case_contour_complete.step`
- `sage60_right_tb_case_contour_bottom.step` / `.stl`
- `sage60_right_tb_case_contour_top.stl`
- `sage60_right_tb_case_contour_complete.step`

### V2 magnetic two-piece case

The current case revision is a two-piece construction. The lower case carries the floor, the plate pocket, the gasket supports, and the trackball opening. The upper case is a single combined frame and skirt; its skirt starts below the lower-case top and covers the lower wall. The upper outline is a simplified convex polygon derived from the plate envelope, with 1.5 mm outline simplification tolerance and mostly straight edges. This follows the Altair-X direction of combining geometric arcs and bold straight edges while keeping the outside silhouette simple: <https://ai03.com/projects/altair/>.

- Lower outer offset from the simplified envelope: 2.8 mm
- Upper outer offset: 4.2 mm
- Upper skirt inner offset: 3.1 mm
- Plate opening clearance: 0.5 mm
- Lower case height / floor: 8.0 mm / 2.5 mm
- Upper skirt: Z 6.4–8.1 mm
- Upper frame: Z 7.9–11.6 mm
- Four blind magnet holes per half in each piece: nominal Ø3.4 mm × 2.2 mm deep, for Ø3 mm × 2 mm neodymium magnets

- `sage60_left_case_v2_bottom.step` / `.stl`
- `sage60_left_case_v2_top.stl`
- `sage60_left_case_v2_complete.step`
- `sage60_right_tb_case_v2_bottom.step` / `.stl`
- `sage60_right_tb_case_v2_top.stl`
- `sage60_right_tb_case_v2_complete.step`

The complete STEP files contain exactly two named bodies per half: `*_LOWER_CASE` and `*_UPPER_CASE`. The bottom and top STL files are exported from those combined bodies, including gasket supports and the right trackball lip.

### V3 controller-clearance revision

The V2 envelope filled the controller edge that is intentionally open in the
plate. V3 adds a simple rectangular service bay from the actual PCB
coordinates: the left XIAO nRF52840 is at the right edge and the right XIAO
nRF52840 Plus is at the left edge. The bay also covers the nearby battery JST
footprint. The lower case opens this unused controller edge through its full
height, while the upper case has a through-window from the skirt datum to the
top face. The opening runs to the corresponding outside edge so the module and
cable are not trapped behind the simplified convex silhouette.

- Left service bay (PCB coordinates): X 167.5–202.0 mm, Y 22.0–61.0 mm
- Right service bay (PCB coordinates): X 43.5–78.5 mm, Y 25.0–61.0 mm
- Upper window: Z 6.4–11.6 mm
- Lower controller bay: Z 0–8.0 mm

- `sage60_left_case_v3_bottom.step` / `.stl`
- `sage60_left_case_v3_top.stl`
- `sage60_left_case_v3_complete.step`
- `sage60_right_tb_case_v3_bottom.step` / `.stl`
- `sage60_right_tb_case_v3_top.stl`
- `sage60_right_tb_case_v3_complete.step`

The Fusion documents for this revision contain only the two case bodies per
half and include `*_LOWER_CONTROL_BAY_CUT` and `*_UPPER_CONTROL_WINDOW_CUT`
features. The controller keepout still needs a final physical check against
the exact XIAO board variant, USB plug, and battery cable bend radius.

## Mounting direction

For this prototype, gasket support at the plate perimeter is a good way to learn how the split halves feel independently. Keep the PCB floating or use soft PCB supports so the plate remains the primary load path. A tray or top mount is easier to tune, but it is stiffer and transfers more case vibration into the board.

For a future electro-capacitive version, bottom-mount is not a requirement. EC designs need the slider/dome/PCB spacing to remain controlled; the practical requirement is a rigid, repeatable plate-to-PCB assembly. A plate-plus-PCB sandwich can still be gasket-mounted by the plate, while the bottom case supports only the assembly and battery. If the future EC design uses an integrated plate, keep the gasket ears and case contact datum independent of the switch mechanism so the EC stack can be swapped without redesigning the case.
