import os
from pathlib import Path
import json,textwrap,hashlib
ROOT=Path(__file__).parent;OUT=Path(os.environ.get('FACADE_OUTPUT',str(ROOT/'output')))
data=json.loads((OUT/'geometry_pixels.json').read_text()); mm=data['mm_per_pixel']
rows=[]
for p in data['paths']:
 points=[(round((x-1)*mm,5),round((832-y)*mm,5)) for x,y in p['points']]
 coords=' '.join(f'({x:.5f} {y:.5f})' for x,y in points)
 rows.append(f'("SF_{p["layer"]}" {int(p["closed"])} ({coords}))')
layers=sorted({'SF_'+p['layer'] for p in data['paths']})
geomhash=hashlib.sha256((OUT/'geometry_pixels.json').read_bytes()).hexdigest()[:10]
text='''; Source-driven sustainable facade. Units: estimated millimetres.
; Load with APPLOAD, run SUSTAIN. Geometry is embedded; no external files.
; Not a native AutoCAD runtime certification. No 100-percent fidelity claim.
(setq SF:DATA '(\n'''
text+='\n'.join('\n'.join(textwrap.wrap(row,width=120,break_long_words=False,break_on_hyphens=False)) for row in rows)
text+='\n))\n'
text+='(setq SF:LAYERS \'('+ ' '.join('"'+s+'"' for s in layers)+'))\n'
text+='(setq SF:BLOCK "SF_REFERENCE_'+geomhash.upper()+'")\n'
text+='''
(defun SF:POLY (row / pts)
  (setq pts (caddr row))
  (entmake
    (append
      (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity")
            (cons 8 (car row)) '(6 . "Continuous") '(62 . 7)
            '(420 . 0) '(370 . 13) '(100 . "AcDbPolyline")
            (cons 90 (length pts)) (cons 70 (cadr row)) '(43 . 0.0))
      (mapcar '(lambda (pt) (cons 10 pt)) pts))))
(defun SF:BUILD (name / row)
  (entmake (list '(0 . "BLOCK") '(100 . "AcDbEntity") '(8 . "0")
    '(100 . "AcDbBlockBegin") (cons 2 name) '(70 . 0)
    '(10 0.0 0.0 0.0) (cons 3 name) '(1 . "")))
  (foreach row SF:DATA (SF:POLY row))
  (entmake '((0 . "ENDBLK") (100 . "AcDbEntity") (8 . "0")
    (100 . "AcDbBlockEnd"))))
(defun c:SUSTAIN (/ pt width fac name)
  (setq pt (getpoint "\\nChoose insertion point: "))
  (if pt
    (progn
      (initget 6)
      (setq width (getreal "\\nEstimated baseline width in mm <20000>: "))
      (if (null width) (setq width 20000.0))
      (setq fac (/ width 20000.0))
      (foreach name SF:LAYERS
        (if (null (tblsearch "LAYER" name))
          (entmake (list '(0 . "LAYER") '(100 . "AcDbSymbolTableRecord")
            '(100 . "AcDbLayerTableRecord") (cons 2 name) '(70 . 0)
            '(62 . 7) '(420 . 0) '(6 . "Continuous") '(370 . 13)))))
      (if (null (tblsearch "BLOCK" SF:BLOCK)) (SF:BUILD SF:BLOCK))
      (entmake (list '(0 . "INSERT") '(100 . "AcDbEntity") '(8 . "0")
        '(100 . "AcDbBlockReference") (cons 2 SF:BLOCK)
        (cons 10 (trans pt 1 0)) (cons 41 fac) (cons 42 fac)
        (cons 43 fac) '(50 . 0.0)))
      (princ "\\nInserted source-traced facade. EXPLODE for individual editable paths.")
      (princ "\\nBlack linework: use a white model-space background. Dimensions are estimated.")))
  (princ))
(princ "\\nLoaded sustainable facade. Run SUSTAIN.")
(princ)
'''
(OUT/'sustainable_facade.lsp').write_text(text,encoding='ascii')
print('AutoLISP',len(rows),'paths',len(text),'bytes')
