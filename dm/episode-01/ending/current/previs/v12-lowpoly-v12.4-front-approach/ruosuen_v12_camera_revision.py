#!/usr/bin/env python3
"""v12.3 candidate film-continuity delta on top of the immutable v12.2 proxy.

Run: python ruosuen_v12_camera_revision.py --out /some/dir
Requires: numpy, Pillow and ruosuen_story_previs.py beside this script.
All revised camera coordinates/focal lengths are NON-APPROVED camera tests.
"""
import argparse, json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import ruosuen_story_previs as base

# Fix source interpolation discontinuity before trying to judge camera action.
# Continuity working samples; physically accurate splash / angular motions not yet modeled.
base.STATIONS=[
 (4.5,-90,27,-9),(5.8,-90,19,-9),(6.5,-90,15,-8),
 (7.5,-90,5,-5),(8.2,-90,-3,0),(9.0,-90,-12,3),
 (10.5,-90,-25,14),
] + [s for s in base.STATIONS if s[0]>10.5]
original_camera=base.camera

def smoothstep(x):
 x=base.clamp(x);return x*x*(3-2*x)

def camera(name,t):
 c=original_camera(name,t)
 if name=='APPROACH': return ((-58,-84,4.1),-43,20,28)
 if name=='BEHIND': return ((-58,-84,4.1),106,38,16)
 if name=='C':
  # Different ground-side angle deliberately introduced via moonlit *environment* not a whale match cut.
  p=smoothstep((t-20.85)/4.7)
  return ((-7,-145,6.0),-14+15*p,26,18)
 if name=='D':return ((29.0,-66.0,4.5),28,2,55)
 if name=='FLOWERWIDE':return ((26,-62,12),30,-5,26)
 if name=='E-TELE':return ((-58,-84,4.1),25,25+1.5*smoothstep((t-47)/4),95)
 if name=='ASCENT':return ((-58,-84,4.1),25,26,35)
 if name=='F':return ((-10,-108,5),0,28,50)
 return c
base.camera=camera

# Extra frames deliberately include a frame close to the outgoing and incoming cuts.
base.EXTRA={
 'N03':[6.2], 'N04':[8.0,9.0,10.3], 'N05':[11.2,12.5,13.9],
 'N06':[14.5,15.5,16.5,17.8],
 'N07':[18.2,19.2,20.2],
 'N08':[20.55,21.4,23.2,25.5],
 'N09':[26.5,28.2], 'N10':[32.0,35.9],
 'N14':[47.2,50.6], 'N15':[51.1,54.4,57.2],
 'N16':[58.0,62.0,63.8]}

# Use an understated hole marker rather than a bright giant infographic shape.
def roof(img,cam,shot,t):
 W,H=img.size;d=ImageDraw.Draw(img)
 p=[base.projection(x,cam,W,H) for x in base.fissure_path()]
 p=[(v[0],v[1]) for v in p if v]
 if len(p)>=3:
  if shot in ('N08','N15','N16'):
   fill=(29,49,63);edge=(72,100,113)
  else:
   fill=(18,31,43);edge=(40,62,74)
  d.polygon(p,fill=fill)
  d.line(p+[p[0]],fill=edge,width=2)
 # Moon is suppressed for all incidental shots and remains tiny when geometrically in opening.
 if shot in ('N01','N08','N15','N16','N17') and base.moon_visible(cam):
  direction=base.N([0,math.cos(math.radians(43.01)),math.sin(math.radians(43.01))]);qq=base.projection(base.N(cam[0])+direction*1000,cam,W,H)
  if qq:
   x,y,_=qq
   d.ellipse((x-3,y-3,x+3,y+3),fill=(230,224,190))
base.draw_roof_and_moon=roof

# Visible flowering wave in the storyboard is a *diagnostic overlay*; physical flowers keep their 4.5-cm size.
original_draw_diagnostic=base.draw_diagnostic

def diagnostic(img,cam,shot,t):
 original_draw_diagnostic(img,cam,shot,t)
 if shot=='N09':
  W,H=img.size;d=ImageDraw.Draw(img)
  # Upper-right amber glow indicates offscreen whale source; not an invented directional beam.
  d.rounded_rectangle((W-342,14,W-20,80),radius=10,fill=(20,31,38),outline=(91,100,85),width=2)
  d.text((W-325,29),'S1 BASE · LIGHT REACTION',fill=(237,221,170),font=base.FONTS)
 elif shot=='N10':
  W,H=img.size;d=ImageDraw.Draw(img)
  for x,y,z,label,on in base.S1:
   q=base.projection((x,y,z+.25),cam,W,H)
   if not q:continue
   px,py,dep=q
   if not (-50<px<W+50 and -50<py<H+50):continue
   active=t>=on
   # Radius is the patch extent, not a flower size; explicit overlay only.
   rr=max(7,min(22,500/max(5,dep)))
   c=(236,219,160) if active else (107,128,136)
   d.ellipse((px-rr,py-rr,px+rr,py+rr),outline=c,width=2)
  text='BASE → TIP   '+('TIP: CLOSED' if t<35.7 else 'TIP: OPEN')
  d.rounded_rectangle((530,13,1110,72),radius=10,fill=(14,30,39),outline=(90,98,79))
  d.text((552,30),text,font=base.FONTS,fill=(240,222,165))
base.draw_diagnostic=diagnostic

# N11 : five total petals: four attached and one detaching, each 4.5cm scale flower proxy.
def corrected_macro(img,cam):
 W,H=img.size;d=ImageDraw.Draw(img);center=base.N([72,8,3.08])
 for i in range(4):
  a=2*base.PI*i/5
  rad=base.N([math.cos(a),math.sin(a),0]);s=base.N([-math.sin(a),math.cos(a),0])
  vv=[center+rad*.007+s*(-.009),center+rad*.026+s*(-.010),center+rad*.030+s*.002,center+rad*.025+s*.010,center+rad*.007+s*.009]
  qs=[base.projection(x,cam,W,H) for x in vv]
  if all(qs):
   ps=[(q[0],q[1]) for q in qs]
   d.polygon(ps,fill=(236,227,209));d.line(ps+[ps[0]],fill=(184,179,159),width=2)
 # fifth petal, physically displaced with attached tiny fruit
 off=base.N([.052,.043,.013]);q=base.projection(center+off,cam,W,H)
 if q:
  x,y,_=q
  d.polygon([(x-13,y+4),(x-10,y-7),(x+4,y-16),(x+9,y-11),(x+7,y+5)],fill=(247,234,203))
  d.ellipse((x-13,y+2,x-8,y+7),fill=(231,212,140))
base.draw_macro=corrected_macro

# Blooming groups: dense physical micro-flower proxy, with diagnostic rings above.
orig_site=base.site_items

def site(t,shot):
 dots=orig_site(t,shot)
 # More flower positions on each mature patch, retain metric physical radius.
 import random
 rng=random.Random(3742)
 for x,y,z,label,start in base.S1:
  for j in range(310):
   xx=x+rng.uniform(-3.9,3.9);yy=y+rng.uniform(-4.8,4.8)
   opening=t>=start+rng.uniform(-0.6,.6)
   dots.append(((xx,yy,z+.075),(237,227,206) if opening else (80,78,65),.0225))
 return dots
base.site_items=site

# Preserve physical scene and camera values in separate manifest for author review.
def make_revision(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 records=[];imgs=[]
 for sid,start,end,title,name,t in base.SHOTS:
  times=base.EXTRA.get(sid,[t])
  for j,tm in enumerate(times):
   fname=f'{sid}-{j+1:02d}-{tm:05.2f}s.png';f=out/fname
   record=base.render_one(sid,tm,f);record['status']='PROVISIONAL: no author camera approval';record['changes']='camera continuity v12.3 comparison';records.append(record);imgs.append(f)
 base.make_contact(imgs,out/'contact-sheet-v12.3.png')
 (out/'frames-v12.3.json').write_text(json.dumps({'version':'v12.3-CAMERA-REVIEW-CANDIDATE','date':'2026-11-22','fps':'keyframe stills only','source':'v12 author provisional + v12.1 timing candidate; adapted v12.2 proxy; not WH-01','frames':records},ensure_ascii=False,indent=2))
 print('frames',len(imgs))
 return records

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',default='/mnt/data/ruosuen_v12_3_camera_previs');args=ap.parse_args();make_revision(args.out)
