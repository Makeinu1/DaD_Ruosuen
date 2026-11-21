#!/usr/bin/env python3
"""
V7 Step 5B: Director's Cut Hero Camera Proof (4 x 960x540 Cycles GPU on Colab NVIDIA L4).
Tests the 4 soul-shaking camera upgrades (A+C Hybrid + Cut 4 Heigei Close-Up):
  1. dc01_heigei_closeup_28s — Cut 4 (50mm, 20-deg front-quarter close-up): Massive snout + serene eye gazing at player!
  2. dc02_ground_bloom_43s   — Cut 6B (Z=0.45m ground-skimming): Delicate 5-petal flowers blooming + golden seeds lifting off + lit whale reflected in mirror lake!
  3. dc03_aerial_track_50s   — Cut 7A (28mm airborne tracking): Camera lifts off the ground to fly alongside the Pearl-Opal whale through golden snow parallax!
  4. dc04_panorama_sym_59s   — Cut 7B (18mm grand panorama): Pull-back revealing 450m cavern, vertical canyon moon, mirror-lake symmetry, & upside-down golden snow!

Also includes Iteration-3 visual polish:
  - Macro noise breakup on cavern basalt walls (ZERO repeating tile rhythm!)
  - Richer Pearl-Opal thin-film iridescence (Ice-Cyan -> Alabaster -> Whisper Sakura -> Champagne-Gold)
"""

import math
import os
import random
import time
from pathlib import Path

import bpy
import bmesh
from mathutils import Euler, Matrix, Vector

CONFIG = {
    "render_res": (960, 540),
    "samples": 48,
    "exposure_locked": 0.0,
    "cliff_albedo_mul": 0.56,
    "cliff_tile_m": 24.0,             # Larger 24m tile + macro noise breakup -> ZERO visible tiling!
    "shore_albedo_mul": 0.44,
    "water_roughness": 0.016,         # Extra-crisp mirror-lake symmetry for Cut 6B & Cut 7B!
    "water_deep_absorb": 0.32,
    "moon_emission": 12.0,
    "moon_sun_energy_locked": 3.2,
    "moon_spot_energy_locked": 160000.0,
    "cavern_sky_bounce_energy": 1950000.0,
    "cavern_lake_bounce_energy": 520000.0,
    "beam_volume_density": 0.00048,
    "whale_unlit_albedo_mul": 0.58,
    "whale_ignite_emit": 3.2,
    "whale_climax_emit": 2.35,        # Rich sculpted Pearl-Opal -> Sakura -> Champagne-Gold (ZERO whiteout!)
    "whale_light_power": 380000.0,
    "flower_open_emit": 0.72,
    "flower_seed_emit": 2.5,
    "petal_emit": 1.80,
    "n_shore_flowers": 5400,
    "n_blizzard_petals": 3000,
    "glare_threshold": 1.55,
    "glare_mix": -0.72,
}

BASE_DIR = Path(os.environ.get("V7_WORK_DIR", "/tmp/v7_work"))
TEX_DIR = BASE_DIR / "textures"
ASSET_DIR = BASE_DIR / "assets"
OUT_DIR = BASE_DIR / "out_step5b"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def enable_cycles_gpu(sc):
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type != "CPU"]
            if gpus:
                for d in prefs.devices:
                    d.use = (d.type != "CPU")
                sc.cycles.device = "GPU"
                print(f"[GPU] Enabled Cycles {backend}: {[d.name for d in gpus]}")
                return backend
        except Exception as e:
            print(f"[GPU] Backend {backend} skipped: {e}")
    sc.cycles.device = "CPU"
    return "CPU"


def angular_basalt_noise(x: float, y: float, z: float, seed: float = 0.0) -> float:
    s_raw = math.sin(z * 0.14 + 0.30 * math.sin(x * 0.035 + y * 0.03 + seed))
    strata = math.copysign(abs(s_raw) ** 0.50, s_raw)
    col = 1.0 - 2.0 * abs(math.sin(x * 0.065 - y * 0.05 + seed) * math.cos(y * 0.06 + x * 0.045))
    crag = 1.0 - 2.0 * abs(math.sin(x * 0.19 + y * 0.16 - z * 0.18 + seed * 1.9))
    return strata * 0.42 + col * 0.36 + crag * 0.22


def load_img(name: str, colorspace: str = "sRGB"):
    img = bpy.data.images.load(str(TEX_DIR / name), check_existing=True)
    img.colorspace_settings.name = colorspace
    return img


def resample_polyline(pts, n_out: int):
    res = []
    n_seg = len(pts) - 1
    for i in range(n_out):
        u = i / (n_out - 1) * n_seg
        idx = min(int(math.floor(u)), n_seg - 1)
        f = u - idx
        res.append((pts[idx][0] * (1.0 - f) + pts[idx + 1][0] * f,
                    pts[idx][1] * (1.0 - f) + pts[idx + 1][1] * f))
    return res


def shore_z(x: float, y: float) -> float:
    y_shore = -24.0 + 0.0045 * (x * x) + 4.0 * math.sin(x * 0.068 + 0.3)
    d = y_shore - y
    if d <= -5.0:
        return -8.0
    t = max(0.0, min(1.0, (d + 5.0) / 30.0))
    st = t * t * (3.0 - 2.0 * t)
    z = -2.4 + st * 9.0
    if z > 0.2:
        step = math.floor(z / 0.85)
        frac = (z / 0.85) - step
        z = z * 0.45 + (step + (frac ** 2.6)) * 0.85 * 0.55
    z += 0.52 * angular_basalt_noise(x * 1.8, y * 1.8, z, 9.1)
    if abs(x + 6.0) < 34.0 and -68.0 < y < -24.0:
        z = min(z, 2.35 + 0.065 * max(0.0, -34.0 - y)) + 0.24 * angular_basalt_noise(x * 2.2, y * 2.2, 0.0, 9.1)
    return z


def make_cavern_mat(name: str, albedo_mul: float, moss_strength: float = 0.0):
    """Anti-tiling basalt shader: 24m box-projected strata + large-scale macro noise breakup!"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    tc = nt.nodes.new("ShaderNodeTexCoord")

    # Domain-warp UV slightly with low-frequency 3D noise to eliminate ANY repeating tile rhythm!
    warp_n = nt.nodes.new("ShaderNodeTexNoise")
    warp_n.inputs["Scale"].default_value = 0.015
    warp_n.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], warp_n.inputs["Vector"])

    warp_mix = nt.nodes.new("ShaderNodeMix")
    warp_mix.data_type = "VECTOR"
    warp_mix.inputs["Factor"].default_value = 0.14
    nt.links.new(tc.outputs["Object"], warp_mix.inputs["A"])
    nt.links.new(warp_n.outputs["Color"], warp_mix.inputs["B"])

    mp = nt.nodes.new("ShaderNodeMapping")
    sc_val = 1.0 / CONFIG["cliff_tile_m"]
    mp.inputs["Scale"].default_value = (sc_val, sc_val, sc_val * 0.75)
    nt.links.new(warp_mix.outputs["Result"], mp.inputs["Vector"])

    t_alb = nt.nodes.new("ShaderNodeTexImage")
    t_alb.image = load_img("anime_cliff_albedo.jpg", "sRGB")
    t_alb.projection = "BOX"
    t_alb.projection_blend = 0.35
    nt.links.new(mp.outputs["Vector"], t_alb.inputs["Vector"])

    # Macro tonal variation across 80-150m cliffs (darkens crevices, varies indigo rock faces)
    macro_n = nt.nodes.new("ShaderNodeTexNoise")
    macro_n.inputs["Scale"].default_value = 0.018
    macro_n.inputs["Detail"].default_value = 4.0
    nt.links.new(tc.outputs["Object"], macro_n.inputs["Vector"])
    macro_rng = nt.nodes.new("ShaderNodeMapRange")
    macro_rng.inputs["From Min"].default_value = 0.25
    macro_rng.inputs["From Max"].default_value = 0.78
    macro_rng.inputs["To Min"].default_value = 0.45
    macro_rng.inputs["To Max"].default_value = 1.25
    macro_rng.clamp = True
    nt.links.new(macro_n.outputs["Fac"], macro_rng.inputs["Value"])

    mul_col = nt.nodes.new("ShaderNodeMix")
    mul_col.data_type = "RGBA"
    mul_col.blend_type = "MULTIPLY"
    mul_col.inputs["Factor"].default_value = 1.0
    mul_col.inputs["B"].default_value = (albedo_mul * 0.70, albedo_mul * 0.88, albedo_mul * 1.28, 1.0)
    nt.links.new(t_alb.outputs["Color"], mul_col.inputs["A"])

    mul_mac = nt.nodes.new("ShaderNodeMix")
    mul_mac.data_type = "RGBA"
    mul_mac.blend_type = "MULTIPLY"
    mul_mac.inputs["Factor"].default_value = 1.0
    nt.links.new(mul_col.outputs["Result"], mul_mac.inputs["A"])
    nt.links.new(macro_rng.outputs["Result"], mul_mac.inputs["B"])

    if moss_strength > 0.0:
        geom = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geom.outputs["Normal"], sep.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.58
        ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
        ramp.color_ramp.elements[1].position = 0.88
        ramp.color_ramp.elements[1].color = (moss_strength, moss_strength, moss_strength, 1)
        nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
        mix_m = nt.nodes.new("ShaderNodeMix")
        mix_m.data_type = "RGBA"
        mix_m.inputs["B"].default_value = (0.015, 0.055, 0.038, 1.0)
        nt.links.new(ramp.outputs["Color"], mix_m.inputs["Factor"])
        nt.links.new(mul_mac.outputs["Result"], mix_m.inputs["A"])
        nt.links.new(mix_m.outputs["Result"], bsdf.inputs["Base Color"])
    else:
        nt.links.new(mul_mac.outputs["Result"], bsdf.inputs["Base Color"])

    t_nrm = nt.nodes.new("ShaderNodeTexImage")
    t_nrm.image = load_img("anime_cliff_normal.png", "Non-Color")
    t_nrm.projection = "BOX"
    t_nrm.projection_blend = 0.35
    nt.links.new(mp.outputs["Vector"], t_nrm.inputs["Vector"])
    nrm_node = nt.nodes.new("ShaderNodeNormalMap")
    nrm_node.inputs["Strength"].default_value = 0.58
    nt.links.new(t_nrm.outputs["Color"], nrm_node.inputs["Color"])
    nt.links.new(nrm_node.outputs["Normal"], bsdf.inputs["Normal"])

    bsdf.inputs["Roughness"].default_value = 0.74
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.32
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_water_mat():
    mat = bpy.data.materials.new("Mat_V7_MirrorLake")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.010, 0.028, 0.056, 1.0)
    bsdf.inputs["Roughness"].default_value = CONFIG["water_roughness"]
    bsdf.inputs["IOR"].default_value = 1.333
    bsdf.inputs["Transmission Weight"].default_value = CONFIG["water_deep_absorb"]

    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 0.10
    n1.inputs["Detail"].default_value = 4.0
    n1.inputs["Roughness"].default_value = 0.50
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.045  # Ultra-calm glassy mirror symmetry for Cut 6B & 7B!
    bump.inputs["Distance"].default_value = 0.10
    nt.links.new(n1.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_whale_body_mat():
    """Sculpted Pearl-Opal Thin-Film Iridescence (Ice-Cyan -> Alabaster -> Sakura-Pink -> Champagne-Gold)."""
    mat = bpy.data.materials.new("Mat_V7_WhaleOpal")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    tc = nt.nodes.new("ShaderNodeTexCoord")
    t_alb = nt.nodes.new("ShaderNodeTexImage")
    t_alb.image = load_img("whale_skin_albedo.jpg", "sRGB")
    nt.links.new(tc.outputs["UV"], t_alb.inputs["Vector"])

    base_mul = nt.nodes.new("ShaderNodeMix")
    base_mul.data_type = "RGBA"
    base_mul.blend_type = "MULTIPLY"
    base_mul.inputs["Factor"].default_value = 1.0
    m = CONFIG["whale_unlit_albedo_mul"]
    base_mul.inputs["B"].default_value = (m * 0.42, m * 0.62, m * 0.95, 1.0)
    nt.links.new(t_alb.outputs["Color"], base_mul.inputs["A"])
    nt.links.new(base_mul.outputs["Result"], bsdf.inputs["Base Color"])

    bsdf.inputs["Roughness"].default_value = 0.22
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.72
        bsdf.inputs["Coat Roughness"].default_value = 0.07
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.24
        bsdf.inputs["Subsurface Scale"].default_value = 0.18

    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.46

    noise_w = nt.nodes.new("ShaderNodeTexNoise")
    noise_w.inputs["Scale"].default_value = 0.24
    noise_w.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], noise_w.inputs["Vector"])

    mix_irid = nt.nodes.new("ShaderNodeMath")
    mix_irid.operation = "MULTIPLY_ADD"
    mix_irid.inputs[1].default_value = 0.36
    nt.links.new(noise_w.outputs["Fac"], mix_irid.inputs[0])
    nt.links.new(lw.outputs["Facing"], mix_irid.inputs[2])

    ramp_p1 = nt.nodes.new("ShaderNodeValToRGB")
    ramp_p1.color_ramp.elements[0].position = 0.05
    ramp_p1.color_ramp.elements[0].color = (0.08, 0.56, 1.00, 1.0)   # Electric ice-cyan
    e1 = ramp_p1.color_ramp.elements.new(0.46)
    e1.color = (0.64, 0.88, 1.00, 1.0)                               # Moon-silver pearl
    ramp_p1.color_ramp.elements[1].position = 0.86
    ramp_p1.color_ramp.elements[1].color = (0.62, 0.28, 1.00, 1.0)   # Rich lavender-violet
    nt.links.new(mix_irid.outputs["Value"], ramp_p1.inputs["Fac"])

    ramp_p3 = nt.nodes.new("ShaderNodeValToRGB")
    ramp_p3.color_ramp.elements[0].position = 0.06
    ramp_p3.color_ramp.elements[0].color = (0.16, 0.72, 1.00, 1.0)   # Deep aqua-cyan shadow
    e2 = ramp_p3.color_ramp.elements.new(0.38)
    e2.color = (0.94, 0.90, 1.00, 1.0)                               # Pearl-alabaster core
    e3 = ramp_p3.color_ramp.elements.new(0.64)
    e3.color = (1.00, 0.44, 0.78, 1.0)                               # Vivid sakura-pink opalescence!
    ramp_p3.color_ramp.elements[1].position = 0.88
    ramp_p3.color_ramp.elements[1].color = (1.00, 0.78, 0.32, 1.0)   # Warm champagne-gold rim!
    nt.links.new(mix_irid.outputs["Value"], ramp_p3.inputs["Fac"])

    phase_mix = nt.nodes.new("ShaderNodeMix")
    phase_mix.name = "WhalePhaseColorMix"
    phase_mix.data_type = "RGBA"
    phase_mix.inputs["Factor"].default_value = 0.0
    nt.links.new(ramp_p1.outputs["Color"], phase_mix.inputs["A"])
    nt.links.new(ramp_p3.outputs["Color"], phase_mix.inputs["B"])
    nt.links.new(phase_mix.outputs["Result"], bsdf.inputs["Emission Color"])

    sep_o = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep_o.inputs["Vector"])
    wave_add = nt.nodes.new("ShaderNodeMath")
    wave_add.operation = "MULTIPLY_ADD"
    wave_add.inputs[1].default_value = 3.2
    nt.links.new(noise_w.outputs["Fac"], wave_add.inputs[0])
    nt.links.new(sep_o.outputs["X"], wave_add.inputs[2])

    wave_rng = nt.nodes.new("ShaderNodeMapRange")
    wave_rng.name = "WhaleIgniteWave"
    wave_rng.inputs["From Min"].default_value = -2.0
    wave_rng.inputs["From Max"].default_value = 5.0
    wave_rng.clamp = True
    nt.links.new(wave_add.outputs["Value"], wave_rng.inputs["Value"])

    contour_mul = nt.nodes.new("ShaderNodeMapRange")
    contour_mul.inputs["From Min"].default_value = 0.0
    contour_mul.inputs["From Max"].default_value = 1.0
    contour_mul.inputs["To Min"].default_value = 0.18   # Sculpted iridescent interior
    contour_mul.inputs["To Max"].default_value = 1.55   # Luminous opalescent rim!
    nt.links.new(lw.outputs["Facing"], contour_mul.inputs["Value"])

    emit_w = nt.nodes.new("ShaderNodeMath")
    emit_w.operation = "MULTIPLY"
    nt.links.new(wave_rng.outputs["Result"], emit_w.inputs[0])
    nt.links.new(contour_mul.outputs["Result"], emit_w.inputs[1])

    emit_str = nt.nodes.new("ShaderNodeMath")
    emit_str.name = "WhaleEmitStrength"
    emit_str.operation = "MULTIPLY"
    emit_str.inputs[1].default_value = 0.0
    nt.links.new(emit_w.outputs["Value"], emit_str.inputs[0])
    nt.links.new(emit_str.outputs["Value"], bsdf.inputs["Emission Strength"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_whale_eye_mat():
    mat = bpy.data.materials.new("Mat_V7_WhaleEye")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.002, 0.006, 0.015, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.02
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat Roughness"].default_value = 0.01
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_flower_mats():
    m_open = bpy.data.materials.new("Mat_FL01_OpenPetal")
    m_open.use_nodes = True
    nt = m_open.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    t_p = nt.nodes.new("ShaderNodeTexImage")
    t_p.image = load_img("petal_rgba.png", "sRGB")
    nt.links.new(t_p.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(t_p.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.42
    nt.links.new(t_p.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = CONFIG["flower_open_emit"]
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    m_seed = bpy.data.materials.new("Mat_FL01_GoldSeed")
    m_seed.use_nodes = True
    nt = m_seed.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (1.0, 0.80, 0.36, 1.0)
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.82, 0.38, 1.0)
    bsdf.inputs["Emission Strength"].default_value = CONFIG["flower_seed_emit"]
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    m_bud = bpy.data.materials.new("Mat_FL01_ClosedBud")
    m_bud.use_nodes = True
    nt = m_bud.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.045, 0.048, 0.042, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.90
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    m_pet = bpy.data.materials.new("Mat_FL01_FlyingPetal")
    m_pet.use_nodes = True
    nt = m_pet.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    t_p2 = nt.nodes.new("ShaderNodeTexImage")
    t_p2.image = load_img("petal_rgba.png", "sRGB")
    nt.links.new(t_p2.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(t_p2.outputs["Alpha"], bsdf.inputs["Alpha"])
    mix_e = nt.nodes.new("ShaderNodeMix")
    mix_e.data_type = "RGBA"
    mix_e.blend_type = "MULTIPLY"
    mix_e.inputs["Factor"].default_value = 1.0
    mix_e.inputs["B"].default_value = (1.0, 0.90, 0.62, 1.0)
    nt.links.new(t_p2.outputs["Color"], mix_e.inputs["A"])
    nt.links.new(mix_e.outputs["Result"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = CONFIG["petal_emit"]
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m_open, m_seed, m_bud, m_pet


def build_natural_cliff_ridge(name, pts_xy, z_base, z_top, seed, mat_rock, taper_top=False):
    pts = resample_polyline(pts_xy, 36)
    bm = bmesh.new()
    n_seg, n_z = len(pts), 26
    grid = []
    for k in range(n_z):
        tz = k / (n_z - 1)
        row = []
        for m in range(n_seg):
            tm = m / (n_seg - 1)
            x0, y0 = pts[m]
            h_env = (0.35 + 0.65 * math.sin(tm * math.pi) ** 0.6) if taper_top else 1.0
            z = z_base + (z_top - z_base) * h_env * tz
            crag = 6.2 * angular_basalt_noise(x0, y0, z, seed)
            to_c = Vector((0.0 - x0, 60.0 - y0)).normalized()
            slope_back = -18.0 * (tz ** 1.35) if taper_top else -6.0 * (tz ** 1.4)
            row.append(bm.verts.new((x0 + to_c.x * (crag + slope_back), y0 + to_c.y * (crag + slope_back), z)))
        grid.append(row)
    for k in range(n_z - 1):
        for m in range(n_seg - 1):
            bm.faces.new((grid[k][m], grid[k][m+1], grid[k+1][m+1], grid[k+1][m]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat_rock)
    bpy.context.collection.objects.link(ob)
    return ob


def build_cavern_geometry(mat_rock, mat_shore):
    fx_c, fy0, fy1, f_hw, z_max = 4.0, 24.0, 242.0, 32.0, 185.0
    bm = bmesh.new()
    nu, nv = 128, 64
    cx, cy, rx, ry = 0.0, 170.0, 225.0, 310.0
    sgrid = []
    for j in range(nv):
        phi = -0.06 + (math.pi * 0.495 + 0.06) * (j / (nv - 1))
        cp, sp = max(0.0, math.cos(phi)), math.sin(phi)
        row = []
        for i in range(nu):
            theta = 2.0 * math.pi * i / nu
            px = cx + rx * cp * math.cos(theta)
            py = cy + ry * cp * math.sin(theta)
            north_lift = 0.62 + 0.38 * max(0.0, min(1.0, (py + 90.0) / 260.0))
            pz = -12.0 + (z_max * north_lift) * (max(0.0, sp) ** 0.72 if sp >= 0 else sp * 0.4)
            disp = 12.0 * angular_basalt_noise(px, py, pz, 3.1) * (0.35 + 0.65 * cp)
            row.append(bm.verts.new((px - math.cos(theta) * cp * disp, py - math.sin(theta) * cp * disp, pz + sp * disp * 0.38)))
        sgrid.append(row)
    for j in range(nv - 1):
        for i in range(nu):
            inext = (i + 1) % nu
            v0, v1, v2, v3 = sgrid[j][i], sgrid[j][inext], sgrid[j+1][inext], sgrid[j+1][i]
            fc = (v0.co + v1.co + v2.co + v3.co) * 0.25
            if fc.z > 62.0 and fy0 <= fc.y <= fy1:
                t_y = (fc.y - fy0) / max(1.0, (fy1 - fy0))
                env_w = (0.45 + 0.85 * (t_y ** 0.55)) * math.sin(min(1.0, t_y * 1.05) * math.pi) ** 0.30
                jagged = 1.0 + 0.20 * math.sin(fc.y * 0.11 + 0.4) + 0.10 * math.cos(fc.y * 0.23 - 0.7)
                if abs(fc.x - fx_c) < (f_hw * env_w * jagged):
                    continue
            bm.faces.new((v0, v3, v2, v1))
    me = bpy.data.meshes.new("V7_EnclosedCavernVault")
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(me.name, me)
    ob.data.materials.append(mat_rock)
    bpy.context.collection.objects.link(ob)

    for side in (-1.0, 1.0):
        bm = bmesh.new()
        ny_r, nz_r = 34, 14
        grid = []
        for k in range(nz_r):
            tz = k / (nz_r - 1)
            row = []
            for m in range(ny_r):
                ty = m / (ny_r - 1)
                py = fy0 + (fy1 - fy0) * ty
                env_w = (0.45 + 0.85 * (ty ** 0.55)) * math.sin(min(1.0, ty * 1.05) * math.pi) ** 0.30
                jagged = 1.0 + 0.20 * math.sin(py * 0.11 + 0.4) + 0.10 * math.cos(py * 0.23 - 0.7)
                px = fx_c + side * (f_hw * env_w * jagged + 16.0 * (tz ** 1.15))
                pz = (88.0 + 78.0 * ty) - 10.0 + tz * 58.0
                crag = 4.5 * angular_basalt_noise(px, py, pz, side * 7.3)
                row.append(bm.verts.new((px + side * crag * 0.4, py, pz + crag * 0.3)))
            grid.append(row)
        for k in range(nz_r - 1):
            for m in range(ny_r - 1):
                if side > 0:
                    bm.faces.new((grid[k][m], grid[k][m+1], grid[k+1][m+1], grid[k+1][m]))
                else:
                    bm.faces.new((grid[k][m], grid[k+1][m], grid[k+1][m+1], grid[k][m+1]))
        me2 = bpy.data.meshes.new(f"CanyonRimGorge_{'R' if side > 0 else 'L'}")
        bm.to_mesh(me2)
        bm.free()
        me2.polygons.foreach_set("use_smooth", [True] * len(me2.polygons))
        ob2 = bpy.data.objects.new(me2.name, me2)
        ob2.data.materials.append(mat_rock)
        bpy.context.collection.objects.link(ob2)

    build_natural_cliff_ridge("Cliff_L_Near", [(-82, -55), (-98, -15), (-125, 25), (-155, 65)], -6.0, 155.0, 11.2, mat_rock)
    build_natural_cliff_ridge("Cliff_L_Mid",  [(-102, 85), (-120, 135), (-142, 185)], -6.0, 165.0, 23.4, mat_rock)
    build_natural_cliff_ridge("Cliff_L_Far",  [(-130, 225), (-78, 285), (-15, 330)], -6.0, 175.0, 35.6, mat_rock)
    build_natural_cliff_ridge("Cliff_R_Near", [(148, 50), (118, 12), (96, -22), (82, -55)], -6.0, 155.0, 47.8, mat_rock)
    build_natural_cliff_ridge("Canon_R1_ExitHeadland", [(158, 72), (110, 56), (66, 56), (62, 82), (84, 124)], -6.0, 94.0, 59.1, mat_rock, taper_top=True)
    build_natural_cliff_ridge("Cliff_R_Far",  [(22, 330), (88, 282), (145, 212)], -6.0, 175.0, 71.3, mat_rock)

    bm = bmesh.new()
    nx, ny = 96, 64
    xs = [-110.0 + 220.0 * i / (nx - 1) for i in range(nx)]
    ys = [-82.0 + 92.0 * j / (ny - 1) for j in range(ny)]
    grid = [[bm.verts.new((x, y, shore_z(x, y))) for x in xs] for y in ys]
    for j in range(ny - 1):
        for i in range(nx - 1):
            bm.faces.new((grid[j][i], grid[j][i+1], grid[j+1][i+1], grid[j+1][i]))
    me_s = bpy.data.meshes.new("V7_ShoreTerrace_S1")
    bm.to_mesh(me_s)
    bm.free()
    me_s.polygons.foreach_set("use_smooth", [True] * len(me_s.polygons))
    ob_s = bpy.data.objects.new(me_s.name, me_s)
    ob_s.data.materials.append(mat_shore)
    bpy.context.collection.objects.link(ob_s)


def build_flower_carpet(m_open, m_seed, m_bud):
    def load_glb_meshes(fn):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(ASSET_DIR / fn))
        added = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        out = {}
        for o in added:
            out[o.name] = o.data.copy()
            bpy.data.objects.remove(o, do_unlink=True)
        return out

    open_parts = load_glb_meshes("fl01_open.glb")
    bud_parts  = load_glb_meshes("fl01_bud.glb")

    def merge_mesh_list(part_dict, transforms, mat_map):
        bms = {m: bmesh.new() for m in set(mat_map.values())}
        for pname, me_src in part_dict.items():
            mat = None
            for k, v in mat_map.items():
                if k in pname:
                    mat = v
                    break
            if mat is None:
                continue
            bm_dst = bms[mat]
            uv_dst = bm_dst.loops.layers.uv.verify()
            uv_src = me_src.uv_layers.active
            for xf in transforms:
                vmap = {v.index: bm_dst.verts.new(xf @ v.co) for v in me_src.vertices}
                for poly in me_src.polygons:
                    try:
                        f = bm_dst.faces.new([vmap[vi] for vi in poly.vertices])
                        f.smooth = True
                        if uv_src:
                            for loop, li in zip(f.loops, poly.loop_indices):
                                loop[uv_dst].uv = uv_src.data[li].uv
                    except ValueError:
                        pass
        objs = []
        for idx, (mat, bm_dst) in enumerate(bms.items()):
            me = bpy.data.meshes.new(f"Carpet_{mat.name}_{idx}")
            bm_dst.to_mesh(me)
            bm_dst.free()
            ob = bpy.data.objects.new(me.name, me)
            ob.data.materials.append(mat)
            bpy.context.collection.objects.link(ob)
            objs.append(ob)
        return objs

    rng = random.Random(2028)
    xf_p0, xf_all = [], []
    for _ in range(CONFIG["n_shore_flowers"]):
        fx = rng.uniform(-58.0, 52.0)
        fy = rng.uniform(-58.0, -23.0)
        fz = shore_z(fx, fy)
        if fz < 0.12 or fz > 4.2:
            continue
        sc = rng.uniform(0.32, 0.64)
        xf = Matrix.Translation((fx, fy, fz - 0.02)) @ Euler((rng.uniform(-0.18, 0.18), rng.uniform(-0.18, 0.18), rng.uniform(0, 6.28)), "XYZ").to_matrix().to_4x4() @ Matrix.Scale(sc, 4)
        if math.hypot((fx - 2.0) * 0.85, (fy + 34.0) * 1.1) < 5.5:
            xf_p0.append(xf)
        else:
            xf_all.append(xf)

    # Extra lush near-water flowers right in front of Cut 6B ground-skimming lens (-6..-2, -32..-24)!
    for _ in range(280):
        fx = rng.uniform(-14.0, 8.0)
        fy = rng.uniform(-38.0, -24.0)
        fz = shore_z(fx, fy)
        if 0.08 < fz < 2.2:
            sc = rng.uniform(0.32, 0.58)
            xf_all.append(Matrix.Translation((fx, fy, fz - 0.02)) @ Euler((rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15), rng.uniform(0, 6.28)), "XYZ").to_matrix().to_4x4() @ Matrix.Scale(sc, 4))

    open_map = {"Petals": m_open, "Seed": m_seed, "Stem": m_bud}
    bud_map  = {"Petals": m_bud,  "Seed": m_bud,  "Stem": m_bud}
    return {
        "p0_open":  merge_mesh_list(open_parts, xf_p0, open_map),
        "all_bud":  merge_mesh_list(bud_parts,  xf_all, bud_map),
        "all_open": merge_mesh_list(open_parts, xf_all, open_map),
    }


def build_blizzard_petals(m_pet):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ASSET_DIR / "sakura_petal_3d.glb"))
    src_ob = next(o for o in bpy.data.objects if o not in before and o.type == "MESH")
    me_src = src_ob.data.copy()
    bpy.data.objects.remove(src_ob, do_unlink=True)

    rng = random.Random(9009)
    bm = bmesh.new()
    uv_dst = bm.loops.layers.uv.verify()
    uv_src = me_src.uv_layers.active
    for i in range(CONFIG["n_blizzard_petals"]):
        t = rng.random()
        if i < 550:
            # Near-camera parallax petals for Cut 7A airborne tracking & Cut 6B lift-off!
            px = rng.uniform(-36.0, 32.0)
            py = rng.uniform(-42.0, 28.0)
            pz = rng.uniform(0.5, 42.0)
            sc = rng.uniform(0.32, 0.72)
        else:
            ang = t * 12.0 + (i % 3) * 2.094 + rng.uniform(-0.4, 0.4)
            rad = 8.0 + 60.0 * (t ** 0.72) + rng.uniform(-8.0, 8.0)
            px = math.cos(ang) * rad
            py = -24.0 + t * 105.0 + math.sin(ang) * 20.0
            pz = 1.5 + t * 78.0 + rng.uniform(-5.0, 5.0)
            sc = rng.uniform(0.55, 1.35)
        xf = Matrix.Translation((px, py, pz)) @ Euler((rng.uniform(0, 6.28), rng.uniform(0, 6.28), rng.uniform(0, 6.28)), "XYZ").to_matrix().to_4x4() @ Matrix.Scale(sc, 4)
        vmap = {v.index: bm.verts.new(xf @ v.co) for v in me_src.vertices}
        for poly in me_src.polygons:
            try:
                f = bm.faces.new([vmap[vi] for vi in poly.vertices])
                f.smooth = True
                if uv_src:
                    for loop, li in zip(f.loops, poly.loop_indices):
                        loop[uv_dst].uv = uv_src.data[li].uv
            except ValueError:
                pass
    me = bpy.data.meshes.new("V7_PetalBlizzard")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    ob.data.materials.append(m_pet)
    bpy.context.collection.objects.link(ob)
    return ob


def setup_compositor(sc):
    if hasattr(sc, "compositing_node_group"):
        ng = bpy.data.node_groups.new("V7_CinemaComp", "CompositorNodeTree")
        sc.compositing_node_group = ng
        nt = ng
        out_n = nt.nodes.new("NodeGroupOutput")
        ng.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    else:
        sc.use_nodes = True
        nt = sc.node_tree
        nt.nodes.clear()
        out_n = nt.nodes.new("CompositorNodeComposite")

    rl = nt.nodes.new("CompositorNodeRLayers")
    glare = nt.nodes.new("CompositorNodeGlare")
    set_ok = False
    if "Type" in glare.inputs:
        for val in ("Fog Glow", "FOG_GLOW", "Bloom", "BLOOM"):
            try:
                glare.inputs["Type"].default_value = val
                set_ok = True
                break
            except Exception:
                pass
    if not set_ok and hasattr(glare, "glare_type"):
        for val in ("FOG_GLOW", "BLOOM", "Fog Glow", "Bloom"):
            try:
                glare.glare_type = val
                set_ok = True
                break
            except Exception:
                pass
    if not set_ok:
        nt.links.new(rl.outputs["Image"], out_n.inputs["Image"])
        return

    if "Threshold" in glare.inputs:
        glare.inputs["Threshold"].default_value = CONFIG["glare_threshold"]
    elif hasattr(glare, "threshold"):
        glare.threshold = CONFIG["glare_threshold"]
    if "Mix" in glare.inputs:
        glare.inputs["Mix"].default_value = CONFIG["glare_mix"]
    elif hasattr(glare, "mix"):
        glare.mix = CONFIG["glare_mix"]
    if "Size" in glare.inputs:
        glare.inputs["Size"].default_value = 7
    elif hasattr(glare, "size"):
        glare.size = 7
    nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
    nt.links.new(glare.outputs["Image"], out_n.inputs["Image"])


def set_vis(objs, vis: bool):
    for o in objs:
        o.hide_render = not vis
        o.hide_viewport = not vis


def main():
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    enable_cycles_gpu(sc)

    sc.cycles.samples = CONFIG["samples"]
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.025
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 4
    sc.cycles.transparent_max_bounces = 6
    sc.cycles.volume_bounces = 1
    sc.cycles.sample_clamp_indirect = 8.0
    sc.render.use_persistent_data = False

    sc.render.resolution_x, sc.render.resolution_y = CONFIG["render_res"]
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"

    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Punchy"
    except Exception:
        pass
    sc.view_settings.exposure = CONFIG["exposure_locked"]

    world = bpy.data.worlds.new("V7_MidnightWorld")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.025, 0.055, 0.135, 1.0)
    bg.inputs["Strength"].default_value = 1.4

    mat_rock  = make_cavern_mat("Mat_V7_CavernRock", CONFIG["cliff_albedo_mul"], moss_strength=0.18)
    mat_shore = make_cavern_mat("Mat_V7_ShoreRock",  CONFIG["shore_albedo_mul"], moss_strength=0.65)
    mat_water = make_water_mat()
    mat_whale = make_whale_body_mat()
    mat_eye   = make_whale_eye_mat()
    m_open, m_seed, m_bud, m_pet = make_flower_mats()

    build_cavern_geometry(mat_rock, mat_shore)

    bpy.ops.mesh.primitive_plane_add(size=750.0, location=(0.0, 180.0, 0.0))
    lake = bpy.context.active_object
    lake.name = "V7_MirrorLake"
    lake.data.materials.append(mat_water)

    moon_pos = Vector((4.0, 228.0, 234.0))
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=moon_pos)
    moon_card = bpy.context.active_object
    moon_card.scale = (290.0, 175.0, 1.0)
    moon_card.rotation_euler = (Vector((-10.0, -62.0, 5.2)) - moon_pos).to_track_quat("Z", "Y").to_euler()
    m_moon = bpy.data.materials.new("Mat_V7_MoonSky")
    m_moon.use_nodes = True
    nt = m_moon.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    ti = nt.nodes.new("ShaderNodeTexImage")
    ti.image = load_img("moon_sky.jpg", "sRGB")
    em.inputs["Strength"].default_value = CONFIG["moon_emission"]
    nt.links.new(ti.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    moon_card.data.materials.append(m_moon)

    beam_start = Vector((4.0, 138.0, 158.0))
    beam_end   = Vector((2.0, -34.0, 0.0))
    beam_dir   = beam_end - beam_start
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=58.0, depth=beam_dir.length,
                                        location=(beam_start + beam_end) * 0.5)
    beam_ob = bpy.context.active_object
    beam_ob.rotation_euler = beam_dir.normalized().to_track_quat("-Z", "Y").to_euler()
    m_vol = bpy.data.materials.new("Mat_V7_MoonbeamVol")
    m_vol.use_nodes = True
    nt = m_vol.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pv = nt.nodes.new("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = (0.62, 0.84, 1.0, 1.0)
    pv.inputs["Anisotropy"].default_value = 0.62
    tc_v = nt.nodes.new("ShaderNodeTexCoord")
    sep_v = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc_v.outputs["Object"], sep_v.inputs["Vector"])
    x2 = nt.nodes.new("ShaderNodeMath"); x2.operation = "MULTIPLY"
    nt.links.new(sep_v.outputs["X"], x2.inputs[0]); nt.links.new(sep_v.outputs["X"], x2.inputs[1])
    y2 = nt.nodes.new("ShaderNodeMath"); y2.operation = "MULTIPLY"
    nt.links.new(sep_v.outputs["Y"], y2.inputs[0]); nt.links.new(sep_v.outputs["Y"], y2.inputs[1])
    r2 = nt.nodes.new("ShaderNodeMath"); r2.operation = "ADD"
    nt.links.new(x2.outputs["Value"], r2.inputs[0]); nt.links.new(y2.outputs["Value"], r2.inputs[1])
    rmap = nt.nodes.new("ShaderNodeMapRange")
    rmap.interpolation_type = "SMOOTHSTEP"
    rmap.inputs["From Min"].default_value = 180.0
    rmap.inputs["From Max"].default_value = 2800.0
    rmap.inputs["To Min"].default_value = CONFIG["beam_volume_density"]
    rmap.inputs["To Max"].default_value = 0.0
    rmap.clamp = True
    nt.links.new(r2.outputs["Value"], rmap.inputs["Value"])
    nt.links.new(rmap.outputs["Result"], pv.inputs["Density"])
    nt.links.new(pv.outputs["Volume"], out.inputs["Volume"])
    beam_ob.data.materials.append(m_vol)

    bpy.ops.import_scene.gltf(filepath=str(ASSET_DIR / "wh01_v20_hero.glb"))
    whale = next(o for o in bpy.data.objects if o.type == "MESH" and "WH01" in o.name)
    whale.rotation_mode = "XYZ"
    for idx, slot in enumerate(whale.material_slots):
        if slot.material and "eye" in slot.material.name.lower():
            whale.material_slots[idx].material = mat_eye
        else:
            whale.material_slots[idx].material = mat_whale

    fl_groups = build_flower_carpet(m_open, m_seed, m_bud)
    blizzard_ob = build_blizzard_petals(m_pet)

    # Lights
    sun_d = bpy.data.lights.new("Key_MoonSun", type="SUN")
    sun_d.energy = CONFIG["moon_sun_energy_locked"]
    sun_d.color = (0.72, 0.86, 1.0)
    sun_d.angle = math.radians(2.5)
    sun_o = bpy.data.objects.new("Key_MoonSun", sun_d)
    bpy.context.collection.objects.link(sun_o)
    sun_o.rotation_euler = (moon_pos - beam_end).to_track_quat("Z", "Y").to_euler()

    spot_d = bpy.data.lights.new("Spot_MoonbeamP0", type="SPOT")
    spot_d.energy = CONFIG["moon_spot_energy_locked"]
    spot_d.color = (0.76, 0.90, 1.0)
    spot_d.spot_size = math.radians(36.0)
    spot_d.spot_blend = 0.65
    spot_d.shadow_soft_size = 8.0
    spot_o = bpy.data.objects.new("Spot_MoonbeamP0", spot_d)
    spot_o.location = beam_start
    spot_o.rotation_euler = (beam_end - beam_start).to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(spot_o)

    sky_d = bpy.data.lights.new("Fill_CanyonSkylight", type="AREA")
    sky_d.shape = "RECTANGLE"; sky_d.size = 130.0; sky_d.size_y = 220.0
    sky_d.energy = CONFIG["cavern_sky_bounce_energy"]; sky_d.color = (0.34, 0.56, 0.92)
    sky_o = bpy.data.objects.new("Fill_CanyonSkylight", sky_d)
    sky_o.location = (4.0, 95.0, 142.0); sky_o.rotation_euler = (math.radians(8.0), 0.0, 0.0)
    sky_o.visible_camera = False; sky_o.visible_glossy = False
    bpy.context.collection.objects.link(sky_o)

    lk_d = bpy.data.lights.new("Fill_LakeBounce", type="AREA")
    lk_d.shape = "RECTANGLE"; lk_d.size = 180.0; lk_d.size_y = 240.0
    lk_d.energy = CONFIG["cavern_lake_bounce_energy"]; lk_d.color = (0.28, 0.54, 0.88)
    lk_o = bpy.data.objects.new("Fill_LakeBounce", lk_d)
    lk_o.location = (0.0, 55.0, 1.8); lk_o.rotation_euler = (math.radians(180.0), 0.0, 0.0)
    lk_o.visible_camera = False; lk_o.visible_glossy = False
    bpy.context.collection.objects.link(lk_o)

    # Pinpoint silver moonlight eye catchlight for Cut 4 Heigei Close-Up!
    eye_d = bpy.data.lights.new("Light_EyeCatch", type="POINT")
    eye_d.energy = 0.0
    eye_d.color = (0.76, 0.90, 1.0)
    eye_d.shadow_soft_size = 0.45
    eye_o = bpy.data.objects.new("Light_EyeCatch", eye_d)
    bpy.context.collection.objects.link(eye_o)

    wlight_d = bpy.data.lights.new("Light_WhaleRadiance", type="POINT")
    wlight_d.energy = 0.0; wlight_d.color = (0.82, 0.92, 1.0); wlight_d.shadow_soft_size = 9.0
    wlight_o = bpy.data.objects.new("Light_WhaleRadiance", wlight_d)
    wlight_o.visible_camera = False
    wlight_o.visible_glossy = False
    bpy.context.collection.objects.link(wlight_o)

    cam_d = bpy.data.cameras.new("V7_MainCam")
    cam_d.sensor_width = 36.0; cam_d.clip_start = 0.25; cam_d.clip_end = 1200.0
    cam_o = bpy.data.objects.new("V7_MainCam", cam_d)
    bpy.context.collection.objects.link(cam_o)
    sc.camera = cam_o

    setup_compositor(sc)

    # 4 NEW DIRECTOR'S CUT HERO CAMERA PROOFS!
    # Note: WH-01 local +X is snout (+12m), -X is tail (-12m).
    c4_x, c4_y = -11.5, -45.0
    c4_z = max(4.2, shore_z(c4_x, c4_y) + 1.8)
    shots = [
        {
            "slug": "dc01_heigei_closeup_28s",
            "label": "Cut 4 (28.5s) 50mm Heigei Close-Up: Front-20deg Snout & Serene Eye Gaze",
            # Whale hovers right over the dark lake edge gazing down toward the adventurer on shore!
            "w_pos": Vector((1.5, -16.0, 9.2)),
            "w_rot": Euler((math.radians(5.0), math.radians(10.0), math.radians(-142.0)), "XYZ"),
            # Adventurer eye-level POV cleanly above shore_z framing the massive snout & serene left eye!
            "cam_pos": Vector((c4_x, c4_y, c4_z)),
            "cam_tgt": Vector((-3.5, -21.0, 8.6)),
            "focal": 42.0, "dof": True, "fstop": 3.5,
            "eye_catch": (Vector((-12.0, -30.0, 12.0)), 6500.0),
            "w_emit": 0.0, "w_phase": 0.0, "w_wave": (15.0, 20.0), "w_light": 0.0, "w_lcol": (0.7, 0.85, 1.0),
            "all_open": False, "blizzard": False,
        },
        {
            "slug": "dc02_ground_bloom_43s",
            "label": "Cut 6B (43.5s) Z=0.45m Ground-Skimming Bloom + Mirror-Lake Symmetry",
            # Whale ignited over the mirror lake, reflecting cleanly in the glassy water!
            "w_pos": Vector((2.0, 26.0, 16.5)),
            "w_rot": Euler((math.radians(-6.0), math.radians(-14.0), math.radians(22.0)), "XYZ"),
            # Camera drops to flower height (Z=0.45m) near shore edge looking across blooming white star-lilies & mirror lake!
            "cam_pos": Vector((-4.5, -31.0, shore_z(-4.5, -31.0) + 0.45)),
            "cam_tgt": Vector((1.5, 22.0, 8.5)),
            "focal": 24.0, "dof": True, "fstop": 3.5,
            "eye_catch": None,
            "w_emit": CONFIG["whale_ignite_emit"], "w_phase": 0.0, "w_wave": (-4.0, 3.0),
            "w_light": CONFIG["whale_light_power"] * 0.80, "w_lcol": (0.68, 0.84, 1.0),
            "all_open": True, "blizzard": True,
        },
        {
            "slug": "dc03_aerial_track_50s",
            "label": "Cut 7A (50.0s) Gravity Release: Airborne Whale Tracking + Golden Snow Parallax",
            # Whale banking gracefully mid-cavern in full sculpted Pearl-Opal/Sakura/Gold iridescence!
            "w_pos": Vector((4.0, 24.0, 32.0)),
            "w_rot": Euler((math.radians(-18.0), math.radians(-10.0), math.radians(32.0)), "XYZ"),
            # Camera lifts off the shore into mid-air (Z=27m!) flying right behind/beside the whale through swirling petals!
            "cam_pos": Vector((-17.5, -1.5, 27.0)),
            "cam_tgt": Vector((5.5, 28.0, 34.5)),
            "focal": 28.0, "dof": True, "fstop": 4.0,
            "eye_catch": None,
            "w_emit": CONFIG["whale_climax_emit"], "w_phase": 1.0, "w_wave": (-20.0, -14.0),
            "w_light": CONFIG["whale_light_power"], "w_lcol": (1.0, 0.88, 0.76),
            "all_open": True, "blizzard": True,
        },
        {
            "slug": "dc04_panorama_sym_59s",
            "label": "Cut 7B (59.0s) 18mm Grand Cavern Panorama + Mirror Symmetry + Anti-Tile Basalt",
            # Whale soaring gracefully under the vertical canyon moon, reflected in the obsidian mirror lake!
            "w_pos": Vector((-2.0, 30.0, 34.0)),
            "w_rot": Euler((math.radians(-14.0), math.radians(-12.0), math.radians(16.0)), "XYZ"),
            # Elevated floating pull-back revealing the 450m cavern, vertical canyon moon, mirror lake, & full flower shore!
            "cam_pos": Vector((-12.0, -64.0, 14.5)),
            "cam_tgt": Vector((2.0, 38.0, 22.0)),
            "focal": 18.0, "dof": False, "fstop": 8.0,
            "eye_catch": None,
            "w_emit": CONFIG["whale_climax_emit"], "w_phase": 1.0, "w_wave": (-20.0, -14.0),
            "w_light": CONFIG["whale_light_power"], "w_lcol": (1.0, 0.90, 0.78),
            "all_open": True, "blizzard": True,
        },
    ]

    w_emit_node  = mat_whale.node_tree.nodes["WhaleEmitStrength"]
    w_phase_node = mat_whale.node_tree.nodes["WhalePhaseColorMix"]
    w_wave_node  = mat_whale.node_tree.nodes["WhaleIgniteWave"]

    for sh in shots:
        cam_o.location = sh["cam_pos"]
        cam_o.data.lens = sh["focal"]
        cam_o.rotation_euler = (sh["cam_tgt"] - sh["cam_pos"]).to_track_quat("-Z", "Y").to_euler()
        cam_o.data.dof.use_dof = sh["dof"]
        if sh["dof"]:
            cam_o.data.dof.focus_distance = (sh["cam_tgt"] - sh["cam_pos"]).length
            cam_o.data.dof.aperture_fstop = sh["fstop"]

        whale.location = sh["w_pos"]
        whale.rotation_euler = sh["w_rot"]

        if sh["eye_catch"]:
            eye_o.location = sh["eye_catch"][0]
            eye_d.energy = sh["eye_catch"][1]
        else:
            eye_d.energy = 0.0

        w_emit_node.inputs[1].default_value = sh["w_emit"]
        w_phase_node.inputs["Factor"].default_value = sh["w_phase"]
        w_wave_node.inputs["From Min"].default_value = sh["w_wave"][0]
        w_wave_node.inputs["From Max"].default_value = sh["w_wave"][1]

        wlight_o.location = sh["w_pos"] + Vector((0.0, -2.0, -1.5))
        wlight_d.energy = sh["w_light"]
        wlight_d.color = sh["w_lcol"]

        set_vis(fl_groups["p0_open"], True)
        set_vis(fl_groups["all_open"], sh["all_open"])
        set_vis(fl_groups["all_bud"],  not sh["all_open"])
        blizzard_ob.hide_render = not sh["blizzard"]

        out_png = OUT_DIR / f"{sh['slug']}.png"
        sc.render.filepath = str(out_png)
        ts = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[STEP 5B GPU] {sh['slug']} rendered in {time.time() - ts:.1f}s -> {out_png}")

    print(f"[STEP 5B DONE] All 4 Director's Cut Proof Stills finished in {time.time() - t0:.1f}s!")


if __name__ == "__main__":
    main()
