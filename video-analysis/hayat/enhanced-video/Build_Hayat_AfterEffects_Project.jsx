/* Run in Adobe After Effects: File > Scripts > Run Script File.
   This script creates and saves a native AEP on the user's machine.
   It is a project builder, NOT a pre-saved AEP or an element-layer animation project. */
(function () {
    var root = new File($.fileName).parent;
    var sourceFile = new File(root.fsName + '/media/Source_Original.mp4');
    var finalFile = new File(root.fsName + '/media/Hayat_Enhanced_Cropped.mp4');
    if (!sourceFile.exists || !finalFile.exists) {
        alert('Extract the complete ZIP first. Keep this JSX beside the media folder.\nMissing: ' + (!sourceFile.exists ? sourceFile.fsName : finalFile.fsName));
        return;
    }
    var undoOpen = false;
    try {
        // newProject uses After Effects' normal save/cancel handling for existing work.
        var project = app.newProject();
        if (!project) { return; }
        app.beginUndoGroup('Build Hayat color-edit project'); undoOpen = true;
        project.bitsPerChannel = 16;
        var mediaFolder = project.items.addFolder('01_MEDIA');
        var compsFolder = project.items.addFolder('02_COMPOSITIONS');
        var original = project.importFile(new ImportOptions(sourceFile));
        original.name = 'SOURCE_original_uncropped'; original.parentFolder = mediaFolder;
        var enhanced = project.importFile(new ImportOptions(finalFile));
        enhanced.name = 'FINAL_enhanced_cropped'; enhanced.parentFolder = mediaFolder;
        var fps = 30;
        var duration = 4169 / fps;
        var warnings = [];
        function createComp(name, w, h) {
            var c = project.items.addComp(name, w, h, 1, duration, fps);
            c.parentFolder = compsFolder;
            c.displayStartTime = 0;
            c.bgColor = [0, 0, 0];
            return c;
        }
        function transform(layer, anchor, position, scale) {
            var tr = layer.property('ADBE Transform Group');
            tr.property('ADBE Anchor Point').setValue(anchor);
            tr.property('ADBE Position').setValue(position);
            tr.property('ADBE Scale').setValue(scale);
        }
        function addControls(comp, label) {
            var adjustment = comp.layers.addSolid([1, 1, 1], label, comp.width, comp.height, 1, duration);
            adjustment.adjustmentLayer = true; adjustment.label = 9;
            var effects = adjustment.property('ADBE Effect Parade');
            var entries = [
                ['ADBE Exposure2', 'Exposure - additional editable correction'],
                ['ADBE HUE SATURATION', 'Hue Saturation - additional editable correction'],
                ['ADBE Brightness & Contrast 2', 'Brightness Contrast - additional editable correction']
            ];
            for (var i = 0; i < entries.length; i++) {
                try { var effect = effects.addProperty(entries[i][0]); effect.name = entries[i][1]; }
                catch (effectError) { warnings.push(entries[i][0]); }
            }
            // Native effects start at their neutral defaults. No look is silently added.
            adjustment.comment = 'Neutral editable controls. In FINAL the approved enhancement is already in the MP4. Use SOURCE_EDIT for a fresh grade from the original.';
            return adjustment;
        }
        var nativeCrop = createComp('SOURCE_CROP_NATIVE_576x316', 576, 316);
        var sourceLayer = nativeCrop.layers.add(original);
        sourceLayer.name = 'Original video - center crop y354 height316';
        // Source: 576x1024. Its center y512 minus crop origin y354 is y158.
        transform(sourceLayer, [288, 512], [288, 158], [100, 100]);
        sourceLayer.inPoint = 0; sourceLayer.outPoint = duration;
        nativeCrop.comment = 'Original media. Non-destructive center crop: x0 y354 width576 height316. No grading baked into this composition.';
        var sourceEdit = createComp('SOURCE_EDIT_FRESH_GRADE_1152x632', 1152, 632);
        var nested = sourceEdit.layers.add(nativeCrop);
        nested.name = 'Original cropped source - 200 percent display scale';
        transform(nested, [288, 158], [576, 316], [200, 200]);
        addControls(sourceEdit, 'EDITABLE_GRADE_STARTS_NEUTRAL');
        sourceEdit.comment = 'Fresh original source for changing the look from scratch. Neutral native effects; this is not a claim to reproduce the delivered FFmpeg curve with AE effects.';
        var main = createComp('FINAL_READY_TO_EDIT_1152x632', 1152, 632);
        var finalLayer = main.layers.add(enhanced);
        finalLayer.name = 'Enhanced final MP4 - audio preserved';
        transform(finalLayer, [enhanced.width / 2, enhanced.height / 2], [576, 316], [115200 / enhanced.width, 63200 / enhanced.height]);
        finalLayer.inPoint = 0; finalLayer.outPoint = duration;
        addControls(main, 'ADDITIONAL_EDITABLE_CORRECTIONS');
        main.comment = 'Exact delivered MP4 as footage. Existing enhancement is baked into this video; the adjustment effects above it are neutral and editable. Add text, cuts, transitions or further correction here. SOURCE_EDIT keeps the original available separately.';
        var comparison = createComp('COMPARE_ORIGINAL_LEFT_FINAL_RIGHT', 2304, 632);
        var left = comparison.layers.add(nativeCrop); left.name = 'LEFT - original cropped'; left.audioEnabled = false;
        transform(left, [288, 158], [576, 316], [200, 200]);
        var right = comparison.layers.add(enhanced); right.name = 'RIGHT - enhanced';
        transform(right, [enhanced.width / 2, enhanced.height / 2], [1728, 316], [115200 / enhanced.width, 63200 / enhanced.height]);
        var beats = [
            [0, 'Opening'], [25.8, 'Color transition'], [43.5, 'House and passage of time'],
            [58.5, 'Reaction and running'], [67.9, 'At the stump'], [87.5, 'Reading'],
            [96.5, 'Watering and growth'], [119.9, 'Cat'], [124.1, 'Closing wide shot'], [128.7, 'Credits']
        ];
        if (main.markerProperty) {
            for (var b = 0; b < beats.length; b++) {
                main.markerProperty.setValueAtTime(beats[b][0], new MarkerValue(beats[b][1] + ' (approx.)'));
            }
        }
        main.openInViewer();
        var projectFile = new File(root.fsName + '/Hayat_Color_Edit.aep');
        var suffix = 2;
        while (projectFile.exists) {
            projectFile = new File(root.fsName + '/Hayat_Color_Edit_' + suffix + '.aep'); suffix++;
        }
        project.save(projectFile);
        app.endUndoGroup(); undoOpen = false;
        alert('Native After Effects project created:\n' + projectFile.fsName + '\n\nUse FINAL_READY_TO_EDIT for the delivered look. SOURCE_EDIT keeps the original available for a fresh grade.' + (warnings.length ? '\nOptional effects unavailable in this AE version: ' + warnings.join(', ') : ''));
    } catch (error) {
        if (undoOpen) { try { app.endUndoGroup(); } catch (ignored) {} }
        alert('Project setup did not finish.\n' + error.toString() + '\nLine: ' + error.line + '\nThe MP4 files remain unchanged.');
    }
}());
