#!/usr/bin/env python3
"""Render 6-fps low-poly scene-only animatic comparisons (no invented motion)."""
import subprocess, math, argparse
from pathlib import Path
import ruosuen_v125_supplementary as v
from PIL import Image
b=v.b
# v12.3 baseline N04 is left unmodified and old N07 lasts until 20.5.
b.SHOTS.append(('N04',7.5,11,'従来の浮上','BREACH',9.0))
segments=[('breach',5.5,18.0),('moon',18.0,26.0)]
FPS=6

def shot_for(t,segment,version):
    if segment=='breach':
        if t<7.5:return 'N03'
        if t<11:return 'N04' if version=='baseline17' else ('N04A' if t<8.1 else 'N04B')
        if t<14:return 'N05'
        return 'N06'
    if t<20.5:
        if version=='baseline17' or t<19.55:return 'N07'
        return 'N07.5'
    return 'N08'

def render_segment(dest,seg,start,end,version):
    tmp=dest/'tmp'/f'{seg}-{version}'
    tmp.mkdir(parents=True,exist_ok=True)
    for n in range(round((end-start)*FPS)):
        t=start+(n+0.5)/FPS
        shot=shot_for(t,seg,version)
        src=tmp/f'{n:04d}.png'
        v.render(shot,t,src)
        # Lossless initial geometry can be downscaled at encode; keep source PNG in tmp only.
    target=dest/f'animatic-{seg}-{version}-6fps.mp4'
    subprocess.run(['ffmpeg','-loglevel','error','-y','-framerate',str(FPS),'-i',str(tmp/'%04d.png'),'-vf','scale=960:540','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
    return str(target)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Render A/B 6fps low-poly camera edit comparisons')
    parser.add_argument('--out',default='./animatic-output')
    args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    for segment,start,end in segments:
        for version in ['baseline17','bridge19']:
            p=render_segment(out,segment,start,end,version)
            print(p,flush=True)
