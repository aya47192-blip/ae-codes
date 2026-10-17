"""Read AutoLISP, execute its polyline emitter in a small mocked CAD environment,
and round-trip the emitted geometry through ezdxf. This is NOT an AutoCAD runtime.
"""
import re,json,math,collections
from pathlib import Path
import ezdxf
BASE=Path('/workspace/palace_lisp');OUT=BASE/'output';REV=BASE/'review'
s=(OUT/'palace_facade_clean.lsp').read_text('ascii')
class Sym(str):pass
class Pair:
    def __init__(self,a,b):self.a=a;self.b=b
    def __repr__(self):return f'Pair({self.a!r},{self.b!r})'
rx=re.compile(r';[^\n]*|"(?:\\.|[^"\\])*"|[()\']|[^\s()\'";]+')
tokens=[m.group() for m in rx.finditer(s) if not m.group().startswith(';')];pos=0

def read():
    global pos
    if pos>=len(tokens):raise ValueError('Unexpected EOF')
    t=tokens[pos];pos+=1
    if t=='(':
        a=[]
        while pos<len(tokens) and tokens[pos]!=')':
            if tokens[pos]=='.':
                pos+=1;b=read()
                assert tokens[pos]==')';pos+=1
                for value in reversed(a):b=Pair(value,b)
                return b
            a.append(read())
        assert pos<len(tokens),'Unclosed list';pos+=1;return a
    if t==')':raise ValueError('Unexpected closing parenthesis')
    if t=="'":return [Sym('QUOTE'),read()]
    if t.startswith('"'):return json.loads(t)
    try:return float(t) if any(c in t for c in '.eE') else int(t)
    except ValueError:return Sym(t.upper())
forms=[]
while pos<len(tokens):forms.append(read())
funcs={f[1]:f for f in forms if isinstance(f,list) and f and f[0]==Sym('DEFUN')}
assert all(Sym(n) in funcs for n in ['C:PALACE','C:PALACEDIMS','C:PALACEINFO','PALC:POLY','PALC:BUILD','PALC:DIMENSION'])
setqs={}
for form in forms:
    if isinstance(form,list) and form and form[0]==Sym('SETQ'):
        assert len(form)%2==1
        for key,val in zip(form[1::2],form[2::2]):
            setqs[key]=val[1] if isinstance(val,list) and val and val[0]==Sym('QUOTE') else val
rows=setqs[Sym('PALC:DATA')];dims=setqs[Sym('PALC:DIMS')]
source=json.loads((OUT/'geometry_mm.json').read_text())
assert len(rows)==len(source['paths'])
for row,original in zip(rows,source['paths']):
    assert row[0]==original['layer'] and row[1]==int(original['closed']) and row[2]==[list(p) for p in original['points']]
for row,d in zip(dims,source['dimensions']):
    for a,b in zip(row[:3],[d['p1'],d['p2'],d['base']]):assert math.dist(a,b)<.0001
    assert abs(row[3]-math.radians(d['angle']))<1e-14
# Ensure all project-specific function calls resolve; no runtime file imports or shell commands.
refs=set()
def walk(v):
    if isinstance(v,list):
        if v and isinstance(v[0],Sym) and v[0].startswith('PALC:'):refs.add(v[0])
        for q in v:walk(q)
for form in forms:walk(form)
assert refs<=set(funcs),refs-set(funcs)
assert '(startapp' not in s.lower() and '(load ' not in s.lower()
# Mock native entmake, letting the unmodified PALC:poly and PALC:emit bodies execute.
doc=ezdxf.new('R2010');ms=doc.modelspace();emitted=[];destination=ms;block_records=[]
doc.layers.new('PALC_00_WHITE_BACKGROUND')
for name in setqs[Sym('PALC:LAYERS')]:doc.layers.new('PALC_'+name)
def native_entmake(records):
    global destination
    attrs={};points=[]
    for item in records:
        if isinstance(item,Pair):attrs[item.a]=item.b
        elif item[0]==10:points.append(item[1:]);attrs[10]=item[1:]
        else:attrs[item[0]]=item[1:]
    kind=attrs[0]
    if kind=='BLOCK':
        assert attrs[2]==attrs[3] and attrs[10]==[0.0,0.0,0.0]
        destination=doc.blocks.new(attrs[2],base_point=attrs[10]);block_records.append('BLOCK');return records
    if kind=='ENDBLK':
        block_records.append('ENDBLK');destination=ms;return records
    if kind=='SOLID':
        assert attrs[420]==0xFFFFFF
        destination.add_solid([attrs[10],attrs[11],attrs[12],attrs[13]],dxfattribs={'layer':attrs[8],'true_color':attrs[420]})
        block_records.append('WHITE_SOLID');return records
    assert kind=='LWPOLYLINE' and attrs[90]==len(points)
    assert attrs[420]==0 and attrs[370]==18 and attrs[43]==0 and attrs[6]=='Continuous'
    e=destination.add_lwpolyline(points,close=bool(attrs[70]),dxfattribs={'layer':attrs[8],'true_color':attrs[420],'lineweight':attrs[370]})
    emitted.append(e);return records

def car(v):return v.a if isinstance(v,Pair) else v[0]
def cdr(v):return v.b if isinstance(v,Pair) else v[1:]
def cons(a,b):return [a]+b if isinstance(b,list) else Pair(a,b)
def call(fn,args,env):
    if isinstance(fn,list) and fn and fn[0]==Sym('LAMBDA'):
        ee=env.copy();ee.update(zip(fn[1],args));result=None
        for f in fn[2:]:result=ev(f,ee)
        return result
    n=str(fn).upper()
    primitives={'CAR':car,'CDR':cdr,'CADR':lambda x:car(cdr(x)),'CADDR':lambda x:car(cdr(cdr(x))),
       'LENGTH':len,'CONS':cons,'LIST':lambda *a:list(a),'APPEND':lambda *a:sum(a,[]),
       'STRCAT':lambda *a:''.join(a),'NULL':lambda x:x is None or x==[],
       '+':lambda *a:sum(a),'*':lambda *a:math.prod(a),'ENTMAKE':native_entmake}
    if n in primitives:return primitives[n](*args)
    if n=='MAPCAR':return [call(args[0],[x],env) for x in args[1]]
    form=funcs[Sym(n)];ee=env.copy();parameters=form[2];loc=parameters.index(Sym('/')) if Sym('/') in parameters else len(parameters)
    ee.update(zip(parameters[:loc],args))
    for name in parameters[loc+1:]:ee[name]=None
    result=None
    for f in form[3:]:result=ev(f,ee)
    return result

def ev(v,env):
    if isinstance(v,Sym):
        if v=='NIL':return None
        if v=='T':return True
        return env[v]
    if not isinstance(v,list):return v
    if not v:return None
    op=v[0]
    if op==Sym('QUOTE'):return v[1]
    if op==Sym('SETQ'):
        result=None
        for k,f in zip(v[1::2],v[2::2]):result=ev(f,env);env[k]=result
        return result
    if op==Sym('FOREACH'):
        result=None
        for item in ev(v[2],env):
            env[v[1]]=item
            for expr in v[3:]:result=ev(expr,env)
        return result
    if op==Sym('IF'):
        condition=ev(v[1],env)
        return ev(v[2],env) if condition else ev(v[3],env) if len(v)>3 else None
    return call(op,[ev(x,env) for x in v[1:]],env)
call(Sym('PALC:BUILD'),['PALC_TEST_BLOCK'],{Sym('PALC:DATA'):rows})
assert block_records==['BLOCK','WHITE_SOLID','ENDBLK']
assert len(doc.blocks.get('PALC_TEST_BLOCK'))==len(rows)+1
assert len(emitted)==len(source['paths'])
for e,p in zip(emitted,source['paths']):
    assert list(e.get_points('xy'))==[tuple(x) for x in p['points']]
    assert bool(e.closed)==p['closed']
for scale in [.5,1,1.25]:
    point=[100,200,0];actual=call(Sym('PALC:POINT'),[[14000,10610.687],point,scale],{})
    expected=[100+14000*scale,200+10610.687*scale,0]
    assert actual==expected
ms.add_blockref('PALC_TEST_BLOCK',(100,200,0),dxfattribs={'xscale':1.25,'yscale':1.25,'zscale':1.25})
file=REV/'autolisp_emitter_roundtrip.dxf';doc.saveas(file);audit=ezdxf.readfile(file).audit();assert not audit.errors
report=json.loads((OUT/'validation.json').read_text());report.update({
 'lisp_balanced_and_parsed':True,'lisp_functions_resolve':True,'lisp_embedded_paths_match_dxf_source':True,
 'lisp_polyline_emitter_mock_executions':len(emitted),'lisp_mock_dxf_audit_errors':len(audit.errors),'lisp_block_builder_mock_execution':True,'lisp_block_entity_count':len(rows)+1,
 'lisp_insertion_scale_tests':[.5,1,1.25],
 'autocad_runtime_test':'Not available: interactive PALACE, native ActiveX dimensions, and display must be confirmed inside AutoCAD. Parser and mocked emitter tests are not an AutoCAD run.'})
(OUT/'validation.json').write_text(json.dumps(report,indent=2))
print('Parsed',len(forms),'top-level forms;',len(funcs),'functions;',len(rows),'embedded paths.')
print('Unmodified AutoLISP block builder and polyline emitter executed against a mocked entmake; DXF round-trip and scale checks passed.')
