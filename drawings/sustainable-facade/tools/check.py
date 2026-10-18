import os
from pathlib import Path
import json,re,math,sys,collections
sys.path[:0]=['/workspace/sustainable_deps','/workspace/elevation/deps']
import ezdxf,pypdfium2 as pdfium
import fitz
ROOT=Path(__file__).parent;OUT=Path(os.environ.get('FACADE_OUTPUT',str(ROOT/'output')))
s=(OUT/'sustainable_facade.lsp').read_text('ascii')
class Sym(str):pass
class Pair:
 def __init__(self,a,b):self.a=a;self.b=b
rx=re.compile(r';[^\n]*|"(?:\\.|[^"\\])*"|[()\']|[^\s()\'";]+')
tokens=[m.group() for m in rx.finditer(s) if not m.group().startswith(';')];pos=0
def read():
 global pos
 t=tokens[pos];pos+=1
 if t=='(':
  seq=[]
  while tokens[pos]!=')':
   if tokens[pos]=='.':
    pos+=1;tail=read();assert tokens[pos]==')';pos+=1
    for v in reversed(seq):tail=Pair(v,tail)
    return tail
   seq.append(read())
  pos+=1;return seq
 if t==')':raise ValueError('unexpected )')
 if t=="'":return [Sym('QUOTE'),read()]
 if t.startswith('"'):return json.loads(t)
 try:return float(t) if any(c in t for c in '.eE') else int(t)
 except ValueError:return Sym(t.upper())
forms=[]
while pos<len(tokens):forms.append(read())
funcs={f[1]:f for f in forms if isinstance(f,list) and f and f[0]==Sym('DEFUN')}
assert set(map(Sym,['SF:POLY','SF:BUILD','C:SUSTAIN']))<=set(funcs)
data={f[1]:f[2][1] for f in forms if isinstance(f,list) and len(f)==3 and f[0]==Sym('SETQ') and isinstance(f[2],list) and f[2][0]==Sym('QUOTE')}
rows=data[Sym('SF:DATA')]
doc=ezdxf.readfile(OUT/'sustainable_facade.dxf');entities=list(doc.modelspace())
assert len(rows)==len(entities)
for row,e in zip(rows,entities):
 assert row[0]=='SF_'+e.dxf.layer and row[1]==int(e.closed)
 assert row[2]==[list(p[:2]) for p in e.get_points()]
 assert e.dxf.lineweight==13 and e.dxf.true_color==0 and e.dxf.const_width==0
# Execute the actual parsed geometry emitter with a mocked native entmake.
emitted=[]
def car(v):return v.a if isinstance(v,Pair) else v[0]
def cdr(v):return v.b if isinstance(v,Pair) else v[1:]
def cons(a,b):return [a]+b if isinstance(b,list) else Pair(a,b)
def entmake(records):
 attrs={};points=[]
 for item in records:
  if isinstance(item,Pair):attrs[item.a]=item.b
  elif item[0]==10:points.append(item[1:])
  else:attrs[item[0]]=item[1:]
 if attrs[0]=='LWPOLYLINE':
  assert attrs[90]==len(points) and attrs[420]==0 and attrs[370]==13 and attrs[43]==0
  emitted.append((attrs[8],attrs[70],points))
 return records
def call(fn,args,env):
 if isinstance(fn,list) and fn[0]==Sym('LAMBDA'):
  ee=env.copy();ee.update(zip(fn[1],args));result=None
  for f in fn[2:]:result=ev(f,ee)
  return result
 name=str(fn).upper();prims={'CAR':car,'CDR':cdr,'CADR':lambda v:car(cdr(v)),'CADDR':lambda v:car(cdr(cdr(v))),'LENGTH':len,'CONS':cons,'LIST':lambda *v:list(v),'APPEND':lambda *v:sum(v,[]),'ENTMAKE':entmake}
 if name in prims:return prims[name](*args)
 if name=='MAPCAR':return [call(args[0],[x],env) for x in args[1]]
 f=funcs[Sym(name)];ee=env.copy();pp=f[2];loc=pp.index(Sym('/')) if Sym('/') in pp else len(pp)
 ee.update(zip(pp[:loc],args))
 for v in pp[loc+1:]:ee[v]=None
 result=None
 for form in f[3:]:result=ev(form,ee)
 return result
def ev(v,env):
 if isinstance(v,Sym):return env.get(v) if v!='NIL' else None
 if not isinstance(v,list):return v
 if not v:return None
 if v[0]==Sym('QUOTE'):return v[1]
 if v[0]==Sym('SETQ'):
  result=None
  for k,f in zip(v[1::2],v[2::2]):result=ev(f,env);env[k]=result
  return result
 if v[0]==Sym('FOREACH'):
  result=None
  for x in ev(v[2],env):
   env[v[1]]=x
   for f in v[3:]:result=ev(f,env)
  return result
 return call(v[0],[ev(q,env) for q in v[1:]],env)
call(Sym('SF:BUILD'),['MOCK_TEST'],{Sym('SF:DATA'):rows})
assert len(emitted)==len(rows)
for result,row in zip(emitted,rows):assert list(result)==row
# PDF resource and geometry check; no raster images in final drawing.
pdf=fitz.open(OUT/'sustainable_facade.pdf');assert len(pdf)==1
assert not pdf[0].get_images(full=True)
drawings=pdf[0].get_drawings();assert drawings
widths={round(d['width'],6) for d in drawings if d.get('type') in ('s','fs')}
assert len(widths)==1 and abs(next(iter(widths))-.13*72/25.4)<.00001
p=pdfium.PdfDocument(str(OUT/'sustainable_facade.pdf'));p[0].render(scale=2).to_pil().save(OUT/'pdf_check.png')
report=json.loads((OUT/'validation.json').read_text())
report.update({'lisp_parsed':True,'lisp_data_matches_dxf':True,'lisp_emitter_mocked_paths':len(emitted),'lisp_real_autocad_test':False,'pdf_pages':1,'pdf_raster_images':0,'pdf_uniform_stroke_pt':list(widths)})
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['paths','duplicate_segments','open_endpoints','lisp_data_matches_dxf','lisp_emitter_mocked_paths','pdf_raster_images','pdf_uniform_stroke_pt']},indent=2))
