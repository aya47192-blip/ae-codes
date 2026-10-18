import os
from pathlib import Path
import sys,json,math,collections
import numpy as np,cv2,ezdxf,cairocffi as cairo
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d
from shapely import LineString,Polygon,box,unary_union,line_merge
from PIL import Image
ROOT=Path(__file__).parent;OUT=Path(os.environ.get('FACADE_OUTPUT',str(ROOT/'output')));OUT.mkdir(exist_ok=True)
SRC=Path(os.environ.get('FACADE_SOURCE',str(Path(__file__).resolve().parents[3]/'IMG_3106.PNG')));A=np.asarray(Image.open(SRC).convert('L')).astype(float)
W,H=1774,887;MM=20000/1768
lines=[];arcs=[];curves=[]
def line(x1,y1,x2,y2,layer='ARCH'):
 if math.hypot(x2-x1,y2-y1)>.00001:lines.append(([float(x1),float(y1)],[float(x2),float(y2)],layer))
def poly(pts,closed=False,layer='ARCH'):
 for a,b in zip(pts,pts[1:]):line(*a,*b,layer)
 if closed:line(*pts[-1],*pts[0],layer)
def rect(x1,y1,x2,y2,layer='ARCH'):poly([(x1,y1),(x2,y1),(x2,y2),(x1,y2)],True,layer)
def h(y,x1,x2,layer='ARCH'):line(x1,y,x2,y,layer)
def v(x,y1,y2,layer='ARCH'):line(x,y1,x,y2,layer)
def arch(xl,xr,yend,ytop,layer='WINDOWS'):
 c=(xl+xr)/2;a=(xr-xl)/2;rise=yend-ytop;r=(a*a+rise*rise)/(2*rise);cy=ytop+r
 angle=math.degrees(math.atan2(cy-yend,a))
 arcs.append({'center':[c,cy],'radius':r,'start':angle,'end':180-angle,'layer':layer})
 return (xl,yend),(xr,yend)
def aframe(xl,xr,yend,ytop,bottom,layer='WINDOWS',baseline=True):
 arch(xl,xr,yend,ytop,layer);v(xl,yend,bottom,layer);v(xr,yend,bottom,layer)
 if baseline:h(bottom,xl,xr,layer)
def curve_y(xl,xr,yend,ytop,x):
 c=(xl+xr)/2;a=(xr-xl)/2;rise=yend-ytop;r=(a*a+rise*rise)/(2*rise)
 return ytop+r-math.sqrt(max(0,r*r-(x-c)**2))
KEYSTONES=[]
def keystone(c,y):
 KEYSTONES.append(Polygon([(c-8,y),(c+8,y),(c+5,y+17),(c-5,y+17)]))
 poly([(c-8,y),(c+8,y),(c+5,y+17),(c-5,y+17)],True,'WINDOWS')
def probe_minima(profile,lo,hi,prom=20):
 smooth=gaussian_filter1d(profile,.38)
 inds,_=find_peaks(-smooth[lo:hi],prominence=prom,distance=2)
 result=[]
 for i in inds+lo:
  den=smooth[i-1]-2*smooth[i]+smooth[i+1]
  d=(smooth[i-1]-smooth[i+1])/(2*den) if den else 0
  result.append(round(i+max(-.5,min(.5,d)),3))
 return result
FLUTE_RUNS=[]
def flutes(x1,x2,y1,y2,probe=(380,440),layer='LOUVERS'):
 rect(x1,y1,x2,y2,layer)
 prof=np.mean(A[probe[0]:probe[1]],axis=0)
 pp=probe_minima(prof,int(x1),int(x2)+1,15)
 pp=[x for x in pp if x1+.8<x<x2-.8]
 for x in pp:v(x,y1,y2,layer)
 FLUTE_RUNS.append({'x':[x1,x2],'y':[y1,y2],'measured_internal_lines':pp})
# Ground and base plinths, source coordinates.
h(832,1,1768,'GROUND')
for x1,x2 in [(55,247),(1525,1718)]:rect(x1,816,x2,832)
for x1,x2 in [(250,697),(1072,1520)]:rect(x1,813,x2,832);h(818,x1,x2)
# Outer wings and floor strings.
for side in [0,1]:
 left=side==0;x1,x2=(58,247) if left else (1525,1715)
 v(x1,335,567);v(x1,584,816);v(x2,335,497);v(x2,584,816)
 rect(x1-3,567,x2,584);h(579,x1-3,x2)
 for y in [406,438,651,686]:
  h(y,x1,91 if left else 1535);h(y,238 if left else 1682,x2)
 # Roof slope/eaves, stepped cornice; measured on each side.
 if left:
  poly([(58,312),(58,259),(143,259),(143,272),(168,272),(168,259),(247,259)])
  poly([(56,259),(56,253),(149,253),(149,267),(163,267),(163,253),(247,253)])
  poly([(40,319),(122,284),(247,284)])
  poly([(40,319),(40,323),(49,327),(49,331),(53,331),(53,337),(247,337)])
  h(319,40,247);h(324,43,247);h(331,49,247)
 else:
  poly([(1715,313),(1715,259),(1629,259),(1629,272),(1605,272),(1605,259),(1525,259)])
  poly([(1718,259),(1718,253),(1612,253),(1612,267),(1625,267),(1625,253),(1525,253)])
  poly([(1734,319),(1652,284),(1525,284)])
  poly([(1734,319),(1734,323),(1726,327),(1726,331),(1722,331),(1722,337),(1525,337)])
  h(319,1525,1734);h(324,1525,1731);h(331,1525,1726)
# Main outer masonry bays: continuous straight edges.
for x1,x2 in [(247,702),(1065,1525)]:
 v(x1,259,497);v(x2,259,497);v(x1,514,832);v(x2,514,832)
 rect(x1-5,497,x2+8,503);poly([(x1-5,503),(x1-1,510),(x1-1,515),(x2+3,515),(x2+3,510),(x2+8,503)])
 dx=0 if x1==247 else 809
 for yy,le,re in [(318,355,606),(324,358,601),(336,367,594)]:h(yy,x1,le+dx);h(yy,re+dx,x2)
# Central structural shaft and horizontal wall bands.
rect(845,264,925,832)
poly([(830,230),(941,230),(941,237),(936,241),(932,246),(932,263),(839,263),(839,246),(835,241),(830,237)],True)
h(238,831,940);h(245,838,933)
for a,b in [(703,845),(925,1065)]:
 h(284,a,b);h(318,a,b);h(325,a,b);h(337,a,b);h(583,a,b);h(593,a,b)
 h(398,a,727 if a==703 else 948);h(398,823 if a==703 else 1044,b)
 # The upper notched parapet is reconstructed as a measured profile.
if True:
 poly([(704,253),(761,253),(761,267),(776,267),(776,253),(839,253)])
 poly([(704,260),(755,260),(755,272),(782,272),(782,260),(839,260)])
 poly([(932,253),(986,253),(986,267),(1002,267),(1002,253),(1065,253)])
 poly([(932,260),(980,260),(980,272),(1008,272),(1008,260),(1065,260)])
# Upper level parapet panels behind the plants.
for a,b in [(379,587),(1181,1395)]:h(253,a,b);h(260,a,b);h(284,a,b)
for a,b in [(247,379),(587,703),(1065,1181),(1395,1525)]:
 rect(a,235,b,259)
# Roof posts and their moulded caps.
for xl,xr in [(262,329),(1445,1512)]:
 rect(xl,129,xr,157);h(160,xl,xr);v(xl,157,228);v(xr,157,228)
 poly([(xl-5,109),(xr+7,109),(xr+7,118),(xr+4,118),(xr+3,123),(xr,128),(xl,128),(xl-2,123),(xl-4,119),(xl-5,119)],True)
 h(119,xl-4,xr+6);h(125,xl-1,xr+1)
# Horizontal roof rail pieces, clipped at central feature frames.
for a,b in [(329,649),(683,792),(868,913),(981,1075),(1114,1445)]:
 for y in [140,146,157,163]:h(y,a,b)
for a,b in [(649,683),(1075,1114)]:
 rect(a-2,137,b+1,145);rect(a,145,b,158);h(163,a,b);v(a,163,228);v(b,163,228)
for x in [393,398,1376,1381]:v(x,163,253)
# Two tall roof light panels: exact rectangular trim and glazing.
roof_details_start=len(lines)
for xl,xr in [(792,868),(913,981)]:
 rect(xl,156,xr,253);rect(xl+5,160,xr-5,253)
 gx1,gx2=xl+14,xr-14
 rect(gx1,169,gx2,225);rect(gx1+4,173,gx2-4,222);rect(gx1+7,176,gx2-7,219)
 rect(gx1,226,gx2,253)
 for y in probe_minima(np.mean(A[:,int(gx1+6):int(gx2-6)],axis=1),228,252,10):h(y,gx1+2,gx2-2,'LOUVERS')
 # Two visible diagonal reflection strokes, measured endpoints.
 line(gx1+12,211,gx2-10,180,'GLASS');line(gx1+13,215,gx2-10,187,'GLASS')
chimney=Polygon([(830,230),(941,230),(941,237),(936,241),(932,246),(932,263),(839,263),(839,246),(835,241),(830,237)])
roof_detail_lines=lines[roof_details_start:];lines=lines[:roof_details_start]
for a,b,layer in roof_detail_lines:
 ls=LineString([a,b]).difference(chimney)
 for g in ([ls] if ls.geom_type=='LineString' else getattr(ls,'geoms',[])):
  if not g.is_empty and g.geom_type=='LineString':line(*g.coords[0],*g.coords[-1],layer)
# Large window cornices: all profiles now real straight segments.
for dx in [0,809]:
 poly([(355+dx,309),(373+dx,297),(585+dx,297),(606+dx,309)],False)
 poly([(355+dx,309),(606+dx,309),(606+dx,315),(355+dx,315)],True)
 poly([(355+dx,315),(355+dx,320),(362+dx,323),(598+dx,323),(606+dx,320),(606+dx,315)])
 rect(358+dx,323,601+dx,328)
 poly([(367+dx,328),(594+dx,328),(594+dx,332),(591+dx,335),(591+dx,339),(369+dx,339),(369+dx,335),(367+dx,332)],True)
 h(343,370+dx,591+dx);h(338,369+dx,592+dx)
 # Window side columns and outboard louver groups.
 flutes(367+dx,414+dx,343,496)
 flutes(550+dx,594+dx,343,496)
 flutes(287+dx if dx==0 else 1099,337+dx if dx==0 else 1146,327,496)
 flutes(624+dx if dx==0 else 1435,671+dx if dx==0 else 1485,327,496)
 # Main arched upper window, stepped contours and central mullion.
 for xl,xr,ye,yt in [(414,550,386,366),(420,545,390,375),(424,541,393,381)]:aframe(xl+dx,xr+dx,ye,yt,496)
 v(479+dx,curve_y(424,541,393,381,479),496,'WINDOWS');v(486+dx,curve_y(424,541,393,381,486),496,'WINDOWS')
 # Main planter face, louver belt and lower moulding.
 rect(358+dx,498,601+dx,546)
 rect(359+dx,546,600+dx,572)
 flutes(360+dx,599+dx,548,571,probe=(550,569))
 rect(357+dx,572,601+dx,579)
 poly([(359+dx,579),(365+dx,585),(367+dx,593),(592+dx,593),(594+dx,585),(599+dx,579)])
 h(589,366+dx,593+dx)
 # Ground floor arched window and fluted side trim.
 for xl,xr,ye,yt in [(413,550,639,615),(419,545,642,622),(423,541,646,628)]:aframe(xl+dx,xr+dx,ye,yt,748)
 v(479+dx,curve_y(423,541,646,628,479),748,'WINDOWS');v(486+dx,curve_y(423,541,646,628,486),748,'WINDOWS')
 flutes(386+dx,413+dx,638,746,probe=(650,700))
 flutes(550+dx,579+dx,638,746,probe=(650,700))
 rect(367+dx,749,595+dx,756);rect(373+dx,756,589+dx,779);h(781,373+dx,589+dx)
 # Narrow inset lights in the masonry.
 for xx in [302+dx if dx==0 else 1115,644+dx if dx==0 else 1458]:
  rect(xx,533,xx+11,608);rect(xx+3,537,xx+8,603)
# Outer paired arched window stacks.
for cx in [163,1607]:
 for dy in [0,250]:
  aframe(cx-43,cx+43,386+dy,362+dy,489+dy)
  aframe(cx-37,cx+37,389+dy,372+dy,489+dy)
  aframe(cx-32,cx+32,393+dy,380+dy,489+dy)
  v(cx-3,curve_y(cx-32,cx+32,393+dy,380+dy,cx-3),489+dy,'WINDOWS');v(cx+3,curve_y(cx-32,cx+32,393+dy,380+dy,cx+3),489+dy,'WINDOWS')
  keystone(cx,351+dy)
  flutes(cx-72,cx-44,374+dy,488+dy,probe=(400,440) if not dy else (650,700))
  flutes(cx+46,cx+75,374+dy,488+dy,probe=(400,440) if not dy else (650,700))
 # Upper and lower simple trough planters, as visible in reference.
 for y in [495,742]:
  if cx==163:x1,x2=(89,213) if y==495 else (90,225)
  else:x1,x2=(1559,1685) if y==495 else (1546,1684)
  bottom=542 if y==495 else 788
  rect(x1,y,x2,bottom)
  v(x1+4,y+4,bottom-4);v(x2-4,y+4,bottom-4)
  for yy in probe_minima(np.mean(A[:,int(x1+25):int(x2-25)],axis=1),y+4,bottom-3,12):h(yy,x1+4,x2-4)
  h(bottom-2,x1-2,x2+2)
# Central upper windows: source positions, multiple exact circular arch trims.
for cx in [775,996]:
 for xl,xr,ye,yt in [(cx-48,cx+48,380,354),(cx-40,cx+40,384,366),(cx-36,cx+36,388,371)]:
  aframe(xl,xr,ye,yt,542)
 # paired upper panes and lower rectangular pane
 v(cx-3,curve_y(cx-36,cx+36,388,371,cx-3),444,'WINDOWS');v(cx+3,curve_y(cx-36,cx+36,388,371,cx+3),444,'WINDOWS');h(444,cx-36,cx+36,'WINDOWS')
 rect(cx-31,454,cx+31,537,'WINDOWS');rect(cx-34,450,cx+34,541,'WINDOWS')
 rect(cx-49,543,cx+49,550)
 poly([(cx-47,550),(cx-40,557),(cx-39,560),(cx+40,560),(cx+41,557),(cx+47,550)])
 h(556,cx-41,cx+42)
 # Ground floor arched door, glass panels, lower recessed rectangles.
 for xl,xr,ye,yt in [(cx-70,cx+70,650,620),(cx-63,cx+63,653,628),(cx-58,cx+58,657,635)]:
  aframe(xl,xr,ye,yt,815)
 v(cx-4,curve_y(cx-58,cx+58,657,635,cx-4),815,'WINDOWS');v(cx+4,curve_y(cx-58,cx+58,657,635,cx+4),815,'WINDOWS')
 h(745,cx-58,cx+58,'WINDOWS');h(752,cx-58,cx+58,'WINDOWS')
 for xx in [cx-49,cx+13]:
  rect(xx,762,xx+30,805,'WINDOWS');rect(xx+4,766,xx+26,800,'WINDOWS')
 keystone(cx,606)
 for y in [818,823,828,832]:h(y,702 if cx==775 else 925,845 if cx==775 else 1065)
# Reflections use measured source straight segments, not wavy contours.
reflections=[(140,424,153,406),(138,450,153,427),(178,431,191,411),(174,451,191,428),
(447,438,465,416),(440,464,465,435),(512,439,529,417),(505,465,529,436),
(749,416,761,398),(750,428,764,409),(786,418,800,399),(787,430,802,411),
(767,510,793,478),(758,531,790,493),
(970,416,983,398),(970,428,987,409),(1008,419,1020,400),(1006,431,1022,412),
(988,511,1015,478),(980,532,1012,493),
(739,699,761,666),(735,719,757,685),(795,705,814,679),(792,721,813,692),
(962,698,980,671),(958,719,979,688),(1015,703,1034,679),(1011,720,1033,694),
(447,686,466,660),(440,712,464,683),(512,688,532,661),(506,713,530,684)]
for a in reflections:line(*a,'GLASS')
for a in reflections[:8]:
 x1,y1,x2,y2=a
 if x1<200:line(x1,y1+250,x2,y2+250,'GLASS')
for x1,y1,x2,y2 in reflections[4:8]+reflections[-4:]:line(x1+809,y1,x2+809,y2,'GLASS')
for x1,y1,x2,y2 in reflections[:4]:line(x1+1444,y1,x2+1444,y2,'GLASS');line(x1+1444,y1+250,x2+1444,y2+250,'GLASS')
# Solar panel planes, each specified from four measured corner coordinates.
PANEL_QUADS=[[(369,106),(440,106),(462,136),(387,136)],[(443,106),(512,106),(534,136),(465,136)],[(515,106),(585,106),(606,136),(537,136)],[(588,106),(649,106),(668,136),(610,136)],
[(681,106),(754,106),(773,136),(699,136)],[(758,106),(822,106),(831,136),(777,136)],[(826,106),(882,106),(883,136),(835,136)],
[(887,106),(941,106),(936,136),(886,136)],[(944,106),(1000,106),(987,136),(940,136)],[(1004,106),(1075,106),(1057,136),(991,136)],
[(1108,106),(1169,106),(1149,136),(1090,136)],[(1173,106),(1241,106),(1223,136),(1153,136)],[(1245,106),(1324,106),(1305,136),(1227,136)],[(1328,106),(1402,106),(1383,136),(1309,136)]]
# Fine cell rows/columns are sampled from the source, then constructed as straight lines.
for quad in PANEL_QUADS:
 q=np.array(quad,float);poly(q.tolist(),True,'SOLAR')
 def at(u,vv):return (1-vv)*((1-u)*q[0]+u*q[1])+vv*((1-u)*q[3]+u*q[2])
 inset=[at(.025,.1),at(.975,.1),at(.975,.9),at(.025,.9)];poly([x.tolist() for x in inset],True,'SOLAR')
 # Source shows three cell columns in each panel.
 for u in [1/3,2/3]:poly([at(u,.1).tolist(),at(u,.9).tolist()],layer='SOLAR')
 # Sample the interior normal scan: detected source dark row strokes.
 vals=[]
 for vv in np.linspace(.12,.88,161):
  pp=np.array([at(u,vv) for u in np.linspace(.08,.92,31)])
  vals.append(np.mean(cv2.remap(A.astype('float32'),pp[:,0].astype('float32')[None],pp[:,1].astype('float32')[None],cv2.INTER_LINEAR)))
 inds,_=find_peaks(-gaussian_filter1d(vals,1),prominence=5,distance=10)
 for i in inds:
  vv=.12+.76*i/160;poly([at(.025,vv).tolist(),at(.975,vv).tolist()],layer='SOLAR')
# Save geometric source before any foreground visibility clipping or deduplication.
(ROOT/'architecture_raw.json').write_text(json.dumps({'lines':lines,'arcs':arcs,'flutes':FLUTE_RUNS,'panel_quads':PANEL_QUADS}))
print('Analytical architecture:',len(lines),'straight segments,',len(arcs),'circular arcs')
# Small roof troughs have their own straight lips and faces.
for x1,x2 in [(236,389),(576,716),(1054,1196),(1384,1540)]:
 rect(x1,228,x2,234);poly([(x1+2,234),(x1+6,240),(x1+6,259),(x2-7,259),(x2-7,240),(x2-2,234)])
# Foreground botanical regions follow visible plant clusters, not rectangular cut-outs.
flora=[]
def region(points):flora.append(Polygon(points))
for a,b in [(230,393),(572,721),(1049,1201),(1379,1544)]:
 region([(a,226),(a+12,209),(a+35,197),(a+65,206),(a+90,198),(b-20,204),(b,222),(b,237),(a,237)])
# Trailing upper-roof vines; positions taken individually from the source.
for x,y,ww,hh in [(281,225,12,59),(346,226,12,59),(615,226,12,61),(678,225,13,64),(1094,226,14,63),(1155,227,13,53),(1426,227,13,58),(1495,226,14,64)]:region([(x-ww,y),(x+ww,y),(x+ww*.7,y+hh*.6),(x+ww*.3,y+hh),(x-ww*.3,y+hh),(x-ww*.7,y+hh*.6)])
# Main upper planter shrubs and leaves.
for dx in [0,809]:
 region([(348+dx,493),(353+dx,475),(368+dx,470),(366+dx,450),(386+dx,462),(397+dx,446),(409+dx,475),(443+dx,468),(471+dx,477),(495+dx,467),(513+dx,478),(538+dx,468),(557+dx,452),(571+dx,446),(579+dx,466),(594+dx,454),(600+dx,475),(609+dx,486),(605+dx,502),(351+dx,502)])
 for x,y,ww,hh in [(391+dx,491,15,55),(444+dx,494,13,49),(534+dx,493,19,52),(574+dx,492,14,48)]:region([(x-ww,y),(x+ww,y),(x+ww*.8,y+hh*.6),(x+ww*.3,y+hh),(x-ww*.3,y+hh),(x-ww*.8,y+hh*.6)])
 # Lower planter row, source has shorter plants.
 region([(365+dx,747),(370+dx,731),(389+dx,720),(408+dx,734),(431+dx,727),(450+dx,737),(470+dx,723),(492+dx,734),(514+dx,725),(541+dx,735),(563+dx,720),(582+dx,730),(596+dx,746),(590+dx,754),(371+dx,754)])
 # Ground planting beds and prominent end leaves.
 if dx==809:dx=826
 region([(247+dx,812),(251+dx,786),(272+dx,784),(264+dx,755),(284+dx,773),(289+dx,752),(300+dx,781),(316+dx,760),(312+dx,788),(340+dx,788),(353+dx,779),(369+dx,791),(387+dx,782),(411+dx,792),(434+dx,782),(463+dx,793),(482+dx,783),(509+dx,793),(531+dx,781),(553+dx,790),(578+dx,782),(600+dx,791),(619+dx,784),(628+dx,755),(645+dx,774),(650+dx,753),(662+dx,779),(675+dx,758),(675+dx,789),(693+dx,789),(697+dx,813)])
# Outside-window greenery, separate upper/lower planting and individual vines.
for dx in [0,1469]:
 for dy in [0,250]:
  region([(58+dx,493+dy),(67+dx,475+dy),(85+dx,470+dy),(98+dx,460+dy),(111+dx,474+dy),(130+dx,468+dy),(151+dx,475+dy),(167+dx,463+dy),(183+dx,474+dy),(197+dx,458+dy),(213+dx,471+dy),(234+dx,465+dy),(247+dx,481+dy),(247+dx,501+dy),(62+dx,501+dy)])
  for x,y,ww,hh in [(86+dx,487+dy,18,82),(193+dx,489+dy,16,65)]:region([(x-ww,y),(x+ww,y),(x+ww*.8,y+hh*.55),(x+ww*.3,y+hh),(x-ww*.3,y+hh),(x-ww*.8,y+hh*.55)])
 # Far-right outer vines differ from the left in the source.
 if dx:region([(1657,490),(1703,485),(1701,530),(1690,587),(1678,552)])
flora_mask=unary_union(flora)
# Masonry areas: actual image joints are retained, then made orthogonal.
stone_mask=unary_union([box(845.9,264.5,924.1,831.5),box(248,515.5,701,812.5),box(1066,515.5,1524,812.5)])
holes=[box(300,531,315,610),box(642,531,657,610),box(1113,531,1128,610),box(1456,531,1471,610)]
for dx in [0,809]:
 holes.extend([box(355+dx,514,604+dx,595),box(365+dx,747,597+dx,782)])
 # Ground arch plus its side fluting.
 ar=np.linspace(math.radians(154),math.radians(26),80)
 # Use exact window's outer arch in a masked closed silhouette.
 xl,xr,ye,yt=413+dx,550+dx,639,615;c=(xl+xr)/2;a=(xr-xl)/2;rr=(a*a+(ye-yt)**2)/(2*(ye-yt));cy=yt+rr
 theta=np.linspace(math.atan2(cy-ye,xl-c),math.atan2(cy-ye,xr-c),100)
 cap=[(c+rr*math.cos(t),cy-rr*math.sin(t)) for t in theta]
 holes.append(Polygon(cap+[(xr,749),(xl,749)]).buffer(.7))
 holes.extend([box(384+dx,637,414+dx,749),box(549+dx,637,581+dx,749)])
stone_mask=stone_mask.difference(unary_union(holes)).difference(flora_mask)
old=json.loads(Path(os.environ.get('FACADE_TRACE',str(Path(__file__).resolve().parents[3]/'drawings/sustainable-facade/geometry_pixels.json'))).read_text())['paths']
plant_lines=[];stone_paths=[]
def parts(g):
 if g.is_empty:return []
 if g.geom_type=='LineString':return [g]
 return [x for x in getattr(g,'geoms',[]) if x.geom_type=='LineString' and x.length>1e-5]
for p in old:
 pts=p['points']+([p['points'][0]] if p['closed'] else [])
 if len(set(map(tuple,pts)))<2:continue
 ls=LineString(pts)
 if ls.intersects(flora_mask):
  for g in parts(ls.intersection(flora_mask)):
   if g.length>.15:plant_lines.append(g)
 if ls.intersects(stone_mask):
  for g in parts(ls.intersection(stone_mask)):
   if g.length>.3:stone_paths.append(g)
# Each masonry chain is simplified before axis constraints; no wavy joints remain.
vertices=[];vedges=[];lookup={}
def vertex(p):
 k=tuple(np.round(p,5))
 if k not in lookup:lookup[k]=len(vertices);vertices.append(k)
 return lookup[k]
for ls in stone_paths:
 pp=np.array(ls.coords,dtype='float32')
 pp=cv2.approxPolyDP(pp.reshape(-1,1,2),.75,False).reshape(-1,2)
 for a,b in zip(pp,pp[1:]):
  if np.linalg.norm(a-b)<.4:continue
  ia,ib=vertex(a),vertex(b);orient=0 if abs(a[0]-b[0])>=abs(a[1]-b[1]) else 1
  vedges.append((ia,ib,orient))
parentx=list(range(len(vertices)));parenty=parentx.copy()
def root(parent,i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def union(parent,a,b):
 a=root(parent,a);b=root(parent,b)
 if a!=b:parent[b]=a
for a,b,o in vedges:union(parenty if o==0 else parentx,a,b)
vv=np.array(vertices);new=vv.copy()
for axis,parent in [(0,parentx),(1,parenty)]:
 groups=collections.defaultdict(list)
 for i in range(len(vv)):groups[root(parent,i)].append(i)
 for group in groups.values():new[group,axis]=np.median(vv[group,axis])
for a,b,o in vedges:
 if np.linalg.norm(new[a]-new[b])>.4:line(*new[a],*new[b],'MASONRY')
# Trim analytical architecture behind foreground planting, preserving its true line direction.
visible=[]
for a,b,layer in lines:
 ls=LineString([a,b]); clipped=ls.intersection(stone_mask) if layer=='MASONRY' else ls.difference(flora_mask) if layer not in ['SOLAR','GROUND'] else ls
 for ss in parts(clipped):visible.append((list(ss.coords[0]),list(ss.coords[-1]),layer))
lines=visible
# Remove exact duplicates and node all straight line intersections per source network.
bylayer=collections.defaultdict(list)
for a,b,layer in lines:bylayer[layer].append(LineString([a,b]))
final_lines=[]
# Global noding is required so coincident lines on different layers aren't duplicated.
all_union=unary_union([g for ls in bylayer.values() for g in ls],grid_size=.000001)
from shapely.strtree import STRtree
original=[g for ls in bylayer.values() for g in ls];original_layers=[name for name,ls in bylayer.items() for g in ls];tree=STRtree(original)
for ls in parts(all_union):
 coords=list(ls.coords)
 for a,b in zip(coords,coords[1:]):
  if math.dist(a,b)<1e-6:continue
  mid=LineString([a,b]).interpolate(.5,normalized=True)
  layer=original_layers[int(tree.nearest(mid))]
  final_lines.append((list(a),list(b),layer))
lines=final_lines
# Split circular arches where the source keystone occludes the crown.
clean_arcs=[]
keymask=unary_union(KEYSTONES)
for arcdata in arcs:
 cx,cy=arcdata['center'];r=arcdata['radius'];start,end=arcdata['start'],arcdata['end']
 angles=np.linspace(start,end,1001)
 visible=np.array([not keymask.contains(__import__('shapely').Point(cx+r*math.cos(math.radians(t)),cy-r*math.sin(math.radians(t)))) for t in angles])
 cut=[0]+list(np.where(visible[1:]!=visible[:-1])[0]+1)+[len(angles)]
 for a,b in zip(cut,cut[1:]):
  if not visible[a]:continue
  lo,hi=angles[a],angles[b-1]
  # Binary-search exact curve/polygon intersection, not a sampled polygon edge.
  if a>0:
   left,right=angles[a-1],angles[a]
   for _ in range(40):
    mid=(left+right)/2;p=__import__('shapely').Point(cx+r*math.cos(math.radians(mid)),cy-r*math.sin(math.radians(mid)))
    if keymask.contains(p):left=mid
    else:right=mid
   lo=(left+right)/2
  if b<len(angles):
   left,right=angles[b-1],angles[b]
   for _ in range(40):
    mid=(left+right)/2;p=__import__('shapely').Point(cx+r*math.cos(math.radians(mid)),cy-r*math.sin(math.radians(mid)))
    if keymask.contains(p):right=mid
    else:left=mid
   hi=(left+right)/2
  if hi-lo>1e-7:clean_arcs.append({**arcdata,'start':float(lo),'end':float(hi)})
arcs=clean_arcs
# Source plant strokes are smoothed as B-splines, with endpoints kept fixed.
from scipy.interpolate import splprep,splev
for ls in plant_lines:
 pp=np.array(ls.coords);closed=bool(np.linalg.norm(pp[0]-pp[-1])<1e-4)
 if len(pp)<4 or ls.length<1.2:
  curves.append({'type':'poly','points':pp.tolist(),'closed':closed});continue
 try:
  weights=np.ones(len(pp));weights[0]=weights[-1]=1e5
  tck,u=splprep(pp.T,s=.014*len(pp),k=min(3,len(pp)-1),w=weights,per=closed)
  knots,cc,degree=tck
  curves.append({'type':'spline','knots':list(knots),'controls':np.array(cc).T.tolist(),'degree':degree,'closed':closed})
 except (ValueError,TypeError):curves.append({'type':'poly','points':pp.tolist(),'closed':closed})
# Connect only short, source-supported gaps in analytical architecture.
# Endpoints near foliage stay clipped, rather than creating strokes across leaves.
from shapely import Point
from shapely.strtree import STRtree
structural={'ARCH','WINDOWS','LOUVERS','GROUND'}
geom=[LineString([a,b]) for a,b,ly in lines if ly in structural]
line_tree=STRtree(geom);flora_buffer=flora_mask.buffer(.8);extended=0
corrected=[]
for a,b,ly in lines:
 aa=np.array(a,float);bb=np.array(b,float)
 if ly in structural:
  for endpoint in [0,1]:
   p=aa if endpoint==0 else bb;other=bb if endpoint==0 else aa
   if flora_buffer.intersects(Point(p)):continue
   vec=p-other;length=np.linalg.norm(vec)
   if length<.3:continue
   direction=vec/length;near=line_tree.query(Point(p).buffer(2.01))
   connected=False
   for j in near:
    target=geom[int(j)]
    if target.equals(LineString([a,b])):continue
    if target.distance(Point(p))<1e-5:connected=True;break
   if connected:continue
   # Curved head connections are already analytically exact.
   if any(abs(np.linalg.norm(p-np.array(q['center']))-q['radius'])<1e-5 for q in arcs):continue
   ray=LineString([p,p+direction*2]);candidates=[]
   for j in near:
    target=geom[int(j)]
    if target.equals(LineString([a,b])):continue
    hit=ray.intersection(target)
    for q in ([hit] if hit.geom_type=='Point' else getattr(hit,'geoms',[])):
     if q.geom_type!='Point':continue
     delta=np.array(q.coords[0])-p;dist=np.linalg.norm(delta)
     if 1e-5<dist<=2:candidates.append((dist,np.array(q.coords[0])))
   if candidates:
    dist,q=min(candidates,key=lambda v:v[0]);sample=np.linspace(p,q,9)
    # Source ink within one native pixel is required throughout the correction.
    supported=[]
    for pp in sample:
     ix,iy=np.rint(pp).astype(int)
     patch=A[max(0,iy-1):min(H,iy+2),max(0,ix-1):min(W,ix+2)]
     supported.append(patch.size and patch.min()<225)
    if all(supported):
     if endpoint==0:aa=q
     else:bb=q
     extended+=1
 corrected.append((aa.tolist(),bb.tolist(),ly))
lines=corrected
# Re-node extended straight geometry, with no duplicate line intervals.
source_geoms=[LineString([a,b]) for a,b,ly in lines];source_layers=[ly for a,b,ly in lines];tree=STRtree(source_geoms)
network=unary_union(source_geoms,grid_size=.000001);lines=[]
for segment in parts(network):
 for a,b in zip(segment.coords,list(segment.coords)[1:]):
  if math.dist(a,b)<1e-6:continue
  mid=LineString([a,b]).interpolate(.5,normalized=True);ly=source_layers[int(tree.nearest(mid))]
  lines.append((list(a),list(b),ly))
# Split LINE/ARC contacts exactly so every intended contact has shared endpoints.
line_cuts=[{0.,1.} for _ in lines];arc_cuts=[{q['start'],q['end']} for q in arcs]
for j,q in enumerate(arcs):
 center=np.array(q['center']);radius=q['radius']
 for i,(a,b,ly) in enumerate(lines):
  a=np.array(a);b=np.array(b);d=b-a;f=a-center;aa=float(d@d)
  if aa<1e-14:continue
  bb=2*float(f@d);cc=float(f@f-radius*radius);disc=bb*bb-4*aa*cc
  if disc < -1e-7:continue
  disc=max(0,disc)
  for t in [(-bb-math.sqrt(disc))/(2*aa),(-bb+math.sqrt(disc))/(2*aa)]:
   if t< -1e-7 or t>1+1e-7:continue
   t=min(1.,max(0.,t));p=a+t*d
   angle=math.degrees(math.atan2(center[1]-p[1],p[0]-center[0]))%360
   if q['start']-1e-7<=angle<=q['end']+1e-7:
    angle=min(q['end'],max(q['start'],angle));line_cuts[i].add(t);arc_cuts[j].add(angle)
split_lines=[]
for (a,b,ly),cuts in zip(lines,line_cuts):
 a=np.array(a);b=np.array(b);tt=sorted(cuts)
 for t1,t2 in zip(tt,tt[1:]):
  p=a+t1*(b-a);q=a+t2*(b-a)
  if np.linalg.norm(q-p)>1e-6:split_lines.append((p.tolist(),q.tolist(),ly))
lines=split_lines;split_arcs=[]
for arc,cuts in zip(arcs,arc_cuts):
 vals=sorted(cuts)
 for a,b in zip(vals,vals[1:]):
  if b-a>1e-7:split_arcs.append({**arc,'start':a,'end':b})
arcs=split_arcs
print('Source-supported junction extensions:',extended)

print('Clean network:',len(lines),'straight LINEs,',len(arcs),'ARCs,',len(curves),'botanical paths')
# Remove repeated closure vertices from short botanical polylines.
for c in curves:
 if c['type']!='poly':continue
 pp=[]
 for point in c['points']:
  if not pp or math.dist(point,pp[-1])>1e-8:pp.append(point)
 if c['closed'] and len(pp)>1 and math.dist(pp[0],pp[-1])<1e-8:pp.pop()
 if len(pp)<3:c['closed']=False
 c['points']=pp
# Export all deliverables from the same analytical scene.
scene={'image_size':[W,H],'mm_per_pixel':MM,'plant_color_aci':94,'lines':lines,'arcs':arcs,'plants':curves}
(OUT/'scene.json').write_text(json.dumps(scene,separators=(',',':')))
def cad(p):return ((p[0]-1)*MM,(832-p[1])*MM)
doc=ezdxf.new('R2000');doc.units=4;doc.header['$LWDISPLAY']=True
layers=['ARCH','WINDOWS','GROUND','GLASS','LOUVERS','SOLAR','MASONRY','PLANTS']
for name in layers:doc.layers.new(name,dxfattribs={'color':94 if name=='PLANTS' else 7,'lineweight':13})
ms=doc.modelspace()
for a,b,layer in lines:ms.add_line(cad(a),cad(b),dxfattribs={'layer':layer,'color':7,'lineweight':13})
for arc in arcs:ms.add_arc(cad(arc['center']),arc['radius']*MM,arc['start'],arc['end'],dxfattribs={'layer':arc['layer'],'color':7,'lineweight':13})
for c in curves:
 attrs={'layer':'PLANTS','color':94,'lineweight':13}
 if c['type']=='poly':ms.add_lwpolyline([cad(p) for p in c['points']],close=c['closed'],dxfattribs=attrs)
 else:
  entity=ms.add_open_spline([(*cad(p),0) for p in c['controls']],degree=c['degree'],knots=c['knots'],dxfattribs=attrs)
  if c['closed']:entity.dxf.flags=3
doc.set_modelspace_vport(height=H*MM,center=(W*MM/2,(832-H/2)*MM));doc.saveas(OUT/'facade_straight.dxf')
# PDF/preview: evaluated splines and genuine circular arcs from the same CAD model.
pt=72/25.4;pw,ph=420*pt,297*pt;scale=MM/50*pt

def paint(ctx):
 ctx.set_source_rgb(0,0,0);ctx.set_line_width(.13*50/MM);ctx.set_line_join(cairo.LINE_JOIN_ROUND);ctx.set_line_cap(cairo.LINE_CAP_ROUND)
 for a,b,layer in lines:ctx.move_to(*a);ctx.line_to(*b);ctx.stroke()
 for a in arcs:
  cx,cy=a['center'];r=a['radius'];ctx.arc(cx,cy,r,math.radians(-a['end']),math.radians(-a['start']));ctx.stroke()
 ctx.set_source_rgb(0,127/255,0)
 for c in curves:
  if c['type']=='poly':pp=c['points']
  else:
   pp=np.array(splev(np.linspace(c['knots'][c['degree']],c['knots'][-c['degree']-1],max(12,len(c['controls'])*5)),(c['knots'],np.array(c['controls']).T,c['degree']))).T
  if len(pp)<2:continue
  ctx.move_to(*pp[0])
  for p in pp[1:]:ctx.line_to(*p)
  if c['closed']:ctx.close_path()
  ctx.stroke()
s=cairo.PDFSurface(str(OUT/'facade_straight.pdf'),pw,ph);ctx=cairo.Context(s);ctx.set_source_rgb(1,1,1);ctx.paint();ctx.translate((pw-W*scale)/2,(ph-H*scale)/2);ctx.scale(scale,scale);paint(ctx);ctx.show_page();s.finish()
for factor,name in [(1,'preview'),(3,'detail')]:
 s=cairo.ImageSurface(cairo.FORMAT_RGB24,W*factor,H*factor);ctx=cairo.Context(s);ctx.set_source_rgb(1,1,1);ctx.paint();ctx.scale(factor,factor);paint(ctx);s.write_to_png(str(OUT/(name+'.png')))
# Keep masks/metadata outside the actual CAD drawing for review.
(OUT/'measurements.json').write_text(json.dumps({'flutes':FLUTE_RUNS,'panel_quads':PANEL_QUADS,'source':'IMG_3106.PNG','scale_is_estimated':True},indent=2)+'\n')
