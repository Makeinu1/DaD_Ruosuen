#!/usr/bin/env python3
"""v15: join two Fun-Control segments into one cut (the model makes 121 frames = 5 s at a time).

Segment 1 covers previs frames [0, n1); segment 2 starts at previs frame --start2 (made with the start
image = segment 1's frame --start2, so both begin from the same painting) and runs to the end of the cut.
The overlap [start2, n1) is cross-faded linearly; the joined cut has start2 + n2 frames.

Usage:
  python join_segments.py --a seg1.mp4 --b seg2.mp4 --start2 71 --out R14_join.mp4 [--fps 24]
"""
import argparse, shutil, subprocess
from pathlib import Path


def ff():
    return shutil.which('ffmpeg') or r'C:\ffmpeg\bin\ffmpeg.exe'


def nframes(p):
    fp = shutil.which('ffprobe') or r'C:\ffmpeg\bin\ffprobe.exe'
    r = subprocess.run([fp, '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
                        'stream=nb_read_frames', '-of', 'csv=p=0', str(p)], capture_output=True, text=True)
    return int(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', type=Path, required=True)
    ap.add_argument('--b', type=Path, required=True)
    ap.add_argument('--start2', type=int, required=True, help='previs frame of the first frame of --b')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--fps', type=int, default=24)
    a = ap.parse_args()
    n1 = nframes(a.a)
    over = n1 - a.start2
    if over < 1:
        raise SystemExit('segments do not overlap')
    off, dur = a.start2 / a.fps, over / a.fps
    total = a.start2 + nframes(a.b)                 # xfade can emit one extra frame; cut to the exact length
    subprocess.run([ff(), '-y', '-loglevel', 'error', '-i', str(a.a), '-i', str(a.b), '-filter_complex',
                    f'[0:v]settb=1/{a.fps},fps={a.fps}[x];[1:v]settb=1/{a.fps},fps={a.fps}[y];'
                    f'[x][y]xfade=transition=fade:duration={dur:.6f}:offset={off:.6f},format=yuv420p',
                    '-frames:v', str(total), '-c:v', 'libx264', '-crf', '16', str(a.out)], check=True)
    print('joined', n1, '+', nframes(a.b), 'overlap', over, '->', nframes(a.out), 'frames', a.out)


if __name__ == '__main__':
    main()
