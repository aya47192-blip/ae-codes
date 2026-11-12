# Gewan Palace — copied blue units integrated into the supplied plan

This revision implements the user's explicit permission to move and uniformly reduce complete reference pieces while leaving the corrected building fixed.

The source is the uploaded `hhhhhhhhhhhhhhhh.dwg`. All 244 original model entities remain unchanged. The added geometry comes from the actual marked reference, not from the rejected fan/strip redesigns. Six editable blocks contain the copied garden units. Their adjacent reference boundary segments are included so the transferred pieces have complete closed outlines. No original building, projection, road, circle, source division or preliminary source guide was deleted or moved.

## Files

- `Review.png` / `Review.pdf`: supplied CAD black; placed copies teal.
- `Black_Linework.png`: the combined drawing in black.
- `Full_Plan.png`: full uncut drawing extent.
- `Copied_Units.png`: the actual reference pieces used, with their placement scales.
- `Gewan_Blue_Units_Merged.dxf`: combined editable CAD, AutoCAD 2000 DXF, millimetres.
- `Placed_Units_Only.dxf`: six block references and their definitions, at the original CAD coordinates. Overlay at 0,0,0; scale 1; rotation 0. Use EXPLODE only if editing the curves individually is needed.
- `Placement_Schedule.csv`: uniform scale and measured dimensions of each placed unit.
- `placement_map.json`: block/curve provenance and source face IDs.
- `verification.json`, `independent_verification.json`: preservation and geometry checks.

## What was checked

Every placed block has identical X/Y/Z scale factors, all below 1, and zero rotation. Block control points and knots retain the copied reference geometry exactly; only uniform scale and translation are applied. There is no nonlinear warp, unequal-axis scaling, mirroring or invented replacement motif.

All 244 original CAD entities were compared after export; none changed. An independent WebAssembly reader also compared their geometry to the original DWG with no differences at a numerical comparison resolution of 0.000001 mm. That resolution is a comparison setting, not a survey or construction accuracy claim.

The six copied unit networks produce 27 closed regions, matching the 27 selected reference faces. The new networks have no dangling segments or invalid rings. The placed curves do not cross source lines, leave the site envelope, cross another copied unit, or overlap the protected building footprint. The minimum measured clearance to original linework is 809.05 mm; this is a geometric clearance, not a claim of code-compliant access or circulation design. Both delivered DXFs were reread and audited with zero errors or fixes.

The underlying reference is a raster image. Curve fitting deviates by up to 1.247 source pixels from its extracted centreline; absolute millimetre reproduction cannot be inferred from that image. Existing source open curves and duplicate boundaries are preserved. The checks about closed regions apply to the additions, not to a global repair of the original drawing.

Desktop AutoCAD opening and SketchUp import were not tested. No new DWG is included because the available DWG conversion path did not pass earlier structural checks. This package contains genuine DXF files, and remains a proposed placement for the user's design review.
