#!/usr/bin/env python3
"""A/B: Original 25-shot timing vs longer whale-in-flower-snow climax.

World/geometry/whale path/cameras come unchanged from the GitHub PR#39
v12.5 renderer via PR#41 six-shot insert script. Both A and B share the
same enhanced flower and petal diagnostic overlay. Snow density / height
are visibility aids only, NOT final physical particle counts or airflow.
"""
from pathlib import Path
import argparse, math, random, json, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import render_19_vs_25_from_original as v13
base=v13.b

CUTS_A=list(v13.CUTS25)
CHANGES={
    "N09":(26.8,30.4), "N10":(30.4,35.8),
    "N10.5":(35.8,36.5), "N11":(36.5,38.0),
    "N12":(38.0,40.0), "N13":(40.0,45.0),
    "N14":(45.0,51.0)
}
CUTS_B=[(sh,*(CHANGES.get(sh,(s,e))),cam) for sh,s,e,cam in CUTS_A]
assert len(CUTS_A)==len(CUTS_B)==25
assert [q[0] for q in CUTS_A]==[q[0] for q in CUTS_B]
assert all(abs(CUTS_B[i][2]-CUTS_B[i+1][1])<1e-9 for i in range(24))
assert CUTS_B[0][1]==0 and CUTS_B[-1][2]==70
assert sum(e-s for sh,s,e,c in CUTS_B if sh in ("N13","N14"))==11.

rng=random.Random(2666)
BLOOMS=[]
for gx,gy,gz,label,start in base.S1:
    for j in range(170):
        dx=rng.uniform(-4.1,4.1);dy=rng.uniform(-4.9,4.9)
        opened=start+rng.uniform(-0.6,0.5)
        BLOOMS.append((gx+dx,gy+dy,gz+.08,opened,j))
rr=random.Random(1130)
SEED_VARIANTS=[]
for i in range(117):
    sub=[]
    for j in range(10):
        angle=rr.random()*2*math.pi
        radius=.18+rr.random()*1.6
        sub.append((radius*math.cos(angle),radius*math.sin(angle),
            rr.uniform(-.45,.45),rr.random()*2*math.pi,
            .5+rr.random()*1.3,rr.randrange(4)))
    SEED_VARIANTS.append(sub)
FONT=ImageFont.truetype(base.FONTPATH,18)
SMALL=ImageFont.truetype(base.FONTPATH,14)

def overlay_luminous_whale(img,cam,t,shot):
    if t<23.6 or shot not in {"N08.5","N09","N12","N13","N14","N14.5","N15"}:
        return img
    W,H=img.size
    p=base.projection(base.pose(t)[0],cam,W,H)
    if p is None:return img
    x,y,dep=p
    if not (-W*.5<x<W*1.5 and -H*.5<y<H*1.5):return img
    w=max(9,min(115,cam[3]/36*W*13/max(dep,1)))
    h=w*.47
    glow=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(glow)
    d.ellipse((x-w*1.3,y-h*1.7,x+w*1.3,y+h*1.7),fill=(253,238,178,25))
    d.ellipse((x-w,y-h,x+w,y+h),fill=(250,245,210,31))
    glow=glow.filter(ImageFilter.GaussianBlur(radius=max(3,int(min(w,18)))))
    return Image.alpha_composite(img.convert("RGBA"),glow).convert("RGB")

def draw_bloom(img,cam,t,shot):
    if shot not in {"N08.5","N09","N10","N10.5","N11","N12","N13"}:return
    W,H=img.size
    d=ImageDraw.Draw(img)
    for x,y,z,opened,i in BLOOMS:
        openness=max(0,min(1,(t-opened)/1.4))
        if openness<=0:continue
        q=base.projection((x,y,z),cam,W,H)
        if not q:continue
        px,py,dep=q
        if not (-5<px<W+5 and -5<py<H+5):continue
        physical_px=cam[3]/36*W*.0225/max(.1,dep)
        r=min(2.8,max(.8,physical_px*.9))
        r*=.5+.5*openness
        tint=(240,229,206) if i%5 else (231,220,180)
        if r<1.4:d.ellipse((px-r,py-r,px+r,py+r),fill=tint)
        else:
            for k in range(5):
                a=2*math.pi*k/5
                xx=px+math.cos(a)*r*.66; yy=py+math.sin(a)*r*.66
                d.ellipse((xx-r*.4,yy-r*.4,xx+r*.4,yy+r*.4),fill=tint)
            d.ellipse((px-.4,py-.4,px+.4,py+.4),fill=(190,170,117))

def draw_petals(img,cam,t,shot):
    if shot not in {"N11","N12","N13","N14","N14.5","N15"} or t<36.6:return
    W,H=img.size
    draw=ImageDraw.Draw(img,"RGBA")
    originals=base.seeds(t)
    for i,(p,color,radius) in enumerate(originals):
        x0,y0,z0=p
        for j,(dx,dy,dz,phase,speed,variant) in enumerate(SEED_VARIANTS[i]):
            spread=8.0 if i>=82 else (5.0 if i>=48 else 2.6)
            xx=x0+dx*spread+.42*math.sin(t*.27*speed+phase)
            yy=y0+dy*spread+.26*math.cos(t*.23*speed+phase)
            zz=z0+dz+.30*math.sin(t*.31+phase)
            if i>=82 and t>=43:
                zz+=min(100,(t-43)*13.0)*(.56+speed*.18)
            elif i>=48 and t>=39.4:
                zz+=min(76,(t-39.4)*8.5)*(.55+speed*.17)
            zz=min(184,zz)
            q=base.projection((xx,yy,zz),cam,W,H)
            if q is None:continue
            x,y,dep=q
            if not (-7<x<W+7 and -7<y<H+7):continue
            phys=cam[3]/36*W*radius/max(.1,dep)
            size=max(1.2,min(5.,1.5+phys*.9))
            phi=phase+t*(.85+speed*.15)
            vx,vy=math.cos(phi),math.sin(phi)
            nx,ny=-vy,vx
            col=(248,240,221,200) if variant!=0 else (239,225,178,205)
            draw.polygon([
                (x+vx*size*.90,y+vy*size*.90),
                (x+nx*size*.58,y+ny*size*.58),
                (x-vx*size*.55,y-vy*size*.55),
                (x-nx*size*.57,y-ny*size*.57)],fill=col)
            if size>2.5 and variant==0:
                draw.ellipse((x-.6,y-.6,x+.6,y+.6),fill=(234,210,146,135))

def enriched_frame(shot,t,size=(640,360)):
    W,H=size
    frame=v13.original.render(shot,t,W,H,letter=None)
    cname="INSERT_"+shot if shot in v13.EXPERIMENT_CAMERAS else next(s[4] for s in base.SHOTS if s[0]==shot)
    cam=base.camera(cname,t)
    frame=overlay_luminous_whale(frame,cam,t,shot)
    draw_bloom(frame,cam,t,shot)
    draw_petals(frame,cam,t,shot)
    return frame

def compare_frame(t):
    sa=v13.at(CUTS_A,t);sb=v13.at(CUTS_B,t)
    A=enriched_frame(sa,t);B=A if sa==sb else enriched_frame(sb,t)
    W,H=A.size
    frame=Image.new("RGB",(W*2,H+80),(9,17,26))
    frame.paste(A,(0,38));frame.paste(B,(W,38))
    d=ImageDraw.Draw(frame)
    d.rectangle((0,0,W*2,38),fill=(14,26,36))
    d.rectangle((0,H+38,W*2,H+80),fill=(14,26,36))
    d.line((W,0,W,H+80),fill=(142,152,146),width=2)
    d.text((14,8),"A  現行25カット：花を丁寧に見せる",font=FONT,fill=(229,229,214))
    d.text((W+14,8),"B  実験25カット：白鯨×花雪を長く",font=FONT,fill=(248,226,180))
    d.text((14,H+48),f"{t:05.2f}s  {sa}  /  花表現を両案同一条件で強化",font=SMALL,fill=(207,223,226))
    d.text((W+14,H+48),f"{t:05.2f}s  {sb}  /  既存鯨軌道・既存カメラ",font=SMALL,fill=(231,215,179))
    return frame

def video(out,start,end,fps=8):
    cmd=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
      "-s","1280x440","-r",str(fps),"-i","-","-an","-c:v","libx264",
      "-preset","veryfast","-crf","24","-pix_fmt","yuv420p",
      "-movflags","+faststart",str(out)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    for k in range(math.ceil((end-start)*fps)):
        t=start+k/fps
        proc.stdin.write(compare_frame(t).tobytes())
    proc.stdin.close()
    error=proc.stderr.read().decode(errors="replace")
    if proc.wait():raise RuntimeError("ffmpeg failed: "+error[-500:])

def contact(out):
    times=[26.4,29.2,33.8,37.8,39.2,41,43.2,46,49,50.5]
    sheet=Image.new("RGB",(720,247*len(times)),(8,13,21))
    for i,t in enumerate(times):
        frame=compare_frame(t).resize((720,247),Image.Resampling.LANCZOS)
        sheet.paste(frame,(0,i*247))
    sheet.save(out/"flower_showcase_comparison_contact.png")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="./flower-ab-render")
    p.add_argument("--fps",type=int,default=8)
    p.add_argument("--start",type=float,default=26.)
    p.add_argument("--end",type=float,default=54.)
    p.add_argument("--contact-only",action="store_true")
    p.add_argument("--no-contact",action="store_true")
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    original_probes=v13.make_unmodified_probes()
    v13.install_additive_cameras()
    # Source gradient RGB is a pure function of dimensions: copy cached pixels.
    orig_bg=base.gradient_bg;cache={}
    def cached_gradient(W,H):
        key=(W,H)
        if key not in cache:cache[key]=orig_bg(W,H)
        return cache[key].copy()
    base.gradient_bg=cached_gradient
    v13.check_reproduction(original_probes)
    assert len(BLOOMS)==len(base.S1)*170
    assert len(SEED_VARIANTS)==117
    if not a.no_contact:contact(out)
    if not a.contact_only:
        fn=out/f"compare_showcase_{a.start:g}-{a.end:g}s.mp4"
        video(fn,a.start,a.end,a.fps)
        print("WROTE",fn,flush=True)
    QA={
        "baseline":"Original GitHub PR #39 v12.5 code + PR #41 25-cut camera inserts",
        "A_whale_snow_seconds":8,"B_whale_snow_seconds":11,
        "B_timing":CHANGES,"shared_absolute_time_and_whale_pose":True,
        "enhancement":"same visual-only S1 flowers and loose airborne white-gold real-petal-plus-fruit proxies in both versions",
        "physical_note":"Flower proxy counts and vertical wind are NOT settled; no new wing, magic beam, or dolphin-style chase",
        "original_12_frame_byte_match":True,
        "approved_25cut_edit":False
    }
    (out/"flower_showcase_comparison_QA.json").write_text(json.dumps(QA,indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__":main()
