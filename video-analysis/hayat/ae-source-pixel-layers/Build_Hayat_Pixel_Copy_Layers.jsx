/* Source-pixel editing regions. No generated art, extracted character layer,
   recoloring, retiming, or reconstruction. The intact source is kept below. */
(function () {
    var root = new File($.fileName).parent;
    var movie = new File(root.fsName + '/Hayat_Restored_TitleOnly_1152x632.mp4');
    if (!movie.exists) { movie = File.openDialog('Choose the FINAL Hayat_Restored_TitleOnly_1152x632.mp4'); }
    if (!movie) { return; }
    var undo = false;
    try {
        var project = app.newProject(); if (!project) { return; }
        app.beginUndoGroup('Build source-pixel background editing layers'); undo = true;
        project.bitsPerChannel = 32;
        // Disable project color conversion rather than introducing a new grade.
        try { project.workingSpace = ''; } catch (ignored) {}
        var footage = project.importFile(new ImportOptions(movie));
        footage.name = 'FINAL_VIDEO_UNCHANGED';
        var W = footage.width, H = footage.height, fps = 30, duration = 3861 / 30;
        if (W !== 1152 || H !== 632 || Math.abs(footage.duration-duration)>0.1 || movie.length!==12575785) { throw new Error('Select the exact 1152x632 final movie from this package (128.7 seconds).'); }
        var folder = project.items.addFolder('SOURCE_PIXEL_WORKSPACES');
        function makeComp(name) {
            var c = project.items.addComp(name, W, H, 1, duration, fps);
            c.parentFolder = folder; c.bgColor = [0,0,0]; c.displayStartTime = 0;
            c.motionBlur = false; c.frameBlending = false;
            return c;
        }
        function identity(layer) {
            layer.startTime = 0; layer.stretch = 100;
            var tr = layer.property('ADBE Transform Group');
            tr.property('ADBE Anchor Point').setValue([W/2,H/2]);
            tr.property('ADBE Position').setValue([W/2,H/2]);
            tr.property('ADBE Scale').setValue([100,100]);
            tr.property('ADBE Rotate Z').setValue(0);
            tr.property('ADBE Opacity').setValue(100);
            layer.blendingMode = BlendingMode.NORMAL;
            layer.motionBlur = false;
            try { layer.frameBlendingType = FrameBlendingType.NO_FRAME_BLEND; } catch (ignored) {}
        }
        var edit = makeComp('01_EDIT_SOURCE_PIXEL_REGIONS__ORIGINAL_BASE_RETAINED');
        var base = edit.layers.add(footage); identity(base);
        base.name = 'BASE_INTACT_FINAL_VIDEO__LOCKED'; base.locked = true;
        base.comment = 'Unmodified final movie. Includes the girl and every original visible object. This full base deliberately remains intact. Hiding an overlay reveals the same object in this base; it does NOT remove an object from the film.';
        var overlays = [];
        function addRegion(name, start, end, vertices, note) {
            var layer = edit.layers.add(footage); identity(layer);
            layer.name = name;
            layer.inPoint = Math.round(start*fps)/fps;
            layer.outPoint = Math.round(end*fps)/fps;
            layer.audioEnabled = false; layer.label = 9;
            if (vertices) {
                var mask = layer.property('ADBE Mask Parade').addProperty('ADBE Mask Atom');
                mask.name = 'Source pixel editing area - no feather or expansion';
                mask.maskMode = MaskMode.ADD;
                var sh = new Shape(); sh.vertices = vertices;
                var tangents = [];
                for (var i=0; i<vertices.length; i++) { tangents.push([0,0]); }
                sh.inTangents = tangents; sh.outTangents = tangents; sh.closed = true;
                mask.property('ADBE Mask Shape').setValue(sh);
                mask.property('ADBE Mask Feather').setValue([0,0]);
                var expansion = mask.property('ADBE Mask Offset');
                if (expansion) { expansion.setValue(0); }
                mask.property('ADBE Mask Opacity').setValue(100);
            }
            layer.comment = note + ' This is a same-frame source-video region, not recovered original illustration layers. Original base remains underneath.';
            overlays.push(layer); return layer;
        }
        function rect(x0,y0,x1,y1) { return [[2*x0,2*y0],[2*x1,2*y0],[2*x1,2*y1],[2*x0,2*y1]]; }
        addRegion('BG_01_TREE_ESTABLISHING__NO_CHARACTERS',7.5,11.3,null,
            'Complete background-only interval. Camera movement and all source colors stay in the movie pixels.');
        addRegion('BG_02_HOUSE_EXTERIOR__NO_CHARACTERS',46,56.2,null,
            'Complete background-only house scene. Original day/night lighting changes are retained.');
        addRegion('BG_03_CAT_SCENE_LEFT_EMPTY_GROUND',35,38.6,rect(0,0,145,316),
            'Only the empty ground at the left edge of this shot; not the cat or shoes.');
        addRegion('BG_04_WATERING_LEFT_FIELD',97,113.3,rect(0,0,150,316),
            'Left background field during the watering scene. Hand and stump remain in the intact original.');
        addRegion('BG_05_WATERING_FAR_RIGHT_FIELD',97,113.3,rect(510,0,576,316),
            'Far-right background field. This is an editing area, not an isolated illustrated object.');
        var houseNative = [[73,51],[92,43],[114,49],[115,61],[110,64],[109,72],[151,58],
            [169,60],[227,69],[240,88],[233,89],[232,112],[242,115],[241,188],
            [113,199],[49,185],[49,135],[35,138],[49,115],[73,111],[74,84]];
        var house = [];
        for (var h=0;h<houseNative.length;h++) { house.push([2*houseNative[h][0],2*houseNative[h][1]]); }
        addRegion('STATIC_HOUSE_END_WIDE__VISIBLE_SOURCE_REGION',124.5,128.7,house,
            'Visible house area in the final wide shot, sampled from the same movie. No painted reconstruction behind or around it.');
        addRegion('BG_06_END_WIDE_LEFT_GROUND_AND_GRASS',124.5,128.7,rect(0,203,270,316),
            'Ground and grass on the left of the closing wide shot. No girl layer is isolated.');
        edit.comment = 'Editing regions only. No girl extraction, scene regeneration or semantic rebuilding. With the intact base and unmodified same-frame copies, default composition is the same video. Hiding overlays reveals the original base, so it does NOT make the background or house disappear. Further edits intentionally change the result.';
        var reference = makeComp('02_ORIGINAL_FINAL_VIDEO_REFERENCE');
        var rl = reference.layers.add(footage); identity(rl); rl.name = 'Original final movie reference';
        var check = makeComp('03_CHECK_DIFFERENCE__BLACK_IS_EXPECTED');
        var refLayer = check.layers.add(reference); refLayer.audioEnabled = false;
        var result = check.layers.add(edit); result.name = 'EDITED_MINUS_REFERENCE';
        result.audioEnabled = false; result.blendingMode = BlendingMode.DIFFERENCE;
        check.comment = 'Should render black when overlays have no edits. This compares the entire rendered frame against the reference inside YOUR After Effects. This workspace was not executed in AE by the author.';
        // Ask AE to evaluate representative full-frame difference samples locally.
        // A null does not render into the image. The slider evaluates an AE expression.
        var report = 'AE runtime comparison not evaluated.';
        try {
            var qaHost = makeComp('04_RUNTIME_QA_PROBE');
            var diffView = qaHost.layers.add(check); diffView.name = 'FINAL_DIFFERENCE_OUTPUT'; diffView.audioEnabled = false;
            var probe = qaHost.layers.addNull(duration); probe.name = 'QA_PROBE__DOES_NOT_RENDER';
            var slider = probe.property('ADBE Effect Parade').addProperty('ADBE Slider Control').property(1);
            slider.expression = "var d=thisComp.layer('FINAL_DIFFERENCE_OUTPUT').sampleImage([thisComp.width/2,thisComp.height/2],[thisComp.width/2,thisComp.height/2],true,time); Math.max(d[0],d[1],d[2])*255;";
            var times = [0,8,36,47,52,99,105,126,128];
            var maxDiff = 0, values = [];
            for (var t=0;t<times.length;t++) {
                var value = slider.valueAtTime(times[t],false);
                maxDiff = Math.max(maxDiff,value); values.push(times[t]+'s: '+value);
            }
            report = 'Representative full-frame mean absolute RGB differences (0-255):\n'+values.join('\n');
            if (maxDiff > 0.0001) {
                // Safety fallback: keep overlay layers available but disable them.
                // The intact movie stays visible, preventing a changed default final.
                for (var k=0;k<overlays.length;k++) { overlays[k].enabled = false; }
                report += '\nNonzero comparison detected. Editing overlays were disabled; original base remains visible. Inspect differences before enabling them.';
            } else { report += '\nRepresentative checks passed. Inspect the Difference composition across the timeline before rendering.'; }
            probe.comment = report;
        } catch (qaError) { report += '\nAutomatic sample check unavailable: '+qaError.toString()+'\nInspect the Difference composition manually.'; }
        check.comment += '\n'+report;
        edit.openInViewer();
        var dest = new File(root.fsName+'/Hayat_Source_Pixel_Regions.aep'); var suffix = 2;
        while(dest.exists) { dest = new File(root.fsName+'/Hayat_Source_Pixel_Regions_'+suffix+'.aep'); suffix++; }
        project.save(dest);
        app.endUndoGroup(); undo=false;
        alert('AEP created: '+dest.fsName+'\n\n'+report+'\n\nImportant: these are editing overlays above the intact video. Hiding an overlay does not erase the object from the base.');
    } catch(error) {
        if(undo) { try { app.endUndoGroup(); } catch(ignored) {} }
        alert('Setup did not finish: '+error.toString()+'\nLine '+error.line);
    }
}());
