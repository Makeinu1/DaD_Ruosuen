#!/usr/bin/env python3
"""v15 bridge: export one cut of the v14.10 previs as data that Blender (or anything else) can load.

The previs (../../previs/v14-director-rebuild/) is the single source of truth for timing, camera,
whale path/acting and the petal simulation. This script imports it unchanged and writes, per frame:

  <out>/cut.json            meta + per-frame camera / whale body frame / whale light
  <out>/petals/f_####.npz   petals in (or near) the camera view:
                            p (N,3) float32 world metres, fruit (N) 0..1, spin (N) rad,
                            bright (N) previs-style light level, kind (N) 0=simulated 1=near-camera snow,
                            idx (N) int32 petal id (simulated: index in the previs petal arrays; near-camera
                            snow: -1) - stable across frames, so anything derived per petal does not jump

Coordinates are the previs world: X east, Y north (into the lake), Z up, metres, lake surface Z=0.

Usage (any Python 3.10+ with numpy + Pillow; scipy not needed):
  python export_cut.py --cut R14 --out C:/VideoStudio/projects/ruosuen/cache/R14 [--fps 24] [--every 1]
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
PREVIS = HERE.parent.parent / 'previs' / 'v14-director-rebuild'
sys.path.insert(0, str(PREVIS))
import ruosuen_v14_previs as pv          # noqa: E402  (runs the previs module set-up: path, flowers, events)
w = pv.w


def cam_dict(c):
    return {'pos': c.pos.tolist(), 'r': c.r.tolist(), 'u': c.u.tolist(), 'f': c.f.tolist(),
            'lens_mm': float(c.lens), 'sensor_w_mm': 36.0, 'sensor_h_mm': 20.25,
            'yaw_deg': float(c.yaw), 'pitch_deg': float(c.pitch)}


def in_view(c, P, margin=0.25, near=0.3):
    q = c.cam_xyz(P)
    z = q[:, 2]
    ax = (18.0 / c.lens) * (1 + margin); ay = (10.125 / c.lens) * (1 + margin)
    zz = np.maximum(z, 1e-3)
    return (z > near) & (np.abs(q[:, 0] / zz) < ax) & (np.abs(q[:, 1] / zz) < ay)


def capture_local_snow(R, cam, t, tau, cid):
    """Run the previs near-camera snow (local_snow) and turn its screen splats back into world points."""
    got = []
    W, H = R.W, R.H

    def cap(A, cam_, x, y, z, petal_rgb, fruit_rgb, spin, g):
        rx = (x - W / 2) / (cam_.lens / 36 * W) * z
        ry = -(y - H / 2) / (cam_.lens / 20.25 * H) * z
        pw = cam_.pos[None, :] + rx[:, None] * cam_.r[None, :] + ry[:, None] * cam_.u[None, :] + z[:, None] * cam_.f[None, :]
        got.append((pw, petal_rgb.mean(1) / 236.0, np.clip(fruit_rgb.mean(1) / 204.0, 0, 1), spin))
    orig = R.paint_flakes
    R.paint_flakes = cap
    try:
        R.local_snow(np.zeros((H, W, 3), np.float32), cam, t, tau, cid)
    finally:
        R.paint_flakes = orig
    if not got:
        return None
    pw, br, fr, sp = (np.concatenate(a) for a in zip(*got))
    return pw, br, fr, sp


def near_density(R, cam, tau, cid):
    """0..1: how much of the previs near-camera snow is out at this moment (local_snow's N_eff / N).
    Mirrors Renderer.local_snow so that Blender's NearSnow can grow and surge the same way
    (R15: with the snow the whale brings to the camera)."""
    if cid in ('R13', 'R14'):
        return float(pv.smooth((tau - pv.TAU_LIFT) / 1.5))
    if cid == 'R17b':
        return 1.0
    P = R.petals
    act = (tau >= P.tau_lift) & ~P.landed & ~P.gone
    n_near = int((np.sum((P.p[act] - cam.pos) ** 2, 1) < 20.0 ** 2).sum()) if act.any() else 0
    return float(pv.smooth(n_near / 150.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cut', required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--fps', type=int, default=24)
    ap.add_argument('--every', type=int, default=1, help='export every n-th frame (tests)')
    ap.add_argument('--no-petals', action='store_true')
    a = ap.parse_args()
    cid = a.cut
    s0, s1 = pv.T[cid]
    n = int(round((s1 - s0) * a.fps))
    (a.out / 'petals').mkdir(parents=True, exist_ok=True)
    R = pv.Renderer(320, 180)            # small: only its cameras, petal sim and near-snow logic are used
    frames = []
    t0 = time.time()
    for k in range(0, n, a.every):
        t = s0 + k / a.fps
        tau = float(pv.tau_of(t))
        cam = R.cams[cid](t, tau)
        fr, Vb, Ve, Vloc = pv.whale_world(tau)
        amp = 1.9 * (1 - 0.8 * max(pv.glide(tau), pv.ignite_glide(tau)))
        extra_roll = pv.glance_roll(tau) + pv.joy_roll(tau) + pv.play_roll(tau) + pv.look_roll(tau)
        wl_p, wl_I = pv.whale_light(tau)
        rec = {'k': k, 't': round(t, 5), 'tau': tau, 'cam': cam_dict(cam),
               'whale': {'p': fr[0].tolist(), 'fwd': fr[1].tolist(), 'left': fr[2].tolist(), 'up': fr[3].tolist(),
                         'amp': amp, 'extra_roll': float(extra_roll),
                         'glow': float(pv.glow_level(tau, w.XMIN)), 'opal': float(pv.opal_mix(tau)),
                         'melt': float(pv.melt_progress(t)) if cid == 'R18' else 0.0},
               'whale_light': {'p': np.asarray(wl_p).tolist(), 'I': float(wl_I)},
               # R15's closest pass: the air full of lit petals glows up around the whale (previs kg)
               'climax': float(pv.climax(tau))}
        if not a.no_petals:
            P = R.petal_state(tau, cid)
            parts = []
            if P is not None:
                act = (tau >= P.tau_detach) & ~P.gone
                idx = np.where(act)[0]
                if len(idx):
                    keep = idx[in_view(cam, P.p[idx])]
                    pp = P.p[keep]
                    d = np.linalg.norm(pp - wl_p, axis=1)
                    bright = 0.05 + wl_I * 1.6 / (1 + (d / 55.0) ** 2) + 0.32 * w.moonlit(pp, soft=7.0)
                    parts.append((pp, P.fruit[keep], P.spin[keep], bright, np.zeros(len(keep), np.uint8), keep.astype(np.int32)))
                rec['near_k'] = near_density(R, cam, tau, cid)
                # the flow of the simulated snow around the camera (median velocity within 30 m, world m/s):
                # NearSnow's world mode lets its petals ride it (R15: the river the whale brings, then lets go)
                act_f = (tau >= P.tau_detach) & ~P.gone & ~P.landed
                near_f = np.where(act_f)[0]
                near_f = near_f[np.sum((P.p[near_f] - cam.pos) ** 2, 1) < 30.0 ** 2] if len(near_f) else near_f
                rec['near_flow'] = np.median(P.v[near_f], 0).tolist() if len(near_f) >= 20 else [0.0, 0.0, 0.0]
                rec['near_flow_n'] = int(len(near_f))
                # R15's slow moment: the near petals hang and glint gold (previs local_snow fk)
                rec['slow'] = float(pv._slow_window(t - pv.T_SLOW)) if cid == 'R15' else 0.0
                ls = capture_local_snow(R, cam, t, tau, cid)
                if ls is not None:
                    pw, br, frt, sp = ls
                    parts.append((pw, frt, sp, br, np.ones(len(pw), np.uint8), np.full(len(pw), -1, np.int32)))
            if parts:
                p, fruit, spin, bright, kind, idx = (np.concatenate(x) for x in zip(*parts))
            else:
                p = np.zeros((0, 3)); fruit = spin = bright = np.zeros(0); kind = np.zeros(0, np.uint8); idx = np.zeros(0, np.int32)
            np.savez(a.out / 'petals' / f'f_{k:04d}.npz', p=p.astype(np.float32), fruit=fruit.astype(np.float16),
                     spin=np.mod(spin, 2 * np.pi).astype(np.float16), bright=bright.astype(np.float16), kind=kind, idx=idx)
            rec['n_petals'] = int(len(p))
        frames.append(rec)
        if k % (a.fps * 2) == 0:
            print(f'{cid} frame {k}/{n} t={t:.2f} tau={tau:.2f} petals={rec.get("n_petals")} {time.time() - t0:.0f}s', flush=True)
    # v16: the flower colony this cut sees (R10-R13): every flower in any frame's view (out to 260 m), with
    # its bloom time, maturity, moonlight, and the times its petals let go (previs Petals: 4 per mature flower)
    if cid in ('R10', 'R11', 'R12', 'R13') and not a.every > 24:
        F = pv.FLOWERS
        seen = np.zeros(len(F), bool)
        for rec in frames[::6]:
            c = rec['cam']; cp_ = np.array(c['pos'])
            q = (F - cp_) @ np.array([c['r'], c['u'], c['f']]).T
            z = q[:, 2]; zz = np.maximum(z, 1e-3)
            ax = 18.0 / c['lens_mm'] * 1.2; ay = 10.125 / c['lens_mm'] * 1.2
            seen |= (z > 0.05) & (z < 260) & (np.abs(q[:, 0] / zz) < ax) & (np.abs(q[:, 1] / zz) < ay)
        fi = np.where(seen)[0]
        Pp = R.petals
        det = np.full((len(F), 4), np.inf, np.float32)
        order = np.argsort(Pp.src, kind='stable')
        s_sorted = Pp.src[order]; starts = np.searchsorted(s_sorted, np.arange(len(F))); ends = np.searchsorted(s_sorted, np.arange(len(F)), 'right')
        for i in fi:
            dd = np.sort(Pp.tau_detach[order[starts[i]:ends[i]]])[:4]
            det[i, :len(dd)] = dd
        np.savez(a.out / 'flowers.npz', p=F[fi].astype(np.float32), idx=fi.astype(np.int32),
                 tau_open=pv.TAU_OPEN[fi].astype(np.float32), mature=pv.MATURE[fi],
                 moon=w.moonlit(F[fi] + np.array([0, 0, 0.2])).astype(np.float32), det=det[fi])
        print('flowers', len(fi))
    # the moon as the previs composes it in the opening (an anchor just beyond the top rim + its angular
    # radius), laid out at the previs' own 1280x720 so that it lands on the same pixels
    R.W, R.H = 1280, 720
    lay = R.moon_layout(cid)
    moon = None if lay is None else {'p': np.asarray(lay[0]).tolist(), 'ang_r': float(lay[1])}
    meta = {'cut': cid, 'film_start_s': s0, 'film_end_s': s1, 'fps': a.fps, 'n_frames': n, 'every': a.every,
            'moon': moon,
            'previs_version': 'v14.10', 'coords': 'previs world: X east, Y north, Z up, metres; lake Z=0',
            'camera_note': 'Blender: sensor_fit HORIZONTAL, sensor_width 36 mm; rotation columns X=r, Y=u, Z=-f',
            'moon_dir': w.MOON_DIR.tolist(), 'ev_contact': float(pv.EV['contact']), 'rim_z': w.RIM_Z, 'top_z': w.TOP_Z, 'top_narrow': w.TOP_NARROW,
            'fissure': w.FISSURE, 'party': [list(map(float, p)) for p in pv.PARTY], 'pc': w.PC.tolist(),
            'whale_local_axes': 'x forward (head +x), y left, z up; same scale as wh01_v20_hero.glb',
            # the previs retimes its whale path (stroke phase, fast stroke); the tail stroke and the light
            # pulse are wrong in Blender unless WhalePath gets the same retime
            'stroke_phase0': float(pv.PATH.stroke_phase0),
            'fast_stroke_tau': None if pv.PATH.fast_stroke_tau is None else float(pv.PATH.fast_stroke_tau),
            'frames': frames}
    (a.out / 'cut.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    print('done', a.out, f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
