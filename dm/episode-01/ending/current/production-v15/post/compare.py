#!/usr/bin/env python3
"""Compare restyled versions of one cut against its Blender guide.

For every candidate video: (1) adherence = correlation of blurred luma with the guide (does the whale /
snow stay where the previs put it?), (2) flicker = mean frame-to-frame change of the fine detail that is
NOT explained by the guide's own change, (3) a still sheet (rows = versions, cols = moments).

  python compare.py --guide R14_guide.mp4 --cand paint=R14_paint.mp4 --cand wan45=wan/x.mp4 ...
                    --times 1.0,4.5 --sheet review.webp [--width 320]
Needs ffmpeg + numpy + scipy + Pillow.
"""
import argparse, json, shutil, subprocess, tempfile
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

FF = shutil.which('ffmpeg') or r'C:\ffmpeg\bin\ffmpeg.exe'


def frames(path, w=320, h=180, n=None):
    tmp = Path(tempfile.mkdtemp())
    subprocess.run([FF, '-loglevel', 'error', '-i', str(path), '-vf', f'scale={w}:{h}', str(tmp / '%04d.png')], check=True)
    fs = sorted(tmp.glob('*.png'))[:n]
    return np.stack([np.asarray(Image.open(f).convert('L'), np.float32) / 255 for f in fs]), fs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--guide', type=Path, required=True)
    ap.add_argument('--cand', action='append', default=[])
    ap.add_argument('--times', default='1.0,4.5')
    ap.add_argument('--sheet', type=Path)
    ap.add_argument('--width', type=int, default=320)
    a = ap.parse_args()
    G, gfs = frames(a.guide)
    rows = [('guide', gfs)]
    res = {}
    for c in a.cand:
        name, p = c.split('=', 1)
        C, cfs = frames(p)
        n = min(len(C), len(G))
        g, x = G[:n], C[:n]
        gb = ndi.gaussian_filter(g, (0, 3, 3)); xb = ndi.gaussian_filter(x, (0, 3, 3))
        adh = float(np.mean([np.corrcoef(gb[i].ravel(), xb[i].ravel())[0, 1] for i in range(n)]))
        hp = lambda v: v - ndi.gaussian_filter(v, (0, 2, 2))
        dx = np.abs(np.diff(hp(x), axis=0)).mean(); dg = np.abs(np.diff(hp(g), axis=0)).mean()
        res[name] = {'frames': n, 'adherence': round(adh, 3), 'flicker': round(float(dx), 4), 'guide_flicker': round(float(dg), 4)}
        rows.append((name, cfs))
    print(json.dumps(res, indent=1))
    if a.sheet:
        ts = [float(t) for t in a.times.split(',')]
        w = a.width; h = w * 9 // 16
        sheet = Image.new('RGB', (w * len(ts), h * len(rows)))
        for r, (name, fs) in enumerate(rows):
            for c, t in enumerate(ts):
                i = min(len(fs) - 1, int(round(t * 24)))
                sheet.paste(Image.open(fs[i]).convert('RGB').resize((w, h)), (c * w, r * h))
        sheet.save(a.sheet, 'WEBP' if a.sheet.suffix == '.webp' else None, quality=55)
        print('sheet', a.sheet, a.sheet.stat().st_size, 'rows', [r[0] for r in rows])


if __name__ == '__main__':
    main()
