"""Ruosuen AREA 1 / continuous low-poly terrain study 12 — perspective previs.
Python 3, numpy, scipy, shapely>=2.1, matplotlib, plotly, numba.
Run: python ruosuen_previs12.py. No external data needed.
Design input: PR #55; original registered nodes retained, no unapproved N128.
Geometry, camera and palette are editable study parameters, not canon. Eye-level views are true scale.
"""
from pathlib import Path
from collections import Counter
import json
import argparse
from shapely.strtree import STRtree
from numba import njit
import numpy as np
from scipy.spatial import Delaunay, cKDTree
from scipy.interpolate import LinearNDInterpolator
from shapely.geometry import Polygon, Point, LineString
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib import patheffects as pe
import plotly.graph_objects as go
OUT=Path(__file__).resolve().parent
P=dict(GATE=(2210,2000,0),N101=(550,2000,5),N102=(1250,2650,30),N103=(1500,2000,-5),N104=(2050,1500,-20),N105=(3000,2650,50),N106=(3720,2000,10),N107=(3950,1500,-5),N108=(2765,850,-50),N109=(3150,500,-65),N110=(4450,550,-65),N111=(4800,2200,20),N112=(3600,3050,60),N113=(480,1450,0),N114=(1050,1050,-10),N115=(1580,1220,-13),N116=(1750,2650,36),N117=(1750,2950,55),N118=(2350,2650,43),N119=(2950,2240,27),N120=(2920,2000,5),N121=(3450,1500,-11),N122=(3450,1020,-33),N123=(4350,1550,-3),N124=(4520,1850,3),N125=(1620,700,-33),N126=(2100,520,-37),N127=(3850,422,-65))
R={3:'N101 N103 GATE',7:'GATE N120 N106 N111',12:'N101 N102 N116 N118 N105 N112',65:'N103 N104 N108 N109 N127 N110',112:'N105 N106',165:'N104 N121 N107 N106',201:'N101 N113 N114 N115 N104',214:'N116 N117',215:'N118 N119 N120',231:'N121 N122 N109',240:'N107 N123 N124',245:'N115 N125 N126'}
outline=np.array([[0,2000],[110,2370],[250,2650],[470,2790],[650,3000],[940,3100],[1350,3180],[1850,3100],[2200,2980],[2550,3200],[3100,3250],[3600,3050],[3950,2950],[4300,2830],[4500,2670],[4410,2480],[4800,2200],[4930,1780],[4720,1300],[4600,1060],[4710,800],[4450,550],[4060,270],[3650,130],[3150,150],[2800,80],[2500,150],[2000,220],[1780,300],[1350,380],[1120,500],[800,700],[620,930],[270,1200],[130,1550]],float)
T={ 'massif':[(1370,2340),(1550,2510),(1950,2540),(2170,2360),(2060,2150),(1720,2180)],'pillar':[(3660,2340),(3910,2540),(4130,2480),(4180,2300),(3930,2200)],'shaft':[(2350,2340),(2550,2420),(2760,2290),(2660,2150),(2430,2160)],'cliff_upper':[(2380,1670),(2500,1650),(2610,1650),(3150,1660),(3480,1720)],'cliff_lower':[(2370,1020),(2520,1130),(2660,1320),(2870,1390),(3110,1330)],'river':[(1050,1050),(1200,900),(1440,620),(1550,540),(1790,680),(2150,650),(2320,320),(2380,290)],'pool':[(2220,300),(2390,370),(2580,300),(2550,230),(2320,230)],'growth':[(3550,880),(3720,1040),(3970,960),(4040,770),(3770,700)]}
trails=[('N108',[(2440,810),(2300,660)],'下棚口'),('N108',[(2730,1000),(2650,1200)],'奥棚口'),('N107',[(4220,1260)],'荷道口'),('N126',[(2050,360),(2000,220)],'廃坑奥口'),('N123',[(4550,1430),(4720,1300)],'石切口'),('N102',[(980,2770),(650,3000)],'上道口'),('N114',[(920,860),(800,700)],'水場口')]
# --- Tunable art and engineering parameters (not geography) ---
CFG=dict(grid=48, road_step=14, rim_step=30, relief=28, vertical_exaggeration=3.2,
         rock_peak=125, shaft_cut=-135, wall_cut=72, roof_base=390,
         road_width=9, local_width=5, trail_width=3, seed=37, fog_distance=1750, eye_height=1.65, moss_spacing=8.5, moss_intensity=0.34, lamp_intensity=0.63, natural_intensity=0.38, ambient=0.43, roof_glow=0.68, wet_glow=0.22, render_width=900, render_height=506)
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,help='Optional JSON parameter overrides');parser.add_argument("--shots",default="return,gate,home,return_night");args=parser.parse_args()
if args.config:
    overrides=json.loads(args.config.read_text());assert set(overrides)<=set(CFG), 'Unknown parameter';CFG.update(overrides)
BG='#f8f6ef'; INK='#303c38'; MAIN='#91573b'; LOCAL='#53675e'; WATER='#6198ad'
plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False,'svg.fonttype':'path'})
rng=np.random.default_rng(CFG['seed'])
# S34 mouth: local transverse u, inward v. Floor boundary and portal share vertices.
O=np.array([2650.,1200.]); forward=np.array([-80.,200.]);forward/=np.linalg.norm(forward);side=np.array([forward[1],-forward[0]])
def uv(u,v):return O+u*side+v*forward
# The front is subdivided at the mouth edges; terrain opening is not a painted black patch.
T['portal']=[uv(u,v).tolist() for u,v in [(-64,9),(-30,-3),(-14,0),(-7,0),(-5,0),(-2,0),(0,0),(2,0),(5,0),(7,0),(14,0),(32,-4),(64,8),(95,65),(65,140),(-55,140),(-90,65)]]
T['terminal_rock']=[(2290,1775),(2350,1715),(2440,1720),(2515,1745),(2600,1805),(2570,1875),(2470,1900),(2370,1890),(2305,1845)]
outer=Polygon(outline); holes={k:Polygon(T[k]) for k in ('massif','pillar','shaft','pool','portal','terminal_rock')}
domain=Polygon(outline, [T[k] for k in holes])
bridge=np.array([1744.347826,653.369565]); main={3,7,12,65}

def sample(q, step):
    q=np.array(q,float); d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1))]
    u=np.unique(np.r_[np.arange(0,d[-1],step),d]); return np.column_stack([np.interp(u,d,q[:,i]) for i in range(q.shape[1])])

def ring(q,step):
    q=np.array(q,float); a=[]
    for p,r in zip(q,np.roll(q,-1,axis=0)):
        count=max(1,int(np.ceil(np.linalg.norm(r-p)/step)))
        a.extend(p+(r-p)*i/count for i in range(count))
    return np.array(a)

def roof(x,y): return CFG['roof_base']+65*np.sin(x/4800*np.pi)*np.sin(y/3200*np.pi)-50*x/4800
roads=[]
for r,s in R.items():
    ns=s.split()
    for a,b in zip(ns,ns[1:]):
        p,q=np.array(P[a]),np.array(P[b]); pts=[p,q]
        if (a,b)==('N109','N127'):pts=[p,[3700,390,-65],q]
        if r in (3,7) and np.linalg.norm(q[:2]-p[:2])>500:
            mid=(p+q)/2;mid[1]-=45;pts=[p,mid,q]
        if (a,b)==('N104','N108'):
            d=np.linalg.norm(q[:2]-p[:2]);pts=[p,*[np.r_[p[:2]+(q[:2]-p[:2])*t/d,h] for t,h in [(450,-25),(750,-45)]],q]
        roads.append((r,a,b,sample(pts,CFG['road_step'])))
roads.append((0,'N102','N103',sample([P['N102'],P['N103']],CFG['road_step'])))
roadxy=np.vstack([q[:,:2] for _,_,_,q in roads]); rt=cKDTree(roadxy)
from scipy.interpolate import PchipInterpolator
from shapely.ops import unary_union
rail_specs=[]
for name,r,xmin,xmax in [('active',7,2244,3670),('abandoned',3,720,1230)]:
    q=np.vstack([q for rr,a,b,q in roads if rr==r]);q=q[np.argsort(q[:,0])];q=q[np.unique(q[:,0],return_index=True)[1]]
    xx=np.linspace(xmin,xmax,int((xmax-xmin)/4)+1);yy=PchipInterpolator(q[:,0],q[:,1])(xx)-15;zzr=PchipInterpolator(q[:,0],q[:,2])(xx)
    rail_specs.append((name,np.c_[xx,yy,zzr]))
rail_bed=unary_union([LineString(q[:,:2]).buffer(1.65,cap_style=2) for _,q in rail_specs])
road_mask=unary_union([LineString(q[:,:2]).buffer((CFG['road_width'] if r in main else CFG['local_width'])/2,cap_style=2) for r,a,b,q in roads])
assert rail_bed.intersection(road_mask).area<1e-6,'rail intersects road'
assert domain.covers(rail_bed),'rail intersects rock or leaves floor'
print('rail bed clearance from walking roads',rail_bed.distance(road_mask),flush=True)

river=np.column_stack([T['river'],[-12,-17,-24,-30,-42,-48,-55,-56]])
riverq=sample(river,12); rv=cKDTree(riverq[:,:2])
ctrl={}
def key(p):return tuple(np.round(np.asarray(p,float),7))
def put(p,z):ctrl[key(p)]=float(z)
for x,y in outline:put((x,y),np.interp(y,[80,700,1500,2000,3250],[-65,-42,-9,12,65]))
# local ledge behind the entrance; the front face will rise from this edge.
for u in [-14,-7,-5,-2,0,2,5,7,14]:put(uv(u,0),-38)
for u,v in [(-100,-30),(100,-30),(-130,90),(130,90)]:put(uv(u,v),-37)
# slope toward the entrance, with true floor support for the camera.
for x,y,z in sample([P['N108'],[2730,1000,-46],[2650,1200,-38]],8):put((x,y),z)
for r,a,b,q in roads:
    for x,y,z in q:
        if r==245 and np.linalg.norm([x-bridge[0],y-bridge[1]])<65:continue
        put((x,y),z)
for x,y,z in riverq:
    if domain.covers(Point(x,y)) and np.linalg.norm(np.array([x,y])-P['N114'][:2])>35:put((x,y),z-2.5)
# R65 overlook: the route remains at its existing grade; the adjacent shelf
# ends in a local rock scarp, with a lower apron visible from walking height.
# This is a geometric study, not a new facility or official surveyed feature.
# Contiguous overlook and basin, with road centerline unchanged.
A=np.array(P['N104'][:2],float); B=np.array(P['N108'][:2],float); along=(B-A)/np.linalg.norm(B-A); across=np.array([along[1],-along[0]])
def slope_pt(d,u): return A+along*d+across*u
for d0 in np.arange(300,811,25):
    grade=np.interp(d0,[0,450,750,np.linalg.norm(B-A)],[-20,-25,-45,-50])
    fade=min(1,(d0-280)/95,(850-d0)/85)
    for u,drop in [(12,0),(24,.35),(33,1.0),(43,12),(52,23),(65,29),(95,30),(145,26)]:
        pp=slope_pt(d0,u)
        if domain.covers(Point(pp)) and rt.query(pp)[0]>9 and rv.query(pp)[0]>38:put(pp,grade-drop*fade)
for x,y,z in [(2200,920,-51),(2100,830,-54),(2000,740,-45),(2300,800,-52),(2410,950,-53),(2710,680,-71),(2850,630,-74),(2940,690,-73),(3020,810,-68),(3240,770,-75),(3330,670,-76),(3490,660,-72),(3650,650,-70),(3920,650,-72),(4120,700,-69),(2700,490,-72),(2820,380,-74),(2990,310,-71)]:
    if domain.covers(Point(x,y)) and rt.query([x,y])[0]>55 and rv.query([x,y])[0]>70:put((x,y),z)
# Local breaks are control lines in the SAME mesh, not strips overlaid on a floor.
# Fade cliffs at their ends and at the known R65 descent; no additional cross-area cliffs.
for k,hi,lo in [('cliff_upper',-2,-18),('cliff_lower',-25,-49)]:
    for x,y in sample(T[k],45):
        for dy,z in [(25,hi),(-25,lo)]:
            pt=(x,y+dy)
            if domain.covers(Point(pt)) and rt.query(pt)[0]>65 and np.linalg.norm(np.asarray(pt)-[2440,1190])>220:put(pt,z)
# Graded channel with true cross-section, centerline water profile preserved.
for i,p in enumerate(riverq):
    if i==0 or i==len(riverq)-1:continue
    delta=riverq[i+1,:2]-riverq[i-1,:2];delta/=np.linalg.norm(delta);normal=np.array([-delta[1],delta[0]])
    for u,h in [(-18,2.6),(-11,1.1),(-7,-.6),(0,-2.2),(7,-.6),(11,1.1),(18,2.6)]:
        pp=p[:2]+u*normal
        if domain.contains(Point(pp)) and domain.boundary.distance(Point(pp))>2 and (rt.query(pp)[0]>13 or np.linalg.norm(pp-bridge)<55):put(pp,p[2]+h)
for name,q in rail_specs:
    for i,(x,y,z) in enumerate(q):
        delta=q[min(i+1,len(q)-1),:2]-q[max(i-1,0),:2];delta/=np.linalg.norm(delta);normal=np.array([-delta[1],delta[0]])
        for u in (-1.65,0,1.65):put(np.array([x,y])+u*normal,z-.16)
for n,(x,y,z) in P.items():put((x,y),z)
base=LinearNDInterpolator(np.array(list(ctrl)),np.array(list(ctrl.values())))
# Add coherent rolling rock shelves near the cavern wall and flanking road corridors.
# Off-road relief vanishes near roads/water; this leaves the inherited centerline profiles intact.
def surface(p):
    x,y=p; z=float(base(x,y));
    if not np.isfinite(z):z=float(np.array(list(ctrl.values()))[cKDTree(np.array(list(ctrl))).query(p)[1]])
    dr=rt.query(p)[0]; dw=rv.query(p)[0]
    w=min(1,max(0,(dr-35)/220)) * min(1,max(0,(dw-45)/160))
    f=(.42*np.sin(x/440+y/680)+.30*np.cos(y/270-x/840)+.28*np.sin((x+y)/215))
    return z+CFG['relief']*w*f
# Densified exact boundary vertices shared by floor, walls and all rock objects.
rings={'outer':ring(outline,CFG['rim_step']),**{k:ring(T[k],CFG['rim_step']) for k in holes}}
# Avoid nearly coincident points near ring constraints.
for k,q in rings.items():
    for p in q:
        if key(p) in ctrl:continue
        put(p,-55.1 if k=='pool' else surface(p))
fixed=np.array(list(ctrl)); ft=cKDTree(fixed)
for y in np.arange(160,3200,CFG['grid']):
    for x in np.arange(70,4800,CFG['grid']):
        p=np.array([x,y])+rng.uniform(-.24,.24,2)*CFG['grid']
        pt=Point(p)
        if domain.contains(pt) and domain.boundary.distance(pt)>24 and ft.query(p)[0]>32:put(p,surface(p))
for cx,cy,rad in [(2210,2000,110),(2398,1170,110),(2660,1174,75)]:
    for yy in np.arange(cy-rad,cy+rad,12):
        for xx in np.arange(cx-rad,cx+rad,12):
            pp=np.array([xx,yy])+rng.uniform(-2,2,2)
            if domain.contains(Point(pp)) and domain.boundary.distance(Point(pp))>5 and ft.query(pp)[0]>7 and rt.query(pp)[0]>8:
                put(pp,surface(pp))
xy=np.array(list(ctrl)); zz=np.array(list(ctrl.values())); d=Delaunay(xy)
# Clip using buffered domain only to tolerate roundoff on exact boundary samples.
D=domain.buffer(1e-5)
F0=np.array([f for f in d.simplices if D.covers(Polygon(xy[f]))]); V=[list(v) for v in np.c_[xy,zz]]; F=[]; M=[]
idx={key(p):i for i,p in enumerate(xy)}
def face(ids,mat):
    ids=list(map(int,ids)); a,b,c=np.asarray([V[i] for i in ids]);
    if np.linalg.norm(np.cross(b-a,c-a))>1e-7:F.append(ids);M.append(mat)
def vert(p):V.append(list(map(float,p)));return len(V)-1
# All floor triangles must be upward-wound.
for f in F0:
    a,b,c=xy[f]; cross=np.cross(np.r_[b-a,0],np.r_[c-a,0])[2]
    face(f if cross>0 else f[::-1],'floor')
# Ensure exact polygon coverage, no gaps around the shaft or rocks.
area=sum(Polygon(xy[f]).area for f in F0)
assert abs(area-domain.area)<2.0,(area,domain.area,domain.area-area)
# Compute actual floor boundary edges, including any inserted collinear samples.
edges=Counter(tuple(sorted((int(a),int(b)))) for f in F0 for a,b in zip(f,np.roll(f,-1)))
boundary=[e for e,c in edges.items() if c==1]
# Ordered boundary cycles from mesh, used verbatim by adjacent surfaces.
adj={}
for a,b in boundary:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert all(len(v)==2 for v in adj.values()),'nonmanifold floor boundary'
cycles=[];seen=set()
for a in adj:
    if a in seen:continue
    loop=[a];prev=a;cur=adj[a][0]
    while cur!=a:
        loop.append(cur);nxt=next(n for n in adj[cur] if n!=prev);prev,cur=cur,nxt
    seen.update(loop);cycles.append(loop)
assert len(cycles)==7,len(cycles)
ringids={}
for loop in cycles:
    p=Polygon(xy[loop]); name=min({'outer':outer,**holes},key=lambda k:abs(p.area-({'outer':outer,**holes}[k]).area))
    ringids[name]=loop
assert set(ringids)==set(rings)
# Shared vertices, stitched surfaces. The outer cut ring is part of the model;
# upper wall continues to the hypothetical ceiling, omitted in overview camera.
def stitch(a,b,mat):
    assert len(a)==len(b)
    for i in range(len(a)):
        j=(i+1)%len(a);face([a[i],a[j],b[j]],mat);face([a[i],b[j],b[i]],mat)
def make_ring(a,scale,shift,zfun):
    p=np.array([V[i] for i in a]);center=p[:,:2].mean(0);q=center+(p[:,:2]-center)*scale+shift
    return [vert([x,y,zfun(i,x,y)]) for i,(x,y) in enumerate(q)]
# Rim orientation for lighting; faces use two-sided light anyway.
a=ringids['outer']; center=np.array([V[i][:2] for i in a]).mean(0)
# Short cut wall and full-height continuation are two connected rings, not tiles.
def wallring(level,scale,amp,zfun):
    pts=np.array([V[i][:2] for i in a]); v=pts-center; normal=v/np.linalg.norm(v,axis=1)[:,None]
    jitter=amp*(.55*np.sin(pts[:,0]/137+pts[:,1]/163+level)+.45*np.cos(pts[:,0]/83-pts[:,1]/121-level))
    qq=center+v*scale+normal*jitter[:,None]
    return [vert([x,y,zfun(i,x,y)]) for i,(x,y) in enumerate(qq)]
b=wallring(0,1.018,22,lambda i,x,y:V[a[i]][2]+CFG['wall_cut']*(.85+.15*np.cos(x/490)))
m=wallring(1,.993,48,lambda i,x,y:180+38*np.sin(x/310)+36*np.cos(y/190));
c=wallring(2,1.015,23,lambda i,x,y:roof(x,y));stitch(a,b,'wall');stitch(b,m,'upper_wall');stitch(m,c,'upper_wall'); roof_outer=c
# Massif emerges from its boundary; asymmetric ridge, shared base and shoulder.
a=ringids['massif']; shoulder=make_ring(a,.89,[-9,8],lambda i,x,y:V[a[i]][2]+27+8*np.sin(x/87));stitch(a,shoulder,'massif');b=make_ring(shoulder,.65,[-42,17],lambda i,x,y:88+18*np.sin(x/130)+8*np.cos(y/96));stitch(shoulder,b,'massif')
peak=vert([1840,2390,CFG['rock_peak']]);
for i in range(len(b)):face([b[i],b[(i+1)%len(b)],peak],'massif')
# A genuinely tall natural pillar, attached to floor; top is open at roof.
a=ringids['pillar'];b=make_ring(a,.69,[-30,14],lambda i,x,y:126+13*np.sin(x/123));c=make_ring(b,.82,[36,-22],lambda i,x,y:260+20*np.cos(y/85));e=make_ring(c,1.45,[-12,15],lambda i,x,y:roof(x,y));stitch(a,b,'pillar');stitch(b,c,'pillar');stitch(c,e,'pillar');roof_pillar=e
# The hole is open: its walls descend to an arbitrary visual cutoff; no floor/cap.
a=ringids['shaft'];b=make_ring(a,.87,[12,-4],lambda i,x,y:V[a[i]][2]-28-7*np.sin(x/60));c=make_ring(b,.72,[-12,12],lambda i,x,y:CFG['shaft_cut']);stitch(a,b,'shaft_rim');stitch(b,c,'shaft_dark')
# Isolated pond basin and separate water plane; no invented drainage path.
a=ringids['pool'];b=make_ring(a,.69,[0,0],lambda i,x,y:-62);stitch(a,b,'basin');center=vert([2400,290,-64]);
for i in range(len(b)):face([b[i],b[(i+1)%len(b)],center],'basin')
# Integrated natural rock aperture, a single continuous vault with no central partition.
a=ringids['portal']; coords=np.array([V[i] for i in a]); uu=(coords[:,:2]-O)@side; vv=(coords[:,:2]-O)@forward
# Jagged shoulders taper back from the front wall. Keep the full tunnel clearance.
b=[vert([*uv(u*.91+3*np.sin(v/21),v+8+3*np.sin(u/9)),12+13*np.sin(u/33)+8*np.cos(v/40)+4*np.sin(u/8)]) for u,v in zip(uu,vv)]
arch={};inner={};innerfloor={}
for i,(u,v) in enumerate(zip(uu,vv)):
    if abs(v)<1e-4 and abs(u)<=7.0001:
        z=-38+3.1+5.8*np.sqrt(max(0,1-(u/7)**2))+0.23*u+0.8*np.sin(u*1.1);arch[i]=vert([*coords[i,:2],z]);inner[i]=vert([*uv(u*.76+5,32),z-1.1]);innerfloor[i]=vert([*uv(u*.76+5,32),-39])
for i in range(len(a)):
    j=(i+1)%len(a)
    if i in arch and j in arch:
        face([arch[i],arch[j],b[j]],'portal_rock');face([arch[i],b[j],b[i]],'portal_rock')
        face([arch[i],arch[j],inner[j]],'tunnel');face([arch[i],inner[j],inner[i]],'tunnel')
        face([a[i],innerfloor[i],innerfloor[j]],'tunnel_floor');face([a[i],innerfloor[j],a[j]],'tunnel_floor')
        face([innerfloor[i],inner[i],inner[j]],'tunnel_dark');face([innerfloor[i],inner[j],innerfloor[j]],'tunnel_dark')
    elif i in arch:
        face([a[i],a[j],arch[i]],'portal_rock');face([arch[i],a[j],b[j]],'portal_rock');face([arch[i],b[j],b[i]],'portal_rock')
        face([a[i],arch[i],inner[i]],'tunnel');face([a[i],inner[i],innerfloor[i]],'tunnel')
    elif j in arch:
        face([a[i],a[j],arch[j]],'portal_rock');face([a[i],arch[j],b[i]],'portal_rock');face([b[i],arch[j],b[j]],'portal_rock')
        face([a[j],arch[j],inner[j]],'tunnel');face([a[j],inner[j],innerfloor[j]],'tunnel')
    else:face([a[i],a[j],b[j]],'portal_rock');face([a[i],b[j],b[i]],'portal_rock')
peak=vert([*uv(8,73),26]);
for i in range(len(b)):face([b[i],b[(i+1)%len(b)],peak],'portal_rock')
# Connected natural buttress below the PORT deck.
a=ringids['terminal_rock'];b=make_ring(a,.91,[8,-6],lambda i,x,y:43+8*np.sin(x/40));stitch(a,b,'terminal_rock')
c=make_ring(b,.75,[7,-8],lambda i,x,y:86+7*np.cos(y/35));stitch(b,c,'terminal_rock')
e=make_ring(c,.78,[8,1],lambda i,x,y:139.);stitch(c,e,'terminal_rock')
cap=vert([np.mean([V[i][0] for i in e]),np.mean([V[i][1] for i in e]),139.]);
for i in range(len(e)):face([e[i],e[(i+1)%len(e)],cap],'terminal_rock')
terminal_top=Polygon([V[i][:2] for i in e]);print('terminal upper shelf bounds',terminal_top.bounds,flush=True)
# Actual open rift loft and separate HOME shaft. All coordinates are trial values.
from shapely import constrained_delaunay_triangles, contains_xy
LEVELS=np.array([390.,520.,650.]);BOUNDS=np.array([[2110,2320],[2030,2240],[1970,2190]],float)
SHAPE=np.array([[1940,.22],[1905,.58],[1960,.88],[2100,1],[2430,.87],[2640,.64],[2780,.31],[2640,.12],[2390,.035],[2100,0]],float)
def aperture(i):
    l,r=BOUNDS[i];return ring(np.c_[l+(r-l)*SHAPE[:,1],SHAPE[:,0]+[0,14,-8][i]],45)
rift_polys=[Polygon(aperture(i)) for i in range(3)]
home_xy=np.array([[2033,1833],[2067,1833],[2067,1867],[2033,1867]],float)
ro=np.array([V[i][:2] for i in roof_outer]);rp=np.array([V[i][:2] for i in roof_pillar]);rd=Polygon(ro,[rp,aperture(0),home_xy]);assert rd.is_valid
rift_rings=[[vert([*q,z]) for q in aperture(i)] for i,z in enumerate(LEVELS)]
home_rings=[[vert([*q,z]) for q in home_xy] for z in LEVELS]
rr=roof_outer+roof_pillar+rift_rings[0]+home_rings[0];roof_idx={key(V[i][:2]):i for i in rr};roof_area=0.
# Irregular interior samples avoid long fan triangles across the ceiling.
roofpts=list(roof_idx);rrng=np.random.default_rng(1107)
for yy in np.arange(130,3300,82):
    for xx in np.arange(0,4950,82):
        q=np.array([xx,yy])+rrng.uniform(-24,24,2);pt=Point(q)
        if rd.contains(pt) and rd.boundary.distance(pt)>33:
            roofpts.append(key(q));roof_idx[key(q)]=vert([*q,roof(*q)+13*np.sin(q[0]/105)*np.cos(q[1]/140)+6*np.sin((q[0]+q[1])/57)])
rpts=np.asarray(roofpts);rdt=Delaunay(rpts);rooftris0=[];rd_buf=rd.buffer(1e-5)
for f in rdt.simplices:
    tri=Polygon(rpts[f]);
    if rd_buf.covers(tri):rooftris0.append(tri);roof_area+=tri.area;face([roof_idx[key(q)] for q in rpts[f]],'ceiling')
print('roof triangulation pre-repair area error',roof_area-rd.area,flush=True)
# Fill any concave-boundary gaps using constrained triangles; original boundary vertices are preserved.
if rd.area-roof_area>.01:
    from shapely.ops import unary_union
    missing=rd.difference(unary_union(rooftris0));parts=[missing] if missing.geom_type=='Polygon' else list(missing.geoms)
    for part in parts:
        if part.geom_type!='Polygon' or part.area<1e-7:continue
        for tri in constrained_delaunay_triangles(part).geoms:
            q=np.asarray(tri.exterior.coords[:-1]);ids=[roof_idx[key(v)] for v in q];face(ids,'ceiling');roof_area+=tri.area
assert abs(roof_area-rd.area)<.01
for ringset,mat in [(rift_rings,'rift'),(home_rings,'lift_shaft')]:
    for a,b in zip(ringset,ringset[1:]):stitch(a,b,mat)
print('roof area error',roof_area-rd.area,'rift aperture areas',[round(p.area,1) for p in rift_polys],flush=True)
# Check topology of rock mesh before any semantic road/water overlay.
E=Counter(tuple(sorted((i,j))) for f in F for i,j in zip(f,np.roll(f,-1)))
print("max rock edge incidence",max(E.values()),"nonmanifold edges",sum(v>2 for v in E.values()));print("nonmanifold locations",[(V[i],V[j],v) for (i,j),v in E.items() if v>2][:8])
# Only the cave wall top, pillar top and shaft cutoff are open; all surfaces joined.
used=set(i for f in F for i in f); nbr={i:[] for i in used}
for a,b in E:nbr[a].append(b);nbr[b].append(a)
visited=set();todo=[next(iter(used))]
while todo:
    i=todo.pop()
    if i in visited:continue
    visited.add(i);todo.extend(j for j in nbr[i] if j not in visited)
assert len(visited)==len(used) and max(E.values())<=2
print('connected rock vertices',len(visited),'of',len(used))
print('floor coverage error m2',round(domain.area-area,5),'rock components',1,'rock vertices',len(used),'rock triangles',len(F))
# Use floor interpolation, excluding triangles clipped away when validating points.
interp=LinearNDInterpolator(d,zz)
for n,(x,y,z) in P.items():assert abs(float(interp(x,y))-z)<1e-5,n
# Cross-section and road geometry use exact same mesh surface. Road strips are draped
# with offsets for visibility, not asserted as physical widths. Bridge remains a deck.
maxerr=0
for r,a,b,q in roads:
    for x,y,z in q:
        if r==245 and np.linalg.norm([x-bridge[0],y-bridge[1]])<65:continue
        maxerr=max(maxerr,abs(float(interp(x,y))-z))
assert maxerr<1e-5,maxerr
print('road sample height residual m',maxerr)
rock_clear=min(holes['terminal_rock'].distance(LineString(q[:,:2]))-(CFG['road_width'] if r in main else CFG['local_width'])/2 for r,a,b,q in roads);print('terminal rock road clearance m',rock_clear);assert rock_clear>0
# Add water surface and visual road ribbons to the scene.
q=np.array(holes['pool'].buffer(-9).exterior.coords[:-1]); ids=[vert([x,y,-56]) for x,y in q]; center=vert([*q.mean(0),-56]);
for i in range(len(ids)):face([ids[i],ids[(i+1)%len(ids)],center],'water')

def ribbon(q,width,mat,deck=False,offset=2.3):
    q=np.asarray(q,float); a=[];b=[]
    for i,(x,y,z) in enumerate(q):
        delta=q[min(i+1,len(q)-1),:2]-q[max(i-1,0),:2]; norm=np.linalg.norm(delta)
        if norm<1e-8:continue
        side=np.array([-delta[1],delta[0]])/norm*width/2
        for out,sign in [(a,1),(b,-1)]:
            p=np.array([x,y])+sign*side; zz0=float(interp(*p))
            if not np.isfinite(zz0) or (deck and np.linalg.norm([x-bridge[0],y-bridge[1]])<75):zz0=z
            out.append(vert([*p,zz0+offset]))
    for i in range(len(a)-1):face([a[i],a[i+1],b[i+1]],mat);face([a[i],b[i+1],b[i]],mat)
# Clip semantic surfaces to actual triangles, then lift by a small display offset.
# Unlike ribbons sampled only along their edges, these surfaces share the exact piecewise-linear terrain.
floorpolys=[Polygon(xy[f]) for f in F0]; index=STRtree(floorpolys)
def drape(geom,mat,offset):
    for i in index.query(geom,predicate='intersects'):
        inter=floorpolys[i].intersection(geom)
        if inter.is_empty:continue
        parts=[inter] if inter.geom_type=='Polygon' else list(getattr(inter,'geoms',[]))
        f=F0[i]; xy0=xy[f]; z0=zz[f]
        A=np.column_stack([xy0,np.ones(3)]);
        if abs(np.linalg.det(A))<1e-6:continue
        coef=np.linalg.solve(A,z0)
        for g in parts:
            if g.geom_type!='Polygon' or g.area<.00001:continue
            coords=np.array(g.exterior.coords[:-1]); h=np.column_stack([coords,np.ones(len(coords))])@coef+offset
            ids=[vert([*p,z]) for p,z in zip(coords,h)]
            # Intersection of a triangle with a simple narrow strip is normally convex;
            # use constrained triangulation for non-convex intersections.
            from shapely import constrained_delaunay_triangles
            im={key(p):v for p,v in zip(coords,ids)}
            for tr in constrained_delaunay_triangles(g).geoms:
                pp=np.array(tr.exterior.coords[:-1]);face([im[key(p)] for p in pp],mat)
river_geom=LineString(riverq[:,:2]).buffer(9,cap_style=2,join_style=2)
# Water is planar across the channel; slope along its course, not draped over rock.
# Cut polygon to floor domain so no overlapping pond surface.
water_line=LineString(riverq[:,:2]); water_poly=water_line.buffer(8.0,cap_style=2,join_style=2).intersection(domain)
from shapely import constrained_delaunay_triangles
# Segmentwise quads, clipped to domain; transverse water elevation identical on both banks.
for i in range(len(riverq)-1):
    p,q=riverq[i:i+2];delta=q[:2]-p[:2];delta/=np.linalg.norm(delta);normal=np.array([-delta[1],delta[0]])
    geom=Polygon([p[:2]+normal*8,p[:2]-normal*8,q[:2]-normal*8,q[:2]+normal*8]).intersection(domain)
    # Never create water across the N114 access road. Bridge crossing is separate deck.
    for ri,aa,bb,rr in roads:
        if ri!=245 and geom.distance(LineString(rr[:,:2]))<8:geom=geom.difference(LineString(rr[:,:2]).buffer(5))
    if geom.is_empty:continue
    for g in ([geom] if geom.geom_type=='Polygon' else getattr(geom,'geoms',[])):
        if g.geom_type!='Polygon':continue
        for tr0 in constrained_delaunay_triangles(g).geoms:
            pts=np.array(tr0.exterior.coords[:-1]);t=np.clip((pts-p[:2])@(q[:2]-p[:2])/np.sum((q[:2]-p[:2])**2),0,1)
            ids=[vert([*pp,z]) for pp,z in zip(pts,p[2]+t*(q[2]-p[2]))];face(ids,'water')

drape(Polygon(T['growth']),'growth',.12)
bridge_zone=Point(bridge).buffer(65)
for r,a,b,q in roads:
    geom=LineString(q[:,:2]).buffer((CFG['road_width'] if r in main else CFG['local_width'])/2,cap_style=2,join_style=2)
    if r==245:
        drape(geom.difference(bridge_zone),'local',.08)
        if geom.intersects(bridge_zone):
            g=geom.intersection(bridge_zone);coords=np.array(g.exterior.coords[:-1]);dxy=q[-1,:2]-q[0,:2]
            # only S32 crosses the river. Preserve interpolated bridge deck profile.
            t=np.clip((coords-q[0,:2])@dxy/(dxy@dxy),0,1);height=q[0,2]+t*(q[-1,2]-q[0,2])+.08
            ids=[vert([*p,z]) for p,z in zip(coords,height)]
            for i in range(1,len(ids)-1):face([ids[0],ids[i],ids[i+1]],'local')
    else:drape(geom,'main' if r in main else 'local',.08)
for n,ps,name in trails:
    p=sample([P[n][:2],*ps],35)
    drape(LineString(p).buffer(CFG['trail_width']/2,cap_style=2),'trail',.10)
# Visual props: provisional human-scale elements, not registered facilities.
def box(c,size,mat):
    c=np.asarray(c);d=np.asarray(size)/2;ids=[vert(c+d*np.array([x,y,z])) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    for a,b,c,d in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]:face([ids[a],ids[b],ids[c]],mat);face([ids[a],ids[c],ids[d]],mat)
# Living illumination layer; preserve the rock geometry and routes.
lrng=np.random.default_rng(7106)
lights={k:[] for k in ['planted','wild','roof','lamp']}
from shapely.ops import unary_union
keepout=unary_union([LineString(q[:,:2]).buffer((CFG['road_width'] if r in main else CFG['local_width'])/2+.4) for r,a,b,q in roads]+[LineString([P[n][:2],*ps]).buffer(CFG['trail_width']/2+.5) for n,ps,name in trails]+[river_geom,bridge_zone])
keepout=unary_union([keepout,rail_bed.buffer(.5)])
def moss_patch(p,scale,kind,detail=False):
    p=np.asarray(p);a=np.arange(8)*np.pi/4+lrng.uniform(0,6.28);ring=p+np.c_[np.cos(a),np.sin(a)]*scale*lrng.uniform(.48,1.08,(8,1));poly=Polygon(ring)
    if not domain.covers(poly) or keepout.intersects(poly) or (kind=='wild' and np.linalg.norm(p-O)<100):return
    z=float(interp(*p));zs=np.asarray(interp(ring));
    if not np.isfinite(z) or not np.all(np.isfinite(zs)) or np.ptp(zs)>1.3*scale:return
    mat='moss_planted' if kind=='planted' else 'moss_wild';ids=[vert([*q,h+.07]) for q,h in zip(ring,zs)];c=vert([*p,z+.11+scale*.05])
    for i in range(8):face([ids[i],ids[(i+1)%8],c],mat)
    lights[kind].append([*p,z+.16+scale*.06])
    if detail:
        for _ in range(16):
            ang=lrng.uniform(0,2*np.pi);q=p+np.array([np.cos(ang),np.sin(ang)])*lrng.uniform(.06,.32)*scale;h=float(interp(*q));v=np.array([np.cos(ang),np.sin(ang)])*lrng.uniform(.045,.13);tip=q+v*lrng.uniform(1.3,2.8)
            if np.isfinite(h) and poly.covers(Point(tip)):face([vert([*(q-v),h+.06]),vert([*(q+v),h+.06]),vert([*tip,h+lrng.uniform(.09,.30)])],mat)
# Roadside communities alternate dense planted banks and gaps.
for r,a,b,q in roads:
    if r==0:continue
    ss=sample(q,CFG['moss_spacing']*(1 if r in main else 1.9));width=(CFG['road_width'] if r in main else CFG['local_width'])/2
    for i,p in enumerate(ss[1:-1],1):
        d=ss[i+1,:2]-ss[i-1,:2];d/=np.linalg.norm(d);n=np.array([-d[1],d[0]])
        for sign in [-1,1]:
            abundance=.5+.29*np.sin(p[0]/43+p[1]/27+sign*1.7)+.21*np.sin(p[0]/13-p[1]/17)
            if lrng.random()>np.clip(abundance+.23 if r in main else abundance-.05,.09,.96):continue
            c=p[:2]+sign*n*(width+lrng.uniform(1.8,4.2))+d*lrng.uniform(-2.8,2.8)
            near=np.linalg.norm(c-np.array(P['GATE'][:2]))<130 or np.linalg.norm(c-slope_pt(450,31))<100 or np.linalg.norm(c-O)<65
            for j in range(lrng.integers(2,5)):
                p2=c+d*lrng.uniform(-2.8,2.8)+sign*n*lrng.uniform(.0,2.3)
                moss_patch(p2,lrng.uniform(.65,1.65),'planted',near)
# Existing river wet-bank colonies, not a new watercourse.
for i,p in enumerate(riverq[1:-1],1):
    d=riverq[i+1,:2]-riverq[i-1,:2];d/=np.linalg.norm(d);n=np.array([-d[1],d[0]])
    for sign in [-1,1]:
        if lrng.random()<.26:continue
        c=p[:2]+sign*n*lrng.uniform(13,31)
        for j in range(lrng.integers(4,10)):moss_patch(c+lrng.normal(0,8,2),lrng.uniform(2.0,5.0),'wild')
for cx,cy,sd,count in [(2390,290,105,240),(1120,980,95,90),(3810,830,110,210),(1800,665,75,90),(2950,660,95,160),(1850,2150,90,45),(2240,930,80,150),(2710,680,65,100)]:
    for _ in range(count):
        pt=np.array([cx,cy])+lrng.normal(0,sd,2)
        if np.linalg.norm(pt-O)>100:moss_patch(pt,lrng.uniform(1.3,4.0),'wild',False)
def service_lamp(x,y):
    z=float(interp(x,y));
    if not np.isfinite(z):return
    box([x,y,z+.30],[.78,.78,.6],'cargo');box([x,y,z+1.05],[.28,.28,1.4],'iron');box([x,y,z+1.87],[.46,.46,.46],'lamp');box([x,y,z+2.16],[.62,.62,.12],'iron');lights['lamp'].append([x,y,z+1.87])
for x,y in [(2198,2007),(2222,1992),(1502,2008),(2056,1505),(2755,846),(3725,2008),(3008,2652),(1757,2948),(3850,430),(1060,1056),(2106,520),(1740,665),(4357,1550),(550,2007),(1255,2657)]:service_lamp(x,y)
rooftris=np.array([[V[j] for j in f] for f,m in zip(F,M) if m=='ceiling']);areas=np.linalg.norm(np.cross(rooftris[:,1]-rooftris[:,0],rooftris[:,2]-rooftris[:,0]),axis=1)/2;areas/=areas.sum()
# Clustered ceiling communities, separated by dark rock.
for idx in lrng.choice(len(rooftris),size=12500,p=areas):
    tri=rooftris[idx];a,b=lrng.random(2);a,b=(1-a,1-b) if a+b>1 else (a,b);x,y,z=tri[0]+a*(tri[1]-tri[0])+b*(tri[2]-tri[0]);
    band=.5+.26*np.sin(x/210+y/115)+.17*np.sin(x/90-y/180)+.07*np.cos(x/39+y/35)
    if lrng.random()<.035+.76*band**3:lights['roof'].append([x,y,z-.45])
def person(x,y,mat='figure'):
    z=float(interp(x,y));box([x,y,z+1.12],[.32,.25,.55],mat);box([x,y,z+1.58],[.21,.21,.24],mat)
    for dy in [-.12,.12]:box([x,y+dy,z+.37],[.18,.16,.74],mat)
    for dy in [-.23,.23]:box([x,y+dy,z+1.03],[.14,.14,.52],mat)
for x,y in [(2194,1997),(2184,2003),(2177,1999),(2200,1996),(2155,2001)]:person(x,y)
for x,y in [(2195,2010),(2198,2011),(2192,2012),(2190,2010),(2186,2011),(2185,2014)]:
    z=float(interp(x,y));box([x,y,z+.55],[1.7,1.5,1.1],'cargo')
for x,y in [(2202,2013),(2173,2013)]:
    z=float(interp(x,y));box([x,y,z+.65],[2.6,2.4,1.3],'cargo')
# Provisional Lamplighter planting work area, not a registered FACILITY.
for x,y in [(2188,1988),(2193,1988),(2198,1988)]:
    z=float(interp(x,y));box([x,y,z+.10],[3.3,1.7,.2],'stonework')
    for k in range(7):moss_patch(np.array([x,y])+lrng.uniform([-.9,-.4],[.9,.4]),.48,'planted',True)
    for dy in [-.94,.94]:box([x,y+dy,z+.22],[3.55,.22,.44],'stonework')
person(2194,1986)
for d0,u in [(463,15),(475,12),(690,0),(800,0)]:person(*slope_pt(d0,u))
for d0 in [440,455,470,485,500,515,530,545,560,575,590]:
    x,y=slope_pt(d0,29);z=float(interp(x,y));box([x,y,z+.45],[.48,.48,.9],'cargo')
for u,v in [(-2,-12),(1,-18)]:
    person(*uv(u,v));q=uv(u+.35,v);z=float(interp(*q));box([*q,z+1.15],[.19,.19,.24],'lamp');lights['lamp'].append([*q,z+1.15])

# Provisional architecture. The opaque boxes are included in direct light occlusion.
architecture=[]
def solid(c,size,mat='stonework'):
    c=np.asarray(c,float);size=np.asarray(size,float);architecture.append((c-size/2,c+size/2));box(c,size,mat)
def beam(a,b,width,mat='iron'):
    a,b=np.asarray(a,float),np.asarray(b,float);d=b-a;d/=np.linalg.norm(d);u=np.cross(d,[0,0,1.]);u=np.cross(d,[0,1.,0]) if np.linalg.norm(u)<.01 else u;u=u/np.linalg.norm(u)*width/2;v=np.cross(d,u);ids=[vert(p+su*u+sv*v) for p in [a,b] for su,sv in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    for i,j,k,l in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]:face([ids[i],ids[j],ids[k]],mat);face([ids[i],ids[k],ids[l]],mat)
for x in [2039,2061]:
    for y in [1839,1861]:
        z=float(interp(x,y));solid([x,y,(650+z)/2],[3,3,650-z])
for z in range(20,651,26):
    for y in [1839,1861]:beam([2039,y,z],[2061,y,z],1.3);beam([2039,y,z],[2061,y,z+22],.65)
    for x in [2039,2061]:beam([x,1839,z],[x,1861,z],1.3)
solid([2050,1850,142],[25,30,6],'stonework')
solid([2188,1850,142],[251,13,6]);solid([2380,1850,142],[140,14,6]);solid([2450,1850,142],[120,76,6])
for x in [2110,2170,2230,2290]:
    for y in [1845,1855]:
        z=float(interp(x,y));solid([x,y,(139+z)/2],[5,5,139-z]);beam([x,y,105],[x+24,y,139],2.8,'stonework')
link=LineString([[2050,1864],[2080,1900],[2160,1935],[2210,1980],[2210,2000]])
drape(link.buffer(2.2,cap_style=2),'local',.10)
for x,y in [(2500,1880),(2395,1880),(2500,1820)]:
    z=100.;solid([x,y,(139+z)/2],[5,5,139-z]);beam([x,y,112],[2450,1850,139],3,'stonework')
for x in range(2070,2490,25):
    for y in [1843.5,1856.5]:beam([x,y,145],[x,y,147],.45);beam([x,y,147],[x+25,y,147],.45)
def shed(x,y,z,w,d,h):
    solid([x,y,z+h/2],[w,d,h],'stonework');rr=[vert([x-w/2,y-d/2,z+h]),vert([x+w/2,y-d/2,z+h]),vert([x+w/2,y+d/2,z+h]),vert([x-w/2,y+d/2,z+h]),vert([x-w/2,y,z+h+3]),vert([x+w/2,y,z+h+3])]
    for tri in [(0,1,5),(0,5,4),(3,4,5),(3,5,2),(0,4,3),(1,2,5)]:face([rr[i] for i in tri],'roof_tile')
for x,y,w,d,h in [(2415,1828,23,16,8),(2445,1828,20,16,10),(2473,1828,20,16,7),(2415,1873,18,14,8)]:shed(x,y,145,w,d,h)
for x in [2435,2450,2470]:solid([x,1870,146],[3,3,2],'cargo')
for x,y,z,w,d in [(2360,1800,86,42,14),(2430,1750,86,54,15),(2490,1800,43,34,15)]:
    solid([x,y,z],[w,d,3]);shed(x,y,z+1.5,min(w-8,22),d-4,6)
    for xx in [x-w/2+3,x+w/2-3]:beam([xx,y,z-20],[xx,y+d/2,z-1.5],2.2,'stonework')
def ellipsoid(c,r,mat):
    c=np.asarray(c);r=np.asarray(r);rings=[]
    for phi in np.linspace(-np.pi/2+.04,np.pi/2-.04,9):rings.append([vert(c+r*np.array([np.cos(phi)*np.cos(t),np.cos(phi)*np.sin(t),np.sin(phi)])) for t in np.linspace(0,2*np.pi,16,endpoint=False)])
    for a,b in zip(rings,rings[1:]):stitch(a,b,mat)
    for a,sgn in [(rings[0],-1),(rings[-1],1)]:
        cap=vert(c+np.array([0,0,sgn*r[2]]))
        for i in range(len(a)):face([a[i],a[(i+1)%len(a)],cap],mat)
ellipsoid([2550,1800,191],[45,13,13],'envelope');solid([2550,1800,168],[28,7,5],'cargo')
for x in [2538,2562]:
    for y in [1797,1803]:beam([x,y,171],[x,y,180],.3)
z0=float(interp(2050,1850));solid([2050,1850,z0+1],[28,28,2]);
# Gate arch spans road, its piers are outside the 9m road width.
for y in [1992,2008]:
    z=float(interp(2210,y));solid([2210,y,z+5],[4,3.5,10]);solid([2210,y,z+.6],[5,4.5,1.2])
for t0,t1 in zip(np.linspace(0,np.pi,13)[:-1],np.linspace(0,np.pi,13)[1:]):beam([2210,2000+8*np.cos(t0),9+8*np.sin(t0)],[2210,2000+8*np.cos(t1),9+8*np.sin(t1)],3.4,'stonework')
for y in [1993,2007]:solid([2210,y,7],[1.4,1.4,2.1],'lamp');lights['lamp'].append([2210,y,7])
for x in [2400,2500]:
    for y in [1820,1880]:solid([x,y,147],[1.2,1.2,4]);solid([x,y,150],[1.5,1.5,1.5],'lamp');lights['lamp'].append([x,y,150])
# Paired warm gate beacons at night; no extra street lamp rows.
for y in [1987,2013]:
    z=float(interp(2210,y));solid([2210,y,z+7],[5,5,14]);solid([2210,y,z+14.8],[4.4,4.4,2.3],'beacon');solid([2210,y,z+16.4],[6,6,1]);lights['lamp'].append([2210,y,z+14.8])
for x,y in [(2184,2024),(2238,2018),(2190,1974)]:
    z=float(interp(x,y));shed(x,y,z,16,10,7);solid([x-8.2,y,z+3.5],[.45,2.5,2.2],'beacon');lights['lamp'].append([x-8.4,y,z+3.5])
# Narrow gauge industrial rail and transfer yard: trial only.
def obox(c,size,axis,mat):
    c=np.asarray(c,float);axis=np.asarray(axis,float);axis/=np.linalg.norm(axis);n=np.array([-axis[1],axis[0]]);dx,dy,dz=np.asarray(size)/2
    ids=[vert(c+np.r_[a*dx*axis+b*dy*n,k*dz]) for a,b,k in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    for a,b,c,d in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]:face([ids[a],ids[b],ids[c]],mat);face([ids[a],ids[c],ids[d]],mat)
def frame_at(q,i):
    d=q[min(i+1,len(q)-1),:2]-q[max(i-1,0),:2];d/=np.linalg.norm(d);return d,np.array([-d[1],d[0]])
rail_metrics={}
for name,q in rail_specs:
    line=LineString(q[:,:2]);drape(line.buffer(1.65,cap_style=2),'ballast',.07)
    grade=np.diff(q[:,2])/np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1);res=np.max(np.abs(interp(q[:,:2])-(q[:,2]-.16)))
    rail_metrics[name]={'horizontal_length_m':float(line.length),'max_sample_grade_percent':float(np.max(np.abs(grade))*100),'floor_control_residual_m':float(res),'road_clearance_m':float(line.buffer(1.65,cap_style=2).distance(road_mask)),'nominal_gauge_m':.9};assert res<1e-5
    ties=sample(q,1.25 if name=='active' else 1.55)
    for i,p in enumerate(ties):
        if name=='abandoned' and ((i//5)%11 in (3,4) or i%7==2):continue
        d,n=frame_at(ties,i);obox(p+[0,0,.02],[.25,1.6,.15],d,'sleeper_old' if name=='abandoned' else 'sleeper')
    for i,(p,t) in enumerate(zip(q,q[1:])):
        if name=='abandoned' and (i//7)%6 in (2,3):continue
        _,n=frame_at(q,i);_,n2=frame_at(q,i+1)
        for sign in (-1,1):beam(p+np.r_[n*.45*sign,.17],t+np.r_[n2*.45*sign,.17],.09,'rail_old' if name=='abandoned' else 'rail')
    if name=='active':
        for i in [3,4,5,14,39,95,235,345]:
            if i>=len(q)-1:continue
            p=q[i];d,n=frame_at(q,i)
            obox(p+[0,0,.56],[2.65,1.18,.22],d,'iron')
            for sign in [-1,1]:
                obox(p+np.r_[n*.51*sign,.94],[2.45,.13,.64],d,'wagon');obox(p+np.r_[d*1.17*sign,.94],[.14,1.10,.64],d,'wagon')
                for j in [-.79,.79]:obox(p+np.r_[n*.47*sign+d*j,.31],[.42,.15,.42],d,'iron')
            for j in [-.7,0,.7]:obox(p+np.r_[d*j,1.01],[.7,.78,.48],d,'ore')
        for i in [0,len(q)-1]:
            p=q[i];d,n=frame_at(q,i);obox(p+[0,0,.48],[.22,1.6,.8],d,'sleeper')
active=rail_specs[0][1];yard=active[:17].copy();yard[:,1]-=4.3
for i,p in enumerate(yard[:-1]):beam(p+[0,0,.26],yard[i+1]+[0,0,.26],1.2,'stonework')
for x,y,w,d,h in [(2260,1951,18,12,5),(2286,1948,24,13,7),(2317,1944,20,12,6)]:
    z=float(interp(x,y));shed(x,y,z,w,d,h);solid([x,y+d/2+.08,z+2.0],[3,.18,3.5],'woodwork')
    lights['lamp'].append([x,y+d/2+1,z+3.8]);box([x,y+d/2+1,z+3.8],[.5,.5,.7],'lamp')
    for j in [-4,0,4]:solid([x+j,y+d/2+2.4,z+.65],[2.3,1.6,1.3],'cargo')
transfer=LineString([[2244,1970],[2231,1954],[2190,1940],[2160,1935]])
drape(transfer.buffer(1.8,cap_style=2),'local',.09)
# Layered port loading halls and timber cranes.
for x in [2395,2425,2455,2485]:
    for y in [1838,1864]:
        solid([x,y,148],[1.5,1.5,6],'stonework');beam([x,y,150.8],[x+10,y,154.5],1.1,'stonework');beam([x+10,y,154.5],[x+20,y,150.8],1.1,'stonework')
for x in [2406,2488]:
    y=1879;beam([x,y,145],[x,y,158],1.4,'woodwork');beam([x,y,158],[x+12,y+9,158],.75,'woodwork');beam([x,y,151],[x+10,y+7,158],.65,'woodwork');beam([x+12,y+9,158],[x+12,y+9,149],.12,'iron')
for x,y,z in [(2360,1800,86),(2430,1750,86),(2490,1800,43)]:
    for j in [-9,0,9]:beam([x+j,y-6,z+1.5],[x+j,y-6,z+3],.45,'stonework')
    beam([x-12,y-6,z+3],[x+12,y-6,z+3],.45,'stonework')
(OUT/'ruosuen_previs12_rail_validation.json').write_text(json.dumps(rail_metrics,indent=2)+'\n');print('rail metrics',rail_metrics,flush=True)

# Sky backdrop is not a rock closure. Exclude from exported OBJ.
for ids in [rift_rings[-1],home_rings[-1]]:
    c=vert(np.mean([V[i] for i in ids],axis=0)+[0,0,.01]);
    for i in range(len(ids)):face([ids[i],ids[(i+1)%len(ids)],c],'sky')
V=np.array(V);F=np.array(F);M=np.array(M)
COL={'floor':'#8c8f83','wall':'#8c8b83','upper_wall':'#777f7d','ceiling':'#626e70','massif':'#8f8c7d','pillar':'#aaa492','shaft_rim':'#7d8177','shaft_dark':'#253332','basin':'#7c8580','water':'#427e91','growth':'#738d69','main':'#ad9b7c','local':'#ada18a','trail':'#b0a18c','portal_rock':'#a29a87','tunnel':'#363d39','tunnel_floor':'#77756a','tunnel_dark':'#101d20','iron':'#403b32','lamp':'#ffd598','figure':'#695344','cargo':'#8f7657','moss_planted':'#75ae78','moss_wild':'#416e60','stonework':'#a19c87','rift':'#88877c','lift_shaft':'#6b706e','envelope':'#b9a98b','sky':'#c2e0ee','terminal_rock':'#8e8b7f','roof_tile':'#5d625e','beacon':'#ffd38a','rail':'#a5a9a1','rail_old':'#806751','sleeper':'#685344','sleeper_old':'#66594c','ballast':'#77776b','wagon':'#755b45','ore':'#7b9e9d','woodwork':'#77624d'}
from PIL import Image
p=V[F];norm=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-12)
light=np.array([-.44,-.38,.81]);light/=np.linalg.norm(light)
base=np.array([to_rgb(COL[m]) for m in M]);shade=.28+.72*np.abs(norm@light);shade[M=='ceiling']*=.68;shade[np.isin(M,['wall','upper_wall'])]*=.9;shade[np.isin(M,['lamp','beacon'])]=1.25;shade[M=='tunnel_dark']=.28
cent=p.mean(1);variation=1+.095*np.sin(cent[:,0]/81+cent[:,1]/103)+.06*np.cos(cent[:,0]/32-cent[:,1]/47);shade*=variation
warm=np.exp(-((cent[:,0]-2210)**2+(cent[:,1]-2000)**2)/180**2);base=np.clip(base+warm[:,None]*np.array([.10,.035,-.035]),0,1)
shade[M=='water']*=1.18
steep=(M=='floor') & (np.abs(norm[:,2])<.72);base[steep]=np.array([.52,.50,.45]);shade[steep]*=.82
low=(M=='floor') & (cent[:,2]<-48);base[low]=base[low]*np.array([.86,.98,1.04])
# Damp bank rock: subdued chroma and darker stone; water is a separate material.
wetdist=rv.query(cent[:,:2])[0];wet=(M=='floor')&(wetdist<45)&(cent[:,2]<-12)
base[wet]*=np.array([.65,.85,.87]);shade[wet]*=.88
rgb=np.clip(base*shade[:,None],0,1)

light_arrays={k:np.asarray(v,dtype=float).reshape(-1,3) for k,v in lights.items()};light_trees={k:cKDTree(v) for k,v in light_arrays.items() if len(v)}
print('light counts', {k:len(v) for k,v in lights.items()})
from scipy.ndimage import gaussian_filter
SUN=np.array([-.12,.015,1.]);DAY=True
from shapely.affinity import translate
from shapely.geometry.polygon import orient
# The intersection is the exact 2D footprint at z=0 for this direction through all three aperture sections.
foot=rift_polys[0]
foot=translate(foot,-LEVELS[0]*SUN[0],-LEVELS[0]*SUN[1])
for level,poly in zip(LEVELS[1:],rift_polys[1:]):foot=foot.intersection(translate(poly,-level*SUN[0],-level*SUN[1]))
# The footprint is convex (verified below); clip rays against each half plane.
assert abs(foot.convex_hull.area-foot.area)<1e-5,(foot.convex_hull.area,foot.area)
foot=orient(foot,sign=1.0);edgepoints=np.asarray(foot.exterior.coords[:-1]);print('beam footprint area',round(foot.area,2),flush=True)
def beam_length(cam,pts,d):
    r=(pts-cam)/d[:,None];c=cam[:2]-cam[2]*SUN[:2];v=r[:,:2]-r[:,2,None]*SUN[:2];lo=np.zeros(len(d));hi=d.copy();ok=np.ones(len(d),bool)
    def cut(a,b):
        nonlocal lo,hi,ok
        parallel=np.abs(b)<1e-10;ok &= (~parallel)|(a>=0);t=np.divide(-a,b,out=np.zeros_like(b),where=~parallel);lo=np.maximum(lo,np.where(b>1e-10,t,-np.inf));hi=np.minimum(hi,np.where(b<-1e-10,t,np.inf))
    for q,w in zip(edgepoints,np.roll(edgepoints,-1,axis=0)):
        e=w-q;n=np.array([-e[1],e[0]]);cut(float(n@(c-q)),v@n)
    cut(cam[2]+85,r[:,2]);cut(390-cam[2],-r[:,2]);return np.where(ok,np.maximum(0,hi-lo)*np.linalg.norm(r,axis=1),0)

def direct_light(pts,obstacles=True):
    pts=np.asarray(pts);ok=np.ones(len(pts),bool)
    for level,poly in zip(LEVELS,rift_polys):
        t=level-pts[:,2];q=pts[:,:2]+t[:,None]*SUN[:2];ok &= (t<=1e-5) | contains_xy(poly,q[:,0],q[:,1])
    if obstacles:
        ids=np.flatnonzero(ok);q=pts[ids];blocked=np.zeros(len(q),bool)
        for l,h in architecture:
            aa=(l-q)/SUN;bb=(h-q)/SUN;enter=np.max(np.minimum(aa,bb),axis=1);leave=np.min(np.maximum(aa,bb),axis=1);blocked|=(leave>np.maximum(enter,.06))&(enter<650-q[:,2])
        ok[ids[blocked]]=False
    return ok
def light_image(im,depth,emit,watermask,cam,right,up,f,focal):
    h,w=depth.shape;Y,X=np.indices((h,w),dtype=np.float32);valid=depth>0;D=np.where(valid,1/np.maximum(depth,1e-12),1e6);d=D[valid]
    pts=cam+((X[valid]+.5-w/2)/focal*d)[:,None]*right+((h/2-Y[valid]-.5)/focal*d)[:,None]*up+d[:,None]*f
    light=np.zeros((len(pts),3),np.float32)
    for k,radius,power,color in [('planted',4.2,CFG['moss_intensity'],[.45,1.,.66]),('wild',9.0,CFG['natural_intensity']*.53,[.35,.82,.78]),('lamp',9.,CFG['lamp_intensity'],[1.,.67,.32]),('roof',22.,CFG['roof_glow']*.22,[.35,.65,.85])]:
        if k not in light_trees:continue
        dist,_=light_trees[k].query(pts,k=min(3,len(light_arrays[k])),workers=4);dist=dist.reshape(len(pts),-1)
        strength=np.minimum(1.,np.sum(np.exp(-(dist/radius)**2),axis=1)*power);light+=strength[:,None]*np.array(color)
    if np.linalg.norm(cam[:2]-O)<65:light+=(.22*np.exp(-(d/13)**2))[:,None]*np.array([1.,.74,.48])
    raw=im.astype(np.float32)/255;out=np.zeros_like(raw);atmos=1-np.exp(-d/CFG['fog_distance'])
    day=(direct_light(pts)&(pts[:,2]<390)) if DAY else np.zeros(len(pts),bool)
    daylight=day[:,None]*np.array([.91,.83,.65]);dist_gate=np.linalg.norm(pts[:,:2]-[2210,2000],axis=1);bounce=(.28*np.exp(-dist_gate/240))[:,None]*np.array([1.,.92,.75]) if DAY else (.17*np.exp(-(dist_gate/38)**2))[:,None]*np.array([1.,.69,.34])
    out[valid]=np.clip(raw[valid]*(CFG['ambient']+light+daylight+bounce)+np.array([.014,.022,.026])+atmos[:,None]*np.array([.018,.032,.043]),0,1)
    if DAY:
        length=beam_length(cam,pts,d);vol=.20*(1-np.exp(-length/155));out[valid]+=vol[:,None]*np.array([.92,.85,.65])
    sky=watermask[valid]==2;tmp=out[valid];tmp[sky]=[.73,.85,.91] if DAY else [.025,.045,.09];out[valid]=tmp
    print('direct lit pixels',int(day.sum()),'sky pixels',int(sky.sum()),flush=True)
    # Approximate reflected ceiling and bank light using actual surface points and view angle.
    # No physical ray tracing: procedural ripples and Fresnel-like response on water pixels only.
    wm=watermask[valid]==1
    if wm.any():
        wp=pts[wm];view=cam-wp;view/=np.linalg.norm(view,axis=1)[:,None];fresnel=.18+.72*(1-np.abs(view[:,2]))**4
        waves=(.5+.5*np.sin(wp[:,0]*1.15+wp[:,1]*.77+2*np.sin(wp[:,1]*.29)))**5
        bands=.5+.5*np.sin(wp[:,0]/29+wp[:,1]/17)
        rawwater=np.array([.035,.12,.17])+fresnel[:,None]*np.array([.09,.20,.26])+waves[:,None]*bands[:,None]*np.array([.07,.18,.21])
        temp=out[valid];temp[wm]=np.clip(rawwater*(1-.32*atmos[wm,None]),0,1);out[valid]=temp
    if np.linalg.norm(cam[:2]-O)<65:out[valid]*=.72
    out+=np.maximum(emit,0)[:,:,None]*np.array([.07,.15,.09])+np.maximum(-emit,0)[:,:,None]*np.array([.23,.14,.055]);sparks=np.zeros_like(out);counts={}
    for k,color,power,size in [('planted',[.53,.95,.62],.28,.20),('wild',[.4,.85,.79],CFG['wet_glow'],.29),('roof',[.48,.78,.96],CFG['roof_glow'],.7),('lamp',[1.,.72,.34],1.,.23)]:
        pp=(light_arrays[k]-cam)@np.array([right,up,f]).T;pp=pp[pp[:,2]>.3]
        if not len(pp):continue
        xx=w/2+focal*pp[:,0]/pp[:,2];yy=h/2-focal*pp[:,1]/pp[:,2];good=(xx>=0)&(xx<w-1)&(yy>=0)&(yy<h-1);xx,yy,dd=xx[good],yy[good],pp[good,2];ix=xx.astype(int);iy=yy.astype(int);good=D[iy,ix]+np.maximum(.75,dd*.004)>=dd;xx,yy,dd=xx[good],yy[good],dd[good];counts[k]=len(dd)
        for x,y,d0 in zip(xx,yy,dd):
            rr=np.clip(focal*size/d0,.37,5 if k in ('planted','wild') else 10);power0=power*(.22+.78*min(1,d0/125)) if k in ('planted','wild') else power;a=max(0,int(x-rr-1));b=min(w,int(x+rr+2));c=max(0,int(y-rr-1));e=min(h,int(y+rr+2));yy0,xx0=np.ogrid[c:e,a:b];g=np.exp(-((xx0-x)**2+(yy0-y)**2)/(2*rr**2))*power0*np.exp(-d0/4000);sparks[c:e,a:b]=np.maximum(sparks[c:e,a:b],g[:,:,None]*np.array(color))
    halo=gaussian_filter(sparks,(3.2,3.2,0))*.95+gaussian_filter(sparks,(10.,10.,0))*.75
    print('visible emitters',counts);return (np.power(np.clip(out+sparks+halo,0,1),.83)*255).astype(np.uint8)

def clip_near(poly,near=.15):
    q=[]
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        if a[2]>=near:q.append(a)
        if (a[2]>=near)!=(b[2]>=near):q.append(a+(b-a)*((near-a[2])/(b[2]-a[2])))
    return q
@njit(cache=True)
def render_buffer(tris,colors,w,h,fog_dist):
    pix=np.zeros((h,w,3),np.uint8);depth=np.full((h,w),-1e30);emit=np.zeros((h,w),np.float32);watermask=np.zeros((h,w),np.uint8)
    fog=np.array([47.,70.,77.]);bg=np.array([12.,20.,22.]);
    for y in range(h):
        for x in range(w):pix[y,x]=bg
    for i in range(len(tris)):
        a,b,c=tris[i];xmin=max(0,int(np.floor(min(a[0],b[0],c[0]))));xmax=min(w-1,int(np.ceil(max(a[0],b[0],c[0]))));ymin=max(0,int(np.floor(min(a[1],b[1],c[1]))));ymax=min(h-1,int(np.ceil(max(a[1],b[1],c[1]))))
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-10:continue
        for y in range(ymin,ymax+1):
            for x in range(xmin,xmax+1):
                u=((b[1]-c[1])*(x+.5-c[0])+(c[0]-b[0])*(y+.5-c[1]))/den;v=((c[1]-a[1])*(x+.5-c[0])+(a[0]-c[0])*(y+.5-c[1]))/den;k=1-u-v
                if min(u,v,k)<-1e-6:continue
                z=u*a[2]+v*b[2]+k*c[2]
                if z>depth[y,x]:
                    depth[y,x]=z;d=1/z;t=1-np.exp(-d/fog_dist);emit[y,x]=colors[i,3]*(1-t) if colors.shape[1]>3 else 0.;watermask[y,x]=int(colors[i,4]) if colors.shape[1]>4 else 0
                    for j in range(3):pix[y,x,j]=min(255,max(0,colors[i,j]*(1-t)+fog[j]*t))
    return pix,depth,emit,watermask

def perspective(name,xy0,target,fov=79,pitch=0):
    z=float(interp(*xy0[:2])) if len(xy0)==2 else float(xy0[2])-CFG['eye_height'];cam=np.array([*xy0[:2],z+CFG['eye_height']]);f=np.array([target[0]-cam[0],target[1]-cam[1],0.]);f/=np.linalg.norm(f);f=np.r_[f[:2]*np.cos(np.deg2rad(pitch)),np.sin(np.deg2rad(pitch))];right=np.cross(f,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,f)
    cp=(V-cam)@np.array([right,up,f]).T;w,h=int(CFG['render_width']),int(CFG['render_height']);focal=w/(2*np.tan(np.deg2rad(fov/2)));tris=[];colors=[]
    pall=cp[F];validfaces=np.flatnonzero(pall[:,:,2].max(axis=1)>.15)
    for i in validfaces:
        ff=F[i];pp=pall[i]
        if pp[:,2].max()<.15:continue
        poly=pp if pp[:,2].min()>=.15 else clip_near(pp)
        if len(poly)<3:continue
        poly=np.asarray(poly);q=np.column_stack([w/2+focal*poly[:,0]/poly[:,2],h/2-focal*poly[:,1]/poly[:,2],1/poly[:,2]])
        if q[:,0].max()<0 or q[:,0].min()>w or q[:,1].max()<0 or q[:,1].min()>h:continue
        for k in range(1,len(q)-1):tris.append(q[[0,k,k+1]]);colors.append(np.r_[rgb[i]*255,1 if M[i]=='moss_planted' else .40 if M[i]=='moss_wild' else -2.7 if M[i]=='beacon' else 0,2 if M[i]=='sky' else 1 if M[i]=='water' else 0])
    im,depth,emit,watermask=render_buffer(np.asarray(tris),np.asarray(colors),w,h,CFG['fog_distance']);im=light_image(im,depth,emit,watermask,cam,right,up,f,focal);Image.fromarray(im).save(OUT/f'ruosuen_previs12_{name}.png');print('water pixels',name,int(watermask.sum()),flush=True);print(name,'camera',cam,'pitch',pitch,'fov',fov,'triangles',len(tris),'background',np.mean(depth<0))
    return dict(name=name,position=cam.tolist(),look_xy=list(target),pitch_deg=pitch,hfov_deg=fov)
shots=[]
choices={'yard':([2244,1985],[2300,1955],87,1),'r7':([2390,1980],[2920,1950],82,4),'old_track':([875,1960],[1230,1940],84,1),'return':([1660,1978],[2210,2000],76,12),'gate':([2242,1997],[3300,2020],88,9),'home':([2059,1850,305],[2400,2080],83,-14),'port':([2410,1850,146.65],[2210,2000],90,8),'return_night':([1660,1978],[2210,2000],76,12),'r65_return':(list(slope_pt(450,31)),[2210,2000],80,10),'roof':([2210,1970],[2160,2010],100,67),'rift_long':([2160,1940],[2200,2700],104,64)}
print('direct-light GATE floor',direct_light([[2210,2000,.1]]).tolist(),flush=True)
for name in args.shots.split(','):
    if not name:continue
    DAY=not name.endswith('night');pos,tgt,fov,pitch=choices[name];shots.append(perspective(name,pos,tgt,fov,pitch))
with open(OUT/'ruosuen_previs12.obj','w') as fp:
    fp.write('# Local metres, preliminary visual model; tunnel cutoff is not geographic endpoint.\n')
    for x,y,z in V:fp.write(f'v {x:.5f} {y:.5f} {z:.5f}\n')
    for m in np.unique(M):
        if m=="sky":continue
        fp.write(f'g {m}\n')
        for i,j,k in F[M==m]:fp.write(f'f {i+1} {j+1} {k+1}\n')
(OUT/'ruosuen_previs12_lights.json').write_text(json.dumps({k:np.round(v,3).tolist() for k,v in light_arrays.items()},separators=(',',':'))+'\n')
(OUT/'ruosuen_previs12_parameters.json').write_text(json.dumps(CFG,indent=2)+'\n')
(OUT/'ruosuen_previs12_cameras.json').write_text(json.dumps(shots,indent=2)+'\n')
print('Total vertices/faces',len(V),len(F),flush=True)
# Cross-section of the aperture; architecture projected from y=1850.
fig,ax=plt.subplots(figsize=(10,7),facecolor=BG);ax.set_facecolor('#dce5e8')
from matplotlib.patches import Polygon as Patch
left=BOUNDS[:,0];right=BOUNDS[:,1];z=LEVELS
ax.add_patch(Patch([[1300,390],*[[a,b] for a,b in zip(left,z)],[1300,650]],color='#a69b83'));ax.add_patch(Patch([[3100,390],*[[a,b] for a,b in zip(right,z)],[3100,650]],color='#a69b83'))
ax.axhspan(-80,390,color='#293a40',zorder=0);ax.fill_between([1300,3100],[-12,8],-80,color='#9a8b72');
lo=max(left-z*SUN[0]);hi=min(right-z*SUN[0]);ax.add_patch(Patch([[lo,0],[hi,0],[hi+650*SUN[0],650],[lo+650*SUN[0],650]],color='#f7e6a5',alpha=.4))
ax.plot([2050,2050],[0,650],color='#b2a78e',lw=5,ls='--');ax.plot([2050,2510],[145,145],color='#d3bb90',lw=5,ls='--');ax.scatter([2210],[0],color='#fbe5b0',s=60);ax.text(2220,12,'GATE',color='white');ax.text(2090,275,'HOME (projected)',color='white');ax.text(2410,158,'PORT (projected)',color='white');ax.text(2190,585,'RIFT',color='#3f494a');ax.set_xlim(1700,2700);ax.set_ylim(-45,680);ax.set_aspect('equal');ax.set_xlabel('AREA 1 local x (m)');ax.set_ylabel('Height above GATE (m)');ax.set_title('FIRSTLIGHT CAVERN / RIFT CROSS-SECTION — PREVIS 12',loc='left',fontsize=12);ax.grid(alpha=.16);fig.tight_layout();fig.savefig(OUT/'ruosuen_previs12_section.png',dpi=150);plt.close(fig)
print('2D beam floor interval',lo,hi,flush=True)
