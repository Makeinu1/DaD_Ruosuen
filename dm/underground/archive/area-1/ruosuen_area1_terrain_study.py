import json, math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, FancyArrowPatch
from matplotlib.lines import Line2D
from matplotlib import patheffects
out=Path(__file__).parent
base={'status': 'design draft, no formal registration', 'coordinate_frame': 'local approximate km, not global datum; z relative to GATE', 'points': {'GATE': {'xy_km': [-0.85, 2.0], 'z_m': 0}, 'N101': {'xy_km': [0.55, 2.0], 'z_m': -10}, 'N102': {'xy_km': [1.25, 2.65], 'z_m': 15}, 'N103': {'xy_km': [1.5, 2.0], 'z_m': -20}, 'N104': {'xy_km': [2.05, 1.5], 'z_m': -35}, 'N105': {'xy_km': [3.0, 2.65], 'z_m': 35}, 'N106': {'xy_km': [3.72, 2.0], 'z_m': -5}, 'N107': {'xy_km': [3.95, 1.5], 'z_m': -20}, 'N108': {'xy_km': [2.765, 0.85], 'z_m': -65}, 'N109': {'xy_km': [3.15, 0.5], 'z_m': -80}, 'N110': {'xy_km': [4.45, 0.55], 'z_m': -80}, 'N111': {'xy_km': [4.8, 2.2], 'z_m': 5}, 'N112': {'xy_km': [3.6, 3.05], 'z_m': 45}, 'D_ENTRY': {'xy_km': [3.15, 0.15], 'z_m': -100}}, 'routes': {'3': ['GATE', 'N101', 'N103', 'N106', 'N111'], '12': ['N101', 'N102', 'N105', 'N112'], '65': ['N103', 'N104', 'N108', 'N109', 'N110'], '112': ['N105', 'N106'], '165': ['N104', 'N107', 'N106']}, 'route_geometry_overrides': {'GATE-N101': [[-0.85, 2.0], [-0.5, 2.02], [-0.23, 1.94], [0, 2.0], [0.55, 2.0]], 'N109-N110': [[3.15, 0.5], [3.7, 0.39], [4.45, 0.55]]}, 'cavern_outline': [[0, 2.0], [0.25, 2.65], [0.65, 3.0], [1.35, 3.18], [2.55, 3.2], [3.6, 3.05], [4.3, 2.83], [4.8, 2.2], [4.72, 1.3], [4.45, 0.55], [3.65, 0.13], [3.15, 0.15], [2.0, 0.22], [1.35, 0.38], [0.8, 0.7], [0.27, 1.2]], 'unknown_openings': [[0.65, 3.0], [0.8, 0.7], [4.72, 1.3], [2.0, 0.22]], 'unmaintained_spur': [[3.15, 0.5], [3.12, 0.33], [3.15, 0.15]], 'journey': [{'from': 'GATE', 'to': 'N101', 'horizontal_km': 1.42, 'dz_m': -10}, {'from': 'N101', 'to': 'N103', 'horizontal_km': 0.95, 'dz_m': -10}, {'from': 'N103', 'to': 'N104', 'horizontal_km': 0.743, 'dz_m': -15}, {'from': 'N104', 'to': 'N108', 'horizontal_km': 0.966, 'dz_m': -30}, {'from': 'N108', 'to': 'N109', 'horizontal_km': 0.52, 'dz_m': -15}, {'from': 'N109', 'to': 'D_ENTRY', 'horizontal_km': 0.355, 'dz_m': -20}]}
P={k:tuple(v['xy_km']) for k,v in base['points'].items() if k!='D_ENTRY'}
P['GATE']=(2.21,2.0) # provisional central position on Route 3
z={k:v['z_m'] for k,v in base['points'].items() if k!='D_ENTRY'}
new={113:(.48,1.45,-15),114:(1.05,1.05,-25),115:(1.58,1.22,-28),116:(1.75,2.65,21),117:(1.75,2.95,40),118:(2.35,2.65,28),119:(2.95,2.24,12),120:(2.92,2,-10),121:(3.45,1.5,-26),122:(3.45,1.02,-48),123:(4.35,1.55,-18),124:(4.52,1.85,-12),125:(1.62,.70,-48),126:(2.10,.52,-52),127:(3.85,.422,-80)}
for n,(x,y,h) in new.items():P[f'N{n}']=(x,y);z[f'N{n}']=h
# Preserve physical elevations; rebase the local vertical datum to the new GATE.
z['GATE']=-15
z={k:h+15 for k,h in z.items()}
R={3:['N101','N103','GATE'],7:['GATE','N120','N106','N111'],12:['N101','N102','N116','N118','N105','N112'],65:['N103','N104','N108','N109','N127','N110'],112:['N105','N106'],165:['N104','N121','N107','N106'],201:['N101','N113','N114','N115','N104'],214:['N116','N117'],215:['N118','N119','N120'],231:['N121','N122','N109'],240:['N107','N123','N124'],245:['N115','N125','N126']}
# Subdivision of existing route geometry preserves original alignment.
paths={('N109','N127'):[P['N109'],(3.7,.39),P['N127']],('N127','N110'):[P['N127'],P['N110']]}
outline=base['cavern_outline'];unknown=base['unknown_openings']
trails=[('N108',[(2.44,.81),(2.30,.66)],'unmaintained'),('N108',[(2.73,1.00),(2.65,1.20)],'unmaintained'),('N107',[(4.22,1.26)],'unmaintained'),('N126',[(2.05,.36),(2.0,.22)],'unmaintained'),('N123',[(4.55,1.43),(4.72,1.3)],'unmaintained'),('N102',[(.98,2.77),(.65,3.0)],'unmaintained'),('N114',[(.92,.86),(.8,.7)],'unmaintained'),('N102',[P['N103']],'local')]
# Public branch from N108 is known as a rough path only, no hidden destination.
facilities={'N105':('Upper Mine','mine'), 'N106':('First Mine','mine'),'N113':('Way shelter','shelter'),'N114':('Spring','water'),'N117':('Survey station','survey'),'N119':('Shaft lookout','lookout'),'N122':('Loading yard','cargo'),'N124':('Old quarry','old'),'N126':('Abandoned workings','old'),'N127':('Way shelter','shelter')}
# Verify intersections of numbered paths are only shared endpoints (plan crossings must be explained).
from shapely.geometry import LineString, Point, Polygon as SPoly
assert SPoly(outline).contains(Point(P['GATE']))
segments=[]
for r,ns in R.items():
 for a,b in zip(ns,ns[1:]):
  coords=paths.get((a,b),[P[a],P[b]])
  segments.append((r,a,b,LineString(coords)))
for i,(r,a,b,l) in enumerate(segments):
 for s,c,d,m in segments[i+1:]:
  cross=l.intersection(m)
  if cross.is_empty:continue
  common=set((a,b))&set((c,d))
  assert cross.geom_type=='Point' and any(cross.distance(Point(P[k]))<1e-7 for k in common),(r,a,b,s,c,d,cross.wkt)
assert all(P[k]==tuple(base['points'][k]['xy_km']) and z[k]==base['points'][k]['z_m']+15 for k in base['points'] if k not in ('D_ENTRY','GATE'))
# Validate the original five routes' ordered node sequences remain subsequences.
for r,ns in base['routes'].items():
 ns=[n for n in ns if n!='GATE']
 sequence=R[3]+R[7][1:] if r=='3' else R[int(r)]
 assert [n for n in sequence if n in ns]==ns
assert R[3][-1]==R[7][0]=='GATE' and set(R[3]) & set(R[7])=={'GATE'}
connections={'N112':{'route':12,'area':2,'name':'Pillarvault'},'N111':{'route':7,'area':11,'name':'Ashvault'},'N110':{'route':65,'area':6,'name':'Silverwell'}}
assert len({c['area'] for c in connections.values()})==len(connections)
assert all(R[c['route']][-1]==n for n,c in connections.items())
route_names={3:'Alden Highroad',7:'Veyran Highroad'}
bg='#f4f1e7'; ink='#38554e'; mute='#697b71'; rock='#e1dbc9'; edge='#a49e85'; colors={3:'#9d7e49',7:'#86647f',12:'#9d7e49',65:'#608674',112:'#858d78',165:'#858d78',201:'#858d78',214:'#858d78',215:'#858d78',231:'#858d78',240:'#858d78',245:'#858d78'}
fig,ax=plt.subplots(figsize=(16,10.8),facecolor=bg);fig.subplots_adjust(left=.035,right=.975,bottom=.235,top=.88);ax.set_aspect('equal');ax.set_xlim(-.42,5.55);ax.set_ylim(-.37,3.65);ax.axis('off')
def poly(ps,**kw):ax.add_patch(Polygon(ps,closed=True,**kw))
def line(ps,**kw):ax.plot(*zip(*ps),**kw)
def txt(x,y,s,**kw):ax.text(x,y,s,color=kw.pop('color',ink),**kw)
def tag(x,y,s,c,fs=10):txt(x,y,s,fontsize=fs,fontweight='bold',color='white',ha='center',va='center',zorder=15,bbox=dict(boxstyle='round,pad=.25',fc=c,ec=bg,lw=.8))
fig.text(.04,.955,'ROYAL CARTOGRAPHIC INSTITUTE',fontsize=22,fontweight='bold',color=ink);fig.text(.04,.915,'RUOSUEN  /  AREA 1  /  REGIONAL ROUTE MAP',fontsize=12,color=mute);fig.text(.96,.955,'DRAFT 06 / TERRAIN STUDY',ha='right',fontsize=12,fontweight='bold',color=mute);fig.lines.append(Line2D([.04,.96],[.895,.895],transform=fig.transFigure,color='#b8b5a6',lw=1))
poly(outline,facecolor=rock,edgecolor=edge,lw=1.8,zorder=2)
for tri in [[(.0,2),(.65,3),(1.25,2.65)],[(1.35,3.18),(2.55,3.2),(3,2.65)],[(4.3,2.83),(4.8,2.2),(3.72,2)],[(.8,.7),(1.35,.38),(2.05,1.5)],[(3.15,.15),(3.65,.13),(3.95,1.5)],[(1.35,.38),(2,.22),(2.10,.52)],[(3.60,3.05),(4.3,2.83),(3.0,2.65)]]:poly(tri,facecolor='#c8c2ad',edgecolor='none',alpha=.45,zorder=3)
poly([(2.35,2.34),(2.55,2.42),(2.76,2.29),(2.66,2.15),(2.43,2.16)],facecolor='#a0aaa0',edgecolor='#71857a',lw=1.1,zorder=3);txt(2.55,2.32,'SHAFT',fontsize=8,ha='center',va='center',color='#405e54')
# Terrain overlay proposal: existing coordinates/roads unchanged.
from matplotlib.patches import Patch
import numpy as np
terrain={
 'massif':[(1.37,2.34),(1.55,2.51),(1.95,2.54),(2.17,2.36),(2.06,2.15),(1.72,2.18)],
 'pillar':[(3.66,2.34),(3.91,2.54),(4.13,2.48),(4.18,2.30),(3.93,2.20)],
 'cliff_upper':[(2.38,1.67),(2.50,1.65),(2.61,1.65),(3.15,1.66),(3.48,1.72)],
 'cliff_lower':[(2.37,1.02),(2.52,1.13),(2.66,1.32),(2.87,1.39),(3.11,1.33)],
 'river':[(1.05,1.05),(1.20,.90),(1.44,.62),(1.55,.54),(1.79,.68),(2.15,.65),(2.32,.32),(2.38,.29)],
 'pool':[(2.22,.30),(2.39,.37),(2.58,.30),(2.55,.23),(2.32,.23)],
 'growth':[(3.55,.88),(3.72,1.04),(3.97,.96),(4.04,.77),(3.77,.70)],
}
allroads=[(str(r),a,b,l) for r,a,b,l in segments]+[('local',k,'',LineString([P[k]]+ps)) for k,ps,state in trails]
for name in ('massif','pillar','pool'):
 g=SPoly(terrain[name]);assert SPoly(outline).covers(g)
 assert all(not g.intersects(l) for r,a,b,l in allroads),name
for name in ('cliff_upper','cliff_lower','river'):
 g=LineString(terrain[name]);assert SPoly(outline).covers(g)
 print(name,[(r,a,b,g.intersection(l).wkt) for r,a,b,l in allroads if g.intersects(l)])
# Regional relief, not a solved elevation mesh.
poly(terrain['massif'],facecolor='#c2b39a',edgecolor='#93846f',lw=.9,zorder=3.1)
center=np.mean(terrain['massif'],axis=0)
for factor in (.74,.44):
 ps=[tuple(center+factor*(np.array(p)-center)) for p in terrain['massif']]
 poly(ps,facecolor='none',edgecolor='#9c8b73',lw=.9,zorder=3.2)
poly(terrain['pillar'],facecolor='#908c7b',edgecolor='#726f60',lw=1,zorder=3.2,hatch='///')
poly(terrain['growth'],facecolor='#b2c5a5',edgecolor='#93a78e',lw=.8,zorder=3.1,hatch='..')
poly(terrain['pool'],facecolor='#8bbac4',edgecolor='#588c9d',lw=1,zorder=3.3)
line(terrain['river'],color='#6da6b9',lw=2.8,solid_capstyle='round',zorder=3.4)
# Flow arrow is hydrological, not compass direction.
ax.add_patch(FancyArrowPatch((2.21,.53),(2.29,.36),arrowstyle='-|>',mutation_scale=10,color='#4e8498',lw=1.4,zorder=3.6))
# Cliff hachures point to the locally lower side. Road crossing is a proposed graded passage.
for name in ('cliff_upper','cliff_lower'):
 pts=terrain[name];line(pts,color='#8d7058',lw=1.55,zorder=3.5)
 for a,b in zip(pts,pts[1:]):
  a=np.array(a);b=np.array(b);v=b-a;length=np.linalg.norm(v);normal=np.array([v[1],-v[0]])/length
  for t in np.linspace(.15,.85,max(2,int(length/.065))):
   p=a+t*v;q=p+.043*normal;line([p,q],color='#8d7058',lw=.8,zorder=3.5)
# Candidate crossing symbols, located from actual intersections.
bridge=LineString(terrain['river']).intersection(next(l for r,a,b,l in allroads if r=='245' and a=='N125' and b=='N126'))
ramp=LineString(terrain['cliff_lower']).intersection(next(l for r,a,b,l in allroads if r=='65' and a=='N104' and b=='N108'))

for r,a,b,l in segments:line(list(l.coords),color=colors[r],lw=4.4 if r<100 else 2.5,solid_capstyle='round',zorder=4)
for k,ps,state in trails:line([P[k]]+ps,color='#8b9487',lw=1.5,ls=(0,(3,3)) if state=='unmaintained' else '-',zorder=5)
# Proposed bridge crossing and graded cliff transition; no official facility IDs yet.
for pt,marker in [(bridge,'s'),(ramp,'d')]:
 ax.plot(pt.x,pt.y,marker=marker,markersize=6,markerfacecolor=bg,markeredgecolor='#805e43',markeredgewidth=1.2,linestyle='None',zorder=9)
# Openings: known mouths, no assumed destination.
for x,y in unknown:
 line([(x-.04,y-.04),(x+.04,y+.04)],color='#48615a',lw=5,solid_capstyle='round',zorder=7)
# Unmaintained interior entrances treated identically, no D label.
for x,y in [(2.65,1.20),(2.30,.66),(4.22,1.26)]:
 line([(x-.035,y),(x+.035,y)],color='#48615a',lw=5,solid_capstyle='round',zorder=7)
for k,d in [('N112',(.22,.22)),('N111',(.34,.10)),('N110',(.25,-.18))]:
 x,y=P[k];ax.add_patch(FancyArrowPatch((x,y),(x+d[0],y+d[1]),arrowstyle='-|>',mutation_scale=13,color=ink,lw=1.6,zorder=6))
for x,y,k in [(3.99,3.38,'N112'),(5.10,2.51,'N111'),(4.96,.20,'N110')]:
 c=connections[k];txt(x,y,f"AREA {c['area']}\n{c['name'].upper()}",fontsize=9,ha='center',va='center',fontweight='bold',color=colors[c['route']],linespacing=1.25)
# Label positions deliberately offset from route shields and facilities.
opts={101:(-.09,.13),102:(-.03,.13),103:(-.08,-.12),104:(.04,.12),105:(.05,.14),106:(.08,.14),107:(-.03,-.10),108:(-.02,-.13),109:(.08,-.12),110:(.03,.12),111:(-.05,.14),112:(-.04,-.14),113:(-.12,0),114:(-.03,-.10),115:(-.06,.12),116:(-.04,-.11),117:(-.16,.04),118:(.02,.12),119:(.13,-.04),120:(.14,-.12),121:(-.03,.11),122:(.12,.05),123:(.04,-.12),124:(.12,.06),125:(-.12,-.06),126:(.14,-.025),127:(.05,-.13)}
for k,(x,y) in P.items():
 if k=='GATE':continue
 dx,dy=opts[int(k[1:])];ax.add_patch(Circle((x,y),.026,fc=bg,ec=ink,lw=1.2,zorder=8));txt(x+dx,y+dy,k,fontsize=8.5,ha='center',va='center',zorder=12,path_effects=[patheffects.withStroke(linewidth=2.5,foreground=rock)])
# Distinct pictograms. A short leader identifies the associated NODE.
from matplotlib.path import Path as MPath
house=MPath([(-1,-.8),(1,-.8),(1,.25),(0,1.1),(-1,.25),(-1,-.8)],[1,2,2,2,2,79])
crate=MPath([(-1,-1),(1,-1),(1,1),(-1,1),(-1,-1),(-1,-1),(1,1),(-1,1),(1,-1)],[1,2,2,2,79,1,2,1,2])
# marker, outline color, fill color
styles={'mine':('D','#527d94','#527d94'),'shelter':(house,'#876b43','#876b43'),'water':('o','#527d94','#527d94'),'survey':('^','#527565','#527565'),'lookout':('^','#527565',bg),'cargo':(crate,'#876b43',bg),'quarry':('D','#88716c',bg),'abandoned':('X','#88716c','#88716c')}
kind_by_node={'N124':'quarry','N126':'abandoned'}
positions={105:(2.98,2.49),106:(3.83,1.90),113:(.57,1.57),114:(1.13,1.16),117:(1.87,2.96),119:(2.95,2.36),122:(3.33,1.04),124:(4.41,1.94),126:(2.00,.46),127:(3.85,.55)}
def mark(kind,x,y):
 marker,col,fill=styles[kind]
 ax.plot(x,y,marker=marker,markersize=8.5,markerfacecolor=fill,markeredgecolor=col,markeredgewidth=1.4,linestyle='None',zorder=13)
for k,(name,kind) in facilities.items():
 kind=kind_by_node.get(k,kind);x,y=positions[int(k[1:])]
 line([P[k],(x,y)],color=styles[kind][1],lw=.85,zorder=6)
 mark(kind,x,y)
for x,y,r in [(.65,1.90,3),(1.88,2.10,3),(2.53,1.89,7),(4.31,2.23,7),(.82,2.39,12),(2.72,2.73,12),(3.37,2.89,12),(1.78,1.66,65),(2.24,1.23,65),(4.22,.41,65),(3.55,2.35,112),(2.72,1.60,165),(.70,1.17,201),(1.84,1.31,201),(1.62,2.82,214),(2.67,2.53,215),(3.39,1.25,231),(4.17,1.62,240),(1.74,.91,245)]:tag(x,y,str(r),colors[r],9)
gx,gy=P['GATE'];ax.add_patch(Circle((gx,gy),.058,fc=bg,ec='#38554e',lw=2,zorder=16));txt(gx,gy+.13,'GATE',fontsize=10,fontweight='bold',ha='center',va='center',zorder=16,path_effects=[patheffects.withStroke(linewidth=3,foreground=rock)])
txt(2.29,3.46,'AREA 1  /  FIRSTLIGHT CAVERN',fontsize=17,fontweight='bold',ha='center');txt(.98,1.73,'ALDEN HIGHROAD',fontsize=9,ha='center',color='#866e44');txt(2.48,1.73,'VEYRAN HIGHROAD',fontsize=9,ha='center',color=colors[7])
line([(.1,-.12),(1.1,-.12)],color=ink,lw=2);line([(.1,-.16),(.1,-.08)],color=ink,lw=1.4);line([(1.1,-.16),(1.1,-.08)],color=ink,lw=1.4);txt(.6,-.24,'1 km (local)',fontsize=9,ha='center')
fig.legend(handles=[Line2D([0],[0],color=colors[3],lw=4,label='Main route (colored)'),Line2D([0],[0],color=colors[201],lw=2.5,label='Regional route'),Line2D([0],[0],color='#8b9487',lw=1.5,label='Local path'),Line2D([0],[0],color='#8b9487',lw=1.5,ls='--',label='Unmaintained trail'),Line2D([0],[0],marker='o',color=ink,mfc=bg,lw=0,label='Node'),Line2D([0],[0],color='#48615a',lw=5,label='Opening')],loc='lower center',bbox_to_anchor=(.5,.165),ncol=6,frameon=False,fontsize=10.5,labelcolor=ink)
fig.lines.append(Line2D([.04,.96],[.158,.158],transform=fig.transFigure,color='#b8b5a6',lw=.8))
def legend_mark(kind,label):
 marker,col,fill=styles[kind]
 return Line2D([0],[0],marker=marker,markerfacecolor=fill,markeredgecolor=col,markeredgewidth=1.4,markersize=8.5,lw=0,label=label)
fig.text(.04,.138,'FACILITIES & WORKINGS',fontsize=9,fontweight='bold',color=ink)
fig.legend(handles=[legend_mark(k,l) for k,l in [('mine','Active mine'),('shelter','Way shelter'),('survey','Survey station'),('cargo','Loading yard'),('quarry','Old quarry'),('abandoned','Abandoned workings')]],loc='lower left',bbox_to_anchor=(.29,.123),ncol=6,frameon=False,fontsize=9.5,labelcolor=ink,columnspacing=1.4)
fig.text(.04,.104,'NATURAL FEATURES & LANDMARKS',fontsize=9,fontweight='bold',color=ink)
fig.legend(handles=[legend_mark('water','Spring'),legend_mark('lookout','Shaft lookout')],loc='lower left',bbox_to_anchor=(.29,.089),ncol=2,frameon=False,fontsize=9.5,labelcolor=ink)
fig.text(.04,.070,'TERRAIN (PROPOSED)',fontsize=9,fontweight='bold',color=ink)
fig.legend(handles=[Patch(fc='#c2b39a',ec='#93846f',label='Rock massif'),Patch(fc='#908c7b',ec='#726f60',hatch='///',label='Pillar'),Line2D([0],[0],color='#8d7058',lw=1.7,label='Cliff'),Line2D([0],[0],color='#6da6b9',lw=2.8,label='Stream / pool'),Patch(fc='#b2c5a5',ec='#93a78e',hatch='..',label='Growth zone'),Line2D([0],[0],marker='s',mfc=bg,mec='#805e43',lw=0,label='Bridge'),Line2D([0],[0],marker='d',mfc=bg,mec='#805e43',lw=0,label='Graded passage')],loc='lower left',bbox_to_anchor=(.29,.055),ncol=7,frameon=False,fontsize=9,labelcolor=ink,columnspacing=1.0)
fig.text(.04,.018,'CONCEPT STUDY · TERRAIN AND CROSSINGS SUBJECT TO APPROVAL · NOT A SURVEYED RELIEF MAP',fontsize=9,color=mute)
fig.canvas.draw()
renderer=fig.canvas.get_renderer()
from itertools import combinations
labels=[]
for t in ax.texts:
 b=t.get_window_extent(renderer)
 if t.get_bbox_patch() is not None: b=t.get_bbox_patch().get_window_extent(renderer)
 labels.append((t.get_text(),b.expanded(1.04,1.13)))
collisions=[(a,b) for (a,p),(b,q) in combinations(labels,2) if p.overlaps(q)]
print('Label collisions:',collisions)
assert not collisions, collisions
for ext in ['png','svg']:fig.savefig(out/f'ruosuen_area1_terrain_study.{ext}',dpi=180,facecolor=bg)
plt.close(fig)
# No D designation or hidden destination in the map data. DM routing link is separate in notes.
data={'status':'design draft; no formal registration','area':1,'coordinate_frame':'Area 1 only; arbitrary local axes; z relative to provisional GATE datum; v4 elevations rebased +15 m', 'gate_position_status':'provisional', 'other_area_connections':connections,'route_names':route_names,'points':{k:{'xy_km':v,'z_m':z[k]} for k,v in P.items()},'routes':R,'route_geometry_overrides':{'-'.join(k):v for k,v in paths.items()},'cavern_outline':outline,'unknown_openings':unknown,'trails':[{'from':k,'vertices':ps,'state':state} for k,ps,state in trails],'facilities':{k:{'name':v[0],'kind':v[1]} for k,v in facilities.items()},'lower_shaft':{'xy_km':[2.55,2.3],'extent':'unknown'},'interior_openings':[[2.65,1.2],[2.30,.66],[4.22,1.26]]}
(out/'ruosuen_area1_terrain_study.json').write_text(json.dumps({'status':'terrain study, unapproved','terrain':terrain,'bridge_candidate_xy_km':[bridge.x,bridge.y],'graded_passage_candidate_xy_km':[ramp.x,ramp.y],'base_map':data},indent=2),encoding='utf-8')
print(f'{len(P)-1} numbered nodes, {len(R)} routes, {len(segments)} numbered-road segments; no unexpected intersections')
