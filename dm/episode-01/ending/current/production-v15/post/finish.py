#!/usr/bin/env python3
"""v15d finishing pass: Blender layers -> the painted frame (no AI, deterministic).

Inputs are Blender layers of the same cut (render_cut.py --control base / petals / whale_matte / near):
  base    the beauty without petals (air, moonlight haze, whale)
  petals  the previs petals alone, already hidden behind the whale
  matte   the whale white, the rest black
  near    (optional, RGBA) the near blizzard of real petals, laid over everything with a soft glow
Nothing here moves anything: composition, whale and petals stay exactly where Blender (= the previs) put
them. What it adds is the painting, after the key paintings (images/adopted CUT05 / CUT09) and the
style reference (v8/keyframe-test/refs/style_ref_painterly.png):
  1. the air is laid in with directional knife strokes (static, screen-locked: a painted background does
     not boil; R14's camera is fixed - a moving camera needs the strokes tied to the scene instead)
     and its colour broken into lavender / cyan strokes
  2. the whale keeps its form and its own (Blender) gouache texture; only a cool shadow side
  3. petals: the stream becomes a soft luminous mist, the nearer/brighter petals short strokes along the
     flow, fruit light kept warm-gold; all screened over
  4. bloom, night grade (navy shadows, warm-white lights), paper grain, vignette

Usage:
  python finish.py --layers renders/R14_d --dst renders/R14_d/final [--mp4 R14_final.mp4] [--frames 0:192]
numpy + scipy + Pillow (+ ffmpeg for --mp4).
"""
import argparse, json, shutil, subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.signal import fftconvolve

LUM = np.array([0.299, 0.587, 0.114], np.float32)


def line_kernel(length, width, angle_deg):
    """Normalised anisotropic gaussian: long along angle, thin across."""
    r = int(np.ceil(max(length, width) * 2.5))
    y, x = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
    a = np.radians(angle_deg)
    u = x * np.cos(a) + y * np.sin(a); v = -x * np.sin(a) + y * np.cos(a)
    k = np.exp(-0.5 * ((u / length) ** 2 + (v / width) ** 2))
    return k / k.sum()


def blur_dir(img, k):
    if img.ndim == 2:
        return fftconvolve(img, k, mode='same')
    return np.stack([fftconvolve(img[..., c], k, mode='same') for c in range(img.shape[-1])], -1)


class Canvas:
    """Static textures for one cut (seeded: the same strokes every frame).
    v16: for a camera that turns in place (R15), pass its per-frame cameras (cut.json): the strokes, colour
    breaks and paper grain are then painted on a panorama around the camera and looked up through each
    frame's view, so they stay on the scene while the camera pans (no 'dirty lens'). The vignette stays on
    the screen."""
    def __init__(self, H, W, a, seed=14, cams=None):
        r = np.random.default_rng(seed)
        s = W / 1280.0
        self.H, self.W, self.s = H, W, s
        self.cams = None
        Hs, Ws = H, W
        if cams:
            F = np.array([c['f'] for c in cams.values()], np.float64)
            turn = np.degrees(np.arccos(np.clip(F @ F[0], -1, 1))).max()
            if turn > 1.0:
                Hs, Ws = self._pano(cams, W)
        k1 = line_kernel(11 * s, 3.4 * s, a.angle)            # knife strokes (short, broad)
        k2 = line_kernel(32 * s, 9.0 * s, a.angle + 8)        # broad sweeps
        n1 = blur_dir(r.standard_normal((Hs, Ws)).astype(np.float32), k1)
        n2 = blur_dir(r.standard_normal((Hs, Ws)).astype(np.float32), k2)
        n1 /= n1.std() + 1e-6; n2 /= n2.std() + 1e-6
        st = 0.65 * n1 + 0.35 * n2
        self.stroke = np.tanh(1.6 * st) / np.tanh(1.6)        # flat-ish patches with edges
        c = blur_dir(r.standard_normal((Hs, Ws)).astype(np.float32), line_kernel(30 * s, 7 * s, a.angle - 5))
        self.hue = np.tanh(2.0 * c / (c.std() + 1e-6))
        g = ndi.gaussian_filter(r.standard_normal((Hs, Ws)).astype(np.float32), 0.8 * s)
        self.grain = 1.0 + 0.022 * g / (g.std() + 1e-6)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.vign = 1 - 0.22 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.3
        self.k_smear = line_kernel(5 * s, 1.2 * s, a.angle)
        self.k_dab = line_kernel(2.6 * s, 0.9 * s, a.angle)

    def _pano(self, cams, W):
        """A panorama (azimuth x elevation around the mean view) holding every direction the cut sees,
        one panorama pixel = one screen pixel at the centre of the view."""
        c0 = next(iter(cams.values()))
        fm = np.array([c['f'] for c in cams.values()]).mean(0); fm /= np.linalg.norm(fm)
        sr = np.cross(fm, (0.0, 0.0, 1.0)); sr /= np.linalg.norm(sr); su = np.cross(sr, fm)
        self.B = np.stack([sr, su, fm])
        self.cams = cams
        H = self.H
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
        self.xn = (xs + 0.5 - W / 2) / (W / 2); self.yn = -(ys + 0.5 - H / 2) / (H / 2)
        az, el = [], []
        for c in list(cams.values())[::3]:
            q = self._rays(c, self.xn[::16, ::16], self.yn[::16, ::16])
            az.append(np.arctan2(q[..., 0], q[..., 2]).ravel()); el.append(np.arcsin(np.clip(q[..., 1], -1, 1)).ravel())
        az = np.concatenate(az); el = np.concatenate(el)
        self.rpp = 2 * np.arctan(18.0 / c0['lens_mm']) / W
        m = 24 * self.rpp
        self.az0 = az.min() - m; self.el1 = el.max() + m
        Wp = int(np.ceil((az.max() + m - self.az0) / self.rpp)); Hp = int(np.ceil((self.el1 - (el.min() - m)) / self.rpp))
        print(f'  canvas on the scene: panorama {Wp}x{Hp} px (the camera turns)')
        return Hp, Wp

    def _rays(self, c, xn, yn):
        L = c['lens_mm']
        d = (np.array(c['f'])[None, None] + (xn * 18.0 / L)[..., None] * np.array(c['r'])[None, None]
             + (yn * 10.125 / L)[..., None] * np.array(c['u'])[None, None])
        q = d @ self.B.T
        return q / np.linalg.norm(q, axis=-1, keepdims=True)

    def maps(self, k):
        """stroke, hue, grain as seen in frame k."""
        if self.cams is None:
            return self.stroke, self.hue, self.grain
        q = self._rays(self.cams[k], self.xn, self.yn)
        col = (np.arctan2(q[..., 0], q[..., 2]) - self.az0) / self.rpp
        row = (self.el1 - np.arcsin(np.clip(q[..., 1], -1, 1))) / self.rpp
        return tuple(ndi.map_coordinates(m, (row, col), order=1, mode='reflect').astype(np.float32)
                     for m in (self.stroke, self.hue, self.grain))


LAV = np.array([0.050, -0.012, 0.070], np.float32)       # lavender stroke
CYA = np.array([-0.040, 0.025, 0.045], np.float32)       # cyan stroke
MIST = np.array([0.78, 0.88, 1.00], np.float32)
DAB = np.array([1.00, 0.97, 0.92], np.float32)
GOLD = np.array([1.00, 0.82, 0.50], np.float32)


def load(p, mode='RGB'):
    return np.asarray(Image.open(p).convert(mode), np.float32) / 255.0


def frame(base, pet, matte, cv, a, near=None, gold=0.0, k=0):
    H, W, _ = base.shape
    stroke, hue_m, grain = cv.maps(k)
    M = ndi.gaussian_filter(matte[..., 0], 1.0 * cv.s)[..., None]
    L = (base @ LUM)[..., None]
    # 1. air: smear along the stroke direction, then knife-stroke value + colour breaks (scaled by its light)
    air = 0.55 * base + 0.45 * blur_dir(base, cv.k_smear)
    lift = np.clip(L * 3.0, 0, 1)                             # darks stay dark, strokes show where there is light
    air = air * (1 + a.stroke * stroke[..., None] * (0.35 + 0.65 * lift))
    hue = np.where(hue_m[..., None] > 0, hue_m[..., None] * LAV, -hue_m[..., None] * CYA)
    air = air + hue * a.hue * np.clip(L * 4.0, 0, 1)
    # 2. whale: its own gouache texture comes from Blender and moves with it; no screen-locked strokes on
    #    it (they would slide over the moving body), only a cool shadow side
    wl = base + (1 - np.clip(L * 1.4, 0, 1)) * np.array([-0.02, 0.0, 0.03], np.float32)
    wl = wl + a.whale_detail * (wl - ndi.gaussian_filter(wl, (2.5 * cv.s, 2.5 * cv.s, 0)))   # grooves and strokes read
    x = air * (1 - M) + wl * M
    # keep the whale the brightest thing: a soft dark ring just outside its body separates it from the
    # bright stream behind (a painter's halo of shadow), the body itself is untouched
    ring = np.clip(ndi.gaussian_filter(matte[..., 0], 5 * cv.s) - matte[..., 0], 0, 1)[..., None]
    x = x * (1 - a.ring * ring)
    Lx = (x @ LUM)[..., None]
    x = Lx + (x - Lx) * a.sat                                 # the paintings are bluer than the previs grey
    # 3. petals: mist along the stream + short strokes for the brighter ones, fruit light kept gold
    PL = pet.max(-1)
    warm = np.clip((pet[..., 0] - pet[..., 2]) * 4.0, 0, 1)[..., None]
    mist = ndi.gaussian_filter(PL, 3.5 * cv.s)[..., None] * a.mist * MIST * (1 - 0.7 * M)   # thin over the whale
    t = np.clip((PL - a.dab_lo) / (a.dab_hi - a.dab_lo), 0, 1); t = t * t * (3 - 2 * t)
    core = blur_dir(ndi.grey_dilation(PL * t, size=(2, 2)), cv.k_dab) * 1.6
    dabs = core[..., None] * (DAB * (1 - warm) + GOLD * warm) * a.dab
    fine = ndi.gaussian_filter(PL, 0.6 * cv.s)[..., None] * a.fine * MIST * (1 - 0.5 * M)   # keep the previs sparkle
    p = np.clip(mist + dabs + fine, 0, 1)
    x = 1 - (1 - np.clip(x, 0, 1)) * (1 - p)
    # near blizzard: real petal shapes over everything (they are within 30 m), with a little glow
    if near is not None:
        al = near[..., 3:4] * a.near_alpha; rgb = near[..., :3]
        if a.near_tint:                  # the whale's light colours the petals near it on screen (falls off)
            tint = np.array([float(v) for v in a.near_tint.split(',')], np.float32)
            if a.near_tint_gold:          # the whale's light turns pale gold with each stroke (whale_gold.json)
                tg = np.array([float(v) for v in a.near_tint_gold.split(',')], np.float32)
                tint = tint * (1 - gold) + tg * gold
            dist = ndi.distance_transform_edt(matte[..., 0] < 0.5)
            wgt = (a.near_tint_k * np.exp(-(dist / (a.near_tint_r * cv.s)) ** 2))[..., None]
            Ln = (rgb @ LUM)[..., None]
            rgb = rgb * (1 - wgt) + np.clip(Ln * tint * 1.15, 0, 1) * wgt
        # keep a window on the whale: petals passing in front of it are thinned (a painter's choice)
        win = np.clip(ndi.gaussian_filter(ndi.grey_dilation(matte[..., 0], size=(int(9 * cv.s),) * 2), 8 * cv.s) * 1.5, 0, 1)[..., None]
        al = al * (1 - a.whale_window * win)
        x = x * (1 - al) + rgb * al
        g = ndi.gaussian_filter(rgb * al, (3 * cv.s, 3 * cv.s, 0))
        x = x + a.near_glow * g
    # 4. exposure, bloom, grade, paper, vignette
    x = x * a.gain
    hi = np.clip(x - 0.45, 0, None)
    x = x + a.bloom * (0.6 * ndi.gaussian_filter(hi, (6 * cv.s, 6 * cv.s, 0)) + 0.4 * ndi.gaussian_filter(hi, (26 * cv.s, 26 * cv.s, 0)))
    L2 = (x @ LUM)[..., None]
    x = x + np.array([-0.004, 0.002, 0.016], np.float32) * (1 - np.clip(L2 * 5, 0, 1))      # navy shadows
    x = x * (1 + np.array([0.02, 0.0, -0.03], np.float32) * np.clip((L2 - 0.5) * 2, 0, 1))  # warm-white lights
    x = x * grain[..., None] * cv.vign[..., None]
    x = np.where(x < 0.75, x, 0.75 + (1 - np.exp(-(x - 0.75) * 3.0)) * 0.25)              # soft shoulder
    return np.clip(x, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--layers', type=Path, required=True, help='folder with control_base/ control_petals/ control_whale_matte/')
    ap.add_argument('--dst', type=Path, required=True)
    ap.add_argument('--frames', default='')
    ap.add_argument('--mp4', type=Path)
    ap.add_argument('--fps', type=int, default=24)
    ap.add_argument('--angle', type=float, default=-22.0, help='stroke direction in degrees (screen, y down)')
    ap.add_argument('--stroke', type=float, default=0.18)
    ap.add_argument('--hue', type=float, default=0.25)
    ap.add_argument('--mist', type=float, default=0.12)
    ap.add_argument('--dab', type=float, default=0.7)
    ap.add_argument('--dab-lo', type=float, default=0.55)
    ap.add_argument('--dab-hi', type=float, default=0.75)
    ap.add_argument('--fine', type=float, default=0.22)
    ap.add_argument('--bloom', type=float, default=0.45)
    ap.add_argument('--sat', type=float, default=1.35)
    ap.add_argument('--near-glow', type=float, default=0.25)
    ap.add_argument('--near-alpha', type=float, default=0.9)
    ap.add_argument('--whale-window', type=float, default=0.6)
    ap.add_argument('--near-tint', default='', help='r,g,b: colour of the whale light on the near petals around it')
    ap.add_argument('--near-tint-r', type=float, default=260.0)
    ap.add_argument('--near-tint-gold', default='', help='r,g,b: the near-petal tint when the whale light is gold')
    ap.add_argument('--near-tint-k', type=float, default=0.85)
    ap.add_argument('--whale-detail', type=float, default=0.6)
    ap.add_argument('--ring', type=float, default=0.5)
    ap.add_argument('--gain', type=float, default=1.12)
    ap.add_argument('--cam-json', type=Path, help="the cut's cut.json: if its camera turns, the canvas stays on the scene")
    a = ap.parse_args()
    cams = None
    if a.cam_json:
        cams = {f['k']: f['cam'] for f in json.loads(a.cam_json.read_text(encoding='utf-8'))['frames']}
    files = sorted((a.layers / 'control_base').glob('*.png'))
    if a.frames:
        f0, f1 = (int(v) for v in a.frames.split(':'))
        files = [f for f in files if f0 <= int(f.stem) < f1]
    a.dst.mkdir(parents=True, exist_ok=True)
    cv = None
    gj = a.layers / 'whale_gold.json'
    golds = json.loads(gj.read_text(encoding='utf-8')) if gj.exists() else {}
    for f in files:
        base = load(f)
        if cv is None:
            cv = Canvas(base.shape[0], base.shape[1], a, cams=cams)
        pet = load(a.layers / 'control_petals' / f.name)
        matte = load(a.layers / 'control_whale_matte' / f.name)
        nf = a.layers / 'control_near' / f.name
        near = load(nf, 'RGBA') if nf.exists() else None
        x = frame(base, pet, matte, cv, a, near, golds.get(f.stem, 0.0) * 0.85, int(f.stem))
        Image.fromarray((x * 255 + 0.5).astype(np.uint8)).save(a.dst / f.name)
    print('finished', len(files), 'frames ->', a.dst)
    if a.mp4:
        ff = shutil.which('ffmpeg') or r'C:\ffmpeg\bin\ffmpeg.exe'
        subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(a.fps), '-i', str(a.dst / '%04d.png'),
                        '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', str(a.mp4)], check=True)
        print('mp4', a.mp4)


if __name__ == '__main__':
    main()
