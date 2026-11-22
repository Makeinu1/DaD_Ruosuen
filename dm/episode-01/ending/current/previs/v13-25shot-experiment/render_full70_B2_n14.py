#!/usr/bin/env python3
"""70-second visual-only lowpoly previs.

v12.5 original cave/whale path, v13 25-shot provisional B edit,
B2 white-gold S1 flower snow, author's N14 approved natural stroke-and-glide
and "slightly larger" side-follow camera. Never mutate v12.5 source files.
"""
from pathlib import Path
import argparse
import json
import math
import subprocess

from PIL import Image, ImageDraw, ImageFont
import ruosuen_whale_natural_swim_comparison as natural
import ruosuen_flower_snow_B_vs_B2 as b2
import ruosuen_n14_approved_medium as approved

CUTS = list(b2.CUTS_B)
assert len(CUTS) == 25
assert CUTS[0][1] == 0 and CUTS[-1][2] == 70
assert next((s,e) for shot,s,e,_ in CUTS if shot == 'N14') == (45.0,51.0)
assert all(abs(CUTS[i][2]-CUTS[i+1][1]) < 1e-7 for i in range(24))

def cut_at(t):
    return natural.v13.at(CUTS,t)

def draw(t, size):
    shot = cut_at(t)
    if shot == 'N14':
        return approved.render(t, 'approved_medium', size)
    return b2.enriched_frame(shot, t, size=size, mode='B2')

def write_video(path, fps, size):
    n = 70*fps
    cmd = ['ffmpeg','-y','-hide_banner','-loglevel','error',
           '-f','rawvideo','-pix_fmt','rgb24',
           '-s',f'{size[0]}x{size[1]}','-r',str(fps),'-i','-',
           '-an','-c:v','libx264','-preset','veryfast','-crf','23',
           '-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
    p = subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for frame in range(n):
            t=frame/fps
            p.stdin.write(draw(t,size).tobytes())
            if frame % (8*3) == 0:
                print(f'RENDER {frame:03d}/{n}  {t:05.2f}s  {cut_at(t)}',flush=True)
    finally:
        p.stdin.close()
    error=p.stderr.read().decode(errors='replace')
    if p.wait(): raise RuntimeError(error[-1500:])

def contact_sheet(out):
    moments = [1.5,4.,6.5,8.4,9.6,10.7,12.,13.5,16.,18.8,19.9,
               23.5,26.4,29.1,33.,36.1,37.1,39.,41.5,45.5,48.,
               50.5,51.4,54.,57.,60.,66.,69.]
    W,H=400,225; pad=10; footer=26; cols=4
    rows=math.ceil(len(moments)/cols)
    sheet=Image.new('RGB',(cols*(W+pad)+pad,rows*(H+footer+pad)+pad),(8,15,25))
    pen=ImageDraw.Draw(sheet)
    font=ImageFont.truetype(natural.b.FONTPATH,17)
    for i,t in enumerate(moments):
        thumbnail=draw(t,(640,360)).resize((W,H),Image.Resampling.LANCZOS)
        x=pad+(i%cols)*(W+pad); y=pad+(i//cols)*(H+footer+pad)
        sheet.paste(thumbnail,(x,y))
        tag=f'{t:05.2f}s  {cut_at(t)}'+('  N14 approved' if cut_at(t)=='N14' else '')
        pen.text((x+4,y+H+2),tag,font=font,fill=(241,225,192) if cut_at(t)=='N14' else (222,232,239))
    sheet.save(out/'full70-28timepoints.png',optimize=True)

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument('--out',type=Path,default=Path('artifacts/full70-B2-N14'))
    pa.add_argument('--fps',type=int,default=8)
    args=pa.parse_args()
    assert args.fps>0
    args.out.mkdir(parents=True,exist_ok=True)
    natural.install()  # 12 original v12.5 frames byte-identical before/after.
    contact_sheet(args.out)
    movie=args.out/'full70-B2-N14-approved-medium-1280x720-8fps.mp4'
    write_video(movie,args.fps,(1280,720))
    p=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
        '-show_entries','stream=nb_frames,width,height,duration,r_frame_rate','-of','json',str(movie)]))['streams'][0]
    assert int(p['nb_frames'])==70*args.fps
    assert p['width']==1280 and p['height']==720
    assert abs(float(p['duration'])-70)<.01
    assert p['r_frame_rate']==f'{args.fps}/1'
    qa={
        'name':'空に降る雪 full70 lowpoly previs',
        'source':'GitHub main v12.5 original + merged PR #41 experimental sources',
        'duration_s':70,'frames':70*args.fps,'fps':args.fps,
        'screen':[1280,720],'cut_count':25,'storyboard_approved_25cut':False,
        'source_whale_path_unchanged':True,
        'timeline':'provisional B: N13 40-45s / N14 45-51s',
        'N14_author_approved':{'camera':'side-follow ②','size':'slightly larger',
            'acting':'natural vertical fluke stroke then glide','time_s':[45,51]},
        'flower_snow':'B2 white/gold, visualization-only unapproved particle density',
        'soundtrack':'none','original_v12_5_12_probes_unchanged':True,
        'unresolved':['N13 to N14 to N14.5 camera continuity',
                      'N06 PC proximity','N08 occlusion','N16 whole-tail exit'],
        'video':p,
    }
    (args.out/'full70-B2-N14-QA.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('PASS 70s MP4 / 560 frames / original v12.5 preserved',flush=True)

if __name__ == '__main__':
    main()
