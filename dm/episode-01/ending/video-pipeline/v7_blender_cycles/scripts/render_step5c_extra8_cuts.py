#!/usr/bin/env python3
"""
V7 Step 5C: 8 Additional 960x540 Cycles GPU Lookdev Stills to complete the full 16-Cut 90s Storyboard!
  1. ex01_02s_open_cam_a      — Cut 1 (02.0s): Locked Cam A Opening Stillness (P0 only lit, rest buds)
  2. ex02_08s_p0_flower_macro — Cut 1B (08.0s): 65mm Macro of delicate 4.5cm 5-petal P0 white star-lilies + gold seeds
  3. ex03_21s_silent_breach   — Cut 3A (21.0s): Silent unlit leviathan breaking the obsidian mirror lake surface
  4. ex04_30s_eye_hold_macro  — Cut 4B (30.5s): 65mm Serene Eye Hold (pinpoint moonlight glint in calm dark eye)
  5. ex05_38s_first_spark     — Cut 6A-pre (38.5s): Snout touches moonbeam (head cyan-silver, tail still unlit!)
  6. ex06_45s_petal_liftoff   — Cut 6C (45.5s): Ground-level macro of glowing golden-seeded petals rising upward
  7. ex07_73s_exit_c_r1       — Cut 8 (73.0s): Canon Exit C — glowing whale half-occluded behind R1 rock headland
  8. ex08_86s_aftermath_cam_a — Cut 9 (86.0s): Locked Cam A Dreamlike Aftermath (identical framing to 02.0s!)
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
    "cliff_tile_m": 24.0,
    "shore_albedo_mul": 0.44,
    "water_roughness": 0.018,
    "water_deep_absorb": 0.34,
    "moon_emission": 12.0,
    "moon_sun_energy_locked": 3.2,
    "moon_spot_energy_locked": 160000.0,
    "cavern_sky_bounce_energy": 1950000.0,
    "cavern_lake_bounce_energy": 520000.0,
    "beam_volume_density": 0.00048,
    "whale_unlit_albedo_mul": 0.58,
    "whale_ignite_emit": 3.4,
    "whale_climax_emit": 2.45,
    "whale_light_power": 380000.0,
    "flower_open_emit": 0.72,
    "flower_seed_emit": 2.6,
    "petal_emit": 1.85,
    "n_shore_flowers": 5400,
    "n_blizzard_petals": 2600,
    "glare_threshold": 1.55,
    "glare_mix": -0.72,
}

BASE_DIR = Path(os.environ.get("V7_WORK_DIR", "/tmp/v7_work"))
TEX_DIR = BASE_DIR / "textures"
ASSET_DIR = BASE_DIR / "assets"
OUT_DIR = BASE_DIR / "out_step5c"
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
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    tc = nt.nodes.new("ShaderNodeTexCoord")
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
    n1.inputs["Scale"].default_value = 0.12
    n1.inputs["Detail"].default_value = 4.0
    n1.inputs["Roughness"].default_value = 0.50
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])

    # Concentric breach ripples centered at (-3, -8, 0) for Cut 3A!
    sub_v = nt.nodes.new("ShaderNodeVectorMath")
    sub_v.operation = "DISTANCE"
    sub_v.inputs[1].default_value = (-3.0, -8.0, 0.0)
    nt.links.new(tc.outputs["Object"], sub_v.inputs[0])

    mul_f = nt.nodes.new("ShaderNodeMath"); mul_f.operation = "MULTIPLY"; mul_f.inputs[1].default_value = 1.8
    nt.links.new(sub_v.outputs["Value"], mul_f.inputs[0])
    sin_n = nt.nodes.new("ShaderNodeMath"); sin_n.operation = "SINE"
    nt.links.new(mul_f.outputs["Value"], sin_n.inputs[0])
    env_d = nt.nodes.new("ShaderNodeMapRange")
    env_d.inputs["From Min"].default_value = 0.0; env_d.inputs["From Max"].default_value = 32.0
    env_d.inputs["To Min"].default_value = 1.0; env_d.inputs["To Max"].default_value = 0.0
    env_d.clamp = True
    nt.links.new(sub_v.outputs["Value"], env_d.inputs["Value"])
    wake_mul = nt.nodes.new("ShaderNodeMath"); wake_mul.operation = "MULTIPLY"
    nt.links.new(sin_n.outputs["Value"], wake_mul.inputs[0]); nt.links.new(env_d.outputs["Result"], wake_mul.inputs[1])
    wake_str = nt.nodes.new("ShaderNodeMath"); wake_str.operation = "MULTIPLY"; wake_str.name = "WakeRippleStrength"
    wake_str.inputs[1].default_value = 0.0
    nt.links.new(wake_mul.outputs["Value"], wake_str.inputs[0])
    comb_h = nt.nodes.new("ShaderNodeMath"); comb_h.operation = "ADD"
    nt.links.new(n1.outputs["Fac"], comb_h.inputs[0]); nt.links.new(wake_str.outputs["Value"], comb_h.inputs[1])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.14
    nt.links.new(comb_h.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_whale_body_mat():
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
    base_mul.data_type = "RGBA"; base_mul.blend_type = "MULTIPLY"; base_mul.inputs["Factor"].default_value = 1.0
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

    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.46
    noise_w = nt.nodes.new("ShaderNodeTexNoise"); noise_w.inputs["Scale"].default_value = 0.24; noise_w.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], noise_w.inputs["Vector"])

    mix_irid = nt.nodes.new("ShaderNodeMath"); mix_irid.operation = "MULTIPLY_ADD"; mix_irid.inputs[1].default_value = 0.36
    nt.links.new(noise_w.outputs["Fac"], mix_irid.inputs[0]); nt.links.new(lw.outputs["Facing"], mix_irid.inputs[2])

    ramp_p1 = nt.nodes.new("ShaderNodeValToRGB")
    ramp_p1.color_ramp.elements[0].position = 0.05; ramp_p1.color_ramp.elements[0].color = (0.08, 0.56, 1.00, 1.0)
    e1 = ramp_p1.color_ramp.elements.new(0.46); e1.color = (0.64, 0.88, 1.00, 1.0)
    ramp_p1.color_ramp.elements[1].position = 0.86; ramp_p1.color_ramp.elements[1].color = (0.62, 0.28, 1.00, 1.0)
    nt.links.new(mix_irid.outputs["Value"], ramp_p1.inputs["Fac"])

    ramp_p3 = nt.nodes.new("ShaderNodeValToRGB")
    ramp_p3.color_ramp.elements[0].position = 0.06; ramp_p3.color_ramp.elements[0].color = (0.16, 0.72, 1.00, 1.0)
    e2 = ramp_p3.color_ramp.elements.new(0.38); e2.color = (0.94, 0.90, 1.00, 1.0)
    e3 = ramp_p3.color_ramp.elements.new(0.64); e3.color = (1.00, 0.44, 0.78, 1.0)
    ramp_p3.color_ramp.elements[1].position = 0.88; ramp_p3.color_ramp.elements[1].color = (1.00, 0.78, 0.32, 1.0)
    nt.links.new(mix_irid.outputs["Value"], ramp_p3.inputs["Fac"])

    phase_mix = nt.nodes.new("ShaderNodeMix"); phase_mix.name = "WhalePhaseColorMix"; phase_mix.data_type = "RGBA"
    phase_mix.inputs["Factor"].default_value = 0.0
    nt.links.new(ramp_p1.outputs["Color"], phase_mix.inputs["A"]); nt.links.new(ramp_p3.outputs["Color"], phase_mix.inputs["B"])
    nt.links.new(phase_mix.outputs["Result"], bsdf.inputs["Emission Color"])

    sep_o = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep_o.inputs["Vector"])
    wave_add = nt.nodes.new("ShaderNodeMath"); wave_add.operation = "MULTIPLY_ADD"; wave_add.inputs[1].default_value = 3.0
    nt.links.new(noise_w.outputs["Fac"], wave_add.inputs[0]); nt.links.new(sep_o.outputs["X"], wave_add.inputs[2])

    wave_rng = nt.nodes.new("ShaderNodeMapRange"); wave_rng.name = "WhaleIgniteWave"; wave_rng.clamp = True
    wave_rng.inputs["From Min"].default_value = -2.0; wave_rng.inputs["From Max"].default_value = 5.0
    nt.links.new(wave_add.outputs["Value"], wave_rng.inputs["Value"])

    contour_mul = nt.nodes.new("ShaderNodeMapRange")
    contour_mul.inputs["From Min"].default_value = 0.0; contour_mul.inputs["From Max"].default_value = 1.0
    contour_mul.inputs["To Min"].default_value = 0.20; contour_mul.inputs["To Max"].default_value = 1.52
    nt.links.new(lw.outputs["Facing"], contour_mul.inputs["Value"])

    emit_w = nt.nodes.new("ShaderNodeMath"); emit_w.operation = "MULTIPLY"
    nt.links.new(wave_rng.outputs["Result"], emit_w.inputs[0]); nt.links.new(contour_mul.outputs["Result"], emit_w.inputs[1])

    emit_str = nt.nodes.new("ShaderNodeMath"); emit_str.name = "WhaleEmitStrength"; emit_str.operation = "MULTIPLY"
    emit_str.inputs[1].default_value = 0.0
    nt.links.new(emit_w.outputs["Value"], emit_str.inputs[0]); nt.links.new(emit_str.outputs["Value"], bsdf.inputs["Emission Strength"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_whale_eye_mat():
    mat = bpy.data.materials.new("Mat_V7_WhaleEye")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.002, 0.005, 0.014, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.015
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat Roughness"].default_value = 0.01
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_flower_mats():
    m_open = bpy.data.materials.new("Mat_FL01_OpenPetal")
    m_open.use_nodes = True
    nt = m_open.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    t_p = nt.nodes.new("ShaderNodeTexImage"); t_p.image = load_img("petal_rgba.png", "sRGB")
    nt.links.new(t_p.outputs["Color"], bsdf.inputs["Base Color"]); nt.links.new(t_p.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.40
    nt.links.new(t_p.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = CONFIG["flower_open_emit"]
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    m_seed = bpy.data.materials.new("Mat_FL01_GoldSeed")
    m_seed.use_nodes = True
    nt = m_seed.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (1.0, 0.80, 0.36, 1.0)
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.82, 0.38, 1.0)
    bsdf.inputs["Emission Strength"].default_value = CONFIG["flower_seed_emit"]
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    m_bud = bpy.data.materials.new("Mat_FL01_ClosedBud")
    m_bud.use_nodes = True
    nt = m_bud.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.045, 0.048, 0.042, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.90
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    m_pet = bpy.data.materials.new("Mat_FL01_FlyingPetal")
    m_pet.use_nodes = True
    nt = m_pet.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    t_p2 = nt.nodes.new("ShaderNodeTexImage"); t_p2.image = load_img("petal_rgba.png", "sRGB")
    nt.links.new(t_p2.outputs["Color"], bsdf.inputs["Base Color"]); nt.links.new(t_p2.outputs["Alpha"], bsdf.inputs["Alpha"])
    mix_e = nt.nodes.new("ShaderNodeMix"); mix_e.data_type = "RGBA"; mix_e.blend_type = "MULTIPLY"
    mix_e.inputs["Factor"].default_value = 1.0; mix_e.inputs["B"].default_value = (1.0, 0.88, 0.56, 1.0)
    nt.links.new(t_p2.outputs["Color"], mix_e.inputs["A"]); nt.links.new(mix_e.outputs["Result"], bsdf.inputs["Emission Color"])
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
    bm.to_mesh(me); bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me); ob.data.materials.append(mat_rock)
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
    bm.to_mesh(me); bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(me.name, me); ob.data.materials.append(mat_rock)
    bpy.context.collection.objects.link(ob)

    for side in (-1.0, 1.0):
        bm = bmesh.new(); ny_r, nz_r = 34, 14; grid = []
        for k in range(nz_r):
            tz = k / (nz_r - 1); row = []
            for m in range(ny_r):
                ty = m / (ny_r - 1); py = fy0 + (fy1 - fy0) * ty
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
        bm.to_mesh(me2); bm.free()
        me2.polygons.foreach_set("use_smooth", [True] * len(me2.polygons))
        ob2 = bpy.data.objects.new(me2.name, me2); ob2.data.materials.append(mat_rock)
        bpy.context.collection.objects.link(ob2)

    build_natural_cliff_ridge("Cliff_L_Near", [(-82, -55), (-98, -15), (-125, 25), (-155, 65)], -6.0, 155.0, 11.2, mat_rock)
    build_natural_cliff_ridge("Cliff_L_Mid",  [(-102, 85), (-120, 135), (-142, 185)], -6.0, 165.0, 23.4, mat_rock)
    build_natural_cliff_ridge("Cliff_L_Far",  [(-130, 225), (-78, 285), (-15, 330)], -6.0, 175.0, 35.6, mat_rock)
    build_natural_cliff_ridge("Cliff_R_Near", [(148, 50), (118, 12), (96, -22), (82, -55)], -6.0, 155.0, 47.8, mat_rock)
    build_natural_cliff_ridge("Canon_R1_ExitHeadland", [(158, 72), (110, 56), (66, 56), (62, 82), (84, 124)], -6.0, 94.0, 59.1, mat_rock, taper_top=True)
    build_natural_cliff_ridge("Cliff_R_Far",  [(22, 330), (88, 282), (145, 212)], -6.0, 175.0, 71.3, mat_rock)

    bm = bmesh.new(); nx, ny = 96, 64
    xs = [-110.0 + 220.0 * i / (nx - 1) for i in range(nx)]
    ys = [-82.0 + 92.0 * j / (ny - 1) for j in range(ny)]
    grid = [[bm.verts.new((x, y, shore_z(x, y))) for x in xs] for y in ys]
    for j in range(ny - 1):
        for i in range(nx - 1):
            bm.faces.new((grid[j][i], grid[j][i+1], grid[j+1][i+1], grid[j+1][i]))
    me_s = bpy.data.meshes.new("V7_ShoreTerrace_S1")
    bm.to_mesh(me_s); bm.free()
    me_s.polygons.foreach_set("use_smooth", [True] * len(me_s.polygons))
    ob_s = bpy.data.objects.new(me_s.name, me_s); ob_s.data.materials.append(mat_shore)
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
                    mat = v; break
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
            bm_dst.to_mesh(me); bm_dst.free()
            ob = bpy.data.objects.new(me.name, me); ob.data.materials.append(mat)
            bpy.context.collection.objects.link(ob)
            objs.append(ob)
        return objs

    rng = random.Random(2028)
    xf_p0, xf_all, xf_after = [], [], []
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
            if rng.random() < 0.28:  # 28% lingering open blossoms in Cut 9 aftermath!
                xf_after.append(xf)

    # Extra lush P0 sanctum cluster for Cut 1B macro!
    for _ in range(320):
        ang = rng.uniform(0, 6.283)
        rad = rng.uniform(0.0, 4.5) ** 0.8
        fx, fy = 2.0 + math.cos(ang) * rad, -34.0 + math.sin(ang) * rad
        fz = shore_z(fx, fy)
        if fz > 0.1:
            sc = rng.uniform(0.34, 0.62)
            xf_p0.append(Matrix.Translation((fx, fy, fz - 0.02)) @ Euler((rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), rng.uniform(0, 6.28)), "XYZ").to_matrix().to_4x4() @ Matrix.Scale(sc, 4))

    open_map = {"Petals": m_open, "Seed": m_seed, "Stem": m_bud}
    bud_map  = {"Petals": m_bud,  "Seed": m_bud,  "Stem": m_bud}
    return {
        "p0_open":    merge_mesh_list(open_parts, xf_p0, open_map),
        "all_bud":    merge_mesh_list(bud_parts,  xf_all, bud_map),
        "all_open":   merge_mesh_list(open_parts, xf_all, open_map),
        "after_open": merge_mesh_list(open_parts, xf_after, open_map),
    }


def build_petal_clouds(m_pet):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ASSET_DIR / "sakura_petal_3d.glb"))
    src_ob = next(o for o in bpy.data.objects if o not in before and o.type == "MESH")
    me_src = src_ob.data.copy()
    bpy.data.objects.remove(src_ob, do_unlink=True)

    def make_cloud(name, transforms):
        bm = bmesh.new()
        uv_dst = bm.loops.layers.uv.verify()
        uv_src = me_src.uv_layers.active
        for xf in transforms:
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
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); ob.data.materials.append(m_pet)
        bpy.context.collection.objects.link(ob)
        return ob

    rng = random.Random(7777)
    # 1. Close-up rising petals right over P0/S1 for Cut 6C title macro!
    xf_macro = []
    for _ in range(420):
        px = rng.uniform(-6.0, 10.0)
        py = rng.uniform(-38.0, -26.0)
        pz = shore_z(px, py) + rng.uniform(0.15, 6.5)
        sc = rng.uniform(0.28, 0.62)
        xf_macro.append(Matrix.Translation((px, py, pz)) @ Euler((rng.uniform(0, 6.28), rng.uniform(0, 6.28), rng.uniform(0, 6.28)), "XYZ").to_matrix().to_4x4() @ Matrix.Scale(sc, 4))

    # 2. Lingering aftermath faint petals for Cut 9!
    xf_after = []
    for _ in range(240):
        px = rng.uniform(-45.0, 45.0)
        py = rng.uniform(-45.0, 45.0)
        pz = rng.uniform(2.0, 45.0)
        sc = rng.uniform(0.35, 0.85)
        xf_after.append(Matrix.Translation((px, py, pz)) @ Euler((rng.uniform(0, 6.28), rng.uniform(0, 6.28), rng.uniform(0, 6.28)), "XYZ").to_matrix().to_4x4() @ Matrix.Scale(sc, 4))

    # 3. Full Exit C trailing petals
    xf_exit = []
    for _ in range(1100):
        px = rng.uniform(-20.0, 95.0)
        py = rng.uniform(-10.0, 95.0)
        pz = rng.uniform(4.0, 65.0)
        sc = rng.uniform(0.45, 1.15)
        xf_exit.append(Matrix.Translation((px, py, pz)) @ Euler((rng.uniform(0, 6.28), rng.uniform(0, 6.28), rng.uniform(0, 6.28)), "XYZ").to_matrix().to_4x4() @ Matrix.Scale(sc, 4))

    return {
        "macro": make_cloud("Petals_MacroLiftoff", xf_macro),
        "after": make_cloud("Petals_Aftermath", xf_after),
        "exit":  make_cloud("Petals_ExitTrail", xf_exit),
    }


def setup_compositor(sc):
    if hasattr(sc, "compositing_node_group"):
        ng = bpy.data.node_groups.new("V7_CinemaComp", "CompositorNodeTree")
        sc.compositing_node_group = ng; nt = ng
        out_n = nt.nodes.new("NodeGroupOutput")
        ng.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    else:
        sc.use_nodes = True; nt = sc.node_tree; nt.nodes.clear()
        out_n = nt.nodes.new("CompositorNodeComposite")

    rl = nt.nodes.new("CompositorNodeRLayers")
    glare = nt.nodes.new("CompositorNodeGlare")
    set_ok = False
    if "Type" in glare.inputs:
        for val in ("Fog Glow", "FOG_GLOW", "Bloom", "BLOOM"):
            try:
                glare.inputs["Type"].default_value = val; set_ok = True; break
            except Exception:
                pass
    if not set_ok and hasattr(glare, "glare_type"):
        for val in ("FOG_GLOW", "BLOOM", "Fog Glow", "Bloom"):
            try:
                glare.glare_type = val; set_ok = True; break
            except Exception:
                pass
    if not set_ok:
        nt.links.new(rl.outputs["Image"], out_n.inputs["Image"]); return

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
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 4; sc.cycles.transparent_max_bounces = 6; sc.cycles.volume_bounces = 1
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
    sc.world = world; world.use_nodes = True
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
    lake = bpy.context.active_object; lake.data.materials.append(mat_water)

    moon_pos = Vector((4.0, 228.0, 234.0))
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=moon_pos)
    moon_card = bpy.context.active_object; moon_card.scale = (290.0, 175.0, 1.0)
    moon_card.rotation_euler = (Vector((-10.0, -62.0, 5.2)) - moon_pos).to_track_quat("Z", "Y").to_euler()
    m_moon = bpy.data.materials.new("Mat_V7_MoonSky"); m_moon.use_nodes = True
    nt = m_moon.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = load_img("moon_sky.jpg", "sRGB")
    em.inputs["Strength"].default_value = CONFIG["moon_emission"]
    nt.links.new(ti.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    moon_card.data.materials.append(m_moon)

    beam_start = Vector((4.0, 138.0, 158.0))
    beam_end   = Vector((2.0, -34.0, 0.0))
    beam_dir   = beam_end - beam_start
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=58.0, depth=beam_dir.length, location=(beam_start + beam_end) * 0.5)
    beam_ob = bpy.context.active_object
    beam_ob.rotation_euler = beam_dir.normalized().to_track_quat("-Z", "Y").to_euler()
    m_vol = bpy.data.materials.new("Mat_V7_MoonbeamVol"); m_vol.use_nodes = True
    nt = m_vol.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); pv = nt.nodes.new("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = (0.62, 0.84, 1.0, 1.0); pv.inputs["Anisotropy"].default_value = 0.62
    tc_v = nt.nodes.new("ShaderNodeTexCoord"); sep_v = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc_v.outputs["Object"], sep_v.inputs["Vector"])
    x2 = nt.nodes.new("ShaderNodeMath"); x2.operation = "MULTIPLY"; nt.links.new(sep_v.outputs["X"], x2.inputs[0]); nt.links.new(sep_v.outputs["X"], x2.inputs[1])
    y2 = nt.nodes.new("ShaderNodeMath"); y2.operation = "MULTIPLY"; nt.links.new(sep_v.outputs["Y"], y2.inputs[0]); nt.links.new(sep_v.outputs["Y"], y2.inputs[1])
    r2 = nt.nodes.new("ShaderNodeMath"); r2.operation = "ADD"; nt.links.new(x2.outputs["Value"], r2.inputs[0]); nt.links.new(y2.outputs["Value"], r2.inputs[1])
    rmap = nt.nodes.new("ShaderNodeMapRange"); rmap.interpolation_type = "SMOOTHSTEP"; rmap.clamp = True
    rmap.inputs["From Min"].default_value = 180.0; rmap.inputs["From Max"].default_value = 2800.0
    rmap.inputs["To Min"].default_value = CONFIG["beam_volume_density"]; rmap.inputs["To Max"].default_value = 0.0
    nt.links.new(r2.outputs["Value"], rmap.inputs["Value"]); nt.links.new(rmap.outputs["Result"], pv.inputs["Density"])
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

    # Add glossy dark serene eye sphere parented to whale (local left side near mouth corner) for Cut 4B!
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=0.34, location=(5.4, 2.05, -0.35))
    eye_l = bpy.context.active_object; eye_l.name = "WH01_SereneEye_L"
    eye_l.data.materials.append(mat_eye)
    eye_l.parent = whale

    fl_groups = build_flower_carpet(m_open, m_seed, m_bud)
    p_clouds  = build_petal_clouds(m_pet)

    # Lights
    sun_d = bpy.data.lights.new("Key_MoonSun", type="SUN")
    sun_d.energy = CONFIG["moon_sun_energy_locked"]; sun_d.color = (0.72, 0.86, 1.0); sun_d.angle = math.radians(2.5)
    sun_o = bpy.data.objects.new("Key_MoonSun", sun_d); bpy.context.collection.objects.link(sun_o)
    sun_o.rotation_euler = (moon_pos - beam_end).to_track_quat("Z", "Y").to_euler()

    spot_d = bpy.data.lights.new("Spot_MoonbeamP0", type="SPOT")
    spot_d.energy = CONFIG["moon_spot_energy_locked"]; spot_d.color = (0.76, 0.90, 1.0)
    spot_d.spot_size = math.radians(36.0); spot_d.spot_blend = 0.65; spot_d.shadow_soft_size = 8.0
    spot_o = bpy.data.objects.new("Spot_MoonbeamP0", spot_d)
    spot_o.location = beam_start; spot_o.rotation_euler = (beam_end - beam_start).to_track_quat("-Z", "Y").to_euler()
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

    eye_d = bpy.data.lights.new("Light_EyeCatch", type="POINT")
    eye_d.energy = 0.0; eye_d.color = (0.80, 0.94, 1.0); eye_d.shadow_soft_size = 0.18
    eye_o = bpy.data.objects.new("Light_EyeCatch", eye_d)
    bpy.context.collection.objects.link(eye_o)

    wlight_d = bpy.data.lights.new("Light_WhaleRadiance", type="POINT")
    wlight_d.energy = 0.0; wlight_d.color = (0.82, 0.92, 1.0); wlight_d.shadow_soft_size = 9.0
    wlight_o = bpy.data.objects.new("Light_WhaleRadiance", wlight_d)
    wlight_o.visible_camera = False; wlight_o.visible_glossy = False
    bpy.context.collection.objects.link(wlight_o)

    cam_d = bpy.data.cameras.new("V7_MainCam")
    cam_d.sensor_width = 36.0; cam_d.clip_start = 0.15; cam_d.clip_end = 1200.0
    cam_o = bpy.data.objects.new("V7_MainCam", cam_d)
    bpy.context.collection.objects.link(cam_o); sc.camera = cam_o

    setup_compositor(sc)

    p0_z = shore_z(2.0, -34.0)
    c4_x, c4_y = -11.5, -45.0
    c4_z = max(4.2, shore_z(c4_x, c4_y) + 1.8)

    # 8 NEW CUTS TO COMPLETE THE FULL 16-CUT 90-SECOND STORYBOARD!
    shots = [
        {
            "slug": "ex01_02s_open_cam_a",
            "cam_pos": Vector((-10.0, -62.0, 5.2)), "cam_tgt": Vector((4.0, 48.0, 31.0)), "focal": 20.0,
            "dof": False, "fstop": 8.0, "whale_vis": False,
            "w_pos": Vector((0, 0, -50)), "w_rot": Euler((0, 0, 0), "XYZ"),
            "wake": 0.0, "eye_catch": None, "w_emit": 0.0, "w_phase": 0.0, "w_wave": (15, 20),
            "w_light": 0.0, "w_lcol": (0.7, 0.85, 1.0), "fl_mode": "p0_only", "petal_mode": None,
        },
        {
            "slug": "ex02_08s_p0_flower_macro",
            "cam_pos": Vector((-0.6, -37.2, shore_z(-0.6, -37.2) + 0.42)),
            "cam_tgt": Vector((2.2, -33.5, p0_z + 0.18)), "focal": 58.0,
            "dof": True, "fstop": 2.4, "whale_vis": False,
            "w_pos": Vector((0, 0, -50)), "w_rot": Euler((0, 0, 0), "XYZ"),
            "wake": 0.0, "eye_catch": None, "w_emit": 0.0, "w_phase": 0.0, "w_wave": (15, 20),
            "w_light": 0.0, "w_lcol": (0.7, 0.85, 1.0), "fl_mode": "p0_only", "petal_mode": None,
        },
        {
            "slug": "ex03_21s_silent_breach",
            "cam_pos": Vector((-10.0, -58.0, 6.2)), "cam_tgt": Vector((-1.0, 6.0, 7.5)), "focal": 24.0,
            "dof": False, "fstop": 8.0, "whale_vis": True,
            "w_pos": Vector((-3.0, -8.0, 2.2)), "w_rot": Euler((math.radians(4.0), math.radians(-18.0), math.radians(-115.0)), "XYZ"),
            "wake": 3.2, "eye_catch": None, "w_emit": 0.0, "w_phase": 0.0, "w_wave": (15, 20),
            "w_light": 0.0, "w_lcol": (0.7, 0.85, 1.0), "fl_mode": "p0_only", "petal_mode": None,
        },
        {
            "slug": "ex04_30s_eye_hold_macro",
            # Tight poetic 65mm portrait of the whale's left flank/face & calm dark eye catching silver moonlight!
            "cam_pos": Vector((-9.5, -34.5, max(4.5, shore_z(-9.5, -34.5) + 2.2))),
            "cam_tgt": Vector((-1.8, -19.5, 8.6)), "focal": 68.0,
            "dof": True, "fstop": 2.8, "whale_vis": True,
            "w_pos": Vector((1.5, -16.0, 9.2)), "w_rot": Euler((math.radians(5.0), math.radians(10.0), math.radians(-142.0)), "XYZ"),
            "wake": 0.4, "eye_catch": (Vector((-9.5, -26.0, 11.2)), 9500.0),
            "w_emit": 0.0, "w_phase": 0.0, "w_wave": (15, 20),
            "w_light": 0.0, "w_lcol": (0.7, 0.85, 1.0), "fl_mode": "p0_only", "petal_mode": None,
        },
        {
            "slug": "ex05_38s_first_spark",
            # Exact split-second snout touches moonbeam: ONLY front snout (+X > +3) ignites cyan-silver; tail stays dark!
            "cam_pos": Vector((-8.0, -48.0, 6.4)), "cam_tgt": Vector((4.5, 12.0, 26.5)), "focal": 32.0,
            "dof": False, "fstop": 8.0, "whale_vis": True,
            "w_pos": Vector((3.0, 8.0, 25.5)), "w_rot": Euler((math.radians(-10.0), math.radians(-26.0), math.radians(34.0)), "XYZ"),
            "wake": 0.0, "eye_catch": None, "w_emit": CONFIG["whale_ignite_emit"] * 1.15, "w_phase": 0.0, "w_wave": (4.0, 9.0),
            "w_light": CONFIG["whale_light_power"] * 0.42, "w_lcol": (0.45, 0.82, 1.0),
            "fl_mode": "p0_only", "petal_mode": None,
        },
        {
            "slug": "ex06_45s_petal_liftoff",
            # Title Beat『空に降る雪』: Ground-level 45mm macro looking UP through blooming flowers & rising golden petals!
            "cam_pos": Vector((-1.2, -36.5, shore_z(-1.2, -36.5) + 0.36)),
            "cam_tgt": Vector((2.5, -24.0, 6.2)), "focal": 42.0,
            "dof": True, "fstop": 2.8, "whale_vis": True,
            "w_pos": Vector((4.0, 22.0, 32.0)), "w_rot": Euler((math.radians(-12.0), math.radians(-14.0), math.radians(24.0)), "XYZ"),
            "wake": 0.0, "eye_catch": None, "w_emit": CONFIG["whale_climax_emit"], "w_phase": 1.0, "w_wave": (-20, -14),
            "w_light": CONFIG["whale_light_power"] * 0.90, "w_lcol": (1.0, 0.90, 0.78),
            "fl_mode": "all_open", "petal_mode": "macro",
        },
        {
            "slug": "ex07_73s_exit_c_r1",
            # Canon Exit C: Glowing Pearl-Opal whale half-occluded behind right-hand rocky headland R1!
            "cam_pos": Vector((-10.0, -62.0, 6.2)), "cam_tgt": Vector((38.0, 66.0, 26.0)), "focal": 24.0,
            "dof": False, "fstop": 8.0, "whale_vis": True,
            "w_pos": Vector((64.0, 82.0, 28.0)), "w_rot": Euler((math.radians(-8.0), math.radians(-6.0), math.radians(24.0)), "XYZ"),
            "wake": 0.0, "eye_catch": None, "w_emit": CONFIG["whale_climax_emit"], "w_phase": 1.0, "w_wave": (-20, -14),
            "w_light": CONFIG["whale_light_power"] * 0.75, "w_lcol": (1.0, 0.88, 0.74),
            "fl_mode": "all_open", "petal_mode": "exit",
        },
        {
            "slug": "ex08_86s_aftermath_cam_a",
            # Cut 9 Dreamlike Aftermath: IDENTICAL locked Cam A to Cut 1 (02.0s), whale gone, lingering blossoms & faint petals!
            "cam_pos": Vector((-10.0, -62.0, 5.2)), "cam_tgt": Vector((4.0, 48.0, 31.0)), "focal": 20.0,
            "dof": False, "fstop": 8.0, "whale_vis": False,
            "w_pos": Vector((0, 0, -50)), "w_rot": Euler((0, 0, 0), "XYZ"),
            "wake": 0.0, "eye_catch": None, "w_emit": 0.0, "w_phase": 0.0, "w_wave": (15, 20),
            "w_light": 0.0, "w_lcol": (0.7, 0.85, 1.0), "fl_mode": "aftermath", "petal_mode": "after",
        },
    ]

    wake_node    = mat_water.node_tree.nodes["WakeRippleStrength"]
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

        whale.hide_render = not sh["whale_vis"]
        eye_l.hide_render = not sh["whale_vis"]
        whale.location = sh["w_pos"]
        whale.rotation_euler = sh["w_rot"]

        wake_node.inputs[1].default_value = sh["wake"]
        if sh["eye_catch"]:
            eye_o.location = sh["eye_catch"][0]; eye_d.energy = sh["eye_catch"][1]
        else:
            eye_d.energy = 0.0

        w_emit_node.inputs[1].default_value = sh["w_emit"]
        w_phase_node.inputs["Factor"].default_value = sh["w_phase"]
        w_wave_node.inputs["From Min"].default_value = sh["w_wave"][0]
        w_wave_node.inputs["From Max"].default_value = sh["w_wave"][1]

        wlight_o.location = sh["w_pos"] + Vector((0.0, -2.0, -1.5))
        wlight_d.energy = sh["w_light"]; wlight_d.color = sh["w_lcol"]

        fm = sh["fl_mode"]
        set_vis(fl_groups["p0_open"], True)
        set_vis(fl_groups["all_open"], fm == "all_open")
        set_vis(fl_groups["all_bud"],  fm in ("p0_only", "aftermath"))
        set_vis(fl_groups["after_open"], fm == "aftermath")

        for k, ob in p_clouds.items():
            ob.hide_render = (sh["petal_mode"] != k)

        out_png = OUT_DIR / f"{sh['slug']}.png"
        sc.render.filepath = str(out_png)
        ts = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[STEP 5C GPU] {sh['slug']} rendered in {time.time() - ts:.1f}s -> {out_png}")

    print(f"[STEP 5C DONE] All 8 Extra Cuts finished in {time.time() - t0:.1f}s!")


if __name__ == "__main__":
    main()
