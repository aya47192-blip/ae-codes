import os
from pathlib import Path
import sys,json,math,collections,re
import numpy as np,ezdxf,fitz
from scipy.interpolate import splev
from PIL import Image,ImageDraw
ROOT=Path(__file__).parent;OUT=Path(os.environ.get('FACADE_OUTPUT',str(ROOT/'output')));d=ezdxf.readfile(OUT/'facade_straight.dxf');ms=list(d.modelspace());scene=json.loads((OUT/'scene.json').read_text())
audit=d.audit();assert not audit.errors and not audit.fixes
counts=collections.Counter(e.dxftype() for e in ms)
assert all(e.dxftype() in ['LINE','ARC'] for e in ms if e.dxf.layer!='PLANTS')
assert all(e.dxf.lineweight==13 and e.dxf.color==(94 if e.dxf.layer=='PLANTS' else 7) for e in ms)
assert all(e.dxftype()!='IMAGE' for e in ms)
# Test the actual cornice rails at every declared horizontal level.
railchecks=[];MM=scene['mm_per_pixel']
for offset in [0,809]:
 for y in [297,309,315,323,328,338,343,546,572,579,589,593]:
  ycad=(832-y)*MM
  candidates=[e for e in ms if e.dxftype()=='LINE' and 350+offset-1<=e.dxf.start.x/MM+1<=610+offset+1 and abs(e.dxf.start.y-ycad)<1e-5 and abs(e.dxf.end.y-ycad)<1e-5]
  assert candidates,(offset,y)
  assert all(abs(e.dxf.start.y-e.dxf.end.y)<1e-8 for e in candidates)
  railchecks.append({'source_offset_x':offset,'source_y':y,'straight':True})
segments=collections.Counter();small_angle=[];zero=0
for e in ms:
 if e.dxftype()!='LINE':continue
 a=tuple(round(x,7) for x in e.dxf.start);b=tuple(round(x,7) for x in e.dxf.end)
 segments[tuple(sorted([a,b]))]+=1
 dx=abs(a[0]-b[0]);dy=abs(a[1]-b[1]);length=math.hypot(dx,dy)
 zero+=length<1e-6
 if e.dxf.layer in ['ARCH','LOUVERS','MASONRY','WINDOWS'] and length>10*MM:
  angle=math.degrees(math.atan2(min(dx,dy),max(dx,dy)))
  if 1e-5<angle<2:small_angle.append((e.dxf.layer,angle))
assert sum(v-1 for v in segments.values())==0
assert not zero and not small_angle,small_angle
arc_keys=collections.Counter((tuple(round(x,7) for x in e.dxf.center),round(e.dxf.radius,7),round(e.dxf.start_angle,7),round(e.dxf.end_angle,7)) for e in ms if e.dxftype()=='ARC')
assert not any(v>1 for v in arc_keys.values())
# Compare actual native CAD spline evaluation to the shared scene.
plant_entities=[e for e in ms if e.dxf.layer=='PLANTS'];maxdiff=0
assert len(plant_entities)==len(scene['plants'])
for e,c in zip(plant_entities,scene['plants']):
 if c['type']!='spline':continue
 tool=e.construction_tool();u=np.linspace(c['knots'][c['degree']],c['knots'][-c['degree']-1],9)
 expected=np.array(splev(u,(c['knots'],np.array(c['controls']).T,c['degree']))).T
 for t,p in zip(u,expected):
  normalized_t=(float(t)-c['knots'][0])/(c['knots'][-1]-c['knots'][0]);xyz=tool.point(normalized_t);xy=np.array([xyz.x/MM+1,832-xyz.y/MM]);maxdiff=max(maxdiff,float(np.linalg.norm(xy-p)))
assert maxdiff<1e-5,maxdiff
# Parse the actual AutoLISP payload, validating every emitted entity and angle conversion.
class Sym(str):pass
class Pair:
 def __init__(self,a,b):self.a=a;self.b=b
text=(OUT/'facade_straight.lsp').read_text('ascii')
rx=re.compile(r';[^\n]*|"(?:\\.|[^"\\])*"|[()\']|[^\s()\'";]+');tokens=[m.group() for m in rx.finditer(text) if not m.group().startswith(';')];pos=0
def read():
 global pos
 t=tokens[pos];pos+=1
 if t=='(':
  seq=[]
  while tokens[pos]!=')':
   if tokens[pos]=='.':
    pos+=1;tail=read();assert tokens[pos]==')';pos+=1
    for q in reversed(seq):tail=Pair(q,tail)
    return tail
   seq.append(read())
  pos+=1;return seq
 if t==')':raise ValueError('unmatched )')
 if t=="'":return [Sym('QUOTE'),read()]
 if t.startswith('"'):return json.loads(t)
 try:return float(t) if any(c in t for c in '.eE') else int(t)
 except ValueError:return Sym(t.upper())
forms=[]
while pos<len(tokens):forms.append(read())
rows=next(f[2][1] for f in forms if isinstance(f,list) and len(f)==3 and f[0]==Sym('SETQ') and f[1]==Sym('F2:DATA'))
assert len(rows)==len(ms)
def get(row,key):
 r=[]
 for item in row:
  if isinstance(item,Pair) and item.a==key:r.append(item.b)
  elif isinstance(item,list) and item[0]==key:r.append(item[1:])
 return r
for row,e in zip(rows,ms):
 assert get(row,0)==[e.dxftype()] and get(row,8)==[e.dxf.layer]
 assert get(row,370)==[13] and get(row,62)==[94 if e.dxf.layer=='PLANTS' else 7]
 for code in [62,70,71,72,73,74,90,370]:assert all(type(v) is int for v in get(row,code)),(code,get(row,code))
 if e.dxftype()=='LINE':
  assert math.dist(get(row,10)[0],e.dxf.start)<1e-8 and math.dist(get(row,11)[0],e.dxf.end)<1e-8
 elif e.dxftype()=='ARC':
  assert abs(get(row,50)[0]-math.radians(e.dxf.start_angle))<1e-9
  assert abs(get(row,51)[0]-math.radians(e.dxf.end_angle))<1e-9
  assert math.dist(get(row,10)[0],e.dxf.center)<1e-8
 elif e.dxftype()=='SPLINE':
  assert get(row,71)==[e.dxf.degree]
  assert np.max(np.abs(np.array(get(row,40))-np.array(e.knots)))<1e-9
  assert np.max(np.abs(np.array(get(row,10))-np.array(e.control_points)))<1e-8
 elif e.dxftype()=='LWPOLYLINE':
  assert get(row,70)==[int(e.closed)]
  assert np.max(np.abs(np.array(get(row,10))-np.array([p[:2] for p in e.get_points()])))<1e-8
# Pure-vector PDF, one common stroke weight.
pdf=fitz.open(OUT/'facade_straight.pdf');assert len(pdf)==1 and not pdf[0].get_images(full=True)
widths={round(x['width'],6) for x in pdf[0].get_drawings() if x.get('type') in ['s','fs']}
assert len(widths)==1 and abs(next(iter(widths))-.13*72/25.4)<1e-5
pdf[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(OUT/'pdf_check.png')
# Comparison is outside the drawing; the CAD file itself has no added captions.
old=Image.open(str(Path(__file__).resolve().parents[3]/'drawings/sustainable-facade/detail.png'));new=Image.open(OUT/'detail.png')
box=(350*3,292*3,610*3,346*3);a=old.crop(box);b=new.crop(box);compare=Image.new('RGB',(a.width,2*a.height+70),'white');draw=ImageDraw.Draw(compare)
draw.text((10,5),'PREVIOUS RASTER-CENTRELINE RESULT',fill='black');compare.paste(a,(0,25));draw.text((10,a.height+40),'NEW: ANALYTICAL STRAIGHT LINES',fill='black');compare.paste(b,(0,a.height+60));compare.save(OUT/'cornice_comparison.png')
report={'dxf_version':d.dxfversion,'entities':dict(counts),'architecture_entity_types':['LINE','ARC'],'architecture_polylines':0,'architecture_splines':0,'straight_cornice_checks':railchecks,'duplicate_line_intervals':0,'duplicate_arcs':0,'zero_length_lines':0,'unintended_near_axis_angles_under_2_degrees':0,'dxf_audit_errors':len(audit.errors),'pdf_raster_images':0,'plant_color_aci':94,'plant_color_rgb':[0,127,0],'uniform_lineweight_mm':.13,'native_spline_vs_scene_max_distance_px':maxdiff,'lisp_entity_records_checked':len(rows),'lisp_arc_angles_checked_as_radians':True,'tested_in_real_autocad':False,'assumed_baseline_width_mm':20000,'limitations':['Geometric reconstruction from raster; not a guarantee of identical stroke count or 100% visual fidelity.','Dimensions are estimated.','Foliage and masonry detail retain source-extraction limitations; not every open stroke was closed.','Line and arc geometry was tested numerically, not by opening AutoCAD.']}
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='straight_cornice_checks'},indent=2))
