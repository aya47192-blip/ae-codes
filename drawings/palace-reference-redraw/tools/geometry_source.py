"""Closed, uniform-weight black vector reconstruction of the displayed facade.
Visual reconstruction only: the chat image is not available as a raster file.
The façade remains an elevation; no unseen floor-plan layout is invented.
"""
import sys,math,json,random,collections,hashlib
from pathlib import Path
sys.path.insert(0,'/workspace/elevation/deps')
import shapely
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, Point, box
from shapely import make_valid
import cairocffi as cairo
import ezdxf
import fitz
import pypdfium2 as pdfium

BASE=Path('/workspace/palace_reference'); OUT=BASE/'output'; REVIEW=BASE/'review'
OUT.mkdir(exist_ok=True); REVIEW.mkdir(exist_ok=True)
W,H=988.,785.
LINE_MM=.18
LINE_PT=LINE_MM*72/25.4
LAYERS=['01_STRUCTURE','02_CORNICES','03_FRAMES_DOORS','04_GLAZING_SHUTTERS','05_STONE_JOINTS','06_ORNAMENT','07_RAILINGS','08_STEPS']
random.seed(314159)

def rect(x,y,w,h):return box(x,y,x+w,y+h)
def clean(g):
    if not g.is_valid:g=make_valid(g)
    return g

def polys(g):
    if g.is_empty:return []
    if isinstance(g,Polygon):return [g] if g.area>.055 else []
    if hasattr(g,'geoms'):return [p for q in g.geoms for p in polys(q)]
    return []

def bezier(p0,p1,p2,p3,n=14):
    return [((1-t)**3*p0[0]+3*(1-t)**2*t*p1[0]+3*(1-t)*t*t*p2[0]+t**3*p3[0],
             (1-t)**3*p0[1]+3*(1-t)**2*t*p1[1]+3*(1-t)*t*t*p2[1]+t**3*p3[1]) for t in [i/n for i in range(n+1)]]

def circle(cx,cy,r,n=32):return Polygon([(cx+r*math.cos(2*math.pi*i/n),cy+r*math.sin(2*math.pi*i/n)) for i in range(n)])

def arch(x,top,w,bottom,rise=None,round_top=False):
    cx=x+w/2;rise=rise or w*.34
    spring=top+rise
    if round_top:
        pts=[(x,bottom),(x,spring)]
        pts += [(cx+w/2*math.cos(t),spring+rise*math.sin(t)) for t in [math.pi+i*math.pi/48 for i in range(49)]]
        pts += [(x+w,bottom)]
    else:
        pts=[(x,bottom),(x,spring)]
        pts+=bezier((x,spring),(x,top+rise*.40),(cx-w*.14,top+rise*.08),(cx,top),24)[1:]
        pts+=bezier((cx,top),(cx+w*.14,top+rise*.08),(x+w,top+rise*.40),(x+w,spring),24)[1:]
        pts.append((x+w,bottom))
    return clean(Polygon(pts))

def crenellation(x,y,w,n,h=23,depth=13):
    # Start and finish on complete merlons, without a dangling end spike.
    p=w/(n-.45); pts=[(x,y)]
    for i in range(n):
        a=x+i*p; t=min(x+w,a+p*.55);pts.append((t,y))
        if i<n-1:
            pts.extend([(t+p*.06,y+depth*.4),(t+p*.12,y+depth*.4),
                        (t+p*.17,y+depth),(t+p*.30,y+depth),
                        (t+p*.35,y+depth*.4),(t+p*.40,y+depth*.4),(a+p,y)])
    pts += [(x+w,y+h),(x,y+h)]
    return clean(Polygon(pts))

def leaf(a,b,width):
    dx,dy=b[0]-a[0],b[1]-a[1];d=math.hypot(dx,dy)
    if d<.1:return Polygon()
    nx,ny=-dy/d*width,dx/d*width
    p=bezier(a,(a[0]+dx*.28+nx,a[1]+dy*.28+ny),(b[0]-dx*.22+nx*.7,b[1]-dy*.22+ny*.7),b)
    p+=bezier(b,(b[0]-dx*.25-nx*.7,b[1]-dy*.25-ny*.7),(a[0]+dx*.26-nx,a[1]+dy*.26-ny),a)[1:]
    return clean(Polygon(p))

def petal_flower(cx,cy,r,petals=8):
    return Polygon([(cx+(r*(.76+.24*math.cos(petals*t)))*math.cos(t),cy+(r*(.76+.24*math.cos(petals*t)))*math.sin(t))
                    for t in [i*math.tau/96 for i in range(96)]])

class Scene:
    def __init__(self):self.items=[];self.group=''
    def add(self,g,layer='01_STRUCTURE',domain=None):
        g=clean(g)
        if domain is not None:g=g.intersection(domain)
        for p in polys(g):self.items.append({'poly':p,'layer':layer,'group':self.group})
    def r(self,x,y,w,h,layer='01_STRUCTURE',domain=None):self.add(rect(x,y,w,h),layer,domain)
    def mask(self,g,groups=None):
        result=[];gx0,gy0,gx1,gy1=g.bounds
        for item in self.items:
            if groups is not None and item['group'] not in groups:result.append(item);continue
            x0,y0,x1,y1=item['poly'].bounds
            if gx1<x0 or gx0>x1 or gy1<y0 or gy0>y1:result.append(item);continue
            for p in polys(clean(item['poly'].difference(g))):result.append(dict(item,poly=p))
        self.items=result
    def rings(self):
        result=[];seen=set()
        for item in self.items:
            for ring in [item['poly'].exterior,*item['poly'].interiors]:
                pts=[(round(x,5),round(y,5)) for x,y in list(ring.coords)[:-1]]
                # Remove adjacent duplicates and nearly collinear points.
                pts=[p for i,p in enumerate(pts) if p!=pts[i-1]]
                if len(pts)<3:continue
                if abs(Polygon(pts).area)<.025:continue
                # Ring orientation/start point independent deduplication.
                i=min(range(len(pts)),key=lambda j:pts[j]);forward=pts[i:]+pts[:i]
                reverse=[forward[0]]+list(reversed(forward[1:]));key=tuple(min(forward,reverse))
                if key in seen:continue
                seen.add(key)
                result.append({'points':pts,'layer':item['layer'],'group':item['group']})
        return result

sc=Scene()

def masonry(domain,ystart,yend,h=22,cell=44):
    # Ordered ashlar basketweave visible in the clearer reference: tall blocks
    # alternate with short stacks of horizontal stone strips. No random tiles.
    for row,y in enumerate(range(int(ystart),int(yend),22)):
        for x in range(int(domain.bounds[0])-44+(22 if row%2 else 0),int(domain.bounds[2])+44,44):
            tall_x=x
            stack_x=x+21
            sc.add(rect(tall_x,y,21,min(22,yend-y)),'05_STONE_JOINTS',domain)
            for dy,hh in [(0,5),(5,5),(10,6),(16,6)]:
                if y+dy<yend:sc.add(rect(stack_x,y+dy,23,min(hh,yend-y-dy)),'05_STONE_JOINTS',domain)

def courses(domain,ys):
    for a,b in zip(ys,ys[1:]):
        if b-a>.5:sc.add(rect(domain.bounds[0],a,domain.bounds[2]-domain.bounds[0],b-a),'05_STONE_JOINTS',domain)

def vent(x,y,w=12,h=24):
    sc.r(x,y,w,h,'03_FRAMES_DOORS')
    sc.r(x+2,y+2,w-4,h-4,'04_GLAZING_SHUTTERS')
    inner=rect(x+2,y+2,w-4,h-4)
    for yy in [y+6,y+h-6]:
        rad=min(2.6,(w-4)*.34)
        sc.add(petal_flower(x+w/2,yy,rad,8),'06_ORNAMENT',inner)
        sc.add(circle(x+w/2,yy,max(.4,rad*.23),16),'06_ORNAMENT',inner)

def ribband(x,y,w,h,pitch=6):
    sc.r(x,y,w,h,'02_CORNICES')
    n=max(1,round(w/pitch));step=w/n
    for i in range(n):sc.r(x+i*step,y,step,h,'02_CORNICES')

def oval_leaf(a,b,width):
    cx=(a[0]+b[0])/2;cy=(a[1]+b[1])/2
    dx=b[0]-a[0];dy=b[1]-a[1];d=math.hypot(dx,dy);ux=dx/d;uy=dy/d
    return Polygon([(cx+ux*d*.5*math.cos(t)-uy*width*math.sin(t),
                     cy+uy*d*.5*math.cos(t)+ux*width*math.sin(t))
                    for t in [i*math.tau/40 for i in range(40)]])

def pierced_rosette(cx,cy,r,domain):
    sc.add(circle(cx,cy,r*.14,24),'06_ORNAMENT',domain)
    sc.add(circle(cx,cy,r*.24,32),'06_ORNAMENT',domain)
    for i in range(8):
        t=i*math.tau/8
        a=(cx+r*.29*math.cos(t),cy+r*.29*math.sin(t))
        b=(cx+r*.75*math.cos(t),cy+r*.75*math.sin(t))
        sc.add(oval_leaf(a,b,r*.13),'06_ORNAMENT',domain)
        u=t+math.pi/8
        sc.add(circle(cx+r*.84*math.cos(u),cy+r*.84*math.sin(u),r*.10,20),'06_ORNAMENT',domain)
        sc.add(oval_leaf((cx+r*.75*math.cos(t),cy+r*.75*math.sin(t)),
                         (cx+r*.99*math.cos(t),cy+r*.99*math.sin(t)),r*.095),'06_ORNAMENT',domain)
    sc.add(circle(cx,cy,r*.98,72),'06_ORNAMENT',domain)
    sc.add(circle(cx,cy,r*1.13,72),'06_ORNAMENT',domain)
    # Small perforations around the outer circlet, as in the reference jali.
    for i in range(16):
        t=math.tau*i/16
        sc.add(circle(cx+r*1.05*math.cos(t),cy+r*1.05*math.sin(t),r*.045,12),'06_ORNAMENT',domain)

def floral_lattice(domain,pitch=10,r=3.3):
    # Each leaf carries three large rosettes, rather than an invented daisy grid.
    for pane in polys(domain):
        x0,y0,x1,y1=pane.bounds;cx=(x0+x1)/2
        rad=min((x1-x0)*.40,16.5)
        for cy in [y1-97,y1-58,y1-19]:pierced_rosette(cx,cy,rad,pane)
        # Closely set small perforations fill the margins between the rosettes.
        for yy in [y0+4+i*5 for i in range(int((y1-y0)/5))]:
            for xx in [x0+2.4,x1-2.4]:
                if pane.contains(Point(xx,yy)):
                    sc.add(circle(xx,yy,1.05,16),'06_ORNAMENT',pane)
        for cy in [y1-78,y1-39]:
            for dx in [-9,0,9]:
                sc.add(petal_flower(cx+dx,cy,2.6,4),'06_ORNAMENT',pane)

def keystone(cx,y,w=18,h=17):
    p=Polygon([(cx-w/2,y),(cx+w/2,y),(cx+w*.32,y+h),(cx-w*.32,y+h)])
    sc.mask(p)
    sc.add(p,'02_CORNICES');sc.add(p.buffer(-2,join_style='mitre'),'02_CORNICES')

def scroll_outline(cx,cy,w,h,mirror=1):
    # Smooth closed C-scroll traced through visual anchors; no angular fish-like corners.
    control=[(-.5,.44),(-.5,-.14),(-.24,-.5),(.16,-.48),(.48,-.24),(.40,.03),
             (.13,.12),(-.02,-.06),(.12,-.19),(-.11,-.20),(-.25,.02),(-.16,.30),(.25,.48)]
    points=[];n=len(control)
    for i in range(n):
        p0,p1,p2,p3=[control[j%n] for j in [i-1,i,i+1,i+2]]
        for k in range(8):
            t=k/8;t2=t*t;t3=t2*t
            xy=[.5*((2*p1[d])+(-p0[d]+p2[d])*t+(2*p0[d]-5*p1[d]+4*p2[d]-p3[d])*t2+(-p0[d]+3*p1[d]-3*p2[d]+p3[d])*t3) for d in [0,1]]
            points.append((cx+mirror*xy[0]*w,cy+xy[1]*h))
    return clean(Polygon(points))

def carved_surround(cx,outer,opening):
    domain=outer.difference(opening.buffer(2.5,join_style='round'))
    sc.add(outer,'06_ORNAMENT')
    # Crown leaves over the keystone, read as a fan in the clearer reference.
    for dx,yy in [(-26,384),(-18,378),(-9,375),(0,374),(9,375),(18,378),(26,384)]:
        sc.add(leaf((cx+dx*.20,391),(cx+dx,yy),2.5),'06_ORNAMENT',domain)
    for side in [-1,1]:
        # Curled heads along the arched band, replacing the former row of daisies.
        for dx,yy,w,h in [(79,382,12,16),(62,385,17,10),(45,380,15,10),(80,404,12,20),(94,420,11,18)]:
            sc.add(scroll_outline(cx+side*dx,yy,w,h,side),'06_ORNAMENT',domain)
        for aa,bb in [((30,389),(59,379)),((47,399),(72,390)),((68,413),(89,399)),((90,434),(100,414))]:
            a=(cx+side*aa[0],aa[1]);b=(cx+side*bb[0],bb[1])
            sc.add(leaf(a,b,3.6),'06_ORNAMENT',domain)
        for dx,yy in [(87,438),(87,495),(79,511)]:
            sc.add(scroll_outline(cx+side*dx,yy,15,19,side),'06_ORNAMENT',domain)
        # The dominant radiating acanthus fan at the sides of each window.
        for j,(dx,yy) in enumerate([(101,432),(104,441),(106,452),(105,464),(103,477),(96,489),(84,495)]):
            a=(cx+side*(69+j*.45),464+j*.55)
            b=(cx+side*dx,yy)
            sc.add(leaf(a,b,4.1),'06_ORNAMENT',domain)
        # Lower scrolls and border leaflets visible below the radiating fans.
        for dx,yy,w,h in [(98,500,14,14),(90,513,17,14),(99,528,12,15),(77,529,13,16)]:
            sc.add(scroll_outline(cx+side*dx,yy,w,h,side),'06_ORNAMENT',domain)
        for j in range(4):
            sc.add(leaf((cx+side*78,531-j*3),(cx+side*(91+j*3),516-j*8),2.2),'06_ORNAMENT',domain)

def upper_balcony(cx,left,right):
    # Projection, stepped stone carving panel, nested pointed arch and two leaves.
    x=left;y=371;w=right-left
    surround=Polygon([(x,542),(x,386),(x+16,386),(x+16,371),(right-16,371),(right-16,386),(right,386),(right,542)])
    sc.mask(surround)
    window=arch(cx-61,400,122,531,rise=28)
    sc.add(window,'03_FRAMES_DOORS')
    sc.add(arch(cx-54,407,108,531,rise=27),'03_FRAMES_DOORS')
    inner=arch(cx-47,415,94,529,rise=24)
    sc.add(inner,'03_FRAMES_DOORS')
    sc.r(cx-2.5,416,5,113,'03_FRAMES_DOORS',inner)
    floral_lattice(inner.difference(rect(cx-3,413,6,119)),pitch=10.2,r=3.25)
    carved_surround(cx,surround,window)
    keystone(cx,391,20,17)
    # Clear balcony front: boundaries closed, ornaments remain visible behind it.
    sc.r(cx-66,487,132,56,'07_RAILINGS')
    sc.r(cx-62,490,124,39,'07_RAILINGS')
    for xx in [cx-49,cx+49]:sc.r(xx,490,2,39,'07_RAILINGS')
    sc.r(cx-1,490,2,39,'07_RAILINGS')

def hourglass_panel(x,y,w,h):
    sc.r(x,y,w,h,'04_GLAZING_SHUTTERS')
    sc.r(x+3,y+3,w-6,h-6,'04_GLAZING_SHUTTERS')
    l=x+5;r=x+w-5;cx=x+w/2;top=y+5;bot=y+h-5;mid=y+h*.5
    pts=[(l,top),(r,top),(r,top+12),(cx+3,mid-8),(r-2,mid+24),(cx,mid+34),(l+2,mid+24),(cx-3,mid-8),(l,top+12)]
    sc.add(Polygon(pts),'04_GLAZING_SHUTTERS',rect(x+3,y+3,w-6,h-6))
    sc.add(Polygon([(l,bot),(r,bot),(r,bot-8),(cx+2,bot-20),(r-1,bot-30),(cx,bot-38),(l+1,bot-30),(cx-2,bot-20),(l,bot-8)]),'04_GLAZING_SHUTTERS',rect(x+3,y+3,w-6,h-6))

# =================== BACK TOWER ===================
sc.group='tower_masonry'
tower_wall=rect(37,152,315,628)
sc.add(tower_wall)
masonry(tower_wall,153,727,h=14,cell=37)
sc.group='tower_crown'
sc.add(crenellation(25,85,338,12,h=23,depth=14),'02_CORNICES')
sc.add(Polygon([(25,108),(363,108),(356,117),(32,117)]),'02_CORNICES')
sc.r(33,117,320,10,'02_CORNICES')
ribband(37,129,315,22,5.5)
sc.r(36,126,317,4,'02_CORNICES')
sc.r(37,151,315,3,'02_CORNICES')
# Six small inset slit windows across the upper ashlar wall.
for x in [104,136,168,200,232,264]:
    opening=rect(x,170,13,24);sc.mask(opening,groups=['tower_masonry'])
    sc.r(x,170,13,24,'03_FRAMES_DOORS');sc.r(x+3,173,7,18,'03_FRAMES_DOORS')
# Glazed strips on the exposed lower part of the left tower.
sc.group='tower_glazing'
for y,h in [(289,108),(399,108)]:
    sc.mask(rect(39,y,45,h),groups=['tower_masonry'])
    hourglass_panel(39,y,45,h)

# =================== CENTRAL UPPER MASS ===================
sc.group='central_wall'
central=rect(352,247,241,533)
sc.mask(central)
sc.add(central)
courses(central,[247,273,298,324,355,389,430,471,512,553,594,635,676,717,728,780])
sc.group='central_crown'
# Front return of the battlement overlaps the high tower at the left.
sc.mask(rect(329,214,275,34))
sc.add(crenellation(329,214,275,11,h=21,depth=13),'02_CORNICES')
sc.r(339,235,255,12,'02_CORNICES')
sc.r(351,247,242,25,'02_CORNICES')
sc.r(351,272,242,5,'02_CORNICES')
sc.r(351,277,242,20,'02_CORNICES')
sc.r(351,297,242,4,'02_CORNICES')
sc.r(485,248,1.1,24,'02_CORNICES')

# =================== RECESSED RIGHT BAY ===================
sc.group='recess_wall'
recess=rect(593,261,106,283)
sc.mask(recess);sc.add(recess)
for x in [614,641,668]:vent(x,290,12,24)
# Pair of patterned arch leaves behind the narrow balcony.
recess_window=arch(601,408,91,532,rise=21)
sc.mask(recess_window,groups=['recess_wall']);sc.add(recess_window,'03_FRAMES_DOORS')
sc.add(arch(607,415,79,530,rise=20),'03_FRAMES_DOORS')
inner=arch(611,419,71,530,rise=20)
sc.add(inner,'03_FRAMES_DOORS');sc.r(645,420,3,110,'03_FRAMES_DOORS',inner)
floral_lattice(inner.difference(rect(644,417,5,117)),pitch=9.5,r=3.1)
sc.r(594,487,105,57,'07_RAILINGS');sc.r(600,491,93,38,'07_RAILINGS')
sc.r(644,491,3,38,'07_RAILINGS')

# =================== LEFT FRONT WING ===================
sc.group='left_wing'
left=rect(88,274,264,506)
sc.mask(left);sc.add(left)
courses(left,[274,287,322,350,389,430,471,512,542,565,586,607,629,650,673,696,719,737,780])
sc.group='left_crown'
sc.mask(rect(77,251,286,35))
sc.add(crenellation(77,251,286,11,h=22,depth=13),'02_CORNICES')
sc.add(Polygon([(77,273),(363,273),(355,285),(85,285)]),'02_CORNICES')
for x in [104,136,167,199,230,262,293,325]:vent(x,291,12,23)
ribband(87,323,266,21,5.5)
sc.r(87,344,266,6,'02_CORNICES')

# =================== RIGHT FRONT WING ===================
sc.group='right_wing'
right=rect(699,274,232,506)
sc.mask(right);sc.add(right)
courses(right,[274,287,322,350,389,430,471,512,542,565,586,607,629,650,673,696,719,737,780])
sc.group='right_crown'
sc.mask(rect(688,251,254,35))
sc.add(crenellation(688,251,254,10,h=22,depth=13),'02_CORNICES')
sc.add(Polygon([(688,273),(942,273),(934,285),(696,285)]),'02_CORNICES')
for x in [714,746,778,810,842,874,905]:vent(x,291,12,23)
ribband(698,323,234,21,5.4)
sc.r(698,344,234,6,'02_CORNICES')

# Central projecting cornice joins the two primary masses.
sc.group='central_cornice'
sc.mask(rect(352,324,253,32),groups=['central_wall'])
ribband(352,324,253,22,18)
for x in [357,363,369,375,381,559,565,571,577,583,589,595,601]:sc.r(x,324,2,22,'02_CORNICES')
sc.add(Polygon([(352,346),(605,346),(597,356),(352,356)]),'02_CORNICES')

# =================== THREE TALL CENTRAL WINDOWS ===================
sc.group='central_windows'
for x,w,inner_x,inner_w in [(367,59,381,32),(435,80,445,60),(524,59,538,31)]:
    outer=arch(x,400,w,711,rise=29,round_top=True)
    sc.mask(outer,groups=['central_wall'])
    sc.add(outer,'03_FRAMES_DOORS')
    sc.add(arch(x+5,406,w-10,706,rise=27,round_top=True),'03_FRAMES_DOORS')
    sc.add(arch(x+9,411,w-18,701,rise=25,round_top=True),'03_FRAMES_DOORS')
    sc.add(Polygon([(x,708),(x+w,708),(x+w-5,717),(x+5,717)]),'03_FRAMES_DOORS')
    glass=arch(inner_x,416,inner_w,699,rise=21)
    sc.add(glass,'04_GLAZING_SHUTTERS')
    # Upper leaded glass has closed lozenges and kite shapes, not open crossings.
    topdom=glass.intersection(rect(inner_x,414,inner_w,70))
    cx=inner_x+inner_w/2
    if w>65:
        sc.add(Polygon([(cx,419),(cx+14,437),(cx,451),(cx-14,437)]),'04_GLAZING_SHUTTERS',topdom)
        sc.add(Polygon([(inner_x+2,435),(cx-3,452),(cx-10,482),(inner_x+2,482)]),'04_GLAZING_SHUTTERS',topdom)
        sc.add(Polygon([(inner_x+inner_w-2,435),(cx+3,452),(cx+10,482),(inner_x+inner_w-2,482)]),'04_GLAZING_SHUTTERS',topdom)
    else:
        sc.add(Polygon([(cx,418),(cx+10,431),(cx+3,444),(cx+10,480),(cx-10,480),(cx-3,444),(cx-10,431)]),'04_GLAZING_SHUTTERS',topdom)
    # Rectangular shutter leaves and individual closed slats.
    sc.r(inner_x,484,inner_w,141,'04_GLAZING_SHUTTERS')
    for y in [485+i*6.8 for i in range(21)]:
        sc.r(inner_x+1,y,inner_w-2,4.7,'04_GLAZING_SHUTTERS')
    sc.r(inner_x+1,627,inner_w-2,71,'04_GLAZING_SHUTTERS')
    lower=rect(inner_x+3,629,inner_w-6,67)
    if w>65:
        l,r=inner_x+3,inner_x+inner_w-3
        panes=[[(l+6,629),(r-6,629),(cx+14,653),(cx,664),(cx-14,653)],
               [(cx,664),(cx+14,677),(cx,690),(cx-14,677)],
               [(l,629),(l+6,629),(cx-14,653),(cx,664),(cx-14,677),(cx,690),(cx,696),(l,696)],
               [(r-6,629),(r,629),(r,696),(cx,696),(cx,690),(cx+14,677),(cx,664),(cx+14,653)]]
        for pane in panes:sc.add(Polygon(pane),'04_GLAZING_SHUTTERS',lower)
    else:
        sc.add(Polygon([(cx-8,630),(cx+8,630),(cx+8,657),(cx+3,668),(cx+8,683),(cx+8,696),(cx-8,696),(cx-8,683),(cx-3,668),(cx-8,657)]),'04_GLAZING_SHUTTERS',lower)

# =================== UPPER ORNATE BALCONIES ===================
sc.group='left_balcony';upper_balcony(220,114,326)
sc.group='right_balcony';upper_balcony(815,725,905)
# Narrow side railings join the carved frames to the wall pilasters.
sc.group='side_rails'
for x,y,w in [(88,399,26),(326,399,26),(699,399,26)]:
    sc.r(x,y,w,23,'07_RAILINGS')
    for xx in [x+5,x+11,x+17,x+23]:
        if xx<x+w:sc.r(xx,y,1.3,23,'07_RAILINGS')

# =================== FIRST-FLOOR PILASTERS / BELT CORNICE ===================
sc.group='left_pilasters'
for x in [88,326]:
    sc.mask(rect(x,422,26,118),groups=['left_wing'])
    sc.r(x,422,26,113,'01_STRUCTURE')
    sc.r(x-2,535,30,7,'02_CORNICES')
sc.group='right_pilasters'
for x in [699,905]:
    sc.mask(rect(x,422,26,118),groups=['right_wing'])
    sc.r(x,422,26,113,'01_STRUCTURE')
    sc.r(x-2,535,30,7,'02_CORNICES')
sc.group='belt_cornices'
for x,w in [(77,287),(698,244)]:
    sc.mask(rect(x,542,w,24))
    sc.add(Polygon([(x,542),(x+w,542),(x+w-1,556),(x+w-7,564),(x+6,564),(x,556)]),'02_CORNICES')
    sc.r(x+4,539,w-8,4,'02_CORNICES')
    sc.r(x+2,558,w-4,7,'02_CORNICES')

# =================== LOWER DECORATIVE VENTS ===================
sc.group='lower_vents'
for x in [152,171,190,244,263,282,748,766,785,838,857,876]:
    opening=rect(x,577,8,19);sc.mask(opening,groups=['left_wing','right_wing'])
    vent(x,577,8,19)

# =================== LOWER ARCHES AND ROSE WINDOWS ===================
def fluted_column(x,y,w,h):
    sc.mask(rect(x,y,w,h),groups=['left_wing','right_wing','ground_left','ground_right'])
    sc.r(x,y,w,h,'03_FRAMES_DOORS')
    for a in [2.5,5,7.5,10,12.5,15]:
        if a<w-1:sc.r(x+a,y+1,1.1,h-2,'03_FRAMES_DOORS')

def rose_window(cx,top,bottom,w):
    outer=arch(cx-w/2,top,w,bottom,rise=w*.47,round_top=True)
    sc.mask(outer,groups=['left_wing','right_wing'])
    sc.add(outer,'03_FRAMES_DOORS')
    for d in [4,8]:sc.add(arch(cx-w/2+d,top+d,w-2*d,bottom,rise=(w-2*d)*.47,round_top=True),'03_FRAMES_DOORS')
    glazing=arch(cx-w/2+10,top+11,w-20,699,rise=(w-20)*.47,round_top=True)
    sc.add(glazing,'04_GLAZING_SHUTTERS')
    cy=top+46
    sc.add(circle(cx,cy,5,32),'06_ORNAMENT',glazing)
    sc.add(circle(cx,cy,7,32),'06_ORNAMENT',glazing)
    for i in range(8):
        theta=math.tau*i/8
        a=(cx+8*math.cos(theta),cy+8*math.sin(theta));b=(cx+26*math.cos(theta),cy+26*math.sin(theta))
        sc.add(oval_leaf(a,b,5.0),'06_ORNAMENT',glazing)
        u=theta+math.pi/8
        a=(cx+22*math.cos(u),cy+22*math.sin(u));b=(cx+33*math.cos(u),cy+33*math.sin(u))
        sc.add(oval_leaf(a,b,3.6),'06_ORNAMENT',glazing)
        sc.add(circle(cx+30*math.cos(theta),cy+30*math.sin(theta),2.5,20),'06_ORNAMENT',glazing)
    for yy in [top+20,top+70]:
        for side in [-1,1]:sc.add(petal_flower(cx+side*17,yy,4,6),'06_ORNAMENT',glazing)
    sc.r(cx-w/2+9,700,w-18,36,'04_GLAZING_SHUTTERS')
    for yy in [700,708,717,726]:sc.r(cx-w/2+9,yy,w-18,8,'04_GLAZING_SHUTTERS')
    keystone(cx,top-11,19,17)

# Ground-floor arched window and door, left wing.
sc.group='ground_left'
rose_window(173,620,737,80)
# Pilasters and joined impost caps below the arches.
for x,w in [(119,18),(210,20),(303,18)]:fluted_column(x,658,w,79)
for x,w in [(106,33),(207,27),(299,36)]:
    cap=Polygon([(x,645),(x+w,645),(x+w-5,651),(x+w-5,658),(x+11,658),(x+7,651)])
    sc.mask(cap,groups=['left_wing','ground_left']);sc.add(cap,'02_CORNICES')
# Pointed-topped entrance, including lower panel and upper inset panel.
left_door=arch(236,617,61,751,rise=30,round_top=True)
sc.mask(left_door,groups=['left_wing']);sc.add(left_door,'03_FRAMES_DOORS')
sc.add(arch(241,623,51,747,rise=27,round_top=True),'03_FRAMES_DOORS')
sc.add(arch(247,635,39,686,rise=18,round_top=True),'03_FRAMES_DOORS')
sc.add(arch(252,641,29,681,rise=14,round_top=True),'03_FRAMES_DOORS')
sc.r(247,696,39,44,'03_FRAMES_DOORS');sc.r(252,701,29,34,'03_FRAMES_DOORS')
keystone(266.5,608,19,16)

# Right-hand paired arched rose windows.
sc.group='ground_right'
for cx in [769,857]:rose_window(cx,620,737,80)
for x,w in [(718,18),(806,18),(895,18)]:fluted_column(x,658,w,79)
for x,w in [(710,28),(801,28),(892,37)]:
    cap=Polygon([(x,645),(x+w,645),(x+w-5,651),(x+w-5,658),(x+10,658),(x+7,651)])
    sc.mask(cap,groups=['right_wing','ground_right']);sc.add(cap,'02_CORNICES')

# =================== PROJECTING CENTRAL DOOR AND CARVED TYMPANUM ===================
sc.group='front_entry'
entry=rect(580,543,134,218)
sc.mask(entry)
sc.add(entry,'01_STRUCTURE')
sc.r(592,557,110,202,'03_FRAMES_DOORS')
sc.r(598,563,98,196,'03_FRAMES_DOORS')
# Leaf-patterned pointed pediment above the ground door.
entry_arch=arch(604,593,86,758,rise=35)
sc.add(entry_arch,'03_FRAMES_DOORS')
carving=rect(601,567,92,78).difference(entry_arch)
for side in [-1,1]:
    root=(647+side*42,571)
    for dx,yy in [(37,605),(29,600),(21,593),(13,584),(8,574)]:
        sc.add(leaf(root,(647+side*dx,yy),2.6),'06_ORNAMENT',carving)
for yy in [570,577,584]:
    for dx in [-6,0,6]:
        x=647+dx
        sc.add(Polygon([(x,yy-3),(x+3,yy),(x,yy+3),(x-3,yy)]),'06_ORNAMENT',carving)
# Curved door surround and closed inset panels.
sc.add(arch(609,615,76,755,rise=34,round_top=True),'03_FRAMES_DOORS')
sc.add(arch(616,625,62,752,rise=28,round_top=True),'03_FRAMES_DOORS')
sc.add(arch(621,631,52,749,rise=24,round_top=True),'03_FRAMES_DOORS')
sc.add(arch(629,641,36,686,rise=17,round_top=True),'03_FRAMES_DOORS')
sc.add(arch(633,646,28,681,rise=14,round_top=True),'03_FRAMES_DOORS')
sc.r(628,696,38,43,'03_FRAMES_DOORS');sc.r(633,701,28,33,'03_FRAMES_DOORS')
keystone(647,607,18,17)

# =================== STEPS AND BASELINE ===================
sc.group='steps'
for x,y,w,h in [(236,751,62,6),(222,758,91,5),(208,764,119,6),(193,771,148,6),
                 (595,754,100,6),(583,760,124,6),(571,766,148,6),(559,772,172,7)]:
    sc.r(x,y,w,h,'08_STEPS')
sc.r(-133,781,1220,7,'08_STEPS')
