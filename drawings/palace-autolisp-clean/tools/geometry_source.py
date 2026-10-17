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

BASE=Path('/workspace/palace_lisp'); OUT=BASE/'output'; REVIEW=BASE/'review'
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

def masonry(domain,ystart,yend,h=16,cell=43):
    row=0;y=ystart
    while y<yend:
        rh=min(h,yend-y);x=domain.bounds[0]-(cell*.55 if row%2 else 0)
        while x<domain.bounds[2]:
            cw=cell*random.choice([.55,.75,1.,1.,1.25])
            # Shared stone edges coincide exactly, avoiding artificial double-width mortar gaps.
            if (row+int(x))%4==0 and cw>24:
                sc.add(rect(x,y,cw,rh*.5),'05_STONE_JOINTS',domain)
                sc.add(rect(x,y+rh*.5,cw,rh*.5),'05_STONE_JOINTS',domain)
            else:
                sc.add(rect(x,y,cw,rh),'05_STONE_JOINTS',domain)
            x+=cw
        y+=rh;row+=1

def courses(domain,ys):
    for a,b in zip(ys,ys[1:]):
        if b-a>.5:sc.add(rect(domain.bounds[0],a,domain.bounds[2]-domain.bounds[0],b-a),'05_STONE_JOINTS',domain)

def vent(x,y,w=12,h=24):
    sc.r(x,y,w,h,'03_FRAMES_DOORS')
    sc.r(x+2,y+2,w-4,h-4,'04_GLAZING_SHUTTERS')
    inner=rect(x+2,y+2,w-4,h-4)
    for yy in [y+6,y+12,y+18]:
        sc.add(Polygon([(x+w/2,yy-2),(x+w-2,yy),(x+w/2,yy+2),(x+2,yy)]),'06_ORNAMENT',inner)

def ribband(x,y,w,h,pitch=6):
    sc.r(x,y,w,h,'02_CORNICES')
    n=max(1,round(w/pitch));step=w/n
    for i in range(n):sc.r(x+i*step,y,step,h,'02_CORNICES')

def floral_lattice(domain,pitch=10,r=3.3):
    x0,y0,x1,y1=domain.bounds
    for row in range(int((y1-y0)/pitch)+2):
        y=y0+pitch*.5+row*pitch
        for col in range(int((x1-x0)/pitch)+2):
            x=x0+pitch*.5+col*pitch+(pitch*.5 if row%2 else 0)
            if not domain.intersects(circle(x,y,r,12)):continue
            sc.add(petal_flower(x,y,r,8),'06_ORNAMENT',domain)
            sc.add(circle(x,y,.78,16),'06_ORNAMENT',domain)
            # Small interstitial diamonds join the geometric lattice visually.
            dx=x+pitch*.5;dy=y+pitch*.5
            sc.add(Polygon([(dx,dy-1.35),(dx+1.2,dy),(dx,dy+1.35),(dx-1.2,dy)]),'06_ORNAMENT',domain)

def keystone(cx,y,w=18,h=17):
    p=Polygon([(cx-w/2,y),(cx+w/2,y),(cx+w*.32,y+h),(cx-w*.32,y+h)])
    sc.mask(p)
    sc.add(p,'02_CORNICES');sc.add(p.buffer(-2,join_style='mitre'),'02_CORNICES')

def carved_surround(cx,outer,opening):
    domain=outer.difference(opening.buffer(3,join_style='round'))
    sc.add(outer,'06_ORNAMENT')
    # Rosettes across the head of the stepped stone surround.
    for dx,dy,r in [(-64,392,10),(-36,387,9),(0,383,8),(36,387,9),(64,392,10)]:
        sc.add(petal_flower(cx+dx,dy,r,6),'06_ORNAMENT',domain)
        sc.add(circle(cx+dx,dy,3,20),'06_ORNAMENT',domain)
    # Curving acanthus leaves follow the arch rather than a raster contour.
    for theta in [math.pi+i*math.pi/16 for i in range(17)]:
        px=cx+80*math.cos(theta);py=468+75*math.sin(theta)
        tx,ty=-math.sin(theta),math.cos(theta)
        nx,ny=math.cos(theta),math.sin(theta)
        for direction in [-1,1]:
            end=(px+tx*12+nx*direction*9,py+ty*12+ny*direction*9)
            sc.add(leaf((px-tx*4,py-ty*4),end,4.3),'06_ORNAMENT',domain)
    # Vertical side vines, with alternating pointed leaves and small scrolls.
    for side in [-1,1]:
        x=cx+side*((outer.bounds[2]-outer.bounds[0])/2-12)
        for j,y in enumerate([410,432,454,476,498,520]):
            sc.add(leaf((x,y+10),(x-side*14,y-10),4.2),'06_ORNAMENT',domain)
            sc.add(leaf((x-side*3,y+6),(x+side*5,y-5),3),'06_ORNAMENT',domain)
            sc.add(circle(x-side*8,y+10,4,24),'06_ORNAMENT',domain)
        # Bottom-corner palm-like fan.
        for theta in [-2.6,-2.25,-1.9,-1.55,-1.2]:
            a=(cx+side*85,529);b=(a[0]+side*math.cos(theta)*22,a[1]+math.sin(theta)*22)
            sc.add(leaf(a,b,3.0),'06_ORNAMENT',domain)
    # Small stepped geometric infill at the top corners.
    for side in [-1,1]:
        for xx,yy in [(80,379),(73,406),(88,430),(90,494)]:
            x=cx+side*xx
            sc.add(Polygon([(x-5,yy),(x,yy-5),(x+5,yy),(x,yy+5)]),'06_ORNAMENT',domain)

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
tower_wall=rect(37,152,315,575)
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
for x in [104,136,167,198,230,262]:
    opening=rect(x,170,13,24);sc.mask(opening,groups=['tower_masonry'])
    sc.r(x,170,13,24,'03_FRAMES_DOORS');sc.r(x+3,173,7,18,'03_FRAMES_DOORS')
# Glazed strips on the exposed lower part of the left tower.
sc.group='tower_glazing'
for y,h in [(289,108),(399,108)]:
    sc.mask(rect(39,y,45,h),groups=['tower_masonry'])
    hourglass_panel(39,y,45,h)

# =================== CENTRAL UPPER MASS ===================
sc.group='central_wall'
central=rect(352,247,241,481)
sc.mask(central)
sc.add(central)
courses(central,[247,273,298,324,355,389,430,471,512,553,594,635,676,717,728])
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
left=rect(88,274,264,463)
sc.mask(left);sc.add(left)
courses(left,[274,287,322,350,389,430,471,512,542,565,586,607,629,650,673,696,719,737])
sc.group='left_crown'
sc.mask(rect(77,251,286,35))
sc.add(crenellation(77,251,286,11,h=22,depth=13),'02_CORNICES')
sc.add(Polygon([(77,273),(363,273),(355,285),(85,285)]),'02_CORNICES')
for x in [104,136,167,199,230,262,293,325]:vent(x,291,12,23)
ribband(87,323,266,21,5.5)
sc.r(87,344,266,6,'02_CORNICES')

# =================== RIGHT FRONT WING ===================
sc.group='right_wing'
right=rect(699,274,232,463)
sc.mask(right);sc.add(right)
courses(right,[274,287,322,350,389,430,471,512,542,565,586,607,629,650,673,696,719,737])
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
        panes=[[(cx,642),(cx+14,660),(cx,676),(cx-14,660)],
               [(l,629),(cx,629),(cx,642),(cx-14,660),(l,660)],
               [(cx,629),(r,629),(r,660),(cx+14,660),(cx,642)],
               [(cx+14,660),(r,660),(r,696),(cx,696),(cx,676)],
               [(l,660),(cx-14,660),(cx,676),(cx,696),(l,696)]]
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
    for i in range(12):
        theta=math.tau*i/12
        a=(cx+8*math.cos(theta),cy+8*math.sin(theta));b=(cx+25*math.cos(theta),cy+25*math.sin(theta))
        sc.add(leaf(a,b,4.1),'06_ORNAMENT',glazing)
        theta+=math.pi/12
        a=(cx+22*math.cos(theta),cy+22*math.sin(theta));b=(cx+32*math.cos(theta),cy+32*math.sin(theta))
        sc.add(leaf(a,b,2.7),'06_ORNAMENT',glazing)
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
    for j in range(5):
        a=(647+side*(8+j*7),608-j*4)
        b=(647+side*(15+j*6),574+j*3)
        sc.add(leaf(a,b,4),'06_ORNAMENT',carving)
    for x,y in [(621,581),(632,574),(611,602)]:
        xx=x if side<0 else 1294-x
        sc.add(petal_flower(xx,y,6,6),'06_ORNAMENT',carving)
        sc.add(circle(xx,y,1.7,20),'06_ORNAMENT',carving)
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
sc.r(0,780,W,1,'08_STEPS')
