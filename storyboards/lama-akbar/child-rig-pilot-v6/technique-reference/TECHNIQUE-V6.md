# Approved front-pilot technique — v6

User approved the visible v6 child diagnostic on 2026-11-05. Preserve this as the baseline; later model-sheet views require separate visual approval before rigging. Approval of this pilot does not establish native AE execution or guarantee zero defects for new views.

Preserve character identity, textured illustrated finish, palette and outfit. Keep one physical painted occurrence of each limb part; no full-body image underneath moving anatomy. Separate complete head skin and facial features; hide tests must reveal intact underpainting, including all lashes owned by eyes rather than glasses.

The basic torso is an opaque modest peach top; shorts are fabric only with no attached skin. Torso row connectivity removes detached hair/skin slivers. Bare feet contain no socks; leather shoes contain no baked sock paint. Clothing and skin use matching bone pivots.

Limb masks center at actual pivots. Adjacent upper-arm/forearm joint radius is 43 source pixels; thigh/shin knee radius is 50. Distal cap overlaps are faded only over their matching proximal underlap. Reuse generated paint texture inside masks; these are reconstructed raster assets, not recovered original brush history.

The blouse torso is newly painted without any sleeve fragments. Each full sleeve derives from one continuous shoulder-to-cuff painting, split at its elbow with local overlap, not two puff sleeve drawings. Blouse_SidePanels is a disjoint remainder of complete torso fabric, with no duplicated torso pixels. In the AE/local dress outfit it is occluded while Dress_Bib_Straps is visible; when dress is off the full blouse is exposed. The PSD keeps full side fabric available; import/setup should use the documented AE wardrobe logic.

Socks use front cuff paint without the opaque hollow oval/back rim. Calf and sock-foot share only a radius-25 ankle overlap. One pair of stockings and one pair of shoes, separate from skin.

The 360 frame/30fps diagnostic, 15 pivots and authored poses were retained from v5. Preserve its motion and timing unless specifically asked to change them. Required checks for each new view: isolated parts, wardrobe hide/show, feature hide/show, rest and compound extremes, actual vacated-limb regions, foot contact, frame comparisons, PSD independent reopening and full MP4 decoding. New artwork requires visual inspection; numerical uniqueness alone is insufficient.

Actual evidence: GIMP PSD save/reopen, psd-tools reading, selected local Pillow FK frames, local decoded H264. After Effects and native Photoshop were not executed. AE Builder is JSX+PNG, not a saved AEP. Production gate remains pending native AE and final visual approval. Do not promote a local diagnostic to native/render-verified production film.

Durable GitHub baseline commit: 07a0ca887da8f3f4a909e1ca4bbfb5f6f901b170
Directory: storyboards/lama-akbar/child-rig-pilot-v6
