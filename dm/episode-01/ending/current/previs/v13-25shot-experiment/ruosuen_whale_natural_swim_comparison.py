#!/usr/bin/env python3
"""N14 natural baleen-whale locomotion study on UNMODIFIED v12.5 world.

4-way, same t=45..51, same parallel camera, shared white/gold S1 particles.
The first panel intentionally retains the prior lateral-wave toy animation as a
negative control. New candidates use primarily dorsoventral bending, horizontal
flukes and a nearly stable head, with optional glide / flipper adjustment.

Biomechanical inspiration: routine baleen whale fluking ~0.19-0.23 Hz
(Gough et al., 2019/2021). This is a visual previs, not physical simulation.
"""
import math, argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import render_19_vs_25_from_original as v13
import ruosuen_flower_snow_B_vs_B2 as b2

b=v13.b
orig=v13.original
START,END=45.,51.
STROKE_FREQ_HZ=0.215
FONT=ImageFont.truetype(b.FONTPATH,18)
SMALL=ImageFont.truetype(b.FONTPATH,13)
GROUND=tuple(b.MESH)
XMAX=max(float(p[0]) for tri in GROUND for p in tri[:3])
XMIN=min(float(p[0]) for tri in GROUND for p in tri[:3])
BASE_POSE=None


def clamp01(v): return min(1.,max(0.,float(v)))
def smooth(u):
    u=clamp01(u)
    return u*u*(3.-2.*u)

def install():
    probes=v13.make_unmodified_probes()
    v13.install_additive_cameras()
    v13.check_reproduction(probes)
    global BASE_POSE
    BASE_POSE=b.pose
    base_bg=b.gradient_bg
    cache={}
    def cached_bg(w,h):
        key=(w,h)
        if key not in cache:cache[key]=base_bg(w,h)
        return cache[key].copy()
    b.gradient_bg=cached_bg


def camera(t):
    # Same fixed relationship as approved comparison candidate ②; camera is
    # calculated from the ORIGINAL spline, never from tail strokes or roll.
    cp,f,side,up=BASE_POSE(t)
    world_up=np.array([0.,0.,1.])
    horizontal_side=np.cross(world_up,f)
    if np.linalg.norm(horizontal_side)<1e-6:horizontal_side=side
    horizontal_side/=np.linalg.norm(horizontal_side)
    pos=cp-15.*f+43.*horizontal_side+8.5*world_up
    target=cp+1.3*up
    d=target-pos
    yaw=math.degrees(math.atan2(d[0],d[1]))
    pitch=math.degrees(math.atan2(d[2],math.hypot(d[0],d[1])))
    return (tuple(float(a) for a in pos),yaw,pitch,39.)


def previous_fishlike(p,t,kind):
    # original liked 'air swimming', intentionally left as old comparison
    x,y,z=map(float,p)
    u=clamp01((x-XMIN)/(XMAX-XMIN))
    tail=(1.-u)
    amp=1.35*(tail**1.8)
    ph=2.25*math.pi*(t-START)+tail*3.1
    y+=amp*.75*math.sin(ph)
    z+=amp*.22*math.cos(ph+.5)
    z+=.12*math.sin(math.pi*(t-START)/6.)*max(0.,u-.45)
    return np.array([x,y,z])


def stroke_envelope(t,typ):
    if typ in ('vertical','flipper'):return 1.
    # One energetic tail stroke → reduced power during long glide.
    # Avoid hard transitions and keep a low-amplitude tail motion even in glide.
    fade=smooth((t-47.15)/.85)
    return 1.-.88*fade


def centerline_z(x,t,typ):
    # Head at +X is mostly steady; tail at -X bends vertically.
    tail=clamp01((6.0-x)/(6.0-XMIN))
    weight=tail**1.85
    phase=2*math.pi*STROKE_FREQ_HZ*(t-START)-1.0*tail+0.15
    amplitude=1.95 if typ in ('vertical','flipper') else 2.1
    return amplitude*weight*stroke_envelope(t,typ)*math.sin(phase)


def natural_deform(p,t,kind,typ):
    x,y,z=map(float,p)
    # Curved spine centerline with phase delay from shoulder to tail.
    base_z=centerline_z(x,t,typ)
    dx=.06
    grad=(centerline_z(x+dx,t,typ)-centerline_z(x-dx,t,typ))/(2*dx)
    theta=math.atan(grad)
    # Rotate local section around Y so cross section follows spine bend.
    xp=x-z*math.sin(theta)
    zp=base_z+z*math.cos(theta)
    yp=y
    tail=clamp01((6.-x)/(6.-XMIN))
    phase=2*math.pi*STROKE_FREQ_HZ*(t-START)-1.0*tail+0.15
    if kind=='tail':
        # Small tail-fluke angle of attack; fluke is a nearly rigid horizontal foil.
        # Pivot around the tail stock x=-11.1, z=0.
        pivot=-11.1
        alpha=math.radians(10.0*stroke_envelope(t,typ)*math.cos(phase-.42))
        ddx=xp-pivot
        ddz=zp-centerline_z(pivot,t,typ)
        xp=pivot+ddx*math.cos(alpha)-ddz*math.sin(alpha)
        zp=centerline_z(pivot,t,typ)+ddx*math.sin(alpha)+ddz*math.cos(alpha)
    if kind=='fin':
        # Pectoral fins stabilize rather than flap symmetrically like bird wings.
        blade=clamp01((abs(y)-1.9)/5.6)
        slow=.33*math.sin(2*math.pi*.13*(t-START)+(.6 if y>0 else -0.45))
        if typ=='flipper':slow*=1.55
        zp+=blade*slow
    return np.array([xp,yp,zp])


def make_whale(t,typ):
    cp,f,side,up=BASE_POSE(t)
    items=[]
    for a,bp,c,kind in GROUND:
        vertices=[]
        for p in (a,bp,c):
            q=previous_fishlike(p,t,kind) if typ=='old' else natural_deform(p,t,kind,typ)
            vertices.append(cp+f*q[0]+side*q[1]+up*q[2])
        n=b.unit(np.cross(vertices[1]-vertices[0],vertices[2]-vertices[0]))
        lam=.66+.24*abs(float(np.dot(n,np.array([.27,.20,.94]))))
        meanx=(a[0]+bp[0]+c[0])/3
        on=b.clamp((t-21.17-(12-meanx)*.13)/1.3)
        col0={'body':(88,112,132),'fin':(79,112,128),'tail':(82,115,130),'dorsal':(70,97,111)}[kind]
        dest=(179,203,215) if kind=='body' else (147,193,201)
        col=tuple(int(b.clamp(col0[i]*lam*(1-on)+dest[i]*on*(.85+.12*lam),0,255)) for i in range(3))
        items.append((vertices,col,1))
    return items


def render_variant(t,typ,size=(640,360)):
    old_whale=b.whale_items
    old_camera=b.camera
    c=camera(t)
    try:
        b.whale_items=lambda tt:make_whale(tt,typ)
        b.camera=lambda name,tt: c if name=='E-TELE' and START<=tt<=END else old_camera(name,tt)
        image=orig.render('N14',t,size[0],size[1],letter=None)
    finally:
        b.whale_items=old_whale
        b.camera=old_camera
    image=b2.overlay_luminous_whale(image,c,t,'N14',strong=True)
    b2.draw_petals(image,c,t,'N14',mode='B2')
    return image

VARIANTS=[
    ('old','旧・左右の揺れ'),
    ('vertical','上下ストローク'),
    ('glide','ひと泳ぎ→滑空'),
    ('flipper','上下＋胸びれ調整'),
]

def frame(t):
    out=Image.new('RGB',(1280,720),(8,14,22))
    d=ImageDraw.Draw(out)
    coords=[(0,0),(640,0),(0,360),(640,360)]
    for (typ,label),(x,y) in zip(VARIANTS,coords):
        im=render_variant(t,typ)
        out.paste(im,(x,y))
        d.rounded_rectangle((x+6,y+49,x+238,y+78),radius=6,fill=(9,19,28))
        d.text((x+16,y+53),label,font=FONT,fill=(240,227,190) if typ!='old' else (209,217,227))
        d.rectangle((x,y,x+639,y+359),outline=(115,129,139),width=1)
    d.line((640,0,640,720),fill=(139,151,159),width=2)
    d.line((0,360,1280,360),fill=(139,151,159),width=2)
    # unobtrusive time marker
    d.rounded_rectangle((525,688,754,712),radius=6,fill=(10,20,29))
    d.text((548,692),f'N14 | {t:05.2f}s | 0.215Hz',font=SMALL,fill=(222,230,236))
    return out


def contact(out):
    ts=[45.,46.0,47.0,48.0,49.2,50.4]
    sheet=Image.new('RGB',(960,540*len(ts)),(8,14,22))
    for i,t in enumerate(ts):
        img=frame(t).resize((960,540),Image.Resampling.LANCZOS)
        sheet.paste(img,(0,i*540))
    sheet.save(out/'natural_whale_swim_contact.png')


def video(path,start,end,fps):
    cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720',
         '-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','24',
         '-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i in range(int(round((end-start)*fps))):
            tt=start+i/fps
            proc.stdin.write(frame(tt).tobytes())
            if i%8==0:print('frame',i,'t',tt,flush=True)
    finally:
        proc.stdin.close()
    err=proc.stderr.read().decode(errors='replace')
    if proc.wait():raise RuntimeError(err[-1400:])


def diagnostics():
    samples=[]
    for t in [45.,46.,47.,48.,49.,50.,50.875]:
        entries={}
        for typ,label in VARIANTS:
            q=natural_deform([-11.1,0.,0.],t,'body',typ) if typ!='old' else previous_fishlike([-11.1,0.,0.],t,'body')
            entries[typ]={'tail_center_xyz_local':[round(float(a),3) for a in q]}
        samples.append({'world_time_s':t,'poses':entries})
    return samples

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='/mnt/data/ruosuen_natural_whale_swim')
    parser.add_argument('--fps',type=int,default=8)
    parser.add_argument('--contact-only',action='store_true')
    a=parser.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    install()
    contact(out)
    qa={'name':'N14 natural whale stroke redesign','source':'GitHub PR #39 unchanged original v12.5 + PR #41 camera/flower B2 lookdev',
        'author_approved':False,'baseline_frame_identity_passed':True,'duration_s':6,'fps':a.fps,
        'shared_conditions':'45-51 world seconds; original WH-01 proxy world path; side tracking camera position; S1 flower-snow',
        'science':'Baleen fluke oscillation largely dorsoventral, ~0.19 blue / 0.23 humpback Hz average in cited study',
        'stroke_frequency_hz':STROKE_FREQ_HZ,'tail_motion_samples':diagnostics(),
        'drawbacks':'synthetic bending of triangular proxy mesh, not full rig/skeleton; glide timing and biomechanical lift not physically simulated; 3D terrain clearance not re-validated; N13/N14.5 continuity not approved'}
    (out/'natural_whale_swim_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not a.contact_only:video(out/'natural_whale_swim_4way_45-51s.mp4',45.,51.,a.fps)

if __name__=='__main__':main()