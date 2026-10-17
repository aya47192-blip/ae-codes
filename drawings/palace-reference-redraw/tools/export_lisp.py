from pathlib import Path
import json
BASE=Path('/workspace/palace_reference');OUT=BASE/'output'
data=json.loads((OUT/'geometry_mm.json').read_text())
header=r'''; palace_reference_redraw.lsp -- self-contained clean facade reconstruction
; Units: millimetres. Nominal facade width: 14000 (ESTIMATED, NOT SURVEYED).
; AutoCAD for Windows with Visual LISP/ActiveX. Load with APPLOAD; run PALACE.
; Shared edges occur once. Closed contours may contain connected junction-to-junction chains.
; All visible facade entities: RGB black, physical lineweight 0.18 mm.
; No external DXF, image, Python, network, or package is required to draw this data.
; Native dimension creation uses AutoCAD ActiveX; this environment could not execute AutoCAD.
(vl-load-com)

(defun PALC:emit (data)
  (if (null (entmake data))
    (progn (princ "\nPALACE: AutoCAD rejected an entity; undo this operation if necessary.") (quit))))

(defun PALC:layer (name white / full)
  (setq full (strcat "PALC_" name))
  (if (null (tblsearch "LAYER" full))
    (PALC:emit
      (list '(0 . "LAYER") '(100 . "AcDbSymbolTableRecord")
            '(100 . "AcDbLayerTableRecord") (cons 2 full) '(70 . 0)
            '(62 . 7) '(6 . "Continuous") '(370 . 18)
            (cons 420 (if white 16777215 0)))))
  full)

(defun PALC:poly (row / pts)
  (setq pts (caddr row))
  (PALC:emit
    (append
      (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity")
            (cons 8 (strcat "PALC_" (car row))) '(62 . 7) '(420 . 0) '(370 . 18) '(6 . "Continuous")
            '(100 . "AcDbPolyline") (cons 90 (length pts)) (cons 70 (cadr row))
            '(38 . 0.0) '(43 . 0.0))
      (mapcar '(lambda (p) (cons 10 p)) pts))))

(defun PALC:build (name / row)
  (PALC:emit
    (list '(0 . "BLOCK") '(100 . "AcDbEntity") '(8 . "0")
          '(100 . "AcDbBlockBegin") (cons 2 name) '(70 . 0) '(10 0.0 0.0 0.0) (cons 3 name) '(1 . "")))
  (PALC:emit
    (list '(0 . "SOLID") '(100 . "AcDbEntity") '(8 . "PALC_00_WHITE_BACKGROUND")
          '(62 . 7) '(420 . 16777215) '(370 . 18) '(100 . "AcDbTrace")
          '(10 -2000.0 -1200.0 0.0) '(11 16000.0 -1200.0 0.0)
          '(12 -2000.0 12410.687 0.0) '(13 16000.0 12410.687 0.0)))
  (foreach row PALC:DATA (PALC:poly row))
  (PALC:emit '((0 . "ENDBLK") (100 . "AcDbEntity") (8 . "0") (100 . "AcDbBlockEnd"))))

(defun PALC:point (xy base factor)
  (list (+ (car base) (* factor (car xy)))
        (+ (cadr base) (* factor (cadr xy))) (caddr base)))

(defun PALC:property (obj name value)
  (if (vlax-property-available-p obj name T)
    (vlax-put-property obj name value)))

(defun PALC:dimension (space row base factor / obj colour)
  (setq obj
    (vla-AddDimRotated space
      (vlax-3d-point (PALC:point (nth 0 row) base factor))
      (vlax-3d-point (PALC:point (nth 1 row) base factor))
      (vlax-3d-point (PALC:point (nth 2 row) base factor))
      (nth 3 row)))
  (vla-put-Layer obj "PALC_09_ESTIMATED_DIMS")
  (vla-put-Lineweight obj 18)
  (setq colour (vla-get-TrueColor obj))
  (vla-SetRGB colour 0 0 0)
  (vla-put-TrueColor obj colour)
  (vlax-release-object colour)
  (foreach item
    (list (cons 'TextHeight (* factor 145.0))
          (cons 'ArrowheadSize (* factor 100.0))
          (cons 'ExtensionLineOffset (* factor 75.0))
          (cons 'ExtensionLineExtend (* factor 65.0))
          (cons 'DimensionLineWeight 18) (cons 'ExtensionLineWeight 18)
          (cons 'DimensionLineColor 0) (cons 'ExtensionLineColor 0) (cons 'TextColor 0)
          (cons 'PrimaryUnitsPrecision 0) (cons 'LinearScaleFactor 1.0) (cons 'ScaleFactor 1.0)
          (cons 'Arrowhead1Type 0) (cons 'Arrowhead2Type 0)
          (cons 'DimLine1Suppress 0) (cons 'DimLine2Suppress 0)
          (cons 'ExtLine1Suppress 0) (cons 'ExtLine2Suppress 0)
          (cons 'DimensionLinetype "Continuous") (cons 'ExtLine1Linetype "Continuous") (cons 'ExtLine2Linetype "Continuous")
          (cons 'UnitsFormat 2) (cons 'TextOverride "<> mm (est.)"))
    (PALC:property obj (car item) (cdr item)))
  (vla-Update obj)
  (vlax-vla-object->ename obj))

(defun PALC:dimensions (record / acad doc space row old result base factor)
  (setq acad (vlax-get-acad-object) doc (vla-get-ActiveDocument acad)
        space (vla-get-ModelSpace doc) base (cadr record) factor (caddr record))
  ; Re-running PALACEDIMS replaces only dimensions tracked for this last insertion.
  (foreach old (cadddr record) (if (entget old) (entdel old)))
  (setq result nil)
  (foreach row PALC:DIMS
    (setq result (cons (PALC:dimension space row base factor) result)))
  (list (car record) base factor (reverse result)))

(defun c:PALACE (/ *error* acad doc mark base factor width name count entity oldlast dims row)
  (setq acad (vlax-get-acad-object) doc (vla-get-ActiveDocument acad)
        oldlast PALC:LAST mark nil entity nil)
  (defun *error* (message)
    (if mark (vl-catch-all-apply 'vla-EndUndoMark (list doc)))
    (setq PALC:LAST oldlast)
    (if (not (wcmatch (strcase message) "*CANCEL*,*QUIT*,*BREAK*"))
      (princ (strcat "\nPALACE error: " message)))
    (princ "\nIf an operation was interrupted, UNDO once removes its new drawing objects.")
    (princ))
  (princ "\nPALACE: estimated geometry in mm. Recommended: use a new blank drawing.")
  (setq base (getpoint "\nPick the ground-datum insertion point: "))
  (if base
    (progn
      (setq base (trans base 1 0))
      (initget 6)
      (setq width (getdist "\nEstimated overall facade width in mm <14000>: "))
      (if (null width) (setq width 14000.0))
      (setq factor (/ width 14000.0))
      (vla-StartUndoMark doc) (setq mark T)
      (PALC:layer "00_WHITE_BACKGROUND" T)
      (foreach row PALC:LAYERS (PALC:layer row nil))
      (PALC:layer "09_ESTIMATED_DIMS" nil)
      (setq name (strcat "PALC_CLEAN_" (itoa (getvar "MILLISECS"))) count 0)
      (while (tblsearch "BLOCK" name)
        (setq count (1+ count) name (strcat name "_" (itoa count))))
      (PALC:build name)
      (setq entity
        (entmakex
          (list '(0 . "INSERT") '(100 . "AcDbEntity") '(8 . "PALC_01_STRUCTURE")
                '(62 . 7) '(420 . 0) '(370 . 18) '(100 . "AcDbBlockReference")
                (cons 2 name) (cons 10 base) (cons 41 factor) (cons 42 factor)
                (cons 43 factor) '(50 . 0.0))))
      (if (null entity) (progn (princ "\nUnable to insert facade block.") (quit)))
      (setq PALC:LAST (list entity base factor nil))
      (setvar "INSUNITS" 4) (setvar "LWDISPLAY" 1) (setvar "FILLMODE" 1)
      (initget "Yes No")
      (setq dims (getkword "\nAdd estimated overall dimensions? [Yes/No] <Yes>: "))
      (if (not (equal dims "No")) (setq PALC:LAST (PALC:dimensions PALC:LAST)))
      (vla-Regen doc 1)
      (vl-catch-all-apply 'vla-ZoomWindow
        (list acad
          (vlax-3d-point (PALC:point '(-2000.0 -1200.0) base factor))
          (vlax-3d-point (PALC:point '(16000.0 12410.687) base factor))))
      (vla-EndUndoMark doc) (setq mark nil)
      (princ (strcat "\nFacade complete. Estimated width: " (rtos width 2 0)
                     " mm; estimated height: " (rtos (* factor 10610.687) 2 0)
                     " mm. One UNDO removes this insertion and its dimensions."))))
  (princ))

(defun c:PALACEDIMS (/ *error* doc mark)
  (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)) mark nil)
  (defun *error* (message)
    (if mark (vl-catch-all-apply 'vla-EndUndoMark (list doc)))
    (princ (strcat "\nDimension command stopped: " message)) (princ))
  (if (and PALC:LAST (entget (car PALC:LAST)))
    (progn (vla-StartUndoMark doc) (setq mark T)
      (setq PALC:LAST (PALC:dimensions PALC:LAST))
      (vla-Regen doc 1) (vla-EndUndoMark doc) (setq mark nil)
      (princ "\nEstimated dimensions updated for the last facade insertion."))
    (princ "\nRun PALACE first."))
  (princ))

(defun c:PALACEINFO ()
  (princ "\nPALACE = draw self-contained facade; PALACEDIMS = native overall dimensions.")
  (princ "\nUnits are mm. Default estimated width 14000 mm; height 10610.687 mm.")
  (princ "\nBlack outlines 0.18 mm. Shared edges once, no loose ends; intentional joints remain.")
  (princ "\nThe reference is visually reconstructed; dimensions are estimated, not surveyed.")
  (princ))

(setq PALC:LAST nil)
(setq PALC:LAYERS
  '("01_STRUCTURE" "02_CORNICES" "03_FRAMES_DOORS" "04_GLAZING_SHUTTERS"
    "05_STONE_JOINTS" "06_ORNAMENT" "07_RAILINGS" "08_STEPS"))
'''
# Localize the property loop variable to avoid leaking state into an existing user's session.
header=header.replace('(defun PALC:dimension (space row base factor / obj colour)', '(defun PALC:dimension (space row base factor / obj colour item)')
def num(v):
 s=f'{v:.4f}'.rstrip('0').rstrip('.')
 return s if '.' in s else s+'.0'
header+=r'''
(defun c:PALACESIZES (/ factor row width height)
  (setq factor (if PALC:LAST (caddr PALC:LAST) 1.0))
  (princ "\nEstimated dimensions in mm, scaled for the last insertion:")
  (foreach row PALC:SIZES
    (setq width (cadr row) height (caddr row))
    (princ (strcat "\n" (car row)
      (if width (strcat " | width=" (rtos (* factor width) 2 0)) "")
      (if height (strcat " | height/level=" (rtos (* factor height) 2 0)) ""))))
  (princ))
'''
# Preserve the complete reference canvas and caption in the self-contained block.
a,b,c,d=data['paper_bounds_mm'];title=data['title'];px,py=title['insert']
for old,new in [('-2000.0',num(a)),('-1200.0',num(b)),('16000.0',num(c)),('12410.687',num(d))]:header=header.replace(old,new)
header=header.replace('"07_RAILINGS" "08_STEPS"','"07_RAILINGS" "08_STEPS" "10_REFERENCE_TITLE"')
header=header.replace('[Yes/No] <Yes>:', '[Yes/No] <No>:')
header=header.replace('(if (not (equal dims "No"))','(if (equal dims "Yes")')
header=header.replace('(PALC:build name)','(PALC:title-style)\n      (PALC:build name)')
header+=r'''
(defun PALC:title-style ()
  (if (null (tblsearch "STYLE" "PALC_REFERENCE_ARIAL"))
    (PALC:emit
      '((0 . "STYLE") (100 . "AcDbSymbolTableRecord") (100 . "AcDbTextStyleTableRecord")
        (2 . "PALC_REFERENCE_ARIAL") (70 . 0) (40 . 0.0) (41 . 1.0) (50 . 0.0)
        (71 . 0) (42 . 0.0) (3 . "arial.ttf") (4 . "")))))
'''
text_record=f'''  (PALC:emit
    '((0 . "TEXT") (100 . "AcDbEntity") (8 . "PALC_10_REFERENCE_TITLE")
      (62 . 7) (420 . 0) (370 . 18) (100 . "AcDbText")
      (10 {num(px)} {num(py)} 0.0) (40 . {num(title['height_mm'])})
      (1 . "Modern Islamic Commercial Elevation") (50 . 0.0) (41 . 1.0)
      (7 . "PALC_REFERENCE_ARIAL") (72 . 1) (11 {num(px)} {num(py)} 0.0)
      (100 . "AcDbText") (73 . 0)))
'''
header=header.replace('  (PALC:emit \'((0 . "ENDBLK")',text_record+'  (PALC:emit \'((0 . "ENDBLK")')

text=header+'\n(setq PALC:DIMS\n  \'(\n'
for d in data['dimensions']:
 pts=' '.join('('+num(p[0])+' '+num(p[1])+')' for p in [d['p1'],d['p2'],d['base']])
 text+='    ('+pts+' '+format(d['angle']*3.141592653589793/180,'.15f')+')\n'
text+='  ))\n\n; Each row: (layer closed-flag ((x y) ...)), in nominal estimated millimetres.\n(setq PALC:DATA\n  \'(\n'
for index,p in enumerate(data['paths'],1):
 text+=f'    ; P{index:04d} -- see feature_dimensions_mm.csv\n'
 text+=f'    ("{p["layer"]}" {1 if p["closed"] else 0} (\n'
 pairs=['('+num(x)+' '+num(y)+')' for x,y in p['points']]
 for start in range(0,len(pairs),5):text+='      '+' '.join(pairs[start:start+5])+'\n'
 text+='    ))\n'
text+='  ))\n(princ "\\nClean facade loaded. Type PALACE to draw, or PALACEINFO for help.")\n(princ)\n'
import csv
size_rows=list(csv.DictReader((OUT/'estimated_dimensions_mm.csv').open()))
size_data='\n(setq PALC:SIZES \'(\n'
for row in size_rows:
 w=row['estimated_width_mm'];h=row['estimated_height_or_level_mm']
 size_data+='  ("'+row['id']+'" '+(w if w else 'nil')+' '+(h if h else 'nil')+')\n'
size_data+='))\n'
text+=size_data
(OUT/'palace_reference_redraw.lsp').write_text(text,encoding='ascii')
print('AutoLISP written:',len(data['paths']),'embedded paths;',len(text),'bytes.')
