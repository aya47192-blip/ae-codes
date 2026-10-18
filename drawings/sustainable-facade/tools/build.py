import os
from pathlib import Path
import sys,json,math,hashlib,collections
sys.path[:0]=['/workspace/sustainable_deps','/workspace/elevation/deps']
import numpy as np,cv2,ezdxf,cairocffi as cairo
from scipy import ndimage
from skimage.morphology import skeletonize
from PIL import Image
ROOT=Path(__file__).parent; OUT=Path(os.environ.get('FACADE_OUTPUT',str(ROOT/'output')));OUT.mkdir(exist_ok=True)
SRC=Path(os.environ.get('FACADE_SOURCE',str(Path(__file__).resolve().parents[3]/'IMG_3106.PNG')))
S=3; W=1774;H=887; MM=20000/1768
im=cv2.imread(str(SRC));gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
g=cv2.resize(gray,None,fx=S,fy=S,interpolation=cv2.INTER_CUBIC)
hi=cv2.dilate(g,np.ones((19,19),np.uint8));lo=cv2.erode(g,np.ones((19,19),np.uint8))
threshold=np.minimum((hi.astype(float)+lo)/2,240)
bw=(g<threshold)&((hi.astype(int)-lo)>7)
sk=skeletonize(bw)
# In the dark PV region, differential ridges separate adjacent cell strokes
# which a binary skeleton would merge into diagonal branches.
ridge=np.load(ROOT/'ridge.npy')
sk[102*S:139*S,365*S:1407*S]=ridge[102*S:139*S,365*S:1407*S]
# Probe straight horizontal/vertical runs directly in the intensity-ridge image.
hough=cv2.HoughLinesP(ridge.astype('uint8')*255,1,np.pi/180,threshold=65,minLineLength=90,maxLineGap=3)
axes=[]
if hough is not None:
 for x1,y1,x2,y2 in hough.reshape(-1,4):
  if abs(y2-y1)<=1 and abs(x2-x1)>=90:
   axes.append((0,(y1+y2)/(2*S),min(x1,x2)/S,max(x1,x2)/S))
  elif abs(x2-x1)<=1 and abs(y2-y1)>=90:
   axes.append((1,(x1+x2)/(2*S),min(y1,y2)/S,max(y1,y2)/S))
print('measured straight runs',len(axes),flush=True)
# Pixel-centre graph. Diagonals are excluded when an orthogonal bridge exists.
ys,xs=np.nonzero(sk); coords=list(zip(ys.tolist(),xs.tolist())); nodes=set(coords)
adj={p:[] for p in coords}
for y,x in coords:
 for dy,dx in [(0,1),(1,0),(1,1),(1,-1)]:
  q=(y+dy,x+dx)
  if q not in nodes:continue
  if dy and dx and ((y,x+dx) in nodes or (y+dy,x) in nodes):continue
  adj[(y,x)].append(q);adj[q].append((y,x))
# Merge the small connected sets of junction pixels to one shared vertex.
critical={p for p in coords if len(adj[p])!=2}
visited=set();mapping={};positions={};groups=[]
for p in critical:
 if p in visited:continue
 stack=[p];visited.add(p);group=[]
 while stack:
  u=stack.pop();group.append(u)
  for v in adj[u]:
   if v in critical and v not in visited:visited.add(v);stack.append(v)
 nid=len(groups);groups.append(group)
 xy=np.array([(x/S,y/S) for y,x in group]);positions[nid]=xy.mean(axis=0)
 for u in group:mapping[u]=nid
nextid=len(groups)
for p in coords:
 if p not in mapping:
  mapping[p]=nextid;positions[nextid]=np.array([p[1]/S,p[0]/S]);nextid+=1
edges=set()
for p in coords:
 a=mapping[p]
 for q in adj[p]:
  b=mapping[q]
  if a!=b:edges.add((min(a,b),max(a,b)))
G=collections.defaultdict(set)
for a,b in edges:G[a].add(b);G[b].add(a)
used=set();raw=[]
def walk(a,b):
 path=[a,b];used.add(tuple(sorted((a,b))))
 while len(G[b])==2:
  c=next(v for v in G[b] if v!=a);key=tuple(sorted((b,c)))
  if key in used:break
  used.add(key);path.append(c);a,b=b,c
 return path
for a in sorted(G):
 if len(G[a])!=2:
  for b in sorted(G[a]):
   if tuple(sorted((a,b))) not in used:raw.append(walk(a,b))
for a,b in sorted(edges):
 if (a,b) not in used:raw.append(walk(a,b))
paths=[];max_dev=0
for chain in raw:
 pts=np.array([positions[k] for k in chain],dtype=np.float32)
 closed=chain[0]==chain[-1]
 if closed:pts=pts[:-1]
 # Light subpixel smoothing, preserving the measured junction coordinates.
 if len(pts)>5:
  smooth=ndimage.gaussian_filter1d(pts,.9,axis=0,mode='wrap' if closed else 'nearest')
  if not closed:smooth[0]=pts[0];smooth[-1]=pts[-1]
 else:smooth=pts
 fit=cv2.approxPolyDP(smooth.reshape(-1,1,2),.23,closed).reshape(-1,2)
 if len(fit)<(3 if closed else 2):fit=pts
 if len(fit)<2:continue
 fit=np.round(fit,5)
 # Remove only consecutive identical points; retain all components.
 fit=np.array([p for i,p in enumerate(fit) if i==0 or not np.array_equal(p,fit[i-1])])
 if len(fit)>=2:paths.append({'points':fit.tolist(),'closed':bool(closed)})
# Isolated image dots are kept as small closed diamonds, not discarded as noise.
for nid,group in enumerate(groups):
 if nid not in G:
  x,y=positions[nid];r=1/(2*S)
  paths.append({'points':[[x-r,y],[x,y-r],[x+r,y],[x,y+r]],'closed':True})
# Project only near-axis straight geometry onto measured long runs.
# Displacement is bounded; no freehand design elements or inferred patterns.
original_points=np.array(sorted({tuple(q) for p in paths for q in p['points']}))
projected=original_points.copy();best=np.full_like(projected,np.inf)
for orient,level,start,end in axes:
 a=1 if orient==0 else 0;b=1-a
 delta=np.abs(original_points[:,a]-level)
 select=(original_points[:,b]>=start-.25)&(original_points[:,b]<=end+.25)&(delta<=.65)&(delta<best[:,a])
 projected[select,a]=level;best[select,a]=delta[select]
snap={tuple(a):np.round(b,5).tolist() for a,b in zip(original_points,projected)}
for p in paths:p['points']=[snap[tuple(q)] for q in p['points']]
# Join only subpixel endpoint gaps supported by visible source ink and tangent direction.
from scipy.spatial import cKDTree
ends=[]
for i,p in enumerate(paths):
 if p['closed']:continue
 pts=np.array(p['points'])
 for j,k in [(0,1),(-1,-2)]:
  d=pts[j]-pts[k];length=np.linalg.norm(d)
  if length>0:ends.append((i,j,pts[j],d/length))
joins=0
if ends:
 tree=cKDTree([q[2] for q in ends]);candidates=[]
 for a,b in tree.query_pairs(.85):
  ia,ja,pa,da=ends[a];ib,jb,pb,db=ends[b]
  delta=pb-pa;length=np.linalg.norm(delta)
  if length<.0001:continue
  if np.dot(delta/length,da)<.65 or np.dot(-delta/length,db)<.65:continue
  samples=np.linspace(pa,pb,9)
  ink=ndimage.map_coordinates(g,[samples[:,1]*S,samples[:,0]*S],order=1)
  if np.max(ink)>244:continue
  candidates.append((length,a,b))
 occupied=set()
 for length,a,b in sorted(candidates):
  if a in occupied or b in occupied:continue
  occupied.update([a,b]);pa=ends[a][2];pb=ends[b][2]
  paths.append({'points':[pa.tolist(),pb.tolist()],'closed':False});joins+=1
print('source-supported subpixel joins',joins,flush=True)

# Re-node all intersections and remove coincident projected segments exactly.
from shapely import LineString,unary_union,line_merge
lines=[]
for p in paths:
 pts=p['points']+([p['points'][0]] if p['closed'] else [])
 if len(set(map(tuple,pts)))>1:lines.append(LineString(pts))
network=line_merge(unary_union(lines,grid_size=.00001))
paths=[]
for ls in network.geoms if hasattr(network,'geoms') else [network]:
 pts=list(map(list,ls.coords));closed=pts[0]==pts[-1]
 if closed:pts=pts[:-1]
 if len(pts)>=2:paths.append({'points':pts,'closed':closed})
# Split categories by measured reference regions, retaining a single lineweight.
def layer(points):
 x,y=np.mean(points,axis=0)
 if y<144 and 365<x<1408:return 'SOLAR'
 plant_rects=[(230,195,393,286),(573,195,720,288),(1050,195,1200,290),(1380,194,1542,290),(55,448,249,574),(345,449,612,549),(1157,448,1424,549),(1520,448,1710,585),(61,704,250,812),(365,715,598,756),(1170,714,1403,756),(1524,708,1714,813),(247,754,699,815),(1070,754,1521,815)]
 if any(a<=x<=c and b<=y<=d for a,b,c,d in plant_rects):return 'PLANTING'
 if (843<x<926 and 264<y<831) or (250<x<700 and 515<y<810) or (1066<x<1522 and 515<y<810):return 'MASONRY_AND_ARCH'
 return 'ARCHITECTURE'
for p in paths:p['layer']=layer(p['points'])
(OUT/'geometry_pixels.json').write_text(json.dumps({'image_size':[W,H],'mm_per_pixel':MM,'paths':paths},separators=(',',':')))
# Native editable CAD entities; no embedded source raster and no background rectangle.
doc=ezdxf.new('R2010');doc.units=4;doc.header['$LWDISPLAY']=True;doc.header['$MEASUREMENT']=1
for name in sorted({p['layer'] for p in paths}):
 doc.layers.new(name,dxfattribs={'color':7,'true_color':0,'lineweight':13})
ms=doc.modelspace()
for p in paths:
 cad=[(round((x-1)*MM,5),round((832-y)*MM,5)) for x,y in p['points']]
 ms.add_lwpolyline(cad,close=p['closed'],dxfattribs={'layer':p['layer'],'color':7,'true_color':0,'lineweight':13,'const_width':0})
doc.set_modelspace_vport(height=H*MM,center=(W*MM/2,(832-H/2)*MM))
doc.saveas(OUT/'sustainable_facade.dxf')
# A3 vector drawing from exactly the same paths at 1:50 nominal scale.
pt=72/25.4;pw=420*pt;ph=297*pt;scale=MM/50*pt
surf=cairo.PDFSurface(str(OUT/'sustainable_facade.pdf'),pw,ph);ctx=cairo.Context(surf)
ctx.set_source_rgb(1,1,1);ctx.paint();ctx.translate((pw-W*scale)/2,(ph-H*scale)/2);ctx.scale(scale,scale)
ctx.set_source_rgb(0,0,0);ctx.set_line_width(.13*pt/scale);ctx.set_line_join(cairo.LINE_JOIN_ROUND);ctx.set_line_cap(cairo.LINE_CAP_ROUND)
for p in paths:
 pts=p['points'];ctx.move_to(*pts[0])
 for xy in pts[1:]:ctx.line_to(*xy)
 if p['closed']:ctx.close_path()
 ctx.stroke()
ctx.show_page();surf.finish()
# Inspection render at source size and 3x source size, independent of PDF rendering.
for factor,name in [(1,'preview'),(3,'detail')]:
 surf=cairo.ImageSurface(cairo.FORMAT_RGB24,W*factor,H*factor);ctx=cairo.Context(surf);ctx.set_source_rgb(1,1,1);ctx.paint();ctx.scale(factor,factor)
 ctx.set_source_rgb(0,0,0);ctx.set_line_width(.13*50/MM);ctx.set_line_join(cairo.LINE_JOIN_ROUND);ctx.set_line_cap(cairo.LINE_CAP_ROUND)
 for p in paths:
  ctx.move_to(*p['points'][0])
  for q in p['points'][1:]:ctx.line_to(*q)
  if p['closed']:ctx.close_path()
  ctx.stroke()
 surf.write_to_png(str(OUT/f'{name}.png'))
# Per-point distance checks use a thin raster rendering of the exported geometry.
render=np.zeros_like(g,dtype=np.uint8)
for p in paths:
 pts=np.rint(np.array(p['points'])*S).astype('int32');cv2.polylines(render,[pts],p['closed'],255,1)
dt=ndimage.distance_transform_edt(~(render>0))/S
res=dt[sk]
source_distance=ndimage.distance_transform_edt(~bw)/S
invented=source_distance[render>0]
# Duplicate segment audit in actual rounded CAD coordinates.
counts=collections.Counter();endpoints=collections.Counter()
for e in ms:
 pts=[tuple(p[:2]) for p in e.get_points()]
 pairs=list(zip(pts,pts[1:]))+([(pts[-1],pts[0])] if e.closed else [])
 for a,b in pairs:
  counts[tuple(sorted((a,b)))]+=1;endpoints[a]+=1;endpoints[b]+=1
read=ezdxf.readfile(OUT/'sustainable_facade.dxf');audit=read.audit()
report={'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'source_size':[W,H],'method':'subpixel local-contrast centreline graph, shared junctions, tolerance-bounded polyline fitting; not manual redesign','source_pixels':int(sk.sum()),'paths':len(paths),'closed_paths':sum(p['closed'] for p in paths),'segments':sum(counts.values()),'duplicate_segments':sum(v-1 for v in counts.values()),'open_endpoints':sum(v==1 for v in endpoints.values()),'dxf_audit_errors':len(audit.errors),'dxf_audit_fixes':len(audit.fixes),'lineweight_mm':.13,'assumed_baseline_width_mm':20000,'source_skeleton_distance_to_vector_px':{'median':float(np.median(res)),'p95':float(np.percentile(res,95)),'p99':float(np.percentile(res,99)),'max':float(res.max()),'within_1px_percent':float((res<=1).mean()*100)},'vector_distance_outside_thresholded_source_ink_px':{'p99':float(np.percentile(invented,99)),'max':float(invented.max())},'source_supported_subpixel_joins':joins,'largest_junction_cluster_pixels':max(map(len,groups)),'limitations':['Pixel distances are internal extraction checks, not proof of exact source fidelity.','Source contains intentional open strokes and faint discontinuities; endpoints are retained rather than guessed closed.','Dimensions are estimated. No millimetre or 100-percent fidelity guarantee.','AutoLISP and DXF have not been opened inside real AutoCAD.']}
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
