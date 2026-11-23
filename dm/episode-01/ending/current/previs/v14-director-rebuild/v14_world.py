#!/usr/bin/env python3
"""『空に降る雪』v14 previs — world, whale path and whale acting.

Coordinates (m): X right(east), Y away from the adventurers into the lake (north),
Z up, lake surface Z=0. Same frame as the v12/v13 previs so values can be compared.

Everything here is a PREVIS ASSUMPTION unless the storyboard says otherwise:
- cave scale, single asymmetric fissure rim at Z=190 (author decision),
- the rock canopy is modelled 40 m thick (rim 190 -> 230) and narrows upward like
  a slot canyon, so the effective moon beam is narrower than the bottom opening,
- moon direction: azimuth +Y, elevation 43 deg (v0.4 working value).
"""
import math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- utilities
def clamp(v, a=0.0, b=1.0):
    return np.minimum(b, np.maximum(a, v))

def smooth(u):
    u = clamp(u)
    return u * u * (3 - 2 * u)

def unit(v):
    v = np.asarray(v, float)
    return v / max(1e-9, float(np.linalg.norm(v)))

# ---------------------------------------------------------------- world
MOON_ELEV = math.radians(43.0)
MOON_DIR = np.array([0.0, math.cos(MOON_ELEV), math.sin(MOON_ELEV)])  # towards the moon
RIM_Z, TOP_Z = 190.0, 230.0
# (y, x_left, x_right) control table of the fissure (cavern-moonlight working model)
FISSURE = [(24, -9, 15), (70, -11, 17), (100, -25, 21), (135, -53, 26),
           (165, -62, 28), (185, -57, 30), (210, -24, 22), (250, -8, 14)]
TOP_NARROW = 0.45  # top rim half-width ratio (slot canyon)

def rim_polygon(z):
    """Fissure outline at height z as list of (x,y,z)."""
    if z >= TOP_Z - 1e-6:
        k = TOP_NARROW
    else:
        k = 1.0
    left, right = [], []
    for y, xl, xr in FISSURE:
        c, h = (xl + xr) / 2, (xr - xl) / 2 * k
        left.append((c - h, y, z))
        right.append((c + h, y, z))
    return left + right[::-1]

def _inside_rim(x, y, k):
    """Vectorised point-in-fissure test at a rim (k = half-width ratio)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    ys = np.array([r[0] for r in FISSURE], float)
    xl = np.array([r[1] for r in FISSURE], float)
    xr = np.array([r[2] for r in FISSURE], float)
    c = (xl + xr) / 2; h = (xr - xl) / 2 * k
    cc = np.interp(y, ys, c); hh = np.interp(y, ys, h)
    inside = (y >= ys[0]) & (y <= ys[-1]) & (np.abs(x - cc) <= hh)
    margin = hh - np.abs(x - cc)
    return inside, np.where((y >= ys[0]) & (y <= ys[-1]), margin, -50.0)

def moonlit(p, soft=2.5):
    """0..1 direct moonlight at world points p (N,3): ray towards the moon must pass
    both the bottom rim (Z=190) and the narrower top rim (Z=230)."""
    p = np.atleast_2d(np.asarray(p, float))
    out = np.ones(len(p))
    for z, k in ((RIM_Z, 1.0), (TOP_Z, TOP_NARROW)):
        s = (z - p[:, 2]) / MOON_DIR[2]
        x = p[:, 0] + s * MOON_DIR[0]; y = p[:, 1] + s * MOON_DIR[1]
        _, m = _inside_rim(x, y, k)
        out *= smooth(m / soft + 0.5)
    out[p[:, 2] >= TOP_Z] = 1.0
    return out

def sight_through_opening(cam, p):
    """1 if the segment cam->p passes through the opening (for points above the
    rim), 0 if blocked by the canopy rock. Points below the rim return 1."""
    p = np.atleast_2d(np.asarray(p, float)); cam = np.asarray(cam, float)
    vis = np.ones(len(p))
    for z, k in ((RIM_Z, 1.0), (TOP_Z, TOP_NARROW)):
        above = p[:, 2] > z
        if not above.any():
            continue
        s = (z - cam[2]) / np.maximum(1e-6, p[:, 2] - cam[2])
        x = cam[0] + s * (p[:, 0] - cam[0]); y = cam[1] + s * (p[:, 1] - cam[1])
        ins, _ = _inside_rim(x, y, k)
        vis = np.where(above & ~ins, 0.0, vis)
    return vis

SHORE = [(-200, 25), (-160, 25), (-135, -3), (-115, -15), (-95, -22), (-85, -26), (-70, -46), (-55, -61),
         (-40, -65), (-20, -69), (0, -64), (20, -42), (35, -30), (50, -12), (62, 3),
         (72, 15), (78, 29), (85, 38), (92, 32), (100, 20), (115, 15), (132, 43), (151, 100), (200, 200)]
_SX = np.array([s[0] for s in SHORE], float); _SY = np.array([s[1] for s in SHORE], float)

def shore_y(x):
    return np.interp(x, _SX, _SY)

def ground_z(x, y):
    """Land height (lake = 0). Land rises to ~2.5 m about 35 m inland (PC ledge)."""
    d = shore_y(x) - np.asarray(y, float)
    return np.where(d > 0, 2.5 * smooth(d / 35.0), 0.0)

def is_land(x, y):
    return shore_y(x) - np.asarray(y, float) > 0

PC = np.array([-58.0, -84.0, 2.5])          # adventurers (eye at +1.6)
PC_EYE = PC + np.array([0, 0, 1.6])
S1_SITES = [(40, -52), (55, -28), (66, 4), (72, 8), (85, 30), (90, 25)]  # base..tip, side

def p0_position():
    """Young flower P0: placed ~1 m inside the west edge of the moonlit footprint near
    the adventurers' shore, so that closed buds just outside stay in shadow."""
    y = -86.0
    xs = np.linspace(-60, 10, 701)
    pts = np.stack([xs, np.full_like(xs, y), ground_z(xs, y) + 0.05], 1)
    lit = moonlit(pts)
    x_edge = xs[np.argmax(lit > 0.5)]
    x = x_edge + 1.0
    return np.array([x, y, float(ground_z(x, y))])

P0 = p0_position()

# ---------------------------------------------------------------- whale path
# Waypoints (x, y, z, target speed m/s). A single continuous world path; the edit samples
# windows of it with time ellipsis between some cuts (v14 rule).
WAYPOINTS = [
    # underwater: along the shore heading west-north-west, passing UNDER the moonlit water
    # near the shore (the only lit water), then turning north
    (32, -28, -12, 4.0), (12, -47, -10.5, 4.0), (-10, -57, -8.5, 3.8), (-27, -55, -6.0, 3.6),
    (-37, -46, -3.0, 3.4),
    # quiet emergence just west of the moonlight edge, heading north (away from the shore)
    (-42, -33, 0.8, 3.4), (-44, -20, 4.0, 3.6),
    # one rising counter-clockwise spiral (radius ~40-45 m) that brings it back towards
    # the adventurers from the west: the 'spiral into the air' of v10
    (-54, 0, 7.0, 4.0), (-74, 15, 9.5, 4.4), (-98, 16, 11.5, 4.6), (-118, 2, 13.5, 4.8),
    (-127, -22, 15.0, 5.0), (-121, -48, 16.0, 5.0), (-104, -70, 16.5, 5.2), (-82, -82, 15.0, 5.4),
    # right over the adventurers heading east
    (-58, -84.5, 12.0, 5.8),
    # the one strong stroke: arc to the south-east, then head-first into the moon beam over land
    (-44, -90, 12.6, 5.6), (-33, -100, 14.2, 5.4), (-25, -112, 16.4, 5.0), (-15, -122, 18.8, 4.6),
    (0, -128, 21.0, 4.4), (16, -124, 22.0, 4.6), (29, -111, 22.0, 4.9), (37, -92, 21.3, 5.4),
    (42, -68, 20.6, 6.2),
    # skimming the S1 cape base -> tip
    (50, -38, 20.0, 7.0), (60, -16, 20.0, 7.0), (70, 4, 20.5, 7.0), (80, 22, 22.0, 6.8), (88, 38, 24.0, 6.2),
    # wide left turn over the lake (R13)
    (96, 62, 28.0, 5.6), (89, 86, 33.0, 5.2), (69, 100, 38.0, 5.0), (43, 99, 42.0, 5.0), (20, 89, 45.0, 4.9),
    # climax crossing to the west through the petal swarm (R14-R16)
    (0, 75, 47.0, 4.8), (-22, 65, 49.0, 4.8), (-44, 63, 51.0, 4.8),
    # right turn to the north and climb through the wide part of the fissure (R17-R18)
    (-63, 71, 56.0, 5.0), (-73, 90, 64.0, 5.2), (-70, 112, 76.0, 5.4), (-58, 130, 92.0, 5.5),
    (-42, 144, 112.0, 5.6), (-30, 154, 134.0, 5.6), (-22, 162, 156.0, 5.5), (-17, 169, 178.0, 5.4),
    (-15, 181, 200.0, 5.3), (-13, 193, 222.0, 5.3),
    # out of the narrow top slot, then levels off to the west over the rock: from the cave
    # floor the head disappears behind the thick rim first and the flukes last (R18)
    (-18, 202, 238.0, 6.0), (-34, 209, 246.0, 6.6), (-56, 214, 252.0, 6.8), (-80, 218, 257.0, 6.8),
    (-108, 222, 261.0, 6.8), (-140, 226, 265.0, 6.8),
]

def _catmull(pts, n=40):
    """Centripetal Catmull-Rom through pts (M,3); returns dense samples (K,3)."""
    P = np.asarray(pts, float)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        def tj(ti, a, b):
            return ti + max(1e-6, np.linalg.norm(b - a)) ** 0.5
        t0 = 0.0; t1 = tj(t0, p0, p1); t2 = tj(t1, p1, p2); t3 = tj(t2, p2, p3)
        for t in np.linspace(t1, t2, n, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(P[-2])
    return np.array(out)

STROKE_T = 5.6          # s, one stroke then glide (v10 ~6 s, N14 approved ~4.7 s)
POWER_FRAC = 0.46       # share of the cycle that is the active down+up stroke

class WhalePath:
    def __init__(self, waypoints=WAYPOINTS, dt=0.01):
        wp = np.array(waypoints, float)
        dense = _catmull(wp[:, :3], n=60)
        seg = np.linalg.norm(np.diff(dense, axis=0), axis=1)
        s = np.concatenate([[0], np.cumsum(seg)])
        # target speed along the path, interpolated from waypoint speeds by arc length
        wp_s = np.array([s[np.argmin(np.linalg.norm(dense - w, axis=1))] for w in wp[:, :3]])
        self.s_dense, self.p_dense = s, dense
        self.v_of_s = lambda q: np.interp(q, wp_s, wp[:, 3])
        self.length = s[-1]
        self.stroke_phase0 = 0.0
        self.fast_stroke_tau = None
        self._integrate(dt)

    # --- stroke timing --------------------------------------------------------
    def stroke_q(self, tau):
        return np.mod((np.asarray(tau, float) - self.stroke_phase0) / STROKE_T, 1.0)

    def surge(self, tau):
        """Speed gain after each power upstroke, then glide decay (0..1)."""
        q = self.stroke_q(tau)
        rise = smooth((q - 0.25) / 0.25)
        decay = np.exp(-np.maximum(0, q - 0.5) * STROKE_T / 2.2)
        return np.where(q < 0.5, rise, decay)

    def fast_gain(self, tau):
        if self.fast_stroke_tau is None:
            return 0.0 * np.asarray(tau, float)
        d = np.asarray(tau, float) - self.fast_stroke_tau
        return np.where(d < 0, smooth((d + 0.6) / 0.6), np.exp(-d / 1.6))

    def _integrate(self, dt):
        taus, ss = [0.0], [0.0]
        t, s = 0.0, 0.0
        while s < self.length:
            v = self.v_of_s(s) * (0.94 + 0.12 * self.surge(t)) * (1 + 0.55 * self.fast_gain(t))
            s += v * dt; t += dt
            taus.append(t); ss.append(min(s, self.length))
        self.tau_tab, self.s_tab = np.array(taus), np.array(ss)
        self.tau_end = t

    def retime(self, phase0=None, fast_tau=None, dt=0.01):
        if phase0 is not None:
            self.stroke_phase0 = phase0
        if fast_tau is not None:
            self.fast_stroke_tau = fast_tau
        self._integrate(dt)

    def s_at(self, tau):
        return np.interp(tau, self.tau_tab, self.s_tab)

    def pos(self, tau):
        s = self.s_at(tau)
        return np.stack([np.interp(s, self.s_dense, self.p_dense[:, i]) for i in range(3)], -1)

    def vel(self, tau, h=0.05):
        return (self.pos(np.asarray(tau) + h) - self.pos(np.asarray(tau) - h)) / (2 * h)

    def frame(self, tau, extra_roll=0.0):
        """Body frame: centre, forward, left, up (bank from horizontal curvature)."""
        p = self.pos(tau)
        f = unit(self.vel(tau))
        f1 = unit(self.vel(tau - 0.4)); f2 = unit(self.vel(tau + 0.4))
        h1 = math.atan2(f1[0], f1[1]); h2 = math.atan2(f2[0], f2[1])
        dpsi = (h2 - h1 + math.pi) % (2 * math.pi) - math.pi
        speed = float(np.linalg.norm(self.vel(tau)))
        yaw_rate = dpsi / 0.8                        # rad/s, + = turning right (clockwise)
        bank = float(np.clip(math.atan2(speed * yaw_rate, 3.2), -math.radians(13), math.radians(13)))
        bank += extra_roll
        wu = np.array([0, 0, 1.0])
        left = unit(np.cross(wu, f)) if abs(f[2]) < 0.999 else np.array([1.0, 0, 0])
        up = unit(np.cross(f, left))
        # roll about forward axis: positive bank = right wing down (into a right turn)
        c, s = math.cos(bank), math.sin(bank)
        left2 = c * left + s * up
        up2 = unit(np.cross(f, left2))
        return p, f, left2, up2

# ---------------------------------------------------------------- whale mesh & acting
_mesh = np.load(HERE / "wh01_v20_lowpoly_previs.npz")
BODY_V = _mesh["v0"].astype(float); BODY_F = _mesh["f0"].astype(int)
EYE_V = _mesh["v1"].astype(float); EYE_F = _mesh["f1"].astype(int)
XMIN, XMAX = BODY_V[:, 0].min(), BODY_V[:, 0].max()

def tail_wave(q, lag):
    """One stroke then glide: full sine over the power part, gentle residual in glide."""
    qq = np.mod(q - lag, 1.0)
    p = qq / POWER_FRAC
    power = np.sin(2 * np.pi * np.clip(p, 0, 1)) * (qq < POWER_FRAC)
    g = (qq - POWER_FRAC) / (1 - POWER_FRAC)
    glide = 0.10 * np.sin(2 * np.pi * g) * (qq >= POWER_FRAC)
    return power + glide

def deform(V, tau, path, amp=1.9, fin_amp=0.35):
    """Dorsoventral stroke (tail only), fluke angle, slow pectoral adjustment."""
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    q = path.stroke_q(tau)
    boost = 1.0 + 0.6 * float(path.fast_gain(tau))
    tail = clamp((5.0 - x) / (5.0 - XMIN)) ** 1.9
    lag = 0.10 * (1 - (x - XMIN) / (XMAX - XMIN))
    cz = amp * boost * tail * tail_wave(q, lag)
    # head counter-motion (very small)
    cz -= 0.10 * amp * clamp((x - 6.0) / 6.0) * tail_wave(q, 0.0)
    out = np.stack([x, y, z + cz], 1)
    # fluke angle of attack around the peduncle
    piv = -9.4
    fl = x < piv
    if fl.any():
        a = math.radians(14.0) * boost * float(np.cos(2 * np.pi * (q - 0.03) / POWER_FRAC)) * (q < POWER_FRAC)
        a += math.radians(3.0) * float(np.sin(2 * np.pi * q))
        dx = out[fl, 0] - piv; dz = out[fl, 2] - out[fl, 2].mean() * 0
        pz = amp * boost * (clamp((5.0 - piv) / (5.0 - XMIN)) ** 1.9) * float(tail_wave(q, 0.10 * (1 - (piv - XMIN) / (XMAX - XMIN))))
        rz = out[fl, 2] - pz
        out[fl, 0] = piv + dx * math.cos(a) - rz * math.sin(a)
        out[fl, 2] = pz + dx * math.sin(a) + rz * math.cos(a)
    # pectorals: slow stabilising sweep, not bird flapping
    fin = (np.abs(y) > 2.7) & (x > -6.5) & (x < 6.0)
    blade = clamp((np.abs(y) - 2.7) / 4.4)
    out[:, 2] += np.where(fin, blade * fin_amp * np.sin(2 * np.pi * (tau / 7.5) + np.sign(y) * 0.5), 0)
    return out

def world_vertices(Vloc, frame):
    p, f, l, u = frame
    return p + np.outer(Vloc[:, 0], f) + np.outer(Vloc[:, 1], l) + np.outer(Vloc[:, 2], u)
