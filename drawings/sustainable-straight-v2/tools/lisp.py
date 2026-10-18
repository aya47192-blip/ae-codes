import os
from pathlib import Path
import json,math,textwrap,hashlib
import ezdxf
ROOT=Path(__file__).parent;OUT=Path(os.environ.get('FACADE_OUTPUT',str(ROOT/'output')));d=ezdxf.readfile(OUT/'facade_straight.dxf')
def num(x):return f'{float(x):.10f}'.rstrip('0').rstrip('.') if float(x)!=0 else '0.0'
def pair(k,v):
 if isinstance(v,str):return f'({k} . "{v}")'
 if isinstance(v,(tuple,list)) or hasattr(v,'__iter__'):return '('+str(k)+' '+' '.join(num(x) for x in v)+')'
 return f'({k} . {str(v) if isinstance(v,int) else num(v)})'
rows=[]
for e in d.modelspace():
 kind=e.dxftype();r=[pair(0,kind),'(100 . "AcDbEntity")',pair(8,e.dxf.layer),pair(62,e.dxf.color),'(370 . 13)']
 if kind=='LINE':r+=['(100 . "AcDbLine")',pair(10,e.dxf.start),pair(11,e.dxf.end)]
 elif kind=='ARC':r+=['(100 . "AcDbCircle")',pair(10,e.dxf.center),pair(40,e.dxf.radius),'(100 . "AcDbArc")',pair(50,math.radians(e.dxf.start_angle)),pair(51,math.radians(e.dxf.end_angle))]
 elif kind=='LWPOLYLINE':
  points=[tuple(p[:2]) for p in e.get_points()];r+=['(100 . "AcDbPolyline")',pair(90,len(points)),pair(70,int(e.closed)),'(43 . 0.0)'];r += [pair(10,p) for p in points]
 elif kind=='SPLINE':
  pts=list(e.control_points);knots=list(e.knots)
  r+=['(100 . "AcDbSpline")',pair(70,e.dxf.flags),pair(71,e.dxf.degree),pair(72,len(knots)),pair(73,len(pts)),'(74 . 0)','(42 . 0.0000001)','(43 . 0.0000001)']
  r += [pair(40,k) for k in knots];r += [pair(10,p) for p in pts]
 else:raise ValueError(kind)
 rows.append('('+' '.join(r)+')')
# AutoLISP entmake uses radians for angles, unlike DXF files which store degrees.
block='FACADE2_'+hashlib.sha256((OUT/'scene.json').read_bytes()).hexdigest()[:10].upper()
text='''; Geometric facade repair: genuine LINE and ARC architecture; source-traced planting.
; APPLOAD, then FACADE2. Data is embedded; estimated millimetres.
(setq F2:DATA '(\n'''
text+='\n'.join('\n'.join(textwrap.wrap(s,120,break_long_words=False,break_on_hyphens=False)) for s in rows)+'\n))\n'
text+='(setq F2:LAYERS \'('+' '.join('"'+s+'"' for s in sorted({e.dxf.layer for e in d.modelspace()}))+'))\n'
text+='(setq F2:BLOCK "'+block+'")\n'
text+='''
(defun F2:BUILD (name / row)
  (entmake (list '(0 . "BLOCK") '(100 . "AcDbEntity") '(8 . "0")
    '(100 . "AcDbBlockBegin") (cons 2 name) '(70 . 0)
    '(10 0.0 0.0 0.0) (cons 3 name) '(1 . "")))
  (foreach row F2:DATA (entmake row))
  (entmake '((0 . "ENDBLK") (100 . "AcDbEntity") (8 . "0")
    (100 . "AcDbBlockEnd"))))
(defun c:FACADE2 (/ point width factor name)
  (setq point (getpoint "\\nInsertion point: "))
  (if point
    (progn
      (initget 6)
      (setq width (getreal "\\nEstimated baseline width in millimetres <20000>: "))
      (if (null width) (setq width 20000.0))
      (setq factor (/ width 20000.0))
      (foreach name F2:LAYERS
        (if (null (tblsearch "LAYER" name))
          (entmake (list '(0 . "LAYER") '(100 . "AcDbSymbolTableRecord")
            '(100 . "AcDbLayerTableRecord") (cons 2 name) '(70 . 0)
            (cons 62 (if (= name "PLANTS") 94 7)) '(6 . "Continuous") '(370 . 13)))))
      (if (null (tblsearch "BLOCK" F2:BLOCK)) (F2:BUILD F2:BLOCK))
      (entmake (list '(0 . "INSERT") '(100 . "AcDbEntity") '(8 . "0")
        '(100 . "AcDbBlockReference") (cons 2 F2:BLOCK)
        (cons 10 (trans point 1 0)) (cons 41 factor) (cons 42 factor)
        (cons 43 factor) '(50 . 0.0)))
      (princ "\\nInserted geometric facade. EXPLODE for individual entities.")))
  (princ))
(princ "\\nLoaded. Run FACADE2.")
(princ)
'''
(OUT/'facade_straight.lsp').write_text(text,encoding='ascii');print('LISP records',len(rows),'bytes',len(text))
