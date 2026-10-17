---
name: cad-elevation-vectorizer
description: Convert raster architectural elevations, sections, facades, and plans into layered AutoCAD DXF and pure vector PDF drawings. Use when the user requests architectural image vectorization or CAD export.
---

CAD Elevation Vectorizer
Convert pixelated raster architectural drawings (elevations, sections, facades, and plans) into mathematically crisp, layered AutoCAD .dxf files and 100% pure vector .pdf drawings using sub-pixel coordinate probing and geometric CAD reconstruction.

When to Use
The user uploads a raster image of an architectural elevation, section, facade, or floor plan and asks to convert it into vector lines.
The user wants an AutoCAD file (.dxf) and/or a vector .pdf from a blurry or pixelated architectural drawing.
The user asks to apply the saved architectural vectorization workflow to new elevations or plans.
Steps
1. Sub-Pixel Coordinate Probing and Grid Overlay Inspection
Do not use naive raster contour tracing (cv2.findContours) directly on compressed architectural JPEGs, as compression artifacts turn thin lines and hatches into jagged double-outlined blobs. Instead, extract exact geometric coordinates first:

Load the uploaded image in Python using cv2 and numpy to get its exact dimensions (W, H).
Generate a high-resolution coordinate grid overlay PNG (matplotlib) with fine X and Y ticks and inspect it via view_image.
Run a programmatic coordinate probe script on the grayscale array to extract:
Exact Y-coordinates of horizontal ground lines, floor slabs, roof eaves, window transoms, and dashed borders.
Exact X-coordinates of vertical walls, structural piers, window mullions, and frame boundaries.
Exact vertex coordinates (x, y) of sloped roofs, ramps, stairs, and diagonal shadows.
Connected-component centroids of colored accents (such as red architectural scale figures using RGB channel differences) and entourage elements (trees, vehicles, boats).
2. Geometric CAD Reconstruction (VectorScene)
Construct a unified VectorScene in Python that builds every architectural element using true geometric primitives:

Orthogonal and Angled Structural Lines: Define roof slopes, walls, slabs, and ramps as single continuous straight lines between their measured start and end vertices.

Parametric Arrays and Grids: Generate curtain-wall mullions, window transoms, vertical facade louvers, and roof standing seams using mathematical loops clipped to boundary functions (y_top_fn(x) and y_bot_fn(x)).

Clipped Masonry and Stone Hatching: Generate horizontal coursing lines and staggered vertical/diagonal joints clipped to polygonal wall boundaries via cv2.pointPolygonTest.

Crisp Vector Entourage: Place clean vector silhouettes for scale figures, branching architectural trees with crisp foliage ticks, vehicles, and boats at the exact centroids measured from the source image.

Standardized CAD Layer Hierarchy: Assign every primitive to one of these layers:

01_GROUND_CUT (ACI Color 7, heavy lineweight 1.45pt) for the primary ground section cut and site profile.
02_MAIN_STRUCTURE (ACI Color 7, medium-heavy 0.60-0.80pt) for primary building outlines, roof profiles, slabs, and structural columns.
03_SECONDARY_ARCH (ACI Color 8, medium-thin 0.35-0.45pt) for window frames, mullions, transoms, railings, and secondary context structures.
04_FACADE_LOUVERS (ACI Color 9, thin 0.24-0.30pt) for fine vertical facade ribs, sun louvers, and roof seam hatches.
05_SHADING_HATCH (ACI Color 9, thin 0.22pt) for stone/brick masonry hatches and architectural shadow polygons.
06_PEOPLE_RED (ACI Color 1, red 0.40pt) for human scale figures.
07_TREES_ENTOURAGE (ACI Color 8, thin 0.30-0.38pt) for architectural trees, vehicles, and boats.
08_WATER_LINE (ACI Color 5, blue-grey 0.35pt) for river, sea, or pool water surface lines.
09_BORDER_TEXT (ACI Color 7, 0.45pt, DASHED for frames) for viewport borders, corner crosshairs, drawing titles, and scale labels.
3. Dual Vector Export (AutoCAD DXF and Pure Vector PDF)
Export both deliverables from the exact same VectorScene instance into a task-specific output directory under /workspace/:

AutoCAD DXF (AC1009 / R12 ASCII format):
Write valid HEADER, TABLES (LTYPE with CONTINUOUS and DASHED, LAYER with ACI color codes), ENTITIES (LINE, POLYLINE/VERTEX/SEQEND, and TEXT), and EOF sections.
Flip the Y-coordinate (y_cad = height - y_img) so the drawing opens right-side-up in AutoCAD.
Pure Vector PDF (cairo.PDFSurface):
Create a cairo.PDFSurface scaled at 2.0x the image dimensions with LINE_CAP_ROUND and LINE_JOIN_ROUND.
Render architectural tonal shading fills (sc.fills) first, followed by vector lines (sc.lines), polylines (sc.polys), and vector typography (sc.texts). Never embed raster images into the PDF.
4. Validation, Visual Critique, and Delivery
Programmatic DXF Check: Verify that the .dxf file has an even line count, starts with (0, SECTION), ends with (0, EOF), and contains all expected layers and entities.
Visual Critique (view_image): Render the generated vector PDF to a high-resolution PNG using pypdfium2 (scale=2.0) into a task-specific intermediate directory under /workspace/ and inspect it with view_image. Compare against the source image to verify roof angles, soffit details, shadow hierarchy, and entourage placement. Fix any discrepancies in the script and re-run before delivering.
File Delivery:
Provide clickable links to the generated PDF and DXF files using the file-delivery mechanism available in the current environment. Do not call unavailable tools or claim files were delivered without generating them.
Provide a concise summary table of the CAD layers in the final response.
Gotchas
Coordinate grid vs. raw pixel indices: When inspecting coordinates on a Matplotlib figure, always verify critical X and Y edges programmatically against the raw NumPy grayscale array (np.where(gray < thresh)) so layout padding does not introduce coordinate offsets.
Inverted Y-axis in AutoCAD: Image coordinates have Y=0 at the top, whereas AutoCAD has Y=0 at the bottom. Always transform y_cad = H - y_img when writing DXF entities


## Runtime and accuracy requirements

Use the existing project checkout; do not create a Git worktree unless requested. Check availability of Python, OpenCV, NumPy, Matplotlib, Cairo, and pypdfium2 before use; install needed dependencies in an isolated environment when permitted. Use view_image for local image inspection when available, or an equivalent available image viewer.

This skill produces DXF and PDF. Native DWG export requires a separately available, verified converter; do not rename DXF to DWG. Ask for a known dimension when real-world scale is required but cannot be inferred. Otherwise disclose that coordinates use image units. Do not invent unreadable dimensions, labels, or structural details; identify uncertain reconstruction and any simplified entourage. Sub-pixel estimates do not establish survey accuracy.
