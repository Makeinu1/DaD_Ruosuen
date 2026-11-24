#!/usr/bin/env python3
"""v15 方式①: Blender beauty frames -> painterly frames (no AI). numpy + scipy + Pillow (+ ffmpeg for mp4).

The aim is the look of the adopted keyframe paintings (images/adopted): night-blue painted background,
flat brush areas with soft edges, glow that blooms into the paint, a little paper grain.
  1. generalised Kuwahara (4 sectors) -> flat brush patches with kept edges
  2. bloom from the highlights (two radii) -> the whale/petal light bleeds into the paint
  3. colour grade: blue-violet shadows, warm-white highlights, light desaturation of mids
  4. static paper grain + vignette (static on purpose: painted backgrounds do not boil)

Usage:
  python paint.py --src renders/R14_a/beauty --dst renders/R14_a/paint [--radius 4] [--mp4 out.mp4] [--fps 24]
"""
import argparse, subprocess, shutil
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def kuwahara(img, r):
    """4-sector Kuwahara on float32 RGB (H,W,3); the sector with the lowest luma variance wins."""
    r = max(2, r + (r % 2))                     # even radius: sector centres sit on whole pixels
    h = r // 2
    k = r + 1
    L = img @ np.array([0.299, 0.587, 0.114], np.float32)
    P = np.pad(np.concatenate([img, L[..., None], (L * L)[..., None]], -1), ((h, h), (h, h), (0, 0)), mode='reflect')
    M = np.stack([ndi.uniform_filter(P[..., c], k, mode='reflect') for c in range(P.shape[-1])], -1)
    H, W = L.shape
    best_v = None; out = None
    for oy in (0, 2 * h):                       # sector centre = pixel -/+ h
        for ox in (0, 2 * h):
            m = M[oy:oy + H, ox:ox + W]
            v = m[..., 4] - m[..., 3] ** 2
            if best_v is None:
                best_v, out = v, m[..., :3].copy()
            else:
                sel = v < best_v
                best_v = np.where(sel, v, best_v); out[sel] = m[..., :3][sel]
    return out


def paper(h, w, seed=11):
    r = np.random.default_rng(seed)
    n = ndi.gaussian_filter(r.standard_normal((h, w)).astype(np.float32), 1.2) * 0.6
    n += ndi.gaussian_filter(r.standard_normal((h, w)).astype(np.float32), 6.0) * 2.0
    n /= max(1e-6, n.std())
    return 1.0 + 0.035 * n


def grade(x):
    L = (x @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    shadow = np.array([0.006, 0.011, 0.026], np.float32)          # night blue in the darks (keep them dark)
    high = np.array([1.0, 0.985, 0.95], np.float32)               # warm white in the lights
    x = x + shadow * (1 - np.clip(L * 3, 0, 1))
    x = x * (0.92 + 0.08 * high)
    sat = 0.85 + 0.25 * np.clip(L * 2, 0, 1)                      # quieter mids, keep the glows
    return L + (x - L) * sat


def process(im, r, grain, vign):
    x = np.asarray(im.convert('RGB'), np.float32) / 255.0
    # split the fine petal speckle from the large forms, so that the brush pass does not turn the
    # snow into a mosaic: forms -> Kuwahara brush patches; snow -> a soft veil plus a few dabs
    med = np.stack([ndi.median_filter(x[..., c], 5) for c in range(3)], -1)
    snow = np.clip(x - med, 0, None)
    base = kuwahara(med, r)
    base = np.stack([ndi.gaussian_filter(base[..., c], 0.8) for c in range(3)], -1)
    veil = np.stack([ndi.gaussian_filter(snow[..., c], 2.2) for c in range(3)], -1) * 2.4
    sl = snow.max(-1)
    thr = np.quantile(sl, 0.985)
    dab = ndi.grey_dilation(np.where(sl > thr, sl, 0), footprint=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
    dab = ndi.gaussian_filter(dab, 0.7)[..., None] * np.array([1.0, 0.97, 0.90], np.float32)
    x = base + veil + 0.8 * dab
    hi = np.clip(x - 0.42, 0, None)
    bloom = 0.55 * np.stack([ndi.gaussian_filter(hi[..., c], 5) for c in range(3)], -1) \
        + 0.45 * np.stack([ndi.gaussian_filter(hi[..., c], 22) for c in range(3)], -1)
    x = x + 0.6 * bloom
    x = grade(x)
    x = x * grain[..., None] * vign[..., None]
    x = np.clip(x, 0, None)
    x = np.where(x < 0.6, x, 0.6 + (1 - np.exp(-(x - 0.6) * 2.5)) * 0.4)   # shoulder above 0.6, mids untouched
    return Image.fromarray(np.clip(x * 255, 0, 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', type=Path, required=True)
    ap.add_argument('--dst', type=Path, required=True)
    ap.add_argument('--radius', type=int, default=0, help='0 = width/320')
    ap.add_argument('--mp4', type=Path)
    ap.add_argument('--fps', type=int, default=24)
    a = ap.parse_args()
    a.dst.mkdir(parents=True, exist_ok=True)
    files = sorted(a.src.glob('*.png'))
    im0 = Image.open(files[0]); W, H = im0.size
    r = a.radius or max(4, W // 160)
    grain = paper(H, W)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vign = 1 - 0.28 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.4
    for f in files:
        process(Image.open(f), r, grain, vign).save(a.dst / f.name)
    print('painted', len(files), 'frames r =', r)
    if a.mp4:
        ff = shutil.which('ffmpeg') or 'ffmpeg'
        subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(a.fps), '-i', str(a.dst / '%04d.png'),
                        '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(a.mp4)], check=True)
        print('mp4', a.mp4)


if __name__ == '__main__':
    main()
