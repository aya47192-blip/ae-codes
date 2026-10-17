"""Manual geometric reconstruction of the image displayed in the chat (1776 x 592).
No raster file was available for pixel measurements. All source coordinates below
are visual estimates, not claims of automated tracing or survey accuracy.
"""
import sys, math, json, collections
from pathlib import Path
sys.path.insert(0, '/workspace/elevation/deps')
import cairocffi as cairo
import ezdxf
import fitz
import pypdfium2 as pdfium

BASE=Path('/workspace/elevation_v2'); OUT=BASE/'output'; REVIEW=BASE/'review'
OUT.mkdir(exist_ok=True); REVIEW.mkdir(exist_ok=True)
W,H=1776,592
LAYERS={
 '01_GROUND_CUT': {'aci':7,'width':1.00,'gray':.08,'plot_mm':35},
 '02_MAIN_STRUCTURE': {'aci':7,'width':.95,'gray':.06,'plot_mm':30},
 '03_SECONDARY_ARCH': {'aci':8,'width':.68,'gray':.10,'plot_mm':20},
 '04_FACADE_LOUVERS': {'aci':9,'width':.48,'gray':.30,'plot_mm':13},
 '05_SHADING_HATCH': {'aci':9,'width':.46,'gray':.40,'plot_mm':13},
 '06_PEOPLE_RED': {'aci':1,'width':.5,'gray':.10,'plot_mm':18},
 '07_TREES_ENTOURAGE': {'aci':8,'width':.5,'gray':.10,'plot_mm':18},
 '08_WATER_LINE': {'aci':5,'width':.5,'gray':.10,'plot_mm':18},
 '09_BORDER_TEXT': {'aci':7,'width':.6,'gray':.10,'plot_mm':20},
}
G='01_GROUND_CUT'; M='02_MAIN_STRUCTURE'; S='03_SECONDARY_ARCH'; F='04_FACADE_LOUVERS'; J='05_SHADING_HATCH'

def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def sub(a,b):return (a[0]-b[0],a[1]-b[1])
def add(a,b):return (a[0]+b[0],a[1]+b[1])
def mul(a,t):return (a[0]*t,a[1]*t)
def length(a,b):return math.dist(a,b)
def area(poly):return sum(cross(a,b) for a,b in zip(poly,poly[1:]+poly[:1]))/2

def inside(p,poly):
    x,y=p; result=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:result=not result
    return result

def split_by_polygon(a,b,poly,keep_inside=True):
    d=sub(b,a); ts=[0.,1.]
    for c,e in zip(poly,poly[1:]+poly[:1]):
        v=sub(e,c); det=cross(d,v)
        if abs(det)<1e-10:continue
        q=sub(c,a); t=cross(q,v)/det; u=cross(q,d)/det
        if 1e-9<t<1-1e-9 and -1e-9<=u<=1+1e-9:ts.append(t)
    ts=sorted(set(round(t,11) for t in ts)); out=[]
    for t,u in zip(ts,ts[1:]):
        if u-t<1e-8:continue
        mid=add(a,mul(d,(t+u)/2))
        if inside(mid,poly)==keep_inside:out.append((add(a,mul(d,t)),add(a,mul(d,u))))
    return out

def infinite_intersect(a,b,c,d):
    v=sub(b,a); w=sub(d,c); det=cross(v,w)
    if abs(det)<1e-10:return b
    return add(a,mul(v,cross(sub(c,a),w)/det))

def inset(poly,dist):
    # Constant-width offset, including the short trapezoids on the left glazing.
    if area(poly)<0:poly=list(reversed(poly))
    shifted=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        v=sub(b,a); n=length(a,b); offset=(-v[1]*dist/n,v[0]*dist/n)
        shifted.append((add(a,offset),add(b,offset)))
    return [infinite_intersect(*shifted[i-1],*shifted[i]) for i in range(len(poly))]

def interp(x,points):
    for a,b in zip(points,points[1:]):
        if a[0]-1e-7<=x<=b[0]+1e-7:
            return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])
    raise ValueError((x,points))

class VectorScene:
    def __init__(self):self.lines=[];self.group=''
    def line(self,a,b,layer=M,width=None):
        if length(a,b)>.15:
            self.lines.append({'a':tuple(map(float,a)),'b':tuple(map(float,b)),'layer':layer,'width':width or LAYERS[layer]['width'],'group':self.group})
    def poly(self,pts,layer=M,closed=False,width=None):
        for a,b in zip(pts,pts[1:]+(pts[:1] if closed else [])):self.line(a,b,layer,width)
    def rect(self,x,y,w,h,layer=M,width=None):self.poly([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],layer,True,width)
    def clipped(self,a,b,poly,layer=F,width=None):
        for c,d in split_by_polygon(a,b,poly):self.line(c,d,layer,width)
    def occlude(self,poly,groups=None):
        new=[]
        for item in self.lines:
            if groups is not None and item['group'] not in groups:new.append(item);continue
            for a,b in split_by_polygon(item['a'],item['b'],poly,False):new.append(dict(item,a=a,b=b))
        self.lines=new
    def deduplicate(self):
        seen=set();result=[]
        for item in self.lines:
            key=tuple(sorted((tuple(round(v,4) for v in item['a']),tuple(round(v,4) for v in item['b']))))
            if key not in seen:seen.add(key);result.append(item)
        self.lines=result

sc=VectorScene()
# --- A. Upper left tower. ---
sc.group='tower'
# Roof edge strip and its visible downturned return.
sc.poly([(233,125),(565,169),(590,229),(598,286)],M,width=1.1)
sc.poly([(233,125),(233,137),(273,202)],M)
sc.poly([(235,127),(563,171)],S)
sc.poly([(243,154),(243,128)],S)
sc.poly([(273,202),(273,180),(566,180)],M)
sc.poly([(273,180),(298,300)],M)
sc.poly([(278,203),(300,300)],S)
sc.poly([(565,170),(577,223),(585,287)],S)
# Vertical sheet joints above the horizontal cap.
roof_rear=[(233,127),(563,171)]
for x in [272,301,329,358,387,416,445,474,503,531,560]:
    sc.line((x,interp(x,roof_rear)),(x,180),F)
# Panel joints avoid the glazed openings and don't continue through them.
sc.line((318,181),(318,298),J)
sc.line((284,240),(338,240),J)
sc.line((549,240),(579,240),J)
for x in [409,521]:
    sc.line((x,181),(x,195),J)
    sc.line((x,242),(x,252),J)
for y in [196,253]:
    sc.rect(339,y,210,45,M)
    sc.rect(342,y+2,205,42,S)
    # Ten visibly repeated intermediate vertical glazing bars.
    for x in [360,379,398,417,435,454,473,492,511,530]:
        sc.line((x,y+2),(x,y+44),F,width=.57)
for a,b in [((583,231),(590,286)),((587,237),(594,286)),((591,245),(596,286))]:sc.line(a,b,S,width=.56)

# --- B. Low roof on the left, behind the folded facade. ---
sc.group='left_roof'
left_roof=[(77,356),(237,313),(295,301),(430,298),(430,316),(237,337)]
# Cover tower below the low roof line.
sc.occlude([(237,313),(295,300),(430,297),(505,298),(531,292),(566,289),(566,337),(237,356)],groups=['tower'])
sc.poly([(77,356),(237,313),(295,301),(430,298)],M)
sc.poly([(77,356),(236,311),(291,330)],S)
# Flat-seam parallel panels on the low pitched surface, not radiating rays.
for rear_x,front_x in [(285,245),(307,268),(329,290),(351,313),(374,335),(396,357),(417,380),(430,402)]:
    a=(rear_x,301-(rear_x-295)*3/135)
    b=(front_x,336-(front_x-237)*20/193)
    sc.clipped(a,b,left_roof,F)
# Left triangular roof planes and the small first roof upstand.
sc.poly([(77,356),(237,337),(237,313),(291,331)],S)
sc.poly([(80,354),(236,316),(281,331)],S,width=.55)
sc.line((112,348),(237,319),F)
sc.line((143,344),(237,322),F)
sc.line((175,341),(237,326),F)
sc.line((207,338),(237,330),F)
sc.line((241,317),(281,332),S)
# Second low roof upstand with a shallow valley at its right-hand side.
upstand=[(430,297),(475,309),(505,307),(505,299),(430,297)]
sc.occlude(upstand[:-1],groups=['left_roof'])
sc.poly(upstand,M)
sc.line((430,297),(430,316),M)
sc.line((434,300),(475,311),S)
sc.line((475,311),(505,308),S)
sc.line((299,301),(429,298),S)

# --- C. Foreground folded panels. Every major panel seam is explicit. ---
sc.group='folded_facade'
face=[(77,356),(237,337),(430,316),(505,308),(505,299),(531,292),(493,373),(493,404),(346,468),(339,471),(79,471)]
sc.poly([(77,356),(79,471)],M,width=1.15)
sc.poly([(77,356),(237,337),(430,316),(505,308)],M,width=1.0)
sc.poly([(505,299),(531,292),(566,289)],M,width=1.0)
sc.poly([(531,292),(466,398),(346,468),(339,471)],M,width=.95)
sc.line((566,289),(510,334),M,width=.95)
# The five long diagonal joints on the folded front, including the missing short one.
for a,b in [((77.45,381),(116,351.4)),((78.2,424),(174,344.5)),((131,471),(263,334.2)),((267,471),(375.5,322)),((339,471),(448,315)),((346,468),(455,314))]:
    sc.line(a,b,M,width=.88)
# Hairline panel joints: stop at actual diagonal boundaries.
for a,b in [((123,387),(174,426.4)),((173,344.6),(173,392)),((174,426.4),(174,471)),((234,364.3),(309,413.3)),((309,329.2),(309,413.3)),((309,401),(366,432.4)),((418,367),(465,398.3))]:sc.line(a,b,J,width=.48)
# Cut-edge of the last sloping plate.
sc.line((531,292),(535,292),S)
sc.line((535,292),(470,397),S,width=.58)

# --- D. Glazing under the left plates. Occluded by the ramp later. ---
sc.group='central_glazing'
left_glass=[(346,468),(493,404),(493,373),(510,365),(510,334),(566,312),(566,471),(346,471)]
sc.poly([(346,468),(493,404),(493,373),(510,365),(510,334),(566,312)],M)
# Individual structural mullions: spacing is piecewise, not a rectangular grid.
for x in [360,364,375,379,399,402,423,427,447,451,470,474,493,497,510,514,521,525,535,539,556,560,564,566]:
    sc.clipped((x,310),(x,471),left_glass,S,width=.68 if x in [375,399,423,447,470,493,510,521,539,560,566] else .45)
# Only the narrow tall glazing has the short horizontal transoms visible in the reference.
for y in [339,357,376,395]:
    sc.clipped((522,y),(535,y),left_glass,F,width=.47)
for y in [329,349,369,389]:
    sc.clipped((540,y),(556,y),left_glass,F,width=.47)
# Short ground-level rebates on the low wedge.
sc.clipped((350,469),(428,469),left_glass,F)
sc.clipped((459,468),(545,468),left_glass,F)

# --- E. Central recess, upper wall and doors. ---
sc.group='central_recess'
sc.poly([(566,312),(590,333),(748,333)],M)
sc.line((566,313),(566,402),M)
sc.line((590,333),(590,402),S)
sc.line((590,374),(629,374),J)
sc.poly([(629,402),(629,342),(726,342),(728,347),(748,347)],M)
sc.line((726,342),(726,359),S)
sc.rect(645,347,17,10,J,width=.6)
sc.poly([(748,359),(674,359),(674,367),(748,367)],M)
sc.line((726,367),(726,401),S)
sc.poly([(698,401),(698,377),(722,377),(722,401)],M)
sc.line((711,378),(711,401),S)
# Recessed lower room, including its left-hand reveal.
sc.poly([(566,423),(590,433),(650,433),(650,459),(566,459)],M)
sc.line((590,433),(590,459),S)
sc.poly([(558,423),(558,471),(650,471),(659,467),(659,423)],M)
sc.line((566,423),(566,471),M)
sc.line((650,423),(650,433),S)
# Lower narrow panes and the small right-hand reveal.
sc.poly([(659,423),(668,427),(748,427)],S)
sc.line((668,427),(668,470),M)
sc.line((679,427),(679,469),S)
for x in [691,713,734]:sc.line((x,427),(x,469),J)
sc.poly([(668,470),(679,468),(748,468)],S)

# --- F. White folded ramp/front fascia. Remove, rather than hide, back lines. ---
ramp=[(428,452),(521,418),(521,402),(748,402),(748,422),(546,422),(428,471)]
sc.occlude(ramp,groups=['central_glazing','central_recess'])
sc.group='ramp'
sc.poly(ramp,M,True,width=1.05)

# --- G. Long rear roof surface and its standing seams. ---
sc.group='main_roof'
roof_top=[(566,289),(1651,201)]
roof_front=[(566,289),(1728,245)]
roof_surface=[(566,289),(1651,201),(1728,245)]
sc.poly([(566,289),(1715,196),(1712,210),(1691,220)],M,width=1.0)
sc.line((598,286),(1713,198),S,width=.58)
sc.line((1651,201),(1728,245),M)
# Seam direction varies mildly with position, as in the roof perspective.
seam_x=[625,665,705,749,793,837,881,926,971,1015,1059,1104,1139,1162,1185,1208,1231,1254,1277,1300,1323,1346,1369,1392,1415,1438,1461,1484,1507,1530,1553,1576,1599,1622,1645]
for x in seam_x:
    y=interp(x,roof_top); slope=.58+.00064*(x-800)
    sc.clipped((x,y),(x+200*slope,y+200),roof_surface,F,width=.49)
# Three triangular roof returns obscure the seams beneath.
for pts in [[(1031,250),(1085,270),(1031,272)],[(1382,238),(1428,258),(1382,260)],[(1551,231),(1597,251),(1551,253)]]:
    sc.occlude(pts,groups=['main_roof'])
    sc.poly(pts,M,True,width=.85)
    sc.poly([(pts[0][0]+3,pts[0][1]+4),(pts[1][0]-5,pts[1][1]),(pts[0][0]+3,pts[2][1]-.4)],S,width=.52)
# Roof vent; its white shaft removes roof seams behind it.
chimney=[(748,231),(759,231),(759,282),(748,282)]
sc.occlude(chimney,groups=['main_roof'])
sc.poly(chimney,M,True,width=1.0)

# --- H. Continuous long fascia (also hides lower ends of roof returns). ---
sc.group='main_fascia'
fascia=[(566,289),(1771,243),(1771,255),(566,312)]
sc.occlude(fascia,groups=['main_roof','tower','central_glazing','central_recess'])
sc.poly(fascia,M,True,width=1.05)
fascia_top=[(566,289),(1771,243)]; fascia_bottom=[(566,312),(1771,255)]
for x in [664,1085,1207,1313,1419,1594]:
    sc.line((x,interp(x,fascia_top)),(x,interp(x,fascia_bottom)),J,width=.54)
sc.poly([(1741,256.4),(1740,270),(1771,255)],M,width=.84)

# --- I. Main zigzag glazed strip. Explicit corner and mullion correspondences. ---
sc.group='curtain_wall'
bottom=[(748,317),(1105,377),(1141,371),(1358,405),(1397,395),(1712,462)]
# Each pair is (top-x, foot-x). The two short folds are real pane edges.
frames=[(748,748),(755,754),(779,776),(805,801),(831,826),(859,853),(889,882),(919,911),(950,941),(982,972),(1015,1005),(1049,1037),(1083,1071),(1117,1105),(1153,1141),(1190,1177),(1227,1213),(1264,1249),(1301,1285),(1338,1321),(1375,1358),(1415,1397),(1451,1432),(1487,1467),(1523,1502),(1559,1537),(1595,1572),(1631,1607),(1667,1642),(1703,1677),(1739,1712)]
# Single outer rim and inset glass quadrilaterals create joined double frames.
outer=[(748,interp(748,fascia_bottom)),(1739,interp(1739,fascia_bottom))]+list(reversed(bottom))
sc.poly(outer,M,True,width=.98)
for (tx,bx),(ux,vx) in zip(frames,frames[1:]):
    pane=[(tx,interp(tx,fascia_bottom)),(ux,interp(ux,fascia_bottom)),(vx,interp(vx,bottom)),(bx,interp(bx,bottom))]
    # The very narrow left sliver still has two distinct boundary lines.
    amount=.85 if ux-tx<10 else 1.35
    sc.poly(inset(pane,amount),S,True,width=.69)

# --- J. Base wall, vertical cladding joints, and low plinth. ---
sc.group='base_wall'
sc.line((748,317),(748,471),M,width=1.0)
for x in [776,893,985,1032,1103,1153,1200,1316,1362,1432,1477,1520,1566]:
    y=interp(x,bottom)+.4
    low=459 if 1220<x<1462 else 471
    sc.line((x,y),(x,low),J,width=.5)
sc.poly([(1220,471),(1220,459),(1462,459),(1462,471)],M,width=.93)
sc.line((1712,462),(1713,471),M,width=.9)
sc.group='ground'
sc.line((79,471),(1713,471),G,width=1.05)

# Reject invalid numbers, zero-length segments, and exact duplicates.
sc.deduplicate()
for item in sc.lines:
    assert all(math.isfinite(v) for p in [item['a'],item['b']] for v in p)
    assert length(item['a'],item['b'])>.15
    assert all(-1<=p[0]<=W+1 and -1<=p[1]<=H+1 for p in [item['a'],item['b']])

# Visible glazing must not cross the opaque walkway.
for item in sc.lines:
    if item['group']=='central_glazing':
        assert not inside(mul(add(item['a'],item['b']),.5),ramp)
# --- Export both formats from this one scene; no embedded raster references. ---
def dxf_export(version,filename):
    doc=ezdxf.new(version)
    for name,spec in LAYERS.items():
        attrs={'color':spec['aci']}
        if version!='R12':attrs['lineweight']=spec['plot_mm']
        doc.layers.new(name,dxfattribs=attrs)
    if 'DASHED' not in doc.linetypes:
        doc.linetypes.new('DASHED',dxfattribs={'description':'Dashed __ __','pattern':[12.,8.,-4.]})
    ms=doc.modelspace()
    for item in sc.lines:
        a,b=item['a'],item['b']
        attrs={'layer':item['layer']}
        ms.add_line((a[0],H-a[1],0),(b[0],H-b[1],0),dxfattribs=attrs)
    if version!='R12':
        doc.header['$INSUNITS']=0 # Unitless: no real-world dimension was supplied.
        doc.header['$LWDISPLAY']=True
    doc.set_modelspace_vport(520,center=(924,294))
    doc.saveas(OUT/filename)
    return doc

dxf_export('R12','elevation_v2.dxf')
dxf_export('R2010','elevation_v2_lineweights.dxf')

pdf_path=OUT/'elevation_v2.pdf'
surface=cairo.PDFSurface(str(pdf_path),W*2,H*2)
ctx=cairo.Context(surface);ctx.scale(2,2)
ctx.set_line_cap(cairo.LINE_CAP_ROUND);ctx.set_line_join(cairo.LINE_JOIN_ROUND)
for item in sc.lines:
    gray=LAYERS[item['layer']]['gray']
    ctx.set_source_rgb(gray,gray,gray);ctx.set_line_width(item['width'])
    ctx.move_to(*item['a']);ctx.line_to(*item['b']);ctx.stroke()
surface.finish()
# High-resolution visual review through a PDF renderer, not from source geometry.
pdf=pdfium.PdfDocument(str(pdf_path)); page=pdf[0]
preview=page.render(scale=.5).to_pil();preview.save(OUT/'elevation_v2_preview.png')
large=page.render(scale=2).to_pil();large.save(REVIEW/'elevation_v2_4x.png')
for name,box in {'left':(65,112,604,483),'center':(336,279,765,481),'roof_and_glazing':(735,187,1776,482)}.items():
    crop=large.crop(tuple(int(v*4) for v in box));crop.save(REVIEW/f'{name}_4x.png')

# Round-trip parsing and meaningful consistency checks.
results={}
for filename in ['elevation_v2.dxf','elevation_v2_lineweights.dxf']:
    parsed=ezdxf.readfile(OUT/filename); audit=parsed.audit(); ents=list(parsed.modelspace())
    assert not audit.errors and not audit.fixes
    assert len(ents)==len(sc.lines) and all(e.dxftype()=='LINE' for e in ents)
    for ent,item in zip(ents,sc.lines):
        assert ent.dxf.layer==item['layer']
        a,b=item['a'],item['b']
        assert length((ent.dxf.start.x,H-ent.dxf.start.y),a)<1e-7
        assert length((ent.dxf.end.x,H-ent.dxf.end.y),b)<1e-7
    results[filename]={'entities':len(ents),'audit_errors':len(audit.errors),'audit_fixes':len(audit.fixes)}
raw=(OUT/'elevation_v2.dxf').read_text().splitlines()
assert len(raw)%2==0 and raw[0].strip()=='0' and raw[1]=='SECTION' and raw[-1]=='EOF'
parsed_pdf=fitz.open(pdf_path)
assert len(parsed_pdf)==1 and not parsed_pdf[0].get_images(full=True)
paths=parsed_pdf[0].get_drawings()
assert sum(len(p['items']) for p in paths)==len(sc.lines)
pdf_items=[item for path in paths for item in path['items']]
pdf_coordinate_errors=[]
for pdf_item,line_item in zip(pdf_items,sc.lines):
    assert pdf_item[0]=='l'
    for actual,expected in zip(pdf_item[1:], [line_item['a'],line_item['b']]):
        difference=length((actual.x/2,actual.y/2),expected)
        pdf_coordinate_errors.append(difference)
        # Cairo PDF coordinates are quantized; allow 0.002 reference units.
        assert difference<.002
layer_counts=collections.Counter(item['layer'] for item in sc.lines)
group_counts=collections.Counter(item['group'] for item in sc.lines)
report={'method':'Manual geometric reconstruction from the chat-displayed reference; no raster pixel analysis available.',
        'reference_dimensions':[W,H], 'scale':'unitless image proportions; 1 CAD unit corresponds to one reference image coordinate unit',
        'guarantees':'DXF read-back, valid independent line entities, PDF contains no embedded images; visual review only for resemblance.',
        'limits':'Not an exact measured trace. No survey dimensions or claimed 100% line correspondence.',
        'line_entities':len(sc.lines),'layers':dict(layer_counts),'groups':dict(group_counts),
        'dxf':results,'pdf':{'pages':len(parsed_pdf),'raster_images':0,'vector_segments':sum(len(p['items']) for p in paths),'max_coordinate_difference_from_dxf':max(pdf_coordinate_errors),'coordinate_tolerance':.002}}
(OUT/'validation_v2.json').write_text(json.dumps(report,indent=2))
(OUT/'scene_v2.json').write_text(json.dumps({'width':W,'height':H,'lines':sc.lines},indent=2))
print(json.dumps(report,indent=2))
