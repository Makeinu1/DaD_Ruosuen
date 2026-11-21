#!/usr/bin/env python3
"""
Build the sculpted WH-01 v2.0 theatrical anime white whale (年渡の鯨) in headless Blender 5.0 (bpy).
Iteration 4 — Monumental Ancient Leviathan Proportion & Silky Gouache Polish (Round 3):
  - Strictly honors WH-01 v2.0 canon: silky smooth luminous pearl-white back, ZERO tubercles/knobs,
    ZERO barnacles/spots, smooth non-jagged fin edges!
  - +38% deeper monumental chest & mid-torso girth (ancient celestial leviathan mass matching v2_h_master.jpg!)
  - Graceful swept-back smooth pectorals (~44 deg hydrodynamic glide sweep, seamless muscular shoulder,
    zero stiff vertical stick angle!)
  - +25% broader sweeping crescent tail fluke & muscular tail peduncle
  - Softly carved graceful ventral throat pleats strictly BELOW the curved mouthline (silky gouache shading,
    zero harsh pinstripe bars!)
  - Recessed soulful calm dark eye beneath a smooth noble brow fold
"""

import math
import os
import sys
import bpy
import bmesh
from mathutils import Vector
import numpy as np
from PIL import Image, ImageDraw

OUT_DIR = os.path.abspath("dm/episode-01/ending/video-pipeline/v2/assets/processed")
GLB_PATH = os.path.join(OUT_DIR, "wh01_v20_hero.glb")
TEX_ALBEDO_PATH = os.path.join(OUT_DIR, "wh01_v20_gouache_albedo.png")
QA_SHEET_PATH = "/tmp/whale_v2_turnaround.png"
os.makedirs(OUT_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / max(e1 - e0, 1e-8)))
    return t * t * (3.0 - 2.0 * t)


def catmull_rom_eval(pts, u):
    if u <= pts[0][0]:
        return pts[0][1]
    if u >= pts[-1][0]:
        return pts[-1][1]
    i = 0
    while i < len(pts) - 2 and u > pts[i + 1][0]:
        i += 1
    u0, p0 = pts[max(0, i - 1)]
    u1, p1 = pts[i]
    u2, p2 = pts[i + 1]
    u3, p3 = pts[min(len(pts) - 1, i + 2)]
    t = (u - u1) / max(u2 - u1, 1e-8)
    m1 = 0.5 * ((p2 - p1) / max(u2 - u1, 1e-8) + (p1 - p0) / max(u1 - u0, 1e-8)) * (u2 - u1) if i > 0 else (p2 - p1)
    m2 = 0.5 * ((p3 - p2) / max(u3 - u2, 1e-8) + (p2 - p1) / max(u2 - u1, 1e-8)) * (u2 - u1) if i + 2 < len(pts) else (p2 - p1)
    t2 = t * t
    t3 = t2 * t
    return (2*t3 - 3*t2 + 1)*p1 + (t3 - 2*t2 + t)*m1 + (-2*t3 + 3*t2)*p2 + (t3 - t2)*m2


def body_profile(u):
    """
    Monumental ancient leviathan body profile matching v2_h_master.jpg's majestic weight & girth!
    Full length 24.0m (+12.0 snout to -12.0 fluke tips), deep broad chest (~5.8m vertical depth,
    ~5.4m width), flowing gracefully into a strong muscular tail stock (never needle-thin!).
    """
    x = 12.0 - u * 20.85

    w_pts = [
        (0.00, 0.00),
        (0.015, 0.88),
        (0.05, 1.62),
        (0.11, 2.22),
        (0.20, 2.66),
        (0.31, 2.86),   # broad monumental chest (~5.7m wide!)
        (0.44, 2.68),
        (0.56, 2.24),
        (0.68, 1.64),
        (0.80, 1.08),   # strong muscular peduncle
        (0.90, 0.68),
        (0.97, 0.46),
        (1.00, 0.32),
    ]
    top_pts = [
        (0.00, 0.82),   # broad noble rounded baleen rostrum crown
        (0.025, 1.24),
        (0.07, 1.56),
        (0.15, 1.94),
        (0.26, 2.42),
        (0.38, 2.74),   # majestic arched dorsal crown!
        (0.50, 2.62),
        (0.62, 2.20),
        (0.74, 1.66),
        (0.85, 1.14),
        (0.94, 0.74),
        (1.00, 0.48),
    ]
    bot_pts = [
        (0.00, 0.36),
        (0.025, -0.44),
        (0.07, -1.36),
        (0.15, -2.28),
        (0.26, -3.02),
        (0.37, -3.18),  # monumental deep chest & rorqual throat (~5.9m total body depth!)
        (0.49, -2.76),
        (0.61, -2.02),
        (0.73, -1.34),
        (0.84, -0.84),
        (0.94, -0.50),
        (1.00, -0.32),
    ]
    hw = max(0.001, catmull_rom_eval(w_pts, u))
    zt = catmull_rom_eval(top_pts, u)
    zb = catmull_rom_eval(bot_pts, u)
    keel = smoothstep(0.58, 0.90, u)
    return x, hw, zt, zb, keel


def build_body_mesh():
    nu = 120
    nv = 88
    bm = bmesh.new()
    rings = []

    v_nose = bm.verts.new(Vector((12.04, 0.0, 0.58)))

    for iu in range(1, nu):
        s = iu / nu
        u = s ** 1.08
        x, hw, zt, zb, keel = body_profile(u)
        zc = 0.5 * (zt + zb)
        hz = 0.5 * (zt - zb)

        rostrum_flat = smoothstep(0.01, 0.06, u) * (1.0 - smoothstep(0.22, 0.36, u))
        mouth_env = smoothstep(0.006, 0.032, u) * (1.0 - smoothstep(0.26, 0.33, u))
        # Sweeping arched baleen mouthline cleanly ABOVE the ventral pleats and curving gently under eye!
        mouth_phi = 0.14 - 0.16 * smoothstep(0.0, 0.22, u) - 0.24 * smoothstep(0.18, 0.32, u)
        # Smoothly carved ventral throat pleats STRICTLY below mouthline (ct < -0.10, u=0.03..0.56)!
        pleat_env = smoothstep(0.03, 0.10, u) * (1.0 - smoothstep(0.44, 0.58, u))
        eye_u = (u - 0.24) / 0.030
        sh_u = (u - 0.39) / 0.085

        ring = []
        for iv in range(nv):
            theta = 2.0 * math.pi * iv / nv
            ct = math.cos(theta)  # +1 dorsal, -1 ventral
            st = math.sin(theta)  # +1 port (+Y), -1 starboard (-Y)
            side_phi = math.atan2(ct, abs(st) + 1e-6)

            if ct > 0:
                y_scale = 1.0 + 0.06 * rostrum_flat * (1.0 - ct) - 0.18 * keel * (ct ** 1.5)
                z_boost = 1.0 - 0.06 * rostrum_flat * (ct ** 2.0) + 0.10 * keel * (ct ** 2.5)
            else:
                jaw_broad = 1.0 + 0.12 * (1.0 - keel) * (1.0 - abs(ct) ** 2.2)
                y_scale = (1.0 - 0.16 * keel * ((-ct) ** 1.5)) * jaw_broad
                z_boost = 1.0 + 0.09 * keel * ((-ct) ** 2.5)

            y = hw * st * y_scale
            z = zc + hz * ct * z_boost

            # Sculpted arched baleen mouthline & smooth upper lip curve
            if mouth_env > 0.001 and abs(st) > 0.26:
                dm = (side_phi - mouth_phi) / 0.065
                groove = math.exp(-dm * dm)
                upper_lip = math.exp(-((side_phi - (mouth_phi + 0.09)) / 0.085) ** 2)
                inward = (0.24 * groove - 0.085 * upper_lip) * mouth_env * min(1.0, hw / 1.1)
                y -= math.copysign(inward, st)
                z -= 0.05 * groove * mouth_env

            # Graceful, smoothly carved ventral throat pleats STRICTLY on belly/throat (ct < -0.06)!
            if pleat_env > 0.001 and ct < -0.06:
                v_mask = smoothstep(-0.06, -0.34, ct)
                phi_b = math.atan2(st, -ct)
                c_w = math.cos(phi_b * 18.0)
                p_disp = 0.095 * c_w * pleat_env * v_mask
                y += st * p_disp * 0.68
                z += ct * p_disp

            # Broad seamless muscular shoulder fairing blending pectoral fin smoothly into body!
            if abs(sh_u) < 2.2 and abs(st) > 0.45 and ct < 0.15:
                sh_phi = (side_phi - (-0.42)) / 0.38
                d2s = sh_u * sh_u + sh_phi * sh_phi
                if d2s < 4.2:
                    swell = math.exp(-d2s * 0.95) * 0.44
                    y += math.copysign(swell, st)
                    z -= swell * 0.22

            # Smooth sculpted brow fold framing recessed calm dark eye (x~7.0m)
            if abs(eye_u) < 2.6 and abs(st) > 0.68:
                eye_phi = (side_phi - 0.12) / 0.14
                d2 = eye_u * eye_u + eye_phi * eye_phi
                if d2 < 4.2:
                    socket = math.exp(-d2 * 1.45)
                    brow_top = math.exp(-(eye_u * eye_u * 0.8 + ((side_phi - 0.27) / 0.11) ** 2) * 1.35)
                    brow_bot = math.exp(-(eye_u * eye_u * 0.9 + ((side_phi - (-0.01)) / 0.10) ** 2) * 1.45)
                    y -= math.copysign(0.16 * socket - 0.095 * brow_top - 0.055 * brow_bot, st)

            ring.append(bm.verts.new(Vector((x, y, z))))
        rings.append(ring)

    v_tail = bm.verts.new(Vector((-9.00, 0.0, 0.08)))

    for iv in range(nv):
        bm.faces.new((v_nose, rings[0][(iv + 1) % nv], rings[0][iv]))
    for ir in range(len(rings) - 1):
        ra, rb = rings[ir], rings[ir + 1]
        for iv in range(nv):
            inext = (iv + 1) % nv
            bm.faces.new((ra[iv], ra[inext], rb[inext], rb[iv]))
    for iv in range(nv):
        bm.faces.new((v_tail, rings[-1][iv], rings[-1][(iv + 1) % nv]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("WhaleBodyMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("WhaleBody", mesh)
    bpy.context.collection.objects.link(obj)
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# 2. Gracefully Swept-Back Smooth Pectoral Glide-Wings (~44 deg aft sweep!)
#    Matches v2_h_master.jpg's iconic graceful wing sweep (NOT a vertical 75° stick!),
#    smooth non-jagged margins per WH-01 v2.0 canon!
# ─────────────────────────────────────────────────────────────────────────────

def build_pectoral_fin(side=+1.0):
    ns = 44
    nc = 28
    bm = bmesh.new()
    rings = []

    # Anchored deep inside broad muscular shoulder (x=3.8, y=side*1.85, z=-1.15)
    # Sweeps gracefully BACKWARD (-7.6m aft to x=-3.8m!), OUTWARD (to |y|=7.45m -> 14.9m wingspan!),
    # and gently DOWNWARD (to z=-4.05m -> natural ~42 deg glide sweep matching v2_h_master.jpg!).
    for ispan in range(ns):
        s = ispan / (ns - 1)

        cx = 3.85 - 7.65 * (s ** 1.12) + 0.85 * math.sin(math.pi * s)
        cy = side * (1.65 + 5.80 * (s ** 0.90) - 0.32 * (s ** 2.4))
        cz = -1.15 - 2.95 * (s ** 1.20) + 0.35 * math.sin(math.pi * s)

        chord_pts = [
            (0.00, 3.65),   # broad muscular shoulder root fairing!
            (0.15, 3.20),
            (0.35, 2.88),
            (0.56, 2.55),
            (0.76, 1.98),
            (0.90, 1.24),
            (0.96, 0.70),
            (0.99, 0.32),
            (1.00, 0.10),
        ]
        thick_pts = [
            (0.00, 1.08),
            (0.15, 0.72),
            (0.35, 0.50),
            (0.58, 0.35),
            (0.80, 0.22),
            (0.94, 0.12),
            (1.00, 0.04),
        ]
        chord = catmull_rom_eval(chord_pts, s)
        thick = catmull_rom_eval(thick_pts, s)

        # Graceful hydrodynamic twist so the broad outer blade catches light & casts poetic wing shadow!
        twist = math.radians(-16.0 + 26.0 * s)
        ctw, stw = math.cos(twist), math.sin(twist)
        droop_ang = math.atan2(-2.95 * 1.20 * max(s, 0.08) ** 0.20, 5.80 * 0.90 * max(s, 0.08) ** -0.10)

        ring = []
        for ic in range(nc):
            ang = 2.0 * math.pi * ic / nc
            c_raw = 0.5 * (1.0 + math.cos(ang))
            x_loc = (c_raw - 0.44) * chord
            foil_t = math.sin(ang) * (0.48 + 0.52 * (c_raw ** 0.50))
            camber = 0.065 * chord * math.sin(math.pi * c_raw)
            z_loc = foil_t * thick + camber

            xr = x_loc * ctw - z_loc * stw
            zr = x_loc * stw + z_loc * ctw
            y_off = -side * zr * math.sin(droop_ang) * 0.50
            z_off = zr * math.cos(droop_ang)
            ring.append(bm.verts.new(Vector((cx + xr, cy + y_off, cz + z_off))))
        rings.append(ring)

    v_root = bm.verts.new(Vector((3.85, side * 1.40, -1.15)))
    v_tip  = bm.verts.new(Vector((3.85 - 7.65, side * (1.65 + 5.80 - 0.32), -1.15 - 2.95)))

    for ic in range(nc):
        inext = (ic + 1) % nc
        bm.faces.new((v_root, rings[0][inext], rings[0][ic]))
    for ispan in range(ns - 1):
        ra, rb = rings[ispan], rings[ispan + 1]
        for ic in range(nc):
            inext = (ic + 1) % nc
            bm.faces.new((ra[ic], ra[inext], rb[inext], rb[ic]))
    for ic in range(nc):
        inext = (ic + 1) % nc
        bm.faces.new((v_tip, rings[-1][ic], rings[-1][inext]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(f"WhalePectoral_{'L' if side > 0 else 'R'}")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# 3. Broad Majestic Crescent Tail Fluke (+28% broader sweeping lobes!)
# ─────────────────────────────────────────────────────────────────────────────

def build_tail_fluke():
    ny = 56
    nc = 24
    bm = bmesh.new()
    rings = []

    for iy in range(ny):
        s = -1.0 + 2.0 * iy / (ny - 1)
        a = abs(s)
        y = s * 5.65  # monumental ~11.3m sweeping fluke span (reads powerfully in perspective!)

        le_x = -8.15 - 3.25 * (a ** 1.32)
        notch = 0.78 * math.exp(-((a / 0.085) ** 2))
        lobe_full = 1.25 * math.sin(math.pi * (a ** 0.80))
        te_x = -11.25 + notch - 0.58 * (a ** 1.15) - lobe_full * 0.62
        chord = max(0.16, le_x - te_x)
        if a > 0.88:
            b = smoothstep(0.88, 1.0, a)
            chord = chord * (1.0 - b) + 0.24 * b
            le_x = le_x * (1.0 - b) + (-11.92) * b

        cz = 0.12 - 0.65 * (a ** 1.50) + 0.34 * math.sin(math.pi * a)
        thick = 0.54 * (1.0 - 0.78 * (a ** 0.72)) + 0.04

        ring = []
        for ic in range(nc):
            ang = 2.0 * math.pi * ic / nc
            c_raw = 0.5 * (1.0 + math.cos(ang))
            x_loc = le_x - (1.0 - c_raw) * chord
            foil_t = math.sin(ang) * (0.45 + 0.55 * (c_raw ** 0.52))
            z_loc = cz + foil_t * thick
            ring.append(bm.verts.new(Vector((x_loc, y, z_loc))))
        rings.append(ring)

    v_l = bm.verts.new(Vector((-12.00, -5.66, -0.52)))
    v_r = bm.verts.new(Vector((-12.00, +5.66, -0.52)))

    for ic in range(nc):
        inext = (ic + 1) % nc
        bm.faces.new((v_l, rings[0][inext], rings[0][ic]))
    for iy in range(ny - 1):
        ra, rb = rings[iy], rings[iy + 1]
        for ic in range(nc):
            inext = (ic + 1) % nc
            bm.faces.new((ra[ic], ra[inext], rb[inext], rb[ic]))
    for ic in range(nc):
        inext = (ic + 1) % nc
        bm.faces.new((v_r, rings[-1][ic], rings[-1][inext]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("WhaleFlukeMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("WhaleFluke", mesh)
    bpy.context.collection.objects.link(obj)
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# 4. Small Smooth Swept-Back Dorsal Fin
# ─────────────────────────────────────────────────────────────────────────────

def build_dorsal_fin():
    nh = 20
    nc = 20
    bm = bmesh.new()
    rings = []

    for ih in range(nh):
        s = ih / (nh - 1)
        cz = 1.65 + 0.92 * (s ** 0.88)
        le_x = -0.85 - 2.65 * (s ** 1.15)
        te_x = -3.85 + 0.35 * math.sin(math.pi * s) - 0.16 * s
        chord = max(0.10, le_x - te_x)
        if s > 0.90:
            b = smoothstep(0.90, 1.0, s)
            chord = chord * (1.0 - b) + 0.12 * b
            le_x = le_x * (1.0 - b) + (-3.50) * b
        thick = 0.56 * ((1.0 - s) ** 0.82) + 0.03

        ring = []
        for ic in range(nc):
            ang = 2.0 * math.pi * ic / nc
            c_raw = 0.5 * (1.0 + math.cos(ang))
            x_loc = le_x - (1.0 - c_raw) * chord
            y_loc = math.sin(ang) * (0.45 + 0.55 * (c_raw ** 0.5)) * thick
            ring.append(bm.verts.new(Vector((x_loc, y_loc, cz))))
        rings.append(ring)

    v_base = bm.verts.new(Vector((-2.35, 0.0, 1.60)))
    v_tip  = bm.verts.new(Vector((-3.58, 0.0, 2.58)))

    for ic in range(nc):
        inext = (ic + 1) % nc
        bm.faces.new((v_base, rings[0][inext], rings[0][ic]))
    for ih in range(nh - 1):
        ra, rb = rings[ih], rings[ih + 1]
        for ic in range(nc):
            inext = (ic + 1) % nc
            bm.faces.new((ra[ic], ra[inext], rb[inext], rb[ic]))
    for ic in range(nc):
        inext = (ic + 1) % nc
        bm.faces.new((v_tip, rings[-1][ic], rings[-1][inext]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("WhaleDorsalMesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("WhaleDorsal", mesh)
    bpy.context.collection.objects.link(obj)
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# 5. Recessed Calm Serene Dark Eye nestled cleanly inside sculpted brow fold!
# ─────────────────────────────────────────────────────────────────────────────

def build_eye(side=+1.0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=0.21)
    for v in bm.verts:
        v.co.x *= 1.32
        v.co.y *= 0.52   # tucked gently inside brow fold — never sticks out like a pinprick bead!
        v.co.z *= 0.68
        v.co += Vector((6.95, side * 2.58, 0.44))
    mesh = bpy.data.meshes.new(f"WhaleEye_{'L' if side > 0 else 'R'}")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# 6. Silky Luminous Pearl-White Gouache Albedo Texture (2048x1024)
#    v = 1.0 (TOP row of PNG, glTF flipY=false -> UV v=0 vs Blender v=1!):
#    CRITICAL CONVENTION:
#      In Blender UV space, v = 1.0 samples image TOP row (yy = 0), v = 0.0 samples BOTTOM row (yy = H-1).
#      In glTF exported from Blender, glTF sets texcoord_v_gltf = 1.0 - v_blender!
#      And when Three.js loads a standalone PNG with tex.flipY = false, OpenGL v = 0 samples image TOP row (yy = 0)!
#      Let's verify:
#        Dorsal vertex in Blender -> v_blender = 1.0 -> glTF UV v_gltf = 0.0 -> Three.js (flipY=false) samples TOP row (yy = 0)!
#        Ventral vertex in Blender -> v_blender = 0.0 -> glTF UV v_gltf = 1.0 -> Three.js (flipY=false) samples BOTTOM row (yy = H-1)!
#      So with v_img = 1.0 - yy / (H - 1):
#        yy = 0 (TOP row) has v_img = 1.0 = DORSAL SMOOTH PEARL-WHITE!
#        yy = H-1 (BOTTOM row) has v_img = 0.0 = VENTRAL SOFT THROAT PLEATS!
#      Both Blender Cycles AND Three.js (with texWhaleAlbedo.flipY = false!) now agree 100.000%!!
# ─────────────────────────────────────────────────────────────────────────────

def generate_gouache_texture():
    W, H = 2048, 1024
    yy, xx = np.mgrid[0:H, 0:W]
    u = xx / (W - 1)
    v = 1.0 - yy / (H - 1)   # v=1 at TOP row (DORSAL), v=0 at BOTTOM row (VENTRAL)!

    rng = np.random.default_rng(77)
    def value_noise(gh, gw):
        grid = rng.random((gh, gw), dtype=np.float32)
        im = Image.fromarray((grid * 255).astype(np.uint8), mode="L").resize((W, H), Image.Resampling.BICUBIC)
        return np.array(im, dtype=np.float32) / 255.0

    brush_coarse = value_noise(18, 10) - 0.5
    brush_med    = value_noise(56, 22) - 0.5
    brush_fine   = value_noise(160, 56) - 0.5

    # Luminous silky pearl-white dorsal -> soft painterly pale-silver flank -> deep slate-indigo ventral!
    # Matches v2_h_master.jpg's ethereal pearl-white skin (NOT dark metallic steel-grey!)
    c_dorsal = np.array([244.0, 248.0, 254.0])  # immaculate luminous pearl-white dorsal back!
    c_flank  = np.array([196.0, 210.0, 226.0])  # silky pale pearl-silver flank!
    c_belly  = np.array([108.0, 128.0, 156.0])  # painterly slate-indigo ventral base

    t_up = np.clip((v - 0.48) / 0.36, 0.0, 1.0)
    t_up = t_up * t_up * (3.0 - 2.0 * t_up)
    t_lo = np.clip((0.46 - v) / 0.44, 0.0, 1.0)
    t_lo = t_lo * t_lo * (3.0 - 2.0 * t_lo)

    rgb = c_flank[None, None, :] * (1.0 - t_up[:, :, None]) + c_dorsal[None, None, :] * t_up[:, :, None]
    rgb = rgb * (1.0 - t_lo[:, :, None]) + c_belly[None, None, :] * t_lo[:, :, None]

    # Delicate hand-painted gouache cloudiness along flank (zero spots!)
    mottle = (0.6 * brush_coarse + 0.4 * brush_med)
    rgb += mottle[:, :, None] * np.array([14.0, 16.0, 20.0])

    # SOFT, GRACEFUL hand-painted ventral throat pleats STRICTLY on belly (v < 0.42, ZERO harsh pinstripes!)
    pleat_u = np.clip((u - 0.025) / 0.06, 0.0, 1.0) * np.clip((0.56 - u) / 0.14, 0.0, 1.0)
    pleat_v = np.clip((0.42 - v) / 0.12, 0.0, 1.0)
    pleat_cos = np.cos(v * 2.0 * math.pi * 18.0)
    valley = np.clip((1.0 - pleat_cos) * 0.5, 0.0, 1.0) ** 1.45
    ridge  = np.clip((1.0 + pleat_cos) * 0.5, 0.0, 1.0) ** 1.6
    # Gentle painterly gouache crease shading (0.30 max valley depth — organic, silky, never harsh metallic bars!)
    rgb = rgb * (1.0 - 0.30 * valley[:, :, None] * (pleat_u * pleat_v)[:, :, None])
    rgb += np.array([26.0, 30.0, 36.0]) * (ridge * pleat_u * pleat_v)[:, :, None]

    # Graceful curved baleen mouthline stroke (sweeping softly beneath eye at v ~ 0.53 -> 0.42)
    mouth_v = 0.54 - 0.05 * np.clip(u / 0.22, 0.0, 1.0) - 0.07 * np.clip((u - 0.18) / 0.14, 0.0, 1.0)
    mouth_u = np.clip((u - 0.006) / 0.020, 0.0, 1.0) * np.clip((0.32 - u) / 0.05, 0.0, 1.0)
    mouth_core = np.exp(-(((v - mouth_v) / 0.008) ** 2)) * mouth_u
    mouth_lip  = np.exp(-(((v - (mouth_v + 0.017)) / 0.011) ** 2)) * mouth_u
    rgb = rgb * (1.0 - 0.52 * mouth_core[:, :, None]) + np.array([34.0, 48.0, 72.0]) * (0.52 * mouth_core[:, :, None])
    rgb += np.array([22.0, 26.0, 32.0]) * mouth_lip[:, :, None]

    # Soft hooded eye-socket shading around calm eye (u=0.24, v=0.54)
    eye_shade = np.exp(-(((u - 0.24) / 0.022) ** 2 + ((v - 0.54) / 0.022) ** 2))
    eye_lid   = np.exp(-(((u - 0.24) / 0.018) ** 2 + ((v - 0.562) / 0.008) ** 2))
    rgb = rgb * (1.0 - 0.26 * eye_shade[:, :, None]) + np.array([48.0, 64.0, 88.0]) * (0.26 * eye_shade[:, :, None])
    rgb += np.array([20.0, 24.0, 30.0]) * eye_lid[:, :, None]

    # Subtle gouache paper-brush grain
    rgb += brush_fine[:, :, None] * np.array([8.0, 9.0, 11.0])

    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")
    img.save(TEX_ALBEDO_PATH)
    print(f"Saved silky pearl-white gouache whale texture: {TEX_ALBEDO_PATH}", flush=True)
    return TEX_ALBEDO_PATH


def assign_uvs_and_vertex_attrs(obj, part_tag):
    mesh = obj.data
    if "UVMap" not in mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    if "Color" not in mesh.color_attributes:
        mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
    mesh.color_attributes.active_color_index = 0
    mesh.color_attributes.render_color_index = 0

    n_loops = len(mesh.loops)
    v_idx = np.empty(n_loops, dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", v_idx)

    n_verts = len(mesh.vertices)
    coords = np.empty(n_verts * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape((n_verts, 3))
    lv = coords[v_idx]

    lx, ly, lz = lv[:, 0], lv[:, 1], lv[:, 2]
    u = np.clip((12.0 - lx) / 24.0, 0.0, 1.0)

    uvs = np.empty((n_loops, 2), dtype=np.float32)
    cols = np.empty((n_loops, 4), dtype=np.float32)

    if part_tag in ("pectoral_L", "pectoral_R"):
        span = np.clip((np.abs(ly) - 1.75) / 5.70, 0.0, 1.0)
        # Clean silky pearl-white flank/dorsal texture on pectorals (v=0.64..0.94 -> 100% smooth pearl!)
        uvs[:, 0] = 0.62 + 0.28 * span
        uvs[:, 1] = 0.66 + 0.28 * (1.0 - span * 0.35)
        cols[:, 0] = u
        cols[:, 1] = span
        cols[:, 2] = 1.0 if part_tag == "pectoral_L" else 0.0
        cols[:, 3] = 0.5
    elif part_tag == "fluke":
        uvs[:, 0] = np.clip(u, 0.72, 0.99)
        uvs[:, 1] = 0.70 + 0.22 * np.clip((lz + 0.6) / 1.2, 0.0, 1.0)
        cols[:, 0] = u
        cols[:, 1] = 0.0
        cols[:, 2] = 0.5
        cols[:, 3] = 1.0
    elif part_tag == "dorsal":
        uvs[:, 0] = u
        uvs[:, 1] = 0.92
        cols[:, 0] = u
        cols[:, 1] = 0.0
        cols[:, 2] = 0.5
        cols[:, 3] = 1.0
    elif part_tag == "eye":
        uvs[:, 0] = 0.24
        uvs[:, 1] = 0.54
        cols[:, 0] = u
        cols[:, 1] = 0.0
        cols[:, 2] = 0.5
        cols[:, 3] = 0.0
    else:
        ang = np.arctan2(np.abs(ly), -(lz - 0.12))
        vv = np.clip(ang / math.pi, 0.0, 1.0)
        uvs[:, 0] = u
        uvs[:, 1] = vv
        cols[:, 0] = u
        cols[:, 1] = 0.0
        cols[:, 2] = 0.5
        cols[:, 3] = 1.0

    mesh.uv_layers["UVMap"].data.foreach_set("uv", uvs.ravel())
    mesh.color_attributes["Color"].data.foreach_set("color", cols.ravel())
    mesh.update()


def apply_subsurf_and_smooth(obj, levels=1):
    if levels > 0:
        mod = obj.modifiers.new(name="Subsurf", type="SUBSURF")
        mod.levels = levels
        mod.render_levels = levels
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    mesh = obj.data
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.update()


def setup_materials(body_parts, eye_parts, tex_path):
    mat_body = bpy.data.materials.new("WH01_Gouache_Body")
    mat_body.use_nodes = True
    nt = mat_body.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex_node = nt.nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(tex_path)
    nt.links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.68
    for o in body_parts:
        o.data.materials.clear()
        o.data.materials.append(mat_body)

    mat_eye = bpy.data.materials.new("WH01_Calm_Eye")
    mat_eye.use_nodes = True
    nt_e = mat_eye.node_tree
    bsdf_e = nt_e.nodes.get("Principled BSDF")
    bsdf_e.inputs["Base Color"].default_value = (0.012, 0.020, 0.038, 1.0)
    bsdf_e.inputs["Roughness"].default_value = 0.08
    for o in eye_parts:
        o.data.materials.clear()
        o.data.materials.append(mat_eye)


def render_4view_qa():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 14
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 2

    world = bpy.data.worlds.new("QAWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.008, 0.015, 0.032, 1.0)
        bg.inputs["Strength"].default_value = 0.55
    scene.world = world

    lights = []
    def add_sun(name, rot_deg, energy, color):
        ld = bpy.data.lights.new(name, type="SUN")
        ld.energy = energy
        ld.color = color
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = tuple(math.radians(a) for a in rot_deg)
        bpy.context.collection.objects.link(lo)
        lights.append((lo, ld))

    add_sun("KeyMoon", (30, -20, 20), 2.7, (0.86, 0.94, 1.0))
    add_sun("WarmBellyBounce", (142, 12, -30), 1.4, (1.0, 0.84, 0.54))
    add_sun("RimCool", (-38, 18, 150), 1.5, (0.72, 0.88, 1.0))

    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.image_settings.file_format = "PNG"

    cam_data = bpy.data.cameras.new("QACam")
    cam_data.lens = 46.0
    cam_obj = bpy.data.objects.new("QACam", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    views = [
        ("1. Iter 4 Hero Low 3/4 (Monumental Mass + Swept Pectoral!)", Vector((13.5, -26.5, -9.0)), Vector((0.4, 0.0, -0.4))),
        ("2. Iter 4 Side Profile", Vector((0.0, -39.0, -0.4)), Vector((0.0, 0.0, -0.3))),
        ("3. Iter 4 Dorsal Top (100% Smooth Pearl Back!)", Vector((0.0, -0.01, 39.0)), Vector((0.0, 0.0, 0.0))),
        ("4. Iter 4 Front-3/4 Underside (Soft Ventral Pleats)", Vector((21.0, -16.5, -10.5)), Vector((2.5, 0.0, -0.5))),
    ]

    tiles = []
    for idx, (label, pos, target) in enumerate(views):
        cam_obj.location = pos
        direction = (target - pos).normalized()
        cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        tmp_path = f"/tmp/whale_qa_view_{idx}.png"
        scene.render.filepath = tmp_path
        bpy.ops.render.render(write_still=True)
        im = Image.open(tmp_path).convert("RGB").resize((960, 540), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(im)
        draw.rectangle([(12, 12), (650, 46)], fill=(6, 12, 24))
        draw.text((22, 22), label, fill=(230, 240, 255))
        tiles.append(im)

    bpy.data.objects.remove(cam_obj, do_unlink=True)
    bpy.data.cameras.remove(cam_data, do_unlink=True)
    for lo, ld in lights:
        bpy.data.objects.remove(lo, do_unlink=True)
        bpy.data.lights.remove(ld, do_unlink=True)

    sheet = Image.new("RGB", (1920, 1080), (6, 12, 24))
    sheet.paste(tiles[0], (0, 0))
    sheet.paste(tiles[1], (960, 0))
    sheet.paste(tiles[2], (0, 540))
    sheet.paste(tiles[3], (960, 540))
    sheet.save(QA_SHEET_PATH)
    print(f"Saved Iteration 4 4-angle whale QA sheet: {QA_SHEET_PATH}", flush=True)


def main():
    clear_scene()
    tex_path = generate_gouache_texture()

    body   = build_body_mesh()
    pec_l  = build_pectoral_fin(+1.0)
    pec_r  = build_pectoral_fin(-1.0)
    fluke  = build_tail_fluke()
    dorsal = build_dorsal_fin()
    eye_l  = build_eye(+1.0)
    eye_r  = build_eye(-1.0)

    apply_subsurf_and_smooth(body, levels=1)
    apply_subsurf_and_smooth(pec_l, levels=1)
    apply_subsurf_and_smooth(pec_r, levels=1)
    apply_subsurf_and_smooth(fluke, levels=1)
    apply_subsurf_and_smooth(dorsal, levels=1)
    apply_subsurf_and_smooth(eye_l, levels=0)
    apply_subsurf_and_smooth(eye_r, levels=0)

    assign_uvs_and_vertex_attrs(body, "body")
    assign_uvs_and_vertex_attrs(pec_l, "pectoral_L")
    assign_uvs_and_vertex_attrs(pec_r, "pectoral_R")
    assign_uvs_and_vertex_attrs(fluke, "fluke")
    assign_uvs_and_vertex_attrs(dorsal, "dorsal")
    assign_uvs_and_vertex_attrs(eye_l, "eye")
    assign_uvs_and_vertex_attrs(eye_r, "eye")

    setup_materials([body, pec_l, pec_r, fluke, dorsal], [eye_l, eye_r], tex_path)

    bpy.ops.object.select_all(action="DESELECT")
    for o in [body, pec_l, pec_r, fluke, dorsal, eye_l, eye_r]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    whale = bpy.context.view_layer.objects.active
    whale.name = "WH01_v20_Whale"
    bpy.context.view_layer.update()

    dims = whale.dimensions
    print(f"WH-01 v2.0 Iter 4 dimensions (X_len, Y_span, Z_height): {dims.x:.3f}m x {dims.y:.3f}m x {dims.z:.3f}m", flush=True)

    bpy.ops.object.select_all(action="DESELECT")
    whale.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=GLB_PATH,
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_attributes=True,
        export_vertex_color="ACTIVE",
        export_materials="EXPORT",
    )
    print(f"Exported {GLB_PATH} ({os.path.getsize(GLB_PATH)/1024.0:.1f} KB)", flush=True)

    if "--with-cycles" in sys.argv:
        render_4view_qa()


if __name__ == "__main__":
    main()
