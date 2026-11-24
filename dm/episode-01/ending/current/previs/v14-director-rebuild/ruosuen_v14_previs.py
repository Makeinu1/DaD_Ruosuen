#!/usr/bin/env python3
"""『空に降る雪』v14 director-rebuild previs — 70 s, 19 cuts, 24 fps.

Implements storyboard-v14-director-rebuild-2026-11-23.md:
- one continuous world path with TIME ELLIPSIS between some cuts (world time tau != film time t),
- slow whale (4-7 m/s), tail-only propulsion: one stroke then glide (5.6 s), speed surge per stroke,
  bank in turns, the single fast stroke after the overhead pass, a passing glance (no stop),
- moonlight through a thick slot-canyon fissure (soft beam), ignition head->tail, light pulse per stroke,
- flowers bloom only where the whale light reaches; petals: guided inside the whale light,
  pure blizzard outside it, free fall after the whale leaves,
- the far walls stay dark; the whale light reaches the canopy only during the ascent,
- R19 identical camera to R01, last petal lands on the water.

Run:  python ruosuen_v14_previs.py --out artifacts/v14-full70 [--fps 24] [--width 1280]
      python ruosuen_v14_previs.py --sheet-only   (contact sheet + QA only)
Requires numpy, Pillow, ffmpeg. All numbers are previs values, not locked camera data.
"""
import argparse, json, math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v14_world as w
from v14_world import clamp, smooth, unit

FONT_PATH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
SHOTLIST = json.loads((HERE.parent.parent / 'shotlist-v14-director-rebuild.json').read_text(encoding='utf-8'))
CUT_LABEL = {c['id']: c for c in SHOTLIST['cuts']}

# ====================================================================== camera
class Cam:
    def __init__(self, pos, target=None, yaw=None, pitch=None, lens=24.0):
        self.pos = np.asarray(pos, float)
        if target is not None:
            d = unit(np.asarray(target, float) - self.pos)
            yaw = math.degrees(math.atan2(d[0], d[1])); pitch = math.degrees(math.asin(np.clip(d[2], -1, 1)))
        self.yaw, self.pitch, self.lens = yaw, pitch, lens
        y, p = math.radians(yaw), math.radians(pitch)
        self.f = np.array([math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)])
        self.r = np.array([math.cos(y), -math.sin(y), 0.0])
        self.u = np.cross(self.r, self.f)

    def cam_xyz(self, P):
        d = np.asarray(P, float) - self.pos
        return np.stack([d @ self.r, d @ self.u, d @ self.f], -1)

    def proj(self, P, W, H):
        c = self.cam_xyz(P)
        z = np.maximum(c[..., 2], 1e-4)
        x = W / 2 + c[..., 0] / z * self.lens / 36 * W
        y = H / 2 - c[..., 1] / z * self.lens / 20.25 * H
        return x, y, c[..., 2]

    def poly2d(self, P, W, H, near=0.2):
        """Project a world polygon with near-plane clipping -> list of (x,y)."""
        c = self.cam_xyz(P)
        out = []
        n = len(c)
        for i in range(n):
            a, b = c[i], c[(i + 1) % n]
            if a[2] >= near:
                out.append(a)
            if (a[2] >= near) != (b[2] >= near):
                t = (near - a[2]) / (b[2] - a[2]); out.append(a + t * (b - a))
        if len(out) < 3:
            return None
        o = np.array(out)
        x = W / 2 + o[:, 0] / o[:, 2] * self.lens / 36 * W
        y = H / 2 - o[:, 1] / o[:, 2] * self.lens / 20.25 * H
        return list(zip(x.tolist(), y.tolist()))

def lerp(a, b, u):
    return np.asarray(a, float) * (1 - u) + np.asarray(b, float) * u

# ====================================================================== path & events
PATH = w.WhalePath()
TAUS = np.arange(0, PATH.tau_end, 0.05)

def head_pt(t):
    return w.world_vertices(np.array([[w.XMAX, 0, 0]]), PATH.frame(t))[0]

def tail_pt(t):
    return w.world_vertices(np.array([[w.XMIN, 0, 0]]), PATH.frame(t))[0]

def _events():
    E = {}
    pos = PATH.pos(TAUS)
    E['emerge'] = float(next(t for t in TAUS if t > 5 and head_pt(t)[2] > 0))
    d = np.linalg.norm(pos[:, :2] - w.PC[:2], axis=1)
    E['over'] = float(TAUS[np.argmin(d)])
    E['contact'] = float(next(t for t in TAUS if t > E['over'] and w.moonlit(head_pt(t)[None])[0] > 0.5))
    for nm, (sx, sy) in zip(['base', 'bank', 'shoulder', 'inner', 'tip', 'side'], w.S1_SITES):
        E[nm] = float(TAUS[np.argmin(np.linalg.norm(pos[:, :2] - np.array([sx, sy]), axis=1))])
    E['cross0'] = float(next(t for t in TAUS if t > E['tip'] + 10 and pos[int(t / 0.05), 0] < 0))
    E['climb'] = float(next(t for t in TAUS if t > E['cross0'] and pos[int(t / 0.05), 2] > 118.0))   # lifts its head to the moon
    E['lip'] = float(next(t for t in TAUS if t > E['cross0'] and pos[int(t / 0.05), 2] > w.RIM_Z))
    E['top'] = float(next(t for t in TAUS if t > E['lip'] and tail_pt(t)[2] > w.TOP_Z + 2))
    return E

EV = _events()
# the one fast stroke ~2.2 s after the overhead pass, and stroke phase so that a light pulse
# lands at the petal lift (R13). Then recompute events with the final timing.
CUTS_T = [(c['id'], c['start_s'], c['end_s']) for c in SHOTLIST['cuts']]
T = {cid: (s, e) for cid, s, e in CUTS_T}

# film->world mapping: tau = tau0[cut] + (t - start). Ellipsis = jumps of tau0 between cuts.
def build_tau0(E):
    t0 = {}
    t0['R05'] = E['emerge'] - 0.6                        # head breaks the surface at ~8.6 s, facing the shore
    # R06: the frontal approach, continuous into the overhead pass (R07) - the rising turn is elided
    t0['R06'] = E['over'] - (18.6 - T['R06'][0])
    # R04: whale crossing under the diagonal band of moonlit water (before the emergence)
    ts_ = np.arange(0.0, E['emerge'], 0.05)
    d_ = [np.linalg.norm(PATH.pos(u)[:2] - np.array([-4.0, -40.0])) for u in ts_]
    t0['R04'] = float(ts_[int(np.argmin(d_))]) - 1.0
    t0['R03'] = t0['R04'] - (T['R04'][0] - T['R03'][0])
    t0['R02'] = t0['R03'] - (T['R03'][0] - T['R02'][0])
    t0['R01'] = t0['R02'] - (T['R02'][0] - T['R01'][0])
    t0['R07'] = E['over'] - (18.6 - T['R07'][0])          # overhead at 18.6 s: it holds its aim, then pulls up late
    t0['R08'] = t0['R07'] + (T['R08'][0] - T['R07'][0])   # continuous (match on action)
    t0['R09'] = E['contact'] - (22.6 - T['R09'][0])        # head touches moonlight at 22.6 s
    t0['R10'] = E['base'] - (28.2 - T['R10'][0])           # whale over S1 base at 28.2 s
    t0['R11'] = E['tip'] - 8.6                           # bloom front crosses the cape and reaches the tip in shot
    t0['R12'] = E['tip'] + 3.0
    t0['R13'] = t0['R12'] + (T['R13'][0] - T['R12'][0])   # continuous with the macro
    t0['R14'] = E['cross0'] - (44.2 - T['R14'][0])         # crossing x=0 at 44.2 s
    t0['R15'] = t0['R14'] + (T['R15'][0] - T['R14'][0])   # continuous
    t0['R17'] = E['climb'] + 1.6                         # v14.7: already on its one straight line to the moon
    t0['R18'] = E['lip'] + 0.3                             # in the slot, ~40 m from the camera
    t0['R19'] = E['top'] + 300.0                           # long ellipsis: the cave is quiet again
    return t0

TAU0 = build_tau0(EV)
LIFT_FILM = 38.5       # the light pulse that starts the lift-off, 0.5 s into R13
PATH.retime(phase0=(TAU0['R13'] + (LIFT_FILM - T['R13'][0])) - 0.44 * w.STROKE_T,
            fast_tau=EV['over'] + 2.3)
EV = _events(); TAU0 = build_tau0(EV)
TAU_LIFT = TAU0['R13'] + (LIFT_FILM - T['R13'][0])

def cut_at(t):
    for cid, s, e in CUTS_T:
        if s <= t < e:
            return cid
    return CUTS_T[-1][0]

def tau_of(t):
    cid = cut_at(t)
    return TAU0[cid] + (t - T[cid][0])

# ====================================================================== whale state
def glow_level(tau, x_local):
    """0..1 self-emission along the body: head->tail wave after contact (Phase 1),
    then pearl-opal (Phase 2-3). Never switches off."""
    dt = tau - EV['contact']
    reach = (w.XMAX - x_local) / (w.XMAX - w.XMIN) * 4.2      # tail lights ~4.2 s after the head
    return smooth((dt - reach) / 1.4)

def opal_mix(tau):
    return smooth((tau - EV['contact'] - 6.0) / 5.0)

def pulse(tau, x_local=None):
    """Light pulse that runs head->tail after each power upstroke."""
    q = PATH.stroke_q(tau)
    base = q - 0.42
    if x_local is None:
        lag = 0.0
    else:
        lag = (w.XMAX - x_local) / (w.XMAX - w.XMIN) * 0.30
    u = np.mod(base - lag, 1.0)
    return np.exp(-(u / 0.07) ** 2) + np.exp(-((u - 1) / 0.07) ** 2)

MOON_R_DEG = 2.4      # angular radius of the moon where a cut does not compose it (real moon ~0.26 deg)
# v14.4: the moon is a composed symbol (in the manner of SHAFT / TYPE-MOON): per cut it is as
# large as fits completely inside the visible opening, up to this radius (fraction of the frame
# height), placed near its true direction - in R17 where the whale is heading - and anchored in
# the opening, so the rock rim never cuts it. The moonlight direction itself stays physical.
MOON_TARGET = {'R01': 0.17, 'R19': 0.17, 'R09': 0.15, 'R17': 0.20, 'R18': 0.30}

def climax(tau):
    """0..1: the whale's light swells at the climax - v14.7: R15, as it passes closest to the
    camera (~48.3-50.0 s) - and settles again after it."""
    a = TAU0['R15'] + 2.3; b = TAU0['R15'] + 4.0
    return float(smooth((tau - a + 0.6) / 1.2) * (1 - smooth((tau - b) / 1.6)))

R18_MERGE = 3.7      # s into R18: the whale, small at the centre of the moon, melts into it

def r18_merge(t):
    """(lift, fade) for the end of R18: the whale's colour rises to the moon's, then its outline
    goes; its light is absorbed, never switched off. The moon itself does nothing (v14.6b: the
    breath of light and the rings were one explanation too many)."""
    tm = T['R18'][0] + R18_MERGE
    lift = float(smooth((t - (tm - 0.8)) / 0.8))
    fade = float(smooth((t - (tm - 0.25)) / 0.55))
    return lift, fade

# v14.6: the bloom comes in beats. On each of these strokes the whale's light flares, and every
# closed bud the flare reaches opens at once (light is the cause, FL-01): in R10 the first
# beat over the cape base; in R11 three more, which between them open all the land in view.
BLOOM_BEATS = [(27.6, 40.0), (30.2, 38.0), (31.6, 46.0), (33.0, 58.0)]   # (film s, reach m)
BEAT_TAU = [(tau_of(ft), R) for ft, R in BLOOM_BEATS]

def flare(tau):
    return float(sum(math.exp(-((tau - tb) / 0.28) ** 2) for tb, _ in BEAT_TAU))

def whale_light(tau):
    """(position, intensity) of the whale as a moving light source."""
    p = PATH.pos(tau)
    I = float(smooth((tau - EV['contact'] - 1.0) / 4.0)) * (1 + 0.25 * float(pulse(tau))) * (1 + 0.30 * climax(tau)) * (1 + 0.9 * flare(tau))
    return p, I

def glance_roll(tau):
    """The eye on the adventurers: during the last seconds of the approach the whale rolls
    ~16 deg so that one eye stays on them, holds it right over their heads, then lets go.
    It never stops."""
    rise = smooth((tau - (EV['over'] - 5.5)) / 3.0)
    fall = 1 - smooth((tau - (EV['over'] + 0.2)) / 1.5)
    return math.radians(16.0) * float(rise * fall)

ROLL_FILM = (39.0, 3.2)  # v14.6: one slow full roll in R13 (start in film s, duration s)

def joy_roll(tau):
    """v14.6: the petals let go and the whale, climbing through them, turns over once -
    a slow full roll to the left (into its turn), belly up at the middle. Not a must-have
    of the old C09 back roll; here it is a moment of release after the bloom."""
    r0 = TAU0['R13'] + (ROLL_FILM[0] - T['R13'][0])
    return -2 * math.pi * float(smooth((tau - r0) / ROLL_FILM[1]))

PLAY_FILM = (42.8, 2.8)   # v14.7: R14, it plays in the petals
LOOK_FILM = (47.9, 2.2)   # v14.7: R15, it looks at us as it passes

def play_roll(tau):
    """v14.7: R14 - rolling lazily in the river of petals: it lays over ~40 deg to the left,
    showing its pale belly, and comes back (one easy sway; the roll in R13 was the release)."""
    r0 = TAU0['R14'] + (PLAY_FILM[0] - T['R14'][0])
    u = (tau - r0) / PLAY_FILM[1]
    return -math.radians(40.0) * (math.sin(math.pi * u) ** 2 if 0 < u < 1 else 0.0)

def look_roll(tau):
    """v14.7: R15 - as it passes the camera it tips ~22 deg towards it, so that its eye is on
    us for a moment (a last look, like the glance at the adventurers in R07), then goes on."""
    r0 = TAU0['R15'] + (LOOK_FILM[0] - T['R15'][0])
    u = (tau - r0) / LOOK_FILM[1]
    return -math.radians(22.0) * (math.sin(math.pi * u) ** 2 if 0 < u < 1 else 0.0)

def glide(tau):
    """1 while the whale glides straight at the adventurers without stroking (R06-R07)."""
    a = EV['over'] - 8.0; b = EV['over'] + 0.8
    return float(smooth((tau - a) / 1.2) * (1 - smooth((tau - b) / 1.0)))

def whale_world(tau):
    fr = PATH.frame(tau, extra_roll=glance_roll(tau) + joy_roll(tau) + play_roll(tau) + look_roll(tau))
    amp = 1.9 * (1 - 0.8 * glide(tau))
    Vb = w.deform(w.BODY_V, tau, PATH, amp=amp)
    Ve = w.deform(w.EYE_V, tau, PATH, amp=amp)
    return fr, w.world_vertices(Vb, fr), w.world_vertices(Ve, fr), Vb

# ====================================================================== flowers & petals
RNG = np.random.default_rng(20261123)

FLOWER_SCALE = 8          # v14.1: ~8x the v14.0 count (a dense colony, FL-01 v0.8)

def _flowers():
    pts = []
    def keep(x, y):
        d = w.shore_y(x) - y
        return (d > 0) & (d < 26)
    for k, (sx, sy) in enumerate(w.S1_SITES):
        need = 650 * FLOWER_SCALE
        got = []
        while sum(len(g) for g in got) < need:
            x = sx + RNG.normal(0, 9.0, need); y = sy + RNG.normal(0, 9.0, need)
            ok = keep(x, y)
            got.append(np.column_stack([x[ok], y[ok]]))
        pts.append(np.vstack(got)[:need])
    # connect the sites with a band along the cape so it reads as one colony
    m = 1500 * FLOWER_SCALE
    u = RNG.random(m) * (len(w.S1_SITES) - 2)
    i = u.astype(int); f = u - i
    S = np.array(w.S1_SITES, float)
    sx = S[i, 0] * (1 - f) + S[i + 1, 0] * f; sy = S[i, 1] * (1 - f) + S[i + 1, 1] * f
    x = sx + RNG.normal(0, 7.0, m); y = sy + RNG.normal(0, 7.0, m)
    ok = keep(x, y)
    pts.append(np.column_stack([x[ok], y[ok]]))
    # v14.6: the colony is not only the band along the cape. It covers the near-shore ledges of
    # the whole east bank that the cameras see (FL-01 v0.8: dense colonies continuing along the
    # shore into the dark), in patches like moss in the cracks of the rock
    m = 30000
    x = RNG.uniform(20, 150, 4 * m); y = RNG.uniform(-100, 70, 4 * m)
    d = w.shore_y(x) - y
    patch = 0.5 + 0.5 * np.sin(x * 0.21 + 2.0 * np.sin(y * 0.13)) * np.sin(y * 0.17 + 1.7 * np.cos(x * 0.11))
    ok = (d > 0.5) & (d < 68) & (RNG.random(4 * m) < 0.30 + 0.70 * patch)
    pts.append(np.column_stack([x[ok], y[ok]])[:m])
    P = np.vstack(pts)
    z = w.ground_z(P[:, 0], P[:, 1]) + 0.06
    return np.column_stack([P, z])

FLOWERS = _flowers()
NF = len(FLOWERS)
MATURE = RNG.random(NF) < 0.8
BLOOM_R = 34.0

def _beat_open(P, jitter):
    """Bloom time of each point: the first beat whose flare reaches it (+ the few hundredths of
    a second the opening takes to start, a little later farther from the light)."""
    to = np.full(len(P), np.inf)
    for tb, R in BEAT_TAU:
        d = np.linalg.norm(P - PATH.pos(tb), axis=1)
        newly = (d < R) & ~np.isfinite(to)
        to[newly] = tb + 0.03 + 0.004 * d[newly] + RNG.uniform(0.0, jitter, newly.sum())
    return to

def _bloom_times():
    return _beat_open(FLOWERS, 0.08)

TAU_OPEN = _bloom_times()

# close-up flowers placed in front of the insert cameras (same colony / same rules)
def flower_open(tau, idx=None):
    to = TAU_OPEN if idx is None else TAU_OPEN[idx]
    return smooth((tau - to) / 0.8)          # v14.6: all at once, in under a second

def bloom_times_for(P):
    return _beat_open(P, 0.05)

def insert_flowers(cam, n, dmin, dmax, spread, seed, keep_out=None):
    r = np.random.default_rng(seed)
    f = cam.f.copy(); f[2] = 0; f = unit(f); rt = unit(np.cross(f, [0, 0, 1.0]))
    d = r.uniform(dmin, dmax, n) ** 1.0
    s = r.uniform(-spread, spread, n) * d
    xy = cam.pos[:2][None] + f[:2][None] * d[:, None] + rt[:2][None] * s[:, None]
    ok = np.array([w.is_land(a, b) for a, b in xy])
    if keep_out is not None:
        ok &= np.linalg.norm(xy - np.asarray(keep_out)[None, :2], axis=1) > 0.05
    xy = xy[ok]
    P = np.column_stack([xy, w.ground_z(xy[:, 0], xy[:, 1])])
    return P

class Petals:
    """Released petal+fruit pairs. Guided inside the whale light, pure blizzard outside,
    free fall once the whale is gone. Simulated in WORLD time."""
    def __init__(self):
        src = np.where(MATURE & np.isfinite(TAU_OPEN))[0]
        if len(src) > 31000:            # v14.6: more colony, same simulated budget (~124k flakes)
            src = np.sort(np.random.default_rng(7).choice(src, 31000, replace=False))
        per = 4
        self.src = np.repeat(src, per)
        n = len(self.src)
        self.n = n
        base = FLOWERS[self.src]
        ang = RNG.uniform(0, 2 * np.pi, n)
        self.p = base + np.column_stack([0.02 * np.cos(ang), 0.02 * np.sin(ang), np.full(n, 0.03)])
        self.v = np.zeros((n, 3))
        self.tau_detach = TAU0['R12'] + 0.9 + RNG.uniform(0, 3.0, n)
        dist_lift = np.linalg.norm(base[:, :2] - np.array([85, 30]), axis=1)
        # the lift-off spreads out from the cape tip as a wave (~2 s across the colony), so the
        # eye can follow 'the flowers let go' rather than one instant burst
        self.tau_lift = TAU_LIFT + 0.02 * dist_lift + RNG.uniform(0, 0.8, n)
        self.lift_v = RNG.uniform(3.0, 16.0, n)
        self.lift_k = RNG.uniform(1.5, 4.0, n)             # how long the magical lift lasts
        # guided petals stream behind the whale as a widening river (not a ball around it)
        self.lag = RNG.uniform(0.3, 4.5, n)
        self.off = RNG.normal(0, 1, (n, 3)) * np.array([6.0, 6.0, 3.5]) * (0.6 + 0.35 * self.lag)[:, None]
        self.sus = RNG.random(n) < 0.42                    # only some petals answer the whale
        loyal = RNG.random(n) < 0.15                       # a few follow it all the way out
        self.hold = np.where(loyal, RNG.uniform(60.0, 140.0, n), RNG.uniform(6.0, 45.0, n))
        self.gone = np.zeros(n, bool)                      # left through the fissure
        self.spin = RNG.uniform(0, 2 * np.pi, n)
        self.spin_rate = RNG.uniform(3.0, 11.0, n)
        self.g = np.zeros(n)            # guided weight
        self.fruit = np.zeros(n)        # fruit glow 0..1
        self.fset = np.zeros(n, bool)
        self.landed = np.zeros(n, bool)
        self.tau = TAU0['R12']
        self.ph = RNG.uniform(0, 100, (3,))

    def wind(self, p, tau):
        # pure blizzard: whale wake (recent path) + large slow eddies + gusts + settle
        v = np.zeros_like(p)
        # the whale's wake: drag behind it plus churning eddies (no snow-plough push in front,
        # which would pile the petals up into a shell)
        for k in range(2, 14, 2):
            tp = tau - k
            if tp < TAU0['R12'] - 20:
                continue
            wp = PATH.pos(tp); wv = PATH.vel(tp)
            d = p - wp
            d2 = np.sum(d ** 2, 1)
            wt = np.exp(-d2 / (2 * 18.0 ** 2)) * math.exp(-k / 6.0)
            ch = np.column_stack([np.sin(0.31 * d[:, 1] + 0.7 * k + tau), np.sin(0.29 * d[:, 2] + 0.9 * k - tau),
                                  np.sin(0.27 * d[:, 0] + 1.1 * k + 0.5 * tau)])
            v += wt[:, None] * (0.35 * wv[None, :] + 1.8 * ch + np.array([0, 0, 0.6]))
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        a = self.ph
        gust = 0.75 + 0.45 * np.sin(0.21 * tau + 0.013 * x + a[0])
        # large meandering air drift over the lake (no vortex centre) + eddies + gusts
        v[:, 0] += 1.5 * np.sin(0.011 * y + 0.06 * tau + a[0]) - 0.6
        v[:, 1] += 1.5 * np.cos(0.010 * x - 0.05 * tau + a[1]) + 0.7
        v[:, 0] += 1.2 * gust * np.sin(0.045 * y + 0.031 * z + 0.17 * tau + a[1])
        v[:, 1] += 1.2 * gust * np.sin(0.041 * x - 0.027 * z + 0.13 * tau + a[2])
        v[:, 2] += 0.6 * gust * np.sin(0.05 * x + 0.04 * y + 0.23 * tau)
        # smaller eddies: break up coherent sheets and domes
        v[:, 0] += 0.9 * np.sin(0.21 * y + 0.17 * z + 0.9 * tau + a[2])
        v[:, 1] += 0.9 * np.sin(0.19 * z + 0.23 * x + 0.7 * tau + a[0])
        v[:, 2] += 0.8 * np.sin(0.18 * x + 0.22 * y + 1.1 * tau + a[1])
        v[:, 2] -= 0.42
        return v

    def step(self, tau_to, dt=1 / 24):
        while self.tau < tau_to - 1e-9:
            h = min(0.25 if tau_to - self.tau > 5.0 else dt, tau_to - self.tau)   # coarse across an ellipsis
            self._step(self.tau, h)
            self.tau += h

    def _step(self, tau, h):
        detached = tau >= self.tau_detach
        lifted = tau >= self.tau_lift
        hover = detached & ~lifted
        free = lifted & ~self.landed & ~self.gone
        nd = detached & ~self.fset
        self.fruit[nd] = 1.0; self.fset |= nd
        if tau > EV['top'] + 2:                       # the whale has gone: every fruit fades
            self.fruit *= math.exp(-h / 5.0)
        # hover: the guided signature (no gravity, no spin)
        self.p[hover, 2] += 0.12 * h * np.exp(-(tau - self.tau_detach[hover]) * 2)
        if not free.any():
            return
        idx = np.where(free)[0]
        p = self.p[idx]
        wp, I = whale_light(tau)
        gone = tau > EV['top'] + 2
        d = np.linalg.norm(p - wp, axis=1)
        light = I / (1 + (d / 42.0) ** 2) * (0.0 if gone else 1.0)
        age = tau - self.tau_lift[idx]
        g = smooth((light - 0.22) / 0.33) * (self.sus[idx] & (age < self.hold[idx]))
        # guided flow: drift along the whale's recent path with a lag, ordered, not converging
        tgt = PATH.pos(np.clip(tau - self.lag[idx], 0, None)) + self.off[idx]
        vg = 0.45 * PATH.vel(tau)[None, :] + 0.32 * (tgt - p)
        sp = np.linalg.norm(vg, axis=1, keepdims=True); vg *= np.minimum(1, 9.0 / np.maximum(sp, 1e-6))
        vp = self.wind(p, tau)
        if gone:
            vp = vp * 0.35 + np.array([0, 0, -0.9])
        # magical lift right after the light pulse
        lift = self.lift_v[idx] * np.exp(-age / self.lift_k[idx]) * (age >= 0)
        vt = g[:, None] * vg + (1 - g[:, None]) * vp
        vt[:, 2] += lift
        k = np.where(g > 0.5, 1.6, 1.0)[:, None]
        self.v[idx] += (vt - self.v[idx]) * np.minimum(1, k * h / 0.8)
        self.p[idx] += self.v[idx] * h
        self.g[idx] = g
        self.spin[idx] += self.spin_rate[idx] * h * (1 - 0.88 * g)
        # fruit glow: kept while guided, fades after the whale has gone
        # petals that followed the whale out through the fissure leave the cave
        out = self.p[idx, 2] > w.TOP_Z + 70
        self.gone[idx[out]] = True
        # ground / water contact
        gz = w.ground_z(self.p[idx, 0], self.p[idx, 1])
        hit = self.p[idx, 2] <= gz + 0.01
        if hit.any():
            j = idx[hit]
            self.p[j, 2] = gz[hit] + 0.01; self.v[j] = 0; self.landed[j] = True

# last petal: a single scripted petal falling into the moonlight at R19
def last_petal(t):
    s, e = T['R19']
    land_t = 67.5
    P_land = np.array([w.P0[0] + 2.0, w.P0[1] + 36.0, 0.02])     # where the opening drop fell (R01)
    u = (t - (land_t - 3.0)) / 3.0
    if u < 0:
        return None, None
    if u >= 1:
        return P_land, (t - land_t)
    k = u
    pos = P_land + np.array([1.6 * math.sin(4.0 * k) * (1 - k), -0.8 * (1 - k), 6.5 * (1 - k) ** 1.15])
    return pos, None

# ====================================================================== drawing helpers
def bg(W, H, top=(7, 10, 16), bot=(11, 15, 21)):
    g = np.linspace(0, 1, H)[:, None]
    a = (np.array(top)[None, :] * (1 - g) + np.array(bot)[None, :] * g)
    return np.repeat(a[:, None, :], W, 1).astype(np.float32)

STAR = None
def stars():
    global STAR
    if STAR is None:
        r = np.random.default_rng(7)
        el = np.radians(r.uniform(25, 89, 700)); az = r.uniform(-np.pi, np.pi, 700)
        STAR = (np.column_stack([np.cos(el) * np.sin(az), np.cos(el) * np.cos(az), np.sin(el)]), r.uniform(0.3, 1.0, 700))
    return STAR

def splat(buf, x, y, col, W, H):
    xi = np.round(x).astype(int); yi = np.round(y).astype(int)
    ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
    if not ok.any():
        return
    col = np.asarray(col, np.float32)
    if col.ndim == 1:
        col = np.broadcast_to(col, (len(x), 3))
    np.add.at(buf, (yi[ok], xi[ok]), col[ok])

def beam_slices(levels):
    """Effective moon-beam cross-sections (world polygons) at given heights."""
    ys = np.linspace(24, 250, 46)
    xs_l = np.interp(ys, [r[0] for r in w.FISSURE], [r[1] for r in w.FISSURE])
    xs_r = np.interp(ys, [r[0] for r in w.FISSURE], [r[2] for r in w.FISSURE])
    c = (xs_l + xs_r) / 2; hw = (xs_r - xs_l) / 2
    out = []
    t43 = math.tan(w.MOON_ELEV)
    for z in levels:
        db = (w.RIM_Z - z) / t43; dt_ = (w.TOP_Z - z) / t43
        yy = np.linspace(24 - dt_, 250 - db, 60)
        lb = np.interp(yy + db, ys, c - hw, left=np.nan, right=np.nan)
        rb = np.interp(yy + db, ys, c + hw, left=np.nan, right=np.nan)
        lt = np.interp(yy + dt_, ys, c - hw * w.TOP_NARROW, left=np.nan, right=np.nan)
        rt = np.interp(yy + dt_, ys, c + hw * w.TOP_NARROW, left=np.nan, right=np.nan)
        L = np.fmax(lb, lt); R = np.fmin(rb, rt)
        ok = np.isfinite(L) & np.isfinite(R) & (R > L)
        if ok.sum() < 2:
            continue
        left = [(L[i], yy[i], z) for i in np.where(ok)[0]]
        right = [(R[i], yy[i], z) for i in np.where(ok)[0]][::-1]
        out.append(np.array(left + right))
    return out

BEAM = beam_slices(np.concatenate([np.arange(185, 30, -12.0), np.arange(30, 0, -5.0), [1.0]]))
WATER_POLY = np.array([(x, w.shore_y(x), 0.0) for x in np.linspace(-260, 260, 105)] +
                      [(260, 700, 0.0), (-260, 700, 0.0)])

class Ground:
    """Land mesh for one camera: fine cells near the camera, coarse far away."""
    def __init__(self, cam):
        quads = []
        cx, cy = cam.pos[0], cam.pos[1]
        low = cam.pos[2] - w.ground_z(cx, cy) < 3
        for x in np.arange(-260, 260, 10.0):
            for y in np.arange(-260, 120, 10.0):
                if low and abs(x + 5 - cx) < 16 and abs(y + 5 - cy) < 16:
                    continue
                quads.append((x, y, 10.0))
        if low:                                       # ground-level camera: fine patch
            for x in np.arange(cx - 16, cx + 16, 1.0):
                for y in np.arange(cy - 16, cy + 16, 1.0):
                    quads.append((x, y, 1.0))
        Q = []
        def add(x, y, s, depth=0):
            xs = np.array([x, x + s, x + s, x]); ys = np.array([y, y, y + s, y + s])
            land = w.is_land(xs, ys)
            if not land.any():
                return
            if not land.all() and depth < 3:
                h = s / 2
                for dx in (0, h):
                    for dy in (0, h):
                        add(x + dx, y + dy, h, depth + 1)
                return
            if not land.all():
                # clip to the shoreline: replace water corners by shore points
                ys = np.minimum(ys, w.shore_y(xs) - 0.01)
            zs = w.ground_z(xs, ys)
            Q.append(np.column_stack([xs, ys, zs]))
        for x, y, s in quads:
            add(x, y, s)
        self.Q = np.array(Q)
        cen = self.Q.mean(1)
        self.cen = cen
        self.moon = w.moonlit(cen + np.array([0, 0, 0.3]))
        self.tex = np.random.default_rng(5).uniform(0.78, 1.18, len(cen))
        self.landfrac = np.array([w.is_land(q[:, 0], q[:, 1]).mean() for q in self.Q])
        c = cam.cam_xyz(cen)
        self.keep = c[:, 2] > -10

    def draw(self, dr, cam, W, H, wl_p, wl_I, extra=0.0):
        cz = cam.cam_xyz(self.Q.reshape(-1, 3)).reshape(-1, 4, 3)
        zc = cz[:, :, 2]
        anyfront = zc.max(1) > 0.15
        allfront = zc.min(1) > 0.2
        zz = np.maximum(zc, 1e-3)
        sx = W / 2 + cz[:, :, 0] / zz * cam.lens / 36 * W
        sy = H / 2 - cz[:, :, 1] / zz * cam.lens / 20.25 * H
        onscr = ~allfront | ((sx.max(1) > -50) & (sx.min(1) < W + 50) & (sy.max(1) > -50) & (sy.min(1) < H + 50))
        cand = np.where(anyfront & onscr)[0]
        c = zc.mean(1)
        order = cand[np.argsort(-c[cand])]
        d = np.linalg.norm(self.cen - wl_p, axis=1)
        wl = wl_I * 1.3 / (1 + (d / 24.0) ** 2)
        base = np.array([17, 18, 18], float)
        fade = 0.45 + 0.55 * np.exp(-np.linalg.norm(self.cen - cam.pos, axis=1) / 90.0)
        for i in order:
            if allfront[i]:
                pts = list(zip(sx[i].tolist(), sy[i].tolist()))
            else:
                pts = cam.poly2d(self.Q[i], W, H)
            if pts is None:
                continue
            L = (0.55 + 0.9 * self.moon[i] + wl[i] + extra) * self.tex[i] * fade[i]
            col = base * L + np.array([14, 18, 26]) * self.moon[i] * fade[i] + np.array([34, 36, 40]) * wl[i]
            dr.polygon(pts, fill=tuple(int(v) for v in np.clip(col, 0, 255)))

def draw_flower(dr, cam, W, H, p, openness, light, seed, released=0.0, sway=None):
    """Detailed flower for close-ups: nodding grey-brown bud -> stem rises -> 5 petals open."""
    r = np.random.default_rng(seed)
    stem_h = 0.045 + 0.03 * openness
    nod = math.radians(70 * (1 - openness))
    az = r.uniform(0, 2 * np.pi)
    base = np.asarray(p, float)
    top = base + np.array([math.sin(nod) * math.cos(az) * 0.03, math.sin(nod) * math.sin(az) * 0.03, stem_h])
    if sway is not None:
        top = top + np.asarray(sway, float)
    sx, sy, sz = cam.proj(np.array([base, top]), W, H)
    if np.any(sz < 0.05):
        return
    lw = max(1, int(cam.lens / 36 * W * 0.003 / max(0.05, sz[0])))
    dr.line([(sx[0], sy[0]), (sx[1], sy[1])], fill=tuple(int(v) for v in np.clip(np.array([40, 60, 52]) * (0.4 + light), 0, 255)), width=lw)
    # head axis
    n = unit(np.array([math.sin(nod) * math.cos(az), math.sin(nod) * math.sin(az), math.cos(nod)]))
    a1 = unit(np.cross(n, [0.3, 0.2, 1.0] if abs(n[2]) < 0.9 else [1, 0, 0])); a2 = np.cross(n, a1)
    petal_len = 0.02
    spread = math.radians(15 + 52 * openness)
    cols = []
    for k in range(5):
        if released and k < int(round(released * 4)):
            continue
        ang = 2 * np.pi * k / 5 + az
        rad = math.cos(ang) * a1 + math.sin(ang) * a2
        tipd = unit(math.sin(spread) * rad + math.cos(spread) * n)
        side = unit(np.cross(tipd, n) if np.linalg.norm(np.cross(tipd, n)) > 1e-6 else a1)
        poly = [top, top + tipd * petal_len * 0.5 + side * 0.006, top + tipd * petal_len, top + tipd * petal_len * 0.5 - side * 0.006]
        cols.append(poly)
    petal_col = np.array([236, 231, 214]) * (0.18 + 1.05 * light)
    sepal_col = np.array([96, 84, 66]) * (0.25 + 0.9 * light)
    for poly in cols:
        pts = cam.poly2d(np.array(poly), W, H)
        if pts:
            dr.polygon(pts, fill=tuple(int(v) for v in np.clip(petal_col * (0.25 + 0.75 * openness) + sepal_col * (1 - openness) * 0.75, 0, 255)))
    # sepals cover the bud while closed
    if openness < 0.8:
        for k in range(5):
            ang = 2 * np.pi * (k + 0.5) / 5 + az
            rad = math.cos(ang) * a1 + math.sin(ang) * a2
            tipd = unit(math.sin(spread * 0.6) * rad + math.cos(spread * 0.6) * n)
            side = unit(np.cross(tipd, n) if np.linalg.norm(np.cross(tipd, n)) > 1e-6 else a1)
            poly = [top, top + tipd * 0.012 + side * 0.005, top + tipd * 0.017, top + tipd * 0.012 - side * 0.005]
            pts = cam.poly2d(np.array(poly), W, H)
            if pts:
                dr.polygon(pts, fill=tuple(int(v) for v in np.clip(sepal_col * (1 - openness * 0.6), 0, 255)))
    if openness > 0.35:
        cx, cy, cz = cam.proj(top[None], W, H)
        rr = max(1, cam.lens / 36 * W * 0.0035 / max(0.05, cz[0]))
        cc = np.array([214, 180, 104]) * (0.2 + light) * min(1.0, (openness - 0.35) / 0.4) + sepal_col * (1 - min(1.0, (openness - 0.35) / 0.4))
        dr.ellipse((cx[0] - rr, cy[0] - rr, cx[0] + rr, cy[0] + rr), fill=tuple(int(v) for v in np.clip(cc, 0, 255)))

def flower_petal_poly(p, openness, seed, k):
    """Same geometry as draw_flower for petal k (used by the scripted macro release)."""
    r = np.random.default_rng(seed)
    stem_h = 0.045 + 0.03 * openness
    nod = math.radians(70 * (1 - openness))
    az = r.uniform(0, 2 * np.pi)
    base = np.asarray(p, float)
    top = base + np.array([math.sin(nod) * math.cos(az) * 0.03, math.sin(nod) * math.sin(az) * 0.03, stem_h])
    n = unit(np.array([math.sin(nod) * math.cos(az), math.sin(nod) * math.sin(az), math.cos(nod)]))
    a1 = unit(np.cross(n, [0.3, 0.2, 1.0] if abs(n[2]) < 0.9 else [1, 0, 0])); a2 = np.cross(n, a1)
    spread = math.radians(15 + 52 * openness)
    ang = 2 * np.pi * k / 5 + az
    rad = math.cos(ang) * a1 + math.sin(ang) * a2
    tipd = unit(math.sin(spread) * rad + math.cos(spread) * n)
    side = unit(np.cross(tipd, n))
    L = 0.02
    return np.array([top, top + tipd * L * 0.5 + side * 0.006, top + tipd * L, top + tipd * L * 0.5 - side * 0.006]), top, tipd

def tone(A, k=170.0, s=110.0):
    """Soft highlight shoulder: keeps the glowing whale from clipping to flat white."""
    A = np.asarray(A, np.float32)
    e = np.maximum(A - k, 0.0)
    return np.where(A > k, k + e / (1 + e / s), A)

# ====================================================================== cameras per cut
def C_static(pos, target, lens):
    cam = Cam(pos, target=target, lens=lens)
    return lambda t, tau: cam

def C_pan(pos, t0, t1, tgt0, tgt1, lens):
    def f(t, tau):
        u = smooth((t - t0) / (t1 - t0))
        return Cam(pos, target=lerp(tgt0, tgt1, u), lens=lens)
    return f

def C_follow(back=-12.5, side=37.5, up=7.8, lens=41.0, drift=1.5):
    """Author-approved N14 side-follow (②, 'slightly larger'); the camera trails slightly
    slower than the whale so it drifts inside the frame instead of being pinned."""
    def f(t, tau):
        p, fwd, left, upv = PATH.frame(tau)
        hs = unit(np.cross([0, 0, 1.0], fwd))
        s, e = T['R15']
        lagm = drift * (t - s)                       # whale gains ~1.5 m/s on the camera
        pos = p + (back - lagm) * fwd + side * hs + up * np.array([0, 0, 1.0])
        tgt = p - 4.0 * fwd + 1.2 * upv              # aim slightly behind the head: lead room
        return Cam(pos, target=tgt, lens=lens)
    return f

def C_dolly(p0, p1, t0, t1, target, lens):
    def f(t, tau):
        u = smooth((t - t0) / (t1 - t0))
        return Cam(lerp(p0, p1, u), target=target, lens=lens)
    return f

def wp(tau):
    return PATH.pos(tau)

GZ = lambda x, y: float(w.ground_z(x, y))
CAM_A = ((-18.0, -93.0, 3.0), None, -24.0, 18.5, 18.0)

def make_cameras():
    C = {}
    camA = Cam(CAM_A[0], yaw=CAM_A[2], pitch=CAM_A[3], lens=CAM_A[4])
    C['R01'] = lambda t, tau: camA
    p0 = w.P0
    # R02: low, across the edge of the moonlight: P0 open in front, buds behind in shadow
    C['R02'] = C_static((p0[0] + 0.26, p0[1] + 0.08, p0[2] + 0.10), (p0[0] - 1.4, p0[1] - 0.62, p0[2] + 0.03), 35)
    # R03: just above the water; the swell from below arrives through the moonlit water
    C['R03'] = C_static((-4.0, -57.5, 0.9), (8.0, -45.0, 0.0), 24)
    # R04: frontal from the shore; the dark mass passes under the moonlit water
    C['R04'] = C_static((-6.0, -67.5, GZ(-6, -67.5) + 3.4), (-3.0, -50.0, -2.0), 24)
    # R05: from the adventurers' shore, low; the whale surfaces facing us
    em = PATH.pos(EV['emerge'] + 1.0)
    C['R05'] = C_static((-56.5, -62.0, GZ(-56.5, -62.0) + 0.9), (em[0], em[1], 1.8), 40)
    # R06: beside the adventurers; it glides straight at us and its head leaves the top of frame
    a6 = PATH.pos(TAU0['R06']); b6 = PATH.pos(TAU0['R06'] + (T['R06'][1] - T['R06'][0]))
    c6 = np.array([-52.0, -90.0, GZ(-52, -90) + 1.7])
    m6 = (a6 + b6) / 2
    C['R06'] = C_static(tuple(c6), (m6[0], m6[1], c6[2] + np.linalg.norm(m6[:2] - c6[:2]) * math.tan(math.radians(5))), 35)
    # R07: the adventurers' eyes, looking up towards the lake it comes from
    C['R07'] = C_static(tuple(w.PC_EYE), (w.PC_EYE[0] - 2.0, w.PC_EYE[1] + 22.0, w.PC_EYE[2] + 10.5), 16)
    # R08: turning round: the tail leaves, one strong stroke, and the moonlight it heads for
    C['R08'] = C_static(tuple(w.PC_EYE), (w.PC_EYE[0] + 10.0, w.PC_EYE[1] - 17.0, w.PC_EYE[2] + 6.0), 18)
    c9 = (-1.5, -172.0, 4.0)
    C['R09'] = C_pan(c9, T['R09'][0] + 0.2, T['R09'][1] - 0.3,
                     wp(TAU0['R09'] + 0.6) + np.array([3, 0, 9.5]), wp(TAU0['R09'] + 4.8) + np.array([8, 0, 10.5]), 28)
    b = wp(EV['base'])
    gb = GZ(b[0] - 6, b[1] - 9)
    # R10 (v14.6): down among the buds of the base colony, just above them: a bed of grey-brown,
    # nodding buds that look like dead grass fills the frame; the whale passes overhead out of
    # frame, its light floods in from the top, flares once - and every bud opens at once
    gb = GZ(b[0] - 4.0, b[1] - 7.0)
    C['R10'] = C_static((b[0] - 4.0, b[1] - 7.0, gb + 0.22), (b[0] - 3.0, b[1] - 4.2, gb - 0.50), 24)
    C['R11'] = C_static((100.0, -36.0, 14.0), (70.0, 6.0, 6.0), 24)
    tip = np.array([85.0, 30.0]); gt = GZ(78.0, 20.0)
    C['R12'] = C_static((78.0 - 0.09, 20.0 - 0.12, gt + 0.245), (78.0, 20.0, gt + 0.065), 80)
    # R13 (v14.6): low over the dark lake, looking back at the cape: the whole colony lets go
    # along the horizon and the whale comes towards us out of it, climbing, and turns over
    # once in the rising petals. Static: it rises through the frame and leaves at the top.
    c13 = np.array([28.7, 119.7, 1.0])
    b13, p13 = math.radians(-42.0), math.radians(20.0)
    C['R13'] = C_static(tuple(c13), tuple(c13 + 100 * np.array([math.cos(b13) * math.cos(p13), math.sin(b13) * math.cos(p13), math.sin(p13)])), 24)
    C['R14'] = C_static((-30.0, -58.0, GZ(-30, -58) + 1.7), wp(TAU0['R14'] + 2.0) + np.array([0, 0, -1]), 90)
    # R15 (v14.6b): 'like filming a train' - someone standing ~16 m off its line, a little
    # below it: the head comes in from the right, and as it passes the camera turns its head
    # to follow (a little late, like a person), keeps the whole 24 m body in frame at the
    # closest point, and keeps watching it climb away up to the left: the shot ends on its
    # back, leaving - 'where is it going?'
    a15 = TAU0['R15']
    P15 = PATH.pos(a15 + 3.0); h15 = unit(PATH.vel(a15 + 3.0) * np.array([1, 1, 0])); n15 = np.array([-h15[1], h15[0], 0])
    n15 = n15 if n15[1] < 0 else -n15
    c15 = P15 + 16.0 * n15 + np.array([0, 0, -3.0])
    g15 = PATH.pos(a15 + 2.4) + np.array([0, 0, -1.0])
    def r15(t, tau, c=c15, g0=g15):
        pm = PATH.pos(np.linspace(tau - 0.5, tau, 7)).mean(0)          # the eye lags a little
        g1 = pm + unit(PATH.vel(tau)) * 2.0
        k = smooth((t - 47.0) / 1.4)                                   # starts turning as it comes close
        return Cam(tuple(c), target=tuple(g0 * (1 - k) + g1 * k), lens=18)
    C['R15'] = r15
    # R17 (v14.7): 'straight on, to the moon'. The camera rides the same straight line behind it
    # (~30 m back, a few metres to the sky side of the line), looking along the line: the moon is
    # composed at the line's vanishing point, the centre of the frame, and the whale - just below
    # it - shrinks up into it, stroking hard (it lifted its head onto this line off screen).
    u = w.EXIT_DIR
    n_up = unit(np.array([0, 0, 1.0]) - u[2] * u)
    z17 = float(PATH.pos(TAU0['R17'])[2])
    p17 = w.EXIT_P0 + u * ((z17 - w.EXIT_P0[2]) / u[2])
    c17a = p17 - u * 30.0 + n_up * 6.5; c17b = c17a + u * 16.0
    def r17(t, tau, a=c17a, b=c17b, s0=T['R17'][0], s1=T['R17'][1], u=u):
        c = lerp(a, b, smooth((t - s0) / (s1 - s0)))
        return Cam(tuple(c), target=tuple(c + u * 1000.0), lens=24)
    C['R17'] = r17
    # R18 (v14.5): the camera stops just under the opening, beside the whale's line, and lets
    # it go: the whale passes it, climbs out of the slot and flies straight on along EXIT_DIR,
    # shrinking towards the vanishing point of that line, where the moon is composed (dead
    # centre of the frame). It never leaves the opening - it goes into the moon.
    u = w.EXIT_DIR
    n_up = unit(np.array([0, 0, 1.0]) - u[2] * u)
    base = w.EXIT_P0 - u * ((200.0 - 160.0) / u[2])
    c18 = base + 4.5 * (0.3 * np.array([1.0, 0, 0]) + 0.95 * n_up)
    C['R18'] = C_static(tuple(c18), tuple(c18 + u * 100.0), 40)
    C['R19'] = lambda t, tau: camA
    return C

# ====================================================================== render one frame
class Renderer:
    def __init__(self, W=1280, H=720):
        self.W, self.H = W, H
        self.cams = make_cameras()
        self.ground = {}
        # close-up flowers in front of the insert cameras (R10 bloom wave, R12 macro)
        self.inserts = {}
        c10 = self.cams['R10'](T['R10'][0], TAU0['R10'])
        P10 = insert_flowers(c10, 900, 0.25, 5.5, 1.0, 10)
        self.inserts['R10'] = (P10, bloom_times_for(P10), np.ones(len(P10), bool))   # v14.7: all mature - every bud in frame opens
        c12 = self.cams['R12'](T['R12'][0], TAU0['R12'])
        hero = np.array([[78.0, 20.0, GZ(78.0, 20.0)]])
        P12 = np.vstack([hero, insert_flowers(c12, 14, 0.25, 1.6, 0.6, 12, keep_out=hero[0])])
        to12 = bloom_times_for(P12); to12[0] = min(to12[0], EV['tip'])
        self.inserts['R12'] = (P12, to12, np.ones(len(P12), bool))
        self.petals = Petals()
        self.font = ImageFont.truetype(FONT_PATH, max(12, H // 48)) if Path(FONT_PATH).exists() else ImageFont.load_default()
        self.stats = []

    def gnd(self, cid, cam):
        key = cid
        if key not in self.ground:
            self.ground[key] = Ground(cam)
        return self.ground[key]

    # ------------------------------------------------------------------ whale
    def whale_layer(self, cam, tau, mirror=False, show=True, hide_under=False):
        W, H = self.W, self.H
        fr, Vb, Ve, Vloc = whale_world(tau)
        if mirror:
            Vb = Vb * np.array([1, 1, -1]); Ve = Ve * np.array([1, 1, -1])
        tri = Vb[w.BODY_F]
        cen = tri.mean(1)
        c = cam.cam_xyz(cen)
        vis = c[:, 2] > 0.3
        sgn = -1.0 if mirror else 1.0
        cross = np.zeros(len(tri), bool)
        if hide_under:                                 # dark water at night: nothing shows below the surface
            zz = tri[:, :, 2] * sgn
            vis &= zz.max(1) > 0.0
            cross = vis & (zz.min(1) < 0.0)            # clipped exactly at the waterline below
        # rock canopy occlusion above the rim
        if not mirror and cen[:, 2].max() > w.RIM_Z:
            vis &= w.sight_through_opening(cam.pos, cen) > 0.5
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
        view = unit(cam.pos - fr[0])
        xl = Vloc[w.BODY_F][:, :, 0].mean(1)
        zl = Vloc[w.BODY_F][:, :, 2].mean(1)
        # moonlight
        ml = w.moonlit(cen) if not mirror else w.moonlit(cen * np.array([1, 1, -1]))
        lam = np.abs(n @ w.MOON_DIR)
        facing = np.abs(n @ unit(cam.pos - cen.mean(0)))
        rim = (1 - facing) ** 2.2
        upn = np.clip(n[:, 2] * (-1 if mirror else 1), 0, 1)
        ambient = 0.17
        dorsal = clamp((zl + 1.0) / 3.0)                   # navy back, pale belly, both dim before ignition
        skin0 = np.array([40, 52, 74])[None, :] * dorsal[:, None] + np.array([84, 92, 104])[None, :] * (1 - dorsal[:, None])
        g = glow_level(tau, xl)
        pul = pulse(tau, xl)
        mix = opal_mix(tau)
        # Phase 1: ice blue / silver / lavender ; Phase 2-3: pearl-opal varying along the body
        ph1 = np.array([170, 205, 236])[None, :] * (0.5 + 0.5 * np.cos(xl * 0.35 + tau * 0.8))[:, None] + \
              np.array([196, 182, 236])[None, :] * (0.5 - 0.5 * np.cos(xl * 0.35 + tau * 0.8))[:, None]
        hue = (xl - w.XMIN) / (w.XMAX - w.XMIN) + 0.08 * math.sin(tau * 0.3)
        wts = np.stack([clamp(1 - np.abs(hue - 0.85) * 3), clamp(1 - np.abs(hue - 0.55) * 3),
                        clamp(1 - np.abs(hue - 0.30) * 3), clamp(1 - np.abs(hue - 0.08) * 4)], 1)
        cols = np.array([[184, 216, 240], [234, 238, 242], [214, 208, 238], [228, 226, 212]], float)
        ws = wts.sum(1, keepdims=True)
        opal = (wts @ cols + np.array([226, 230, 236])[None, :] * clamp(1 - ws)) / np.maximum(ws, 1.0)
        emis = ph1 * (1 - mix) + opal * mix
        sky = 0.40 * upn                                   # faint light from the night sky above
        lit = skin0 * (ambient + sky + 0.9 * ml * lam)[:, None] + np.array([120, 138, 160])[None, :] * (rim * (0.24 + 0.4 * upn + 0.6 * ml))[:, None]
        form = 0.40 + 0.60 * facing                        # keep the 3D form inside the glow
        col = lit * (1 - g[:, None]) + emis * (g * 0.70 * form * (1 + 0.18 * pul) * (1 + 0.22 * climax(tau)) * (1 + 0.45 * flare(tau)))[:, None]
        col = tone(col)
        under = cen[:, 2] < -0.05 if not mirror else np.zeros(len(cen), bool)
        if under.any():
            dep = clamp(-cen[under, 2] / 6.0)
            col[under] = col[under] * (0.35 - 0.25 * dep)[:, None] + np.array([10, 16, 24]) * 0.5
        if mirror:
            # the lake is a dark mirror (it never glows itself); at grazing angles it reflects more
            col *= 0.52 if cam.pos[2] < 2.0 else 0.32
        order = np.argsort(-c[:, 2])
        x, y, z = cam.proj(tri.reshape(-1, 3), W, H)
        X = x.reshape(-1, 3); Y = y.reshape(-1, 3)
        img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        em = Image.new('L', (W, H), 0)
        dr = ImageDraw.Draw(img); de = ImageDraw.Draw(em)
        drawn = 0
        for i in order:
            if not vis[i] or not show:
                continue
            if cross[i]:
                poly = []
                P3 = tri[i]
                for a_, b_ in ((0, 1), (1, 2), (2, 0)):
                    za, zb = P3[a_, 2] * sgn, P3[b_, 2] * sgn
                    if za >= 0:
                        poly.append(P3[a_])
                    if (za >= 0) != (zb >= 0):
                        u = za / (za - zb)
                        poly.append(P3[a_] + (P3[b_] - P3[a_]) * u)
                if len(poly) < 3:
                    continue
                px_, py_, _ = cam.proj(np.array(poly), W, H)
                xs, ys = px_, py_
            else:
                xs, ys = X[i], Y[i]
            if xs.max() < -W or xs.min() > 2 * W or ys.max() < -H or ys.min() > 2 * H:
                continue
            pts = list(zip(xs.tolist(), ys.tolist()))
            cc = tuple(int(v) for v in np.clip(col[i], 0, 255))
            dr.polygon(pts, fill=cc + (255,))
            if g[i] > 0.02:
                de.polygon(pts, fill=int(255 * min(1, g[i] * (0.8 + 0.4 * pul[i]))))
            drawn += 1
        # eyes (dark, one moon glint in Phase 0)
        if show:
            etri = Ve[w.EYE_F]; ec = cam.cam_xyz(etri.mean(1))
            ex, ey, ez = cam.proj(etri.reshape(-1, 3), W, H)
            EX = ex.reshape(-1, 3); EY = ey.reshape(-1, 3)
            for i in np.argsort(-ec[:, 2]):
                if ec[i, 2] > 0.3:
                    dr.polygon(list(zip(EX[i], EY[i])), fill=(6, 8, 12, 255))
        info = dict(drawn=drawn, depth=float(cam.cam_xyz(fr[0][None])[0, 2]))
        sx, sy, sz = cam.proj(Vb, W, H)
        okv = sz > 0.3
        if okv.any():
            info['bbox'] = [float(sx[okv].min()), float(sy[okv].min()), float(sx[okv].max()), float(sy[okv].max())]
        info['min_dist'] = float(np.min(np.linalg.norm(Vb - cam.pos, axis=1)))
        return img, em, info

    # ------------------------------------------------------------------ frame
    def frame(self, t):
        W, H = self.W, self.H
        cid = cut_at(t); tau = tau_of(t)
        cam = self.cams[cid](t, tau)
        show_whale = cid not in ('R01', 'R02', 'R03', 'R19', 'R12')
        # --- background & sky through the thick opening
        A = bg(W, H)
        img = Image.fromarray(A.astype(np.uint8))
        dr = ImageDraw.Draw(img)
        bot = cam.poly2d(np.array(w.rim_polygon(w.RIM_Z)), W, H)
        top = cam.poly2d(np.array(w.rim_polygon(w.TOP_Z)), W, H)
        hole = None
        if bot and top:
            mb = Image.new('L', (W, H), 0); ImageDraw.Draw(mb).polygon(bot, fill=255)
            mt = Image.new('L', (W, H), 0); ImageDraw.Draw(mt).polygon(top, fill=255)
            hole = np.minimum(np.asarray(mb), np.asarray(mt)).astype(np.float32) / 255
            wall = (np.asarray(mb).astype(np.float32) / 255) * (1 - hole)
            sky = np.zeros((H, W, 3), np.float32)
            gy = np.linspace(0, 1, H)[:, None, None]
            sky[:] = np.array([20, 32, 62], np.float32) * (1 - gy) + np.array([30, 46, 80], np.float32) * gy
            A = np.asarray(img).astype(np.float32)
            A = A * (1 - hole[..., None]) + sky * hole[..., None]
            A = A * (1 - wall[..., None]) + np.array([14, 17, 22], np.float32) * wall[..., None]
            sd, sb = stars()
            sx, sy, sz = cam.proj(cam.pos + sd * 1e5, W, H)
            add = np.zeros((H, W, 3), np.float32)
            okz = sz > 0
            splat(add, sx[okz], sy[okz], (np.array([210, 220, 240])[None, :] * sb[okz, None] * 0.55), W, H)
            A += add * hole[..., None]
            # the moon as a composed symbol (v14.4): see draw_moon
            self.draw_moon(A, cam, cid, hole, t)
            img = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)); dr = ImageDraw.Draw(img)
        # --- canopy rock lit by the whale on the way out (R17/R18)
        wl_p, wl_I = whale_light(tau)
        if cid in ('R17', 'R18') and wl_I > 0.05:
            A = np.asarray(img).astype(np.float32)
            # R18: the camera is inside the slot, close to the light; keep the rock darker than
            # the moon so that the moon stays the brightest thing in the frame
            kc = 0.5 if cid == 'R18' else 1.0
            A += self.canopy_light(cam, tau, wl_p, wl_I * kc) * (1 - (hole if hole is not None else 0))[..., None]
            img = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)); dr = ImageDraw.Draw(img)
        # --- water & land
        wpts = cam.poly2d(WATER_POLY, W, H)
        water_mask = Image.new('L', (W, H), 0)
        if wpts:
            dr.polygon(wpts, fill=(12, 18, 27))
            ImageDraw.Draw(water_mask).polygon(wpts, fill=255)
        # moonlit water near the shore + whale light on the water
        for sl in BEAM[-1:]:
            pts = cam.poly2d(sl * np.array([1, 1, 0]), W, H)
            if pts:
                lay = Image.new('L', (W, H), 0); ImageDraw.Draw(lay).polygon(pts, fill=110)
                lay = lay.filter(ImageFilter.GaussianBlur(W / 90))
                m = np.asarray(lay).astype(np.float32) / 255 * np.asarray(water_mask).astype(np.float32) / 255
                A = np.asarray(img).astype(np.float32) + m[..., None] * np.array([46, 58, 74], np.float32)
                img = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)); dr = ImageDraw.Draw(img)
        G = self.gnd(cid, cam)
        G.draw(dr, cam, W, H, wl_p, wl_I if wl_p[2] < 90 else wl_I * 0.3)
        # --- ripples (R01 drop, R03 from below) and the last petal ripple (R19)
        rings = []
        if cid == 'R01':
            c0 = np.array([w.P0[0] + 2.0, w.P0[1] + 36.0, 0.0])
            for k, ts in enumerate((0.75,)):
                age = t - ts
                if age > 0:
                    rings += [(c0, 0.35 + 0.9 * age + j * 0.45, max(0, 1 - age / 2.4)) for j in range(3)]
        if cid in ('R03', 'R04'):
            wpos = PATH.pos(tau)
            for k in range(6):
                ts = T['R03'][0] + 0.15 + 0.55 * k
                age = t - ts
                if age > 0:
                    cpos = PATH.pos(TAU0['R03'] + (ts - T['R03'][0])) * np.array([1, 1, 0])
                    rings.append((cpos, 2.0 + 3.2 * age, max(0, 1 - age / 4.0)))
        if cid == 'R05':
            for k in range(7):
                ts = T['R05'][0] + 0.45 + 0.4 * k
                age = t - ts
                if age > 0:
                    cpos = PATH.pos(TAU0['R05'] + (ts - T['R05'][0]) + 0.8) * np.array([1, 1, 0])
                    rings.append((cpos, 2.5 + 2.4 * age, max(0, 1 - age / 3.0)))
        if cid == 'R19':
            P, after = last_petal(t)
            if after is not None and after > 0:
                rings += [(P * np.array([1, 1, 0]), 0.35 + 0.9 * after + j * 0.45, max(0, 1 - after / 2.4)) for j in range(3)]
        for c0, rad, a in rings:
            qs = np.linspace(0, 2 * np.pi, 97)
            ring = np.column_stack([c0[0] + rad * np.cos(qs), c0[1] + rad * np.sin(qs), np.full(len(qs), 0.02)])
            on_w = ~w.is_land(ring[:, 0], ring[:, 1])
            lit = 0.32 + 0.68 * w.moonlit(ring + np.array([0, 0, 0.1]))
            rx, ry, rz = cam.proj(ring, W, H)
            for j in range(len(qs) - 1):
                if rz[j] < 0.2 or rz[j + 1] < 0.2 or not (on_w[j] and on_w[j + 1]):
                    continue
                L = a * lit[j]
                dr.line([(rx[j], ry[j]), (rx[j + 1], ry[j + 1])], fill=tuple(int(v * L) for v in (165, 196, 220)), width=max(1, W // 480))
        # --- flowers on the ground
        self.speckle(dr, cam, cid, tau)
        self.draw_flowers(dr, cam, tau, cid, img)
        if cid == 'R12':
            self.draw_macro_release(img, cam, tau)
            dr = ImageDraw.Draw(img)
        pe = self.petal_state(tau, cid)
        # --- whale reflection on the dark mirror lake
        A = np.asarray(img).astype(np.float32)
        if cid in ('R05', 'R11', 'R13', 'R14') and show_whale:
            rimg, rem, _ = self.whale_layer(cam, tau, mirror=True, hide_under=True)
            ra = np.asarray(rimg.filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)
            wm = np.asarray(water_mask).astype(np.float32)[..., None] / 255
            A = A * (1 - ra[..., 3:] / 255 * wm * 0.9) + ra[..., :3] * wm * 0.9
            gl = np.asarray(rem.filter(ImageFilter.GaussianBlur(W / 70))).astype(np.float32) / 255
            A += gl[..., None] * wm * np.array([60, 70, 80], np.float32) * 0.6
        if cid == 'R14' and pe is not None:                    # inverted snow on the lake
            A2 = np.zeros_like(A)
            self.draw_petals(A2, cam, pe, tau, far_of=1e9, part='near', mirror=True)
            A += A2 * (np.asarray(water_mask).astype(np.float32)[..., None] / 255) * (0.62 if cam.pos[2] < 2.0 else 0.42)
        # --- the air full of lit petals glows around the whale (R13-R15; v14.7: the climax is R15's
        # closest pass, where it swells with climax())
        kg = {'R13': 0.10, 'R14': 0.12, 'R15': 0.12 + 0.30 * climax(tau)}.get(cid, 0.0)
        if kg > 0 and wl_I > 0.05:
            sx, sy, sz = cam.proj(wl_p[None], W, H)
            if sz[0] > 1.0:
                yy, xx = np.ogrid[:H, :W]
                dd = np.sqrt((xx - float(sx[0])) ** 2 + (yy - float(sy[0])) ** 2) / W
                tint = np.array([150, 175, 205], np.float32) * (1 - opal_mix(tau)) + np.array([205, 210, 222], np.float32) * opal_mix(tau)
                A += (np.exp(-(dd / 0.38) ** 2) * kg * wl_I)[..., None] * tint
        # --- R10/R12: the whale itself is off-frame; its light spills in from the frame edge
        if cid in ('R10', 'R12') and wl_I > 0.05:
            sx, sy, sz = cam.proj(wl_p[None], W, H)
            yy, xx = np.ogrid[:H, :W]
            ex_, ey_ = float(np.clip(sx[0], -0.3 * W, 1.3 * W)), float(np.clip(sy[0], -0.6 * H, 1.3 * H))
            dd = np.sqrt((xx - ex_) ** 2 + (yy - ey_) ** 2) / W
            tint = np.array([150, 175, 205], np.float32) * (1 - opal_mix(tau)) + np.array([196, 204, 222], np.float32) * opal_mix(tau)
            A += (np.exp(-(dd / (0.45 if cid == 'R10' else 0.75)) ** 2) * (0.11 if cid == 'R10' else 0.26) * wl_I)[..., None] * tint      # (kept below the R15 climax)
        # --- moon beam volume and dust
        q = 4
        acc = np.zeros((H // q, W // q), np.float32)
        for sl in BEAM:
            pts = cam.poly2d(sl, W, H)
            if pts:
                m = Image.new('L', (W // q, H // q), 0)
                ImageDraw.Draw(m).polygon([(x / q, y / q) for x, y in pts], fill=255)
                acc += np.asarray(m).astype(np.float32) / 255
        acc = Image.fromarray(np.clip(acc * 18, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(W / 70 / q)).resize((W, H), Image.Resampling.BILINEAR)
        acc = np.asarray(acc).astype(np.float32) / 255
        A += acc[..., None] * np.array([70, 84, 104], np.float32) * (2.4 if cid == 'R08' else 0.55)
        self.dust(A, cam, tau)
        # --- petals behind the whale
        wl_depth = cam.cam_xyz(PATH.pos(tau)[None])[0, 2]
        if pe is not None:
            self.draw_petals(A, cam, pe, tau, far_of=wl_depth, part='far')
        img = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8))
        # --- whale
        info = {}
        if show_whale:
            wimg, wem, info = self.whale_layer(cam, tau, hide_under=cid not in ('R03', 'R04'))
            # underwater whale: only a dark mass that blocks the moonlit water (R03/R04)
            if cid in ('R03', 'R04'):
                m = np.asarray(wimg)[..., 3].astype(np.float32) / 255
                m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(W / 34))).astype(np.float32) / 255
                m *= np.asarray(water_mask).astype(np.float32) / 255     # seen only through the water
                A = np.asarray(img).astype(np.float32)
                lum = A.mean(2, keepdims=True)
                A = A - m[..., None] * np.clip(lum - 8, 0, None) * 0.7
                img = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8))
            else:
                if cid == 'R18':
                    lift, fade = r18_merge(t)
                    if lift > 0 or fade > 0:
                        wa = np.asarray(wimg).astype(np.float32)
                        wa[..., :3] = wa[..., :3] * (1 - lift) + np.array([236, 232, 212], np.float32) * 0.98 * lift
                        wa[..., 3] *= 1 - fade
                        wimg = Image.fromarray(np.clip(wa, 0, 255).astype(np.uint8), 'RGBA')
                        wem = Image.fromarray((np.asarray(wem).astype(np.float32) * (1 - fade)).astype(np.uint8))
                img.paste(wimg, (0, 0), wimg)
                # bloom following the body shape (not a fixed circle)
                if info.get('bbox'):
                    bw = info['bbox'][2] - info['bbox'][0]
                    e = np.asarray(wem).astype(np.float32) / 255
                    if e.max() > 0 or (cid == 'R18' and t > T['R18'][0] + 1.0):
                        # (R18: keep the same tone curve after the whale has melted away, so
                        # the frame does not jump in brightness when its glow reaches zero)
                        A = np.asarray(img).astype(np.float32)
                        g1 = np.asarray(wem.filter(ImageFilter.GaussianBlur(max(2, bw * 0.03)))).astype(np.float32) / 255
                        g2 = np.asarray(wem.filter(ImageFilter.GaussianBlur(max(4, bw * 0.14)))).astype(np.float32) / 255
                        tint = np.array([150, 175, 205], np.float32) * (1 - opal_mix(tau)) + np.array([196, 204, 222], np.float32) * opal_mix(tau)
                        kb = 1.0 / (1.0 + bw / (0.3 * W))         # big on screen -> less halo
                        A += (g1[..., None] * tint * 0.16 + g2[..., None] * tint * 0.26) * kb
                        img = Image.fromarray(np.clip(tone(A), 0, 255).astype(np.uint8))
            self.drops(img, cam, tau, cid, t)
        A = np.asarray(img).astype(np.float32)
        if pe is not None:
            self.draw_petals(A, cam, pe, tau, far_of=wl_depth, part='near')
        self.local_snow(A, cam, t, tau, cid)
        if cid == 'R19':
            self.draw_last_petal(A, cam, t)
            A *= 1.0 - smooth((t - 68.9) / 1.05)                   # fade to black, no end card
        img = Image.fromarray(np.clip(tone(A), 0, 255).astype(np.uint8))
        self.label(img, cid, t)
        info.update(cut=cid, t=round(t, 4), tau=round(tau, 3))
        return img, info

    # ------------------------------------------------------------------ moon
    def hole_mask(self, cam):
        W, H = self.W, self.H
        bot = cam.poly2d(np.array(w.rim_polygon(w.RIM_Z)), W, H)
        top = cam.poly2d(np.array(w.rim_polygon(w.TOP_Z)), W, H)
        if not (bot and top):
            return None
        mb = Image.new('L', (W, H), 0); ImageDraw.Draw(mb).polygon(bot, fill=255)
        mt = Image.new('L', (W, H), 0); ImageDraw.Draw(mt).polygon(top, fill=255)
        return np.minimum(np.asarray(mb), np.asarray(mt)).astype(np.float32) / 255

    def moon_layout(self, cid):
        """Once per cut: choose where the moon sits in the opening and how big it is. Returns a
        world anchor point inside the opening and an angular radius (or None)."""
        if not hasattr(self, '_moon'):
            self._moon = {}
        if cid in self._moon:
            return self._moon[cid]
        from scipy.ndimage import distance_transform_edt
        W, H = self.W, self.H
        s0, s1 = T[cid]; tm = s0 + 0.5 * (s1 - s0)
        cam = self.cams[cid](tm, tau_of(tm))
        hole = self.hole_mask(cam)
        out = None
        if hole is not None and hole.sum() > 30:
            fx = cam.lens / 36 * W
            q = 2
            dt = distance_transform_edt(hole[::q, ::q] > 0.5) * q
            if cid in ('R17', 'R18'):                        # the end of the whale's line
                P = cam.pos + w.EXIT_DIR * 1e5
            else:
                P = cam.pos + w.MOON_DIR * 1e5
            px, py, pz = cam.proj(P[None], W, H)
            pref = np.array([px[0], py[0]]) if pz[0] > 0 else np.array([W / 2, H / 3])
            target = MOON_TARGET.get(cid, 0.0) * H
            if target <= 0:
                target = fx * math.tan(math.radians(MOON_R_DEG))
            yy, xx = np.mgrid[0:dt.shape[0], 0:dt.shape[1]] * q
            dist = np.hypot(xx - pref[0], yy - pref[1])
            score = np.minimum(dt, target * 1.08) - 0.12 * dist
            k = np.unravel_index(int(np.argmax(score)), dt.shape)
            if cid in ('R17', 'R18'):                        # exactly where the whale's line ends
                k = (int(np.clip(round(pref[1] / q), 0, dt.shape[0] - 1)), int(np.clip(round(pref[0] / q), 0, dt.shape[1] - 1)))
            cxy = np.array([xx[k], yy[k]], float); r = min(target, 0.92 * dt[k])
            if r >= 4:
                d = unit(cam.f + cam.r * ((cxy[0] - W / 2) / fx) + cam.u * (-(cxy[1] - H / 2) / fx))
                sdist = (w.TOP_Z + 25.0 - cam.pos[2]) / max(d[2], 0.05)   # anchor just beyond the top rim
                out = (cam.pos + d * sdist, math.atan(r / fx))
        self._moon[cid] = out
        return out

    def draw_moon(self, A, cam, cid, hole, t=None):
        W, H = self.W, self.H
        lay = self.moon_layout(cid)
        if lay is None:
            return
        Q, ang = lay
        mx, my, mz = cam.proj(Q[None], W, H)
        if mz[0] <= 0:
            return
        rr = cam.lens / 36 * W * math.tan(ang)
        yy, xx = np.ogrid[:H, :W]
        ux, uy = (xx - mx[0]) / rr, (yy - my[0]) / rr
        dd = np.sqrt(ux ** 2 + uy ** 2)
        disk = clamp((1.0 + 1.2 / rr - dd) * rr / 1.6)
        limb = 0.80 + 0.20 * np.sqrt(clamp(1 - dd ** 2))
        maria = 1.0
        # the near side as seen from the north (v14.5): one large dark sweep upper left
        # (Imbrium/Procellarum), a chain on the right (Serenitatis-Tranquillitatis-Fecunditatis),
        # small Crisium near the right limb, bright southern highlands - the familiar moon
        # (the rabbit), not two eyes and a mouth
        for (cx_, cy_, r_, k_) in ((-0.40, -0.02, 0.34, 0.17), (-0.20, -0.32, 0.24, 0.19), (-0.48, 0.28, 0.18, 0.10),
                                   (0.16, -0.26, 0.16, 0.17), (0.28, -0.02, 0.18, 0.15), (0.44, 0.20, 0.11, 0.11),
                                   (0.62, -0.24, 0.08, 0.12), (-0.14, 0.34, 0.12, 0.08)):
            maria = maria - k_ * np.exp(-(((ux - cx_) ** 2 + (uy - cy_) ** 2) / r_ ** 2) * 2.2)
        face = disk * limb * maria
        # a hard-edged, luminous disc with a tight bright ring and a wide soft glow: the glow is
        # allowed over the rock rim (it is light, not the disc)
        ring = np.exp(-((dd - 1.0).clip(0) / 0.08) ** 2) * (1 - disk) * 0.55
        glow = np.exp(-((dd - 1.0).clip(0) / 0.7) ** 2) * 0.26 + np.exp(-(dd / 3.0) ** 2) * 0.10
        hsoft = np.asarray(Image.fromarray((hole * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(2.0, rr * 0.4)))).astype(np.float32) / 255
        A += face[..., None] * np.array([236, 232, 212], np.float32) * hole[..., None]
        A += ring[..., None] * np.array([220, 225, 235], np.float32) * hole[..., None]
        A += (glow * (1 - disk))[..., None] * np.array([120, 134, 160], np.float32) * np.maximum(hole, 0.6 * hsoft)[..., None]

    # ------------------------------------------------------------------ details
    def canopy_light(self, cam, tau, wl_p, wl_I):
        """Rock facets of the ceiling and of the slot walls, lit only by the whale."""
        W, H = self.W, self.H
        if not hasattr(self, '_canopy'):
            r = np.random.default_rng(5)
            tris = []
            n = 4200
            cx = r.uniform(-170, 170, n); cy = r.uniform(-70, 340, n)
            _, m = w._inside_rim(cx, cy, 1.0)
            for x, y in zip(cx[m < -0.5], cy[m < -0.5]):
                rad = r.uniform(4.0, 9.5); a0 = r.uniform(0, 2 * np.pi)
                tris.append([(x + rad * math.cos(a0 + k * 2.09 + r.uniform(-0.35, 0.35)),
                              y + rad * math.sin(a0 + k * 2.09 + r.uniform(-0.35, 0.35)),
                              w.RIM_Z - r.uniform(0.0, 8.0)) for k in range(3)])
            ysf = np.array([q[0] for q in w.FISSURE], float)
            cf = np.array([(q[1] + q[2]) / 2 for q in w.FISSURE]); hf = np.array([(q[2] - q[1]) / 2 for q in w.FISSURE])
            ys = np.linspace(24, 250, 80); nl = 7
            for side in (-1, 1):
                for i in range(len(ys) - 1):
                    for lv in range(nl):
                        def e(yy, zz):
                            k = 1 + (w.TOP_NARROW - 1) * (zz - w.RIM_Z) / (w.TOP_Z - w.RIM_Z)
                            return (float(np.interp(yy, ysf, cf) + side * np.interp(yy, ysf, hf) * k) + r.uniform(-1.2, 1.2), yy, zz)
                        z0 = w.RIM_Z + lv * (w.TOP_Z - w.RIM_Z) / nl; z1 = z0 + (w.TOP_Z - w.RIM_Z) / nl
                        a, b, c, d = e(ys[i], z0), e(ys[i + 1], z0), e(ys[i + 1], z1), e(ys[i], z1)
                        tris += [[a, b, c], [a, c, d]]
            T3 = np.array(tris, float)
            self._canopy = (T3, T3.mean(1), r.uniform(0.85, 1.0, len(T3)))
        T3, cen, shade = self._canopy
        d = np.linalg.norm(cen - wl_p, axis=1)
        L = wl_I * (1.5 * np.exp(-(d / 46.0) ** 2) + 0.22 / (1 + (d / 30.0) ** 2))
        L *= 0.45 + 0.55 * clamp((cen[:, 2] - wl_p[2]) / np.maximum(d, 1e-3) + 0.4)
        c = cam.cam_xyz(cen)
        ok = (L > 0.012) & (c[:, 2] > 1.0)
        lay = Image.new('RGB', (W, H), (0, 0, 0)); dl = ImageDraw.Draw(lay)
        tint = np.array([150, 160, 182]) * (1 - opal_mix(tau)) + np.array([176, 168, 160]) * opal_mix(tau)
        for i in np.where(ok)[0][np.argsort(-c[ok, 2])]:
            pts = cam.poly2d(T3[i], W, H)
            if pts:
                col = tint * 0.36 * min(1.0, L[i]) * shade[i]
                dl.polygon(pts, fill=tuple(int(v) for v in np.clip(col, 0, 255)))
        return np.asarray(lay).astype(np.float32)

    def speckle(self, dr, cam, cid, tau):
        """Pebbles and moss for the ground-level close-ups (reveals the moonlight edge)."""
        W, H = self.W, self.H
        cfg = {'R02': (w.P0 + np.array([-0.9, 0, 0]), 2.4, 5200, 21, 0.6), 'R12': (np.array([78.0, 20.0, GZ(78.0, 20.0)]), 0.30, 3000, 22, 0.12)}
        if cid not in cfg:
            return
        if not hasattr(self, '_speck'):
            self._speck = {}
        if cid not in self._speck:
            c0, rad, n, sd, ks = cfg[cid]
            r = np.random.default_rng(sd)
            rr = rad * np.sqrt(r.random(n)); a = r.uniform(0, 2 * np.pi, n)
            P = np.column_stack([c0[0] + rr * np.cos(a), c0[1] + rr * np.sin(a), np.zeros(n)])
            P[:, 2] = w.ground_z(P[:, 0], P[:, 1]) + 0.002
            self._speck[cid] = (P, r.uniform(0.0015, 0.006, n) * ks, r.uniform(0.82, 1.2, n), w.moonlit(P + np.array([0, 0, 0.05])))
        P, size, tone_k, moon = self._speck[cid]
        wl_p, wl_I = whale_light(tau)
        Lw = wl_I * 1.4 / (1 + (np.linalg.norm(P - wl_p, axis=1) / 26) ** 2)
        x, y, z = cam.proj(P, W, H)
        rpx = cam.lens / 36 * W * size / np.maximum(z, 1e-3)
        ok = (z > 0.05) & (rpx > 0.5) & (x > -50) & (x < W + 50) & (y > -50) & (y < H + 50)
        for i in np.where(ok)[0][np.argsort(-z[ok])]:
            L = (0.45 + 1.6 * moon[i] + Lw[i]) * tone_k[i]
            col = np.array([19, 20, 19]) * L + np.array([6, 8, 12]) * moon[i]
            r_ = rpx[i]
            dr.ellipse((x[i] - r_, y[i] - r_ * 0.55, x[i] + r_, y[i] + r_ * 0.55), fill=tuple(int(v) for v in np.clip(col, 0, 255)))

    def draw_flowers(self, dr, cam, tau, cid, img=None):
        W, H = self.W, self.H
        wl_p, wl_I = whale_light(tau)
        op = flower_open(tau)
        rel = self.petals_released_fraction(tau)
        if not hasattr(self, '_fmoon'):
            self._fmoon = w.moonlit(FLOWERS + np.array([0, 0, 0.2]))
        kw = 2.0 if cid == 'R12' else 1.0          # v14.7: R12, the flower is in the whale's light
        light = 0.10 + 1.3 * self._fmoon + kw * wl_I * 1.4 / (1 + (np.linalg.norm(FLOWERS - wl_p, axis=1) / 26) ** 2)
        x, y, z = cam.proj(FLOWERS, W, H)
        ok = (z > 0.3) & (x > -5) & (x < W + 5) & (y > -5) & (y < H + 5)
        idx = np.where(ok)[0]
        size_all = cam.lens / 36 * W * 0.045 / np.maximum(z, 1e-3)
        # far, tiny flowers in one vectorised pass (painted first: they are the farthest)
        tiny = idx[size_all[idx] < 2.2]
        if len(tiny) and img is not None:
            o = op[tiny]; L = np.minimum(1.4, light[tiny]); rl = rel[tiny]
            c = (np.array([236, 230, 212])[None, :] * (0.12 + 0.88 * L)[:, None] * (o * (1 - 0.75 * rl))[:, None] +
                 np.array([86, 76, 62])[None, :] * (0.30 + 0.7 * L)[:, None] * (1 - o)[:, None] +
                 np.array([70, 80, 66])[None, :] * (0.15 + 0.5 * L)[:, None] * (o * 0.75 * rl)[:, None])
            # sub-pixel coverage; each previs sample stands for several real flowers of the dense colony
            cov = np.clip((size_all[tiny] * (0.5 + 0.5 * o)) ** 2 / 3.0 * (1 + 5 * o), 0.30 + 0.15 * o, 1.0)
            arr = np.asarray(img).astype(np.float32)
            xi = np.clip(np.round(x[tiny]).astype(int), 0, W - 1); yi = np.clip(np.round(y[tiny]).astype(int), 0, H - 1)
            order_t = np.argsort(-z[tiny])
            xi, yi, c, cov = xi[order_t], yi[order_t], c[order_t], cov[order_t]
            arr[yi, xi] = arr[yi, xi] * (1 - cov[:, None]) + c * cov[:, None]
            img.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)))
        idx = idx[size_all[idx] >= 2.2]
        idx = idx[np.argsort(-z[idx])]
        for i in idx:
            size = size_all[i]
            o = op[i]; L = min(1.4, light[i])
            if size > 6:
                draw_flower(dr, cam, W, H, FLOWERS[i], o, L, i, released=rel[i])
                continue
            c_open = np.array([236, 230, 212]) * (0.12 + 0.88 * L)
            c_bud = np.array([86, 76, 62]) * (0.15 + 0.6 * L)
            c = c_open * o * (1 - 0.75 * rel[i]) + c_bud * (1 - o) + np.array([70, 80, 66]) * (0.15 + 0.5 * L) * o * 0.75 * rel[i]
            r = max(0.6, size * (0.5 + 0.5 * o) / 2)
            dr.ellipse((x[i] - r, y[i] - r * 0.7, x[i] + r, y[i] + r * 0.7), fill=tuple(int(v) for v in np.clip(c, 0, 255)))
        # the young flower P0 (open in direct moonlight from the start, never disperses)
        px, py, pz = cam.proj(w.P0[None], W, H)
        if pz[0] > 0.08:
            size = cam.lens / 36 * W * 0.045 / pz[0]
            if size > 6:
                # the faintest air movement in the cave: P0 sways a few millimetres
                sw = np.array([0.0035 * math.sin(2 * math.pi * tau / 2.9), 0.0022 * math.sin(2 * math.pi * tau / 2.1 + 1.0), 0.0])
                draw_flower(dr, cam, W, H, w.P0, 1.0, 1.25, 4242, sway=sw)
                # closed buds just outside the moonlight
                for k in range(12):
                    q = w.P0 + np.array([-1.25 - 0.20 * (k % 4) - 0.05 * k, -0.55 + 0.32 * (k // 4) + 0.03 * k, 0])
                    q[2] = float(w.ground_z(q[0], q[1]))
                    draw_flower(dr, cam, W, H, q, 0.0, 0.34 + 0.5 * float(w.moonlit(q[None] + np.array([[0, 0, 0.1]]))[0]), 900 + k)
            else:
                r = max(1.2, size / 2)
                dr.ellipse((px[0] - r, py[0] - r, px[0] + r, py[0] + r), fill=(236, 232, 214))
        if cid in self.inserts:
            P, to, mat = self.inserts[cid]
            o = smooth((tau - to) / 0.8)
            Lw = (2.0 if cid == 'R12' else 1.0) * wl_I * 1.4 / (1 + (np.linalg.norm(P - wl_p, axis=1) / 26) ** 2)
            Lm = 1.3 * w.moonlit(P + np.array([0, 0, 0.2]))
            xx, yy, zz = cam.proj(P, W, H)
            for i in np.argsort(-zz):
                if zz[i] < 0.08:
                    continue
                rel_i = 0.0
                if cid == 'R12' and i == 0:
                    rel_i = 0.25 if tau >= TAU0['R12'] + 1.0 else 0.0
                    rel_i = 0.5 if tau >= TAU0['R12'] + 1.9 else rel_i
                    rel_i = 0.75 if tau >= TAU0['R12'] + 2.6 else rel_i
                draw_flower(dr, cam, W, H, P[i], float(o[i]) if mat[i] else 0.15 * float(o[i]),
                            min(1.4, 0.10 + Lm[i] + Lw[i]), 5000 + i + (0 if cid == 'R10' else 700), released=rel_i)

    def petals_released_fraction(self, tau):
        rel = np.zeros(NF)
        if tau >= TAU0['R12']:
            P = self.petals
            done = tau >= P.tau_detach
            np.add.at(rel, P.src, done.astype(float) / 4.0)
        return rel * 0.8

    def petal_state(self, tau, cid):
        if tau < TAU0['R12'] or cid in ('R01', 'R02', 'R19') and tau < TAU0['R12']:
            return None
        self.petals.step(tau)
        return self.petals

    def draw_petals(self, A, cam, P, tau, far_of, part, mirror=False):
        W, H = self.W, self.H
        det = (tau >= P.tau_detach) & ~P.gone
        if mirror:
            det &= ~P.landed
        if not det.any():
            return
        idx = np.where(det)[0]
        pos = P.p[idx] * (np.array([1, 1, -1]) if mirror else 1)
        x, y, z = cam.proj(pos, W, H)
        sel = (z > 0.15) & (x > -40) & (x < W + 40) & (y > -40) & (y < H + 40)
        sel &= (z >= far_of) if part == 'far' else (z < far_of)
        if not sel.any():
            return
        idx, x, y, z = idx[sel], x[sel], y[sel], z[sel]
        wl_p, wl_I = whale_light(tau)
        d = np.linalg.norm(P.p[idx] - wl_p, axis=1)
        lightw = wl_I * 1.6 / (1 + (d / 42.0) ** 2)
        moon = w.moonlit(P.p[idx], soft=7.0)      # soft: the shaft must not read as a solid shape
        g = P.g[idx]
        pul = float(pulse(tau))
        bright = 0.06 + lightw + 0.32 * moon
        pz = P.p[idx, 2]
        bright = bright * np.where(P.landed[idx], 0.35, 1.0) * clamp((w.TOP_Z + 70 - pz) / 55.0)
        if not mirror and (pz > w.RIM_Z).any():
            bright = bright * w.sight_through_opening(cam.pos, P.p[idx])
        flick = np.abs(np.cos(P.spin[idx]))                      # pure: tumbling flicker
        flick = g * 1.0 + (1 - g) * (0.35 + 0.65 * flick)
        near_opal = clamp(1 - d / 30.0)
        pcol = (np.array([238, 234, 222])[None, :] * (1 - near_opal[:, None]) +
                np.array([224, 214, 236])[None, :] * near_opal[:, None])
        petal_rgb = pcol * (bright * flick)[:, None] * (1 + 0.45 * g * pul)[:, None]
        fruit = P.fruit[idx] * (0.55 + 0.45 * g * (1 + pul)) * (bright > 0.01)
        fruit_rgb = np.array([255, 226, 150])[None, :] * fruit[:, None]
        self.paint_flakes(A, cam, x, y, z, petal_rgb, fruit_rgb, P.spin[idx], g)

    def paint_flakes(self, A, cam, x, y, z, petal_rgb, fruit_rgb, spin, g):
        """Paint petal+fruit flakes: far -> small square footprints (vectorised), near -> tumbling
        petal shapes, very near -> soft out-of-focus discs."""
        W, H = self.W, self.H
        size = cam.lens / 36 * W * 0.022 / z
        q = max(1, int(round(W / 640)))
        small = size < 2.6 * q
        s_rgb = petal_rgb[small] * np.clip(size[small] / (1.8 * q), 0.15, 1)[:, None] + fruit_rgb[small] * np.clip(0.9 / np.sqrt(np.maximum(z[small], 1) / 25), 0.10, 0.9)[:, None]
        fp = np.clip(np.round(size[small] * 0.75), 1, 3 * q).astype(int)
        buf = np.zeros_like(A)
        xs, ys = x[small], y[small]
        for f in np.unique(fp):
            k = fp == f
            bq = np.zeros((H // f + 1, W // f + 1, 3), np.float32)
            splat(bq, xs[k] / f, ys[k] / f, s_rgb[k], W // f + 1, H // f + 1)
            buf += np.repeat(np.repeat(bq, f, 0), f, 1)[:H, :W] * (0.85 if f > 1 else 1.0)
        A += buf
        big = np.where(~small)[0]
        if len(big):
            lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay, 'RGBA')
            bok = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dk = ImageDraw.Draw(bok, 'RGBA')
            for j in big[np.argsort(-z[big])]:
                s_ = min(size[j], W * 0.05)
                ang = spin[j]
                ca, sa = math.cos(ang), math.sin(ang)
                wdt = s_ * (0.35 + 0.65 * abs(math.cos(ang * 0.7))) if g[j] < 0.5 else s_ * 0.85
                pts = [(x[j] + ca * s_, y[j] + sa * s_), (x[j] - sa * wdt * 0.5, y[j] + ca * wdt * 0.5),
                       (x[j] - ca * s_ * 0.8, y[j] - sa * s_ * 0.8), (x[j] + sa * wdt * 0.5, y[j] - ca * wdt * 0.5)]
                c = tuple(int(v) for v in np.clip(petal_rgb[j] + fruit_rgb[j] * 0.2, 0, 255))
                if z[j] < 2.5:            # very near: out-of-focus bokeh
                    r = min(s_ * 0.9, W * 0.022)
                    dk.ellipse((x[j] - r, y[j] - r, x[j] + r, y[j] + r), fill=c + (40,))
                else:
                    dl.polygon(pts, fill=c + (235,))
                    fr = max(0.8, s_ * 0.16)
                    fc = tuple(int(v) for v in np.clip(fruit_rgb[j] * 0.9 + 20, 0, 255))
                    if fruit_rgb[j].max() > 8:
                        dl.ellipse((x[j] + ca * s_ * 0.9 - fr, y[j] + sa * s_ * 0.9 - fr, x[j] + ca * s_ * 0.9 + fr, y[j] + sa * s_ * 0.9 + fr), fill=fc + (255,))
            bok = bok.filter(ImageFilter.GaussianBlur(max(2, W / 260)))
            for L in (lay, bok):
                a = np.asarray(L).astype(np.float32)
                al = a[..., 3:] / 255
                A[:] = A * (1 - al) + a[..., :3] * al

    def local_snow(self, A, cam, t, tau, cid):
        """Pure blizzard in the air right around the camera (R13-R17). The world simulation holds
        ~124k flakes, far fewer than a real colony releases (FX-01 budget ~680k); this layer fills
        the camera's own volume at the same density so that the snow passes in front of us.
        Stateless: positions are a function of film time, wrapped inside a box around the camera."""
        N = {'R13': 320, 'R14': 360, 'R15': 800, 'R17': 260}.get(cid, 0)
        # same air density whatever the lens: a long lens sees a much narrower cone of near air
        N = int(N * min(1.0, (24.0 / cam.lens) ** 2))
        if N == 0:
            return
        W, H = self.W, self.H
        r = np.random.default_rng(1000 + int(cid[1:]))
        D = 18.0                      # near/mid air only: farther snow comes from the world simulation
        ax = 1.15 * 18.0 / cam.lens; ay = 1.15 * 10.125 / cam.lens          # frustum half-extents (tan)
        dep = 1.3 + D * r.random(N) ** 0.9
        base = np.column_stack([r.uniform(-ax, ax, N) * dep, dep, r.uniform(-ay, ay, N) * dep])
        vel = np.column_stack([r.normal(-0.4, 0.9, N), r.normal(0.5, 0.9, N), r.normal(-0.55, 0.35, N)])
        s0 = T[cid][0]
        cam0 = self.cams[cid](s0, TAU0[cid])
        dt = t - s0
        ph = r.uniform(0, 2 * np.pi, N)
        world = (cam0.pos[None, :] + cam0.r[None, :] * base[:, 0:1] + cam0.f[None, :] * base[:, 1:2]
                 + cam0.u[None, :] * base[:, 2:3] + vel * dt
                 + np.column_stack([0.6 * np.sin(1.1 * dt + ph), 0.6 * np.cos(0.9 * dt + ph), 0.25 * np.sin(1.7 * dt + ph)]))
        rel = cam.cam_xyz(world)
        # wrap inside the view frustum so the density stays constant while the camera moves
        rel[:, 2] = np.mod(rel[:, 2] - 1.3, D) + 1.3
        sx = np.mod(rel[:, 0] / rel[:, 2] + ax, 2 * ax) - ax
        sy = np.mod(rel[:, 1] / rel[:, 2] + ay, 2 * ay) - ay
        rel[:, 0] = sx * rel[:, 2]; rel[:, 1] = sy * rel[:, 2]
        pw = cam.pos[None, :] + rel[:, 0:1] * cam.r[None, :] + rel[:, 1:2] * cam.u[None, :] + rel[:, 2:3] * cam.f[None, :]
        x = W / 2 + rel[:, 0] / rel[:, 2] * cam.lens / 36 * W
        y = H / 2 - rel[:, 1] / rel[:, 2] * cam.lens / 20.25 * H
        z = rel[:, 2]
        ok = (x > -60) & (x < W + 60) & (y > -60) & (y < H + 60) & (pw[:, 2] > w.ground_z(pw[:, 0], pw[:, 1]) + 0.05)
        x, y, z, pw = x[ok], y[ok], z[ok], pw[ok]
        wl_p, wl_I = whale_light(tau)
        d = np.linalg.norm(pw - wl_p, axis=1)
        bright = 0.05 + wl_I * 1.6 / (1 + (d / 42.0) ** 2) + 0.32 * w.moonlit(pw, soft=7.0)
        spin = ph[ok] + dt * r.uniform(3.0, 11.0, N)[ok]
        flick = 0.35 + 0.65 * np.abs(np.cos(spin))
        petal_rgb = np.array([238, 234, 222])[None, :] * (bright * flick)[:, None]
        fruit_rgb = np.array([255, 226, 150])[None, :] * (0.45 * np.clip(bright, 0, 1))[:, None]
        self.paint_flakes(A, cam, x, y, z, petal_rgb, fruit_rgb, spin, np.zeros(len(z)))

    def dust(self, A, cam, tau):
        W, H = self.W, self.H
        r = np.random.default_rng(31)
        n = 900
        base = cam.pos + cam.f * r.uniform(2, 45, n)[:, None] + cam.r * r.uniform(-25, 25, n)[:, None] + cam.u * r.uniform(-14, 14, n)[:, None]
        base += np.column_stack([0.15 * np.sin(0.3 * tau + r.uniform(0, 6, n)), 0.15 * np.cos(0.27 * tau + r.uniform(0, 6, n)), 0.05 * np.sin(0.2 * tau + r.uniform(0, 6, n))])
        m = w.moonlit(base)
        x, y, z = cam.proj(base, W, H)
        ok = (z > 0.5) & (m > 0.3)
        tw = 0.5 + 0.5 * np.sin(tau * r.uniform(1, 3, n) + r.uniform(0, 6, n))
        splat(A, x[ok], y[ok], np.array([150, 165, 190])[None, :] * (m[ok] * tw[ok] * np.clip(6 / z[ok], 0.15, 1))[:, None] * 0.6, W, H)

    def drops(self, img, cam, tau, cid, t):
        """Water sheet at the emergence, water thread from the tail, drips overhead."""
        if cid not in ('R05', 'R06', 'R07'):
            return
        W, H = self.W, self.H
        dr = ImageDraw.Draw(img, 'RGBA')
        if not hasattr(self, '_drops'):
            self._drops = {}
        if cid not in self._drops:
            r = np.random.default_rng({'R05': 1, 'R06': 2, 'R07': 3}[cid])
            s, e = T[cid]
            nb = 70 if cid != 'R07' else 40
            per = {'R05': 14, 'R06': 3, 'R07': 6}[cid]
            under = np.where(w.BODY_V[:, 2] < -0.6)[0] if cid != 'R05' else np.where((w.BODY_V[:, 2] > 0.3) & (w.BODY_V[:, 0] > -6.0))[0]
            rec = []
            for tb in np.linspace(TAU0[cid] - 1.5, TAU0[cid] + (e - s), nb):
                fr, Vb, _, _ = whale_world(tb)
                vel = PATH.vel(tb) * 0.35
                for vi in r.choice(under, per):
                    rec.append((tb + r.uniform(0, 0.05), Vb[vi].copy(), vel))
            self._drops[cid] = rec
        for tb, p0, v0 in self._drops[cid]:
            if tb > tau or tau - tb > 3.0:
                continue
            if cid == 'R05' and not (0.0 < p0[2] < 9.0):
                continue
            dt = tau - tb
            p = p0 + v0 * dt + np.array([0, 0, -4.9 * dt * dt])
            if p[2] < 0 and cid != 'R07':
                continue
            if cid == 'R07' and p[2] < w.PC[2]:
                continue
            q = p - (v0 + np.array([0, 0, -9.8 * dt])) * 0.035
            px, py, pz = cam.proj(np.array([p, q]), W, H)
            x0, x1, y0, y1, z0, z1 = px[0], px[1], py[0], py[1], pz[0], pz[1]
            if min(z0, z1) < 0.3:
                continue
            lit = 0.25 + 0.75 * float(w.moonlit(p[None])[0])
            dr.line([(float(x0), float(y0)), (float(x1), float(y1))], fill=(int(150 * lit), int(175 * lit), int(195 * lit), 170), width=max(1, W // 900))
        # a few drops hit the lens right after the pass
        if cid == 'R07':
            for k, (tt, xx, yy) in enumerate(((17.55, 0.62, 0.30), (17.8, 0.38, 0.52), (18.1, 0.70, 0.66))):
                if t > tt:
                    a = max(0, 1 - (t - tt) / 1.4)
                    rr = W * 0.035
                    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                    ImageDraw.Draw(lay).ellipse((xx * W - rr, yy * H + (t - tt) * 30 - rr, xx * W + rr, yy * H + (t - tt) * 30 + rr), fill=(160, 180, 200, int(60 * a)))
                    lay = lay.filter(ImageFilter.GaussianBlur(rr * 0.35))
                    img.paste(lay, (0, 0), lay)

    def draw_macro_release(self, img, cam, tau):
        """R12: petals leave the hero flower one by one; each floats (hover) ~1 s, then rises.
        Near the end the neighbouring flowers let go too: soft, out-of-focus petals rise past
        the lens, so the macro already says 'all of them'."""
        W, H = self.W, self.H
        a0 = tau - TAU0['R12']
        if a0 > 2.0:
            rb = np.random.default_rng(1212)
            dlb = ImageDraw.Draw(img, 'RGBA')
            for j in range(18):
                st = 2.0 + rb.uniform(0, 1.3); age = a0 - st
                if age < 0:
                    continue
                x0 = rb.uniform(0.04, 0.96) * W; vy = rb.uniform(0.25, 0.55) * H
                x = x0 + math.sin(age * rb.uniform(1.0, 2.2) + j) * 0.03 * W
                y = H * 1.08 - vy * age * (1 + 0.6 * age)
                r = rb.uniform(0.018, 0.05) * W
                al = int(min(1.0, age / 0.3) * rb.uniform(60, 110))
                dlb.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=(225, 222, 210, al))
                rf = r * 0.22
                dlb.ellipse((x - rf, y - rf, x + rf, y + rf), fill=(255, 226, 150, min(255, al + 60)))
        P, to, _ = self.inserts['R12']
        seed = 5000 + 0 + 700
        dl = ImageDraw.Draw(img, 'RGBA')
        wl_p, wl_I = whale_light(tau)
        Lw = min(1.4, 0.10 + 2.0 * wl_I * 1.4 / (1 + (np.linalg.norm(P[0] - wl_p) / 26) ** 2))
        for k, t_rel in ((0, 1.0), (1, 1.9), (2, 2.6)):
            a = tau - (TAU0['R12'] + t_rel)
            if a < 0:
                continue
            poly, top, tipd = flower_petal_poly(P[0], 1.0, seed, k)
            up = 0.0045 * min(a, 1.0) + 0.035 * max(0.0, a - 1.0) ** 1.6
            side = np.array([0.006 * math.sin(1.3 * a), 0.004 * a, up])
            # petal turns flat (horizontal) while hovering: the guided signature, no spin
            c = poly.mean(0)
            flat = poly - c
            flat[:, 2] *= max(0.15, 1 - 0.85 * min(1.0, a / 0.6))
            q = c + flat + side
            pts = cam.poly2d(q, W, H, near=0.03)
            if pts:
                col = np.array([238, 232, 216]) * (0.18 + 1.0 * Lw)
                dl.polygon(pts, fill=tuple(int(v) for v in np.clip(col, 0, 255)) + (245,))
            # the fruit stays on the petal (glows faint gold)
            fpos = q[0] * 0.75 + q[2] * 0.25
            fx, fy, fz = cam.proj(fpos[None], W, H)
            if fz[0] > 0.03:
                rr = cam.lens / 36 * W * 0.0012 / fz[0]
                for m, al in ((2.2, 35), (1.5, 70), (1.0, 255)):
                    dl.ellipse((fx[0] - rr * m, fy[0] - rr * m, fx[0] + rr * m, fy[0] + rr * m), fill=(255, 226, 150, al))

    def draw_last_petal(self, A, cam, t):
        W, H = self.W, self.H
        P, after = last_petal(t)
        if P is None:
            return
        x, y, z = cam.proj(P[None], W, H)
        if z[0] < 0.3:
            return
        fade = 1.0 if after is None else max(0.0, 1 - after / 1.4)
        lit = 0.4 + 0.6 * float(w.moonlit(P[None] + np.array([[0, 0, 0.2]]))[0])
        flick = 0.65 + 0.35 * abs(math.cos(t * 5.3))           # tumbling; its fruit keeps the last faint light
        r = max(2.4 * W / 1280, cam.lens / 36 * W * 0.02 / z[0] * 2.4)
        yy, xx = np.ogrid[:H, :W]
        dd = np.sqrt((xx - x[0]) ** 2 + (yy - y[0]) ** 2)
        A += (clamp((r - dd) / 1.2)[..., None] * np.array([232, 230, 222], np.float32) * lit * flick * fade +
              np.exp(-(dd / (r * 3.0)) ** 2)[..., None] * np.array([255, 222, 150], np.float32) * 0.40 * fade)

    def label(self, img, cid, t):
        d = ImageDraw.Draw(img, 'RGBA')
        c = CUT_LABEL[cid]
        txt = f"{cid}  {c['start_s']:.1f}–{c['end_s']:.1f}s   t={t:05.2f}"
        W, H = self.W, self.H
        d.rectangle((8, H - 8 - self.font.size - 8, 8 + self.font.getlength(txt) + 12, H - 8), fill=(0, 0, 0, 110))
        d.text((14, H - 8 - self.font.size - 5), txt, font=self.font, fill=(220, 226, 232, 200))

# ====================================================================== output
def write_movie(R, path, fps):
    W, H = R.W, R.H
    n = int(round(70 * fps))
    cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'veryfast',
           '-crf', '24', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    stats = []
    try:
        for k in range(n):
            t = k / fps
            im, info = R.frame(t)
            proc.stdin.write(im.tobytes())
            stats.append(info)
            if k % (fps * 5) == 0:
                print(f'  frame {k}/{n}  t={t:05.2f}  {info["cut"]}', flush=True)
    finally:
        proc.stdin.close()
    if proc.wait():
        raise RuntimeError('ffmpeg failed')
    return stats

KEY_TIMES = [1.2, 3.0, 5.5, 7.5, 9.6, 13.0, 16.2, 17.3, 18.4, 20.6, 22.8, 25.5, 28.0, 31.0, 34.5,
             36.3, 38.6, 41.5, 46.0, 49.5, 53.0, 57.5, 61.0, 63.5, 66.0, 68.6]

def contact_sheet(R, out):
    tw, th = 400, 225
    cols = 4; rows = math.ceil(len(KEY_TIMES) / cols)
    sheet = Image.new('RGB', (cols * (tw + 8) + 8, rows * (th + 30) + 8), (6, 10, 16))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT_PATH, 16) if Path(FONT_PATH).exists() else ImageFont.load_default()
    R2 = Renderer(960, 540)
    for i, t in enumerate(KEY_TIMES):
        im, info = R2.frame(t)
        x = 8 + (i % cols) * (tw + 8); y = 8 + (i // cols) * (th + 30)
        sheet.paste(im.resize((tw, th), Image.Resampling.LANCZOS), (x, y))
        d.text((x + 4, y + th + 4), f"{t:05.2f}s  {info['cut']}", font=f, fill=(222, 230, 236))
    sheet.save(out / 'v14-keyframes.png', optimize=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=HERE / 'artifacts' / 'v14-full70')
    ap.add_argument('--fps', type=int, default=24)
    ap.add_argument('--width', type=int, default=1280)
    ap.add_argument('--sheet-only', action='store_true')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    W = a.width; H = W * 9 // 16
    contact_sheet(None, a.out)
    qa = {'events_world_tau': {k: round(v, 2) for k, v in EV.items()},
          'tau0_per_cut': {k: round(v, 2) for k, v in TAU0.items()},
          'tau_lift': round(TAU_LIFT, 2), 'path_length_m': round(PATH.length, 1),
          'flowers': int(NF), 'petals': int(Petals().n)}
    if not a.sheet_only:
        R = Renderer(W, H)
        stats = write_movie(R, a.out / f'v14-full70-{W}x{H}-{a.fps}fps.mp4', a.fps)
        qa['frames'] = len(stats)
        per = {}
        for s in stats:
            c = per.setdefault(s['cut'], {'min_dist_m': 1e9, 'bbox_w_px': []})
            if 'min_dist' in s:
                c['min_dist_m'] = min(c['min_dist_m'], s['min_dist'])
            if 'bbox' in s:
                c['bbox_w_px'].append(s['bbox'][2] - s['bbox'][0])
        for k, c in per.items():
            b = c.pop('bbox_w_px')
            if b:
                c['whale_width_px_start_mid_end'] = [round(b[0]), round(b[len(b) // 2]), round(b[-1])]
            if c['min_dist_m'] > 1e8:
                c.pop('min_dist_m')
            else:
                c['min_dist_m'] = round(c['min_dist_m'], 2)
        qa['per_cut'] = per
    (a.out / 'v14-QA.json').write_text(json.dumps(qa, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('done', a.out)

if __name__ == '__main__':
    main()
