#!/usr/bin/env python3
"""v15: lay the previs petals (Blender petal layer) over a painted pass (e.g. Wan Fun-Control output).

The painted pass keeps the whale and camera from the control video, but any snow it paints is its own.
This puts back the previs petal simulation exactly: render_cut.py --control petals gives the petals
alone (the whale and rocks are black mattes, so petals behind the whale stay hidden); here (style 'paint') the fine speckle
becomes a soft mist along the stream plus a few dabs for the brighter petals, screened over the paint.

Geometry: the painted pass was made with ComfyUI ImageScale(crop='center') from a 16:9 source to
--width x --height; the petal layer gets the same centre crop + scale, so the two line up.

Usage:
  python overlay_petals.py --paint renders/R14_b/wanctl/x.mp4 --petals renders/R14_b/control_petals [--style paint|raw] \
                           --start 0 --out renders/R14_b/x_petals.mp4 [--gain 1.0] [--glow 0.6] [--fps 24]
numpy + scipy + Pillow + ffmpeg (C:\\ffmpeg\\bin\\ffmpeg.exe or on PATH).
"""
import argparse, shutil, subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def ffmpeg():
    return shutil.which('ffmpeg') or r'C:\ffmpeg\bin\ffmpeg.exe'


def probe(path):
    out = subprocess.run([ffmpeg(), '-i', str(path)], capture_output=True, text=True, errors='replace').stderr
    import re
    m = re.search(r'Video:.*?(\d{2,5})x(\d{2,5})', out)
    return int(m.group(1)), int(m.group(2))


def centre_fit(im, w, h):
    """ComfyUI ImageScale crop='center': crop the source to the target aspect, then scale."""
    sw, sh = im.size
    if sw * h > sh * w:                       # source wider -> crop width
        cw = round(sh * w / h); x0 = (sw - cw) // 2; im = im.crop((x0, 0, x0 + cw, sh))
    else:
        ch = round(sw * h / w); y0 = (sh - ch) // 2; im = im.crop((0, y0, sw, y0 + ch))
    return im.resize((w, h), Image.LANCZOS)


VEIL = np.array([0.80, 0.90, 1.00], np.float32)     # the stream as a cool luminous mist
DAB = np.array([1.00, 0.97, 0.90], np.float32)      # the nearer, brighter petals as warm-white dabs


def paint_petals(p, a):
    """'paint' style: the raw layer is a fine speckle (most petals are sub-pixel at this distance), which
    reads as digital noise over a painting. Keep the flow as a soft mist and only the brighter petals as
    small dabs. The dab threshold is a soft ramp, so petals fade in/out with their spin instead of popping."""
    k = p.shape[1] / 960.0
    L = p.max(-1)
    veil = ndi.gaussian_filter(L, 3.5 * k) * a.veil
    s = np.clip((L - a.dab_lo) / max(1e-6, a.dab_hi - a.dab_lo), 0, 1)
    s = s * s * (3 - 2 * s)
    core = ndi.grey_dilation(L * s, size=(3, 3))
    dab = ndi.gaussian_filter(core, 0.9 * k) * a.dab
    return np.clip(veil[..., None] * VEIL + dab[..., None] * DAB, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--paint', type=Path, required=True)
    ap.add_argument('--petals', type=Path, required=True, help='folder of ####.png from render_cut.py --control petals')
    ap.add_argument('--start', type=int, default=0, help='previs frame of the first painted frame')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--gain', type=float, default=1.0)
    ap.add_argument('--glow', type=float, default=0.6)
    ap.add_argument('--fps', type=int, default=24)
    ap.add_argument('--style', default='paint', choices=['paint', 'raw'], help='raw: the layer as rendered (+glow)')
    ap.add_argument('--veil', type=float, default=2.2)
    ap.add_argument('--dab', type=float, default=1.4)
    ap.add_argument('--dab-lo', type=float, default=0.30)
    ap.add_argument('--dab-hi', type=float, default=0.45)
    a = ap.parse_args()
    w, h = probe(a.paint)
    dec = subprocess.Popen([ffmpeg(), '-loglevel', 'error', '-i', str(a.paint), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                           stdout=subprocess.PIPE)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    enc = subprocess.Popen([ffmpeg(), '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
                            '-r', str(a.fps), '-i', '-', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', str(a.out)],
                           stdin=subprocess.PIPE)
    i = 0
    while True:
        buf = dec.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        base = np.frombuffer(buf, np.uint8).reshape(h, w, 3).astype(np.float32) / 255.0
        f = a.petals / f'{a.start + i:04d}.png'
        if f.exists():
            p = np.asarray(centre_fit(Image.open(f).convert('RGB'), w, h), np.float32) / 255.0
            if a.style == 'paint':
                p = np.clip(a.gain * paint_petals(p, a), 0, 1)
            else:
                glow = np.stack([ndi.gaussian_filter(p[..., c], 2.0) for c in range(3)], -1)
                p = np.clip(a.gain * p + a.glow * glow, 0, 1)
            base = 1 - (1 - base) * (1 - p)          # screen
        else:
            print('missing petal frame', f)
        enc.stdin.write((np.clip(base, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
        i += 1
    enc.stdin.close(); enc.wait(); dec.wait()
    print('frames', i, '->', a.out)


if __name__ == '__main__':
    main()
