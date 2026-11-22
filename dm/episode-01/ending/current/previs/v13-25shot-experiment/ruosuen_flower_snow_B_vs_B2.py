#!/usr/bin/env python3
from pathlib import Path
import argparse, math, random, json, subprocess, sys
from contextlib import contextmanager
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import render_19_vs_25_from_original as v13
base=v13.b
original=v13.original

# use the already-liked B timing as the baseline for both sides
CUTS_B=[]
for sh,s,e,cam in v13.CUTS25:
    # these are the same timings used in the previous B proposal
    if sh=="N09": s,e=26.8,30.4
    elif sh=="N10": s,e=30.4,35.8
    elif sh=="N10.5": s,e=35.8,36.5
    elif sh=="N11": s,e=36.5,38.0
    elif sh=="N12": s,e=38.0,40.0
    elif sh=="N13": s,e=40.0,45.0
    elif sh=="N14": s,e=45.0,51.0
    CUTS_B.append((sh,s,e,cam))
assert all(abs(CUTS_B[i][2]-CUTS_B[i+1][1])<1e-9 for i in range(len(CUTS_B)-1))

FLOWER_SHOTS={'N08.5','N09','N10','N10.5','N11','N12','N13','N14','N14.5','N15'}
DRIFT_SHOTS={'N11','N12','N13','N14','N14.5','N15'}

FONT=ImageFont.truetype(base.FONTPATH,18)
SMALL=ImageFont.truetype(base.FONTPATH,14)

# Current B visual density
rng=random.Random(2666)
BLOOMS_B=[]
for gx,gy,gz,label,start in base.S1:
    for j in range(170):
        dx=rng.uniform(-4.1,4.1)
        dy=rng.uniform(-4.9,4.9)
        open_time=start+rng.uniform(-0.6,0.5)
        BLOOMS_B.append((gx+dx,gy+dy,gz+0.08,open_time,j))

# Refined B2 density: denser but still localized around existing S1 sites
rng2=random.Random(9311)
BLOOMS_B2=[]
for gx,gy,gz,label,start in base.S1:
    for j in range(250):
        dx=rng2.uniform(-4.6,4.6)
        dy=rng2.uniform(-5.4,5.4)
        open_time=start+rng2.uniform(-0.6,0.45)
        BLOOMS_B2.append((gx+dx,gy+dy,gz+0.08,open_time,j))

rr=random.Random(1130)
SEEDS_B=[]
for i in range(117):
    sub=[]
    for j in range(10):
        theta=rr.random()*2*math.pi
        rad=(0.18+rr.random()*1.6)
        sub.append((rad*math.cos(theta),rad*math.sin(theta),rr.uniform(-0.45,0.45), rr.random()*2*math.pi, 0.5+rr.random()*1.3, rr.randrange(4)))
    SEEDS_B.append(sub)

rr2=random.Random(7710)
SEEDS_B2=[]
for i in range(117):
    sub=[]
    for j in range(16):
        theta=rr2.random()*2*math.pi
        rad=(0.16+rr2.random()*2.1)
        sub.append((rad*math.cos(theta),rad*math.sin(theta),rr2.uniform(-0.6,0.6), rr2.random()*2*math.pi, 0.45+rr2.random()*1.45, rr2.randrange(5)))
    SEEDS_B2.append(sub)

# Refined B2 camera overrides only for the climax shots.
# Intent: hold the whale larger during the emotional peak, then allow shrinking near departure.
B2_CAM_OVERRIDES={
    'N13': ((-58.0,-84.0,4.1), 25.0, 29.0, 42.0),
    'N14': ((-56.0,-82.0,4.8), 24.0, 26.0, 110.0),
    # N15 intentionally not overridden: this is where the whale may begin to feel more distant.
}

@contextmanager
def b2_camera_context(shot):
    old_camera=base.camera
    def wrapped(name,t):
        if shot=='N13' and name=='E-WIDE':
            return B2_CAM_OVERRIDES['N13']
        if shot=='N14' and name=='E-TELE':
            return B2_CAM_OVERRIDES['N14']
        return old_camera(name,t)
    base.camera=wrapped
    try:
        yield
    finally:
        base.camera=old_camera


def overlay_luminous_whale(img,cam,t,shot,strong=False):
    if t<23.6 or shot not in {'N08.5','N09','N12','N13','N14','N14.5','N15'}:
        return img
    W,H=img.size
    cp,_,_,_=base.pose(t)
    p=base.projection(cp,cam,W,H)
    if p is None:
        return img
    x,y,depth=p
    if not (-W*.5<x<W*1.5 and -H*.5<y<H*1.5):
        return img
    w=max(9,min(125,cam[3]/36*W*13/max(depth,1)))
    h=w*.47
    glow=Image.new('RGBA',(W,H),(0,0,0,0))
    d=ImageDraw.Draw(glow)
    outer=(253,238,178,34 if strong else 25)
    inner=(250,245,210,42 if strong else 31)
    d.ellipse((x-w*1.35,y-h*1.75,x+w*1.35,y+h*1.75),fill=outer)
    d.ellipse((x-w,y-h,x+w,y+h),fill=inner)
    glow=glow.filter(ImageFilter.GaussianBlur(radius=max(3,int(min(w,20)))))
    return Image.alpha_composite(img.convert('RGBA'),glow).convert('RGB')


def draw_bloom(img,cam,t,shot,mode='B'):
    if shot not in {'N08.5','N09','N10','N10.5','N11','N12','N13'}:
        return
    W,H=img.size
    d=ImageDraw.Draw(img)
    blooms=BLOOMS_B if mode=='B' else BLOOMS_B2
    for x,y,z,opened,i in blooms:
        openness=max(0,min(1,(t-opened)/1.35))
        if openness<=0:
            continue
        q=base.projection((x,y,z),cam,W,H)
        if not q:
            continue
        px,py,dep=q
        if not (-6<px<W+6 and -6<py<H+6):
            continue
        true_r=cam[3]/36*W*.0225/max(.1,dep)
        floor=0.8 if mode=='B' else 0.95
        ceil=2.8 if mode=='B' else 3.1
        r=min(ceil,max(floor,true_r*(0.9 if mode=='B' else 1.0)))
        r*=0.48+0.52*openness
        tint=(240,229,206) if i%5 else (231,220,180)
        if r<1.4:
            d.ellipse((px-r,py-r,px+r,py+r),fill=tint)
        else:
            for k in range(5):
                a=2*math.pi*k/5
                xx=px+math.cos(a)*r*.66; yy=py+math.sin(a)*r*.66
                d.ellipse((xx-r*.4,yy-r*.4,xx+r*.4,yy+r*.4),fill=tint)
            d.ellipse((px-.45,py-.45,px+.45,py+.45),fill=(194,173,120))


def draw_petals(img,cam,t,shot,mode='B'):
    if shot not in DRIFT_SHOTS or t<36.6:
        return
    W,H=img.size
    dr=ImageDraw.Draw(img,'RGBA')
    originals=base.seeds(t)
    variants_all=SEEDS_B if mode=='B' else SEEDS_B2
    for i,(p,color,actual_radius) in enumerate(originals):
        x0,y0,z0=p
        for dx,dy,dz,phase,speed,variant in variants_all[i]:
            spread = 1.0 if mode=='B' else (1.22 if i<48 else 1.35)
            xx=x0+dx*spread+0.42*math.sin(t*.27*speed+phase)
            yy=y0+dy*spread+0.26*math.cos(t*.23*speed+phase)
            zz=z0+dz+0.30*math.sin(t*.31+phase)
            if i>=82 and t>=43.0:
                zz+=min(110.0,(t-43.0)*(13.0 if mode=='B' else 14.8))*(0.56+speed*.18)
            elif i>=48 and t>=39.4:
                zz+=min(84.0,(t-39.4)*(8.5 if mode=='B' else 9.6))*(0.55+speed*.17)
            zz=min(186.0 if mode=='B' else 196.0,zz)
            q=base.projection((xx,yy,zz),cam,W,H)
            if q is None:
                continue
            x,y,dep=q
            if not (-10<x<W+10 and -10<y<H+10):
                continue
            phys=cam[3]/36*W*actual_radius/max(.1,dep)
            size=max(1.2,min(5.0 if mode=='B' else 5.8,1.5+phys*(0.9 if mode=='B' else 1.0)))
            phi=phase+t*(0.85+speed*.15)
            vx=math.cos(phi); vy=math.sin(phi)
            nx=-vy; ny=vx
            colour=(248,240,221,200) if variant!=0 else (239,225,178,208)
            dr.polygon([(x+vx*size*.90,y+vy*size*.90),
                        (x+nx*size*.58,y+ny*size*.58),
                        (x-vx*size*.55,y-vy*size*.55),
                        (x-nx*size*.57,y-ny*size*.57)], fill=colour)
            if size>2.5 and variant==0:
                dr.ellipse((x-.6,y-.6,x+.6,y+.6),fill=(234,210,146,138))


def get_cam_for_shot(shot,t,mode='B'):
    if mode=='B2' and shot in B2_CAM_OVERRIDES:
        return B2_CAM_OVERRIDES[shot]
    camname=('INSERT_'+shot) if shot in v13.EXPERIMENT_CAMERAS else next((s[4] for s in base.SHOTS if s[0]==shot))
    return base.camera(camname,t)


def enriched_frame(shot,t,size=(640,360),mode='B'):
    W,H=size
    if mode=='B2' and shot in B2_CAM_OVERRIDES:
        with b2_camera_context(shot):
            frame=original.render(shot,t,W,H,letter=None)
    else:
        frame=original.render(shot,t,W,H,letter=None)
    cam=get_cam_for_shot(shot,t,mode)
    frame=overlay_luminous_whale(frame,cam,t,shot,strong=(mode=='B2' and shot in {'N13','N14'}))
    draw_bloom(frame,cam,t,shot,mode)
    draw_petals(frame,cam,t,shot,mode)
    return frame


def at(cuts,t):
    return v13.at(cuts,t)


def compare_frame(t):
    shot=at(CUTS_B,t)
    left=enriched_frame(shot,t,mode='B')
    right=enriched_frame(shot,t,mode='B2')
    W,H=left.size
    out=Image.new('RGB',(W*2,H+80),(9,17,26))
    out.paste(left,(0,38)); out.paste(right,(W,38))
    dr=ImageDraw.Draw(out)
    dr.rectangle((0,0,W*2,38),fill=(14,26,36))
    dr.rectangle((0,H+38,W*2,H+80),fill=(14,26,36))
    dr.line((W,0,W,H+80),fill=(142,152,146),width=2)
    dr.text((14,8),'B  現行見せ場案：花雪と白鯨を長く',font=FONT,fill=(229,229,214))
    dr.text((W+14,8),'B2 改良案：花雪密度↑ / 白鯨を大きく',font=FONT,fill=(248,226,180))
    dr.text((14,H+48),f'{t:05.2f}s  {shot}  /  前回B案',font=SMALL,fill=(207,223,226))
    dr.text((W+14,H+48),f'{t:05.2f}s  {shot}  /  退場感はN15へ後ろ倒し',font=SMALL,fill=(231,215,179))
    return out


def write_video(path,start,end,fps=8):
    cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
         '-s','1280x440','-r',str(fps),'-i','-','-an','-c:v','libx264',
         '-preset','veryfast','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    total=math.ceil((end-start)*fps)
    try:
        for k in range(total):
            t=start+k/fps
            proc.stdin.write(compare_frame(t).tobytes())
            if k%32==0:
                print(f'frame {k}/{total} t={t:.2f}',flush=True)
    finally:
        proc.stdin.close()
    err=proc.stderr.read().decode(errors='replace')
    rc=proc.wait()
    if rc!=0:
        raise RuntimeError(f'ffmpeg rc={rc}: {err[-1200:]}')


def contact_sheet(out):
    times=[30.4,33.8,38.0,40.0,41.2,43.2,45.0,47.0,49.0,50.5,52.0]
    w=720; h=247
    sheet=Image.new('RGB',(w,h*len(times)),(8,13,21))
    for i,t in enumerate(times):
        img=compare_frame(t).resize((w,h),Image.Resampling.LANCZOS)
        sheet.paste(img,(0,i*h))
    path=out/'B_vs_B2_contact.png'
    sheet.save(path)
    return path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',default='/mnt/data/ruosuen_showcase_b2')
    ap.add_argument('--fps',type=int,default=8)
    ap.add_argument('--start',type=float,default=26.0)
    ap.add_argument('--end',type=float,default=54.0)
    ap.add_argument('--contact-only',action='store_true')
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    probes=v13.make_unmodified_probes()
    v13.install_additive_cameras()
    v13.check_reproduction(probes)
    # cache immutable gradient backgrounds for speed
    orig_bg=base.gradient_bg; cache={}
    def cached_bg(W,H):
        key=(W,H)
        if key not in cache:
            cache[key]=orig_bg(W,H)
        return cache[key].copy()
    base.gradient_bg=cached_bg
    contact_sheet(out)
    qa={
        'baseline':'Prior B timing retained for both sides',
        'comparison':'Left=current B, right=refined B2',
        'B_climax_seconds':11,
        'B2_climax_seconds':11,
        'B2_changes':{
            'flower_density':'more bloom markers around existing S1 anchors; denser petal snow readability only',
            'whale_scale':'N13/N14 cameras adjusted to show whale larger',
            'departure_feel':'N15 left unmodified so whale begins to recede later',
        },
        'same_absolute_time':True,
        'same_whale_path':True,
        'same_world_geometry':True,
        'note':'density and petal layering are previs visibility aids, not final physical particle counts'
    }
    (out/'B_vs_B2_QA.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    if not args.contact_only:
        write_video(out/'ruosuen_B_vs_B2_flower_snow_26-54s.mp4',args.start,args.end,args.fps)

if __name__=='__main__':
    main()