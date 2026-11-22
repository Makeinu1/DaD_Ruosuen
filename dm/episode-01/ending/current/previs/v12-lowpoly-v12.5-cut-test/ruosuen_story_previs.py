#!/usr/bin/env python3
"""Episode01 ending low-poly geometric previs. PROVISIONAL, not WH01 author-approved mesh.
Run: python ruosuen_story_previs.py --out DIR
Dependencies: numpy, Pillow. No remote assets, no AI image generation.
"""
import argparse, json, math, random, os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
PI=math.pi
STATIONS=[
 (6.5,-90,15,3),(10.5,-90,-25,14),(12.5,-85.778,-48.941,18),
 (14.5,-73.623,-69.995,15),(16.5,-60.15,-82.341,11.5),
 (18,-49.583,-88.442,16),(19.75,-38.117,-92.615,21),
 (20.8,-32.155,-93.937,24),(21.16,-29.36,-94.371,24.386),
 (25.5,3.941,-90.778,29),(26,8.472,-88.948,30),
 (29.5,37.341,-65.15,31),(31.5,45.778,-48.941,32),
 (33,48.937,-37.155,33),(35.7,50,-9,32),(40,50,30,55),
 (47,50,100,105),(48,50,110,112),(51,42.505,143.809,130),
 (55,21.423,171.284,160),(58,10,179.282,182),
 (62,-2.638,185.175,205),(64,-18.866,189.221,224)]
S1=[(40,-52,3,'base',25.5),(55,-28,3,'bank',28),(66,4,3,'shoulder',31),
 (72,8,3,'inner',33),(85,30,3,'tip',35.7),(90,25,3,'side',35.4)]
SHORE=[(-160,25),(-135,-3),(-115,-15),(-95,-22),(-85,-26),(-70,-46),(-55,-61),
 (-40,-65),(-20,-69),(0,-64),(20,-42),(35,-30),(50,-12),(62,3),
 (72,15),(78,29),(85,38),(92,32),(100,20),(115,15),(132,43),(151,100),(165,200)]
FISSURE=[(24,-9,15),(70,-11,17),(100,-25,21),(135,-53,26),
 (165,-62,28),(185,-57,30),(210,-24,22),(250,-8,14)]
SHOTS=[
 ('N01',0,3,'静かな地底湖','A',1.5),('N02',3,5.5,'異変・波紋','RIPPLE',4.3),
 ('N03',5.5,7.5,'水面下の影','SUB',6.2),('N04',7.5,11,'水面から浮上','BREACH',9.0),
 ('N05',11,14,'岸へ接近','APPROACH',12.5),('N06',14,18,'真上の巨大な通過','B',16.5),
 ('N07',18,20.5,'攻撃せず通過','BEHIND',19.2),('N08',20.5,26,'月光と点灯','C',23.0),
 ('N09',26,31,'S1基部の開花','D',28.0),('N10',31,36.5,'岬先端へ開花','FLOWERWIDE',35.9),
 ('N11',36.5,40,'本物の花弁＋小果実','MACRO',38.4),
 ('N12',40,43,'白金の花吹雪','PLUME',41.5),
 ('N13',43,47,'鯨と花雪の全景','E-WIDE',45),
 ('N14',47,51,'高空の自由遊泳','E-TELE',49.2),
 ('N15',51,57.5,'裂け目への上昇','ASCENT',54.4),
 ('N16',57.5,64,'裂け目から退場','F',61.0),
 ('N17',64,70,'同じ地底湖の静寂','A',67.0)]
EXTRA={'N06':[14.5,15.5,16.5,17.8], 'N08':[20.8,21.4,23.2,25.5],
       'N10':[32.0,35.9], 'N14':[47.2,50.6], 'N16':[58,62,63.8]}
FONTPATH='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if not os.path.exists(FONTPATH):
 FONTPATH='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT=ImageFont.truetype(FONTPATH,24)
FONTS=ImageFont.truetype(FONTPATH,18)
FONTB=ImageFont.truetype(FONTPATH,32)

def N(v):return np.array(v,dtype=float)
def unit(v):
 v=N(v);return v/max(1e-9,np.linalg.norm(v))
def clamp(v,a=0,b=1):return min(b,max(a,v))
def interp(t):
 if t<=STATIONS[0][0]:
  if t<6.5:return N([-90,15,-3]),N([0,-10,4])
  t=6.5
 if t>=STATIONS[-1][0]:
  a,b=STATIONS[-2:];dt=b[0]-a[0];vel=(N(b[1:])-N(a[1:]))/dt
  return N(b[1:])+(t-64)*vel,vel
 idx=next(i for i in range(len(STATIONS)-1) if STATIONS[i][0]<=t<=STATIONS[i+1][0])
 a,b=STATIONS[idx:idx+2];pre=STATIONS[max(0,idx-1)];post=STATIONS[min(len(STATIONS)-1,idx+2)]
 dt=b[0]-a[0];u=(t-a[0])/dt
 p=N(a[1:]);q=N(b[1:]);v0=(q-N(pre[1:]))/(b[0]-pre[0]);v1=(N(post[1:])-p)/(post[0]-a[0]);
 pos=(2*u**3-3*u**2+1)*p+(u**3-2*u**2+u)*dt*v0+(-2*u**3+3*u**2)*q+(u**3-u**2)*dt*v1
 vel=((6*u*u-6*u)*p+(3*u*u-4*u+1)*dt*v0+(-6*u*u+6*u)*q+(3*u*u-2*u)*dt*v1)/dt
 return pos,vel

def pose(t):
 cp,velocity=interp(t);forward=unit(velocity)
 side=unit(N([-forward[1],forward[0],0]));up=unit(np.cross(forward,side));
 # by design no gratuitous full back roll
 return cp,forward,side,up

def world(t,local):
 cp,f,s,u=pose(t);p=N(local)
 return cp+f*p[0]+s*p[1]+u*p[2]

def camera(name,t):
 # Cinematic cameras, all provisional, no physical movement except C / E-TELE.
 cams={
  'A':((-18,-93,3),0,18.5,18),
  'RIPPLE':((-62,-63,2.8),-25,-5,35),
  'SUB':((-66,-57,4.3),-31,-4,28),
  'BREACH':((-56,-39,4.8),-62,17,24),
  'APPROACH':((-48,-74,4.1),-51,23,26),
  'B':((-58,-84,4.1),-60,50,16),
  'BEHIND':((-58,-84,4.1),106,38,24),
  'C':((-10,-113,5),-10+15*clamp((t-20.5)/5.0),40,18),
  'D':((-58,-84,4.1),50,14,20),
  'FLOWERWIDE':((25,-55,12),37,-8,28),
  'MACRO':((71.8,7.64,3.42),29,-40,80),
  'PLUME':((11,-63,6.0),42,18,24),
  'E-WIDE':((-58,-84,4.1),25,31,24),
  'E-TELE':((-58,-84,4.1),25,25+1.5*clamp((t-47)/4),70),
  'ASCENT':((-58,-84,4.1),12,34,35),
  'F':((-10,-108,5),0,37,50)}
 return cams[name]

def basis(cam):
 (x,y,z),yaw,pitch,lens=cam;y=math.radians(yaw);p=math.radians(pitch)
 front=N([math.sin(y)*math.cos(p),math.cos(y)*math.cos(p),math.sin(p)])
 right=N([math.cos(y),-math.sin(y),0]);up=unit(np.cross(right,front))
 return N([x,y,z]) if False else N(cam[0]),right,up,front

def tocamera(p,cam):
 pos,r,u,f=basis(cam);d=N(p)-pos
 return N([np.dot(d,r),np.dot(d,u),np.dot(d,f)])

def projection(p,cam,W,H):
 v=tocamera(p,cam)
 if v[2]<.10:return None
 return (W/2 + (v[0]/v[2]) * cam[3]/36*W,
         H/2 - (v[1]/v[2])*cam[3]/20.25*H, v[2])

def clip_cam(poly,near=.1):
 out=[]
 for i in range(len(poly)):
  a=N(poly[i]);b=N(poly[(i+1)%len(poly)]);in_a=a[2]>=near;in_b=b[2]>=near
  if in_a:out.append(a)
  if in_a!=in_b:
   f=(near-a[2])/(b[2]-a[2]);out.append(a+f*(b-a))
 return out

def mkmesh():
 rings=[(-11.6,.18,.18,.1),(-10.1,.38,.38,.1),(-8.5,.86,.8,.10),(-6.5,1.52,1.4,.05),
 (-4,2.07,1.95,0),(-1.4,2.26,2.21,0),(1.5,2.27,2.15,-.07),(4,2.14,1.98,-.18),
 (6.4,1.88,1.7,-.38),(8.5,1.76,1.55,-.55),(10,1.68,1.35,-.68),
 (11.25,1.35,1.06,-.74),(12,.78,.58,-.75),(12.3,.12,.10,-.75)]
 n=12;tri=[]
 pts=[[N([x,w*math.cos(2*PI*j/n),z+h*math.sin(2*PI*j/n)]) for j in range(n)]for x,w,h,z in rings]
 for i in range(len(pts)-1):
  for j in range(n):
   k=(j+1)%n;tri.append((pts[i][j],pts[i][k],pts[i+1][k],'body'));tri.append((pts[i][j],pts[i+1][k],pts[i+1][j],'body'))
 for sign in [-1,1]:
  a=[(3.3,1.8,-.65),(2.6,3.8,-.75),(-.75,6.5,-1.2),(-2.45,7.4,-1.3),(-3.8,6.8,-1.25),(-2.6,3.45,-.8),(.1,1.9,-.62)]
  arr=[N([x,sign*y,z]) for x,y,z in a];cent=N([-1,sign*4.35,-.95])
  for j in range(len(arr)):tri.append((cent,arr[j],arr[(j+1)%len(arr)],'fin'))
  a=[(-11.2,0,.16),(-10.75,1.3,.18),(-11.2,3.5,.19),(-12.02,4.5,.23),(-11.6,3,.08),(-11.1,.55,.06)]
  arr=[N([x,sign*y,z]) for x,y,z in a];cent=N([-11.4,sign*2.2,.1])
  for j in range(len(arr)):tri.append((cent,arr[j],arr[(j+1)%len(arr)],'tail'))
 tri.extend([(N([-5.7,-.4,1.75]),N([-5.9,0,2.48]),N([-3.95,0,1.94]),'dorsal'),
 (N([-5.7,.4,1.75]),N([-3.95,0,1.94]),N([-5.9,0,2.48]),'dorsal')])
 return tri
MESH=mkmesh()

def gradient_bg(W,H):
 image=Image.new('RGB',(W,H));px=image.load()
 for y in range(H):
  f=y/H;R=int(13+7*f);G=int(25+14*f);B=int(37+17*f)
  for x in range(W):px[x,y]=(R,G,B)
 return image

def polyline_project(points,cam,draw,color,width=2,closed=False):
 seg=[]
 for p in points:
  k=projection(p,cam,1152,648)
  if k is None:
   if len(seg)>1:draw.line(seg,fill=color,width=width,joint='curve')
   seg=[]
  else:seg.append((k[0],k[1]))
 if len(seg)>1:draw.line(seg+[seg[0]] if closed else seg,fill=color,width=width,joint='curve')

def paint_poly_items(img, items,cam):
 # Each item = (world 3d polygon, RGB, opacity?, priority)
 W,H=img.size;polys=[]
 for poly,col,layer in items:
  pp=[tocamera(p,cam) for p in poly]
  pp=clip_cam(pp)
  if len(pp)<3:continue
  xy=[(W/2+(v[0]/v[2])*cam[3]/36*W,H/2-(v[1]/v[2])*cam[3]/20.25*H) for v in pp]
  if max(x for x,y in xy)<0 or min(x for x,y in xy)>W or max(y for x,y in xy)<0 or min(y for x,y in xy)>H:continue
  polys.append((sum(p[2] for p in pp)/len(pp),layer,xy,col))
 polys.sort(reverse=True,key=lambda x:(x[0],-x[1]))
 d=ImageDraw.Draw(img)
 for dep,layer,xy,col in polys:d.polygon(xy,fill=col)

def ground_items():
 land=N([-225,-140,1]);items=[]
 # water: moderately dark plane, deliberately few details
 # Ground tile behind whale, near-shore land separated by actual shore points
 for i in range(len(SHORE)-1):
  a,b=SHORE[i:i+2]
  items.append(([N([a[0],a[1],0]),N([b[0],b[1],0]),N([b[0],-140,1]),N([a[0],-140,1])],(67,69,62),-2))
 items.append(([N([-225,10,0]),N([225,10,0]),N([225,510,0]),N([-225,510,0])],(22,51,64),-3))
 return items
GROUND=ground_items()

def moon_visible(cam):
 pos=N(cam[0]);roof_y=pos[1]+(190-pos[2])/math.tan(math.radians(43.01));x=pos[0]
 lo,hi=FISSURE[0][1:]
 for i in range(len(FISSURE)-1):
  a,b=FISSURE[i:i+2]
  if a[0]<=roof_y<=b[0]:
   f=(roof_y-a[0])/(b[0]-a[0]);lo=a[1]+f*(b[1]-a[1]);hi=a[2]+f*(b[2]-a[2]);break
 return lo<=x<=hi

def fissure_path():
 pts=[(xleft,y,190)for y,xleft,xright in FISSURE]
 pts +=[(xright,y,190)for y,xleft,xright in FISSURE[::-1]]
 return pts

def draw_roof_and_moon(img,cam,shot,t):
 W,H=img.size;dr=ImageDraw.Draw(img)
 # uniform distant cavern roof plane, show asymmetrical single opening as bounded projected 3D polygon
 roof=fissure_path();p=[projection(x,cam,W,H) for x in roof];p=[(q[0],q[1]) for q in p if q]
 if len(p)>=3:
  # an upper roof silhouette/soft ring; sky patch is not a giant gaping hole
  dr.polygon(p,fill=(43,68,84));dr.line(p+[p[0]],fill=(109,137,143),width=2)
 # tiny natural lunar disk only through actual opening; no moon in B or D
 if shot not in ('N02','N03','N04','N05','N06','N07','N09','N10','N11','N12','N13','N14') and moon_visible(cam):
  v=[0,math.cos(math.radians(43.01)),math.sin(math.radians(43.01))]
  origin=N(cam[0]);far=origin+N(v)*1000;qq=projection(far,cam,W,H)
  if qq:
   x,y,_=qq;r=3.5 if cam[3]<=24 else 6.5
   dr.ellipse((x-r,y-r,x+r,y+r),fill=(226,224,198))

def whale_items(t):
 # No whale in N01,N02,N17. Else one shared 24m triangulated proxy.
 cp,f,side,up=pose(t)
 items=[]
 for a,b,c,kind in MESH:
  verts=[cp+f*p[0]+side*p[1]+up*p[2] for p in (a,b,c)]
  normal=unit(np.cross(verts[1]-verts[0],verts[2]-verts[0]))
  lam=.66+.24*abs(np.dot(normal,N([.27,.20,.94])))
  u=(a[0]+b[0]+c[0])/3
  # The whale is not self-emissive before moon contact; organic head-to-tail propagation later.
  on=clamp((t-21.17 - (12-u)*.13)/1.3)
  base={'body':(88,112,132),'fin':(79,112,128),'tail':(82,115,130),'dorsal':(70,97,111)}[kind]
  dest=(179,203,215) if kind=='body' else (147,193,201)
  col=tuple(int(clamp(base[i]*lam*(1-on)+dest[i]*on*(.85+.12*lam),0,255)) for i in range(3))
  items.append((verts,col,1))
 return items

def site_items(t,shot):
 rng=random.Random(2666);items=[];dots=[]
 for x,y,z,label,start in S1:
  for j in range(20):
   xx=x+rng.uniform(-4,4);yy=y+rng.uniform(-5,5);z=z+rng.uniform(-.04,.05)
   open_=t>=start+rng.uniform(-.6,.5)
   if open_:
    # small cream 5-lobed schematic signal on land; radius 2.25cm, maintain size
    dots.append(((xx,yy,z+.075),(232,224,197),.0225))
   else:dots.append(((xx,yy,z+.075),(95,91,74),.018))
 return dots

def seeds(t):
 if t<36.6:return []
 rng=random.Random(1130);dots=[]
 # The three independent depth volumes are composition aids, not a claim all petals climb 100m instantly.
 for layer,n in [(0,48),(1,34),(2,35)]:
  if layer==2 and t<43:continue
  for j in range(n):
   z0=[3,14,43][layer];maxr=[13,24,44][layer];
   life=clamp((t-(36.5+layer*2.9))/7)
   if life<=0:continue
   x=[70,50,46][layer]+rng.uniform(-maxr,maxr)+life*(j%5-2)*.5
   y=[10,28,115][layer]+rng.uniform(-maxr,maxr)+life*18
   z=z0+rng.uniform(0,[6,24,38][layer])+math.sin(t*.16+j)*2
   # each visible object represents one REAL petal+tiny fruit, not an entire flower or extra wing
   dots.append(((x,y,z),[240,232,211] if j%4 else [223,209,163],.012 if layer<2 else .02))
 return dots

def draw_points(img,cam,t,shot):
 W,H=img.size;dr=ImageDraw.Draw(img)
 pts=[]
 if shot in ('N01','N17'):
  pts.append(((-18,-83,2.08),(234,226,198),.025,'P0'))
 elif shot in ('N09','N10','N11','N12'):
  pts += [(p,c,r,'S1') for p,c,r in site_items(t,shot)]
 if shot in ('N11','N12','N13','N14','N15','N16'):
  pts +=[(p,c,r,'petal') for p,c,r in seeds(t)]
 for p,c,r,typ in pts:
  q=projection(p,cam,W,H)
  if q is None:continue
  x,y,z=q
  # exact physical radius, but min 1.2px to visualize locations at storyboard scale;
  # use close macro on N11 for correct organ geometry.
  rr=max(1.25,cam[3]/36*W*r/max(.15,z))
  if typ=='petal':
   if rr<2.0:rr=2.0
   dr.polygon([(x-rr,y-rr),(x+rr*.7,y-rr*.2),(x+rr*.5,y+rr*.7),(x-rr*.3,y+rr)],fill=tuple(c))
  else:
   dr.ellipse((x-rr,y-rr,x+rr,y+rr),fill=tuple(c))

def draw_macro(img,cam):
 W,H=img.size;d=ImageDraw.Draw(img)
 center=N([72,8,3.08])
 # Five real petals each ~2cm long (not abstract sparkles), fruit ~2.5mm attached.
 for i in range(5):
  a=2*PI*i/5
  rad=N([math.cos(a),math.sin(a),0]);side=N([-math.sin(a),math.cos(a),0])
  verts=[center+rad*.007+side*(-.009),center+rad*.026+side*(-.010),center+rad*.030+side*.002,center+rad*.025+side*.010,center+rad*.007+side*.009]
  arr=[projection(q,cam,W,H) for q in verts];arr=[(v[0],v[1]) for v in arr if v]
  if len(arr)==5:d.polygon(arr,fill=(236,227,209));d.line(arr+[arr[0]],fill=(184,179,159),width=2)
 # exactly one petal detaching, containing small attached fruit (marker visible without increasing physical fruit radius)
 offset=N([.052,.043,.013]);q=projection(center+offset,cam,W,H)
 if q:
  x,y,dep=q;d.polygon([(x-13,y+4),(x-10,y-7),(x+4,y-16),(x+9,y-11),(x+7,y+5)],fill=(247,234,203))
  d.ellipse((x-13,y+2,x-8,y+7),fill=(231,212,140))
 c=projection(center,cam,W,H)
 if c:d.ellipse((c[0]-3,c[1]-3,c[0]+3,c[1]+3),fill=(206,179,108))

def draw_water_marks(img,cam,t,shot):
 W,H=img.size;d=ImageDraw.Draw(img)
 if shot in ('N02','N03'):
  for rr in [5,9,14,19]:
   pts=[]
   for a in range(65):
    p=N([-89+rr*math.cos(a*2*PI/64),1+rr*math.sin(a*2*PI/64),.10])
    qq=projection(p,cam,W,H)
    if qq:pts.append((qq[0],qq[1]))
   if len(pts)>3:d.line(pts,fill=(110,155,169),width=3)
 if shot in ('N04','N05'):
  # displaced water is spatial cue, not magical illumination
  center=N([-90,-10,0]);rng=random.Random(12)
  for j in range(22):
   p=center+N([rng.uniform(-9,9),rng.uniform(-8,8),rng.uniform(1,8)])
   q=projection(p,cam,W,H)
   if q:d.line([(q[0],q[1]),(q[0]+2,q[1]+8)],fill=(105,142,155),width=2)
 if shot in ('N01','N17'):
  for xx,yy in [(-60,20),(-23,60),(30,12)]:
   a=projection((xx-8,yy,.06),cam,W,H);b=projection((xx+8,yy,.06),cam,W,H)
   if a and b:d.line((a[0],a[1],b[0],b[1]),fill=(51,84,95),width=1)

def draw_diagnostic(img,cam,shot,t):
 W,H=img.size;d=ImageDraw.Draw(img)
 # Explicit production markers, not magical luminous objects. Same meter-scale geometry.
 def label(text,pos,color=(213,203,156),dx=14,dy=-22):
  p=projection(pos,cam,W,H)
  if not p:return None
  x,y,_=p
  if x<-25 or x>W+25 or y<-25 or y>H+25:return None
  d.ellipse((x-5,y-5,x+5,y+5),outline=color,width=2)
  d.text((x+dx,y+dy),text,font=FONTS,fill=color)
  return (x,y)
 if shot=='N06':
  cp,_,_,_=pose(t);label('body center / PROXY',cp)
 if shot=='N08':
  cp,_,_,_=pose(t);label('WH-01 / before or after contact',cp,(192,224,225),-255,20)
 if shot in ('N09','N10'):
  cp,_,_,_=pose(t)
  a=label('S1 base',S1[0][:3],(238,204,138))
  b=label('S1 tip 35.7s',S1[4][:3],(238,204,138))
  w=label('WHALE / luminous',cp,(173,218,229),-230,-29)
  if w and a and shot=='N09':
   # color-coded causality line is diagram annotation, not a physical directed beam
   d.line((w[0],w[1],a[0],a[1]),fill=(173,164,106),width=2)
 if shot=='N16':
  cp,_,_,_=pose(t);label('Whale (proxy)',cp,(194,220,226),20,15)
  label('single fissure',(-5,170,190),(235,196,139),-120,-28)
 if shot in ('N01','N17'):
  label('P0 · young / no dispersion',(-18,-83,2.08),(228,214,175),12,-30)
def draw_legend(img,shot,frame,t,cam):
 W,H=img.size;d=ImageDraw.Draw(img,'RGBA')
 d.rounded_rectangle((13,11,520,85),radius=11,fill=(8,18,29,212),outline=(73,98,112,140),width=1)
 _,start,end,name,_,_=next(s for s in SHOTS if s[0]==shot)
 d.text((25,15),f'{shot}  {t:05.2f}s   {name}',font=FONT,fill=(241,241,231,255))
 d.text((25,51),f'CAM {frame} · {cam[3]:g}mm · yaw {cam[1]:g}° · pitch {cam[2]:g}°',font=FONTS,fill=(171,206,214,255))
 d.rounded_rectangle((W-286,H-39,W-14,H-11),radius=6,fill=(8,18,29,200))
 d.text((W-272,H-37),'LOW-POLY PREVIS · NOT FINAL',font=FONTS,fill=(206,184,144,255))

def render_one(shot,t,outpath):
 W,H=1152,648
 sid,s0,s1,title,camName,_=next(s for s in SHOTS if s[0]==shot)
 cam=camera(camName,t)
 img=gradient_bg(W,H)
 geoms=GROUND.copy()
 if shot not in ('N01','N02','N17'):
  geoms += whale_items(t)
 paint_poly_items(img,GROUND,cam)
 draw_roof_and_moon(img,cam,shot,t)
 if shot not in ('N01','N02','N17'):
  body=whale_items(t)
  if shot=='N03':body=[(p,tuple(int(x*.26) for x in col),lay) for p,col,lay in body]
  paint_poly_items(img,body,cam)
 draw_water_marks(img,cam,t,shot)
 draw_points(img,cam,t,shot)
 draw_diagnostic(img,cam,shot,t)
 if shot=='N11':draw_macro(img,cam)
 if shot=='N17':
  # one last white petal near P0, still NOT P0's own petal; fades on land/lake
  d=ImageDraw.Draw(img)
  p=projection((-20,-62,3.1),cam,W,H)
  if p:d.polygon([(p[0]-3,p[1]-2),(p[0]+4,p[1]-1),(p[0],p[1]+5)],fill=(232,226,202))
 draw_legend(img,shot,camName,t,cam)
 img.save(outpath,optimize=True)
 return {'shot':shot,'time':t,'camera':camName,'filename':outpath.name,'camera_xyz':cam[0],
 'yaw_deg':cam[1],'pitch_deg':cam[2],'focal_mm':cam[3]}

def make_contact(images,out):
 from PIL import ImageOps
 TW,TH=396,223
 font=ImageFont.truetype(FONTPATH,15)
 cols=3;rows=math.ceil(len(images)/cols)
 sheet=Image.new('RGB',(TW*cols, (TH+25)*rows+15),(10,23,34));d=ImageDraw.Draw(sheet)
 for i,p in enumerate(images):
  with Image.open(p) as im:small=im.resize((TW,TH),Image.Resampling.LANCZOS)
  x=(i%cols)*TW;y=(i//cols)*(TH+25)
  sheet.paste(small,(x,y));d.text((x+10,y+TH+2),p.stem,fill=(215,232,238),font=font)
 sheet.save(out,optimize=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',default='/mnt/data/ruosuen_v12_previs');args=ap.parse_args()
 out=Path(args.out);out.mkdir(parents=True,exist_ok=True);records=[];imgs=[]
 for sid,start,end,title,cam,t in SHOTS:
  times=EXTRA.get(sid,[t])
  for j,tm in enumerate(times):
   name=f'{sid}-{j+1:02d}-{tm:05.2f}s.png'
   p=out/name;records.append(render_one(sid,tm,p));imgs.append(p)
 make_contact(imgs,out/'contact-sheet.png')
 (out/'frames.json').write_text(json.dumps({'version':'previs-v12.2-draft','date':'2026-11-22','source':'v12/v12.1 unapproved timing and 3D XY stations v0.4','frames':records},ensure_ascii=False,indent=2))
 print('frames',len(records),'files',len(list(out.iterdir())))
