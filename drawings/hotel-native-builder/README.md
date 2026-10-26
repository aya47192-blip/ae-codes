**Latest1.2.0:** [Download revised Bohemian V3, Greek Coastal V2 and Modern Alternative](Ayaa_Lobby_Components_v1_2_0.rbz) · [Preview PDF](../hotel-layout-revision-1-2/revised_options_preview.pdf). Includes the original Modern as a fourth menu choice. Reinstall and restart SketchUp.

**Latest:1.1.0 adds Greek Coastal as a third menu option.** [Download the three-option update](Ayaa_Lobby_Components_v1_1_0.rbz) · [Greek Coastal previews](../hotel-greek-coastal/greek_coastal_preview.pdf). New Modern and Bohemian V2 payloads are byte-identical to1.0.1. Reinstall and restart all SketchUp windows.

**Version1.0.1:** fixes the reported `undefined method refresh for UI:Module` error by calling `model.active_view.refresh`. Reinstall this RBZ, close ALL SketchUp windows, and reopen SketchUp before building. Geometry, furniture positions and materials are unchanged.

# SketchUp lobby: one furnished model, independent whole-piece components

[Download Ayaa Lobby extension](Ayaa_Lobby_Components_v1_0_1.rbz)

This RBZ includes both complete layouts: New Modern and latest Bohemian V2. It builds the entire selected lobby in one SketchUp model. Furniture is in the original reference positions. Each chair, sofa, table, counter and fixture is a separate complete top-level component. Users never open individual asset files.

## Installation

1. Download Ayaa_Lobby_Components_v1_0_1.rbz without unzipping it.
2. SketchUp Desktop: Extensions > Extension Manager > Install Extension. Select the RBZ.
3. Open a new model. The default scale figure is allowed.
4. Extensions > Ayaa Lobby > Build NEW MODERN (or BOHEMIAN V2).
5. Wait for completion, then choose where to save the single furnished SKP.

No Ruby Console and no COLLADA importer are used. Geometry is created through SketchUp's native PolygonMesh API. Materials and UV charts are included. Each original geometry is partitioned into UV-consistent surfaces; every input position/UV triangle is retained. Small geometry is constructed enlarged and scaled back to avoid the small-face tolerance. Existing entities are never deleted. The view frames only the newly built lobby.

The extension checks that all expected components exist and checks every component's world bounds against the source within0.1mm before reporting success. A failure aborts the build operation and reports the actual exception. Saving creates a standard native SKP inside SketchUp itself.

## Validation and limits

- Ruby syntax checked with tree-sitter-ruby.
- Modern:160 components,33 complete furniture pieces,1987 source geometry instances,318605 triangles.
- Bohemian V2:239 components,33 complete furniture pieces,2795 source geometry instances,769911 triangles.
- No missing or duplicate source meshes; source position/UV triangle multisets match exactly.
- Matrix/units roundtrip and texture paths verified.
- SketchUp Desktop is unavailable here. The extension has not been run inside SketchUp; native API behavior and installation remain untested on the user's version. This is an RBZ builder, not a prebuilt SKP file.
