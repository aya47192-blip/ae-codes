# Gewan Palace — connected surrounding landscape review

This revision replaces the rejected miniature-block placement. It works on the actual surrounding landscape as one connected field: left of the corrected building, below it, and on its right.

## What changed

The reference curves are laid into the full working field. Missing exterior guide portions are completed from the clean reference; divisions now meet the actual field edges and building projections. Contacts were adapted and reference curves were trimmed at protected boundaries. Redundant near-boundary clipping slivers were removed. This is an integrated interpretation of the reference in the current CAD, not the earlier set of unchanged small stamps, and not a claim of literal unchanged reference-piece geometry.

The corrected building, central existing concept, chalets/plot boundaries, roads and original circles were not redrawn or smoothed. 243 original model entities are preserved exactly. One straight preliminary guide inside the blue work area (DXF handle 70) was shortened at its upper field-perimeter contact; its original support line and lower position were retained. The uploaded DWG itself remains unchanged.

## Files

- `Review.png` / `Review.pdf`: exported CAD, source black and changed/completed landscape teal.
- `Black_Linework.png`: the same combined drawing in black.
- `CAD_Dark_Preview.png`: the same geometry on a drafting background; preview colours only.
- `Connected_Layout_Review.dxf`: editable native LINE / ARC / LWPOLYLINE / SPLINE geometry, millimetres, original CAD coordinates.
- `verification.json`, `reference_path_map.json`: preservation checks, contact measurements and reference provenance.

## Verification and limits

The DXF was reread and audited without errors or automatic repairs. An independent WebAssembly DWG/DXF reader compared the protected source geometry to the uploaded DWG: no differences. The added curves are simple, stay within the working boundary and do not enter the protected building. Native curve-end contacts were checked against analytic source lines/arcs and the actual cubic curves, with a maximum residual below 0.01 mm.

That contact residual measures geometric joining, not the accuracy of the raster reference or construction dimensions. The reference originated as a raster image; some junctions and boundary-adjacent curve portions were deliberately adapted to the current CAD. Original source open features outside this scope remain unchanged.

A diagnostic chord-network polygonization finds 30 bounded regions after removing sub-3 m² clipping pockets. Numerical/connector cut-dangle artifacts remain in that separate chord diagnostic. It is not a successful SketchUp face-formation test. Desktop AutoCAD opening and SketchUp import/push-pull were not tested, so this is a layout/CAD review, not a certified extrusion-ready model. No new DWG is supplied; the delivered CAD format is DXF.
