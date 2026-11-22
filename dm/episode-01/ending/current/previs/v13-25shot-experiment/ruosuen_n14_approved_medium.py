#!/usr/bin/env python3
"""Approved N14 (45–51s) side-follow whale size and natural stroke→glide.

NON-DESTRUCTIVE: imports canonical v12.5 world/whale proxy without changing
source files; does not alter 19-cut timing. The approved decision is limited to
N14's motion direction/acting and 'slightly larger' framing, not 25-cut lock.
"""
from pathlib import Path
import argparse, json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import ruosuen_whale_natural_swim_comparison as nat

b=nat.b
orig=nat.orig
START,END=45.,51.
# Camera: (behind the whale, horizontal offset, elevation, lens equivalent)
CAMERAS={
    'baseline':(-15.0,43.0,8.5,39.0),
    'approved_medium':(-12.5,37.5,7.8,41.0),
    'large_alternative':(-10.5,32.5,7.0,43.0),
}
WORLD_UP=np.array([0.,0.,1.])
FONT=ImageFont.truetype(b.FONTPATH,19)
SMALL=ImageFont.truetype(b.FONTPATH,14)


def camera(t,style='approved_medium'):
    back,horizontal,elevation,lens=CAMERAS[style]
    cp,f,side,up=nat.BASE_POSE(t)
    hside=np.cross(WORLD_UP,f)
    if np.linalg.norm(hside)<1e-6:hside=side
    hside=hside/np.linalg.norm(hside)
    position=cp+back*f+horizontal*hside+elevation*WORLD_UP
    target=cp+1.2*up
    d=target-position
    yaw=math.degrees(math.atan2(d[0],d[1]))
    pitch=math.degrees(math.atan2(d[2],math.hypot(d[0],d[1])))
    return tuple(float(v) for v in position),yaw,pitch,lens


def render(t,style='approved_medium',size=(1280,720)):
    current_camera=b.camera
    current_whale=b.whale_items
    selected_cam=camera(t,style)
    try:
        # Current WH-01 geometry, original shared world trajectory, new acting only.
        b.whale_items=lambda tt:nat.make_whale(tt,'glide')
        b.camera=lambda name,tt:selected_cam if name=='E-TELE' and START<=tt<=END else current_camera(name,tt)
        frame=orig.render('N14',t,size[0],size[1],letter=None)
    finally:
        b.camera=current_camera
        b.whale_items=current_whale
    frame=nat.b2.overlay_luminous_whale(frame,selected_cam,t,'N14',strong=True)
    nat.b2.draw_petals(frame,selected_cam,t,'N14',mode='B2')
    return frame


def compared(t):
    out=Image.new('RGB',(1280,720),(8,14,22))
    d=ImageDraw.Draw(out)
    d.rounded_rectangle((240,16,1040,52),radius=8,fill=(10,21,31))
    d.text((259,23),'N14 自然な泳ぎ：鯨の画角3案／中央を採用',font=FONT,fill=(240,239,225))
    cases=[('baseline','旧サイズ'),('approved_medium','採用：少し大きい'),('large_alternative','大きい比較案')]
    for i,(style,title) in enumerate(cases):
        x=12+i*423
        out.paste(render(t,style,(410,410)),(x,128))
        d.rectangle((x,128,x+409,537),outline=(127,146,157),width=1)
        d.rounded_rectangle((x+8,89,x+225,119),radius=6,fill=(10,22,33))
        d.text((x+16,95),title,font=FONT,fill=(247,222,155) if i==1 else (216,227,234))
    d.rounded_rectangle((437,678,843,708),radius=7,fill=(10,22,33))
    d.text((450,687),f'{t:05.2f}s | 同じ上下ストローク→滑空・同じ花雪',font=SMALL,fill=(218,224,232))
    return out


def write_movie(path,frames,fps):
    it=iter(frames)
    first=next(it)
    width,height=first.size
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
         '-s',f'{width}x{height}','-r',str(fps),'-i','-','-an','-c:v','libx264',
         '-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        proc.stdin.write(first.tobytes())
        for im in it:proc.stdin.write(im.tobytes())
    finally:proc.stdin.close()
    error=proc.stderr.read().decode(errors='replace')
    if proc.wait()!=0:raise RuntimeError(error[-1000:])


def info(path):
    j=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
        '-show_entries','stream=width,height,nb_frames,r_frame_rate,duration','-of','json',str(path)]))
    return j['streams'][0]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='rendered-approved-N14')
    parser.add_argument('--fps',type=int,default=8)
    parser.add_argument('--stills-only',action='store_true')
    args=parser.parse_args()
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    nat.install()
    render(48.,'approved_medium').save(out/'N14-natural-glide-approved-medium-48s.png')
    compared(48.).save(out/'N14-size-comparison-48s.png')
    if not args.stills_only:
        ts=[START+i/args.fps for i in range(int(round((END-START)*args.fps)))]
        write_movie(out/'N14-natural-glide-approved-medium-45-51s.mp4',(render(t) for t in ts),args.fps)
        write_movie(out/'N14-size-comparison-45-51s.mp4',(compared(t) for t in ts),args.fps)
    clips={p.name:info(p) for p in out.glob('*.mp4')}
    for p,v in clips.items():
        assert v['width']==1280 and v['height']==720 and v['r_frame_rate']==f'{args.fps}/1'
        assert int(v['nb_frames'])==int(round(6*args.fps))
        assert abs(float(v['duration'])-6)<0.01
    qa={
        'context':'DM episode-01 ending N14, original v12.5 world imported, 19-cut source untouched',
        'author_approved_on_2026_11_22':{
            'acting':'baleen-like dorsoventral tail strokes, single stroke followed by glide',
            'camera':'side-follow ②','size':'slightly larger / 少し大きい',
            'absolute_time_s':[START,END]},
        'approved_camera_params_relative_m':CAMERAS['approved_medium'],
        'rendered_motion':'glide variant from ruosuen_whale_natural_swim_comparison.py',
        'visual_snow':'B2 from ruosuen_flower_snow_B_vs_B2.py',
        'fps':args.fps,'video_streams':clips,
        'status':'previs locked for N14 framing and acting only; not final storyboard/camera lens calibration'}
    (out/'N14-approved-medium-QA.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('PASS N14 approved-medium camera and natural stroke→glide; original v12.5 untouched',flush=True)

if __name__=='__main__':main()