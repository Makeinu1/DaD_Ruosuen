"""Area 1 cartographic study from the previs12 OBJ. Requires numpy, matplotlib, scipy, shapely.
All top-down projected geometry is local and provisional; no DM-only destination data.
Usage: python ruosuen_area1_map_draft.py (with previs12.py and OBJ in same folder).
"""
from pathlib import Path
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.collections import PolyCollection, LineCollection
from matplotlib.patches import Polygon as Patch, Circle, Rectangle, FancyBboxPatch
from matplotlib.lines import Line2D
from matplotlib.colors import to_rgb
from matplotlib.tri import Triangulation, LinearTriInterpolator
from scipy.ndimage import gaussian_filter
from shapely.geometry import Polygon, LineString, Point
from shapely.affinity import translate
import sys,json
D=Path(__file__).resolve().parent
src=D/'ruosuen_previs12.py'; ns={'__file__':str(src)}; old=sys.argv;sys.argv=[str(src)];exec(compile(src.read_text().split('ctrl={}')[0],str(src),'exec'),ns);sys.argv=old
P,R,T,outline,roads,trails,rail_specs=[ns[k] for k in ['P','R','T','outline','roads','trails','rail_specs']]
plt.rcParams.update({'font.family':'Noto Sans CJK JP','svg.fonttype':'path','pdf.fonttype':42,'axes.unicode_minus':False,'font.size':10})
PAPER='#f9f5e9'; INK='#302e28'; MUTED='#6c6357'; MAIN='#884229'; LOCAL='#4b5148'; WATER='#467983'; PRO='#766478'; ROCK='#796047'; HALO='#f9f5e9'
verts=[];groups=defaultdict(list);name=''
with open(D/'ruosuen_previs12.obj') as f:
    for line in f:
        if line.startswith('v '):verts.append([float(x) for x in line.split()[1:]])
        elif line.startswith('g '):name=line.split()[1]
        elif line.startswith('f '):groups[name].append([int(x.split('/')[0])-1 for x in line.split()[1:]])
V=np.array(verts); G={k:np.array(v) for k,v in groups.items()}; outer=Polygon(outline)
fig=plt.figure(figsize=(420/25.4,297/25.4),facecolor=PAPER); ax=fig.add_axes([.018,.082,.964,.839]);ax.set_aspect('equal');ax.axis('off');ax.set_xlim(-230,5220);ax.set_ylim(-85,3440)
# Terrain base and actual mesh-derived floor shading. Continuous tone suppresses triangulation noise.
ax.add_patch(Patch(outline,fc='#f3ecdc',ec='none',zorder=1));
# Rasterize original floor faces directly; OBJ rounding can make a generic triangulation finder reject thin faces.
x=np.linspace(-20,4960,1246);y=np.linspace(50,3280,809);X,Y=np.meshgrid(x,y);zr=np.full(X.shape,np.nan)
for tri3 in V[G['floor']]:
    a,b,c=tri3;u=b-a;v=c-a;det=u[0]*v[1]-u[1]*v[0]
    if abs(det)<1e-10:continue
    ix=np.searchsorted(x,[tri3[:,0].min(),tri3[:,0].max()],side='left');iy=np.searchsorted(y,[tri3[:,1].min(),tri3[:,1].max()],side='left');ix[1]=min(len(x),ix[1]+1);iy[1]=min(len(y),iy[1]+1)
    if ix[0]>=ix[1] or iy[0]>=iy[1]:continue
    sl=np.s_[iy[0]:iy[1],ix[0]:ix[1]];xx=X[sl]-a[0];yy=Y[sl]-a[1];p=(xx*v[1]-yy*v[0])/det;q=(u[0]*yy-u[1]*xx)/det;ok=(p>=-1e-6)&(q>=-1e-6)&(p+q<=1+1e-6);zr[sl][ok]=a[2]+p[ok]*u[2]+q[ok]*v[2]
valid=np.isfinite(zr);Z=np.ma.masked_invalid(zr);raw=np.ma.filled(Z,0.);s=gaussian_filter(raw,4)/np.maximum(gaussian_filter(valid.astype(float),4),1e-7);gy,gx=np.gradient(s,y[1]-y[0],x[1]-x[0]);normal=np.stack([-gx*3.0,-gy*3.0,np.ones_like(gx)],axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True);light=np.array([-.55,.52,.65]);light/=np.linalg.norm(light);illum=normal@light
# Ink on pale paper: restrict tonal relief to substantial slopes, not artificial spot elevation halos.
slope=np.hypot(gx,gy);strength=np.clip((slope-.045)/.42,0,1);shade=(illum-.85)*.16*strength;base=np.array(to_rgb('#f3ecdc'));rgb=np.clip(base[None,None,:]+shade[:,:,None],0,1);im=np.dstack((rgb,valid.astype(float)));ax.imshow(im,extent=[x[0],x[-1],y[0],y[-1]],origin='lower',zorder=2,interpolation='bilinear')
# Actual wall apron / internal rock surfaces: plan projection, ordered by altitude. No roof projected on floor.
def rock_group(name,col,z,exag=1):
    p=V[G[name]];n=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-9);n*=np.where(n[:,2]<0,-1,1)[:,None];val=np.clip(n@light,-.5,1);b=np.array(to_rgb(col));rgb=np.clip(b[None,:]+(val[:,None]-.5)*.20*exag,0,1);order=np.argsort(p[:,:,2].mean(1));ax.add_collection(PolyCollection(p[order,:,:2],facecolors=rgb[order],edgecolors=rgb[order],linewidths=.12,zorder=z))
# Engraved cave plan: actual cave rim, and outboard ink strokes rather than a bevel.
from shapely.ops import unary_union
rng=np.random.default_rng(82)
roadguard=unary_union([LineString(q[:,:2]).buffer(45) for r,a,b,q in roads]+[LineString(np.array([P[n][:2],*ps])).buffer(40) for n,ps,name in trails])
ring=LineString(np.vstack([outline,outline[0]]))
outer_ink=outer.buffer(24,join_style=1).difference(outer)
for p in getattr(outer_ink,'geoms',[outer_ink]):
    if p.geom_type=='Polygon':
        # exact boundary retained; pale wash outside the cave wall
        from matplotlib.path import Path as MPath
        from matplotlib.patches import PathPatch
        vs=[];cs=[]
        for r in [p.exterior,*p.interiors]:
            q=np.asarray(r.coords);vs.extend(q);cs.extend([MPath.MOVETO]+[MPath.LINETO]*(len(q)-2)+[MPath.CLOSEPOLY])
        ax.add_patch(PathPatch(MPath(vs,cs),fc='#e4d8bf',ec='none',zorder=1.1))
# Three staggered lengths create a cut-rock convention without changing the surveyed outline.
edge=[];edge_width=[]
for d in np.arange(8,ring.length,15):
    p=np.asarray(ring.interpolate(d).coords[0]);t=np.asarray(ring.interpolate(min(d+7,ring.length)).coords[0])-np.asarray(ring.interpolate(max(d-7,0)).coords[0]);t/=np.linalg.norm(t);n=np.array([-t[1],t[0]])
    if outer.contains(Point(p+n*12)):n=-n
    L=rng.uniform(17,48)*(1.0+.35*np.sin(d/94)+.21*np.cos(d/38));q=p+n*L+t*rng.uniform(-10,10)
    if roadguard.intersects(LineString([p,q])):continue
    edge.append([p+n*2,q]);edge_width.append(rng.uniform(.38,.85))
ax.add_collection(LineCollection(edge,colors='#9b876a',linewidths=edge_width,alpha=.8,zorder=4))
ax.plot(*np.vstack([outline,outline[0]]).T,c='#65513b',lw=1.5,zorder=5,solid_joinstyle='round')
# Actual surface geometry is retained. For massifs use slope-directed strokes inside the surveyed footprint.
# Rasterize each relief group to a regular grid using only its projected triangles.
def engraved_relief(group,key,base,ink):
    tris=V[G[group]];q=np.asarray(T[key]);poly=Polygon(q);x0,y0,x1,y1=poly.bounds;xx=np.arange(x0-4,x1+8,4);yy=np.arange(y0-4,y1+8,4);XX,YY=np.meshgrid(xx,yy);zz=np.full(XX.shape,np.nan)
    for tri in tris:
        a,b,c=tri;u=b-a;v=c-a;det=u[0]*v[1]-u[1]*v[0]
        if abs(det)<1e-8:continue
        i0,i1=np.searchsorted(xx,[tri[:,0].min(),tri[:,0].max()]);j0,j1=np.searchsorted(yy,[tri[:,1].min(),tri[:,1].max()]);i1=min(i1+1,len(xx));j1=min(j1+1,len(yy))
        if i0>=i1 or j0>=j1:continue
        sl=np.s_[j0:j1,i0:i1];X0=XX[sl]-a[0];Y0=YY[sl]-a[1];u1=(X0*v[1]-Y0*v[0])/det;v1=(u[0]*Y0-u[1]*X0)/det;ok=(u1>=-1e-5)&(v1>=-1e-5)&(u1+v1<=1+1e-5);z=a[2]+u1*u[2]+v1*v[2];zz[sl][ok]=np.fmax(zz[sl][ok],z[ok])
    good=np.isfinite(zz);w=gaussian_filter(good.astype(float),2);smooth=gaussian_filter(np.nan_to_num(zz),2)/np.maximum(w,1e-8);dy,dx=np.gradient(smooth,4,4);mag=np.hypot(dx,dy)
    ax.add_patch(Patch(q,fc=base,ec=ink,lw=1.0,zorder=6,joinstyle='round'))
    # continuous wash clipped to measured footprint; no projected roof or invented height lines
    n=np.stack([-dx*2.2,-dy*2.2,np.ones_like(dx)],axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True);val=n@light;col=np.clip(np.array(to_rgb(base))[None,None,:]+(val[:,:,None]-.73)*.22,0,1);im=np.dstack([col,good.astype(float)]);artist=ax.imshow(im,extent=[xx[0],xx[-1],yy[0],yy[-1]],origin='lower',zorder=6.1,interpolation='bilinear');artist.set_clip_path(Patch(q,transform=ax.transData))
    seg=[];width=[]
    for j in range(3,len(yy)-3,4):
        for i in range(3,len(xx)-3,4):
            if not good[j,i] or mag[j,i]<.075:continue
            p=np.array([xx[i],yy[j]])+rng.uniform(-5,5,2);v=np.array([-dx[j,i],-dy[j,i]])/mag[j,i];L=np.clip(10+mag[j,i]*45,12,38)*rng.uniform(.75,1.25);end=p+v*L
            if not poly.buffer(-3).covers(LineString([p,end])):continue
            if rng.random()>np.clip(.35+mag[j,i],.4,.95):continue
            seg.append([p,end]);width.append(np.clip(.35+mag[j,i]*.6,.35,.9)*rng.uniform(.85,1.2))
    ax.add_collection(LineCollection(seg,colors=ink,linewidths=width,alpha=.72,zorder=7))
    # A few continuous ridges picked from the mesh, not full-area contour intervals.
    low=np.nanmin(zz);high=np.nanmax(zz);levels=np.linspace(low+(high-low)*.27,high-(high-low)*.15,3)
    if high-low>20:
        ax.contour(xx,yy,np.ma.masked_where(~good,smooth),levels=levels,colors=[ink],linewidths=.48,alpha=.38,zorder=6.8)
    ax.plot(*np.vstack([q,q[0]]).T,color=ink,lw=1.25,zorder=7.2,linestyle=(0,(3,2)) if key in ('portal','terminal_rock') else '-',solid_joinstyle='round')
engraved_relief('massif','massif','#d8c6a1','#836444')
engraved_relief('terminal_rock','terminal_rock','#e3d4b7',PRO)
engraved_relief('portal_rock','portal','#e1d0b3',PRO)
# Pillar = solid rock cut: cross-hatching inside exact footprint, not a miniature mountain.
q=np.asarray(T['pillar']);ax.add_patch(Patch(q,fc='#ded0b3',ec='#69573f',lw=1.25,hatch='////',zorder=7.2));
# Shaft = negative relief: a dark unmeasured interior and inward rim cuts; no depicted bottom.
q=np.asarray(T['shaft']);c=q.mean(0);inner=c+(q-c)*.78;ax.add_patch(Patch(q,fc='#a09276',ec='#554d3d',lw=1.15,zorder=6));ax.add_patch(Patch(inner,fc='#34403d',ec='#6e6958',lw=.9,zorder=6.5));L=LineString(np.vstack([q,q[0]]));segs=[]
for d in np.arange(7,L.length,13):
    p=np.array(L.interpolate(d).coords[0]);v=(c-p);v/=np.linalg.norm(v);segs.append([p+v*3,p+v*rng.uniform(25,42)])
ax.add_collection(LineCollection(segs,colors='#554d3d',linewidths=.65,alpha=.85,zorder=7))
# Local floor hachures (derived from the actual gradient); keep the majority of floor paper-clear.
marks=[];widths=[]
for iy in range(8,len(y)-8,7):
    for ix in range(8,len(x)-8,7):
        if not valid[iy,ix]:continue
        v=np.array([gx[iy,ix],gy[iy,ix]]);sl=np.linalg.norm(v)
        if sl<.12 or sl>.95:continue
        pt=np.array([x[ix],y[iy]])+rng.uniform(-7,7,2);v/=sl;end=pt-v*np.clip(sl*70,12,32)*rng.uniform(.7,1.2);seg=LineString([pt,end])
        if not outer.buffer(-75).covers(seg) or roadguard.intersects(seg) or rng.random()>min(.9,sl*2.4):continue
        marks.append([pt,end]);widths.append(np.clip(.34+sl*.4,.34,.8))
ax.add_collection(LineCollection(marks,colors='#9a805f',linewidths=widths,alpha=.62,zorder=3.8))
# Cliffs with hachures on low side, not continuous false contours.
for key in ['cliff_upper','cliff_lower']:
    q=np.array(T[key]);ax.plot(*q.T,c='#8c7963',lw=1.25,zorder=8,solid_capstyle='round');L=LineString(q); seg=[]
    for d in np.arange(12,L.length-6,27):
        p=np.array(L.interpolate(d).coords[0]);u=np.array(L.interpolate(d+5).coords[0])-np.array(L.interpolate(max(0,d-5)).coords[0]);u/=np.linalg.norm(u);n=np.array([u[1],-u[0]]);length=rng.uniform(22,40);seg.append([p,p+n*length]);
    ax.add_collection(LineCollection(seg,colors='#907b63',linewidths=.65,zorder=8))
# Water and wet ledge, map-width exaggerated for legibility, not width measurements.
river=np.array(T['river']);ax.plot(*river.T,c='#d9e8df',lw=3.3,zorder=8);ax.plot(*river.T,c=WATER,lw=1.45,zorder=9,solid_capstyle='round');ax.add_patch(Patch(T['pool'],fc='#b2cdd0',ec=WATER,lw=1.1,zorder=9));q=np.asarray(T['pool']);c=q.mean(0);q=c+(q-c)*.84;ax.plot(*np.vstack([q,q[0]]).T,c=WATER,lw=.55,alpha=.65,zorder=9.1)
growth=Polygon(T['growth']);pts=[]
for _ in range(380):
    a=rng.uniform(*[growth.bounds[i] for i in (0,2)]);b=rng.uniform(*[growth.bounds[i] for i in (1,3)]);
    if growth.contains(Point(a,b)):pts.append((a,b))
ax.add_patch(Patch(T['growth'],fc='#c5ccad',ec='none',alpha=.55,zorder=7));ax.scatter(*np.array(pts).T,s=2.1,c='#728966',alpha=.6,zorder=8,linewidths=0)
# Roof fissure projected as a dashed overhead line: no floor barrier. Candidate only.
shape=np.array([[1940,.22],[1905,.58],[1960,.88],[2100,1],[2430,.87],[2640,.64],[2780,.31],[2640,.12],[2390,.035],[2100,0]],float);rift=np.c_[2110+210*shape[:,1],shape[:,0]]
# Ceiling fissure omitted from walking sheet; structural geometry retained in model.
# Roads from the same plan as the 3D model. Actual road width not implied by stroke.
def line(q,color,lw,z=14,**kw):ax.plot(*np.array(q)[:,:2].T,c=color,lw=lw,zorder=z,solid_capstyle='round',solid_joinstyle='round',**kw)
for r,a,b,q in roads:
    if r==0:line(q,LOCAL,1.15,13,linestyle=(0,(2,2)));continue
    w=3.0 if r in [3,7,12,65] else 1.45;line(q,HALO,w+1.7,12);line(q,MAIN if r in [3,7,12,65] else LOCAL,w,13)
    if r in [3,7,12,65]:line(q,'#dfb78d',.95,13.2)
# Rails are schematic offset in cartographic line weight, using exact candidate centerline. Not a public passenger service.
for name,q in rail_specs:
    q=q.copy();q[:,1]-=22  # cartographic displacement only, to separate the track from the road in print
    line(q,HALO,2.1,14);line(q,PRO,1.15,15,linestyle=(0,(4,1.6)) if name=='active' else (0,(1.4,3.0)))
    if name=='active':
        L=LineString(q[:,:2]); seg=[]
        for d in np.arange(0,L.length,26):
            p=np.asarray(L.interpolate(d).coords[0]);u=np.asarray(L.interpolate(min(L.length,d+2)).coords[0])-np.asarray(L.interpolate(max(0,d-2)).coords[0]);u/=max(np.linalg.norm(u),1e-10);n=np.array([-u[1],u[0]]);seg.append([p-n*9,p+n*9]);
        ax.add_collection(LineCollection(seg,colors=PRO,linewidths=.65,zorder=15))
for n,ps,name in trails:
    q=np.array([P[n][:2],*ps]);line(q,HALO,2.0,12);line(q,LOCAL,1.25,13,linestyle=(0,(2.1,2.0)));u=q[-1]-q[-2];u=u/np.linalg.norm(u);side=np.array([-u[1],u[0]])*31;line([q[-1]-side,q[-1]+side],LOCAL,2,16)
# Labels. Text halos are gentle, leaving the underlying terrain visible.
labels=[]
def txt(x,y,s,size=10,col=INK,weight='normal',ha='center',va='center',rot=0,halo=2.2,z=25,**kw):
    size=size*1.07 if any(ord(ch)>127 for ch in s) else size;family='Noto Serif CJK JP' if any(ord(ch)>127 for ch in s) and not s.startswith(('AREA','PORT','HOME')) else 'Noto Sans CJK JP';t=ax.text(x,y,s,fontfamily=family,ha=ha,va=va,fontsize=size,color=col,fontweight=weight,rotation=rot,zorder=z,path_effects=[pe.withStroke(linewidth=halo,foreground=HALO)] if halo else [],**kw);labels.append(t);return t
def tag(r,x,y):
    color=MAIN if r in [3,7,12,65] else LOCAL;return txt(x,y,f'R{r}',10.5 if r in [3,7,12,65] else 9.5,color,'bold',halo=0,bbox=dict(boxstyle='round,pad=.18,rounding_size=.22',fc=PAPER,ec=color,lw=.75))
def leader(p,xy,label,size=10,ha='center',col=INK):
    ax.plot([p[0],xy[0]],[p[1],xy[1]],c=col,lw=.6,alpha=.65,zorder=21);return txt(*xy,label,size,col,ha=ha,va='bottom')
def symbol(n,m,col,sz=45):
    x,y=P[n][:2];ax.scatter([x],[y],s=sz,marker=m,facecolor=col,edgecolor=HALO,lw=1,zorder=21)
# GATE anchors center as a cartographic symbol, not illumination.
xg,yg=P['GATE'][:2];ax.add_patch(Circle((xg,yg),70,fc=PAPER,ec=MAIN,lw=1.1,zorder=18));ax.add_patch(Circle((xg,yg),48,fc=INK,ec=PAPER,lw=2,zorder=22));ax.add_patch(Circle((xg,yg),18,fc=PAPER,ec='none',zorder=23));txt(2200,2095,'GATE',18,INK,'bold',halo=3.4)
# Facility glyphs. No node numbers.
for n,m,col,sz in [('N105','D','#445a54',61),('N106','D','#445a54',61),('N117','^',LOCAL,52),('N113','p','#77654c',50),('N114','o',WATER,48),('N119','^',LOCAL,45),('N122','s','#77654c',44),('N124','D','#857465',48),('N126','X','#7e6053',54),('N127','p','#77654c',50)]:symbol(n,m,col,sz)
bridge=np.array([1744.347826,653.369565]);ax.scatter(*bridge,s=48,marker='s',facecolor=PAPER,edgecolor=MAIN,linewidth=1.2,zorder=21)
# route shields arranged near their roads, repeated on long routes
for r,x,y in [(3,1020,2040),(7,3210,2045),(12,2060,2700),(12,3395,2875),(65,1745,1725),(65,2920,710),(65,4160,350),(112,3380,2330),(165,2830,1550),(201,720,1225),(201,1765,1405),(214,1640,2800),(215,2660,2520),(231,3370,1255),(240,4210,1630),(245,1515,910)]:tag(r,x,y)
for x,y,s,sz,col,ha,w in [(1740,2445,'ヴァルド岩山',13.0,INK,'center','bold'),(2550,2275,'ネルガ竪穴',10.0,'#f7f1e3','center','bold'),(3965,2690,'オルド大柱',13.0,INK,'center','bold'),(3000,1720,'レムナ崖',11,ROCK,'center','normal'),(2885,1355,'レムナ谷',11,ROCK,'center','normal'),(1050,1850,'アルデン大街道',11,MAIN,'center','bold'),(3220,1890,'ヴェイラン大街道',11,MAIN,'center','bold'),(3010,2745,'ヴァルド鉱山',11.5,INK,'center','bold'),(3730,1905,'ヴェイラン鉱山',11.5,INK,'center','bold'),(1750,3030,'測量所',10,INK,'center','normal'),(440,1540,'リューネ小屋',10,INK,'center','normal'),(980,1145,'リューネ水場',10,INK,'center','normal'),(3035,2250,'ネルガ観測点',9.4,INK,'left','normal'),(3510,1040,'荷捌き場',9,INK,'left','normal'),(4550,1950,'オルド採石場跡',9.5,INK,'center','normal'),(2050,435,'レムナ廃鉱山',10.2,INK,'center','normal'),(3850,520,'レムナ小屋',10,INK,'center','normal'),(1720,565,'リューネ橋',9,INK,'center','normal'),(1325,505,'リューネ沢',11,WATER,'center','normal'),(2395,175,'リューネ池',11,WATER,'center','normal'),(3820,840,'エルナ岩棚',11.5,LOCAL,'center','bold')]:txt(x,y,s,sz,col,w,ha,halo=0 if s=='ネルガ竪穴' else 2.3)
# Openings use named anchors inherited from old map studies; no destinations beyond mouths.
# Approximate registered positions of HOME and PORT.
for xy,s,anchor in [((1890,1840),'HOME',(2050,1850)),((2520,1810),'PORT（上層）',(2450,1850))]:
    ax.plot([anchor[0],xy[0]],[anchor[1],xy[1]],color=PRO,lw=.8,ls=(0,(3,2)),zorder=20);ax.scatter(*anchor,s=13,facecolor=PAPER,edgecolor=PRO,lw=.8,zorder=21);txt(*xy,s,9.5,PRO,'medium',halo=2.4)
# Rail annotation separated from roads; old track is distinguished by line style.
txt(3380,1785,'鉱山軌道',9.1,PRO,halo=2.4);txt(980,1760,'旧軌道',9.1,PRO,halo=2.4)
# AREA exits: arrows begin at confirmed nodes; labels lie outside the cavern.
for n,end,lab,xy,ha in [('N112',(3690,3210),'AREA 2  ピラーヴォルト',(3740,3340),'center'),('N111',(5100,2290),'AREA 11\nアッシュヴォルト',(5100,2420),'right'),('N110',(4620,400),'AREA 6  シルヴァーウェル',(4710,285),'center')]:
    p=P[n][:2];ax.annotate('',xy=end,xytext=p,arrowprops=dict(arrowstyle='-|>',color=MAIN,lw=2,shrinkA=0,shrinkB=0),zorder=21);txt(*xy,lab,11,MAIN,'bold',ha,halo=2.8)
# Small set of spot heights from registered route elevations only, rounded as in earlier map.
for n,xy in [('N105',(3160,2640)),('N106',(3710,2070)),('N117',(1890,2950)),('N108',(2810,955)),('N109',(3180,420)),('N126',(2085,595))]:
    z=round(P[n][2]/5)*5;txt(*xy,f'{z:+d}',8.5,MUTED,ha='left',halo=1.8)
# Scale, annotation area in naturally empty lower-left margin, no compass.
x0=0;y0=155
for i in range(4):ax.add_patch(Rectangle((x0+i*125,y0),125,18,fc=INK if i%2==0 else PAPER,ec=INK,lw=.7,zorder=28))
for x,v in [(0,'0'),(250,'250'),(500,'500 m')]:txt(x0+x,y0+52,v,8.5,MUTED,halo=0)
# Header/footer: minimal real-map layout.
fig.text(.036,.961,'AREA 1',size=23,weight='bold',color=MAIN,va='center');fig.text(.175,.961,'ファーストライト大空洞',fontfamily='Noto Serif CJK JP',size=25,weight='bold',color=INK,va='center');fig.text(.038,.924,'FIRSTLIGHT CAVERN  /  探索携行図',size=10.5,color=MUTED,va='center');fig.text(.965,.960,'王立地図院',fontfamily='Noto Serif CJK JP',size=18,weight='bold',color=INK,ha='right',va='center');fig.text(.965,.926,'探索携行図  ·  改訂 03',size=10.5,color=PRO,ha='right',va='center');fig.add_artist(Line2D([.035,.965],[.908,.908],transform=fig.transFigure,c='#8b7657',lw=1.25));fig.add_artist(Line2D([.035,.965],[.905,.905],transform=fig.transFigure,c='#b5a58b',lw=.45))
fig.add_artist(Line2D([.035,.965],[.078,.078],transform=fig.transFigure,c='#bfb5a0',lw=.8))
# legend all required primary semantics, no dense swatches.
handles=[Line2D([0],[0],c=MAIN,lw=2.7,label='主要街道'),Line2D([0],[0],c=LOCAL,lw=1.6,label='地域街道'),Line2D([0],[0],c=LOCAL,lw=1.4,ls='--',label='確認済み横道'),Line2D([0],[0],c=PRO,lw=1.3,ls='--',label='産業用軌道'),Line2D([0],[0],c=WATER,lw=1.5,label='水系'),Line2D([0],[0],marker='D',c=LOCAL,lw=0,label='鉱山・採石場'),Line2D([0],[0],marker='p',c='#77654c',lw=0,label='小屋'),Line2D([0],[0],marker='^',c=LOCAL,lw=0,label='観測・測量'),Line2D([0],[0],marker='s',c='#77654c',lw=0,label='荷捌き場'),Line2D([0],[0],marker='X',c='#7e6053',lw=0,label='廃鉱山'),Line2D([0],[0],marker='s',markerfacecolor=PAPER,markeredgecolor=MAIN,c=MAIN,lw=0,label='橋'),Line2D([0],[0],marker='|',markersize=10,c=LOCAL,lw=0,label='開口端'),Line2D([0],[0],c=ROCK,lw=1.3,marker=3,markersize=4,label='崖'),Patch([[0,0],[1,0],[1,1],[0,1]],fc='#ded0b3',ec=ROCK,hatch='////',label='岩柱')]
fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.028),ncol=7,frameon=False,fontsize=10.1,labelcolor=INK,handlelength=2.0,columnspacing=1.5,handletextpad=.55)
fig.text(.035,.012,'標高：GATE基準（m）　横道は確認範囲まで　軌道離隔は誇張',size=9.4,color=MUTED);fig.text(.965,.012,'A3横  /  局所平面図  /  概略測量図',ha='right',size=9.4,color=PRO)
# report overlapping labels (actual text extents, not halos/leader lines)
fig.canvas.draw();renderer=fig.canvas.get_renderer(); overlaps=[]
for i,a in enumerate(labels):
    ba=a.get_window_extent(renderer)
    for b in labels[i+1:]:
        bb=b.get_window_extent(renderer)
        if ba.overlaps(bb):overlaps.append([a.get_text(),b.get_text()])
print('LABEL OVERLAPS',overlaps)
for ext in ['png','svg']:
    fig.savefig(D/f'area-1-institute-ja-r03.{ext}',dpi=240,facecolor=PAPER)
plt.close(fig)
import cairosvg
cairosvg.svg2pdf(url=str(D/'area-1-institute-ja-r03.svg'),write_to=str(D/'area-1-institute-ja-r03.pdf'))
report={'source':'previs12 OBJ, route samples and candidate geometry','known_nodes':len(P),'routes':len(R),'observed_trails':len(trails),'registered_terrain_keys':[k for k in T if k not in ('terminal_rock','portal')],'candidate_features':['outline','floor relief','HOME/PORT locations','terminal rock','rail alignments','portal landform'],'label_overlaps':overlaps,'rail_cartographic_offset_m':22,'draft_only':False,'names_provisional':False,'lighting_layer':False,'ceiling_fissure_on_handout':False,'dm_destination_in_map':False,'render_style':'mesh-derived engraved relief, cut rock boundary, serif place names, outlined main road','geometry_changed':False};(D/'area-1-institute-ja-r03-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
