"""Build nonduplicated facade linework, estimated-mm DXF/PDF, and self-contained AutoLISP.
No raster trace or AutoCAD runtime is claimed; the geometry is manually reconstructed.
"""
import sys,math,json,csv,collections,importlib.util
from pathlib import Path
sys.path.insert(0,'/workspace/elevation/deps')
import shapely
from shapely.geometry import Polygon,LineString,MultiLineString,Point,box
from shapely.ops import unary_union,linemerge
from shapely.strtree import STRtree
import numpy as np
import ezdxf,fitz,pypdfium2
import cairocffi as cairo
BASE=Path('/workspace/palace_reference');OUT=BASE/'output';REV=BASE/'review'
OUT.mkdir(exist_ok=True);REV.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('palace_geometry',BASE/'geometry_source.py');geom=importlib.util.module_from_spec(spec);spec.loader.exec_module(geom)
sc=geom.sc
# Projecting rails are in front of the glass, so ornament cannot pass through their solid bars.
for group,cx,w in [('left_balcony',220,132),('right_balcony',815,132),('recess_wall',646.5,105)]:
    x=cx-w/2
    frame=box(x,487,x+w,543).difference(box(x+4,491,x+w-4,529))
    frame=frame.union(box(cx-1,490,cx+1,530))
    for item in list(sc.items):
        if item['group']==group and item['layer']!='07_RAILINGS':
            sc.items.remove(item)
            for p in geom.polys(item['poly'].difference(frame)):sc.items.append(dict(item,poly=p))

# Unify crossing, non-nested pieces of each ornament into clean silhouettes.
# Nested rings (flower centers and frame contours) remain separate, preserving their detail.
original_overlap_pairs=0
clean_items=[]
for key in sorted({(q['group'],q['layer']) for q in sc.items}):
    items=[q for q in sc.items if (q['group'],q['layer'])==key]
    if key[1]!='06_ORNAMENT':
        clean_items+=items;continue
    gs=[q['poly'] for q in items];tree=STRtree(gs);parents=list(range(len(gs)))
    def root(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    for i,p in enumerate(gs):
        for j in tree.query(p,predicate='intersects'):
            j=int(j)
            if j<=i:continue
            q=gs[j]
            if max(p.area,q.area)>1000:continue
            if p.buffer(.000001).covers(q) or q.buffer(.000001).covers(p):continue
            if p.intersection(q).area>.0001:
                original_overlap_pairs+=1;a,b=root(i),root(j);parents[b]=a
    clusters=collections.defaultdict(list)
    for i,p in enumerate(gs):clusters[root(i)].append(p)
    for members in clusters.values():
        merged=unary_union(members)
        for p in geom.polys(merged):clean_items.append({'poly':p,'layer':key[1],'group':key[0]})
sc.items=clean_items
rings=sc.rings()
source_lines=[LineString(r['points']+[r['points'][0]]) for r in rings]
# A planar line network: one copy of each shared edge, all junctions connected.
network=shapely.unary_union(source_lines,grid_size=.001)
parts=list(network.geoms) if hasattr(network,'geoms') else [network]
# Classify each atomic edge from its nearest source contour, without duplicating shared edges.
edges=[]
for l in parts:
    cs=list(l.coords)
    for a,b in zip(cs,cs[1:]):
        if math.dist(a,b)>.00001:edges.append(LineString([a,b]))
midpoints=[e.interpolate(.5,normalized=True) for e in edges]
nearest=STRtree(source_lines).nearest(midpoints)
by_layer=collections.defaultdict(list)
for edge,i in zip(edges,nearest):by_layer[rings[int(i)]['layer']].append(edge)
paths=[]
MM=14000/917;DATUM=780;X0=25
for layer,ls in sorted(by_layer.items()):
    merged=linemerge(MultiLineString(ls))
    for p in (list(merged.geoms) if hasattr(merged,'geoms') else [merged]):
        # Preserve junctions; only simplify the interiors of individual chains.
        q=p
        coords=list(q.coords);closed=math.dist(coords[0],coords[-1])<1e-7
        if closed:coords=coords[:-1]
        mm=[(round((x-X0)*MM,4),round((DATUM-y)*MM,4)) for x,y in coords]
        mm=[p for i,p in enumerate(mm) if i==0 or p!=mm[i-1]]
        if len(mm)<2:continue
        if closed and len(mm)<3:continue
        paths.append({'layer':layer,'closed':closed,'points':mm})
# Validate the actual rounded exported geometry, not just the pre-export source.
all_segments=[];keys=set();endpoint_degree=collections.Counter()
for path in paths:
    cs=path['points'];pairs=list(zip(cs,cs[1:]+(cs[:1] if path['closed'] else [])))
    if not LineString(cs+(cs[:1] if path['closed'] else [])).is_simple:
        (REV/'bad_path.json').write_text(json.dumps(path))
        raise RuntimeError(f"Nonsimple chain: {path['layer']} {len(cs)} points; see bad_path.json")
    for a,b in pairs:
        key=tuple(sorted((a,b)));assert key not in keys;keys.add(key)
        assert math.dist(a,b)>.0001
        all_segments.append(LineString([a,b]));endpoint_degree[a]+=1;endpoint_degree[b]+=1
# A degree-one node would be a loose line end. Layer junction chains are allowed and joined.
loose=[p for p,d in endpoint_degree.items() if d==1]
assert not loose,loose[:10]
# Check proper X crossings between exported segments. Junctions sharing endpoints are intentional.
seg_tree=STRtree(all_segments);bad_crossings=[]
for i,s in enumerate(all_segments):
    for j in seg_tree.query(s,predicate='crosses'):
        j=int(j)
        if j>i:bad_crossings.append((i,j))
# Rounding/simplification can create crossings near a junction; never hide these in a readiness report.
if bad_crossings:raise RuntimeError(f'{len(bad_crossings)} unconnected crossings in exported paths: {bad_crossings[:8]}')

TOWER_H=(780-85)*MM;RIGHT_H=(780-251)*MM
DIMS=[{'id':'OVERALL_WIDTH','p1':(0,TOWER_H),'p2':(14000,RIGHT_H),'base':(7000,TOWER_H+1000),'angle':0,'value':14000},
      {'id':'OVERALL_HEIGHT','p1':((0-25)*MM,0),'p2':(0,TOWER_H),'base':(-1300,TOWER_H/2),'angle':90,'value':TOWER_H}]
SCHEDULE=[
 ('OVERALL_WIDTH','Overall facade width',14000,None),('TOWER_HEIGHT','Highest crown above ground datum',None,TOWER_H),
 ('MIDDLE_CROWN','Middle crown above ground datum',None,(780-214)*MM),('SIDE_CROWNS','Side crowns above ground datum',None,RIGHT_H),
 ('BELT_CORNICE','Lower edge of first-floor belt above datum',None,(780-564)*MM),
 ('LEFT_DOOR','Left door opening',61*MM,134*MM),('CENTRAL_DOOR','Projecting entrance door',62*MM,127*MM),
 ('LEFT_BALCONY','Left upper opening',122*MM,131*MM),('RIGHT_BALCONY','Right upper opening',122*MM,131*MM),
 ('RECESS_OPENING','Recessed upper opening',91*MM,124*MM),('NARROW_TALL_WINDOWS','Narrow tall outer frames',59*MM,311*MM),
 ('MIDDLE_TALL_WINDOW','Middle tall outer frame',80*MM,311*MM),('GROUND_ROSE_WINDOWS','Outer rose-window frames',80*MM,117*MM),
 ('LEFT_WING','Left front-wing width',264*MM,None),('RIGHT_WING','Right front-wing width',232*MM,None),
 ('CENTRAL_BAY','Central bay width',241*MM,None)]
(OUT/'geometry_mm.json').write_text(json.dumps({'units':'mm','estimated_overall_width':14000,'nominal_source_scale':MM,'paths':paths,'dimensions':DIMS},separators=(',',':')))
with (OUT/'estimated_dimensions_mm.csv').open('w',newline='') as f:
    writer=csv.writer(f,lineterminator='\n');writer.writerow(['id','description','estimated_width_mm','estimated_height_or_level_mm'])
    for ident,desc,w,h in SCHEDULE:writer.writerow([ident,desc,round(w) if w is not None else '',round(h) if h is not None else ''])

LAYERS=geom.LAYERS;LW=.18;LW_PT=LW*72/25.4
BBOX=(-2000,-1200,16000,TOWER_H+1800)
doc=ezdxf.new('R2010');ms=doc.modelspace()
doc.layers.new('00_WHITE_BACKGROUND',dxfattribs={'true_color':0xFFFFFF,'lineweight':18})
for l in LAYERS+['09_ESTIMATED_DIMS']:doc.layers.new(l,dxfattribs={'color':7,'true_color':0,'lineweight':18})
a,b,c,d=BBOX
ms.add_solid([(a,b),(c,b),(a,d),(c,d)],dxfattribs={'layer':'00_WHITE_BACKGROUND','true_color':0xFFFFFF,'lineweight':18})
for path in paths:
    ms.add_lwpolyline(path['points'],close=path['closed'],dxfattribs={'layer':path['layer'],'true_color':0,'color':7,'lineweight':18,'const_width':0})
for dim in DIMS:
    entity=ms.add_linear_dim(base=dim['base'],p1=dim['p1'],p2=dim['p2'],angle=dim['angle'],text='<> mm (est.)',
       override={'dimtxt':145,'dimasz':100,'dimexo':75,'dimexe':65,'dimclrd':0,'dimclre':0,'dimclrt':0,'dimlwd':18,'dimlwe':18,'dimdec':0,'dimtad':1},
       dxfattribs={'layer':'09_ESTIMATED_DIMS','true_color':0,'lineweight':18})
    entity.render()
doc.header['$INSUNITS']=4;doc.header['$LWDISPLAY']=True;doc.header['$CELWEIGHT']=18
doc.set_modelspace_vport(14000,center=(7000,5500))
file_dxf=OUT/'palace_reference_redraw.dxf';doc.saveas(file_dxf)
check=ezdxf.readfile(file_dxf);audit=check.audit();assert not audit.errors and not audit.fixes
cad_paths=list(check.modelspace().query('LWPOLYLINE'))
assert len(cad_paths)==len(paths)
for ent,path in zip(cad_paths,paths):
    assert bool(ent.closed)==path['closed'] and ent.dxf.lineweight==18 and ent.dxf.true_color==0
    assert list(ent.get_points('xy'))==[tuple(p) for p in path['points']]
# Vector PDF: one drawing sheet plus an estimated-dimension schedule.
PAGE_W=420*72/25.4;PAGE_H=297*72/25.4;MARGIN=30
SF=min((PAGE_W-2*MARGIN)/(c-a),(PAGE_H-2*MARGIN)/(d-b));TX=(PAGE_W-(c-a)*SF)/2-a*SF;TY=(PAGE_H-(d-b)*SF)/2+d*SF
pdf_path=OUT/'palace_reference_redraw.pdf';surface=cairo.PDFSurface(str(pdf_path),PAGE_W,PAGE_H);ctx=cairo.Context(surface)
def black():ctx.set_source_rgb(0,0,0)
def wpt(p):return (TX+p[0]*SF,TY-p[1]*SF)
def text(x,y,s,size=8):
    ctx.select_font_face('Sans');ctx.set_font_size(size);black();ctx.move_to(x,y);ctx.show_text(s)
ctx.set_source_rgb(1,1,1);ctx.paint();black();ctx.set_line_width(LW_PT);ctx.set_line_join(cairo.LINE_JOIN_ROUND)
for path in paths:
    ctx.move_to(*wpt(path['points'][0]))
    for p in path['points'][1:]:ctx.line_to(*wpt(p))
    if path['closed']:ctx.close_path()
    ctx.stroke()
# Render dimensions as uncluttered lines outside the facade, matching the native DXF dimensions.
for dim in DIMS:
    p,q=dim['p1'],dim['p2'];base=dim['base'];horizontal=dim['angle']==0
    e1=(p[0],base[1]) if horizontal else (base[0],p[1]);e2=(q[0],base[1]) if horizontal else (base[0],q[1])
    for u,v in [(p,e1),(q,e2),(e1,e2)]:ctx.move_to(*wpt(u));ctx.line_to(*wpt(v));ctx.stroke()
    # Open architectural arrowheads all share the same stroke width.
    for tip,sgn in [(e1,1),(e2,-1)]:
        t=(tip[0]+sgn*100,tip[1]) if horizontal else (tip[0],tip[1]+sgn*100)
        vv=[(t[0],t[1]-45),tip,(t[0],t[1]+45)] if horizontal else [(t[0]-45,t[1]),tip,(t[0]+45,t[1])]
        ctx.move_to(*wpt(vv[0]));ctx.line_to(*wpt(vv[1]));ctx.line_to(*wpt(vv[2]));ctx.stroke()
    mid=((e1[0]+e2[0])/2,(e1[1]+e2[1])/2);px,py=wpt(mid)
    if horizontal:text(px-40,py-5,f"{dim['value']:.0f} mm (est.)",9)
    else:
        ctx.save();ctx.translate(px-7,py+50);ctx.rotate(-math.pi/2);text(0,0,f"{dim['value']:.0f} mm (est.)",9);ctx.restore()
text(35,PAGE_H-19,'ESTIMATED GEOMETRY - 14,000 mm nominal width - black 0.18 mm - dimensions are not surveyed',8)
ctx.show_page();ctx.set_source_rgb(1,1,1);ctx.paint()
text(55,55,'ESTIMATED DIMENSION SCHEDULE (mm)',16)
text(55,78,'Visual reconstruction. All values are proportional estimates, not construction measurements.',9)
text(55,110,'ID / ELEMENT',10);text(760,110,'WIDTH (mm)',10);text(930,110,'HEIGHT / LEVEL (mm)',10)
for i,(ident,desc,ww,hh) in enumerate(SCHEDULE):
    y=140+i*31;text(55,y,ident+' - '+desc,9)
    text(785,y,'-' if ww is None else f'{ww:.0f}',10);text(970,y,'-' if hh is None else f'{hh:.0f}',10)
text(55,685,'AutoLISP: APPLOAD palace_reference_redraw.lsp, then type PALACE.',11)
text(55,707,'Pick an insertion point; accept 14000 mm or enter a different total width. PALACEDIMS adds native dimensions.',10)
text(55,739,'Geometry is shared with the DXF and the embedded AutoLISP data. No external image or CAD import is required.',9)
surface.finish()
pdf=fitz.open(pdf_path);assert len(pdf)==2 and all(not p.get_images(full=True) for p in pdf)
widths={round(p['width'],5) for page in pdf for p in page.get_drawings() if p['type'] in ['s','fs']};assert widths=={round(LW_PT,5)},widths
r=pypdfium2.PdfDocument(str(pdf_path));im=r[0].render(scale=1.5).to_pil();im.save(OUT/'palace_reference_preview.png')
r[0].render(scale=3).to_pil().save(REV/'drawing_3x.png')
report={'estimated_width_mm':14000,'estimated_tower_height_mm':TOWER_H,'lineweight_mm':.18,'source':'Manual visual reconstruction; dimensions explicitly estimated.',
 'ornament_overlap_pairs_resolved':original_overlap_pairs,'unique_paths':len(paths),'closed_polyline_paths':sum(p['closed'] for p in paths),
 'junction_to_junction_chains':sum(not p['closed'] for p in paths),'unique_segments':len(all_segments),'duplicate_segments':0,
 'loose_endpoints':len(loose),'unconnected_proper_crossings':len(bad_crossings),'dxf_audit_errors':len(audit.errors),'dxf_audit_fixes':len(audit.fixes),
 'pdf_pages':2,'pdf_raster_images':0,'notes':'Shared edges are drawn once. Open entity chains terminate at connected junctions; complete contours remain closed as a network. Intended joints and leaded-glass motifs remain.',
 'autocad_runtime_test':'Not available. AutoLISP syntax, embedded geometry and API call structure will be checked separately; no claim of execution in AutoCAD.'}
(OUT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
