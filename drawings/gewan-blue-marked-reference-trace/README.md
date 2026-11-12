# Marked blue area — copied reference linework

This package traces the actual linework inside the user's blue marking. It is not a redesign or another shell-inspired alternative. The exact clean version of the marked image was recovered and supplied as `Unmarked_Reference.png`.

## Files

- `Standalone.png` / `Selected_Reference.pdf`: isolated copied linework, derived from the exported CAD.
- `Reference_Overlay.png`: exported CAD linework over the clean reference, for checking the copy.
- `Reference_Comparison.png`: selected reference area beside the CAD-derived isolated drawing.
- `Selected_Reference_Standalone.dxf`: 70 native cubic spline paths, in millimetres, with a uniform reference scale.
- `reference_path_map.json`: every CAD path mapped to its source reference edge.
- `verification.json`: measured precision and export checks.

The source image's previously confirmed 25 m large circle calibrates the standalone scale. A raster source does not support a claim of absolute millimetre accuracy. The maximum fitted curve deviation from its extracted centreline is 1.247 source pixels. Shared graph junctions are checked after DXF readback. Open ends at contacts with the existing building/boundaries are intentional; this standalone network is not advertised as an independently closed set of extrudable faces.

The original uploaded DWG, corrected U-shaped building and user-made red areas were not modified. Experimental integration files were withheld: placing the copied reference directly on the corrected CAD produced collisions with building projections. An attempted nonlinear fit changed the copied shapes and was rejected. The standalone copy remains unwarped. Integration awaits the user's decision about moving/scaling complete pieces while retaining their shapes and leaving the building fixed.

The DXF was reread and audited successfully. Opening in desktop AutoCAD or SketchUp was not tested. No combined DWG is supplied.
