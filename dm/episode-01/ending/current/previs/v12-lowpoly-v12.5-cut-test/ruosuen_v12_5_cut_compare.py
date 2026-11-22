#!/usr/bin/env python3
"""v12.5 A/B low-poly film edit experiment. Source: v12.4 camera patch (itself v12.3/v12.2).
Uses the same STATIONS, 24m lowpoly WH-01 proxy, background and static cameras.
A: 17 shots, existing v12.4/v12.3 70s composition.
B: 19 shots, split N04 into two, add environmental N07.5 (70s).
No WH01 3D geometry, solid rock occlusion, or author approval is claimed.
"""
import argparse,json,math,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import ruosuen_v12_4_front_axis as v124
b=v124.base
N=b.N

# New fixed camera locations: directors' *comparison* values, not final production settings.
NEW_CAMERAS={
 'BREACH_FRONT':((-90,-24,3.2), 0,5,28),
 'BREACH_THREEQ':((-70,-42,5.0),-48,20,24),
 'MOON_ESTABLISH':((-7,-145,6.0),-14,39,28),
}
PREVIOUS_CAMERA=b.camera

def current_camera(name,t):
 return NEW_CAMERAS[name] if name in NEW_CAMERAS else PREVIOUS_CAMERA(name,t)
b.camera=current_camera

# N07.5 is a fixed empty environment shot; never assert it is the PC's eye position.
PROVISIONAL_SHOTS=[
 ('N04A',7.5,9.05,'正面から水面突破','BREACH_FRONT',8.3),
 ('N04B',9.05,11.0,'斜め前方の巨体','BREACH_THREEQ',9.9),
 ('N07.5',19.45,20.50,'月光空間の再提示','MOON_ESTABLISH',20.0),
]
b.SHOTS += PROVISIONAL_SHOTS

# Use one common spline and mesh; no convenient animation repositioning at a cut.
# The v12.4 script patched base.pose and early stations on import.
# Make time-resolved water cues as a low-poly diagnostic only (not a fluid sim).
def breach_spray(img,cam,t):
 W,H=img.size;d=ImageDraw.Draw(img)
 u=b.clamp((t-7.45)/2.6)
 rr=5+11*u
 for radius in (rr*.5,rr):
  points=[]
  for i in range(84):
   a=2*math.pi*i/83
   p=(-90+radius*math.cos(a),-11+radius*math.sin(a),0.12)
   q=b.projection(p,cam,W,H)
   if q:points.append(q[:2])
  if len(points)>8:d.line(points,fill=(75,114,128),width=2)
 if t<10.9:
  # Stable spatial water directions; droplets fall as a function of time rather than follow the whale.
  for i in range(18):
   a=2*math.pi*i/18
   x=-90+7*math.cos(a);y=-11+7*math.sin(a)
   phase=b.clamp((t-7.55)/2.6)
   h=1.2+5.4*math.sin(math.pi*phase)*(0.5+0.5*abs(math.sin(3*a)))
   p=b.projection((x,y,h),cam,W,H)
   if p:
    xx,yy,_=p;d.line((xx,yy,xx+1.4,yy+7.5),fill=(105,143,158),width=2)

# No text overlays/distracting annotations needed except a tiny time/camera slate.
_gradient={}
_orig_grad=b.gradient_bg
def gradient_cached(w,h):
 key=(w,h)
 if key not in _gradient:_gradient[key]=_orig_grad(w,h)
 return _gradient[key].copy()
b.gradient_bg=gradient_cached

CUTS_A=[
 ('N01',0,3,'A'),('N02',3,5.5,'RIPPLE'),('N03',5.5,7.5,'SUB'),
 ('N04',7.5,11,'BREACH'),('N05',11,14,'APPROACH'),('N06',14,18,'B'),
 ('N07',18,20.5,'BEHIND'),('N08',20.5,26,'C'),
 ('N09',26,31,'D'),('N10',31,36.5,'FLOWERWIDE'),('N11',36.5,40,'MACRO'),
 ('N12',40,43,'PLUME'),('N13',43,47,'E-WIDE'),('N14',47,51,'E-TELE'),
 ('N15',51,57.5,'ASCENT'),('N16',57.5,64,'F'),('N17',64,70,'A'),
]
CUTS_B=[
 ('N01',0,3,'A'),('N02',3,5.5,'RIPPLE'),('N03',5.5,7.5,'SUB'),
 ('N04A',7.5,9.05,'BREACH_FRONT'),('N04B',9.05,11,'BREACH_THREEQ'),
 ('N05',11,14,'APPROACH'),('N06',14,18,'B'),
 ('N07',18,19.45,'BEHIND'),('N07.5',19.45,20.5,'MOON_ESTABLISH'),
 ('N08',20.5,26,'C'),('N09',26,31,'D'),('N10',31,36.5,'FLOWERWIDE'),
 ('N11',36.5,40,'MACRO'),('N12',40,43,'PLUME'),('N13',43,47,'E-WIDE'),
 ('N14',47,51,'E-TELE'),('N15',51,57.5,'ASCENT'),('N16',57.5,64,'F'),
 ('N17',64,70,'A'),
]
assert len(CUTS_A)==17 and len(CUTS_B)==19
assert abs(sum(e-s for _,s,e,_ in CUTS_B)-70)<.001

def cut_at(t,version):
 cuts=CUTS_B if version=='B' else CUTS_A
 for sh,s,e,c in cuts:
  if s<=t<e:return sh,s,e,c
 return cuts[-1]

def render(shot,t,width=1152,height=648,letter=None):
 cam_name={'N04A':'BREACH_FRONT','N04B':'BREACH_THREEQ','N07.5':'MOON_ESTABLISH'}.get(shot)
 if cam_name is None:cam_name=next(x[4] for x in b.SHOTS if x[0]==shot)
 cam=b.camera(cam_name,t)
 img=b.gradient_bg(width,height)
 v124._CURRENT_SHOT=shot
 b.paint_poly_items(img,b.GROUND,cam)
 # same roof position and moon visibility algorithm as v12.3
 b.draw_roof_and_moon(img,cam,'N08' if shot=='N07.5' else shot,t)
 if shot not in ('N01','N02','N07.5','N17'):
  body=b.whale_items(t)
  if shot=='N03':body=[(p,tuple(int(x*.26) for x in col),ly) for p,col,ly in body]
  b.paint_poly_items(img,body,cam)
 if shot in ('N04A','N04B'):breach_spray(img,cam,t)
 else:b.draw_water_marks(img,cam,t,shot)
 b.draw_points(img,cam,t,shot)
 if shot not in ('N04A','N04B','N07.5'):b.draw_diagnostic(img,cam,shot,t)
 if shot=='N11':b.draw_macro(img,cam)
 if shot=='N17':
  p=b.projection((-20,-62,3.1),cam,width,height)
  if p:
   d=ImageDraw.Draw(img);d.polygon([(p[0]-3,p[1]-2),(p[0]+4,p[1]-1),(p[0],p[1]+5)],fill=(232,226,202))
 # Small labels remain useful but the underlying image is one time and one camera.
 d=ImageDraw.Draw(img)
 font=ImageFont.truetype(b.FONTPATH, 19 if width>=960 else 15)
 small=ImageFont.truetype(b.FONTPATH, 15 if width>=960 else 12)
 label={'N04A':'正面突破 / FRONT','N04B':'巨体を見せる / THREE-QUARTER','N07.5':'月光の空間 / ENVIRONMENT'}.get(shot,shot)
 d.rounded_rectangle((8,8,min(width-8,480 if width>=960 else 290),63 if width>=960 else 48),radius=8,fill=(9,22,33),outline=(58,85,96),width=1)
 d.text((15,10),f'{shot}  {t:05.2f}s  {label}',font=font,fill=(231,236,231))
 d.text((15,37 if width>=960 else 29),f'CAM {cam_name}  {cam[3]:g}mm / yaw {cam[1]:+g} / pitch {cam[2]:+g}',font=small,fill=(169,203,214))
 if letter:
  tw=90; d.rounded_rectangle((width-tw-8,9,width-9,39),radius=6,fill=(24,42,49))
  d.text((width-tw+5,12),f'CUT {letter}',font=font,fill=(235,208,150))
 return img

KEYFRAMES=[('N03',7.1),('N04A',7.6),('N04A',8.1),('N04A',8.65),
           ('N04B',9.12),('N04B',9.85),('N04B',10.75),
           ('N05',11.2),('N05',13.9),('N06',14.5),('N06',16.5),
           ('N07',18.2),('N07',19.35),('N07.5',19.5),('N07.5',20.1),
           ('N08',20.55),('N08',21.4),('N08',23.2)]

def make_contact(out):
 tw,th=460,259;gap=28;cols=3
 sources=[]
 for sh,t in KEYFRAMES:
  path=out/'keyframes'/f'{sh}-{t:05.2f}s.png'
  sources.append((sh,t,path))
 rows=math.ceil(len(sources)/cols)
 sheet=Image.new('RGB',(tw*cols,(th+gap)*rows),(14,28,39));d=ImageDraw.Draw(sheet)
 ft=ImageFont.truetype(b.FONTPATH,15)
 for i,(sh,t,path) in enumerate(sources):
  with Image.open(path) as f: thumb=f.resize((tw,th),Image.Resampling.LANCZOS)
  x=(i%cols)*tw;y=(i//cols)*(th+gap)
  sheet.paste(thumb,(x,y));d.text((x+8,y+th+3),f'{sh} | {t:.2f}s',font=ft,fill=(223,221,188))
 sheet.save(out/'19shot-added-frames-contact.png',optimize=True)
 # Side-by-side stills to inspect the broken vs repaired N03->N04 cut
 pair=Image.new('RGB',(1152*2,648*2),(12,26,37))
 d=ImageDraw.Draw(pair)
 labels=[('N03',7.1,'SAME'),('N04',8.1,'A'),('N04A',8.1,'B'),('N04B',9.12,'B')]
 for i,(sh,t,v) in enumerate(labels):
  im=render(sh,t,1152,648,v)
  pair.paste(im,(i%2*1152,i//2*648))
 pair.save(out/'split-breach-comparison.png',optimize=True)

def make_map(out):
 W,H=1180,690;im=Image.new('RGB',(W,H),(18,36,48));d=ImageDraw.Draw(im)
 font=ImageFont.truetype(b.FONTPATH,20)
 def xy(x,y):return (int(540+(x+55)*3.0),int(530-(y+85)*2.9))
 for xx in (-110,-90,-70,-50,-30,0,30):
  d.line([xy(xx,-100),xy(xx,60)],fill=(35,56,68),width=1)
 for yy in (-80,-40,0,40):
  d.line([xy(-140,yy),xy(60,yy)],fill=(35,56,68),width=1)
 pts=[xy(*b.interp(x/20)[0][:2]) for x in range(80,425)]
 d.line(pts,fill=(191,209,207),width=3)
 for sh,t in [('N03',7.1),('N04A',8.1),('N04B',9.85),('N05',12.5),('N06',16.5),('N07.5',20.0)]:
  p=b.interp(t)[0];x,y=xy(p[0],p[1]);d.ellipse((x-5,y-5,x+5,y+5),fill=(234,215,169));d.text((x+9,y-13),sh,font=font,fill=(222,218,183))
 for n in ('BREACH_FRONT','BREACH_THREEQ','MOON_ESTABLISH','SUB','B','C'):
  cam=b.camera(n,8.5);p=cam[0];x,y=xy(p[0],p[1]);c=(146,204,218) if n in ('BREACH_FRONT','BREACH_THREEQ') else (124,167,188)
  d.ellipse((x-6,y-6,x+6,y+6),fill=c)
  r=math.radians(cam[1]);d.line((x,y,x+int(26*math.sin(r)),y-int(26*math.cos(r))),fill=c,width=2)
  d.text((x+12,y+11),n,font=ImageFont.truetype(b.FONTPATH,14),fill=c)
 d.text((25,22),'v12.5 · A/B FIXED CAMERA PLAN · PROVISIONAL',font=font,fill=(224,235,230))
 d.text((25,53),'Shared whale XYZ path; NO cut teleports or dolly cameras',font=font,fill=(166,202,214))
 im.save(out/'camera-plan-v12.5.png',optimize=True)

def video(out,version,start,end,fps=8,size=(640,360)):
 name=f'cut-{version}-{start:04.1f}-{end:04.1f}s.mp4'
 dest=out/name
 cmd=['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{size[0]}x{size[1]}',
      '-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','24',
      '-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
 try:
  for i in range(int(round((end-start)*fps))):
   t=start+i/fps
   sh,_,_,_=cut_at(t,version)
   img=render(sh,t,*size,letter=version)
   p.stdin.write(img.tobytes())
 finally:
  p.stdin.close()
 err=p.stderr.read().decode();r=p.wait()
 if r!=0:raise RuntimeError(f'ffmpeg failed {r}: {err[:700]}')
 return str(dest)

def test_dimensions(out):
 data=[]
 for version,cuts in [('A',CUTS_A),('B',CUTS_B)]:
  for i,(sh,s,e,camname) in enumerate(cuts):
   cam=b.camera(camname,(s+e)/2)
   entry={'version':version,'id':sh,'start':s,'end':e,'camera':camname,'XYZ_m':list(cam[0]),
       'yaw_deg':cam[1],'pitch_deg':cam[2],'focal_mm':cam[3],
       'camera_motion':camname in ('C','E-TELE'),'author_approved':False}
   if sh not in ('N01','N02','N07.5','N17'):
    for attr,t in [('start',s+.02),('end',e-.02)]:
     p=b.interp(t)[0];q=b.projection(p,b.camera(camname,t),1152,648)
     entry['whale_center_'+attr+'_xy_px']=list(map(lambda z:round(z,1),q[:2])) if q else None
   data.append(entry)
 z={'project':'D&D Ruosuen / 空に降る雪','version':'v12.5-B-19shot-vs-A-17shot',
    'author_approved':False,'A_shots':len(CUTS_A),'B_shots':len(CUTS_B),'A_duration_s':70,'B_duration_s':70,
    'single_shared_whale_path':True,'source':'main v12.4 frontend trajectory + v12.3 scene and 3D low-poly proxy',
    'warnings':['N04A large head is due to camera perspective; near collision not validated','N04B head may leave upper edge of frame','N07.5 explicitly excludes whale to test environmental insert','B N07 reduced to 1.45s; emotional relief may be too short','N16 tail disappearance and thick ceiling remain unverified','B adds 2 cuts but keeps 70-second provisional duration'],
    'cuts':data}
 (out/'camera-cut-manifest-v12.5.json').write_text(json.dumps(z,ensure_ascii=False,indent=2)+'\n')
 return z

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--out',default='./v12.5-out');parser.add_argument('--videos',action='store_true');parser.add_argument('--full',action='store_true')
 args=parser.parse_args();out=Path(args.out);(out/'keyframes').mkdir(parents=True,exist_ok=True)
 for sh,t in KEYFRAMES:
  target=out/'keyframes'/f'{sh}-{t:05.2f}s.png'
  render(sh,t).save(target,optimize=True)
 make_contact(out);make_map(out);manifest=test_dimensions(out)
 if args.videos:
  print('rendering A: 5.5-26.0s',flush=True)
  print(video(out,'A',5.5,26.0),flush=True)
  print('rendering B: 5.5-26.0s',flush=True)
  print(video(out,'B',5.5,26.0),flush=True)
 if args.full:
  print('rendering full B 70s 5fps',flush=True)
  print(video(out,'B',0,70,5),flush=True)
 print('DONE',len(KEYFRAMES),'frames',len(CUTS_A),len(CUTS_B),flush=True)

if __name__=='__main__':main()
