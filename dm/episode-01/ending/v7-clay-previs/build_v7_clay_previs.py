#!/usr/bin/env python3
"""Blender 4.x / 5.x 100-Point Theatrical Clay Previs Engine for Episode 1 Ending 'Kousetsuka' (v7.0).

Built against all 6 project creative & technical skills:
  - cinematic-previs (matte clay, real S35/FF optics, 24fps, 180deg motion blur, DoF, stills-first QA)
  - cinematic-camera-continuity (unbroken 3D C1 spline, zero teleport/axis-flip, dirty OTS, eye-trace handoff)
  - animation-principles (Disney 12 principles: stroke->glide timing, pectoral wing lag, true petal detachment)
  - illustration-composition (4-act chiaroscuro value arc, 4-layer controlled snow density, foreground-mid-far depth)
  - blender-python-previs (Blender 5.3+ API safe, NumPy vectorized 2,020-petal snow + 450-flower colony, OptiX GPU)
  - gemini-previs-video (3-detail physical consequences: water drop, breach spray, belly drips, awakening breath)

Run headless:
  blender --background --factory-startup --python-exit-code 1 \
    --python dm/episode-01/ending/v7-clay-previs/build_v7_clay_previs.py -- --mode stills --quality cycles
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
import bmesh
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "spec_v7.json"
OUT_DIR = ROOT / "out"
LOOK_DIR = OUT_DIR / "look"
STILLS_DIR = OUT_DIR / "stills"
CLIPS_DIR = OUT_DIR / "clips"
QA_REPORT_PATH = OUT_DIR / "qa_v7_report.json"


# ---------------------------------------------------------------------------
# Math, Easing & Continuous Snow Integral Helpers
# ---------------------------------------------------------------------------

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def smoothstep(e0: float, e1: float, x: float) -> float:
    t = clamp((x - e0) / (e1 - e0 if abs(e1 - e0) > 1e-6 else 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ease_cubic(u: float) -> float:
    t = clamp(u, 0.0, 1.0)
    return 4.0 * t * t * t if t < 0.5 else 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_vec(a, b, t: float) -> Vector:
    return Vector(a).lerp(Vector(b), t)


def _build_snow_integral_table():
    """Precompute C2-smooth vertical & swirl displacement integrals over u = t - 36.8 in [0, 62s].
    Eliminates ALL t=70s velocity/position discontinuities: petals lift (36.8..66s), lose lift & hang
    weightlessly as the whale climbs away (66..71s = '置いていかれる雪'), then drift steadily down (71s+)."""
    n = 1551
    dt = 0.04
    us = np.arange(n, dtype=np.float64) * dt
    # Updraft velocity ramps up 0..2.4s, cruises through C6a-C6d, decays smoothly to 0 across 28.5..33.8s (t=65.3..70.6s)
    v_up = np.array([
        smoothstep(0.0, 2.4, u) * (1.0 - smoothstep(28.5, 33.8, u)) * (1.0 + 0.35 * smoothstep(2.0, 8.0, u))
        for u in us
    ], dtype=np.float64)
    # Downward gravity snowfall ramps smoothly across 31.8..36.8s (t=68.6..73.6s)
    v_dn = np.array([smoothstep(31.8, 36.8, u) for u in us], dtype=np.float64)
    # Wind swirl strength decays smoothly as whale departs
    w_sw = np.array([smoothstep(0.0, 2.6, u) * (1.0 - smoothstep(29.0, 35.5, u)) for u in us], dtype=np.float64)

    int_up = np.zeros(n, dtype=np.float64)
    int_dn = np.zeros(n, dtype=np.float64)
    int_sw = np.zeros(n, dtype=np.float64)
    int_up[1:] = np.cumsum(0.5 * (v_up[:-1] + v_up[1:]) * dt)
    int_dn[1:] = np.cumsum(0.5 * (v_dn[:-1] + v_dn[1:]) * dt)
    int_sw[1:] = np.cumsum(0.5 * (w_sw[:-1] + w_sw[1:]) * dt)
    return dt, int_up, int_dn, int_sw


_SNOW_DT, _SNOW_INT_UP, _SNOW_INT_DN, _SNOW_INT_SW = _build_snow_integral_table()


def eval_snow_integrals(u: float) -> tuple[float, float, float]:
    if u <= 0.0:
        return 0.0, 0.0, 0.0
    fi = u / _SNOW_DT
    i0 = min(len(_SNOW_INT_UP) - 2, int(fi))
    f = clamp(fi - i0, 0.0, 1.0)
    iu = float(_SNOW_INT_UP[i0] * (1.0 - f) + _SNOW_INT_UP[i0 + 1] * f)
    idn = float(_SNOW_INT_DN[i0] * (1.0 - f) + _SNOW_INT_DN[i0 + 1] * f)
    isw = float(_SNOW_INT_SW[i0] * (1.0 - f) + _SNOW_INT_SW[i0 + 1] * f)
    return iu, idn, isw


# ---------------------------------------------------------------------------
# Scene Reset & Refined Chiaroscuro Clay Materials
# ---------------------------------------------------------------------------

def clear_scene():
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.materials, bpy.data.worlds, bpy.data.actions):
        for item in list(col):
            if item.users == 0:
                col.remove(item)
    scene.camera = None


def make_watergate_stone_material(name: str = "MAT-ArchStone_Clay"):
    """v7.7 Subterranean Old-Kingdom Slate Masonry (blender-skills materials + value-hierarchy lock):
    - Midground Twin Water-Gates MUST act as dark theatrical side frames (24-36% value) rather than glare walls!
    - Procedural weathered stone block variation + mortar AO cavity darkening + moss-tinged parapets + wet waterline."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.28

    geom = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geom.outputs["Position"], sep.inputs["Vector"])

    # Stone masonry block noise + mortar patina crevices
    n_stone = nt.nodes.new("ShaderNodeTexNoise")
    n_stone.inputs["Scale"].default_value = 0.55
    n_stone.inputs["Detail"].default_value = 6.0
    n_stone.inputs["Roughness"].default_value = 0.62
    nt.links.new(geom.outputs["Position"], n_stone.inputs["Vector"])

    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 0.72
    vor.inputs["Randomness"].default_value = 0.35
    nt.links.new(geom.outputs["Position"], vor.inputs["Vector"])

    mortar_mr = nt.nodes.new("ShaderNodeMapRange")
    mortar_mr.interpolation_type = "SMOOTHSTEP"
    mortar_mr.clamp = True
    mortar_mr.inputs["From Min"].default_value = 0.02
    mortar_mr.inputs["From Max"].default_value = 0.14
    mortar_mr.inputs["To Min"].default_value = 0.48
    mortar_mr.inputs["To Max"].default_value = 1.0
    nt.links.new(vor.outputs["Distance"], mortar_mr.inputs["Value"])

    stone_cr = nt.nodes.new("ShaderNodeValToRGB")
    stone_cr.color_ramp.elements[0].position = 0.25
    stone_cr.color_ramp.elements[0].color = (0.040, 0.055, 0.082, 1.0)
    stone_cr.color_ramp.elements[1].position = 0.78
    stone_cr.color_ramp.elements[1].color = (0.082, 0.106, 0.148, 1.0)
    nt.links.new(n_stone.outputs["Fac"], stone_cr.inputs["Fac"])

    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 4
    ao.inputs["Distance"].default_value = 3.2
    nt.links.new(stone_cr.outputs["Color"], ao.inputs["Color"])

    cav_fac = nt.nodes.new("ShaderNodeMath")
    cav_fac.operation = "MULTIPLY"
    nt.links.new(ao.outputs["AO"], cav_fac.inputs[0])
    nt.links.new(mortar_mr.outputs["Result"], cav_fac.inputs[1])

    stone_cav = nt.nodes.new("ShaderNodeMix")
    stone_cav.data_type = "RGBA"
    stone_cav.inputs["A"].default_value = (0.022, 0.030, 0.046, 1.0)
    nt.links.new(cav_fac.outputs["Value"], stone_cav.inputs["Factor"])
    nt.links.new(ao.outputs["Color"], stone_cav.inputs["B"])

    # Capillary wet waterline band z = 0..3.1m
    n_jit = nt.nodes.new("ShaderNodeMapRange")
    n_jit.inputs["From Min"].default_value = 0.2
    n_jit.inputs["From Max"].default_value = 0.8
    n_jit.inputs["To Min"].default_value = -0.55
    n_jit.inputs["To Max"].default_value = 0.55
    nt.links.new(n_stone.outputs["Fac"], n_jit.inputs["Value"])
    z_eff = nt.nodes.new("ShaderNodeMath")
    z_eff.operation = "ADD"
    nt.links.new(sep.outputs["Z"], z_eff.inputs[0])
    nt.links.new(n_jit.outputs["Result"], z_eff.inputs[1])

    dry_f = nt.nodes.new("ShaderNodeMapRange")
    dry_f.interpolation_type = "SMOOTHSTEP"
    dry_f.clamp = True
    dry_f.inputs["From Min"].default_value = -0.15
    dry_f.inputs["From Max"].default_value = 3.1
    dry_f.inputs["To Min"].default_value = 0.0
    dry_f.inputs["To Max"].default_value = 1.0
    nt.links.new(z_eff.outputs["Value"], dry_f.inputs["Value"])

    c_wet = nt.nodes.new("ShaderNodeMix")
    c_wet.data_type = "RGBA"
    c_wet.inputs["A"].default_value = (0.016, 0.022, 0.036, 1.0)
    nt.links.new(dry_f.outputs["Result"], c_wet.inputs["Factor"])
    nt.links.new(stone_cav.outputs["Result"], c_wet.inputs["B"])

    # Subtle glossy reflection damping in mirror lake
    lp = nt.nodes.new("ShaderNodeLightPath")
    g_dim = nt.nodes.new("ShaderNodeMix")
    g_dim.data_type = "RGBA"
    g_dim.blend_type = "MULTIPLY"
    g_dim.inputs["B"].default_value = (0.72, 0.74, 0.78, 1.0)
    nt.links.new(lp.outputs["Is Glossy Ray"], g_dim.inputs["Factor"])
    nt.links.new(c_wet.outputs["Result"], g_dim.inputs["A"])
    nt.links.new(g_dim.outputs["Result"], bsdf.inputs["Base Color"])

    r_wet = nt.nodes.new("ShaderNodeMapRange")
    r_wet.clamp = True
    r_wet.inputs["From Min"].default_value = 0.0
    r_wet.inputs["From Max"].default_value = 1.0
    r_wet.inputs["To Min"].default_value = 0.22
    r_wet.inputs["To Max"].default_value = 0.84
    nt.links.new(dry_f.outputs["Result"], r_wet.inputs["Value"])
    nt.links.new(r_wet.outputs["Result"], bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.28
    bump.inputs["Distance"].default_value = 0.12
    nt.links.new(mortar_mr.outputs["Result"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # Distance atmospheric mist veil far out along outer arches (95..220m)
    cam_data = nt.nodes.new("ShaderNodeCameraData")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.interpolation_type = "SMOOTHSTEP"
    mr.clamp = True
    mr.inputs["From Min"].default_value = 95.0
    mr.inputs["From Max"].default_value = 225.0
    mr.inputs["To Min"].default_value = 0.0
    mr.inputs["To Max"].default_value = 0.65
    nt.links.new(cam_data.outputs["View Z Depth"], mr.inputs["Value"])
    mist_em = nt.nodes.new("ShaderNodeEmission")
    mist_em.name = "MIST_EM"
    mist_em.inputs["Color"].default_value = (0.025, 0.040, 0.068, 1.0)
    mist_em.inputs["Strength"].default_value = 0.22
    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mr.outputs["Result"], mix_sh.inputs["Fac"])
    nt.links.new(bsdf.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(mist_em.outputs["Emission"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_cavern_roof_material(name: str = "MAT-CavernRoof"):
    """v9.0 Stratified Karst Limestone Cavern Interior Material (Roof Canopy, Cave Walls, Reefs, Stalactites, Pillars, Fissure):
    Blends anime_cliff_albedo.jpg + horizontal sedimentary bedding ribs + crevice AO + subtle cold Act 1-3 glow-moss pinpoints."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.90
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.20

    rev = nt.nodes.new("ShaderNodeValue")
    rev.name = "VAL_ROOF_REVEAL"
    rev.outputs[0].default_value = 0.24

    geom = nt.nodes.new("ShaderNodeNewGeometry")
    sep_p = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geom.outputs["Position"], sep_p.inputs["Vector"])

    # Macro limestone massif turbulence + Z-compressed sedimentary strata bedding
    n_rock = nt.nodes.new("ShaderNodeTexNoise")
    n_rock.inputs["Scale"].default_value = 0.14
    n_rock.inputs["Detail"].default_value = 8.0
    n_rock.inputs["Roughness"].default_value = 0.68
    nt.links.new(geom.outputs["Position"], n_rock.inputs["Vector"])

    mp_strata = nt.nodes.new("ShaderNodeMapping")
    mp_strata.inputs["Scale"].default_value = (0.04, 0.04, 0.28)
    nt.links.new(geom.outputs["Position"], mp_strata.inputs["Vector"])

    n_strata = nt.nodes.new("ShaderNodeTexNoise")
    n_strata.inputs["Scale"].default_value = 1.15
    n_strata.inputs["Detail"].default_value = 6.0
    n_strata.inputs["Roughness"].default_value = 0.62
    nt.links.new(mp_strata.outputs["Vector"], n_strata.inputs["Vector"])

    vor_block = nt.nodes.new("ShaderNodeTexVoronoi")
    vor_block.feature = "DISTANCE_TO_EDGE"
    vor_block.inputs["Scale"].default_value = 0.16
    nt.links.new(geom.outputs["Position"], vor_block.inputs["Vector"])

    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 8
    ao.inputs["Distance"].default_value = 2.8

    # Tri-planar BOX painted cliff texture at macro cave scale (~24m tile)
    cliff_img = _load_tex_image("anime_cliff_albedo.jpg", "sRGB")
    cliff_bw = None
    dark_ramp = nt.nodes.new("ShaderNodeValToRGB")
    dark_ramp.color_ramp.elements[0].position = 0.22
    dark_ramp.color_ramp.elements[0].color = (0.036, 0.046, 0.068, 1.0)
    dark_ramp.color_ramp.elements[1].position = 0.82
    dark_ramp.color_ramp.elements[1].color = (0.095, 0.116, 0.155, 1.0)
    nt.links.new(n_strata.outputs["Fac"], dark_ramp.inputs["Fac"])

    stone_src = dark_ramp.outputs["Color"]
    if cliff_img is not None:
        mp_cl = nt.nodes.new("ShaderNodeMapping")
        mp_cl.inputs["Scale"].default_value = (0.042, 0.042, 0.042)
        nt.links.new(geom.outputs["Position"], mp_cl.inputs["Vector"])
        tc_cl = nt.nodes.new("ShaderNodeTexImage")
        tc_cl.image = cliff_img
        tc_cl.projection = "BOX"
        tc_cl.projection_blend = 0.35
        nt.links.new(mp_cl.outputs["Vector"], tc_cl.inputs["Vector"])

        cliff_bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(tc_cl.outputs["Color"], cliff_bw.inputs["Color"])

        dim_cl = nt.nodes.new("ShaderNodeMix")
        dim_cl.data_type = "RGBA"
        dim_cl.blend_type = "MULTIPLY"
        dim_cl.inputs["Factor"].default_value = 1.0
        dim_cl.inputs["B"].default_value = (0.20, 0.23, 0.28, 1.0)
        nt.links.new(tc_cl.outputs["Color"], dim_cl.inputs["A"])

        mix_cl = nt.nodes.new("ShaderNodeMix")
        mix_cl.data_type = "RGBA"
        mix_cl.inputs["Factor"].default_value = 0.52
        nt.links.new(dark_ramp.outputs["Color"], mix_cl.inputs["A"])
        nt.links.new(dim_cl.outputs["Result"], mix_cl.inputs["B"])
        stone_src = mix_cl.outputs["Result"]

    # Crevice AO shadow + waterline capillary darkening below z = 2.6m
    ao_cav = nt.nodes.new("ShaderNodeMix")
    ao_cav.data_type = "RGBA"
    ao_cav.inputs["A"].default_value = (0.008, 0.011, 0.018, 1.0)
    nt.links.new(ao.outputs["AO"], ao_cav.inputs["Factor"])
    nt.links.new(stone_src, ao_cav.inputs["B"])

    col_act = nt.nodes.new("ShaderNodeMix")
    col_act.data_type = "RGBA"
    col_act.blend_type = "MULTIPLY"
    col_act.inputs["Factor"].default_value = 1.0
    nt.links.new(ao_cav.outputs["Result"], col_act.inputs["A"])

    val_lvl = nt.nodes.new("ShaderNodeMapRange")
    val_lvl.clamp = True
    val_lvl.inputs["From Min"].default_value = 0.0
    val_lvl.inputs["From Max"].default_value = 1.0
    val_lvl.inputs["To Min"].default_value = 0.54
    val_lvl.inputs["To Max"].default_value = 1.08
    nt.links.new(rev.outputs[0], val_lvl.inputs["Value"])

    comb_v = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(val_lvl.outputs["Result"], comb_v.inputs["Red"])
    nt.links.new(val_lvl.outputs["Result"], comb_v.inputs["Green"])
    nt.links.new(val_lvl.outputs["Result"], comb_v.inputs["Blue"])
    nt.links.new(comb_v.outputs["Color"], col_act.inputs["B"])

    wet_w = nt.nodes.new("ShaderNodeMapRange")
    wet_w.interpolation_type = "SMOOTHSTEP"
    wet_w.clamp = True
    wet_w.inputs["From Min"].default_value = -0.2
    wet_w.inputs["From Max"].default_value = 2.8
    nt.links.new(sep_p.outputs["Z"], wet_w.inputs["Value"])

    col_wet = nt.nodes.new("ShaderNodeMix")
    col_wet.data_type = "RGBA"
    col_wet.inputs["A"].default_value = (0.010, 0.014, 0.022, 1.0)
    nt.links.new(wet_w.outputs["Result"], col_wet.inputs["Factor"])
    nt.links.new(col_act.outputs["Result"], col_wet.inputs["B"])
    nt.links.new(col_wet.outputs["Result"], bsdf.inputs["Base Color"])

    r_wet = nt.nodes.new("ShaderNodeMapRange")
    r_wet.clamp = True
    r_wet.inputs["From Min"].default_value = 0.0
    r_wet.inputs["From Max"].default_value = 1.0
    r_wet.inputs["To Min"].default_value = 0.24
    r_wet.inputs["To Max"].default_value = 0.90
    nt.links.new(wet_w.outputs["Result"], r_wet.inputs["Value"])
    nt.links.new(r_wet.outputs["Result"], bsdf.inputs["Roughness"])

    # Stratified rock + block fracture + painted cliff height bump
    h_mix = nt.nodes.new("ShaderNodeMath")
    h_mix.operation = "MULTIPLY_ADD"
    h_mix.inputs[1].default_value = 0.55
    nt.links.new(n_rock.outputs["Fac"], h_mix.inputs[0])
    h_str = nt.nodes.new("ShaderNodeMath")
    h_str.operation = "MULTIPLY_ADD"
    h_str.inputs[1].default_value = 0.35
    nt.links.new(n_strata.outputs["Fac"], h_str.inputs[0])
    if cliff_bw is not None:
        h_cbw = nt.nodes.new("ShaderNodeMath")
        h_cbw.operation = "MULTIPLY"
        h_cbw.inputs[1].default_value = 0.30
        nt.links.new(cliff_bw.outputs["Val"], h_cbw.inputs[0])
        nt.links.new(h_cbw.outputs["Value"], h_str.inputs[2])
    else:
        h_str.inputs[2].default_value = 0.0
    nt.links.new(h_str.outputs["Value"], h_mix.inputs[2])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.72
    bump.inputs["Distance"].default_value = 0.42
    nt.links.new(h_mix.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # Subtle cold grazing rim + whisper-dim subterranean glow-moss starlight specks (world/02!)
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.40

    if "Emission Color" in bsdf.inputs:
        vor_gm = nt.nodes.new("ShaderNodeTexVoronoi")
        vor_gm.inputs["Scale"].default_value = 2.6
        nt.links.new(geom.outputs["Position"], vor_gm.inputs["Vector"])

        gm_dot = nt.nodes.new("ShaderNodeMapRange")
        gm_dot.clamp = True
        gm_dot.inputs["From Min"].default_value = 0.01
        gm_dot.inputs["From Max"].default_value = 0.048
        gm_dot.inputs["To Min"].default_value = 1.0
        gm_dot.inputs["To Max"].default_value = 0.0
        nt.links.new(vor_gm.outputs["Distance"], gm_dot.inputs["Value"])

        n_gm_patch = nt.nodes.new("ShaderNodeTexNoise")
        n_gm_patch.inputs["Scale"].default_value = 0.075
        n_gm_patch.inputs["Detail"].default_value = 3.0
        nt.links.new(geom.outputs["Position"], n_gm_patch.inputs["Vector"])

        gm_patch = nt.nodes.new("ShaderNodeMapRange")
        gm_patch.clamp = True
        gm_patch.inputs["From Min"].default_value = 0.56
        gm_patch.inputs["From Max"].default_value = 0.72
        nt.links.new(n_gm_patch.outputs["Fac"], gm_patch.inputs["Value"])

        gm_z = nt.nodes.new("ShaderNodeMapRange")
        gm_z.clamp = True
        gm_z.inputs["From Min"].default_value = 3.5
        gm_z.inputs["From Max"].default_value = 12.0
        nt.links.new(sep_p.outputs["Z"], gm_z.inputs["Value"])

        gm_mul1 = nt.nodes.new("ShaderNodeMath")
        gm_mul1.operation = "MULTIPLY"
        nt.links.new(gm_dot.outputs["Result"], gm_mul1.inputs[0])
        nt.links.new(gm_patch.outputs["Result"], gm_mul1.inputs[1])

        gm_mul2 = nt.nodes.new("ShaderNodeMath")
        gm_mul2.operation = "MULTIPLY"
        nt.links.new(gm_mul1.outputs["Value"], gm_mul2.inputs[0])
        nt.links.new(gm_z.outputs["Result"], gm_mul2.inputs[1])

        gm_e = nt.nodes.new("ShaderNodeMath")
        gm_e.operation = "MULTIPLY"
        gm_e.inputs[1].default_value = 0.14
        nt.links.new(gm_mul2.outputs["Value"], gm_e.inputs[0])

        rim_m = nt.nodes.new("ShaderNodeMath")
        rim_m.operation = "MULTIPLY"
        nt.links.new(lw.outputs["Facing"], rim_m.inputs[0])
        nt.links.new(rev.outputs[0], rim_m.inputs[1])
        rim_s = nt.nodes.new("ShaderNodeMath")
        rim_s.operation = "MULTIPLY"
        rim_s.inputs[1].default_value = 0.12
        nt.links.new(rim_m.outputs["Value"], rim_s.inputs[0])

        em_tot = nt.nodes.new("ShaderNodeMath")
        em_tot.operation = "ADD"
        nt.links.new(rim_s.outputs["Value"], em_tot.inputs[0])
        nt.links.new(gm_e.outputs["Value"], em_tot.inputs[1])
        nt.links.new(em_tot.outputs["Value"], bsdf.inputs["Emission Strength"])

        em_col = nt.nodes.new("ShaderNodeMix")
        em_col.data_type = "RGBA"
        em_col.inputs["A"].default_value = (0.10, 0.18, 0.34, 1.0)
        em_col.inputs["B"].default_value = (0.20, 0.62, 0.56, 1.0)
        gm_col_f = nt.nodes.new("ShaderNodeMapRange")
        gm_col_f.clamp = True
        gm_col_f.inputs["From Min"].default_value = 0.0
        gm_col_f.inputs["From Max"].default_value = 0.06
        nt.links.new(gm_e.outputs["Value"], gm_col_f.inputs["Value"])
        nt.links.new(gm_col_f.outputs["Result"], em_col.inputs["Factor"])
        nt.links.new(em_col.outputs["Result"], bsdf.inputs["Emission Color"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_clay_material(
    name: str,
    base_color=(0.45, 0.48, 0.54, 1.0),
    roughness: float = 0.84,
    metallic: float = 0.0,
    specular: float = 0.24,
    emission_color=None,
    emission_strength: float = 0.0,
    mist_range: tuple[float, float] | None = None,
    mist_color=(0.035, 0.050, 0.075, 1.0),
    mist_strength: float = 0.35,
    wet_waterline: bool = False,
    subsurface: float = 0.0,
    subsurf_radius=(0.24, 0.68, 0.56),
    sheen: float = 0.0,
    sheen_tint=(0.82, 0.88, 0.94, 1.0),
):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    if subsurface > 0.0 and "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = subsurface
        if "Subsurface Scale" in bsdf.inputs:
            bsdf.inputs["Subsurface Scale"].default_value = 0.010
        if "Subsurface Radius" in bsdf.inputs:
            bsdf.inputs["Subsurface Radius"].default_value = subsurf_radius
    if sheen > 0.0 and "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = sheen
        if "Sheen Tint" in bsdf.inputs:
            bsdf.inputs["Sheen Tint"].default_value = sheen_tint

    # v7.3 (blender-skills materials): capillary wet-stone darkening & sheen where ruins emerge from lake z=0!
    if wet_waterline:
        geom = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geom.outputs["Position"], sep.inputs["Vector"])
        n_wet = nt.nodes.new("ShaderNodeTexNoise")
        n_wet.inputs["Scale"].default_value = 0.22
        n_wet.inputs["Detail"].default_value = 4.0
        nt.links.new(geom.outputs["Position"], n_wet.inputs["Vector"])
        n_off = nt.nodes.new("ShaderNodeMapRange")
        n_off.inputs["From Min"].default_value = 0.2
        n_off.inputs["From Max"].default_value = 0.8
        n_off.inputs["To Min"].default_value = -0.55
        n_off.inputs["To Max"].default_value = 0.55
        nt.links.new(n_wet.outputs["Fac"], n_off.inputs["Value"])
        z_jit = nt.nodes.new("ShaderNodeMath")
        z_jit.operation = "ADD"
        nt.links.new(sep.outputs["Z"], z_jit.inputs[0])
        nt.links.new(n_off.outputs["Result"], z_jit.inputs[1])
        dry_f = nt.nodes.new("ShaderNodeMapRange")
        dry_f.interpolation_type = "SMOOTHSTEP"
        dry_f.clamp = True
        dry_f.inputs["From Min"].default_value = -0.15
        dry_f.inputs["From Max"].default_value = 2.65
        dry_f.inputs["To Min"].default_value = 0.0
        dry_f.inputs["To Max"].default_value = 1.0
        nt.links.new(z_jit.outputs["Value"], dry_f.inputs["Value"])
        # Dark wet stone at waterline (0.34x albedo) -> full weathered stone above z=2.65m
        c_wet = nt.nodes.new("ShaderNodeMix")
        c_wet.data_type = "RGBA"
        c_wet.inputs["A"].default_value = (base_color[0] * 0.32, base_color[1] * 0.35, base_color[2] * 0.40, 1.0)
        c_wet.inputs["B"].default_value = base_color
        nt.links.new(dry_f.outputs["Result"], c_wet.inputs["Factor"])
        nt.links.new(c_wet.outputs["Result"], bsdf.inputs["Base Color"])
        r_wet = nt.nodes.new("ShaderNodeMapRange")
        r_wet.clamp = True
        r_wet.inputs["From Min"].default_value = 0.0
        r_wet.inputs["From Max"].default_value = 1.0
        r_wet.inputs["To Min"].default_value = 0.24
        r_wet.inputs["To Max"].default_value = roughness
        nt.links.new(dry_f.outputs["Result"], r_wet.inputs["Value"])
        nt.links.new(r_wet.outputs["Result"], bsdf.inputs["Roughness"])

    if emission_color is not None and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = emission_color
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if mist_range is not None:
        cam_data = nt.nodes.new("ShaderNodeCameraData")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.interpolation_type = "SMOOTHSTEP"
        mr.clamp = True
        mr.inputs["From Min"].default_value = mist_range[0]
        mr.inputs["From Max"].default_value = mist_range[1]
        mr.inputs["To Min"].default_value = 0.0
        mr.inputs["To Max"].default_value = 0.86
        nt.links.new(cam_data.outputs["View Z Depth"], mr.inputs["Value"])
        mist_em = nt.nodes.new("ShaderNodeEmission")
        mist_em.name = "MIST_EM"
        mist_em.inputs["Color"].default_value = mist_color
        mist_em.inputs["Strength"].default_value = mist_strength
        mix_sh = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(mr.outputs["Result"], mix_sh.inputs["Fac"])
        nt.links.new(bsdf.outputs["BSDF"], mix_sh.inputs[1])
        nt.links.new(mist_em.outputs["Emission"], mix_sh.inputs[2])
        nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    else:
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_mirror_lake_material(name: str = "MAT-MirrorLake_Clay"):
    """v7.3 Physical Liquid Mirror-Lake Shader (built via blender-skills: materials + lookdev + lighting):
    Replaces the flat chrome-mirror plane & blue mist band with:
    1. True water Fresnel (IOR 1.333, capped reflectance 0.14..0.58) so reflections are ALWAYS darker & cooler than direct architecture.
    2. Dual-octave horizontally-stretched calm lake micro-ripples (anisotropic X:Y ratio) driven gently by VAL_WATER_TIME.
    3. Distance-graded ripple & roughness modulation: ultra-calm near/mid lake preserves C6c's crystal-clear mirror whale twin,
       while far water (y=60..145m under the sunken sanctuary) softly breaks & attenuates distant architecture reflections into
       poetic shimmering liquid bands instead of a flat Photoshop vertical-flip sticker!"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geom = nt.nodes.new("ShaderNodeNewGeometry")
    sep_pos = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geom.outputs["Position"], sep_pos.inputs["Vector"])

    # Distance factor along lake depth Y (-35m near shore -> +125m sunken sanctuary):
    # Keeps near/mid lake silky calm for the mirror whale while softening far sanctuary reflections!
    far_f = nt.nodes.new("ShaderNodeMapRange")
    far_f.interpolation_type = "SMOOTHSTEP"
    far_f.clamp = True
    far_f.inputs["From Min"].default_value = 15.0
    far_f.inputs["From Max"].default_value = 115.0
    far_f.inputs["To Min"].default_value = 0.0
    far_f.inputs["To Max"].default_value = 1.0
    nt.links.new(sep_pos.outputs["Y"], far_f.inputs["Value"])

    # Animated gentle time offset so ripples breathe organically in the 96s film
    t_val = nt.nodes.new("ShaderNodeValue")
    t_val.name = "VAL_WATER_TIME"
    t_val.outputs[0].default_value = 0.0

    # Horizontally-stretched world coordinates (real perspective water ripples stretch cleanly across X!)
    map_a = nt.nodes.new("ShaderNodeMapping")
    map_a.inputs["Scale"].default_value = (0.032, 0.38, 1.0)
    nt.links.new(geom.outputs["Position"], map_a.inputs["Vector"])
    noise_a = nt.nodes.new("ShaderNodeTexNoise")
    noise_a.noise_dimensions = "4D"
    noise_a.inputs["Scale"].default_value = 2.8
    noise_a.inputs["Detail"].default_value = 4.0
    noise_a.inputs["Roughness"].default_value = 0.54
    nt.links.new(map_a.outputs["Vector"], noise_a.inputs["Vector"])
    t_slow = nt.nodes.new("ShaderNodeMath")
    t_slow.operation = "MULTIPLY"
    t_slow.inputs[1].default_value = 0.045
    nt.links.new(t_val.outputs[0], t_slow.inputs[0])
    nt.links.new(t_slow.outputs["Value"], noise_a.inputs["W"])

    map_b = nt.nodes.new("ShaderNodeMapping")
    map_b.inputs["Scale"].default_value = (0.11, 1.15, 1.0)
    nt.links.new(geom.outputs["Position"], map_b.inputs["Vector"])
    noise_b = nt.nodes.new("ShaderNodeTexNoise")
    noise_b.noise_dimensions = "4D"
    noise_b.inputs["Scale"].default_value = 4.2
    noise_b.inputs["Detail"].default_value = 5.0
    noise_b.inputs["Roughness"].default_value = 0.58
    nt.links.new(map_b.outputs["Vector"], noise_b.inputs["Vector"])
    t_fine = nt.nodes.new("ShaderNodeMath")
    t_fine.operation = "MULTIPLY"
    t_fine.inputs[1].default_value = 0.085
    nt.links.new(t_val.outputs[0], t_fine.inputs[0])
    nt.links.new(t_fine.outputs["Value"], noise_b.inputs["W"])

    # Blend broad calm swells (62%) + fine horizontal night-lake shimmer (38%)
    wave_mix = nt.nodes.new("ShaderNodeMix")
    wave_mix.data_type = "FLOAT"
    wave_mix.inputs["Factor"].default_value = 0.38
    nt.links.new(noise_a.outputs["Fac"], wave_mix.inputs["A"])
    nt.links.new(noise_b.outputs["Fac"], wave_mix.inputs["B"])

    # Bump strength scales smoothly: 0.028 calm near/mid (whale twin crisp) -> 0.145 visible liquid shimmer far!
    bump_str = nt.nodes.new("ShaderNodeMapRange")
    bump_str.clamp = True
    bump_str.inputs["From Min"].default_value = 0.0
    bump_str.inputs["From Max"].default_value = 1.0
    bump_str.inputs["To Min"].default_value = 0.028
    bump_str.inputs["To Max"].default_value = 0.145
    nt.links.new(far_f.outputs["Result"], bump_str.inputs["Value"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.16
    nt.links.new(bump_str.outputs["Result"], bump.inputs["Strength"])
    nt.links.new(wave_mix.outputs["Result"], bump.inputs["Height"])

    # Glossy reflection roughness: 0.024 near/mid (whale twin razor-poetic) -> 0.068 far sanctuary zone!
    rough_dist = nt.nodes.new("ShaderNodeMapRange")
    rough_dist.clamp = True
    rough_dist.inputs["From Min"].default_value = 0.0
    rough_dist.inputs["From Max"].default_value = 1.0
    rough_dist.inputs["To Min"].default_value = 0.024
    rough_dist.inputs["To Max"].default_value = 0.068
    nt.links.new(far_f.outputs["Result"], rough_dist.inputs["Value"])

    # True deep abyssal water absorption (prevents 135kW Cathedral light from painting a diffuse blue stripe on the lake!)
    deep_bsdf = nt.nodes.new("ShaderNodeBsdfDiffuse")
    deep_bsdf.inputs["Color"].default_value = (0.0008, 0.0020, 0.0048, 1.0)
    deep_bsdf.inputs["Roughness"].default_value = 0.75
    nt.links.new(bump.outputs["Normal"], deep_bsdf.inputs["Normal"])

    # Cool indigo-silver tinted water reflection (never 100% pure white chrome mirror!)
    glossy = nt.nodes.new("ShaderNodeBsdfGlossy")
    glossy.inputs["Color"].default_value = (0.52, 0.64, 0.80, 1.0)
    nt.links.new(rough_dist.outputs["Result"], glossy.inputs["Roughness"])
    nt.links.new(bump.outputs["Normal"], glossy.inputs["Normal"])

    # Physical water Fresnel (IOR 1.333) clamped to realistic nocturnal lake reflectance (0.14..0.58)
    # and gently damped in the far sanctuary band (0.76x) so far reflections recede softly into darkness!
    fres = nt.nodes.new("ShaderNodeFresnel")
    fres.inputs["IOR"].default_value = 1.333
    nt.links.new(bump.outputs["Normal"], fres.inputs["Normal"])

    fres_map = nt.nodes.new("ShaderNodeMapRange")
    fres_map.clamp = True
    fres_map.inputs["From Min"].default_value = 0.02
    fres_map.inputs["From Max"].default_value = 0.82
    fres_map.inputs["To Min"].default_value = 0.14
    fres_map.inputs["To Max"].default_value = 0.58
    nt.links.new(fres.outputs["Fac"], fres_map.inputs["Value"])

    far_damp = nt.nodes.new("ShaderNodeMapRange")
    far_damp.clamp = True
    far_damp.inputs["From Min"].default_value = 0.0
    far_damp.inputs["From Max"].default_value = 1.0
    far_damp.inputs["To Min"].default_value = 1.00
    far_damp.inputs["To Max"].default_value = 0.72
    nt.links.new(far_f.outputs["Result"], far_damp.inputs["Value"])

    refl_fac = nt.nodes.new("ShaderNodeMath")
    refl_fac.operation = "MULTIPLY"
    nt.links.new(fres_map.outputs["Result"], refl_fac.inputs[0])
    nt.links.new(far_damp.outputs["Result"], refl_fac.inputs[1])

    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(refl_fac.outputs["Value"], mix_sh.inputs["Fac"])
    nt.links.new(deep_bsdf.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(glossy.outputs["BSDF"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_sunken_city_material(name: str = "MAT-SunkenCity"):
    """v7.8 Classical Limestone Ashlar + Cavity AO Shader (built via blender-skills: materials + lookdev):
    - VAL_CITY_REVEAL = 0.0 (Act 1 & Act 3): pitch abyss (100% invisible).
    - VAL_CITY_REVEAL = 1.0 (Act 2): carved ashlar moonlight limestone with AO crevice darkening across column
      flutes, triglyphs, stoa arches & dome coffers, dark capillary waterline (z = 0..3m), and glossy-ray suppression
      so mirror lake reflections stay subordinate & liquid."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.86
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.24

    rev = nt.nodes.new("ShaderNodeValue")
    rev.name = "VAL_CITY_REVEAL"
    rev.outputs[0].default_value = 0.0

    geom = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geom.outputs["Position"], sep.inputs["Vector"])

    # Subtle weathered classical ashlar stone variation (finer block cadence reinforces colossal Museum-scale monumentality!)
    n_stone = nt.nodes.new("ShaderNodeTexNoise")
    n_stone.inputs["Scale"].default_value = 0.68
    n_stone.inputs["Detail"].default_value = 5.0
    n_stone.inputs["Roughness"].default_value = 0.60
    nt.links.new(geom.outputs["Position"], n_stone.inputs["Vector"])

    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 0.88
    vor.inputs["Randomness"].default_value = 0.22
    nt.links.new(geom.outputs["Position"], vor.inputs["Vector"])

    mortar_mr = nt.nodes.new("ShaderNodeMapRange")
    mortar_mr.interpolation_type = "SMOOTHSTEP"
    mortar_mr.clamp = True
    mortar_mr.inputs["From Min"].default_value = 0.02
    mortar_mr.inputs["From Max"].default_value = 0.14
    mortar_mr.inputs["To Min"].default_value = 0.62
    mortar_mr.inputs["To Max"].default_value = 1.0
    nt.links.new(vor.outputs["Distance"], mortar_mr.inputs["Value"])

    stone_cr = nt.nodes.new("ShaderNodeValToRGB")
    stone_cr.color_ramp.elements[0].position = 0.25
    stone_cr.color_ramp.elements[0].color = (0.072, 0.106, 0.168, 1.0)
    stone_cr.color_ramp.elements[1].position = 0.80
    stone_cr.color_ramp.elements[1].color = (0.132, 0.184, 0.272, 1.0)
    nt.links.new(n_stone.outputs["Fac"], stone_cr.inputs["Fac"])

    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 4
    ao.inputs["Distance"].default_value = 4.2
    nt.links.new(stone_cr.outputs["Color"], ao.inputs["Color"])

    cav_fac = nt.nodes.new("ShaderNodeMath")
    cav_fac.operation = "MULTIPLY"
    nt.links.new(ao.outputs["AO"], cav_fac.inputs[0])
    nt.links.new(mortar_mr.outputs["Result"], cav_fac.inputs[1])

    stone_cav = nt.nodes.new("ShaderNodeMix")
    stone_cav.data_type = "RGBA"
    stone_cav.inputs["A"].default_value = (0.034, 0.052, 0.088, 1.0)
    nt.links.new(cav_fac.outputs["Value"], stone_cav.inputs["Factor"])
    nt.links.new(ao.outputs["Color"], stone_cav.inputs["B"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.08
    nt.links.new(mortar_mr.outputs["Result"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    n_jit = nt.nodes.new("ShaderNodeMapRange")
    n_jit.inputs["From Min"].default_value = 0.2
    n_jit.inputs["From Max"].default_value = 0.8
    n_jit.inputs["To Min"].default_value = -0.65
    n_jit.inputs["To Max"].default_value = 0.65
    nt.links.new(n_stone.outputs["Fac"], n_jit.inputs["Value"])
    z_eff = nt.nodes.new("ShaderNodeMath")
    z_eff.operation = "ADD"
    nt.links.new(sep.outputs["Z"], z_eff.inputs[0])
    nt.links.new(n_jit.outputs["Result"], z_eff.inputs[1])

    dry_mask = nt.nodes.new("ShaderNodeMapRange")
    dry_mask.interpolation_type = "SMOOTHSTEP"
    dry_mask.clamp = True
    dry_mask.inputs["From Min"].default_value = -0.2
    dry_mask.inputs["From Max"].default_value = 3.0
    dry_mask.inputs["To Min"].default_value = 0.0
    dry_mask.inputs["To Max"].default_value = 1.0
    nt.links.new(z_eff.outputs["Value"], dry_mask.inputs["Value"])

    # Glossy ray damping: reflected image of the sunken sanctuary is naturally darker & loses air-mist self-glow!
    lp = nt.nodes.new("ShaderNodeLightPath")
    gloss_scale = nt.nodes.new("ShaderNodeMix")
    gloss_scale.data_type = "FLOAT"
    gloss_scale.inputs["A"].default_value = 1.0
    gloss_scale.inputs["B"].default_value = 0.54
    nt.links.new(lp.outputs["Is Glossy Ray"], gloss_scale.inputs["Factor"])

    # Combine wet-waterline darkening with carved moonlight blue-slate ashlar stone
    wet_albedo = nt.nodes.new("ShaderNodeMix")
    wet_albedo.data_type = "RGBA"
    wet_albedo.inputs["A"].default_value = (0.022, 0.034, 0.056, 1.0)  # dark waterlogged submerged base!
    nt.links.new(stone_cav.outputs["Result"], wet_albedo.inputs["B"])
    nt.links.new(dry_mask.outputs["Result"], wet_albedo.inputs["Factor"])

    # Wet roughness transition (0.24 glistening wet base -> 0.86 dry carved limestone)
    wet_rough = nt.nodes.new("ShaderNodeMapRange")
    wet_rough.clamp = True
    wet_rough.inputs["From Min"].default_value = 0.0
    wet_rough.inputs["From Max"].default_value = 1.0
    wet_rough.inputs["To Min"].default_value = 0.24
    wet_rough.inputs["To Max"].default_value = 0.86
    nt.links.new(dry_mask.outputs["Result"], wet_rough.inputs["Value"])
    nt.links.new(wet_rough.outputs["Result"], bsdf.inputs["Roughness"])

    # Scale revealed albedo by glossy-ray factor so reflections stay subordinate
    refl_albedo = nt.nodes.new("ShaderNodeMix")
    refl_albedo.data_type = "RGBA"
    refl_albedo.blend_type = "MULTIPLY"
    refl_albedo.inputs["Factor"].default_value = 1.0
    nt.links.new(wet_albedo.outputs["Result"], refl_albedo.inputs["A"])
    comb_g = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(gloss_scale.outputs["Result"], comb_g.inputs["Red"])
    nt.links.new(gloss_scale.outputs["Result"], comb_g.inputs["Green"])
    nt.links.new(gloss_scale.outputs["Result"], comb_g.inputs["Blue"])
    nt.links.new(comb_g.outputs["Color"], refl_albedo.inputs["B"])

    col_mix = nt.nodes.new("ShaderNodeMix")
    col_mix.data_type = "RGBA"
    col_mix.inputs["A"].default_value = (0.005, 0.007, 0.012, 1.0)  # invisible pitch abyss in Act 1 & Act 3
    nt.links.new(rev.outputs[0], col_mix.inputs["Factor"])
    nt.links.new(refl_albedo.outputs["Result"], col_mix.inputs["B"])
    nt.links.new(col_mix.outputs["Result"], bsdf.inputs["Base Color"])

    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (0.14, 0.24, 0.40, 1.0)  # subtle cool twilight aerial haze
        em_dry = nt.nodes.new("ShaderNodeMapRange")
        em_dry.clamp = True
        em_dry.inputs["From Min"].default_value = 0.0
        em_dry.inputs["From Max"].default_value = 1.0
        em_dry.inputs["To Min"].default_value = 0.004
        em_dry.inputs["To Max"].default_value = 0.022
        nt.links.new(dry_mask.outputs["Result"], em_dry.inputs["Value"])

        em_gloss = nt.nodes.new("ShaderNodeMix")
        em_gloss.data_type = "FLOAT"
        em_gloss.inputs["A"].default_value = 1.0
        em_gloss.inputs["B"].default_value = 0.16  # air mist does NOT double-glow inside the water reflection!
        nt.links.new(lp.outputs["Is Glossy Ray"], em_gloss.inputs["Factor"])

        em_m1 = nt.nodes.new("ShaderNodeMath")
        em_m1.operation = "MULTIPLY"
        nt.links.new(rev.outputs[0], em_m1.inputs[0])
        nt.links.new(em_dry.outputs["Result"], em_m1.inputs[1])

        em_m2 = nt.nodes.new("ShaderNodeMath")
        em_m2.operation = "MULTIPLY"
        nt.links.new(em_m1.outputs["Value"], em_m2.inputs[0])
        nt.links.new(em_gloss.outputs["Result"], em_m2.inputs[1])
        nt.links.new(em_m2.outputs["Value"], bsdf.inputs["Emission Strength"])

    # Aerial Perspective Depth Mist separating distant y=178m Sanctuary cleanly from y=40m Aqueduct!
    cam_d_city = nt.nodes.new("ShaderNodeCameraData")
    mr_haze = nt.nodes.new("ShaderNodeMapRange")
    mr_haze.interpolation_type = "SMOOTHSTEP"
    mr_haze.clamp = True
    mr_haze.inputs["From Min"].default_value = 135.0
    mr_haze.inputs["From Max"].default_value = 275.0
    mr_haze.inputs["To Min"].default_value = 0.0
    mr_haze.inputs["To Max"].default_value = 0.34
    nt.links.new(cam_d_city.outputs["View Z Depth"], mr_haze.inputs["Value"])

    haze_rev = nt.nodes.new("ShaderNodeMath")
    haze_rev.operation = "MULTIPLY"
    nt.links.new(mr_haze.outputs["Result"], haze_rev.inputs[0])
    nt.links.new(rev.outputs[0], haze_rev.inputs[1])

    haze_gloss = nt.nodes.new("ShaderNodeMath")
    haze_gloss.operation = "MULTIPLY"
    nt.links.new(haze_rev.outputs["Value"], haze_gloss.inputs[0])
    nt.links.new(em_gloss.outputs["Result"] if "Emission Color" in bsdf.inputs else gloss_scale.outputs["Result"], haze_gloss.inputs[1])

    mist_sky = nt.nodes.new("ShaderNodeEmission")
    mist_sky.inputs["Color"].default_value = (0.042, 0.078, 0.142, 1.0)
    mist_sky.inputs["Strength"].default_value = 0.55

    mix_haze = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(haze_gloss.outputs["Value"], mix_haze.inputs["Fac"])
    nt.links.new(bsdf.outputs["BSDF"], mix_haze.inputs[1])
    nt.links.new(mist_sky.outputs["Emission"], mix_haze.inputs[2])
    nt.links.new(mix_haze.outputs["Shader"], out.inputs["Surface"])
    return mat


def _load_tex_image(filename: str, colorspace: str = "sRGB"):
    """Load texture cleanly from local previs textures/ or upstream v7_blender_cycles/textures/."""
    for p in (
        SPEC_PATH.parent / "textures" / filename,
        ROOT / "textures" / filename,
        ROOT.parent / "video-pipeline" / "v7_blender_cycles" / "textures" / filename,
    ):
        if p.exists():
            img = bpy.data.images.load(str(p), check_existing=True)
            try:
                img.colorspace_settings.name = colorspace
            except Exception:
                pass
            return img
    return None


def make_shore_rock_material(name: str = "MAT-Shore_Rock"):
    """v9.0 Wet Karst Basalt Shoreline & Stratified Rock Shelf Shader:
    Blends fractured Voronoi rock strata + anime_cliff_albedo.jpg + crisp 0.04m surface bump +
    dark damp mossy crevices (world/02 & storyboard-v14 R10: dark rock & moss so ONLY white flowers pop!)"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    geom = nt.nodes.new("ShaderNodeNewGeometry")
    sep_p = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geom.outputs["Position"], sep_p.inputs["Vector"])
    sep_n = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geom.outputs["Normal"], sep_n.inputs["Vector"])

    # World-space fracture cracks warped by turbulent rock noise (ZERO geometric tile grids!)
    n_warp = nt.nodes.new("ShaderNodeTexNoise")
    n_warp.inputs["Scale"].default_value = 2.2
    n_warp.inputs["Detail"].default_value = 4.0
    n_warp.inputs["Roughness"].default_value = 0.65
    nt.links.new(geom.outputs["Position"], n_warp.inputs["Vector"])

    warp_vec = nt.nodes.new("ShaderNodeMix")
    warp_vec.data_type = "VECTOR"
    warp_vec.inputs["Factor"].default_value = 0.36
    nt.links.new(geom.outputs["Position"], warp_vec.inputs["A"])
    nt.links.new(n_warp.outputs["Color"], warp_vec.inputs["B"])

    vor_c = nt.nodes.new("ShaderNodeTexVoronoi")
    vor_c.feature = "DISTANCE_TO_EDGE"
    vor_c.inputs["Scale"].default_value = 1.95
    nt.links.new(warp_vec.outputs["Result"], vor_c.inputs["Vector"])

    vor_f = nt.nodes.new("ShaderNodeTexVoronoi")
    vor_f.feature = "DISTANCE_TO_EDGE"
    vor_f.inputs["Scale"].default_value = 7.8
    nt.links.new(warp_vec.outputs["Result"], vor_f.inputs["Vector"])

    n_grain = nt.nodes.new("ShaderNodeTexNoise")
    n_grain.inputs["Scale"].default_value = 14.0
    n_grain.inputs["Detail"].default_value = 6.0
    n_grain.inputs["Roughness"].default_value = 0.68
    nt.links.new(geom.outputs["Position"], n_grain.inputs["Vector"])

    n_moss = nt.nodes.new("ShaderNodeTexNoise")
    n_moss.inputs["Scale"].default_value = 0.95
    n_moss.inputs["Detail"].default_value = 5.0
    n_moss.inputs["Roughness"].default_value = 0.60
    nt.links.new(geom.outputs["Position"], n_moss.inputs["Vector"])

    crack_edge = nt.nodes.new("ShaderNodeMapRange")
    crack_edge.clamp = True
    crack_edge.inputs["From Min"].default_value = 0.008
    crack_edge.inputs["From Max"].default_value = 0.11
    nt.links.new(vor_c.outputs["Distance"], crack_edge.inputs["Value"])

    fine_crack = nt.nodes.new("ShaderNodeMapRange")
    fine_crack.clamp = True
    fine_crack.inputs["From Min"].default_value = 0.006
    fine_crack.inputs["From Max"].default_value = 0.10
    nt.links.new(vor_f.outputs["Distance"], fine_crack.inputs["Value"])

    # Cavity AO + fracture crevice mask
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 8
    ao.inputs["Distance"].default_value = 0.36
    cav = nt.nodes.new("ShaderNodeMath")
    cav.operation = "MULTIPLY"
    nt.links.new(ao.outputs["AO"], cav.inputs[0])
    nt.links.new(crack_edge.outputs["Result"], cav.inputs[1])

    # Optional cliff albedo texture detail projected softly onto world XY
    cliff_img = _load_tex_image("anime_cliff_albedo.jpg", "sRGB")
    rock_col_ramp = nt.nodes.new("ShaderNodeValToRGB")
    rock_col_ramp.color_ramp.elements[0].position = 0.18
    rock_col_ramp.color_ramp.elements[0].color = (0.036, 0.044, 0.060, 1.0)
    rock_col_ramp.color_ramp.elements[1].position = 0.85
    rock_col_ramp.color_ramp.elements[1].color = (0.094, 0.110, 0.136, 1.0)
    nt.links.new(n_grain.outputs["Fac"], rock_col_ramp.inputs["Fac"])

    rock_tex_mix = rock_col_ramp.outputs["Color"]
    cliff_bw = None
    if cliff_img is not None:
        mp_r = nt.nodes.new("ShaderNodeMapping")
        mp_r.inputs["Scale"].default_value = (0.22, 0.22, 0.22)
        nt.links.new(geom.outputs["Position"], mp_r.inputs["Vector"])
        tc_r = nt.nodes.new("ShaderNodeTexImage")
        tc_r.image = cliff_img
        tc_r.projection = "BOX"
        tc_r.projection_blend = 0.35
        nt.links.new(mp_r.outputs["Vector"], tc_r.inputs["Vector"])

        cliff_bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(tc_r.outputs["Color"], cliff_bw.inputs["Color"])

        # Mix world position box projection cleanly with dark basalt tones
        dim_cliff = nt.nodes.new("ShaderNodeMix")
        dim_cliff.data_type = "RGBA"
        dim_cliff.blend_type = "MULTIPLY"
        dim_cliff.inputs["Factor"].default_value = 1.0
        dim_cliff.inputs["B"].default_value = (0.26, 0.29, 0.33, 1.0)
        nt.links.new(tc_r.outputs["Color"], dim_cliff.inputs["A"])

        blend_cliff = nt.nodes.new("ShaderNodeMix")
        blend_cliff.data_type = "RGBA"
        blend_cliff.inputs["Factor"].default_value = 0.56
        nt.links.new(rock_col_ramp.outputs["Color"], blend_cliff.inputs["A"])
        nt.links.new(dim_cliff.outputs["Result"], blend_cliff.inputs["B"])
        rock_tex_mix = blend_cliff.outputs["Result"]

    # Darken cracks & crevices strongly
    rock_cav = nt.nodes.new("ShaderNodeMix")
    rock_cav.data_type = "RGBA"
    rock_cav.inputs["A"].default_value = (0.016, 0.020, 0.028, 1.0)
    nt.links.new(cav.outputs["Value"], rock_cav.inputs["Factor"])
    nt.links.new(rock_tex_mix, rock_cav.inputs["B"])

    # Upward-facing moss growth mask (top flats & damp rock pockets above water z > 0.28m)
    up_mask = nt.nodes.new("ShaderNodeMapRange")
    up_mask.clamp = True
    up_mask.inputs["From Min"].default_value = 0.62
    up_mask.inputs["From Max"].default_value = 0.90
    nt.links.new(sep_n.outputs["Z"], up_mask.inputs["Value"])

    moss_patch = nt.nodes.new("ShaderNodeMapRange")
    moss_patch.interpolation_type = "SMOOTHSTEP"
    moss_patch.clamp = True
    moss_patch.inputs["From Min"].default_value = 0.44
    moss_patch.inputs["From Max"].default_value = 0.68
    nt.links.new(n_moss.outputs["Fac"], moss_patch.inputs["Value"])

    moss_z_ok = nt.nodes.new("ShaderNodeMapRange")
    moss_z_ok.clamp = True
    moss_z_ok.inputs["From Min"].default_value = 0.24
    moss_z_ok.inputs["From Max"].default_value = 0.60
    nt.links.new(sep_p.outputs["Z"], moss_z_ok.inputs["Value"])

    m_fac1 = nt.nodes.new("ShaderNodeMath")
    m_fac1.operation = "MULTIPLY"
    nt.links.new(up_mask.outputs["Result"], m_fac1.inputs[0])
    nt.links.new(moss_patch.outputs["Result"], m_fac1.inputs[1])

    moss_fac = nt.nodes.new("ShaderNodeMath")
    moss_fac.operation = "MULTIPLY"
    nt.links.new(m_fac1.outputs["Value"], moss_fac.inputs[0])
    nt.links.new(moss_z_ok.outputs["Result"], moss_fac.inputs[1])

    col_moss = nt.nodes.new("ShaderNodeMix")
    col_moss.data_type = "RGBA"
    col_moss.inputs["B"].default_value = (0.032, 0.068, 0.044, 1.0)  # deep moody emerald-slate cave moss
    nt.links.new(moss_fac.outputs["Value"], col_moss.inputs["Factor"])
    nt.links.new(rock_cav.outputs["Result"], col_moss.inputs["A"])

    # Wet shoreline capillary darkening below z = 0.48m!
    wet_mask = nt.nodes.new("ShaderNodeMapRange")
    wet_mask.interpolation_type = "SMOOTHSTEP"
    wet_mask.clamp = True
    wet_mask.inputs["From Min"].default_value = 0.02
    wet_mask.inputs["From Max"].default_value = 0.56
    nt.links.new(sep_p.outputs["Z"], wet_mask.inputs["Value"])

    col_wet = nt.nodes.new("ShaderNodeMix")
    col_wet.data_type = "RGBA"
    col_wet.inputs["A"].default_value = (0.014, 0.018, 0.026, 1.0)
    nt.links.new(wet_mask.outputs["Result"], col_wet.inputs["Factor"])
    nt.links.new(col_moss.outputs["Result"], col_wet.inputs["B"])
    nt.links.new(col_wet.outputs["Result"], bsdf.inputs["Base Color"])

    # Roughness: wet shoreline slick 0.16 -> bare stone 0.64 -> velvety moss 0.90!
    r_rock_moss = nt.nodes.new("ShaderNodeMix")
    r_rock_moss.data_type = "FLOAT"
    r_rock_moss.inputs["A"].default_value = 0.62
    r_rock_moss.inputs["B"].default_value = 0.90
    nt.links.new(moss_fac.outputs["Value"], r_rock_moss.inputs["Factor"])

    r_wet = nt.nodes.new("ShaderNodeMix")
    r_wet.data_type = "FLOAT"
    r_wet.inputs["A"].default_value = 0.16
    nt.links.new(wet_mask.outputs["Result"], r_wet.inputs["Factor"])
    nt.links.new(r_rock_moss.outputs["Result"], r_wet.inputs["B"])
    nt.links.new(r_wet.outputs["Result"], bsdf.inputs["Roughness"])

    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.42
    if "Sheen Weight" in bsdf.inputs:
        nt.links.new(moss_fac.outputs["Value"], bsdf.inputs["Sheen Weight"])

    # Tactile warped fracture + cliff strata + fine grit rock bump!
    h_crack = nt.nodes.new("ShaderNodeMath")
    h_crack.operation = "MULTIPLY_ADD"
    h_crack.inputs[1].default_value = 0.38
    nt.links.new(crack_edge.outputs["Result"], h_crack.inputs[0])
    h_f2 = nt.nodes.new("ShaderNodeMath")
    h_f2.operation = "MULTIPLY_ADD"
    h_f2.inputs[1].default_value = 0.22
    nt.links.new(fine_crack.outputs["Result"], h_f2.inputs[0])
    h_g = nt.nodes.new("ShaderNodeMath")
    h_g.operation = "MULTIPLY_ADD" if cliff_bw is not None else "MULTIPLY"
    h_g.inputs[1].default_value = 0.24
    nt.links.new(n_grain.outputs["Fac"], h_g.inputs[0])
    if cliff_bw is not None:
        h_cbw = nt.nodes.new("ShaderNodeMath")
        h_cbw.operation = "MULTIPLY"
        h_cbw.inputs[1].default_value = 0.32
        nt.links.new(cliff_bw.outputs["Val"], h_cbw.inputs[0])
        nt.links.new(h_cbw.outputs["Value"], h_g.inputs[2])
    nt.links.new(h_g.outputs["Value"], h_f2.inputs[2])
    nt.links.new(h_f2.outputs["Value"], h_crack.inputs[2])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.46
    bump.inputs["Distance"].default_value = 0.032
    nt.links.new(h_crack.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_shore_moss_material(name: str = "MAT-ShoreMoss"):
    """Velvety damp cavern moss cushions with microscopic faint glow-moss flecks (world/02)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    geom = nt.nodes.new("ShaderNodeNewGeometry")
    n_vel = nt.nodes.new("ShaderNodeTexNoise")
    n_vel.inputs["Scale"].default_value = 28.0
    n_vel.inputs["Detail"].default_value = 5.0
    nt.links.new(geom.outputs["Position"], n_vel.inputs["Vector"])

    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.25
    cr.color_ramp.elements[0].color = (0.018, 0.044, 0.028, 1.0)
    cr.color_ramp.elements[1].position = 0.78
    cr.color_ramp.elements[1].color = (0.042, 0.088, 0.054, 1.0)
    nt.links.new(n_vel.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.92
    if "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = 0.65
        if "Sheen Tint" in bsdf.inputs:
            bsdf.inputs["Sheen Tint"].default_value = (0.36, 0.58, 0.44, 1.0)
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.08
        if "Subsurface Radius" in bsdf.inputs:
            bsdf.inputs["Subsurface Radius"].default_value = (0.20, 0.62, 0.44)

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.015
    nt.links.new(n_vel.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # Microscopic pinpoint faint bioluminescent spore hint in moss crevices (kept ultra-dim < 0.14 so flowers stay sole glow hero!)
    if "Emission Color" in bsdf.inputs:
        n_sp = nt.nodes.new("ShaderNodeTexVoronoi")
        n_sp.inputs["Scale"].default_value = 24.0
        nt.links.new(geom.outputs["Position"], n_sp.inputs["Vector"])
        sp_m = nt.nodes.new("ShaderNodeMapRange")
        sp_m.clamp = True
        sp_m.inputs["From Min"].default_value = 0.05
        sp_m.inputs["From Max"].default_value = 0.12
        sp_m.inputs["To Min"].default_value = 0.14
        sp_m.inputs["To Max"].default_value = 0.0
        nt.links.new(n_sp.outputs["Distance"], sp_m.inputs["Value"])
        bsdf.inputs["Emission Color"].default_value = (0.28, 0.76, 0.66, 1.0)
        nt.links.new(sp_m.outputs["Result"], bsdf.inputs["Emission Strength"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_calyx_bud_material(name: str = "MAT-CalyxBud"):
    """FL-01 Living Dormant Sepal Sheath: cool frosted sage-jade sepals (NEVER burnt terracotta SSS or wilted brown!)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    tc = nt.nodes.new("ShaderNodeTexCoord")
    n_sep = nt.nodes.new("ShaderNodeTexNoise")
    n_sep.inputs["Scale"].default_value = 22.0
    n_sep.inputs["Detail"].default_value = 4.0
    nt.links.new(tc.outputs["Object"], n_sep.inputs["Vector"])

    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.25
    cr.color_ramp.elements[0].color = (0.072, 0.138, 0.120, 1.0)  # living cool deep sage-jade groove
    cr.color_ramp.elements[1].position = 0.78
    cr.color_ramp.elements[1].color = (0.155, 0.238, 0.208, 1.0)  # frosted pale celadon-jade calyx rib
    nt.links.new(n_sep.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])

    bsdf.inputs["Roughness"].default_value = 0.68
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.22
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.14
        if "Subsurface Scale" in bsdf.inputs:
            bsdf.inputs["Subsurface Scale"].default_value = 0.006
        if "Subsurface Radius" in bsdf.inputs:
            bsdf.inputs["Subsurface Radius"].default_value = (0.22, 0.68, 0.58)
    if "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = 0.62
        if "Sheen Tint" in bsdf.inputs:
            bsdf.inputs["Sheen Tint"].default_value = (0.80, 0.90, 0.88, 1.0)

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(n_sep.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_bud_seam_material(name: str = "MAT-BudInnerSeam"):
    """Subtle non-emissive milky-porcelain inner petal fold peeking softly at closed bud tip seams."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.74, 0.78, 0.82, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.44
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.28
        if "Subsurface Scale" in bsdf.inputs:
            bsdf.inputs["Subsurface Scale"].default_value = 0.008
        if "Subsurface Radius" in bsdf.inputs:
            bsdf.inputs["Subsurface Radius"].default_value = (0.55, 0.72, 0.88)
    if "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = 0.48
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_moon_maria_material(name: str = "MAT-FullMoon"):
    """v9.0 TYPE-MOON Full Moon Shader:
    Crisp Northern Hemisphere lunar maria (moon_sky.jpg UV-disk projection: Sea of Tranquility,
    Mare Crisium & bright southern Tycho ray burst) with deep sapphire-slate sea contrast,
    unclipped ivory-silver highlands under AgX, and a subtle icy lunar limb bloom rim."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")

    tc = nt.nodes.new("ShaderNodeTexCoord")
    moon_img = _load_tex_image("moon_sky.jpg", "sRGB")

    if moon_img is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = moon_img
        tex.extension = "CLIP"
        nt.links.new(tc.outputs["UV"], tex.inputs["Vector"])

        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(tex.outputs["Color"], bw.inputs["Color"])

        # Perceptual contrast ramp: carve sharp maria seas vs bright silver highlands & Tycho rays
        cr = nt.nodes.new("ShaderNodeValToRGB")
        cr.color_ramp.interpolation = "EASE"
        cr.color_ramp.elements[0].position = 0.16
        cr.color_ramp.elements[0].color = (0.20, 0.27, 0.42, 1.0)  # deep TYPE-MOON indigo-slate maria
        e_mid = cr.color_ramp.elements.new(0.48)
        e_mid.color = (0.64, 0.72, 0.85, 1.0)                        # luminous lunar silver-grey plateau
        cr.color_ramp.elements[1].position = 0.86
        cr.color_ramp.elements[1].color = (0.98, 0.99, 1.00, 1.0)  # crisp icy Tycho ray highlight
        nt.links.new(bw.outputs["Val"], cr.inputs["Fac"])

        # Preserve crisp pixel-level crater nuance by blending 35% raw image with TYPE-MOON sapphire-ivory grade
        tint_mix = nt.nodes.new("ShaderNodeMix")
        tint_mix.data_type = "RGBA"
        tint_mix.inputs["Factor"].default_value = 0.65
        nt.links.new(tex.outputs["Color"], tint_mix.inputs["A"])
        nt.links.new(cr.outputs["Color"], tint_mix.inputs["B"])

        # Subtle cool celestial rim glow around outer 5% lunar limb
        lw = nt.nodes.new("ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = 0.28
        inv_f = nt.nodes.new("ShaderNodeMath")
        inv_f.operation = "SUBTRACT"
        inv_f.inputs[0].default_value = 1.0
        nt.links.new(lw.outputs["Facing"], inv_f.inputs[1])

        rim_pow = nt.nodes.new("ShaderNodeMath")
        rim_pow.operation = "POWER"
        rim_pow.inputs[1].default_value = 6.5
        nt.links.new(lw.outputs["Facing"], rim_pow.inputs[0])

        rim_col = nt.nodes.new("ShaderNodeMix")
        rim_col.data_type = "RGBA"
        rim_col.inputs["B"].default_value = (0.82, 0.92, 1.00, 1.0)
        nt.links.new(rim_pow.outputs["Value"], rim_col.inputs["Factor"])
        nt.links.new(tint_mix.outputs["Result"], rim_col.inputs["A"])

        # Base strength 0.82..1.34 (keeps dark seas vivid & Tycho crisp), +0.62 translucent rim corona
        em_base = nt.nodes.new("ShaderNodeMapRange")
        em_base.clamp = True
        em_base.inputs["From Min"].default_value = 0.14
        em_base.inputs["From Max"].default_value = 0.90
        em_base.inputs["To Min"].default_value = 0.78
        em_base.inputs["To Max"].default_value = 1.32
        nt.links.new(bw.outputs["Val"], em_base.inputs["Value"])

        rim_mul = nt.nodes.new("ShaderNodeMath")
        rim_mul.operation = "MULTIPLY"
        rim_mul.inputs[1].default_value = 0.58
        nt.links.new(rim_pow.outputs["Value"], rim_mul.inputs[0])

        em_add = nt.nodes.new("ShaderNodeMath")
        em_add.operation = "ADD"
        nt.links.new(em_base.outputs["Result"], em_add.inputs[0])
        nt.links.new(rim_mul.outputs["Value"], em_add.inputs[1])

        nt.links.new(rim_col.outputs["Result"], em.inputs["Color"])
        nt.links.new(em_add.outputs["Value"], em.inputs["Strength"])
    else:
        em.inputs["Color"].default_value = (0.86, 0.91, 0.98, 1.0)
        em.inputs["Strength"].default_value = 1.15
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def make_moon_corona_material(name: str = "MAT-MoonCorona"):
    """TYPE-MOON atmospheric ice-blue & silver moonlight corona + wispy cloud veil behind GEO-FullMoon."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    elif hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")

    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs["Vector"])

    # UV in [0..1], centered at (0.5, 0.5): compute normalized radius r_norm in [0..1.414]
    dx = nt.nodes.new("ShaderNodeMath")
    dx.operation = "SUBTRACT"
    dx.inputs[1].default_value = 0.5
    nt.links.new(sep.outputs["X"], dx.inputs[0])

    dy = nt.nodes.new("ShaderNodeMath")
    dy.operation = "SUBTRACT"
    dy.inputs[1].default_value = 0.5
    nt.links.new(sep.outputs["Y"], dy.inputs[0])

    dx2 = nt.nodes.new("ShaderNodeMath")
    dx2.operation = "MULTIPLY"
    nt.links.new(dx.outputs["Value"], dx2.inputs[0])
    nt.links.new(dx.outputs["Value"], dx2.inputs[1])

    dy2 = nt.nodes.new("ShaderNodeMath")
    dy2.operation = "MULTIPLY"
    nt.links.new(dy.outputs["Value"], dy2.inputs[0])
    nt.links.new(dy.outputs["Value"], dy2.inputs[1])

    r2 = nt.nodes.new("ShaderNodeMath")
    r2.operation = "ADD"
    nt.links.new(dx2.outputs["Value"], r2.inputs[0])
    nt.links.new(dy2.outputs["Value"], r2.inputs[1])

    r_lin = nt.nodes.new("ShaderNodeMath")
    r_lin.operation = "SQRT"
    nt.links.new(r2.outputs["Value"], r_lin.inputs[0])

    # r_norm = clamp(r_lin / 0.45, 0, 1) -> guaranteed zero well inside quad border!
    rn = nt.nodes.new("ShaderNodeMapRange")
    rn.interpolation_type = "SMOOTHSTEP"
    rn.clamp = True
    rn.inputs["From Min"].default_value = 0.10
    rn.inputs["From Max"].default_value = 0.44
    rn.inputs["To Min"].default_value = 0.0
    rn.inputs["To Max"].default_value = 1.0
    nt.links.new(r_lin.outputs["Value"], rn.inputs["Value"])

    inv_r = nt.nodes.new("ShaderNodeMath")
    inv_r.operation = "SUBTRACT"
    inv_r.inputs[0].default_value = 1.0
    nt.links.new(rn.outputs["Result"], inv_r.inputs[1])

    # Crisp TYPE-MOON inner silver bloom (pow 4.8) + feather-soft wispy night cloud veil (pow 3.0)
    inner_h = nt.nodes.new("ShaderNodeMath")
    inner_h.operation = "POWER"
    inner_h.inputs[1].default_value = 4.8
    nt.links.new(inv_r.outputs["Value"], inner_h.inputs[0])

    outer_h = nt.nodes.new("ShaderNodeMath")
    outer_h.operation = "POWER"
    outer_h.inputs[1].default_value = 3.0
    nt.links.new(inv_r.outputs["Value"], outer_h.inputs[0])

    # Stretched atmospheric night clouds drifting gently horizontally across the corona
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.6, 5.8, 1.0)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    n_wisp = nt.nodes.new("ShaderNodeTexNoise")
    n_wisp.inputs["Scale"].default_value = 2.6
    n_wisp.inputs["Detail"].default_value = 4.0
    n_wisp.inputs["Roughness"].default_value = 0.58
    nt.links.new(mp.outputs["Vector"], n_wisp.inputs["Vector"])

    wisp_mod = nt.nodes.new("ShaderNodeMapRange")
    wisp_mod.clamp = True
    wisp_mod.inputs["From Min"].default_value = 0.34
    wisp_mod.inputs["From Max"].default_value = 0.72
    wisp_mod.inputs["To Min"].default_value = 0.36
    wisp_mod.inputs["To Max"].default_value = 1.0
    nt.links.new(n_wisp.outputs["Fac"], wisp_mod.inputs["Value"])

    outer_w = nt.nodes.new("ShaderNodeMath")
    outer_w.operation = "MULTIPLY"
    nt.links.new(outer_h.outputs["Value"], outer_w.inputs[0])
    nt.links.new(wisp_mod.outputs["Result"], outer_w.inputs[1])

    corona_mix = nt.nodes.new("ShaderNodeMath")
    corona_mix.operation = "MULTIPLY_ADD"
    corona_mix.inputs[1].default_value = 0.55
    nt.links.new(inner_h.outputs["Value"], corona_mix.inputs[0])
    m_out = nt.nodes.new("ShaderNodeMath")
    m_out.operation = "MULTIPLY"
    m_out.inputs[1].default_value = 0.16
    nt.links.new(outer_w.outputs["Value"], m_out.inputs[0])
    nt.links.new(m_out.outputs["Value"], corona_mix.inputs[2])

    alpha_cl = nt.nodes.new("ShaderNodeClamp")
    nt.links.new(corona_mix.outputs["Value"], alpha_cl.inputs["Value"])

    # Glacial cyan-indigo outer veil -> pale silver inner ring
    c_mix = nt.nodes.new("ShaderNodeMix")
    c_mix.data_type = "RGBA"
    c_mix.inputs["A"].default_value = (0.36, 0.58, 0.94, 1.0)
    c_mix.inputs["B"].default_value = (0.86, 0.93, 1.00, 1.0)
    nt.links.new(inner_h.outputs["Value"], c_mix.inputs["Factor"])

    nt.links.new(c_mix.outputs["Result"], em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.15

    nt.links.new(alpha_cl.outputs["Result"], mix_sh.inputs["Fac"])
    nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(em.outputs["Emission"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_whale_dissolve_material(name: str = "MAT-Whale_Clay", aurora_mode: str = "sky_veil"):
    """v9.0 Authentic Cetacean Leviathan Skin Shader:
    Blends mottled painterly whale_skin_albedo.jpg (UV-locked so zero swimming drift!) +
    2-scale dermal relief bump + deep 0.62m cavity AO carving eyelid folds, mouth cleft & 20 pleats +
    head-to-tail moonlight ignition wave (VAL_IGNITE) + tail-to-head dissolve (VAL_DISSOLVE)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    elif hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.48

    glow_val = nt.nodes.new("ShaderNodeValue")
    glow_val.name = "VAL_GLOW"
    glow_val.outputs[0].default_value = 0.0

    ignite_val = nt.nodes.new("ShaderNodeValue")
    ignite_val.name = "VAL_IGNITE"
    ignite_val.outputs[0].default_value = 0.0

    dissolve_val = nt.nodes.new("ShaderNodeValue")
    dissolve_val.name = "VAL_DISSOLVE"
    dissolve_val.outputs[0].default_value = 0.0

    whale_t = nt.nodes.new("ShaderNodeValue")
    whale_t.name = "VAL_WHALE_TIME"
    whale_t.outputs[0].default_value = 0.0

    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tex_coord.outputs["Object"], sep.inputs["Vector"])

    # Anatomical UV-locked mottled whale skin texture (no sliding during swim deform!)
    skin_img = _load_tex_image("whale_skin_albedo.jpg", "sRGB")
    skin_tex = None
    skin_bw = None
    if skin_img is not None:
        skin_tex = nt.nodes.new("ShaderNodeTexImage")
        skin_tex.image = skin_img
        nt.links.new(tex_coord.outputs["UV"], skin_tex.inputs["Vector"])
        skin_bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(skin_tex.outputs["Color"], skin_bw.inputs["Color"])

    map_u = nt.nodes.new("ShaderNodeMapRange")
    map_u.inputs["From Min"].default_value = -13.5
    map_u.inputs["From Max"].default_value = 12.2
    map_u.inputs["To Min"].default_value = 0.0
    map_u.inputs["To Max"].default_value = 1.0
    nt.links.new(sep.outputs["Y"], map_u.inputs["Value"])

    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.42
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.55
    nt.links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])

    n_center = nt.nodes.new("ShaderNodeMath")
    n_center.operation = "SUBTRACT"
    n_center.inputs[1].default_value = 0.5
    nt.links.new(noise.outputs["Fac"], n_center.inputs[0])

    n_amp = nt.nodes.new("ShaderNodeMath")
    n_amp.operation = "MULTIPLY"
    n_amp.inputs[1].default_value = 0.24
    nt.links.new(n_center.outputs[0], n_amp.inputs[0])

    u_misty = nt.nodes.new("ShaderNodeMath")
    u_misty.operation = "ADD"
    nt.links.new(map_u.outputs["Result"], u_misty.inputs[0])
    nt.links.new(n_amp.outputs[0], u_misty.inputs[1])

    # Head-to-tail moonlight ignition mask: u_head = 1 - map_u (0 at nose, 1 at tail)
    u_head = nt.nodes.new("ShaderNodeMath")
    u_head.operation = "SUBTRACT"
    u_head.inputs[0].default_value = 1.0
    nt.links.new(map_u.outputs["Result"], u_head.inputs[1])

    n_ig = nt.nodes.new("ShaderNodeMath")
    n_ig.operation = "MULTIPLY"
    n_ig.inputs[1].default_value = 0.11
    nt.links.new(n_center.outputs[0], n_ig.inputs[0])

    u_head_n = nt.nodes.new("ShaderNodeMath")
    u_head_n.operation = "ADD"
    nt.links.new(u_head.outputs[0], u_head_n.inputs[0])
    nt.links.new(n_ig.outputs[0], u_head_n.inputs[1])

    map_ig = nt.nodes.new("ShaderNodeMapRange")
    map_ig.inputs["From Min"].default_value = 0.0
    map_ig.inputs["From Max"].default_value = 1.0
    map_ig.inputs["To Min"].default_value = -0.22
    map_ig.inputs["To Max"].default_value = 1.24
    nt.links.new(ignite_val.outputs[0], map_ig.inputs["Value"])

    ig_lo = nt.nodes.new("ShaderNodeMath")
    ig_lo.operation = "SUBTRACT"
    ig_lo.inputs[1].default_value = 0.14
    nt.links.new(map_ig.outputs["Result"], ig_lo.inputs[0])

    ig_hi = nt.nodes.new("ShaderNodeMath")
    ig_hi.operation = "ADD"
    ig_hi.inputs[1].default_value = 0.14
    nt.links.new(map_ig.outputs["Result"], ig_hi.inputs[0])

    ig_raw = nt.nodes.new("ShaderNodeMapRange")
    ig_raw.interpolation_type = "SMOOTHSTEP"
    ig_raw.clamp = True
    nt.links.new(u_head_n.outputs[0], ig_raw.inputs["Value"])
    nt.links.new(ig_lo.outputs[0], ig_raw.inputs["From Min"])
    nt.links.new(ig_hi.outputs[0], ig_raw.inputs["From Max"])

    lit_fac = nt.nodes.new("ShaderNodeMath")
    lit_fac.operation = "SUBTRACT"
    lit_fac.inputs[0].default_value = 1.0
    nt.links.new(ig_raw.outputs["Result"], lit_fac.inputs[1])

    # Crisp micro-carved marine pearl finish + wet dermal sheen (coat preserves eye folds & mouthline!)
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.10
        if "Subsurface Scale" in bsdf.inputs:
            bsdf.inputs["Subsurface Scale"].default_value = 0.035
        if "Subsurface Radius" in bsdf.inputs:
            bsdf.inputs["Subsurface Radius"].default_value = (0.48, 0.68, 0.88)
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.40
        bsdf.inputs["Coat Roughness"].default_value = 0.09

    # Multi-scale dermal skin relief + roughness variation (never flat vinyl!)
    n_skin = nt.nodes.new("ShaderNodeTexNoise")
    n_skin.inputs["Scale"].default_value = 1.8
    n_skin.inputs["Detail"].default_value = 6.0
    n_skin.inputs["Roughness"].default_value = 0.62
    mp_skin = nt.nodes.new("ShaderNodeMapping")
    mp_skin.inputs["Scale"].default_value = (1.8, 0.45, 1.8)
    nt.links.new(tex_coord.outputs["UV"], mp_skin.inputs["Vector"])
    nt.links.new(mp_skin.outputs["Vector"], n_skin.inputs["Vector"])

    # Tactile Bump from whale_skin_albedo.jpg + dermal ripples
    bump_h = n_skin.outputs["Fac"]
    if skin_bw is not None:
        bm_mix = nt.nodes.new("ShaderNodeMix")
        bm_mix.data_type = "FLOAT"
        bm_mix.inputs["Factor"].default_value = 0.62
        nt.links.new(n_skin.outputs["Fac"], bm_mix.inputs["A"])
        nt.links.new(skin_bw.outputs["Val"], bm_mix.inputs["B"])
        bump_h = bm_mix.outputs["Result"]

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.24
    bump.inputs["Distance"].default_value = 0.045
    nt.links.new(bump_h, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    rough_mr = nt.nodes.new("ShaderNodeMapRange")
    rough_mr.clamp = True
    rough_mr.inputs["From Min"].default_value = 0.20
    rough_mr.inputs["From Max"].default_value = 0.80
    rough_mr.inputs["To Min"].default_value = 0.22
    rough_mr.inputs["To Max"].default_value = 0.50
    nt.links.new(n_skin.outputs["Fac"], rough_mr.inputs["Value"])
    nt.links.new(rough_mr.outputs["Result"], bsdf.inputs["Roughness"])

    # Deep 0.65m Ambient Occlusion cavity shading carving out eyelid folds, mouth gape, blowhole & pleats!
    ao_w = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao_w.samples = 8
    ao_w.inputs["Distance"].default_value = 0.65
    ao_pow = nt.nodes.new("ShaderNodeMath")
    ao_pow.operation = "POWER"
    ao_pow.inputs[1].default_value = 2.40
    nt.links.new(ao_w.outputs["AO"], ao_pow.inputs[0])
    ao_mod = nt.nodes.new("ShaderNodeMapRange")
    ao_mod.clamp = True
    ao_mod.inputs["From Min"].default_value = 0.0
    ao_mod.inputs["From Max"].default_value = 1.0
    ao_mod.inputs["To Min"].default_value = 0.10
    ao_mod.inputs["To Max"].default_value = 1.00
    nt.links.new(ao_pow.outputs["Value"], ao_mod.inputs["Value"])

    # Brilliant silver ignition wave crest right at the moving frontier
    crest_mul = nt.nodes.new("ShaderNodeMath")
    crest_mul.operation = "MULTIPLY"
    nt.links.new(lit_fac.outputs[0], crest_mul.inputs[0])
    nt.links.new(ig_raw.outputs["Result"], crest_mul.inputs[1])

    crest_em = nt.nodes.new("ShaderNodeMath")
    crest_em.operation = "MULTIPLY"
    crest_em.inputs[1].default_value = 8.4
    nt.links.new(crest_mul.outputs[0], crest_em.inputs[0])

    # Thin-film pearl-opal iridescence combined with organic cetacean skin countershading
    canon_opal = (aurora_mode == "canon_starry_opal")
    starry_mode = (aurora_mode in ("starry_aurora_whale", "canon_starry_opal"))
    lw_opal = nt.nodes.new("ShaderNodeLayerWeight")
    lw_opal.inputs["Blend"].default_value = 0.56 if canon_opal else (0.52 if starry_mode else 0.48)

    mp_op = nt.nodes.new("ShaderNodeMapping")
    mp_op.inputs["Scale"].default_value = (0.20, 0.12, 0.28) if starry_mode else (1.0, 1.0, 1.0)
    nt.links.new(tex_coord.outputs["Object"], mp_op.inputs["Vector"])

    n_opal = nt.nodes.new("ShaderNodeTexNoise")
    n_opal.noise_dimensions = "4D"
    n_opal.inputs["Scale"].default_value = 1.45 if starry_mode else 0.11
    n_opal.inputs["Detail"].default_value = 3.0
    n_opal.inputs["Roughness"].default_value = 0.45
    nt.links.new(mp_op.outputs["Vector"], n_opal.inputs["Vector"])
    wt_mul = nt.nodes.new("ShaderNodeMath")
    wt_mul.operation = "MULTIPLY"
    wt_mul.inputs[1].default_value = 0.08 if canon_opal else 0.09
    nt.links.new(whale_t.outputs[0], wt_mul.inputs[0])
    nt.links.new(wt_mul.outputs["Value"], n_opal.inputs["W"])

    opal_m1 = nt.nodes.new("ShaderNodeMix")
    opal_m1.data_type = "FLOAT"
    opal_m1.inputs["Factor"].default_value = 0.16 if canon_opal else (0.44 if starry_mode else 0.40)
    nt.links.new(lw_opal.outputs["Facing"], opal_m1.inputs["A"])
    nt.links.new(map_u.outputs["Result"], opal_m1.inputs["B"])

    opal_fac = nt.nodes.new("ShaderNodeMix")
    opal_fac.data_type = "FLOAT"
    opal_fac.inputs["Factor"].default_value = 0.58 if canon_opal else (0.48 if starry_mode else 0.28)
    nt.links.new(opal_m1.outputs["Result"], opal_fac.inputs["A"])
    nt.links.new(n_opal.outputs["Fac"], opal_fac.inputs["B"])

    cr_opal = nt.nodes.new("ShaderNodeValToRGB")
    cr_opal.color_ramp.interpolation = "EASE"
    if canon_opal:
        cr_opal.color_ramp.elements[0].position = 0.20
        cr_opal.color_ramp.elements[0].color = (0.34, 0.72, 0.98, 1.0)
        e1 = cr_opal.color_ramp.elements.new(0.36)
        e1.color = (0.58, 0.86, 0.94, 1.0)
        e2 = cr_opal.color_ramp.elements.new(0.50)
        e2.color = (0.86, 0.90, 0.96, 1.0)
        e3 = cr_opal.color_ramp.elements.new(0.66)
        e3.color = (0.68, 0.62, 0.96, 1.0)
        cr_opal.color_ramp.elements[1].position = 0.82
        cr_opal.color_ramp.elements[1].color = (0.96, 0.58, 0.74, 1.0)
    elif starry_mode:
        cr_opal.color_ramp.elements[0].position = 0.18
        cr_opal.color_ramp.elements[0].color = (0.05, 0.56, 1.00, 1.0)
        e1 = cr_opal.color_ramp.elements.new(0.35)
        e1.color = (0.12, 0.88, 0.80, 1.0)
        e2 = cr_opal.color_ramp.elements.new(0.50)
        e2.color = (0.90, 0.96, 1.00, 1.0)
        e3 = cr_opal.color_ramp.elements.new(0.66)
        e3.color = (0.48, 0.24, 1.00, 1.0)
        cr_opal.color_ramp.elements[1].position = 0.82
        cr_opal.color_ramp.elements[1].color = (1.00, 0.20, 0.58, 1.0)
    else:
        cr_opal.color_ramp.elements[0].position = 0.14
        cr_opal.color_ramp.elements[0].color = (0.72, 0.90, 1.00, 1.0)
        e1 = cr_opal.color_ramp.elements.new(0.38)
        e1.color = (0.20, 0.72, 1.00, 1.0)
        e2 = cr_opal.color_ramp.elements.new(0.62)
        e2.color = (0.64, 0.42, 0.99, 1.0)
        cr_opal.color_ramp.elements[1].position = 0.84
        cr_opal.color_ramp.elements[1].color = (1.00, 0.34, 0.68, 1.0)
    nt.links.new(opal_fac.outputs["Result"], cr_opal.inputs["Fac"])

    # Blend UV skin mottling into lit pearl-opal albedo + Act 1 dark sapphire-slate skin!
    lit_base_src = cr_opal.outputs["Color"]
    dark_col_src = None
    if skin_tex is not None:
        skin_lit = nt.nodes.new("ShaderNodeMix")
        skin_lit.data_type = "RGBA"
        skin_lit.blend_type = "MULTIPLY"
        skin_lit.inputs["Factor"].default_value = 0.68
        nt.links.new(cr_opal.outputs["Color"], skin_lit.inputs["A"])
        nt.links.new(skin_tex.outputs["Color"], skin_lit.inputs["B"])
        lit_base_src = skin_lit.outputs["Result"]

        dark_col_node = nt.nodes.new("ShaderNodeMix")
        dark_col_node.data_type = "RGBA"
        dark_col_node.blend_type = "MULTIPLY"
        dark_col_node.inputs["Factor"].default_value = 1.0
        dark_col_node.inputs["B"].default_value = (0.14, 0.17, 0.24, 1.0)
        nt.links.new(skin_tex.outputs["Color"], dark_col_node.inputs["A"])
        dark_col_src = dark_col_node.outputs["Result"]

    albedo_dim = nt.nodes.new("ShaderNodeMix")
    albedo_dim.data_type = "RGBA"
    albedo_dim.blend_type = "MULTIPLY"
    albedo_dim.inputs["Factor"].default_value = 1.0
    dim_v = 0.22 if (aurora_mode == "starry_aurora_whale") else 0.24
    albedo_dim.inputs["B"].default_value = (dim_v, dim_v, dim_v + 0.02, 1.0)
    nt.links.new(lit_base_src, albedo_dim.inputs["A"])

    mix_lit_state = nt.nodes.new("ShaderNodeMix")
    mix_lit_state.data_type = "RGBA"
    if dark_col_src is not None:
        nt.links.new(dark_col_src, mix_lit_state.inputs["A"])
    else:
        mix_lit_state.inputs["A"].default_value = (0.06, 0.08, 0.12, 1.0)
    nt.links.new(lit_fac.outputs[0], mix_lit_state.inputs["Factor"])
    nt.links.new(albedo_dim.outputs["Result"], mix_lit_state.inputs["B"])

    # Cavity AO sculpts both Act 1 dark eye/jaw folds AND Act 2 pearlescent skin!
    albedo_ao = nt.nodes.new("ShaderNodeMix")
    albedo_ao.data_type = "RGBA"
    albedo_ao.blend_type = "MULTIPLY"
    albedo_ao.inputs["Factor"].default_value = 1.0
    nt.links.new(mix_lit_state.outputs["Result"], albedo_ao.inputs["A"])
    comb_ao = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(ao_mod.outputs["Result"], comb_ao.inputs["Red"])
    nt.links.new(ao_mod.outputs["Result"], comb_ao.inputs["Green"])
    nt.links.new(ao_mod.outputs["Result"], comb_ao.inputs["Blue"])
    nt.links.new(comb_ao.outputs["Color"], albedo_ao.inputs["B"])
    nt.links.new(albedo_ao.outputs["Result"], bsdf.inputs["Base Color"])

    # Dissolve opacity [0..1]
    map_d = nt.nodes.new("ShaderNodeMapRange")
    map_d.inputs["From Min"].default_value = 0.0
    map_d.inputs["From Max"].default_value = 1.0
    map_d.inputs["To Min"].default_value = -0.24
    map_d.inputs["To Max"].default_value = 1.26
    nt.links.new(dissolve_val.outputs[0], map_d.inputs["Value"])

    sub_lo = nt.nodes.new("ShaderNodeMath")
    sub_lo.operation = "SUBTRACT"
    sub_lo.inputs[1].default_value = 0.16
    nt.links.new(map_d.outputs["Result"], sub_lo.inputs[0])

    add_hi = nt.nodes.new("ShaderNodeMath")
    add_hi.operation = "ADD"
    add_hi.inputs[1].default_value = 0.08
    nt.links.new(map_d.outputs["Result"], add_hi.inputs[0])

    smooth_op = nt.nodes.new("ShaderNodeMapRange")
    smooth_op.interpolation_type = "SMOOTHSTEP"
    smooth_op.clamp = True
    nt.links.new(u_misty.outputs[0], smooth_op.inputs["Value"])
    nt.links.new(sub_lo.outputs[0], smooth_op.inputs["From Min"])
    nt.links.new(add_hi.outputs[0], smooth_op.inputs["From Max"])

    if "Emission Color" in bsdf.inputs:
        em_col_src = cr_opal.outputs["Color"]
        if skin_bw is not None:
            em_tint = nt.nodes.new("ShaderNodeMix")
            em_tint.data_type = "RGBA"
            em_tint.blend_type = "MULTIPLY"
            em_tint.inputs["Factor"].default_value = 0.45
            nt.links.new(cr_opal.outputs["Color"], em_tint.inputs["A"])
            comb_sk = nt.nodes.new("ShaderNodeCombineColor")
            sk_lift = nt.nodes.new("ShaderNodeMapRange")
            sk_lift.clamp = True
            sk_lift.inputs["From Min"].default_value = 0.0
            sk_lift.inputs["From Max"].default_value = 1.0
            sk_lift.inputs["To Min"].default_value = 0.55
            sk_lift.inputs["To Max"].default_value = 1.15
            nt.links.new(skin_bw.outputs["Val"], sk_lift.inputs["Value"])
            nt.links.new(sk_lift.outputs["Result"], comb_sk.inputs["Red"])
            nt.links.new(sk_lift.outputs["Result"], comb_sk.inputs["Green"])
            nt.links.new(sk_lift.outputs["Result"], comb_sk.inputs["Blue"])
            nt.links.new(comb_sk.outputs["Color"], em_tint.inputs["B"])
            em_col_src = em_tint.outputs["Result"]

        nt.links.new(em_col_src, bsdf.inputs["Emission Color"])
        em_base = nt.nodes.new("ShaderNodeMath")
        em_base.operation = "MULTIPLY_ADD"
        em_base.inputs[1].default_value = 0.44 if canon_opal else (0.64 if starry_mode else 0.46)
        em_base.inputs[2].default_value = 0.032 if canon_opal else (0.18 if starry_mode else 0.24)
        nt.links.new(lw_opal.outputs["Facing"], em_base.inputs[0])

        em_ao = nt.nodes.new("ShaderNodeMath")
        em_ao.operation = "MULTIPLY"
        nt.links.new(em_base.outputs[0], em_ao.inputs[0])
        nt.links.new(ao_mod.outputs["Result"], em_ao.inputs[1])

        mul_em = nt.nodes.new("ShaderNodeMath")
        mul_em.operation = "MULTIPLY"
        nt.links.new(lit_fac.outputs[0], mul_em.inputs[0])
        nt.links.new(em_ao.outputs["Value"], mul_em.inputs[1])

        inv_op = nt.nodes.new("ShaderNodeMath")
        inv_op.operation = "SUBTRACT"
        inv_op.inputs[0].default_value = 1.0
        nt.links.new(smooth_op.outputs["Result"], inv_op.inputs[1])

        edge_em = nt.nodes.new("ShaderNodeMath")
        edge_em.operation = "MULTIPLY"
        edge_em.inputs[1].default_value = 1.65
        nt.links.new(inv_op.outputs[0], edge_em.inputs[0])

        d_sq = nt.nodes.new("ShaderNodeMath")
        d_sq.operation = "POWER"
        d_sq.inputs[1].default_value = 2.0
        nt.links.new(dissolve_val.outputs[0], d_sq.inputs[0])

        mul_lunar = nt.nodes.new("ShaderNodeMath")
        mul_lunar.operation = "MULTIPLY"
        mul_lunar.inputs[1].default_value = 1.40
        nt.links.new(d_sq.outputs[0], mul_lunar.inputs[0])

        add1 = nt.nodes.new("ShaderNodeMath")
        add1.operation = "ADD"
        nt.links.new(mul_em.outputs[0], add1.inputs[0])
        nt.links.new(crest_em.outputs[0], add1.inputs[1])

        add2 = nt.nodes.new("ShaderNodeMath")
        add2.operation = "ADD"
        nt.links.new(add1.outputs[0], add2.inputs[0])
        nt.links.new(edge_em.outputs[0], add2.inputs[1])

        add3 = nt.nodes.new("ShaderNodeMath")
        add3.operation = "ADD"
        nt.links.new(add2.outputs[0], add3.inputs[0])
        nt.links.new(mul_lunar.outputs[0], add3.inputs[1])
        nt.links.new(add3.outputs[0], bsdf.inputs["Emission Strength"])

    nt.links.new(smooth_op.outputs["Result"], mix_sh.inputs["Fac"])
    nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(bsdf.outputs["BSDF"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_whale_eye_material(name: str = "MAT-Whale_Eye"):
    """v9.0 Expressive Cetacean Leviathan Eye (CUT06_KEY_eye.png):
    Object-space radial gaze mapping (100% immune to UV seams/white stop bugs!):
    Deep obsidian pupil -> striated oceanic sapphire-slate iris -> dark moist sclera -> wet corneal clearcoat."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    elif hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    # Normalize eyeball local (X depth=0.195, Y fore-aft=0.275, Z height=0.175) so Y/Z = radial iris gaze coords!
    mp.inputs["Scale"].default_value = (0.0, 1.0 / 0.275, 1.0 / 0.175)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(mp.outputs["Vector"], sep.inputs["Vector"])

    y2 = nt.nodes.new("ShaderNodeMath")
    y2.operation = "MULTIPLY"
    nt.links.new(sep.outputs["Y"], y2.inputs[0])
    nt.links.new(sep.outputs["Y"], y2.inputs[1])

    z2 = nt.nodes.new("ShaderNodeMath")
    z2.operation = "MULTIPLY"
    nt.links.new(sep.outputs["Z"], z2.inputs[0])
    nt.links.new(sep.outputs["Z"], z2.inputs[1])

    r2 = nt.nodes.new("ShaderNodeMath")
    r2.operation = "ADD"
    nt.links.new(y2.outputs["Value"], r2.inputs[0])
    nt.links.new(z2.outputs["Value"], r2.inputs[1])

    r_eye = nt.nodes.new("ShaderNodeMath")
    r_eye.operation = "SQRT"
    nt.links.new(r2.outputs["Value"], r_eye.inputs[0])

    # Delicate iris fiber texture
    n_ir = nt.nodes.new("ShaderNodeTexNoise")
    n_ir.inputs["Scale"].default_value = 14.0
    n_ir.inputs["Detail"].default_value = 4.0
    nt.links.new(mp.outputs["Vector"], n_ir.inputs["Vector"])

    n_off = nt.nodes.new("ShaderNodeMapRange")
    n_off.inputs["From Min"].default_value = 0.0
    n_off.inputs["From Max"].default_value = 1.0
    n_off.inputs["To Min"].default_value = -0.045
    n_off.inputs["To Max"].default_value = 0.045
    nt.links.new(n_ir.outputs["Fac"], n_off.inputs["Value"])

    r_mod = nt.nodes.new("ShaderNodeMath")
    r_mod.operation = "ADD"
    nt.links.new(r_eye.outputs["Value"], r_mod.inputs[0])
    nt.links.new(n_off.outputs["Result"], r_mod.inputs[1])

    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.interpolation = "EASE"
    # Set endpoints [0] & [1] FIRST so NO default white stop remains at 1.0!
    cr.color_ramp.elements[0].position = 0.24
    cr.color_ramp.elements[0].color = (0.002, 0.003, 0.005, 1.0)  # deep velvet pupil center
    cr.color_ramp.elements[1].position = 0.72
    cr.color_ramp.elements[1].color = (0.014, 0.020, 0.032, 1.0)  # damp dark slate-obsidian whale sclera
    e_ir = cr.color_ramp.elements.new(0.35)
    e_ir.color = (0.040, 0.088, 0.168, 1.0)                         # deep oceanic sapphire-cerulean iris
    e_ir2 = cr.color_ramp.elements.new(0.50)
    e_ir2.color = (0.020, 0.046, 0.095, 1.0)                        # outer iris navy
    e_lim = cr.color_ramp.elements.new(0.60)
    e_lim.color = (0.006, 0.010, 0.018, 1.0)                        # dark limbus ring
    nt.links.new(r_mod.outputs["Value"], cr.inputs["Fac"])

    nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.02
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat Roughness"].default_value = 0.01
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.96

    alpha_val = nt.nodes.new("ShaderNodeValue")
    alpha_val.name = "VAL_EYE_ALPHA"
    alpha_val.outputs[0].default_value = 1.0
    nt.links.new(alpha_val.outputs[0], mix_sh.inputs["Fac"])
    nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(bsdf.outputs["BSDF"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    return mat


def _load_petal_image():
    """Load canonical veined milky-white & pale champagne-gold FL-01 petal texture if present."""
    return _load_tex_image("petal_rgba.png", "sRGB")


def make_bloom_petal_material(name: str = "MAT-Kousetsuka_Petal", always_open: bool = False):
    """v7.9 Canon FL-01 v0.8 Veined Petal Material:
    - Uses canonical petal_rgba.png veined creamy-white lamina tapering to pale champagne-gold throat!
    - STRICT FL-01 RULE: attached flowers are 100% NON-EMISSIVE (Emission = 0.0), illuminated organically
      by localized P0 moonlight (C1/C8) and Whale Shore Glow (C5b/C6a) via realistic Subsurface + Translucent backlighting!"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.44
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.28
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.42
        if "Subsurface Scale" in bsdf.inputs:
            bsdf.inputs["Subsurface Scale"].default_value = 0.015

    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep_uv = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep_uv.inputs["Vector"])
    cr_f = nt.nodes.new("ShaderNodeValToRGB")
    cr_f.color_ramp.elements[0].position = 0.14
    cr_f.color_ramp.elements[0].color = (0.94, 0.78, 0.44, 1.0)
    cr_f.color_ramp.elements[1].position = 0.40
    cr_f.color_ramp.elements[1].color = (0.95, 0.96, 0.98, 1.0)
    nt.links.new(sep_uv.outputs["Y"], cr_f.inputs["Fac"])

    img = _load_petal_image()
    if img is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.extension = "EXTEND"
        nt.links.new(tc.outputs["UV"], tex.inputs["Vector"])
        # Eliminate premultiplied black edge halo: blend clean milky-ivory ramp wherever Alpha < 0.96!
        mr_a = nt.nodes.new("ShaderNodeMapRange")
        mr_a.clamp = True
        mr_a.inputs["From Min"].default_value = 0.70
        mr_a.inputs["From Max"].default_value = 0.96
        nt.links.new(tex.outputs["Alpha"], mr_a.inputs["Value"])
        mix_tex = nt.nodes.new("ShaderNodeMix")
        mix_tex.data_type = "RGBA"
        nt.links.new(mr_a.outputs["Result"], mix_tex.inputs["Factor"])
        nt.links.new(cr_f.outputs["Color"], mix_tex.inputs["A"])
        nt.links.new(tex.outputs["Color"], mix_tex.inputs["B"])
        petal_col_out = mix_tex.outputs["Result"]
    else:
        petal_col_out = cr_f.outputs["Color"]

    if always_open:
        nt.links.new(petal_col_out, bsdf.inputs["Base Color"])
        col_src = petal_col_out
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 0.0
    else:
        obj_info = nt.nodes.new("ShaderNodeObjectInfo")
        sep_oc = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(obj_info.outputs["Color"], sep_oc.inputs["Color"])

        # R = bloom openness [0..1]: dark grey-brown bud margin -> crisp veined milky-white petal!
        mix_col = nt.nodes.new("ShaderNodeMix")
        mix_col.data_type = "RGBA"
        mix_col.inputs["A"].default_value = (0.24, 0.21, 0.17, 1.0)
        nt.links.new(sep_oc.outputs["Red"], mix_col.inputs["Factor"])
        nt.links.new(petal_col_out, mix_col.inputs["B"])
        nt.links.new(mix_col.outputs["Result"], bsdf.inputs["Base Color"])
        col_src = mix_col.outputs["Result"]
        # Attached (G=0): 100% NON-EMISSIVE per FL-01 v0.8! Detached airborne (G>0): subtle pearl wake scatter!
        if "Emission Color" in bsdf.inputs and "Emission Strength" in bsdf.inputs:
            nt.links.new(col_src, bsdf.inputs["Emission Color"])
            em_mul = nt.nodes.new("ShaderNodeMath")
            em_mul.operation = "MULTIPLY"
            em_mul.inputs[1].default_value = 0.28
            nt.links.new(sep_oc.outputs["Green"], em_mul.inputs[0])
            nt.links.new(em_mul.outputs["Value"], bsdf.inputs["Emission Strength"])

    # Delicate backlit translucency (so moonlight & whale glow shine through veined white & golden throat!)
    transl = nt.nodes.new("ShaderNodeBsdfTranslucent")
    t_tint = nt.nodes.new("ShaderNodeMix")
    t_tint.data_type = "RGBA"
    t_tint.blend_type = "MULTIPLY"
    t_tint.inputs["Factor"].default_value = 1.0
    t_tint.inputs["B"].default_value = (1.00, 0.94, 0.80, 1.0)
    nt.links.new(col_src, t_tint.inputs["A"])
    nt.links.new(t_tint.outputs["Result"], transl.inputs["Color"])

    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    if always_open:
        mix_sh.inputs["Fac"].default_value = 0.32
    else:
        tr_fac = nt.nodes.new("ShaderNodeMath")
        tr_fac.operation = "MULTIPLY"
        tr_fac.inputs[1].default_value = 0.32
        nt.links.new(sep_oc.outputs["Red"], tr_fac.inputs[0])
        nt.links.new(tr_fac.outputs["Value"], mix_sh.inputs["Fac"])
    nt.links.new(bsdf.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(transl.outputs["BSDF"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_kousetsuka_seed_material(name: str = "MAT-Kousetsuka_Seed", always_glow: bool = False):
    """v7.9 Canon FL-01 2-3mm Basal Dry Fruit ('小果実'):
    - Attached on flower stem (obj_info.Color.Green = 0.0): matte warm honey-ochre seed (zero fake emission!).
    - Detached & airborne (obj_info.Color.Green = 1.0, or flying snow always_glow=True): emits pale champagne-gold micro-glow!"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.76, 0.58, 0.26, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.45

    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (1.00, 0.86, 0.48, 1.0)
        if always_glow:
            bsdf.inputs["Emission Strength"].default_value = 2.60
        else:
            obj_info = nt.nodes.new("ShaderNodeObjectInfo")
            sep_oc = nt.nodes.new("ShaderNodeSeparateColor")
            nt.links.new(obj_info.outputs["Color"], sep_oc.inputs["Color"])
            em_mul = nt.nodes.new("ShaderNodeMath")
            em_mul.operation = "MULTIPLY"
            em_mul.inputs[1].default_value = 2.60
            nt.links.new(sep_oc.outputs["Green"], em_mul.inputs[0])
            nt.links.new(em_mul.outputs["Value"], bsdf.inputs["Emission Strength"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_soft_beam_material(
    name: str = "MAT-MoonShaft",
    color=(0.76, 0.85, 0.96, 1.0),
    base_atten: float = 0.20,
    fade_z_half: float = 68.0,
    edge_power: float = 3.2,
):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    elif hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = color
    em.inputs["Strength"].default_value = 0.65

    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.50
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])

    pwr = nt.nodes.new("ShaderNodeMath")
    pwr.operation = "POWER"
    pwr.inputs[1].default_value = edge_power
    nt.links.new(inv.outputs[0], pwr.inputs[0])

    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])

    fade_bot = nt.nodes.new("ShaderNodeMapRange")
    fade_bot.interpolation_type = "SMOOTHSTEP"
    fade_bot.clamp = True
    fade_bot.inputs["From Min"].default_value = -fade_z_half
    fade_bot.inputs["From Max"].default_value = -fade_z_half * 0.62
    nt.links.new(sep.outputs["Z"], fade_bot.inputs["Value"])

    fade_top = nt.nodes.new("ShaderNodeMapRange")
    fade_top.interpolation_type = "SMOOTHSTEP"
    fade_top.clamp = True
    fade_top.inputs["From Min"].default_value = fade_z_half
    fade_top.inputs["From Max"].default_value = fade_z_half * 0.62
    nt.links.new(sep.outputs["Z"], fade_top.inputs["Value"])

    v_mul = nt.nodes.new("ShaderNodeMath")
    v_mul.operation = "MULTIPLY"
    nt.links.new(fade_bot.outputs["Result"], v_mul.inputs[0])
    nt.links.new(fade_top.outputs["Result"], v_mul.inputs[1])

    f_mul = nt.nodes.new("ShaderNodeMath")
    f_mul.operation = "MULTIPLY"
    nt.links.new(pwr.outputs[0], f_mul.inputs[0])
    nt.links.new(v_mul.outputs[0], f_mul.inputs[1])

    atten = nt.nodes.new("ShaderNodeMath")
    atten.name = "VAL_BEAM_ATTEN"
    atten.operation = "MULTIPLY"
    atten.inputs[1].default_value = base_atten
    nt.links.new(f_mul.outputs[0], atten.inputs[0])

    nt.links.new(atten.outputs[0], mix_sh.inputs["Fac"])
    nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(em.outputs["Emission"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_aurora_petal_material(name: str, em_strength: float = 0.34, far_muted: bool = False, aurora_mode: str = "sky_veil", near_whale: bool = False):
    """v7.7 Canon FL-01 + Whale-Light Iridescence Shader:
    - 'canon_starry_opal' (3=A): Petals stay predominantly milky snow-white (#F2F5F8) with warm pale champagne-gold
      2-3mm seed glints (#F4DA94), catching faint pastel ice-aqua / dawn-sakura translucency ONLY on sparkle peaks
      and near-whale wake corridors! Zero neon-pink confetti!"""
    canon_opal = (aurora_mode == "canon_starry_opal")
    starry_mode = (aurora_mode == "starry_aurora_whale")
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.68 if ((starry_mode or canon_opal) and not far_muted) else (0.72 if not far_muted else 0.85)
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.32 if (starry_mode or canon_opal) else 0.28

    t_val = nt.nodes.new("ShaderNodeValue")
    t_val.name = "VAL_PETAL_TIME"
    t_val.outputs[0].default_value = 0.0

    geom = nt.nodes.new("ShaderNodeNewGeometry")
    n_broad = nt.nodes.new("ShaderNodeTexNoise")
    n_broad.inputs["Scale"].default_value = 0.055 if (starry_mode or canon_opal) else 0.045
    n_broad.inputs["Detail"].default_value = 2.0
    nt.links.new(geom.outputs["Position"], n_broad.inputs["Vector"])

    n_fine = nt.nodes.new("ShaderNodeTexNoise")
    n_fine.inputs["Scale"].default_value = 1.65 if (starry_mode or canon_opal) else 1.4
    n_fine.inputs["Detail"].default_value = 1.0
    nt.links.new(geom.outputs["Position"], n_fine.inputs["Vector"])

    n_mix = nt.nodes.new("ShaderNodeMix")
    n_mix.data_type = "FLOAT"
    n_mix.inputs["Factor"].default_value = 0.50 if (starry_mode or canon_opal) else 0.42
    nt.links.new(n_broad.outputs["Fac"], n_mix.inputs["A"])
    nt.links.new(n_fine.outputs["Fac"], n_mix.inputs["B"])

    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.interpolation = "EASE"
    if far_muted:
        cr.color_ramp.elements[0].position = 0.25
        if canon_opal:
            cr.color_ramp.elements[0].color = (0.58, 0.72, 0.90, 1.0)
            cr.color_ramp.elements[1].position = 0.75
            cr.color_ramp.elements[1].color = (0.86, 0.84, 0.90, 1.0)
        else:
            cr.color_ramp.elements[0].color = (0.18, 0.56, 0.92, 1.0) if starry_mode else (0.28, 0.56, 0.88, 1.0)
            cr.color_ramp.elements[1].position = 0.75
            cr.color_ramp.elements[1].color = (0.86, 0.32, 0.68, 1.0) if starry_mode else (0.76, 0.42, 0.72, 1.0)
    elif canon_opal:
        # v7.7 Canon 3=A: Crisp milky pearl-white core + warm champagne-gold seed glint + whisper ice/sakura whale bounce!
        tint = 1.0 if near_whale else 0.52
        cr.color_ramp.elements[0].position = 0.18
        cr.color_ramp.elements[0].color = (lerp(0.76, 0.54, tint), lerp(0.90, 0.86, tint), 1.00, 1.0)
        e1 = cr.color_ramp.elements.new(0.36)
        e1.color = (0.95, 0.97, 1.00, 1.0)                            # crisp milky pearl-white (FL-01!)
        e2 = cr.color_ramp.elements.new(0.56)
        e2.color = (0.96, 0.96, 0.98, 1.0)                            # pure luminous white core
        e3 = cr.color_ramp.elements.new(0.70)
        e3.color = (1.00, 0.86, 0.54, 1.0)                            # champagne-gold 2-3mm seed accent (#F4DA94!)
        cr.color_ramp.elements[1].position = 0.84
        cr.color_ramp.elements[1].color = (0.99, lerp(0.88, 0.72, tint), lerp(0.92, 0.82, tint), 1.0)
    elif starry_mode:
        # v7.6 Jewel-Aurora Shimmering Petals (vivid luminous pastel under AgX!)
        cr.color_ramp.elements[0].position = 0.22
        cr.color_ramp.elements[0].color = (0.06, 0.62, 1.00, 1.0)     # glacier ice-blue
        e1 = cr.color_ramp.elements.new(0.35)
        e1.color = (0.14, 0.90, 0.80, 1.0)                            # aurora aqua-mint shimmer
        e2 = cr.color_ramp.elements.new(0.48)
        e2.color = (0.94, 0.97, 1.00, 1.0)                            # milky pearl-white (FL-01!)
        e3 = cr.color_ramp.elements.new(0.60)
        e3.color = (1.00, 0.74, 0.32, 1.0)                            # champagne-gold seed glint
        e4 = cr.color_ramp.elements.new(0.71)
        e4.color = (0.50, 0.26, 1.00, 1.0)                            # dreamy pastel lavender
        cr.color_ramp.elements[1].position = 0.82
        cr.color_ramp.elements[1].color = (1.00, 0.22, 0.60, 1.0)     # radiant dawn sakura-pink!
    else:
        cr.color_ramp.elements[0].position = 0.24
        cr.color_ramp.elements[0].color = (0.22, 0.74, 1.00, 1.0)
        e1 = cr.color_ramp.elements.new(0.46)
        e1.color = (0.94, 0.96, 1.00, 1.0)
        e2 = cr.color_ramp.elements.new(0.60)
        e2.color = (1.00, 0.80, 0.52, 1.0)
        cr.color_ramp.elements[1].position = 0.78
        cr.color_ramp.elements[1].color = (1.00, 0.38, 0.70, 1.0)
    nt.links.new(n_mix.outputs["Result"], cr.inputs["Fac"])

    if (starry_mode or canon_opal) and not far_muted:
        # Keep diffuse gently restrained so directional lights don't blow petals to solid chalk; emission sparkles cleanly!
        p_dim = nt.nodes.new("ShaderNodeMix")
        p_dim.data_type = "RGBA"
        p_dim.blend_type = "MULTIPLY"
        p_dim.inputs["Factor"].default_value = 1.0
        dv = 0.62 if canon_opal else 0.34
        p_dim.inputs["B"].default_value = (dv, dv, min(1.0, dv + 0.02), 1.0)
        nt.links.new(cr.outputs["Color"], p_dim.inputs["A"])
        nt.links.new(p_dim.outputs["Result"], bsdf.inputs["Base Color"])
    else:
        nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])

    if "Emission Color" in bsdf.inputs:
        nt.links.new(cr.outputs["Color"], bsdf.inputs["Emission Color"])
        if (starry_mode or canon_opal) and not far_muted:
            # Per-petal animated diamond sparkle glint ('煌めき')!
            n_gl = nt.nodes.new("ShaderNodeTexNoise")
            n_gl.noise_dimensions = "4D"
            n_gl.inputs["Scale"].default_value = 2.6
            n_gl.inputs["Detail"].default_value = 1.0
            nt.links.new(geom.outputs["Position"], n_gl.inputs["Vector"])
            pt_m = nt.nodes.new("ShaderNodeMath")
            pt_m.operation = "MULTIPLY"
            pt_m.inputs[1].default_value = 0.45
            nt.links.new(t_val.outputs[0], pt_m.inputs[0])
            nt.links.new(pt_m.outputs["Value"], n_gl.inputs["W"])
            gl_mr = nt.nodes.new("ShaderNodeMapRange")
            gl_mr.interpolation_type = "SMOOTHSTEP"
            gl_mr.clamp = True
            gl_mr.inputs["From Min"].default_value = 0.56
            gl_mr.inputs["From Max"].default_value = 0.80
            gl_mr.inputs["To Min"].default_value = em_strength * (1.10 if canon_opal else 1.45)
            gl_mr.inputs["To Max"].default_value = em_strength * (2.60 if canon_opal else 3.60)
            nt.links.new(n_gl.outputs["Fac"], gl_mr.inputs["Value"])
            nt.links.new(gl_mr.outputs["Result"], bsdf.inputs["Emission Strength"])
        else:
            bsdf.inputs["Emission Strength"].default_value = em_strength
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_star_vault_material(name: str = "MAT-StarVault", aurora_mode: str = "sky_veil"):
    """v7.8 Grand Winter Milky Way Star-Vault Shader:
    - VAL_STAR_WAKE = 0.0 (Act 1 & Act 3): 100% dark invisible pitch cosmos!
    - VAL_STAR_WAKE = 1.0 (Act 2): rich winter blackbody star palette (Rigel sapphire, Vega white, rare Betelgeuse gold)
      with sharp dynamic magnitude range & subtle lake-reflection attenuation so water stays dark mirror silk."""
    canon_opal = (aurora_mode == "canon_starry_opal")
    starry_mode = (aurora_mode in ("starry_aurora_whale", "canon_starry_opal"))
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")

    wake = nt.nodes.new("ShaderNodeValue")
    wake.name = "VAL_STAR_WAKE"
    wake.outputs[0].default_value = 0.0

    st_time = nt.nodes.new("ShaderNodeValue")
    st_time.name = "VAL_STAR_TIME"
    st_time.outputs[0].default_value = 0.0

    geom = nt.nodes.new("ShaderNodeNewGeometry")
    n_col = nt.nodes.new("ShaderNodeTexNoise")
    n_col.inputs["Scale"].default_value = 0.19
    n_col.inputs["Detail"].default_value = 2.0
    nt.links.new(geom.outputs["Position"], n_col.inputs["Vector"])

    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.interpolation = "LINEAR"
    cr.color_ramp.elements[0].position = 0.16
    cr.color_ramp.elements[0].color = (0.52, 0.78, 1.00, 1.0)     # blue-white Rigel/Sirius
    e1 = cr.color_ramp.elements.new(0.46)
    e1.color = (0.97, 0.99, 1.00, 1.0)                            # crisp crystal Vega white
    e2 = cr.color_ramp.elements.new(0.76)
    e2.color = (0.76, 0.87, 1.00, 1.0) if canon_opal else ((0.88, 0.82, 1.00, 1.0) if starry_mode else (1.00, 0.72, 0.88, 1.0))
    cr.color_ramp.elements[1].position = 0.92
    cr.color_ramp.elements[1].color = (1.00, 0.86, 0.58, 1.0)     # sparse pale amber Betelgeuse
    nt.links.new(n_col.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], em.inputs["Color"])

    # Animated 4D star scintillation + wider dynamic magnitude contrast (faint galactic dust -> sparkling 2nd-mag stars!)
    n_mag = nt.nodes.new("ShaderNodeTexNoise")
    n_mag.noise_dimensions = "4D"
    n_mag.inputs["Scale"].default_value = 1.25
    n_mag.inputs["Detail"].default_value = 1.0
    nt.links.new(geom.outputs["Position"], n_mag.inputs["Vector"])
    st_w = nt.nodes.new("ShaderNodeMath")
    st_w.operation = "MULTIPLY"
    st_w.inputs[1].default_value = 0.35
    nt.links.new(st_time.outputs[0], st_w.inputs[0])
    nt.links.new(st_w.outputs["Value"], n_mag.inputs["W"])

    mag_mr = nt.nodes.new("ShaderNodeMapRange")
    mag_mr.clamp = True
    mag_mr.inputs["From Min"].default_value = 0.28
    mag_mr.inputs["From Max"].default_value = 0.74
    mag_mr.inputs["To Min"].default_value = 0.22 if canon_opal else 0.38
    mag_mr.inputs["To Max"].default_value = 5.20 if canon_opal else (3.40 if starry_mode else 2.65)
    nt.links.new(n_mag.outputs["Fac"], mag_mr.inputs["Value"])

    lp = nt.nodes.new("ShaderNodeLightPath")
    g_dim = nt.nodes.new("ShaderNodeMix")
    g_dim.data_type = "FLOAT"
    g_dim.inputs["A"].default_value = 1.0
    g_dim.inputs["B"].default_value = 0.45
    nt.links.new(lp.outputs["Is Glossy Ray"], g_dim.inputs["Factor"])

    str_m1 = nt.nodes.new("ShaderNodeMath")
    str_m1.operation = "MULTIPLY"
    nt.links.new(wake.outputs[0], str_m1.inputs[0])
    nt.links.new(mag_mr.outputs["Result"], str_m1.inputs[1])

    str_mul = nt.nodes.new("ShaderNodeMath")
    str_mul.operation = "MULTIPLY"
    nt.links.new(str_m1.outputs["Value"], str_mul.inputs[0])
    nt.links.new(g_dim.outputs["Result"], str_mul.inputs[1])
    nt.links.new(str_mul.outputs["Value"], em.inputs["Strength"])

    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def make_starburst_hero_material(name: str = "MAT-StarburstHero"):
    """v7.8 Tier-4 Winter Constellation 1st-Magnitude 4-Point Diffraction Starbursts:
    Crisp razor-sharp crystal diamonds (Sirius / Rigel / Capella / Betelgeuse tint) driving galactic awe in Act 2."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")

    wake = nt.nodes.new("ShaderNodeValue")
    wake.name = "VAL_STAR_WAKE"
    wake.outputs[0].default_value = 0.0

    st_time = nt.nodes.new("ShaderNodeValue")
    st_time.name = "VAL_STAR_TIME"
    st_time.outputs[0].default_value = 0.0

    geom = nt.nodes.new("ShaderNodeNewGeometry")
    n_col = nt.nodes.new("ShaderNodeTexNoise")
    n_col.inputs["Scale"].default_value = 0.08
    nt.links.new(geom.outputs["Position"], n_col.inputs["Vector"])

    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.25
    cr.color_ramp.elements[0].color = (0.64, 0.84, 1.00, 1.0)
    e1 = cr.color_ramp.elements.new(0.65)
    e1.color = (0.98, 0.99, 1.00, 1.0)
    cr.color_ramp.elements[1].position = 0.90
    cr.color_ramp.elements[1].color = (1.00, 0.88, 0.62, 1.0)
    nt.links.new(n_col.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], em.inputs["Color"])

    n_mag = nt.nodes.new("ShaderNodeTexNoise")
    n_mag.noise_dimensions = "4D"
    n_mag.inputs["Scale"].default_value = 0.45
    nt.links.new(geom.outputs["Position"], n_mag.inputs["Vector"])
    st_w = nt.nodes.new("ShaderNodeMath")
    st_w.operation = "MULTIPLY"
    st_w.inputs[1].default_value = 0.25
    nt.links.new(st_time.outputs[0], st_w.inputs[0])
    nt.links.new(st_w.outputs["Value"], n_mag.inputs["W"])

    mag_mr = nt.nodes.new("ShaderNodeMapRange")
    mag_mr.clamp = True
    mag_mr.inputs["From Min"].default_value = 0.30
    mag_mr.inputs["From Max"].default_value = 0.72
    mag_mr.inputs["To Min"].default_value = 2.8
    mag_mr.inputs["To Max"].default_value = 6.2
    nt.links.new(n_mag.outputs["Fac"], mag_mr.inputs["Value"])

    lp = nt.nodes.new("ShaderNodeLightPath")
    g_dim = nt.nodes.new("ShaderNodeMix")
    g_dim.data_type = "FLOAT"
    g_dim.inputs["A"].default_value = 1.0
    g_dim.inputs["B"].default_value = 0.35
    nt.links.new(lp.outputs["Is Glossy Ray"], g_dim.inputs["Factor"])

    m1 = nt.nodes.new("ShaderNodeMath")
    m1.operation = "MULTIPLY"
    nt.links.new(wake.outputs[0], m1.inputs[0])
    nt.links.new(mag_mr.outputs["Result"], m1.inputs[1])

    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "MULTIPLY"
    nt.links.new(m1.outputs["Value"], m2.inputs[0])
    nt.links.new(g_dim.outputs["Result"], m2.inputs[1])
    nt.links.new(m2.outputs["Value"], em.inputs["Strength"])

    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def make_aurora_veil_material(name: str = "MAT-AuroraVeil", aurora_mode: str = "sky_veil"):
    """v7.5 Gossamer Translucent Subterranean Aurora Curtains (glacier ice-blue -> pastel lavender -> pale sakura-rose):
    Uses UV edge feathering + vertically-stretched 4D aurora-ray noise so ZERO hard polygon borders ever appear!
    100% transparent/hidden in Act 1 & Act 3; subtle painted watercolor silk (max ~0.22 alpha) in Act 2!"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    elif hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    mix_sh = nt.nodes.new("ShaderNodeMixShader")

    a_val = nt.nodes.new("ShaderNodeValue")
    a_val.name = "VAL_AURORA"
    a_val.outputs[0].default_value = 0.0

    t_val = nt.nodes.new("ShaderNodeValue")
    t_val.name = "VAL_AURORA_TIME"
    t_val.outputs[0].default_value = 0.0

    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs["Vector"])

    # Horizontal end feathering: 4 * u * (1 - u) clamped smoothstep -> 0 at u=0 and u=1!
    one_m_u = nt.nodes.new("ShaderNodeMath")
    one_m_u.operation = "SUBTRACT"
    one_m_u.inputs[0].default_value = 1.0
    nt.links.new(sep.outputs["X"], one_m_u.inputs[1])
    u_prod = nt.nodes.new("ShaderNodeMath")
    u_prod.operation = "MULTIPLY"
    nt.links.new(sep.outputs["X"], u_prod.inputs[0])
    nt.links.new(one_m_u.outputs["Value"], u_prod.inputs[1])
    u_fade = nt.nodes.new("ShaderNodeMapRange")
    u_fade.interpolation_type = "SMOOTHSTEP"
    u_fade.clamp = True
    u_fade.inputs["From Min"].default_value = 0.0
    u_fade.inputs["From Max"].default_value = 0.19
    u_fade.inputs["To Min"].default_value = 0.0
    u_fade.inputs["To Max"].default_value = 1.0
    nt.links.new(u_prod.outputs["Value"], u_fade.inputs["Value"])

    if aurora_mode == "canon_starry_opal":
        # Symmetric bell envelope across galactic latitude v in [0..1] (0 at margins, peak around v=0.5!)
        one_m_v = nt.nodes.new("ShaderNodeMath")
        one_m_v.operation = "SUBTRACT"
        one_m_v.inputs[0].default_value = 1.0
        nt.links.new(sep.outputs["Y"], one_m_v.inputs[1])
        v_prod = nt.nodes.new("ShaderNodeMath")
        v_prod.operation = "MULTIPLY"
        nt.links.new(sep.outputs["Y"], v_prod.inputs[0])
        nt.links.new(one_m_v.outputs["Value"], v_prod.inputs[1])
        v_bell = nt.nodes.new("ShaderNodeMapRange")
        v_bell.interpolation_type = "SMOOTHSTEP"
        v_bell.clamp = True
        v_bell.inputs["From Min"].default_value = 0.015
        v_bell.inputs["From Max"].default_value = 0.24
        v_bell.inputs["To Min"].default_value = 0.0
        v_bell.inputs["To Max"].default_value = 1.0
        nt.links.new(v_prod.outputs["Value"], v_bell.inputs["Value"])

        # Isotropic 3D galactic cloud + dark cosmic rift (ZERO stretched UV zebra streaks!)
        geom = nt.nodes.new("ShaderNodeNewGeometry")
        sep_w = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geom.outputs["Position"], sep_w.inputs["Vector"])
        alt_fade = nt.nodes.new("ShaderNodeMapRange")
        alt_fade.interpolation_type = "SMOOTHSTEP"
        alt_fade.clamp = True
        alt_fade.inputs["From Min"].default_value = 22.0
        alt_fade.inputs["From Max"].default_value = 46.0
        alt_fade.inputs["To Min"].default_value = 0.0
        alt_fade.inputs["To Max"].default_value = 1.0
        nt.links.new(sep_w.outputs["Z"], alt_fade.inputs["Value"])

        n_cloud = nt.nodes.new("ShaderNodeTexNoise")
        n_cloud.inputs["Scale"].default_value = 0.017
        n_cloud.inputs["Detail"].default_value = 7.0
        n_cloud.inputs["Roughness"].default_value = 0.65
        nt.links.new(geom.outputs["Position"], n_cloud.inputs["Vector"])

        cloud_mr = nt.nodes.new("ShaderNodeMapRange")
        cloud_mr.interpolation_type = "SMOOTHSTEP"
        cloud_mr.clamp = True
        cloud_mr.inputs["From Min"].default_value = 0.36
        cloud_mr.inputs["From Max"].default_value = 0.78
        cloud_mr.inputs["To Min"].default_value = 0.14
        cloud_mr.inputs["To Max"].default_value = 1.0
        nt.links.new(n_cloud.outputs["Fac"], cloud_mr.inputs["Value"])

        # Organic warped Dark Cosmic Dust Rift along galactic equator v ~ 0.50
        n_rift = nt.nodes.new("ShaderNodeTexNoise")
        n_rift.inputs["Scale"].default_value = 0.032
        n_rift.inputs["Detail"].default_value = 4.0
        nt.links.new(geom.outputs["Position"], n_rift.inputs["Vector"])
        rift_jit = nt.nodes.new("ShaderNodeMapRange")
        rift_jit.inputs["From Min"].default_value = 0.2
        rift_jit.inputs["From Max"].default_value = 0.8
        rift_jit.inputs["To Min"].default_value = -0.11
        rift_jit.inputs["To Max"].default_value = 0.11
        nt.links.new(n_rift.outputs["Fac"], rift_jit.inputs["Value"])

        v_warp = nt.nodes.new("ShaderNodeMath")
        v_warp.operation = "ADD"
        nt.links.new(sep.outputs["Y"], v_warp.inputs[0])
        nt.links.new(rift_jit.outputs["Result"], v_warp.inputs[1])

        v_off = nt.nodes.new("ShaderNodeMath")
        v_off.operation = "SUBTRACT"
        v_off.inputs[1].default_value = 0.50
        nt.links.new(v_warp.outputs["Value"], v_off.inputs[0])

        v_abs = nt.nodes.new("ShaderNodeMath")
        v_abs.operation = "ABSOLUTE"
        nt.links.new(v_off.outputs["Value"], v_abs.inputs[0])

        rift_carve = nt.nodes.new("ShaderNodeMapRange")
        rift_carve.interpolation_type = "SMOOTHSTEP"
        rift_carve.clamp = True
        rift_carve.inputs["From Min"].default_value = 0.015
        rift_carve.inputs["From Max"].default_value = 0.130
        rift_carve.inputs["To Min"].default_value = 0.26
        rift_carve.inputs["To Max"].default_value = 1.00
        nt.links.new(v_abs.outputs["Value"], rift_carve.inputs["Value"])

        cr = nt.nodes.new("ShaderNodeValToRGB")
        cr.color_ramp.interpolation = "EASE"
        cr.color_ramp.elements[0].position = 0.24
        cr.color_ramp.elements[0].color = (0.018, 0.045, 0.130, 1.0)
        e1 = cr.color_ramp.elements.new(0.58)
        e1.color = (0.075, 0.148, 0.295, 1.0)
        cr.color_ramp.elements[1].position = 0.88
        cr.color_ramp.elements[1].color = (0.185, 0.280, 0.435, 1.0)
        nt.links.new(cloud_mr.outputs["Result"], cr.inputs["Fac"])
        nt.links.new(cr.outputs["Color"], em.inputs["Color"])
        em.inputs["Strength"].default_value = 0.96

        lp = nt.nodes.new("ShaderNodeLightPath")
        g_dim = nt.nodes.new("ShaderNodeMix")
        g_dim.data_type = "FLOAT"
        g_dim.inputs["A"].default_value = 1.0
        g_dim.inputs["B"].default_value = 0.42
        nt.links.new(lp.outputs["Is Glossy Ray"], g_dim.inputs["Factor"])

        m0 = nt.nodes.new("ShaderNodeMath")
        m0.operation = "MULTIPLY"
        nt.links.new(u_fade.outputs["Result"], m0.inputs[0])
        nt.links.new(v_bell.outputs["Result"], m0.inputs[1])

        m0b = nt.nodes.new("ShaderNodeMath")
        m0b.operation = "MULTIPLY"
        nt.links.new(m0.outputs["Value"], m0b.inputs[0])
        nt.links.new(alt_fade.outputs["Result"], m0b.inputs[1])

        m1 = nt.nodes.new("ShaderNodeMath")
        m1.operation = "MULTIPLY"
        nt.links.new(m0b.outputs["Value"], m1.inputs[0])
        nt.links.new(cloud_mr.outputs["Result"], m1.inputs[1])

        m2 = nt.nodes.new("ShaderNodeMath")
        m2.operation = "MULTIPLY"
        nt.links.new(m1.outputs["Value"], m2.inputs[0])
        nt.links.new(rift_carve.outputs["Result"], m2.inputs[1])

        m3 = nt.nodes.new("ShaderNodeMath")
        m3.operation = "MULTIPLY"
        m3.inputs[1].default_value = 0.34
        nt.links.new(m2.outputs["Value"], m3.inputs[0])

        m4 = nt.nodes.new("ShaderNodeMath")
        m4.operation = "MULTIPLY"
        nt.links.new(m3.outputs["Value"], m4.inputs[0])
        nt.links.new(a_val.outputs[0], m4.inputs[1])

        m5 = nt.nodes.new("ShaderNodeMath")
        m5.operation = "MULTIPLY"
        nt.links.new(m4.outputs["Value"], m5.inputs[0])
        nt.links.new(g_dim.outputs["Result"], m5.inputs[1])

        nt.links.new(m5.outputs["Value"], mix_sh.inputs["Fac"])
        nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
        nt.links.new(em.outputs["Emission"], mix_sh.inputs[2])
        nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
        return mat

    em.inputs["Strength"].default_value = 1.35

    # Vertical aurora curtain profile: rises quickly near lower glowing hem (v=0..0.30), feathers silkily to 0 at v=1.0!
    v_bot = nt.nodes.new("ShaderNodeMapRange")
    v_bot.interpolation_type = "SMOOTHSTEP"
    v_bot.clamp = True
    v_bot.inputs["From Min"].default_value = 0.0
    v_bot.inputs["From Max"].default_value = 0.28
    v_bot.inputs["To Min"].default_value = 0.0
    v_bot.inputs["To Max"].default_value = 1.0
    nt.links.new(sep.outputs["Y"], v_bot.inputs["Value"])

    v_top = nt.nodes.new("ShaderNodeMapRange")
    v_top.interpolation_type = "SMOOTHSTEP"
    v_top.clamp = True
    v_top.inputs["From Min"].default_value = 0.34
    v_top.inputs["From Max"].default_value = 1.0
    v_top.inputs["To Min"].default_value = 1.0
    v_top.inputs["To Max"].default_value = 0.0
    nt.links.new(sep.outputs["Y"], v_top.inputs["Value"])

    v_env = nt.nodes.new("ShaderNodeMath")
    v_env.operation = "MULTIPLY"
    nt.links.new(v_bot.outputs["Result"], v_env.inputs[0])
    nt.links.new(v_top.outputs["Result"], v_env.inputs[1])

    # Vertically-stretched animated aurora ray folds!
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (6.8, 0.55, 1.0)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    n_rays = nt.nodes.new("ShaderNodeTexNoise")
    n_rays.noise_dimensions = "4D"
    n_rays.inputs["Scale"].default_value = 2.4
    n_rays.inputs["Detail"].default_value = 4.0
    n_rays.inputs["Roughness"].default_value = 0.48
    nt.links.new(mp.outputs["Vector"], n_rays.inputs["Vector"])
    t_mul = nt.nodes.new("ShaderNodeMath")
    t_mul.operation = "MULTIPLY"
    t_mul.inputs[1].default_value = 0.032
    nt.links.new(t_val.outputs[0], t_mul.inputs[0])
    nt.links.new(t_mul.outputs["Value"], n_rays.inputs["W"])

    ray_mr = nt.nodes.new("ShaderNodeMapRange")
    ray_mr.interpolation_type = "SMOOTHSTEP"
    ray_mr.clamp = True
    ray_mr.inputs["From Min"].default_value = 0.32
    ray_mr.inputs["From Max"].default_value = 0.78
    ray_mr.inputs["To Min"].default_value = 0.14
    ray_mr.inputs["To Max"].default_value = 1.0
    nt.links.new(n_rays.outputs["Fac"], ray_mr.inputs["Value"])

    # Color ramp: lower glacier aqua-blue -> mid ethereal lavender -> upper pale dawn sakura-rose pink!
    col_u = nt.nodes.new("ShaderNodeMix")
    col_u.data_type = "FLOAT"
    col_u.inputs["Factor"].default_value = 0.30
    nt.links.new(sep.outputs["Y"], col_u.inputs["A"])
    nt.links.new(sep.outputs["X"], col_u.inputs["B"])

    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.interpolation = "EASE"
    cr.color_ramp.elements[0].position = 0.14
    cr.color_ramp.elements[0].color = (0.14, 0.72, 1.00, 1.0)     # luminous glacier aqua-blue lower veil (AgX pastel!)
    e1 = cr.color_ramp.elements.new(0.48)
    e1.color = (0.56, 0.36, 0.98, 1.0)                            # dreamy pastel twilight lavender core
    cr.color_ramp.elements[1].position = 0.80
    cr.color_ramp.elements[1].color = (1.00, 0.32, 0.68, 1.0)     # luminous dawn sakura-rose crest
    nt.links.new(col_u.outputs["Result"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], em.inputs["Color"])

    # Final restrained translucent silk alpha (capped around 0.24 * VAL_AURORA — pure painted atmospheric silk!)
    m1 = nt.nodes.new("ShaderNodeMath")
    m1.operation = "MULTIPLY"
    nt.links.new(u_fade.outputs["Result"], m1.inputs[0])
    nt.links.new(v_env.outputs["Value"], m1.inputs[1])

    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "MULTIPLY"
    nt.links.new(m1.outputs["Value"], m2.inputs[0])
    nt.links.new(ray_mr.outputs["Result"], m2.inputs[1])

    m3 = nt.nodes.new("ShaderNodeMath")
    m3.operation = "MULTIPLY"
    m3.inputs[1].default_value = 0.24
    nt.links.new(m2.outputs["Value"], m3.inputs[0])

    m4 = nt.nodes.new("ShaderNodeMath")
    m4.operation = "MULTIPLY"
    nt.links.new(m3.outputs["Value"], m4.inputs[0])
    nt.links.new(a_val.outputs[0], m4.inputs[1])

    nt.links.new(m4.outputs["Value"], mix_sh.inputs["Fac"])
    nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(em.outputs["Emission"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_translucent_fx_material(name: str, color=(0.82, 0.89, 0.98, 1.0), em_strength: float = 0.45, alpha_default: float = 0.25):
    """Soft Fresnel-feathered translucent clay FX material (spray curtains, lake mist, awakening breath)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    elif hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = color
    em.inputs["Strength"].default_value = em_strength

    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.42
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])

    pwr = nt.nodes.new("ShaderNodeMath")
    pwr.operation = "POWER"
    pwr.inputs[1].default_value = 1.8
    nt.links.new(inv.outputs[0], pwr.inputs[0])

    a_val = nt.nodes.new("ShaderNodeValue")
    a_val.name = "VAL_ALPHA"
    a_val.outputs[0].default_value = alpha_default

    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(pwr.outputs[0], mul.inputs[0])
    nt.links.new(a_val.outputs[0], mul.inputs[1])

    nt.links.new(mul.outputs[0], mix_sh.inputs["Fac"])
    nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(em.outputs["Emission"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    return mat


# ---------------------------------------------------------------------------
# Procedural Clean Clay Geometry Builders
# ---------------------------------------------------------------------------

def finalize_mesh_obj(name: str, bm: bmesh.types.BMesh, mat, smooth: bool = True, collection=None):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    if mat is not None:
        if isinstance(mat, (list, tuple)):
            for m in mat:
                obj.data.materials.append(m)
        else:
            obj.data.materials.append(mat)
    return obj


def _catmull_rom_eval(pts: list[tuple[float, float]], u: float) -> float:
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
    return (2 * t3 - 3 * t2 + 1) * p1 + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * p2 + (t3 - t2) * m2


def _whale_body_profile(u: float) -> tuple[float, float, float, float, float]:
    """Authentic humpback/blue rorqual leviathan proportions (+12.0m nose -> -11.0m peduncle):
    Graceful tapered baleen rostrum, deep ~5.0m thoracic chest, strong muscular tail stock."""
    y = 12.0 - u * 23.0
    w_pts = [
        (0.00, 0.00),
        (0.018, 0.62),  # sleek tapered rorqual snout apex (zero bowling-pin nose bulb!)
        (0.055, 1.28),
        (0.115, 1.94),
        (0.20, 2.44),
        (0.26, 2.60),   # broad cranial cheek around eye & jaw corner
        (0.35, 2.66),   # massive pectoral chest (~5.32m wide)
        (0.48, 2.38),
        (0.62, 1.88),
        (0.75, 1.24),
        (0.88, 0.70),
        (0.96, 0.42),
        (1.00, 0.26),
    ]
    top_pts = [
        (0.00, 0.56),   # sleek tapered rostrum tip (y=+12m)
        (0.03, 0.92),
        (0.08, 1.22),
        (0.16, 1.56),   # nasal blowhole crown (y ~ 8.3m)
        (0.27, 1.96),
        (0.39, 2.24),   # noble dorsal arch
        (0.54, 2.02),
        (0.68, 1.56),
        (0.82, 1.02),
        (0.93, 0.64),
        (1.00, 0.42),
    ]
    bot_pts = [
        (0.00, 0.16),
        (0.025, -0.34),
        (0.07, -1.04),
        (0.15, -1.82),
        (0.26, -2.50),
        (0.37, -2.68),  # monumental deep chest & rorqual throat!
        (0.51, -2.28),
        (0.65, -1.62),
        (0.79, -1.04),
        (0.92, -0.58),
        (1.00, -0.32),
    ]
    hw = max(0.001, _catmull_rom_eval(w_pts, u))
    zt = _catmull_rom_eval(top_pts, u)
    zb = _catmull_rom_eval(bot_pts, u)
    keel = smoothstep(0.62, 0.92, u)
    return y, hw, zt, zb, keel


def build_anatomical_whale(mat_whale, mat_eye) -> tuple[bpy.types.Object, np.ndarray, list[tuple[bpy.types.Object, Vector]]]:
    """v9.0 24m Anatomical Baleen Leviathan (+Y nose, -Y tail, +Z dorsal, dense cephalic sculpt + UVMap):
    - Broad U-shaped rorqual rostrum with gentle dorsal splashguard tubercles & twin blowholes
    - Deep shadowed sweeping baleen mouthline cleft separating upper jaw shelf from muscled lower mandible
    - Carved almond orbital recess + protruding fleshy upper/lower eyelids & swept cheek folds
    - 18 silky ventral throat pleats strictly beneath the lower jaw contour
    - Multi-layer sapphire/obsidian eyeball oriented to cheek contour + zero swim-drift deformation sync!"""
    bm = bmesh.new()
    uv_lay = bm.loops.layers.uv.new("UVMap")

    # Dense cephalic ring concentration along head/eye/mouthline (u=0.00..0.38 -> 62 rings!) + 54 torso/tail rings
    head_u = [0.001 + 0.379 * (i / 61.0) ** 1.12 for i in range(62)]
    body_u = [0.380 + 0.620 * (i / 54.0) for i in range(1, 55)]
    u_vals = head_u + body_u
    nv = 96
    rings = []

    for u in u_vals:
        y, hw, zt, zb, keel = _whale_body_profile(u)
        zc = 0.5 * (zt + zb)
        hz = 0.5 * (zt - zb)

        rostrum_flat = smoothstep(0.015, 0.08, u) * (1.0 - smoothstep(0.24, 0.37, u))
        mouth_env = smoothstep(0.003, 0.018, u) * (1.0 - smoothstep(0.33, 0.41, u))
        # Sweeping baleen mouthline cleft dipping cleanly beneath eye corner (u=0.255 -> side_phi ~ -0.14)
        mouth_phi = 0.08 - 0.14 * smoothstep(0.0, 0.22, u) - 0.18 * smoothstep(0.18, 0.36, u)
        pleat_env = smoothstep(0.04, 0.11, u) * (1.0 - smoothstep(0.46, 0.60, u))

        # Orbital socket center at u_eye=0.255 (y ~ 6.14m), side_phi=+0.028 (crisp expressive almond slit!)
        eye_u = (u - 0.255) / 0.022
        sh_u = (u - 0.365) / 0.080

        # Subtle organic rostral crest waves & twin blowhole crest near u=0.17..0.20 (y ~ 7.4..8.1m)
        rostral_crest = 0.08 * smoothstep(0.03, 0.12, u) * smoothstep(0.34, 0.20, u)
        tubercle_wave = 0.024 * math.sin(u * 48.0) * smoothstep(0.03, 0.08, u) * smoothstep(0.24, 0.15, u)
        blowhole_bump = 0.11 * math.exp(-((u - 0.188) / 0.022) ** 2)
        dorsal_crest = 0.14 * math.exp(-((u - 0.68) / 0.08) ** 2)
        ped_keel = 0.22 * math.sin(clamp((u - 0.72) / 0.26, 0.0, 1.0) * math.pi) if u >= 0.72 else 0.0

        ring = []
        for j in range(nv):
            theta = 2.0 * math.pi * j / nv
            ct = math.cos(theta)  # +1 dorsal, -1 ventral
            st = math.sin(theta)  # +1 +X right cheek, -1 -X left cheek
            side_phi = math.atan2(ct, abs(st) + 1e-6)
            sign_st = 1.0 if st >= 0.0 else -1.0

            if ct >= 0.0:
                # Broad flat-arched mysticete upper rostrum + graceful tail keel
                x_sc = 1.0 + 0.08 * rostrum_flat * (1.0 - ct) - 0.18 * keel * (ct ** 1.45)
                z_sc = 1.0 - 0.07 * rostrum_flat * (ct ** 2.0) + 0.10 * keel * (ct ** 2.4)
                x = hw * st * x_sc
                d_ridge = (ct ** 10) * (dorsal_crest + ped_keel) + (ct ** 7) * (rostral_crest + tubercle_wave)
                bh_ridge = (math.exp(-((abs(st) - 0.09) / 0.06) ** 2) - 0.55 * math.exp(-(abs(st) / 0.04) ** 2)) * (ct ** 8) * blowhole_bump
                z = zc + hz * ct * z_sc + d_ridge + bh_ridge
            else:
                # Heavy broadened lower mandible chin/jawline + 18 deep ventral throat pleats strictly below jaw!
                jaw_broad = 1.0 + 0.15 * (1.0 - keel) * (1.0 - abs(ct) ** 2.1)
                x_sc = (1.0 - 0.16 * keel * ((-ct) ** 1.45)) * jaw_broad
                z_sc = 1.0 + 0.09 * keel * ((-ct) ** 2.4)
                x = hw * st * x_sc
                z = zc + hz * ct * z_sc
                if pleat_env > 0.001 and ct < -0.11:
                    v_mask = smoothstep(-0.11, -0.34, ct)
                    phi_b = math.atan2(st, -ct)
                    c_w = math.cos(phi_b * 18.0) - 0.18 * math.cos(phi_b * 36.0)
                    p_disp = 0.088 * c_w * pleat_env * v_mask
                    x += st * p_disp * 0.62
                    z += ct * p_disp

            # Deep shadowed Baleen Mouthline Cleft + Upper Lip Shelf + Heavy Lower Mandible Rim
            if mouth_env > 0.001 and abs(st) > 0.24:
                dm = (side_phi - mouth_phi) / 0.046
                groove = math.exp(-dm * dm)
                upper_lip = math.exp(-((side_phi - (mouth_phi + 0.075)) / 0.058) ** 2)
                lower_jaw = math.exp(-((side_phi - (mouth_phi - 0.078)) / 0.062) ** 2)
                inward = (0.36 * groove - 0.11 * upper_lip - 0.13 * lower_jaw) * mouth_env * min(1.0, hw / 0.85)
                x -= sign_st * inward
                z -= 0.045 * upper_lip * mouth_env

            # Muscular pectoral shoulder fairing smoothly carrying wings
            if abs(sh_u) < 2.2 and abs(st) > 0.45 and ct < 0.18:
                sh_phi = (side_phi - (-0.42)) / 0.36
                d2s = sh_u * sh_u + sh_phi * sh_phi
                if d2s < 4.2:
                    swell = math.exp(-d2s * 0.95) * 0.36
                    x += sign_st * swell
                    z -= swell * 0.18

            # Carved Almond Eye Socket + Fleshy Upper/Lower Eyelid Folds + Cheek Wrinkles (signed multiply!)
            if abs(eye_u) < 3.0 and abs(st) > 0.65:
                ep = (side_phi - 0.028) / 0.062
                d2 = eye_u * eye_u + ep * ep
                if d2 < 6.4:
                    # Deep INWARD socket pocket (-0.36m) so cupped eyelid walls frame expressive sapphire eyeball!
                    socket = math.exp(-d2 * 1.25)
                    # Proud fleshy upper eyelid hood sheltering top edge + sharp lid crease
                    up_lid = math.exp(-(eye_u * eye_u * 0.68 + ((side_phi - 0.090) / 0.026) ** 2) * 1.25)
                    up_crease = math.exp(-(eye_u * eye_u * 0.62 + ((side_phi - 0.128) / 0.018) ** 2) * 1.35)
                    # Fleshy lower eyelid bulge & sweeping tear-trough skin fold curving down toward mouth
                    lo_lid = math.exp(-(eye_u * eye_u * 0.72 + ((side_phi + 0.032) / 0.024) ** 2) * 1.30)
                    cheek_fold1 = math.exp(-(((u - 0.244) / 0.024) ** 2 * 0.60 + ((side_phi + 0.072) / 0.016) ** 2) * 1.30)
                    cheek_fold2 = math.exp(-(((u - 0.236) / 0.026) ** 2 * 0.60 + ((side_phi + 0.104) / 0.015) ** 2) * 1.30)
                    x_shift = (
                        -0.36 * socket
                        + 0.175 * up_lid
                        - 0.080 * up_crease
                        + 0.135 * lo_lid
                        - 0.065 * cheek_fold1
                        - 0.045 * cheek_fold2
                    )
                    x += sign_st * x_shift

            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)

    v_nose = bm.verts.new((0.0, 12.04, 0.52))
    v_tail = bm.verts.new((0.0, -11.06, 0.06))
    for j in range(nv):
        jn = (j + 1) % nv
        bm.faces.new((v_nose, rings[0][j], rings[0][jn]))
    for i in range(len(rings) - 1):
        for j in range(nv):
            jn = (j + 1) % nv
            bm.faces.new((rings[i][j], rings[i][jn], rings[i + 1][jn], rings[i + 1][j]))
    for j in range(nv):
        jn = (j + 1) % nv
        bm.faces.new((v_tail, rings[-1][jn], rings[-1][j]))
    n_body_faces = len(bm.faces)

    # 1b. Dedicated Anatomical Swept Falcate Dorsal Fin
    df_rings = []
    df_steps = 12
    for k in range(df_steps + 1):
        u = k / df_steps
        yc = lerp(-3.60, -5.35, u ** 1.38)
        zc = lerp(1.38, 2.95, u ** 0.82)
        chord = lerp(1.48, 0.12, u ** 0.88)
        thick = lerp(0.24, 0.028, u ** 0.90)
        row = []
        for m in range(14):
            ang = 2.0 * math.pi * m / 14
            ca_f = math.cos(ang)
            yy = yc + chord * ca_f - 0.18 * (u ** 1.4) * (1.0 - ca_f) * 0.5
            xx = thick * math.sin(ang) * lerp(0.45, 1.0, (ca_f + 1.0) * 0.5)
            row.append(bm.verts.new((xx, yy, zc)))
        df_rings.append(row)
    for k in range(df_steps):
        for m in range(14):
            mn = (m + 1) % 14
            bm.faces.new((df_rings[k][m], df_rings[k][mn], df_rings[k + 1][mn], df_rings[k + 1][m]))
    bm.faces.new(df_rings[-1])
    n_dorsal_end = len(bm.faces)

    # 2. High-Craft Graceful Arching Pectoral Wings
    for side in (-1.0, 1.0):
        fin_rings = []
        steps = 22
        for k in range(steps + 1):
            u = k / steps
            x = side * lerp(1.32, 7.35, u)
            y = lerp(4.10, -3.75, u ** 1.12)
            z = lerp(-1.10, -2.65 + 0.34 * (u ** 2.2), u ** 0.86)
            chord = lerp(1.42, 0.08, u ** 0.86) * (1.0 + 0.16 * math.sin(u * math.pi))
            tub = 0.075 * math.sin(u * math.pi * 4.5) * smoothstep(0.18, 0.40, u) * smoothstep(0.95, 0.65, u)
            thick = lerp(0.32, 0.026, u ** 0.92)
            ring = []
            for m in range(14):
                ang = 2.0 * math.pi * m / 14
                ca_f = math.cos(ang)
                lead_push = tub if ca_f > 0.3 else 0.0
                ring.append(bm.verts.new((x, y + (chord * ca_f) + lead_push, z + thick * math.sin(ang) * lerp(0.55, 1.0, (ca_f + 1.0) * 0.5))))
            fin_rings.append(ring)
        for k in range(steps):
            for m in range(14):
                mn = (m + 1) % 14
                if side > 0:
                    bm.faces.new((fin_rings[k][m], fin_rings[k + 1][m], fin_rings[k + 1][mn], fin_rings[k][mn]))
                else:
                    bm.faces.new((fin_rings[k][m], fin_rings[k][mn], fin_rings[k + 1][mn], fin_rings[k + 1][m]))
        bm.faces.new(fin_rings[-1] if side > 0 else list(reversed(fin_rings[-1])))
    n_pec_end = len(bm.faces)

    # 3. Crescent Horizontal Tail Flukes with Median Notch
    for side in (-1.0, 1.0):
        fluke_rings = []
        steps = 16
        for k in range(steps + 1):
            u = k / steps
            x = side * lerp(0.16, 3.85, u)
            y = lerp(-10.8, -13.55, u ** 1.22)
            notch_off = 0.34 * math.exp(-((u - 0.06) / 0.10) ** 2)
            z = lerp(0.04, 0.22 * math.sin(u * math.pi), u)
            chord = lerp(1.28, 0.08, u ** 0.88) * (1.0 + 0.24 * math.sin(u * math.pi))
            thick = lerp(0.24, 0.024, u)
            ring = []
            for m in range(14):
                ang = 2.0 * math.pi * m / 14
                ca_f = math.cos(ang)
                yy = y + chord * ca_f + (notch_off if ca_f < 0 else 0.0)
                ring.append(bm.verts.new((x, yy, z + thick * math.sin(ang) * lerp(0.50, 1.0, (ca_f + 1.0) * 0.5))))
            fluke_rings.append(ring)
        for k in range(steps):
            for m in range(14):
                mn = (m + 1) % 14
                if side > 0:
                    bm.faces.new((fluke_rings[k][m], fluke_rings[k + 1][m], fluke_rings[k + 1][mn], fluke_rings[k][mn]))
                else:
                    bm.faces.new((fluke_rings[k][m], fluke_rings[k][mn], fluke_rings[k + 1][mn], fluke_rings[k + 1][m]))
        bm.faces.new(fluke_rings[-1] if side > 0 else list(reversed(fluke_rings[-1])))

    # Assign clean anatomical UVMap aligned to whale_skin_albedo.jpg (v=1 dorsal -> v=0 ventral)
    bm.faces.ensure_lookup_table()
    for fi, f in enumerate(bm.faces):
        for loop in f.loops:
            co = loop.vert.co
            u_co = clamp((12.04 - co.y) / 25.6, 0.0, 1.0)
            if fi < n_body_faces:
                ang = math.atan2(abs(co.x), -(co.z - 0.05))
                loop[uv_lay].uv = (u_co, clamp(ang / math.pi, 0.0, 1.0))
            elif fi < n_dorsal_end:
                loop[uv_lay].uv = (u_co, 0.94)
            elif fi < n_pec_end:
                span = clamp((abs(co.x) - 1.32) / 6.0, 0.0, 1.0)
                loop[uv_lay].uv = (0.58 + 0.30 * span, 0.68 + 0.26 * (1.0 - 0.35 * span))
            else:
                loop[uv_lay].uv = (clamp(u_co, 0.72, 0.99), 0.72 + 0.20 * clamp((co.z + 0.5) / 1.0, 0.0, 1.0))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    whale_obj = finalize_mesh_obj("GEO-WH01_Whale", bm, mat_whale, smooth=True)
    sub = whale_obj.modifiers.new("Subsurf", type="SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    n_v = len(whale_obj.data.vertices)
    base_arr = np.empty((n_v, 3), dtype=np.float32)
    whale_obj.data.vertices.foreach_get("co", base_arr.ravel())

    # Almond-slit Anatomical Eyes nestled deeply inside carved orbital eyelid folds (aligned to cheek slope!)
    y_e, hw_e, zt_e, zb_e, _ = _whale_body_profile(0.255)
    zc_e = 0.5 * (zt_e + zb_e)
    hz_e = 0.5 * (zt_e - zb_e)
    eye_phi = 0.025
    # Surface cheek point before socket recess -> pocket floor is x_surf - 0.38 -> nestle eyeball cleanly visible!
    rostrum_e = smoothstep(0.015, 0.08, 0.255) * (1.0 - smoothstep(0.24, 0.37, 0.255))
    x_surf = hw_e * math.cos(eye_phi) * (1.0 + 0.08 * rostrum_e * (1.0 - math.sin(eye_phi)))
    z_surf = zc_e + hz_e * math.sin(eye_phi)
    y_e_a, hw_a, _, _, _ = _whale_body_profile(0.215)
    y_e_b, hw_b, _, _, _ = _whale_body_profile(0.295)
    cheek_slope = math.atan2(hw_b - hw_a, y_e_b - y_e_a)

    eyes = []
    for side, tag in ((-1.0, "L"), (1.0, "R")):
        bm_e = bmesh.new()
        bmesh.ops.create_uvsphere(bm_e, u_segments=32, v_segments=20, radius=1.0)
        rot_cheek = Matrix.Rotation(side * (-cheek_slope - 0.14), 4, "Z")
        for v in bm_e.verts:
            lx = v.co.x * 0.195
            ly = v.co.y * 0.275
            lz = v.co.z * 0.175
            v.co = rot_cheek @ Vector((lx, ly, lz))
        bmesh.ops.recalc_face_normals(bm_e, faces=bm_e.faces)
        eye = finalize_mesh_obj(f"GEO-WH01_Eye_{tag}", bm_e, mat_eye, smooth=True)
        eye.parent = whale_obj
        # Nestle eyeball cleanly visible (cornea apex ~x_surf - 0.025) framed by upper/lower almond lids!
        base_loc = Vector((side * (x_surf - 0.220), y_e, z_surf))
        eye.location = base_loc
        eyes.append((eye, base_loc))

    return whale_obj, base_arr, eyes


def whale_stroke_wave(phase_u: float) -> float:
    """Asymmetric majestic whale tail stroke (5.2s cycle: slow upward anticipation -> powerful downstroke -> serene glide)."""
    c = phase_u % 1.0
    if c < 0.28:
        # Slow gentle upward anticipation
        return 0.42 * math.sin((c / 0.28) * math.pi * 0.5)
    elif c < 0.50:
        # Deep graceful downward propulsion stroke
        u = (c - 0.28) / 0.22
        return lerp(0.42, -0.95, ease_cubic(u))
    else:
        # Unhurried damped glide recovery
        u = (c - 0.50) / 0.50
        return -0.95 * ((1.0 - ease_cubic(u)) ** 1.35)


def eval_whale_local_point(
    pt: Vector,
    t: float,
    glance_deg: float = 0.0,
    yaw_rate: float = 0.0,
    roll_rate: float = 0.0,
) -> Vector:
    """Scalar twin of deform_whale_sway so parented eyes track carved orbital sockets to sub-mm accuracy!"""
    cycle = 5.2
    x0, y0, z0 = pt.x, pt.y, pt.z
    s_tail = clamp((12.0 - y0) / 24.0, 0.0, 1.0)
    ph = (t / cycle) - s_tail * 0.42
    ang = 2.0 * math.pi * ph
    stroke = 0.62 * math.sin(ang) - 0.28 * math.sin(2.0 * ang - 0.35) + 0.10 * math.cos(3.0 * ang)
    calm_glance = 1.0 - 0.55 * smoothstep(61.8, 63.2, t) * smoothstep(66.2, 64.8, t)
    dz_body = 1.05 * calm_glance * (s_tail ** 1.85) * stroke

    fin_u = clamp((abs(x0) - 1.7) / 5.25, 0.0, 1.0)
    fin_lag = 0.45 * calm_glance * (fin_u ** 1.55) * math.sin(2.0 * math.pi * ((t / cycle) - 0.14 - fin_u * 0.18))
    fin_roll_drag = (-1.0 if x0 > 0 else (1.0 if x0 < 0 else 0.0)) * clamp(roll_rate * 0.28, -0.55, 0.55) * (fin_u ** 1.45)
    dz = dz_body + fin_lag + fin_roll_drag

    curve_bend = clamp(yaw_rate * 2.2, -1.35, 1.35) * ((y0 / 12.0) ** 2 - 0.35)
    dx = curve_bend + 0.22 * calm_glance * (s_tail ** 1.65) * math.cos(ang * 0.65)
    x, y, z = x0 + dx, y0, z0 + dz

    if abs(glance_deg) > 1e-3:
        glance_rad = math.radians(glance_deg)
        hw = clamp((y0 - 2.0) / 8.5, 0.0, 1.0)
        hw = hw * hw * (3.0 - 2.0 * hw)
        a_g = glance_rad * hw
        ca, sa = math.cos(a_g), math.sin(a_g)
        yr = y - 2.0
        x, y = x * ca - yr * sa, 2.0 + x * sa + yr * ca
    return Vector((x, y, z))


def deform_whale_sway(
    whale_obj: bpy.types.Object,
    base_arr: np.ndarray,
    t: float,
    glance_deg: float = 0.0,
    yaw_rate: float = 0.0,
    roll_rate: float = 0.0,
):
    """NumPy-vectorized organic whale deformation:
    - 5.2s stroke-and-glide tail fluke undulation (Disney #2 Anticipation, #9 Timing)
    - Phase-lagged pectoral wingtip flex trailing strokes & barrel roll (Disney #5 Follow-Through)
    - Subtle spine curvature into curved turns (Disney #7 Arc)
    - Gentle head glance toward viewer in C6d (22deg)."""
    cycle = 5.2
    x0 = base_arr[:, 0]
    y0 = base_arr[:, 1]
    z0 = base_arr[:, 2]

    s_tail = np.clip((12.0 - y0) / 24.0, 0.0, 1.0)
    # Travelling stroke wave down the spine (sample piecewise stroke cleanly via smooth harmonic approximation)
    ph = (t / cycle) - s_tail * 0.42
    ang = 2.0 * math.pi * ph
    # Asymmetric stroke-and-glide waveform (Fourier match to anticipation + downstroke + calm glide!)
    stroke = 0.62 * np.sin(ang) - 0.28 * np.sin(2.0 * ang - 0.35) + 0.10 * np.cos(3.0 * ang)
    # Ease stroke amplitude slightly during the tender C6d slow-motion glance (62.5..65.5s)
    calm_glance = 1.0 - 0.55 * smoothstep(61.8, 63.2, t) * smoothstep(66.2, 64.8, t)
    dz_body = 1.05 * calm_glance * (s_tail ** 1.85) * stroke

    # Pectoral fin follow-through flex (|x0| > 1.7m)
    fin_u = np.clip((np.abs(x0) - 1.7) / 5.25, 0.0, 1.0)
    fin_lag = 0.45 * calm_glance * (fin_u ** 1.55) * np.sin(2.0 * math.pi * ((t / cycle) - 0.14 - fin_u * 0.18))
    fin_roll_drag = -np.sign(x0) * clamp(roll_rate * 0.28, -0.55, 0.55) * (fin_u ** 1.45)
    dz = dz_body + fin_lag + fin_roll_drag

    # Subtle spine curvature bending organically into curved trajectory turns
    curve_bend = clamp(yaw_rate * 2.2, -1.35, 1.35) * ((y0 / 12.0) ** 2 - 0.35)
    dx = curve_bend + 0.22 * calm_glance * (s_tail ** 1.65) * np.cos(ang * 0.65)

    x = x0 + dx
    y = y0.copy()
    z = z0 + dz

    # Gentle head glance in C6d (anterior third y0 > 2.0)
    if abs(glance_deg) > 1e-3:
        glance_rad = math.radians(glance_deg)
        hw = np.clip((y0 - 2.0) / 8.5, 0.0, 1.0)
        hw = hw * hw * (3.0 - 2.0 * hw)
        a_g = glance_rad * hw
        ca, sa = np.cos(a_g), np.sin(a_g)
        yr = y - 2.0
        xn = x * ca - yr * sa
        yn = 2.0 + x * sa + yr * ca
        x, y = xn, yn

    out = np.empty_like(base_arr)
    out[:, 0] = x
    out[:, 1] = y
    out[:, 2] = z
    whale_obj.data.vertices.foreach_set("co", out.ravel())
    whale_obj.data.update()


def build_grounded_adventurer(pc_spec: dict, mat_pc) -> tuple[bpy.types.Object, bpy.types.Object]:
    """Grounded clay human adventurer with articulated separate head object for subtle head-turn/look-up acting."""
    h = pc_spec["height"]
    sw = pc_spec["shoulder_w"]
    idx = int(pc_spec["id"][-1])
    bm = bmesh.new()

    def add_cone(target_bm, loc, rx1, ry1, rx2, ry2, depth, rot_x=0.0, rot_y=0.0):
        res = bmesh.ops.create_cone(target_bm, cap_ends=True, cap_tris=False, segments=16, radius1=1.0, radius2=1.0, depth=1.0)
        for v in res["verts"]:
            f = v.co.z + 0.5
            v.co.x *= lerp(rx1, rx2, f)
            v.co.y *= lerp(ry1, ry2, f)
            v.co.z *= depth
        m = Matrix.Translation(loc) @ Matrix.Rotation(rot_x, 4, "X") @ Matrix.Rotation(rot_y, 4, "Y")
        bmesh.ops.transform(target_bm, matrix=m, verts=res["verts"])

    def add_sphere(target_bm, loc, sx, sy, sz):
        res = bmesh.ops.create_uvsphere(target_bm, u_segments=16, v_segments=12, radius=1.0)
        m = Matrix.Translation(loc) @ Matrix.Diagonal((sx, sy, sz, 1.0))
        bmesh.ops.transform(target_bm, matrix=m, verts=res["verts"])

    for sx in (-0.11, 0.11):
        add_cone(bm, (sx, 0.0, h * 0.24), 0.062, 0.085, 0.078, 0.085, h * 0.48)
    hem_z = h * (0.16 if idx in (1, 2) else 0.34)
    waist_z = h * 0.56
    chest_z = h * 0.79
    add_cone(bm, (0.0, 0.0, 0.5 * (hem_z + waist_z)), sw * 0.56, 0.17, sw * 0.36, 0.13, waist_z - hem_z + 0.06)
    add_cone(bm, (0.0, 0.0, 0.5 * (waist_z + chest_z)), sw * 0.36, 0.13, sw * 0.50, 0.16, chest_z - waist_z + 0.06)
    for side in (-1.0, 1.0):
        add_cone(bm, (side * (sw * 0.53), 0.0, h * 0.62), 0.052, 0.055, 0.068, 0.068, h * 0.34, rot_y=side * math.radians(-7.0))
    add_sphere(bm, (0.0, 0.0, h * 0.79), sw * 0.54, 0.16, h * 0.065)
    if idx in (1, 2):
        add_cone(bm, (0.0, -0.10, h * 0.48), sw * 0.58, 0.08, sw * 0.44, 0.06, h * 0.60)
    elif idx == 3:
        for side in (-1.0, 1.0):
            add_sphere(bm, (side * sw * 0.48, 0.0, h * 0.81), 0.11, 0.11, 0.07)

    body_obj = finalize_mesh_obj(f"GEO-{pc_spec['id']}", bm, mat_pc, smooth=True)
    body_obj.location = Vector(pc_spec["pos"])

    # Separate articulated head pivoted at base of neck for subtle look tracking
    bm_h = bmesh.new()
    add_cone(bm_h, (0.0, 0.0, h * 0.03), 0.058, 0.058, 0.052, 0.052, h * 0.07)
    add_sphere(bm_h, (0.0, 0.015, h * 0.105), 0.095, 0.112, h * 0.078)
    head_obj = finalize_mesh_obj(f"GEO-{pc_spec['id']}_Head", bm_h, mat_pc, smooth=True)
    head_obj.parent = body_obj
    head_obj.location = (0.0, 0.0, h * 0.825)
    return body_obj, head_obj


def viaduct_curve(x: float) -> tuple[float, float]:
    """Dead-plumb straight East-West Aqueduct-Causeway axis (y = 40.0m, yaw = 0.0 deg) parallel to the Sanctuary."""
    return 40.0, 0.0


def viaduct_deck_z(x: float) -> float | None:
    """Surviving horizontal masonry ledge elevation along the Heavily-Ruined Plumb Classical Aqueduct
    (returns None across collapsed arch gaps L2/L3/R2/R3 and sacred central breach [-36..+36]!)."""
    ax = abs(x)
    if ax < 36.0 or ax > 108.0:
        return None

    if -40.5 < x <= -36.0:
        return 16.2
    if 36.0 <= x <= 40.5:
        return 20.8
    # Only L1 (-60..-40.5) and R1 (+40.5..+60) retain continuous stripped z=12.8m arch roadbeds!
    if -60.0 <= x <= -40.5 or 40.5 <= x <= 60.0:
        return 12.8
    # Outer pier tops around +-61.5m and +-83.5m
    if abs(ax - 83.5) < 2.2:
        return 14.6 if x < 0 else 15.0
    return None



def build_ruined_arch_bridge(bridge_spec: dict, mat_stone, rng: random.Random) -> bpy.types.Object:
    """v7.9 Heavily Ruined Plumb Dual-Tier Roman Aqueduct (yaw = 0.0 deg, tilt = 0.0 deg, heavier collapse than Sanctuary!):
    - Every surviving pier, pilaster, archivolt & cornice remains dead plumb & horizontal so original construction is unmistakable.
    - Dramatic multi-tier destruction > Sanctuary weathering:
      * 72m Central Sacred Breach ([-36, +36]) with asymmetrical broken terminal piers (Left sheared to z=16.2m; Right z=21.8m)
      * Inner upper-arcade bays (-48..-38m and +40..+50m) sheared cleanly away down to exposed z=12.8m mid-roadbed!
      * Bay R2b (+72..+84m) loses upper arch & crown, leaving tall broken Doric pilasters standing skyward!
      * Outer Water Arches L3 (-108..-84m) & R3 (+84..+108m) COMPLETELY collapsed across the river channel, leaving
        twin submerged cutwater piers, broken archivolts, and fallen masonry chunks on waterline shoals!"""
    thick = bridge_spec["thickness"]
    bm = bmesh.new()

    def add_box_local(m_base: Matrix, lx, ly, lz, sx, sy, sz, rx=0.0, ry=0.0, rz=0.0):
        res = bmesh.ops.create_cube(bm, size=1.0)
        m = (
            m_base
            @ Matrix.Translation((lx, ly, lz))
            @ Euler((rx, ry, rz), "XYZ").to_matrix().to_4x4()
            @ Matrix.Diagonal((sx, sy, sz, 1.0))
        )
        bmesh.ops.transform(bm, matrix=m, verts=res["verts"])

    def add_semicircular_spandrel(m_span: Matrix, half_w: float, half_t: float, z_bot: float, spring_z: float, clear_r: float, z_top: float, n_arc: int = 24):
        arch_pts = []
        for k in range(n_arc + 1):
            ang = lerp(0.0, math.pi, k / n_arc)
            arch_pts.append((clear_r * math.cos(ang), spring_z + clear_r * math.sin(ang)))
        pts_xz = [(-half_w, z_bot), (-half_w, z_top), (half_w, z_top), (half_w, z_bot), (clear_r, z_bot)]
        pts_xz.extend(arch_pts)
        pts_xz.append((-clear_r, z_bot))
        fv = [bm.verts.new(m_span @ Vector((px, -half_t, pz))) for (px, pz) in pts_xz]
        bv = [bm.verts.new(m_span @ Vector((px,  half_t, pz))) for (px, pz) in pts_xz]
        bm.faces.new(fv)
        bm.faces.new(list(reversed(bv)))
        n = len(pts_xz)
        for i in range(n):
            ni = (i + 1) % n
            bm.faces.new((fv[i], bv[i], bv[ni], fv[ni]))
        return arch_pts

    def add_archivolt_band(m_bay: Matrix, spring_z: float, clear_r: float, r_thick: float, y_half: float, a0_deg: float = 0.0, a1_deg: float = 180.0, n_ar: int = 24):
        """Smooth concentric Roman archivolt ring segment (full 180 deg intact or partial broken haunch!)."""
        r_out_a = clear_r + r_thick
        ring_f, ring_b = [], []
        for k in range(n_ar + 1):
            ang = math.radians(lerp(a0_deg, a1_deg, k / n_ar))
            ca, sa = math.cos(ang), math.sin(ang)
            ring_f.append((
                bm.verts.new(m_bay @ Vector((clear_r * ca, -y_half, spring_z + clear_r * sa))),
                bm.verts.new(m_bay @ Vector((r_out_a * ca, -y_half, spring_z + r_out_a * sa))),
            ))
            ring_b.append((
                bm.verts.new(m_bay @ Vector((clear_r * ca,  y_half, spring_z + clear_r * sa))),
                bm.verts.new(m_bay @ Vector((r_out_a * ca,  y_half, spring_z + r_out_a * sa))),
            ))
        for k in range(n_ar):
            ri0, ro0 = ring_f[k]
            ri1, ro1 = ring_f[k + 1]
            bi0, bo0 = ring_b[k]
            bi1, bo1 = ring_b[k + 1]
            bm.faces.new((ri0, ro0, ro1, ri1))
            bm.faces.new((bi0, bi1, bo1, bo0))
            bm.faces.new((ro0, bo0, bo1, ro1))
            bm.faces.new((ri0, ri1, bi1, bi0))
        bm.faces.new((ring_f[0][0], ring_b[0][0], ring_b[0][1], ring_f[0][1]))
        bm.faces.new((ring_f[-1][0], ring_f[-1][1], ring_b[-1][1], ring_b[-1][0]))

    def add_aqueduct_lower_piers_only(x0: float, x1: float, max_pier_z: float = 10.6, stub_deg: float = 28.0):
        """Collapsed Lower Water Arch bay: vertical submerged piers + broken archivolt stubs open to lake & stars!"""
        xc = 0.5 * (x0 + x1)
        yc, yaw = viaduct_curve(xc)
        m_bay = Matrix.Translation((xc, yc, 0.0)) @ Matrix.Rotation(yaw, 4, "Z")
        half_w = (x1 - x0) * 0.5
        half_t = thick * 0.5
        clear_r1 = 8.4
        spring1 = 2.0
        pier_cx = 0.5 * (half_w + clear_r1)
        pier_w_side = half_w - clear_r1
        for sx in (-pier_cx, pier_cx):
            add_box_local(m_bay, sx, 0.0, -1.2, pier_w_side + 1.2, thick + 2.2, 6.2)
            add_box_local(m_bay, sx, 0.0, spring1 + 0.1, pier_w_side + 0.9, thick + 1.2, 0.95)
            h_p = max_pier_z - spring1
            add_box_local(m_bay, sx, 0.0, spring1 + h_p * 0.5, pier_w_side * 1.15, thick, h_p)
        if stub_deg > 5.0:
            add_archivolt_band(m_bay, spring1, clear_r1, 0.90, half_t + 0.28, 0.0, stub_deg, n_ar=8)
            add_archivolt_band(m_bay, spring1, clear_r1, 0.90, half_t + 0.28, 180.0 - stub_deg * 0.7, 180.0, n_ar=6)

    def add_classical_aqueduct_bay(x0: float, x1: float, upper_mode: str = "full"):
        """Modular 2-tier Aqueduct bay supporting authentic partial upper ruin modes:
        'full' | 'left_only' | 'right_only' | 'skeletal_right' | 'stripped'."""
        xc = 0.5 * (x0 + x1)
        yc, yaw = viaduct_curve(xc)
        m_bay = Matrix.Translation((xc, yc, 0.0)) @ Matrix.Rotation(yaw, 4, "Z")
        bay_w = x1 - x0
        half_w = bay_w * 0.5
        half_t = thick * 0.5
        clear_r1 = 8.4
        spring1 = 2.0
        top1 = 12.0

        add_semicircular_spandrel(m_bay, half_w, half_t, -4.5, spring1, clear_r1, top1, n_arc=26)
        add_archivolt_band(m_bay, spring1, clear_r1, 0.90, half_t + 0.30, 0.0, 180.0, n_ar=26)
        add_box_local(m_bay, 0.0, 0.0, spring1 + clear_r1 + 0.42, 1.35, thick + 1.05, 1.55)

        pier_cx = 0.5 * (half_w + clear_r1)
        pier_w_side = half_w - clear_r1
        for sx in (-pier_cx, pier_cx):
            add_box_local(m_bay, sx, 0.0, -1.2, pier_w_side + 1.2, thick + 2.2, 6.2)
            add_box_local(m_bay, sx, 0.0, spring1 + 0.1, pier_w_side + 0.9, thick + 1.2, 0.95)
            add_box_local(m_bay, sx, 0.0, 0.5 * (spring1 + top1), pier_w_side * 0.68, thick + 0.65, top1 - spring1 - 0.8)

        # Continuous Horizontal Mid-Impost Cornice Roadbed (z = 11.8..12.8m)
        add_box_local(m_bay, 0.0, 0.0, 12.3, bay_w + 0.1, thick + 1.15, 1.05)
        if upper_mode in ("stripped", "broken_pier_left", "broken_pier_right"):
            # Entire upper tier collapsed down to flat z=12.8m roadbed — plus at most 1 solitary upright broken pier shaft!
            if upper_mode == "broken_pier_left":
                add_box_local(m_bay, -half_w * 0.72, 0.0, 15.6, 2.2, thick * 0.94, 5.6)
                add_box_local(m_bay, -half_w * 0.35, 0.0, 13.7, 2.4, thick * 0.84, 1.8)
            elif upper_mode == "broken_pier_right":
                add_box_local(m_bay,  half_w * 0.72, 0.0, 15.8, 2.2, thick * 0.94, 6.0)
                add_box_local(m_bay,  half_w * 0.35, 0.0, 13.6, 2.4, thick * 0.84, 1.6)
            for bi in (-1, 0, 1):
                if rng.random() < 0.40:
                    add_box_local(m_bay, bi * 4.8, rng.uniform(-1.1, 1.1), 13.05, rng.uniform(2.4, 3.8), 1.5, rng.uniform(0.45, 0.95))
            return

        ux_list = [(-bay_w * 0.25, "L"), (bay_w * 0.25, "R")]
        for ux, tag in ux_list:
            keep_full = (
                upper_mode == "full"
                or (upper_mode == "left_only" and tag == "L")
                or (upper_mode == "right_only" and tag == "R")
                or (upper_mode == "skeletal_right" and tag == "L")
            )
            if keep_full:
                m_u = m_bay @ Matrix.Translation((ux, 0.0, 0.0))
                arch2 = add_semicircular_spandrel(m_u, bay_w * 0.25, half_t * 0.86, 12.8, 14.4, 3.4, 19.6, n_arc=18)
                mid_k = arch2[len(arch2) // 2]
                add_box_local(m_u, mid_k[0], 0.0, mid_k[1] + 0.2, 0.85, thick * 0.96, 0.95)
                add_box_local(m_u, 0.0, 0.0, 19.85, bay_w * 0.5 + 0.1, thick + 0.75, 0.80)
                add_box_local(m_u, 0.0, 0.0, 20.45, bay_w * 0.5 + 0.1, thick + 1.25, 0.70)
            elif upper_mode == "skeletal_right" and tag == "R":
                # Upright broken Doric pilasters standing skyward without arch crown!
                add_box_local(m_bay, ux - bay_w * 0.25, 0.0, 16.0, 1.65, thick * 0.96, 6.4)
                add_box_local(m_bay, ux + bay_w * 0.25, 0.0, 15.2, 1.65, thick * 0.96, 4.8)
            else:
                # Half-collapsed broken upper stub right next to the surviving arch
                sub_x = ux + (bay_w * 0.18 if tag == "L" else -bay_w * 0.18)
                add_box_local(m_bay, sub_x, 0.0, 14.6, 3.0, thick * 0.86, 3.6)

        for px, cond in ((-half_w, upper_mode in ("full", "left_only", "skeletal_right")), (0.0, upper_mode != "stripped"), (half_w, upper_mode in ("full", "right_only"))):
            if cond:
                add_box_local(m_bay, px, 0.0, 16.1, 1.65, thick * 0.96, 6.8)
                add_box_local(m_bay, px, 0.0, 19.1, 2.05, thick * 1.06, 0.75)

    # HEAVY RUINED LEFT AQUEDUCT WING (-132 .. -36m): ONLY 1 lower arch survives intact, 3 outer vaults collapsed!
    add_aqueduct_lower_piers_only(-132.0, -108.0, max_pier_z=6.8, stub_deg=0.0)
    add_aqueduct_lower_piers_only(-108.0,  -84.0, max_pier_z=9.6, stub_deg=24.0)    # L3 outer water arch collapsed!
    add_aqueduct_lower_piers_only( -84.0,  -60.0, max_pier_z=14.6, stub_deg=44.0)   # L2 SHATTERED OPEN ARCH OVER LAKE!
    add_classical_aqueduct_bay(    -60.0,  -36.0, upper_mode="broken_pier_left")    # L1 1 surviving lower arch + bare deck & pier stub!

    # HEAVY RUINED RIGHT AQUEDUCT WING (+36 .. +132m) — unmistakably heavier destruction than Sanctuary in C6a/C6b/C6c!
    add_classical_aqueduct_bay(     36.0,   60.0, upper_mode="broken_pier_right")   # R1 1 surviving lower arch, upper arcade GONE!
    add_aqueduct_lower_piers_only(  60.0,   84.0, max_pier_z=15.0, stub_deg=46.0)   # R2 SHATTERED ARCH VAULT GAPING TO STARS!
    add_aqueduct_lower_piers_only(  84.0,  108.0, max_pier_z=10.2, stub_deg=26.0)   # R3 sunken east piers & archivolts!
    add_aqueduct_lower_piers_only( 108.0,  132.0, max_pier_z=6.8, stub_deg=0.0)

    # TWIN ASYMMETRICALLY WEATHERED PLUMB TERMINAL PYLONS (x = -37.6m sheared to 16.2m; x = +37.6m weathered 20.8m!)
    for side, p_top in ((-1.0, 16.2), (1.0, 20.8)):
        px = side * 37.6
        py, pyaw = viaduct_curve(px)
        m_p = Matrix.Translation((px, py, 0.0)) @ Matrix.Rotation(pyaw, 4, "Z")
        add_box_local(m_p, 0.0, 0.0, 0.2, 7.6, thick + 2.8, 9.5)
        add_box_local(m_p, 0.0, 0.0, p_top * 0.5, 6.2, thick + 1.6, p_top)
        add_box_local(m_p, 0.0, 0.0, 12.3, 6.8, thick + 2.2, 1.1)
        if p_top > 20.0:
            add_box_local(m_p, 0.0, 0.0, 19.9, 6.8, thick + 2.2, 0.9)
            add_box_local(m_p, -1.1, 0.0, 20.8, 4.0, thick + 1.8, 0.9)
        for lx in (-2.0, 2.0):
            add_box_local(m_p, lx, -(thick * 0.5 + 0.65), p_top * 0.5, 1.3, 0.7, max(4.0, p_top - 2.2))
            add_box_local(m_p, lx,  (thick * 0.5 + 0.65), p_top * 0.5, 1.3, 0.7, max(4.0, p_top - 2.2))
        in_dir = -side
        add_box_local(m_p, in_dir * 3.8, 0.0, 12.3, 2.2, thick + 1.1, 1.05)

    # Low Fallen Aqueduct Masonry Shoal Debris strictly beneath broken bays (|x| >= 32m, C6c mirror lane 100% clear!)
    m_world = Matrix.Identity(4)
    debris = [
        (-33.5, 39.2, 0.4, 4.6, 3.8, 2.4, 0.08, 0.14, 0.35),
        ( 33.8, 40.8, 0.5, 4.8, 4.0, 2.6, -0.06, -0.12, -0.28),
        (-71.5, 40.2, 0.5, 6.2, 4.2, 2.5, 0.05, 0.16, 0.32),
        ( 71.0, 39.6, 0.6, 6.6, 4.4, 2.8, -0.06, 0.18, -0.24),
        ( 93.0, 39.5, 0.6, 6.4, 4.4, 2.8, 0.05, 0.18, 0.22),
        (-95.0, 40.4, 0.5, 6.0, 4.2, 2.6, 0.04, -0.16, -0.40),
    ]
    for db in debris:
        add_box_local(m_world, *db)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bridge_obj = finalize_mesh_obj("GEO-ArchBridge", bm, mat_stone, smooth=False)
    bev = bridge_obj.modifiers.new("Bevel", type="BEVEL")
    bev.width = 0.12
    bev.segments = 2
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(40.0)
    return bridge_obj


def build_sunken_sanctuary_city(mat_city, rng: random.Random) -> bpy.types.Object:
    """v8.0 Colossal Museum-Scale Greco-Roman Acropolis-Pantheon Sanctuary (y = 178m, 188m wide x 104m tall, 0.0 deg plumb!):
    Calibrated to National Museum of Nature & Science (Ueno) scale relative to the 24m Whale:
    - 2.5x higher architectural component frequency (7 dense arcade bays per wing, 12-column fluted portico,
      2-tier arched Rotunda drum, 22-stepped processional stair, fine balustrade cornices) immediately triggers authentic megalithic scale!
    - Tier 1 (z = -4..21.6m): Dense flooded classical retaining arcades (7 per wing) & 22-flight Axial Staircase.
    - Tier 2 (z = 21.6..60.5m): Dodecastyle (12-column) fluted Parthenon Portico (broken step-wise on #6..#11) + Two-Tier Stoa Wings.
    - Tier 3 (z = 47..104.0m): Double-tier 28-bay Pantheon Rotunda Drum + 24-rib Coffered Dome with wide Front-Right Fracture."""
    bm = bmesh.new()

    def add_box_m(m_base: Matrix, lx, ly, lz, sx, sy, sz, rx=0.0, ry=0.0, rz=0.0):
        res = bmesh.ops.create_cube(bm, size=1.0)
        m = m_base @ Matrix.Translation((lx, ly, lz)) @ Euler((rx, ry, rz), "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal((sx, sy, sz, 1.0))
        bmesh.ops.transform(bm, matrix=m, verts=res["verts"])

    def add_cyl_m(m_base: Matrix, lx, ly, lz, r1, r2, depth, segs=16):
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r1, radius2=r2, depth=depth)
        bmesh.ops.transform(bm, matrix=m_base @ Matrix.Translation((lx, ly, lz)), verts=res["verts"])

    def add_fluted_column(m_base: Matrix, lx: float, ly: float, z_base: float, h: float, r_bot: float, r_top: float, n_flutes: int = 16, broken_h: float | None = None):
        """Build a plumb 16-flute classical Doric column with Attic base plinth, entasis shaft & capital."""
        add_box_m(m_base, lx, ly, z_base + 0.40, r_bot * 2.25, r_bot * 2.25, 0.80)
        add_cyl_m(m_base, lx, ly, z_base + 0.95, r_bot * 1.18, r_bot * 1.06, 0.42, segs=16)

        actual_h = broken_h if broken_h is not None else (h - 1.45)
        n_rings = 7
        n_verts_ring = n_flutes * 2
        rings = []
        for ir in range(n_rings):
            u = ir / (n_rings - 1)
            z = z_base + 1.15 + u * max(0.8, actual_h - 1.15)
            r_u = lerp(r_bot, r_top, u * (actual_h / max(1.0, h - 1.45))) + 0.03 * math.sin(u * math.pi)
            row = []
            for j in range(n_verts_ring):
                ang = 2.0 * math.pi * j / n_verts_ring
                flute_r = r_u * (1.0 if (j % 2 == 0) else 0.89)
                row.append(bm.verts.new(m_base @ Vector((lx + flute_r * math.cos(ang), ly + flute_r * math.sin(ang), z))))
            rings.append(row)
        for ir in range(n_rings - 1):
            for j in range(n_verts_ring):
                jn = (j + 1) % n_verts_ring
                bm.faces.new((rings[ir][j], rings[ir][jn], rings[ir + 1][jn], rings[ir + 1][j]))
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])

        if broken_h is None:
            cap_z = z_base + h - 1.25
            add_cyl_m(m_base, lx, ly, cap_z + 0.30, r_top * 0.98, r_top * 1.38, 0.65, segs=16)
            add_box_m(m_base, lx, ly, cap_z + 0.88, r_top * 2.75, r_top * 2.75, 0.60)

    def add_classical_arcade_bay(m_base: Matrix, cx: float, cy: float, bay_w: float, thick: float, z_bot: float, spring_z: float, clear_r: float, z_top: float, n_arc: int = 14):
        """Extrude one plumb semicircular classical arch spandrel bay cleanly aligned to horizontal cornices."""
        m_bay = m_base @ Matrix.Translation((cx, cy, 0.0))
        half_w = bay_w * 0.5
        half_t = thick * 0.5
        arch_pts = []
        for k in range(n_arc + 1):
            ang = lerp(0.0, math.pi, k / n_arc)
            arch_pts.append((clear_r * math.cos(ang), spring_z + clear_r * math.sin(ang)))
        pts_xz = [(-half_w, z_bot), (-half_w, z_top), (half_w, z_top), (half_w, z_bot), (clear_r, z_bot)]
        pts_xz.extend(arch_pts)
        pts_xz.append((-clear_r, z_bot))
        fv = [bm.verts.new(m_bay @ Vector((px, -half_t, pz))) for (px, pz) in pts_xz]
        bv = [bm.verts.new(m_bay @ Vector((px,  half_t, pz))) for (px, pz) in pts_xz]
        bm.faces.new(fv)
        bm.faces.new(list(reversed(bv)))
        n = len(pts_xz)
        for i in range(n):
            ni = (i + 1) % n
            bm.faces.new((fv[i], bv[i], bv[ni], fv[ni]))
        pier_cx = 0.5 * (half_w + clear_r)
        for sx in (-pier_cx, pier_cx):
            add_box_m(m_base, cx + sx, cy, 0.5 * (z_bot + z_top), (half_w - clear_r) * 0.72, thick + 0.6, z_top - z_bot)
        add_box_m(m_base, cx, cy, spring_z + clear_r + 0.12, 0.75, thick + 0.75, 0.90)

    # STRICT 0.0-DEGREE PLUMB & HORIZONTAL MASTER FRAME (y = 178.0m, 188m total facade span, crown z = 104m)
    m_cit = Matrix.Translation((2.0, 178.0, 0.0))

    # --- TIER 1 (z = -4.0 .. 21.6m): DENSE 7-BAY WATERFRONT ARCADED TERRACE & 22-FLIGHT STAIRCASE ---
    add_box_m(m_cit, 0.0, 13.0, 8.8, 184.0, 50.0, 25.6)
    add_box_m(m_cit, 0.0,  0.0, 21.1, 188.0, 52.0, 1.15)  # Broad horizontal Sacred Podium Datum z = 21.6m

    for side in (-1.0, 1.0):
        for bi in range(7):
            cx = side * (22.5 + bi * 10.0)
            if bi == 6 or (side > 0 and bi == 5):
                # Outer wing edges weathered lower into stepped pier blocks
                add_box_m(m_cit, cx - side * 2.0, -19.5, 4.2 if side < 0 else 2.6, 8.6, 4.2, 16.0 if side < 0 else 12.8)
                continue
            add_classical_arcade_bay(m_cit, cx, -19.5, bay_w=10.0, thick=3.8, z_bot=-4.0, spring_z=3.8, clear_r=3.1, z_top=21.0, n_arc=14)
        add_box_m(m_cit, side * 52.0, -19.5, 11.4, 68.0, 4.6, 0.85)
        add_box_m(m_cit, side * 50.0, -19.5, 21.1, 64.0, 5.0, 1.05)

    # Monumental 22-Flight Axial Processional Staircase sweeping smoothly out of water (z = -2.0 -> 21.6m)
    for st in range(22):
        u = st / 21.0
        sy = lerp(-34.0, -16.0, u)
        sz = lerp(-2.0, 21.0, u)
        sw = lerp(35.0, 28.0, u)
        add_box_m(m_cit, 0.0, sy, sz - 4.0, sw, 1.45, 9.0)
    for sx in (-18.0, 18.0):
        add_box_m(m_cit, sx, -24.5, 6.5, 3.2, 19.5, 21.5)
        add_box_m(m_cit, sx, -29.0, 1.5, 4.0, 10.5, 12.5)

    # --- TIER 2 (z = 21.6 .. 60.5m): DODECASTYLE (12-COLUMN) PARTHENON & DENSE 2-TIER STOA GALLERIES ---
    for sx_w in (-58.0, 58.0):
        add_box_m(m_cit, sx_w, -3.5, 33.8, 62.0, 3.8, 24.4)
    for side in (-1.0, 1.0):
        for bi in range(7):
            cx = side * (30.5 + bi * 8.4)
            if side > 0 and bi >= 5:
                if bi == 5:
                    add_box_m(m_cit, cx - 2.6, -12.0, 26.2, 2.0, 3.6, 9.2)
                continue
            add_classical_arcade_bay(m_cit, cx, -12.0, bay_w=8.4, thick=3.2, z_bot=21.6, spring_z=24.8, clear_r=2.5, z_top=34.0, n_arc=14)
            if (side < 0 and bi >= 4) or (side > 0 and bi >= 2):
                if bi in (2, 4):
                    add_box_m(m_cit, cx - side * 2.8, -12.0, 37.8, 1.8, 3.4, 6.8)
                continue
            add_classical_arcade_bay(m_cit, cx, -12.0, bay_w=8.4, thick=2.9, z_bot=34.4, spring_z=37.4, clear_r=2.3, z_top=46.6, n_arc=14)
        add_box_m(m_cit, side * (56.0 if side < 0 else 47.0), -12.0, 34.2, 60.0 if side < 0 else 42.0, 4.0, 0.95)
        if side < 0:
            add_box_m(m_cit, -43.0, -12.0, 46.8, 34.0, 4.2, 1.15)
        else:
            add_box_m(m_cit,  34.5, -12.0, 46.8, 17.5, 4.2, 1.15)

    # Central Dodecastyle (12-Column!) Fluted Parthenon Portico (z = 21.6 .. 60.5m)
    for step_i in range(3):
        add_box_m(m_cit, 0.0, -4.5, 22.05 + step_i * 0.85, 56.0 - step_i * 1.4, 25.5 - step_i * 1.0, 0.90)

    add_box_m(m_cit, -13.0, 2.0, 35.5, 16.5, 11.0, 23.0)
    add_box_m(m_cit,  13.0, 2.0, 35.5, 16.5, 11.0, 23.0)
    add_box_m(m_cit,   0.0, 2.0, 43.2, 14.0, 11.0, 7.2)
    add_box_m(m_cit,   0.0, 6.2, 35.5, 44.0,  3.8, 23.0)

    # 12 Slim Fluted Doric Columns (#0-#5 full height 22.0m supporting pediment; #6..#11 weathered downward!)
    front_cols = [lerp(-24.2, 24.2, k / 11.0) for k in range(12)]
    col_breaks = {6: 18.2, 7: 14.8, 8: 11.2, 9: 7.8, 10: 4.8, 11: 2.2}
    for k, cx in enumerate(front_cols):
        add_fluted_column(m_cit, cx, -15.4, 24.2, 22.2, 1.06, 0.86, n_flutes=16, broken_h=col_breaks.get(k))

    for sx in (-24.2, 24.2):
        for sy in (-8.8, -2.0, 4.8):
            if sx > 0 and sy < 0.0:
                add_fluted_column(m_cit, sx, sy, 24.2, 22.2, 1.04, 0.84, n_flutes=16, broken_h=10.5)
            else:
                add_fluted_column(m_cit, sx, sy, 24.2, 22.2, 1.04, 0.84, n_flutes=16, broken_h=None)

    # Bold Horizontal 3-Band Entablature + 15 Triglyphs + Dead-Horizontal Sheared Pediment (broken x > +4.2m!)
    add_box_m(m_cit, -10.8, -15.2, 47.05, 30.8, 3.8, 1.25)
    add_box_m(m_cit, -10.8, -15.2, 48.50, 30.6, 3.6, 1.55)
    for tx in [lerp(-24.8, 3.6, ti / 13.0) for ti in range(14)]:
        add_box_m(m_cit, tx, -17.10, 48.50, 0.88, 0.42, 1.50)
    add_box_m(m_cit, -10.8, -15.3, 49.70, 32.0, 4.6, 0.95)

    y_tf, y_tb = -17.3, -13.3
    tymp_pts = [(-26.4, 50.0), (0.0, 60.2), (3.8, 58.2), (5.2, 54.4), (4.2, 50.0)]
    tf = [bm.verts.new(m_cit @ Vector((px, y_tf + 1.1, pz))) for px, pz in tymp_pts]
    tb = [bm.verts.new(m_cit @ Vector((px, y_tb, pz))) for px, pz in tymp_pts]
    bm.faces.new(tf)
    bm.faces.new(list(reversed(tb)))
    for i in range(len(tymp_pts)):
        ni = (i + 1) % len(tymp_pts)
        bm.faces.new((tf[i], tb[i], tb[ni], tf[ni]))
    add_box_m(m_cit, -13.4, -15.3, 55.2, 28.8, 5.2, 1.15, ry=math.radians(-21.2))
    add_box_m(m_cit,   2.4, -15.3, 59.3,  5.6, 5.2, 1.15, ry=math.radians( 21.2))
    add_box_m(m_cit, -10.2,  -4.2, 48.2, 33.5, 22.8, 3.5)

    # --- TIER 3 (z = 47.0 .. 104.0m): TWO-STORY 28-BAY PANTHEON ROTUNDA DRUM & 24-RIB DOME ---
    drum_cx, drum_cy = 0.0, 15.0
    drum_r = 22.8
    n_bays = 28
    res_db = bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=drum_r + 1.3, radius2=drum_r + 1.1, depth=5.6)
    bmesh.ops.transform(bm, matrix=m_cit @ Matrix.Translation((drum_cx, drum_cy, 49.0)), verts=res_db["verts"])
    for ring_z, ring_ext, ring_h in ((51.6, 1.35, 1.2), (62.8, 1.25, 1.2), (76.4, 1.70, 1.5)):
        res_rc = bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=drum_r + ring_ext, radius2=drum_r + ring_ext, depth=ring_h)
        bmesh.ops.transform(bm, matrix=m_cit @ Matrix.Translation((drum_cx, drum_cy, ring_z)), verts=res_rc["verts"])

    for dk in range(n_bays):
        az = 2.0 * math.pi * dk / n_bays
        px = drum_cx + (drum_r - 0.5) * math.cos(az)
        py = drum_cy + (drum_r - 0.5) * math.sin(az)
        aw_p = math.atan2(math.sin(az), math.cos(az))
        pier_h = 18.2 if (-1.34 <= aw_p <= 0.48) else 25.0
        add_box_m(m_cit, px, py, 51.6 + pier_h * 0.5, 2.0, 2.8, pier_h, rz=az)
        add_box_m(m_cit, px, py, 51.6 + pier_h * 0.5, 2.5, 1.4, pier_h, rz=az)
        az_mid = az + math.pi / n_bays
        aw_m = math.atan2(math.sin(az_mid), math.cos(az_mid))
        mx = drum_cx + (drum_r - 0.4) * math.cos(az_mid)
        my = drum_cy + (drum_r - 0.4) * math.sin(az_mid)
        if not (-1.40 <= aw_m <= 0.54):
            add_box_m(m_cit, mx, my, 73.2, 2.0, 4.0, 6.0, rz=az_mid)
            add_box_m(m_cit, mx, my, 62.6, 2.0, 4.0, 4.4, rz=az_mid)
            add_box_m(m_cit, mx, my, 52.0, 2.0, 4.0, 4.6, rz=az_mid)

    dome_c = Vector((drum_cx, drum_cy, 76.6))
    r_out = 22.4
    r_in = 20.6
    dome_scale_z = 1.22  # crown oculus rises smoothly to z ~ 103.5m!
    for s_i, (sr_off, sz_off, sh_ring) in enumerate(((1.2, 0.7, 1.6), (0.35, 2.2, 1.5), (-0.65, 3.6, 1.4))):
        res_sr = bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=r_out + sr_off, radius2=r_out + sr_off - 0.35, depth=sh_ring)
        bmesh.ops.transform(bm, matrix=m_cit @ Matrix.Translation((drum_cx, drum_cy, dome_c.z + sz_off)), verts=res_sr["verts"])

    def _dome_breach_cut(az_val: float) -> float | None:
        """Wider Front-Right Observatory Dome collapse facing camera & exposing hollowed interior coffered vault!"""
        aw = math.atan2(math.sin(az_val), math.cos(az_val))
        if -1.45 <= aw <= 0.62:
            return math.radians(10.0 + 18.0 * math.cos((aw + 0.42) * 1.6) + 5.0 * math.sin(aw * 6.0))
        return None


    n_lat, n_lon = 14, 40
    for il in range(n_lat - 1):
        el0 = lerp(0.0, math.radians(76.0), il / (n_lat - 1))
        el1 = lerp(0.0, math.radians(76.0), (il + 1) / (n_lat - 1))
        for io in range(n_lon):
            az0 = 2.0 * math.pi * io / n_lon
            az1 = 2.0 * math.pi * (io + 1) / n_lon
            az_mid = 0.5 * (az0 + az1)
            cut_el = _dome_breach_cut(az_mid)
            if cut_el is not None and el1 > cut_el:
                continue
            corners_o, corners_i = [], []
            for el, az in ((el0, az0), (el0, az1), (el1, az1), (el1, az0)):
                ca, sa, ce, se = math.cos(az), math.sin(az), math.cos(el), math.sin(el)
                vo = dome_c + Vector((r_out * ce * ca, r_out * ce * sa, r_out * se * dome_scale_z))
                vi = dome_c + Vector((r_in  * ce * ca, r_in  * ce * sa, r_in  * se * dome_scale_z))
                corners_o.append(bm.verts.new(m_cit @ vo))
                corners_i.append(bm.verts.new(m_cit @ vi))
            bm.faces.new(corners_o)
            bm.faces.new(list(reversed(corners_i)))
            for s in range(4):
                sn = (s + 1) % 4
                bm.faces.new((corners_o[s], corners_o[sn], corners_i[sn], corners_i[s]))

    # 24 Smooth Continuous Meridian Coffer Ribs curving uninterruptedly up the monumental Dome!
    for rk in range(24):
        az_c = 2.0 * math.pi * rk / 24.0
        cut_el = _dome_breach_cut(az_c)
        max_rib_el = min(math.radians(76.0), cut_el) if cut_el is not None else math.radians(76.0)
        if max_rib_el <= math.radians(10.0):
            continue
        n_rs = 12
        rib_rings = []
        for ir in range(n_rs + 1):
            el = lerp(0.02, max_rib_el, ir / n_rs)
            ca, sa, ce, se = math.cos(az_c), math.sin(az_c), math.cos(el), math.sin(el)
            tx, ty = -sa, ca
            hw = 0.34 * lerp(1.0, 0.56, ir / n_rs)
            c0 = dome_c + Vector((r_out * ce * ca, r_out * ce * sa, r_out * se * dome_scale_z))
            c1 = dome_c + Vector(((r_out + 0.50) * ce * ca, (r_out + 0.50) * ce * sa, (r_out + 0.50) * se * dome_scale_z))
            v_il = bm.verts.new(m_cit @ (c0 - Vector((tx * hw, ty * hw, 0.0))))
            v_ir = bm.verts.new(m_cit @ (c0 + Vector((tx * hw, ty * hw, 0.0))))
            v_or = bm.verts.new(m_cit @ (c1 + Vector((tx * hw * 0.72, ty * hw * 0.72, 0.0))))
            v_ol = bm.verts.new(m_cit @ (c1 - Vector((tx * hw * 0.72, ty * hw * 0.72, 0.0))))
            rib_rings.append((v_il, v_ir, v_or, v_ol))
        for ir in range(n_rs):
            for s in range(4):
                sn = (s + 1) % 4
                bm.faces.new((rib_rings[ir][s], rib_rings[ir][sn], rib_rings[ir + 1][sn], rib_rings[ir + 1][s]))
        bm.faces.new(list(reversed(rib_rings[0])))
        bm.faces.new(rib_rings[-1])

    # Pantheon Crown Oculus Stone Collar Ring
    r_oc = r_out * math.cos(math.radians(76.0))
    z_oc = dome_c.z + r_out * math.sin(math.radians(76.0)) * dome_scale_z
    for ok in range(24):
        az = 2.0 * math.pi * ok / 24.0
        if _dome_breach_cut(az) is not None:
            continue
        add_box_m(m_cit, dome_c.x + r_oc * math.cos(az), dome_c.y + r_oc * math.sin(az), z_oc, 1.3, 1.8, 0.85, rz=az)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    city_obj = finalize_mesh_obj("GEO-SunkenSanctuaryCity", bm, mat_city, smooth=False)
    bev = city_obj.modifiers.new("Bevel", type="BEVEL")
    bev.width = 0.14
    bev.segments = 2
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(42.0)
    return city_obj


def build_cavern_roof_canopy(mat_roof, rng: random.Random) -> bpy.types.Object:
    """v8.3 Seamless Radial-Lofted Torn-Sky-Rift Cavern Dome (ZERO rectangular stair-steps!):
    Lofts 10 smooth radial tiers outward from a continuous 160-segment organic jagged Sky Rift contour
    (strictly clear of Sanctuary, Winter Milky Way, and Moon +18deg/+43deg cone!) out to the 90deg cavern ceiling."""
    bm = bmesh.new()
    origin = Vector((0.0, -54.0, 2.15))

    n_perim = 160
    u_rad_steps = [-0.08, 0.0, 0.08, 0.20, 0.36, 0.54, 0.72, 0.86, 1.0]
    rings = []
    for ur in u_rad_steps:
        row = []
        for ip in range(n_perim + 1):
            phi = math.pi * (ip / n_perim)  # 0 (right horizon) -> pi/2 (high zenith arch) -> pi (left horizon)
            cph, sph = math.cos(phi), math.sin(phi)
            # Smooth jagged natural diagonal fissure opening framing Sanctuary & Moon without obstruction
            jag = (
                2.4 * math.sin(phi * 5.0 + 0.6)
                + 1.2 * math.cos(phi * 11.0 - 0.3)
                + 0.6 * math.sin(phi * 19.0 + 1.2)
            ) * sph
            az_in = 2.0 + 44.0 * cph + 4.5 * math.sin(2.0 * phi) + jag * 0.7
            el_in = 2.0 + 57.5 * (sph ** 0.78) + 6.5 * cph * sph + jag

            az_out = 2.0 + 104.0 * cph
            el_out = 2.0 + 87.5 * (sph ** 0.50)

            u_c = clamp(ur, 0.0, 1.0)
            az_d = lerp(az_in, az_out, u_c ** 0.92) + (1.2 if ur < 0 else 0.0) * (-cph)
            el_d = lerp(el_in, el_out, u_c ** 0.92) + (0.9 if ur < 0 else 0.0)

            # Thickened curled stone lip near ur <= 0.08
            rock_n = 4.2 * math.sin(az_d * 0.16 + el_d * 0.13) + 2.4 * math.cos(az_d * 0.34 - el_d * 0.28)
            rr = 232.0 + 10.0 * u_c + (5.5 if ur < 0 else 0.0) + rock_n
            az, el = math.radians(az_d), math.radians(el_d)
            pt = origin + Vector((rr * math.cos(el) * math.sin(az), rr * math.cos(el) * math.cos(az), rr * math.sin(el)))
            row.append(bm.verts.new(pt))
        rings.append(row)

    for ir in range(len(u_rad_steps) - 1):
        for ip in range(n_perim):
            bm.faces.new((rings[ir][ip], rings[ir][ip + 1], rings[ir + 1][ip + 1], rings[ir + 1][ip]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = finalize_mesh_obj("GEO-CavernRoofCanopy", bm, mat_roof, smooth=True)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    obj.hide_render = False
    return obj


def build_cavern_walls_and_headlands(mat_rock, mat_shore, rng: random.Random) -> tuple[bpy.types.Object, bpy.types.Object]:
    """v9.0 Phase 3 Subterranean Limestone Cavern Walls & Stratified Lake Reef Headlands (R1/R2):
    - Encloses left/right cave flanks & behind-shore vault smoothly from lake_z=-6m up to roof canopy,
      keeping a 100% open vista corridor over Sanctuary (+Y), Aqueduct (+-108m), Moon & Milky Way rift!
    - R1 (left promontory) & R2 (right basalt spit + outer reef) frame lake edges without obstructing any camera/whale."""
    bm_w = bmesh.new()
    origin = Vector((0.0, -54.0, 2.15))

    # Perimeter karst wall curving outside [-47deg, +49deg] Sanctuary/SkyRift vista + low far horizon ridge behind Sanctuary
    n_az = 128
    z_rings = [-6.0, 1.5, 14.0, 34.0, 62.0, 96.0, 134.0, 168.0]
    grid = []
    for iz, zw in enumerate(z_rings):
        u_z = iz / (len(z_rings) - 1)
        row = []
        for ia in range(n_az):
            az_d = -180.0 + (360.0 * ia / n_az)
            # Inside central Sky Rift / Sanctuary window [-44..+48deg], keep rock perimeter low horizon ledge below z=7m!
            in_vista = (-45.0 <= az_d <= 49.0)
            edge_fade = clamp(min(abs(az_d + 45.0), abs(az_d - 49.0)) / 14.0, 0.0, 1.0)
            if in_vista:
                z_cur = lerp(-6.0, 6.2, clamp(u_z * 1.4, 0.0, 1.0)) if zw > 1.5 else zw
                r_base = 236.0
            else:
                z_arch = zw * lerp(0.12, 1.0, edge_fade ** 0.70)
                if zw <= 1.5:
                    z_arch = zw
                z_cur = z_arch
                # Closer rugged cavern flanks on left/right (r~98..136m), sweeping back behind shore cam (r~72m at +-170deg)
                abs_az = abs(az_d)
                if abs_az > 135.0:
                    r_base = lerp(115.0, 72.0, (abs_az - 135.0) / 45.0)
                else:
                    r_base = lerp(225.0, 114.0, smoothstep(45.0, 98.0, abs_az))

            az_rad = math.radians(az_d)
            # Stratified protruding limestone ribs & recessed shelves along cave wall
            buttress = (
                14.5 * math.sin(az_rad * 7.0 + u_z * 2.2)
                + 8.2 * math.cos(az_rad * 13.0 - u_z * 3.8)
                + 4.5 * math.sin(u_z * 14.0 + az_rad * 3.0)
            ) * (0.0 if in_vista else smoothstep(0.0, 0.25, u_z))
            rr = r_base - clamp(buttress, -18.0, 24.0)
            # Curve upper wall cleanly inward above z=60m toward roof dome
            r_inward = rr * (1.0 - 0.14 * (u_z ** 2.2))
            wx = origin.x + r_inward * math.sin(az_rad)
            wy = origin.y + r_inward * math.cos(az_rad)
            row.append(bm_w.verts.new((wx, wy, z_cur)))
        grid.append(row)

    for iz in range(len(z_rings) - 1):
        for ia in range(n_az):
            ia_n = (ia + 1) % n_az
            bm_w.faces.new((grid[iz][ia], grid[iz][ia_n], grid[iz + 1][ia_n], grid[iz + 1][ia]))
    bmesh.ops.recalc_face_normals(bm_w, faces=bm_w.faces)
    walls_obj = finalize_mesh_obj("GEO-CavernWalls", bm_w, mat_rock, smooth=False)

    # Stratified Basalt & Karst Headland Promontories (R1 Left, R2 Right spit & outer reefs) emerging cleanly from mirror lake
    bm_hl = bmesh.new()

    def add_karst_headland(cx: float, cy: float, sx: float, sy: float, height: float, yaw_deg: float, seed_k: float):
        # Stratified terraced karst basalt cliff mesa (chiseled vertical flutes & horizontal rock ledges, ZERO smooth spheres!)
        nr, ns = 8, 20
        rings = []
        rot_m = Matrix.Rotation(math.radians(yaw_deg), 3, "Z")
        for ir in range(nr):
            u = ir / (nr - 1)
            pz = lerp(-1.4, height, u)
            # Stepped sedimentary shelf overhang + inward plateau taper near top
            taper = lerp(1.06, 0.56, u ** 1.65) * (1.0 - 0.14 * ((ir % 2) and 0.35 or 0.0))
            step_wave = 1.0 + 0.09 * math.sin(u * 14.0 + seed_k)
            row = []
            for j in range(ns):
                ang = 2.0 * math.pi * j / ns
                crag = 1.0 + 0.20 * math.sin(ang * 3.0 + seed_k) + 0.11 * math.cos(ang * 7.0 - seed_k * 1.3 + u * 2.5)
                rx = sx * taper * step_wave * crag * math.cos(ang)
                ry = sy * taper * step_wave * crag * math.sin(ang)
                tz = pz + 0.12 * height * math.sin(ang * 4.0 + seed_k) * u
                loc_v = rot_m @ Vector((rx, ry, tz))
                row.append(bm_hl.verts.new((cx + loc_v.x, cy + loc_v.y, loc_v.z)))
            rings.append(row)
        for ir in range(nr - 1):
            for j in range(ns):
                jn = (j + 1) % ns
                bm_hl.faces.new((rings[ir][j], rings[ir][jn], rings[ir + 1][jn], rings[ir + 1][j]))
        top_ctr = bm_hl.verts.new((cx, cy, height * 0.96))
        for j in range(ns):
            jn = (j + 1) % ns
            bm_hl.faces.new((rings[-1][j], rings[-1][jn], top_ctr))

    headlands_cfg = [
        # R1: Left rocky basalt cliff headland beside shore (clear of C6c orbit (-21.5, -51.6, 5.5)!)
        (-26.5, -45.5, 8.8, 5.8, 2.0, 22.0, 1.1),
        (-42.0, -32.0, 11.5, 8.0, 4.6, 34.0, 2.3),
        (-64.0, -12.0, 18.0, 12.0, 13.5, 28.0, 3.7),
        (-88.0,  24.0, 21.0, 15.0, 24.0, 18.0, 4.9),
        # R2: Right low water-skimming basalt spit (clear of C5a cam!) + outer right karst reef!
        ( 21.0, -47.2, 6.8, 3.8, 1.30, -18.0, 5.5),
        ( 65.0, -24.0, 15.0, 11.5, 11.0, -28.0, 6.8),
        ( 88.0,  16.0, 20.0, 14.5, 22.0, -22.0, 7.9),
        (114.0,  62.0, 24.0, 18.0, 32.0, -12.0, 9.2),
    ]
    for h_args in headlands_cfg:
        add_karst_headland(*h_args)

    bmesh.ops.recalc_face_normals(bm_hl, faces=bm_hl.faces)
    headlands_obj = finalize_mesh_obj("GEO-CavernHeadlands", bm_hl, mat_rock, smooth=False)
    return walls_obj, headlands_obj


def build_cavern_stalactites(mat_rock, rng: random.Random) -> bpy.types.Object:
    """v9.0 Sculpted Organic Dripstone Stalactite Curtains & Torn-Rift Teeth (ZERO floating mid-air cones!):
    1) Flank cavern vault stalactites live strictly outside [-47deg..+50deg] Sanctuary/Sky-Rift vista AND root
       continuously up inside the overhead cave ceiling (z_root = 112..152m) so flat tops NEVER dangle in air!
    2) Torn-Rift Rim Teeth sprout strictly from inside the rock CavernRoofCanopy edge, outside Moon corridor."""
    bm = bmesh.new()
    origin = Vector((0.0, -54.0, 2.15))

    def add_fluted_stalactite(top_pos: Vector, length: float, r_top: float, seed_off: float, tilt_x: float = 0.0, tilt_y: float = 0.0):
        nr, ns = 12, 14
        rings = []
        rot_t = Matrix.Rotation(tilt_x, 3, "X") @ Matrix.Rotation(tilt_y, 3, "Y")
        for ir in range(nr):
            u = ir / (nr - 1)
            r_env = lerp(r_top, 0.22, u ** 0.72) * (1.0 + 0.14 * math.sin(u * 13.0 + seed_off))
            ring = []
            for j in range(ns):
                ang = 2.0 * math.pi * j / ns
                flute = 1.0 + 0.24 * math.sin(ang * 5.0 + seed_off + u * 1.4) + 0.12 * math.cos(ang * 9.0 - u * 3.0)
                rr = max(0.14, r_env * flute)
                loc = rot_t @ Vector((rr * math.cos(ang), rr * math.sin(ang), -u * length))
                ring.append(bm.verts.new(top_pos + loc))
            rings.append(ring)
        for ir in range(nr - 1):
            for j in range(ns):
                jn = (j + 1) % ns
                bm.faces.new((rings[ir][j], rings[ir][jn], rings[ir + 1][jn], rings[ir + 1][j]))
        bm.faces.new(list(reversed(rings[0])))
        tip_v = bm.verts.new(top_pos + (rot_t @ Vector((0.0, 0.0, -length * 1.04))))
        for j in range(ns):
            jn = (j + 1) % ns
            bm.faces.new((rings[-1][j], rings[-1][jn], tip_v))

    # 1. Left & Right Flank Cavern Vault Stalactite Curtains — ALL roots anchored high (z_root 114..152m), outside Sky Rift [-47..+50deg]!
    flank_clusters = [
        # (cx, cy, cz_ceil_root, count, spread_x, spread_y, len_lo, len_hi, r_lo, r_hi)
        (-62.0, -18.0, 118.0,  6, 10.0, 14.0, 46.0, 74.0, 3.6, 6.2),
        (-74.0,  14.0, 126.0,  8, 14.0, 18.0, 48.0, 82.0, 4.0, 7.0),
        (-96.0,  52.0, 136.0,  9, 16.0, 24.0, 52.0, 88.0, 4.4, 7.6),
        (-112.0, 90.0, 144.0,  8, 16.0, 22.0, 54.0, 86.0, 4.6, 8.0),
        ( 68.0, -18.0, 118.0,  6, 10.0, 14.0, 42.0, 68.0, 3.4, 5.8),
        ( 86.0,  16.0, 128.0,  8, 14.0, 20.0, 48.0, 82.0, 4.0, 6.8),
        (106.0,  58.0, 138.0,  9, 16.0, 24.0, 52.0, 88.0, 4.4, 7.6),
        (118.0,  96.0, 146.0,  8, 16.0, 22.0, 54.0, 86.0, 4.6, 8.0),
    ]
    for ic, (cx, cy, cz, cnt, sx, sy, l0, l1, r0, r1) in enumerate(flank_clusters):
        for k in range(cnt):
            px = cx + rng.uniform(-sx, sx)
            py = cy + rng.uniform(-sy, sy)
            az_check = math.degrees(math.atan2(px, py + 54.0))
            if -47.5 <= az_check <= 50.5:
                continue
            pz = cz + rng.uniform(-4.0, 8.0)
            length = rng.uniform(l0, l1)
            r_top = rng.uniform(r0, r1)
            add_fluted_stalactite(Vector((px, py, pz)), length, r_top, ic * 3.1 + k * 0.9, rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05))

    # 2. High Torn-Sky-Rift Perimeter Teeth sprouting downward directly FROM CavernRoofCanopy rock edge (outside Moon & Sanctuary!)
    for ik in range(44):
        phi = math.pi * ((ik + 0.5) / 44.0)
        cph, sph = math.cos(phi), math.sin(phi)
        jag = (2.4 * math.sin(phi * 5.0 + 0.6) + 1.2 * math.cos(phi * 11.0 - 0.3)) * sph
        az_d = 2.0 + 43.0 * cph + 4.5 * math.sin(2.0 * phi) + jag * 0.7
        el_d = 2.0 + 57.5 * (sph ** 0.78) + 6.5 * cph * sph + jag + 1.5
        # Keep clear of Moon corridor (+6..+32deg) AND Sanctuary dome crest (-24..+28deg)
        if (-24.0 <= az_d <= 30.0) or (el_d > 53.0 and abs(az_d - 2.0) < 28.0):
            continue
        az, el = math.radians(az_d), math.radians(el_d)
        rr = 234.0 + rng.uniform(-2.0, 4.0)
        top_pt = origin + Vector((rr * math.cos(el) * math.sin(az), rr * math.cos(el) * math.cos(az), rr * math.sin(el) + 10.0))
        if abs(top_pt.x - 43.5) < 24.0 and top_pt.z > 98.0 and top_pt.y > -26.0:
            continue
        length = rng.uniform(34.0, 56.0)
        r_top = rng.uniform(3.2, 5.8)
        add_fluted_stalactite(top_pt, length, r_top, 90.0 + ik * 1.4, rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = finalize_mesh_obj("GEO-CavernStalactites", bm, mat_rock, smooth=False)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    return obj


def build_cavern_star_vault(mat_stars, rng: random.Random, aurora_mode: str = "sky_veil") -> bpy.types.Object:
    """v7.8 Grand Panoramic Winter Milky Way Star-Vault:
    - 'canon_starry_opal': 5,200 crisp astronomical stars across a true curved celestial hemisphere (r = 250..274m
      centered at (0, 60, 0)), dense 4th-5th mag star-dust streaming along a tilted Milky Way belt WITH an authentic
      dark central dust-rift attenuation channel + 1,100 sparkling 2nd-3rd mag constellation stars across zenith!"""
    octa_v = [
        ( 0.0,  0.0,  1.0), ( 0.0,  0.0, -1.0),
        ( 1.0,  0.0,  0.0), (-1.0,  0.0,  0.0),
        ( 0.0,  1.0,  0.0), ( 0.0, -1.0,  0.0),
    ]
    octa_f = [
        (0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2),
        (1, 4, 2), (1, 3, 4), (1, 5, 3), (1, 2, 5),
    ]
    all_v, all_f = [], []
    canon_opal = (aurora_mode == "canon_starry_opal")
    starry_mode = (aurora_mode == "starry_aurora_whale")
    n_stars = 5200 if canon_opal else (3600 if starry_mode else 2200)
    mw_frac = 0.78 if canon_opal else (0.60 if starry_mode else 0.65)
    for i in range(n_stars):
        if canon_opal:
            sr = rng.uniform(249.0, 272.0)
            if i < int(n_stars * mw_frac):
                az_deg = rng.uniform(-74.0, 74.0)
                el_mw = 31.0 + 0.30 * az_deg + 4.5 * math.sin(math.radians(az_deg * 2.4))
                # Carve delicate Dark Cosmic Dust Rift down the galactic equator; discard stars below horizon (NO clamping pile-up!)
                for _attempt in range(3):
                    d_el = rng.gauss(0.0, 11.5)
                    if abs(d_el) < 2.2 and rng.random() < 0.68:
                        continue
                    break
                el_deg = el_mw + d_el
                if el_deg < 10.5 or el_deg > 83.5:
                    el_deg = rng.uniform(12.0, 80.0)
                    az_deg = rng.uniform(-74.0, 74.0)
                rad = rng.uniform(0.08, 0.21) if rng.random() < 0.87 else rng.uniform(0.24, 0.42)
            else:
                az_deg = rng.uniform(-78.0, 78.0)
                el_deg = rng.uniform(11.0, 84.0)
                rad = rng.uniform(0.14, 0.30) if rng.random() < 0.84 else rng.uniform(0.32, 0.54)
            az, el = math.radians(az_deg), math.radians(el_deg)
            sx = sr * math.cos(el) * math.sin(az)
            sy = 60.0 + sr * math.cos(el) * math.cos(az)
            sz = sr * math.sin(el)
        elif i < int(n_stars * mw_frac):
            sx = rng.uniform(-235.0, 245.0)
            z_center = 114.0 + 0.30 * sx + 18.0 * math.sin(sx * 0.018)
            sz = clamp(rng.gauss(z_center, 24.0), 26.0, 255.0)
            sy = rng.uniform(210.0, 275.0)
            rad = rng.uniform(0.11, 0.36) if rng.random() < 0.86 else rng.uniform(0.42, 0.72)
        else:
            sx = rng.uniform(-250.0, 260.0)
            sz = rng.uniform(24.0, 265.0)
            sy = rng.uniform(205.0, 285.0)
            rad = rng.uniform(0.11, 0.34) if rng.random() < 0.88 else rng.uniform(0.38, 0.66)
        off = len(all_v)
        for vx, vy, vz in octa_v:
            all_v.append((sx + vx * rad, sy + vy * rad, sz + vz * rad))
        for a, b, c in octa_f:
            all_f.append((a + off, b + off, c + off))

    mesh = bpy.data.meshes.new("MESH-CavernStarVault")
    mesh.from_pydata(all_v, [], all_f)
    mesh.materials.append(mat_stars)
    obj = bpy.data.objects.new("GEO-CavernStarVault", mesh)
    bpy.context.scene.collection.objects.link(obj)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    obj.hide_render = True
    return obj


def build_winter_starburst_heroes(mat_hero, rng: random.Random) -> bpy.types.Object:
    """v7.8 Tier-4 Winter Constellation 1st-Magnitude 4-Point Diffraction Starbursts:
    56 crisp tiny tangential diffraction star-crosses anchored across winter sky quadrants & above the open Pantheon dome
    (strictly clear of the C7a moon disc!), reading as razor-sharp 3-6px crystal sparks in Cycles."""
    all_v, all_f = [], []
    moon_vec = Vector((43.5, 78.0 + 54.0, 131.5 - 2.15)).normalized()
    count = 0
    tries = 0
    while count < 56 and tries < 400:
        tries += 1
        if count < 38:
            az_deg = rng.uniform(-62.0, 62.0)
            el_mw = 27.0 + 0.44 * az_deg
            el_deg = clamp(el_mw + rng.gauss(0.0, 14.0), 14.0, 74.0)
        else:
            az_deg = rng.uniform(-68.0, 68.0)
            el_deg = rng.uniform(16.0, 76.0)
        az, el = math.radians(az_deg), math.radians(el_deg)
        sr = rng.uniform(244.0, 248.0)
        pos = Vector((sr * math.cos(el) * math.sin(az), 60.0 + sr * math.cos(el) * math.cos(az), sr * math.sin(el)))
        # Protect C7a Moon silhouette cone (keep starbursts at least ~9 deg off the moon!)
        ray_c7a = (pos - Vector((0.0, -54.0, 2.15))).normalized()
        if ray_c7a.dot(moon_vec) > 0.985:
            continue
        # Tangent frame facing viewer center (0, -10, 15)
        n_dir = (Vector((0.0, -10.0, 15.0)) - pos).normalized()
        u_dir = n_dir.cross(Vector((0.0, 0.0, 1.0))).normalized()
        v_dir = u_dir.cross(n_dir).normalized()
        sp_len = rng.uniform(0.75, 1.38)
        sp_w = sp_len * 0.14
        # Build vertical & horizontal slim diamonds around `pos`
        for ax_a, ax_b, la, wa in ((u_dir, v_dir, sp_len * 0.85, sp_w), (v_dir, u_dir, sp_len * 1.10, sp_w)):
            off = len(all_v)
            all_v.append(tuple(pos - ax_a * la))
            all_v.append(tuple(pos - ax_b * wa + n_dir * 0.04))
            all_v.append(tuple(pos + ax_a * la))
            all_v.append(tuple(pos + ax_b * wa + n_dir * 0.04))
            all_f.append((off, off + 1, off + 2, off + 3))
        count += 1

    mesh = bpy.data.meshes.new("MESH-StarburstHero")
    mesh.from_pydata(all_v, [], all_f)
    mesh.materials.append(mat_hero)
    obj = bpy.data.objects.new("GEO-StarburstHero", mesh)
    bpy.context.scene.collection.objects.link(obj)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    obj.hide_render = True
    return obj


def build_aurora_veils(mat_aurora, aurora_mode: str = "sky_veil") -> bpy.types.Object:
    """v7.8 Celestial Winter Milky Way Galactic Star-Cloud Canopy (canon_starry_opal mode)
    or subtle sky aurora curtains (sky_veil fallback):
    In Winter Milky Way mode: a smooth sweeping panoramic dome belt (r = 264m centered at (0, 60, 0)) arching
    diagonally high over the Pantheon Sanctuary across the entire winter sky vault with seamless UV edge feathering!"""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    if aurora_mode == "canon_starry_opal":
        nu, nv = 46, 18
        sr = 264.0
        grid = []
        for iu in range(nu + 1):
            u = iu / nu
            az_deg = lerp(-76.0, 76.0, u)
            el_center = 31.0 + 0.30 * az_deg + 4.5 * math.sin(math.radians(az_deg * 2.4))
            col = []
            for iv in range(nv + 1):
                v = iv / nv
                el_deg = clamp(el_center + lerp(-24.0, 24.0, v), 10.5, 86.0)
                az, el = math.radians(az_deg), math.radians(el_deg)
                x = sr * math.cos(el) * math.sin(az)
                y = 60.0 + sr * math.cos(el) * math.cos(az)
                z = sr * math.sin(el)
                col.append(bm.verts.new((x, y, z)))
            grid.append(col)
        for iu in range(nu):
            for iv in range(nv):
                f = bm.faces.new((grid[iu][iv], grid[iu + 1][iv], grid[iu + 1][iv + 1], grid[iu][iv + 1]))
                uvs = [(iu / nu, iv / nv), ((iu + 1) / nu, iv / nv), ((iu + 1) / nu, (iv + 1) / nv), (iu / nu, (iv + 1) / nv)]
                for loop, uv_co in zip(f.loops, uvs):
                    loop[uv_layer].uv = uv_co
        obj = finalize_mesh_obj("GEO-AuroraVeil", bm, mat_aurora, smooth=True)
        if hasattr(obj, "visible_shadow"):
            obj.visible_shadow = False
        obj.hide_render = True
        return obj

    # (x0, x1, y_base, y_amp, z_bot0, z_bot1, height, wave_ph)
    ribbons = [
        (-195.0, 185.0, 218.0, 24.0, 44.0,  94.0, 96.0, 0.2),
        (-145.0, 215.0, 236.0, 28.0, 62.0, 120.0, 92.0, 2.1),
        (-220.0,  85.0, 228.0, 18.0, 32.0,  68.0, 82.0, 4.0),
    ]
    nu, nv = 42, 10
    for x0, x1, yb, yamp, zb0, zb1, hh, ph in ribbons:
        grid = []
        for iu in range(nu + 1):
            u = iu / nu
            x = lerp(x0, x1, u)
            y = yb + yamp * math.sin(u * math.pi * 2.2 + ph)
            zb = lerp(zb0, zb1, u) + 12.0 * math.sin(u * math.pi * 1.6 + ph * 0.7)
            col = []
            for iv in range(nv + 1):
                v = iv / nv
                col.append(bm.verts.new((x, y + v * 14.0, zb + v * hh)))
            grid.append(col)
        for iu in range(nu):
            for iv in range(nv):
                f = bm.faces.new((grid[iu][iv], grid[iu + 1][iv], grid[iu + 1][iv + 1], grid[iu][iv + 1]))
                uvs = [(iu / nu, iv / nv), ((iu + 1) / nu, iv / nv), ((iu + 1) / nu, (iv + 1) / nv), (iu / nu, (iv + 1) / nv)]
                for loop, uv_co in zip(f.loops, uvs):
                    loop[uv_layer].uv = uv_co

    obj = finalize_mesh_obj("GEO-AuroraVeil", bm, mat_aurora, smooth=True)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    obj.hide_render = True
    return obj


def shore_surface_z(wx: float, wy: float, shore_z: float) -> float:
    edge_drop = smoothstep(-51.6, -49.1, wy)
    flat_zone = math.exp(-((wx - 0.5) / 8.5) ** 2 - ((wy + 54.8) / 4.2) ** 2)
    # Keep PC1..4 standing pad & C5a right-flank vantage clear while carving rocky shelves behind!
    pc_pad = math.exp(-((wx) / 3.4) ** 2 - ((wy + 55.2) / 1.4) ** 2)
    c5a_clear = 1.0 - math.exp(-((wx - 22.0) / 7.0) ** 2 - ((wy + 56.5) / 5.5) ** 2)
    strata_raw = 0.24 * math.sin(wx * 0.58 + wy * 0.22) + 0.14 * math.cos(wy * 0.85 - wx * 0.35)
    terraced = round(strata_raw * 6.5) / 6.5 * 0.62 + strata_raw * 0.38
    micro_crag = 0.045 * math.sin(wx * 2.4 + wy * 1.9) * math.cos(wx * 1.7 - wy * 2.3)
    rim_rise = (1.65 * (smoothstep(10.0, 28.0, abs(wx)) ** 1.4) + 1.15 * smoothstep(-60.0, -72.0, wy)) * c5a_clear
    relief = (1.0 - flat_zone) * terraced + (1.0 - pc_pad) * micro_crag + rim_rise
    return lerp(shore_z + relief, -0.42, edge_drop)


def _create_botanical_flower_meshes(mat_leaf, mat_calyx, mat_bud_seam, mat_receptacle, mat_stamen, mat_petal, mat_seed):
    """v9.0 True 4-Part Living Botanical Kousetsuka Meshes (FL-01 v0.8 & CUT03/CUT08):
    1. MESH-HeroStem: ONLY curving stem + 4 willow leaves + 2 tapered sleeping lateral buds (NO open stamens!)
    2. MESH-HeroBudCup: Crisp 5-ribbed imbricate teardrop closed bud WITH creamy inner-petal tip peek at apex suture!
    3. MESH-HeroOpenHeart: Separate receptacle + 5 reflexed sepals + 5 carpels + 5 golden anthers (hidden until bloom!)
    4. MESH-HeroPetal: 16x11 cupped veined ovate petal blade + attached 2-3mm basal dry fruit capsule!"""
    # 1. Clean Hero Stem + 4 Willow Leaves + 2 Tapered Living Lateral Side-Buds (NO open flower organs!)
    bm = bmesh.new()

    def _stem_pt(u: float) -> Vector:
        return Vector((0.006 * math.sin(u * math.pi), 0.004 * math.sin(u * math.pi * 1.3), u * 0.142))

    n_sr, n_ss = 10, 8
    s_rings = []
    for ir in range(n_sr):
        u = ir / (n_sr - 1)
        c = _stem_pt(u)
        r = lerp(0.0044, 0.0024, u)
        row = []
        for j in range(n_ss):
            a = 2.0 * math.pi * j / n_ss
            row.append(bm.verts.new(c + Vector((r * math.cos(a), r * math.sin(a), 0.0))))
        s_rings.append(row)
    for ir in range(n_sr - 1):
        for j in range(n_ss):
            jn = (j + 1) % n_ss
            f = bm.faces.new((s_rings[ir][j], s_rings[ir][jn], s_rings[ir + 1][jn], s_rings[ir + 1][j]))
            f.material_index = 0

    def add_willow_leaf(u_node: float, az_deg: float, pitch_deg: float, length: float, width: float):
        anchor = _stem_pt(u_node)
        m_lf = (
            Matrix.Translation(anchor)
            @ Matrix.Rotation(math.radians(az_deg), 4, "Z")
            @ Matrix.Rotation(math.radians(pitch_deg), 4, "Y")
        )
        nu_l, nv_l = 12, 7
        grid_l = []
        for iu in range(nu_l):
            u = iu / (nu_l - 1)
            lx = u * length
            half_w = width * math.sin((u ** 0.68) * math.pi) * lerp(0.18, 1.0, smoothstep(0.0, 0.14, u)) * (1.0 - 0.16 * u)
            arch_z = 0.012 * math.sin(u * math.pi * 1.15) - 0.009 * (u ** 2.3)
            row = []
            for iv in range(nv_l):
                v = (iv / (nv_l - 1)) * 2.0 - 1.0
                v_fold = (abs(v) ** 1.25) * 0.0032 * math.sin(u * math.pi)
                row.append(bm.verts.new(m_lf @ Vector((lx, v * half_w, arch_z + v_fold))))
            grid_l.append(row)
        for iu in range(nu_l - 1):
            for iv in range(nv_l - 1):
                f = bm.faces.new((grid_l[iu][iv], grid_l[iu + 1][iv], grid_l[iu + 1][iv + 1], grid_l[iu][iv + 1]))
                f.material_index = 0

    def add_tapered_teardrop_bud(bm_target, m_base: Matrix, h_bud: float, rad_b: float, mat_sheath: int, mat_tip: int):
        """Sculpted 5-sepal imbricate teardrop closed bud with delicate pale petal tip seam near apex."""
        nr, ns = 9, 15
        b_rings = []
        for ir in range(nr):
            u = ir / (nr - 1)
            bz = u * h_bud
            br = rad_b * (math.sin(clamp(u * 0.90 + 0.08, 0.04, 0.99) * math.pi * 0.92) ** 0.72) * (1.0 - 0.62 * (u ** 2.4))
            row = []
            for j in range(ns):
                ang = 2.0 * math.pi * j / ns + u * 0.36  # graceful spiral sepal fold!
                rib = 1.0 + 0.16 * math.cos(5.0 * (ang - u * 0.36))
                row.append(bm_target.verts.new(m_base @ Vector((br * rib * math.cos(ang), br * rib * math.sin(ang), bz))))
            b_rings.append(row)
        for ir in range(nr - 1):
            u_mid = (ir + 0.5) / (nr - 1)
            for j in range(ns):
                jn = (j + 1) % ns
                f = bm_target.faces.new((b_rings[ir][j], b_rings[ir][jn], b_rings[ir + 1][jn], b_rings[ir + 1][j]))
                # Uppermost tip suture grooves show delicate hint of milky petal fold waiting inside!
                is_seam = (u_mid > 0.74) and (j % 3 == 1)
                f.material_index = mat_tip if is_seam else mat_sheath
        f_bot = bm_target.faces.new(list(reversed(b_rings[0])))
        f_bot.material_index = mat_sheath
        apex_v = bm_target.verts.new(m_base @ Vector((0.0, 0.0, h_bud * 1.05)))
        for j in range(ns):
            jn = (j + 1) % ns
            f_t = bm_target.faces.new((b_rings[-1][j], b_rings[-1][jn], apex_v))
            f_t.material_index = mat_tip if (j % 3 == 1) else mat_sheath

    # 4 Alternate Narrow Pointed Willow Leaves climbing stem
    add_willow_leaf(0.14,  28.0, -28.0, 0.088, 0.015)
    add_willow_leaf(0.26, 205.0, -32.0, 0.082, 0.014)
    add_willow_leaf(0.45,  95.0, -22.0, 0.068, 0.012)
    add_willow_leaf(0.62, 285.0, -18.0, 0.056, 0.010)

    # 2 Graceful Living Closed Lateral Buds along stem nodes (CUT03_KEY_flower.png silhouette!)
    for u_sb, az_sb, ln_sb, hb_sb, rb_sb in ((0.46, 255.0, 0.032, 0.030, 0.0072), (0.68, 70.0, 0.025, 0.024, 0.0058)):
        sb_anchor = _stem_pt(u_sb)
        ped = Matrix.Translation(sb_anchor) @ Matrix.Rotation(math.radians(az_sb), 4, "Z") @ Matrix.Rotation(math.radians(26.0), 4, "Y")
        res_p = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.0020, radius2=0.0014, depth=ln_sb)
        bmesh.ops.transform(bm, matrix=ped @ Matrix.Translation((0, 0, ln_sb * 0.5)), verts=res_p["verts"])
        bm.faces.ensure_lookup_table()
        for f in bm.faces[-8:]:
            f.material_index = 0
        add_tapered_teardrop_bud(bm, ped @ Matrix.Translation((0, 0, ln_sb * 0.92)), h_bud=hb_sb, rad_b=rb_sb, mat_sheath=1, mat_tip=2)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    stem_mesh = bpy.data.meshes.new("MESH-HeroStem")
    bm.to_mesh(stem_mesh)
    bm.free()
    for p in stem_mesh.polygons:
        p.use_smooth = True
    stem_mesh.materials.append(mat_leaf)
    stem_mesh.materials.append(mat_calyx)
    stem_mesh.materials.append(mat_bud_seam)

    # 2. Dedicated Living Dormant Terminal Bud Cup (5-ribbed teardrop curving downward gracefully!)
    bm_b = bmesh.new()
    m_droop = Matrix.Translation((0, 0, -0.003)) @ Matrix.Rotation(math.radians(32.0), 4, "X")
    add_tapered_teardrop_bud(bm_b, m_droop, h_bud=0.064, rad_b=0.0172, mat_sheath=0, mat_tip=1)
    bmesh.ops.recalc_face_normals(bm_b, faces=bm_b.faces)
    bud_mesh = bpy.data.meshes.new("MESH-HeroBudCup")
    bm_b.to_mesh(bud_mesh)
    bm_b.free()
    for p in bud_mesh.polygons:
        p.use_smooth = True
    bud_mesh.materials.append(mat_calyx)
    bud_mesh.materials.append(mat_bud_seam)

    # 3. Separate Open Flower Heart (5 Reflexed Calyx Sepals + Receptacle + 5 Carpels + 5 Golden Stamens)
    #    Strictly hidden during closed-bud phase so ZERO organs poke out of C1 buds!
    bm_h = bmesh.new()
    res_rec = bmesh.ops.create_uvsphere(bm_h, u_segments=10, v_segments=6, radius=1.0)
    bmesh.ops.transform(bm_h, matrix=Matrix.Diagonal((0.011, 0.011, 0.007, 1.0)), verts=res_rec["verts"])
    bm_h.faces.ensure_lookup_table()
    for f in bm_h.faces:
        f.material_index = 1

    for k in range(5):
        ang = 2.0 * math.pi * k / 5.0 + math.radians(36.0)
        mc = Matrix.Translation((0, 0, -0.004)) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(math.radians(28.0), 4, "Y")
        nu_s, nv_s = 10, 5
        gs = []
        for iu in range(nu_s):
            u = iu / (nu_s - 1)
            sx = u * 0.040
            hw = 0.0085 * math.sin((u ** 0.72) * math.pi * 0.92) * (1.0 - 0.35 * u)
            sz = -0.011 * (u ** 1.45) + 0.0022 * math.sin(u * math.pi)
            row = []
            for iv in range(nv_s):
                v = (iv / (nv_s - 1)) * 2.0 - 1.0
                row.append(bm_h.verts.new(mc @ Vector((sx, v * hw, sz + abs(v) * 0.0014 * math.sin(u * math.pi)))))
            gs.append(row)
        for iu in range(nu_s - 1):
            for iv in range(nv_s - 1):
                f = bm_h.faces.new((gs[iu][iv], gs[iu + 1][iv], gs[iu + 1][iv + 1], gs[iu][iv + 1]))
                f.material_index = 0

        a_ov = 2.0 * math.pi * k / 5.0
        m_ov = Matrix.Translation((0.0044 * math.cos(a_ov), 0.0044 * math.sin(a_ov), 0.0045)) @ Matrix.Rotation(a_ov, 4, "Z")
        n_before = len(bm_h.faces)
        res_o = bmesh.ops.create_uvsphere(bm_h, u_segments=8, v_segments=5, radius=1.0)
        bmesh.ops.transform(bm_h, matrix=m_ov @ Matrix.Diagonal((0.0024, 0.0020, 0.0048, 1.0)), verts=res_o["verts"])
        res_sg = bmesh.ops.create_cone(bm_h, cap_ends=True, segments=6, radius1=0.00075, radius2=0.00025, depth=0.0085)
        bmesh.ops.transform(bm_h, matrix=m_ov @ Matrix.Translation((0.0012, 0.0, 0.0078)) @ Matrix.Rotation(math.radians(16.0), 4, "Y"), verts=res_sg["verts"])
        bm_h.faces.ensure_lookup_table()
        for f in bm_h.faces[n_before:]:
            f.material_index = 1

        a_st = a_ov + math.radians(36.0)
        m_st = Matrix.Translation((0, 0, 0.0045)) @ Matrix.Rotation(a_st, 4, "Z")
        fil_r = 0.00058
        n_fr, n_fs = 7, 6
        f_rings = []
        for ir in range(n_fr):
            u = ir / (n_fr - 1)
            fx = 0.0042 + u * 0.0128 + 0.0022 * math.sin(u * math.pi)
            fz = u * 0.0245 - 0.0038 * (u ** 2.3)
            row = []
            for j in range(n_fs):
                aj = 2.0 * math.pi * j / n_fs
                row.append(bm_h.verts.new(m_st @ Vector((fx + fil_r * math.cos(aj), fil_r * math.sin(aj), fz))))
            f_rings.append(row)
        for ir in range(n_fr - 1):
            for j in range(n_fs):
                jn = (j + 1) % n_fs
                f = bm_h.faces.new((f_rings[ir][j], f_rings[ir][jn], f_rings[ir + 1][jn], f_rings[ir + 1][j]))
                f.material_index = 2
        n_before = len(bm_h.faces)
        for lobe_y in (-0.00085, 0.00085):
            res_an = bmesh.ops.create_uvsphere(bm_h, u_segments=8, v_segments=6, radius=1.0)
            bmesh.ops.transform(
                bm_h,
                matrix=m_st @ Matrix.Translation((0.0170, lobe_y, 0.0205)) @ Matrix.Rotation(math.radians(38.0), 4, "Y") @ Matrix.Diagonal((0.0023, 0.00095, 0.0011, 1.0)),
                verts=res_an["verts"],
            )
        bm_h.faces.ensure_lookup_table()
        for f in bm_h.faces[n_before:]:
            f.material_index = 2

    bmesh.ops.recalc_face_normals(bm_h, faces=bm_h.faces)
    open_heart_mesh = bpy.data.meshes.new("MESH-HeroOpenHeart")
    bm_h.to_mesh(open_heart_mesh)
    bm_h.free()
    for p in open_heart_mesh.polygons:
        p.use_smooth = True
    open_heart_mesh.materials.append(mat_calyx)
    open_heart_mesh.materials.append(mat_receptacle)
    open_heart_mesh.materials.append(mat_stamen)

    # 3. Sculpted 16x11 Cupped Mid-Vein Rounded-Tip FL-01 Petal (UV-mapped inside petal_rgba.png!) + Basal Dry Seed Capsule
    bm_p = bmesh.new()
    uv_lay = bm_p.loops.layers.uv.new("UVMap")
    nu_p, nv_p = 16, 11
    p_len = 0.090
    p_max_hw = 0.0265
    grid_p = []
    uv_grid = []
    for iu in range(nu_p):
        u = iu / (nu_p - 1)  # 0 = golden claw base -> 1 = rounded milky apex
        w_shape = math.sin((u ** 0.70) * math.pi) * lerp(0.18, 1.0, smoothstep(0.0, 0.16, u))
        hw = p_max_hw * (w_shape ** 0.88)
        if iu == nu_p - 1:
            hw = 0.0014
        cup_center_z = 0.015 * math.sin(u * math.pi * 0.88) - 0.006 * (u ** 3.2)
        row_v, row_uv = [], []
        for iv in range(nv_p):
            v = (iv / (nv_p - 1)) * 2.0 - 1.0  # -1..+1 across width
            # Subtle graceful apical cleft curve matching FL-01
            notch_dip = 0.0028 * math.exp(-(v / 0.24) ** 2) * smoothstep(0.76, 1.0, u)
            px = u * p_len - notch_dip
            mid_ridge = 0.0014 * ((1.0 - abs(v)) ** 2.2) * math.sin(u * math.pi)
            cup_z = 0.0080 * (v * v) * math.sin(u * math.pi) + mid_ridge
            ruffle_z = 0.0018 * (abs(v) ** 1.8) * math.sin(u * 3.6 * math.pi + v * 1.4)
            row_v.append(bm_p.verts.new((px, v * hw, cup_center_z + cup_z + ruffle_z)))
            uv_u = 0.50 + v * 0.17 * w_shape
            uv_v = lerp(0.14, 0.85, u)
            row_uv.append((uv_u, uv_v))
        grid_p.append(row_v)
        uv_grid.append(row_uv)

    for iu in range(nu_p - 1):
        for iv in range(nv_p - 1):
            f = bm_p.faces.new((grid_p[iu][iv], grid_p[iu + 1][iv], grid_p[iu + 1][iv + 1], grid_p[iu][iv + 1]))
            f.material_index = 0
            fuvs = [uv_grid[iu][iv], uv_grid[iu + 1][iv], uv_grid[iu + 1][iv + 1], uv_grid[iu][iv + 1]]
            for loop, uv_co in zip(f.loops, fuvs):
                loop[uv_lay].uv = uv_co

    # Small oval striated 2-3mm Dry Fruit / Seed Capsule fused cleanly onto basal claw (mat 1: MAT-Kousetsuka_Seed)
    n_sb = len(bm_p.faces)
    res_sd = bmesh.ops.create_uvsphere(bm_p, u_segments=8, v_segments=6, radius=1.0)
    bmesh.ops.transform(bm_p, matrix=Matrix.Translation((-0.0042, 0.0, 0.0008)) @ Matrix.Diagonal((0.0058, 0.0026, 0.0026, 1.0)), verts=res_sd["verts"])
    bm_p.faces.ensure_lookup_table()
    for f in bm_p.faces[n_sb:]:
        f.material_index = 1

    bmesh.ops.recalc_face_normals(bm_p, faces=bm_p.faces)
    petal_mesh = bpy.data.meshes.new("MESH-HeroPetal")
    bm_p.to_mesh(petal_mesh)
    bm_p.free()
    for p in petal_mesh.polygons:
        p.use_smooth = True
    petal_mesh.materials.append(mat_petal)
    petal_mesh.materials.append(mat_seed)
    return stem_mesh, bud_mesh, open_heart_mesh, petal_mesh


def _build_dynamic_petal_mesh(name: str, count: int, mat_petal, mat_seed=None) -> tuple[bpy.types.Object, np.ndarray]:
    """Build ONE single NumPy mesh holding `count` curved UV-mapped FL-01 petals WITH attached glowing golden 3mm basal seed capsules!"""
    # 16-vert cupped wavy FL-01 almond blade (indices 0..15) + 6-vert ovoid basal seed octahedron (indices 16..21)
    tpl_list = [
        [-0.125,  0.000,  0.018],  # 0: claw base
        [-0.070, -0.042,  0.013], [-0.070, 0.000, -0.004], [-0.070,  0.042,  0.013],  # 1,2,3
        [-0.010, -0.068,  0.018], [-0.010, 0.000, -0.007], [-0.010,  0.068,  0.018],  # 4,5,6
        [ 0.055, -0.062,  0.015], [ 0.055, 0.000, -0.004], [ 0.055,  0.062,  0.015],  # 7,8,9
        [ 0.115, -0.026,  0.022], [ 0.115, 0.000,  0.012], [ 0.115,  0.026,  0.022],  # 10,11,12
        [ 0.142,  0.000,  0.026],  # 13: pointed tip
    ]
    # Attached 2-3mm champagne-gold oval seed capsule at basal claw (-0.138 -> -0.118)
    seed_pts = [
        [-0.146,  0.000,  0.021],  # 14: seed tail tip
        [-0.130, -0.011,  0.019], [-0.130,  0.011,  0.019], [-0.130, 0.000, 0.030], [-0.130, 0.000, 0.008],  # 15..18
        [-0.115,  0.000,  0.019],  # 19: seed throat join
    ]
    tpl_uvs_pt = [
        (0.50, 0.13),
        (0.39, 0.28), (0.50, 0.28), (0.61, 0.28),
        (0.32, 0.50), (0.50, 0.50), (0.68, 0.50),
        (0.34, 0.70), (0.50, 0.70), (0.66, 0.70),
        (0.42, 0.82), (0.50, 0.82), (0.58, 0.82),
        (0.50, 0.87),
    ] + [(0.50, 0.14)] * 6
    tpl_verts = np.array(tpl_list + seed_pts, dtype=np.float32)

    petal_faces = [
        (0, 1, 2), (0, 2, 3),
        (1, 4, 5, 2), (2, 5, 6, 3),
        (4, 7, 8, 5), (5, 8, 9, 6),
        (7, 10, 11, 8), (8, 11, 12, 9),
        (10, 13, 11), (11, 13, 12),
    ]
    seed_faces = [
        (14, 15, 17), (14, 17, 16), (14, 16, 18), (14, 18, 15),
        (19, 17, 15), (19, 16, 17), (19, 18, 16), (19, 15, 18),
    ]
    nv = len(tpl_verts)
    all_verts, all_faces, all_uvs, all_mats = [], [], [], []
    use_seed_slot = (mat_seed is not None)
    for i in range(count):
        off = i * nv
        for v in tpl_verts:
            all_verts.append((float(v[0]), float(v[1]), float(v[2]) - 500.0))
        for f in petal_faces:
            all_faces.append(tuple(idx + off for idx in f))
            all_mats.append(0)
            for idx in f:
                all_uvs.append(tpl_uvs_pt[idx])
        for f in seed_faces:
            all_faces.append(tuple(idx + off for idx in f))
            all_mats.append(1 if use_seed_slot else 0)
            for idx in f:
                all_uvs.append((0.50, 0.06))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(all_verts, [], all_faces)
    uv_layer = mesh.uv_layers.new(name="UVMap")
    uv_layer.data.foreach_set("uv", np.array(all_uvs, dtype=np.float32).ravel())
    mesh.polygons.foreach_set("material_index", np.array(all_mats, dtype=np.int32))
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.materials.append(mat_petal)
    if use_seed_slot:
        mesh.materials.append(mat_seed)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    return obj, tpl_verts


def _update_dynamic_petal_mesh(
    obj: bpy.types.Object,
    tpl_verts: np.ndarray,
    pos: np.ndarray,
    rot: np.ndarray,
    scale: np.ndarray,
):
    """Vectorized NumPy transform of `N` petals (pos: Nx3, rot: Nx3 XYZ Euler, scale: N) -> foreach_set in ~1.2ms!"""
    cx, cy, cz = np.cos(rot[:, 0]), np.cos(rot[:, 1]), np.cos(rot[:, 2])
    sx, sy, sz = np.sin(rot[:, 0]), np.sin(rot[:, 1]), np.sin(rot[:, 2])
    # XYZ Euler rotation matrix R = Rz @ Ry @ Rx
    r00 = cz * cy
    r01 = cz * sy * sx - sz * cx
    r02 = cz * sy * cx + sz * sx
    r10 = sz * cy
    r11 = sz * sy * sx + cz * cx
    r12 = sz * sy * cx - cz * sx
    r20 = -sy
    r21 = cy * sx
    r22 = cy * cx

    n = pos.shape[0]
    R = np.empty((n, 3, 3), dtype=np.float32)
    R[:, 0, 0], R[:, 0, 1], R[:, 0, 2] = r00, r01, r02
    R[:, 1, 0], R[:, 1, 1], R[:, 1, 2] = r10, r11, r12
    R[:, 2, 0], R[:, 2, 1], R[:, 2, 2] = r20, r21, r22

    # Scaled template (N, V, 3) = einsum('n,vj->nvj') then rotated by R^T + pos
    # out[n, v, i] = scale[n] * sum_j R[n, i, j] * tpl[v, j] + pos[n, i]
    pts = np.einsum("nij,vj->nvi", R, tpl_verts, optimize=True) * scale[:, None, None] + pos[:, None, :]
    obj.data.vertices.foreach_set("co", pts.astype(np.float32).ravel())
    obj.data.update()


def _build_colony_crown_mesh(
    name: str,
    count: int,
    mat_bloom,
    mat_stamen=None,
    mat_calyx=None,
) -> tuple[bpy.types.Object, np.ndarray]:
    """One NumPy-driven multi-material mesh holding `count` detailed cupped 5-petal Kousetsuka crowns
    (UV-mapped onto petal_rgba.png + golden 5-star stamen core + pointed dark calyx cup)."""
    verts = []
    petal_faces = []
    petal_uvs = []
    stamen_faces = []
    calyx_faces = []

    # 5 graceful cupped smooth-shaded ovate FL-01 petals (13 verts / 11 faces per petal, rounded tips!)
    for k in range(5):
        a = 2.0 * math.pi * k / 5.0
        ca, sa = math.cos(a), math.sin(a)
        px, py = -sa, ca
        base = len(verts)
        z_stagger = 0.0012 * (1.0 if (k % 2 == 0) else -1.0)

        def _p(r: float, w: float, z: float):
            return [ca * r + px * w, sa * r + py * w, z + z_stagger * (w / 0.025)]

        verts.extend([
            _p(0.005,  0.000, 0.004),   # 0: claw throat
            _p(0.026, -0.015, 0.010),   # 1: lower-left
            _p(0.026,  0.000, 0.005),   # 2: lower-mid
            _p(0.026,  0.015, 0.010),   # 3: lower-right
            _p(0.052, -0.024, 0.015),   # 4: belly-left
            _p(0.052,  0.000, 0.008),   # 5: belly-mid
            _p(0.052,  0.024, 0.015),   # 6: belly-right
            _p(0.076, -0.016, 0.013),   # 7: shoulder-left
            _p(0.076,  0.000, 0.009),   # 8: shoulder-mid
            _p(0.076,  0.016, 0.013),   # 9: shoulder-right
            _p(0.091, -0.007, 0.011),   # 10: left apex lobe
            _p(0.090,  0.000, 0.009),   # 11: center subtle notch
            _p(0.091,  0.007, 0.011),   # 12: right apex lobe
        ])
        uvs_k = [
            (0.50, 0.14),
            (0.37, 0.34), (0.50, 0.34), (0.63, 0.34),
            (0.32, 0.56), (0.50, 0.56), (0.68, 0.56),
            (0.38, 0.74), (0.50, 0.74), (0.62, 0.74),
            (0.45, 0.85), (0.50, 0.83), (0.55, 0.85),
        ]
        f_defs = [
            (0, 1, 2), (0, 2, 3),
            (1, 4, 5, 2), (2, 5, 6, 3),
            (4, 7, 8, 5), (5, 8, 9, 6),
            (7, 10, 11, 8), (8, 11, 12, 9),
        ]
        for fd in f_defs:
            petal_faces.append(tuple(base + j for j in fd))
            for j in fd:
                petal_uvs.append(uvs_k[j])

    # Rounded Botanical Stamen Crown: central ovary dome + 5 curved golden anthers (no spiky origami star!)
    st_ov_c = len(verts)
    verts.append([0.0, 0.0, 0.013])
    st_ov_r = len(verts)
    for j in range(6):
        aj = 2.0 * math.pi * j / 6.0
        verts.append([0.0065 * math.cos(aj), 0.0065 * math.sin(aj), 0.007])
    for j in range(6):
        stamen_faces.append((st_ov_c, st_ov_r + j, st_ov_r + (j + 1) % 6))
    for k in range(5):
        a_s = 2.0 * math.pi * k / 5.0 + math.radians(36.0)
        cx_s, cy_s = 0.0145 * math.cos(a_s), 0.0145 * math.sin(a_s)
        ab = len(verts)
        verts.extend([
            [cx_s, cy_s, 0.0185],
            [cx_s + 0.0032, cy_s, 0.015],
            [cx_s, cy_s + 0.0032, 0.015],
            [cx_s - 0.0032, cy_s, 0.015],
            [cx_s, cy_s - 0.0032, 0.015],
            [cx_s, cy_s, 0.010],
        ])
        for m in range(4):
            mn = (m + 1) % 4
            stamen_faces.append((ab, ab + 1 + m, ab + 1 + mn))
            stamen_faces.append((ab + 5, ab + 1 + mn, ab + 1 + m))

    # Subtle downward-hugging receptacle skirt ONLY (strictly z <= -0.004 so never pierces petals!)
    cx_ctr = len(verts)
    verts.append([0.0, 0.0, -0.006])
    cx_val = len(verts)
    for k in range(5):
        a = 2.0 * math.pi * k / 5.0
        verts.append([0.009 * math.cos(a), 0.009 * math.sin(a), -0.002])
    cx_tips = len(verts)
    for k in range(5):
        a_s = 2.0 * math.pi * k / 5.0 + math.radians(36.0)
        verts.append([0.024 * math.cos(a_s), 0.024 * math.sin(a_s), -0.012])
    for k in range(5):
        kn = (k + 1) % 5
        calyx_faces.append((cx_ctr, cx_tips + k, cx_val + k))
        calyx_faces.append((cx_ctr, cx_val + kn, cx_tips + k))

    tpl = np.array(verts, dtype=np.float32)
    nv = len(tpl)
    all_v, all_f, all_uvs, all_mats = [], [], [], []
    use_st = (mat_stamen is not None)
    use_cx = (mat_calyx is not None)
    st_slot = 1 if use_st else 0
    cx_slot = (2 if use_st else 1) if use_cx else 0
    for i in range(count):
        off = i * nv
        for v in tpl:
            all_v.append((float(v[0]), float(v[1]), float(v[2]) - 500.0))
        for f in petal_faces:
            all_f.append(tuple(idx + off for idx in f))
            all_mats.append(0)
        all_uvs.extend(petal_uvs)
        for f in stamen_faces:
            all_f.append(tuple(idx + off for idx in f))
            all_mats.append(st_slot)
            all_uvs.extend([(0.50, 0.08)] * 3)
        for f in calyx_faces:
            all_f.append(tuple(idx + off for idx in f))
            all_mats.append(cx_slot)
            all_uvs.extend([(0.50, 0.04)] * 3)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(all_v, [], all_f)
    uv_layer = mesh.uv_layers.new(name="UVMap")
    uv_layer.data.foreach_set("uv", np.array(all_uvs, dtype=np.float32).ravel())
    mesh.polygons.foreach_set("material_index", np.array(all_mats, dtype=np.int32))
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.materials.append(mat_bloom)
    if use_st:
        mesh.materials.append(mat_stamen)
    if use_cx:
        mesh.materials.append(mat_calyx)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    return obj, tpl


def _build_colony_bud_mesh(name: str, count: int, mat_calyx, mat_bud_seam) -> tuple[bpy.types.Object, np.ndarray]:
    """One NumPy-driven multi-material mesh holding `count` sculpted 5-ribbed teardrop closed Kousetsuka buds
    (gracefully drooping ~22deg, revealing tiny pale inner-petal tip seam at apex!)."""
    verts = []
    calyx_faces = []
    seam_faces = []

    m_droop = Matrix.Rotation(math.radians(24.0), 4, "X")
    nr, ns = 6, 10
    rings = []
    for ir in range(nr):
        u = ir / (nr - 1)
        bz = u * 0.056
        br = 0.0148 * (math.sin(clamp(u * 0.90 + 0.08, 0.04, 0.99) * math.pi * 0.92) ** 0.72) * (1.0 - 0.60 * (u ** 2.3))
        row = []
        for j in range(ns):
            ang = 2.0 * math.pi * j / ns + u * 0.34
            rib = 1.0 + 0.15 * math.cos(5.0 * (ang - u * 0.34))
            pt = m_droop @ Vector((br * rib * math.cos(ang), br * rib * math.sin(ang), bz))
            row.append(len(verts))
            verts.append([pt.x, pt.y, pt.z])
        rings.append(row)
    for ir in range(nr - 1):
        u_mid = (ir + 0.5) / (nr - 1)
        for j in range(ns):
            jn = (j + 1) % ns
            fd = (rings[ir][j], rings[ir][jn], rings[ir + 1][jn], rings[ir + 1][j])
            if u_mid > 0.72 and (j % 2 == 0):
                seam_faces.append(fd)
            else:
                calyx_faces.append(fd)
    apex_idx = len(verts)
    ap_pt = m_droop @ Vector((0.0, 0.0, 0.058))
    verts.append([ap_pt.x, ap_pt.y, ap_pt.z])
    for j in range(ns):
        jn = (j + 1) % ns
        fd = (rings[-1][j], rings[-1][jn], apex_idx)
        if j % 2 == 0:
            seam_faces.append(fd)
        else:
            calyx_faces.append(fd)

    tpl = np.array(verts, dtype=np.float32)
    nv = len(tpl)
    all_v, all_f, all_mats = [], [], []
    for i in range(count):
        off = i * nv
        for v in tpl:
            all_v.append((float(v[0]), float(v[1]), float(v[2]) - 500.0))
        for f in calyx_faces:
            all_f.append(tuple(idx + off for idx in f))
            all_mats.append(0)
        for f in seam_faces:
            all_f.append(tuple(idx + off for idx in f))
            all_mats.append(1)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(all_v, [], all_f)
    mesh.polygons.foreach_set("material_index", np.array(all_mats, dtype=np.int32))
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.materials.append(mat_calyx)
    mesh.materials.append(mat_bud_seam)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    return obj, tpl


def _build_colony_shed_calyx_mesh(name: str, count: int, mat_calyx, mat_stamen) -> tuple[bpy.types.Object, np.ndarray]:
    """Bare 5-sepal reflexed calyx + central golden stamens revealed ONLY AFTER colony petal shedding (C6a/C8!)."""
    verts = []
    calyx_faces = []
    stamen_faces = []

    cx_ctr = len(verts)
    verts.append([0.0, 0.0, 0.002])
    for k in range(5):
        a = 2.0 * math.pi * k / 5.0 + math.radians(36.0)
        ca, sa = math.cos(a), math.sin(a)
        b_i = len(verts)
        verts.extend([
            [ca * 0.008, sa * 0.008, 0.001],
            [ca * 0.024 - sa * 0.005, sa * 0.024 + ca * 0.005, -0.008],
            [ca * 0.036, sa * 0.036, -0.015],
            [ca * 0.024 + sa * 0.005, sa * 0.024 - ca * 0.005, -0.008],
        ])
        calyx_faces.append((cx_ctr, b_i, b_i + 1, b_i + 2))
        calyx_faces.append((cx_ctr, b_i + 2, b_i + 3, b_i))
        a_s = 2.0 * math.pi * k / 5.0
        sx, sy = 0.0085 * math.cos(a_s), 0.0085 * math.sin(a_s)
        tx, ty = 0.0115 * math.cos(a_s), 0.0115 * math.sin(a_s)
        st_b = len(verts)
        verts.extend([
            [tx, ty, 0.017],
            [sx + 0.0011, sy, 0.004],
            [sx, sy + 0.0011, 0.004],
            [sx - 0.0011, sy, 0.004],
        ])
        stamen_faces.append((st_b, st_b + 1, st_b + 2))
        stamen_faces.append((st_b, st_b + 2, st_b + 3))

    tpl = np.array(verts, dtype=np.float32)
    nv = len(tpl)
    all_v, all_f, all_mats = [], [], []
    for i in range(count):
        off = i * nv
        for v in tpl:
            all_v.append((float(v[0]), float(v[1]), float(v[2]) - 500.0))
        for f in calyx_faces:
            all_f.append(tuple(idx + off for idx in f))
            all_mats.append(0)
        for f in stamen_faces:
            all_f.append(tuple(idx + off for idx in f))
            all_mats.append(1)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(all_v, [], all_f)
    mesh.polygons.foreach_set("material_index", np.array(all_mats, dtype=np.int32))
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.materials.append(mat_calyx)
    mesh.materials.append(mat_stamen)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    return obj, tpl


def build_environment(spec: dict, mats: dict):
    w = spec["world"]
    rng = random.Random(spec["seed"])
    p0_pos = Vector(w["p0_flower"]["pos"])

    # 1. Dark glassy mirror lake plane
    bm_lake = bmesh.new()
    bmesh.ops.create_grid(bm_lake, x_segments=4, y_segments=4, size=260.0)
    lake = finalize_mesh_obj("GEO-MirrorLake", bm_lake, mats["water"], smooth=True)
    lake.location = (0.0, 22.0, w["lake_z"])

    # 2. Stratified Fractured Basalt Shore + Flat Landmark Slabs + 1,600 Macro Pebbles + 320 Velvet Moss Cushions!
    bm_sh = bmesh.new()
    uv_sh = bm_sh.loops.layers.uv.new("UVMap")
    bmesh.ops.create_grid(bm_sh, x_segments=200, y_segments=140, size=1.0)
    for v in bm_sh.verts:
        wx = v.co.x * 32.0
        wy = lerp(-74.0, -48.6, (v.co.y + 1.0) * 0.5)
        wz = shore_surface_z(wx, wy, w["shore_z"])
        v.co = Vector((wx, wy, wz))
    for f in bm_sh.faces:
        for loop in f.loops:
            loop[uv_sh].uv = (loop.vert.co.x * 0.16, loop.vert.co.y * 0.16)
    finalize_mesh_obj("GEO-Shore", bm_sh, mats["shore"], smooth=True)

    # Angular faceted stratified basalt shelves & flat landmark boulders (NO potato icospheres!)
    bm_b = bmesh.new()
    boulders = [
        ( 6.8, -51.8, 1.05, 0.85, 0.42),
        ( 1.9, -51.6, 0.72, 0.55, 0.28),
        (-4.8, -51.9, 1.35, 0.95, 0.55),
        (-8.2, -53.2, 1.80, 1.25, 0.78),
        ( 9.5, -52.8, 1.65, 1.15, 0.68),
        ( 6.0, -54.8, 0.78, 0.62, 0.30),
        (-3.6, -54.2, 0.65, 0.55, 0.25),
        (-1.1, -51.7, 0.92, 0.64, 0.36),
        ( 2.35, -52.1, 0.62, 0.48, 0.22),
        ( 0.45, -51.85, 0.58, 0.44, 0.20),
        # Flat basalt shelf stones framing P0 & midground shore (clear of C5b camera lane!)
        ( 3.20, -51.55, 0.48, 0.38, 0.14),
        ( 5.35, -51.65, 0.66, 0.46, 0.22),
        ( 4.95, -53.15, 0.44, 0.34, 0.12),
        (-2.65, -52.30, 0.85, 0.58, 0.30),
        (-6.40, -51.60, 1.45, 0.92, 0.46),
        ( 8.10, -51.45, 1.28, 0.88, 0.44),
        (12.20, -52.90, 2.20, 1.65, 1.05),
        (-12.5, -52.60, 2.35, 1.70, 1.15),
    ]
    for ib, (bx, by, sx, sy, sz) in enumerate(boulders):
        bz = shore_surface_z(bx, by, w["shore_z"]) - sz * 0.28
        yaw_b = rng.uniform(0.0, 6.283)
        rb = Matrix.Rotation(yaw_b, 3, "Z")
        res = bmesh.ops.create_icosphere(bm_b, subdivisions=2, radius=1.0)
        for v in res["verts"]:
            p = v.co.copy()
            # Cleavage plane flattening top + angular hexagonal rock shear!
            if p.z > 0.38:
                p.z = lerp(0.38, 0.54, (p.z - 0.38) / 0.62)
            shear = 1.0 + 0.18 * math.sin(p.x * 3.1 + ib) - 0.14 * abs(math.cos(p.y * 2.7 - ib))
            strat = 0.06 * round(p.z * 5.0)
            v.co = Vector((bx, by, bz)) + (rb @ Vector(((p.x * shear + strat) * sx, p.y * shear * sy, p.z * sz)))
    finalize_mesh_obj("GEO-ShoreBoulders", bm_b, mats["shore"], smooth=False)

    # 1,600 Multi-Scale River-Worn Basalt Slate Cobbles & Shore Shingle (R02/R12 macro texture + shoreline shingle!)
    bm_peb = bmesh.new()
    peb_centers = [
        (4.0, -52.4, 1.85),   # dense gravel/pebbles framing P0 macro!
        (4.4, -52.2, 2.40),   # C5b macro meadow crevices!
        (1.5, -52.0, 3.20),
        (-1.5, -52.4, 3.40),
        (7.0, -52.4, 3.60),
        (-4.5, -52.6, 3.80),
    ]
    for ip in range(1600):
        if ip < 1150:
            cx, cy, rad = peb_centers[ip % len(peb_centers)]
            ang = rng.uniform(0.0, 6.283)
            rr = rad * (rng.random() ** 0.72)
            px = cx + rr * math.cos(ang)
            py = cy + rr * math.sin(ang) * 0.68
        else:
            px = rng.uniform(-14.5, 15.5)
            py = rng.uniform(-56.8, -50.8)
        if not (-16.0 <= px <= 16.5 and -57.2 <= py <= -50.6):
            continue
        if math.hypot(px - p0_pos.x, py - p0_pos.y) < 0.08:
            continue
        pz = shore_surface_z(px, py, w["shore_z"]) - 0.006
        pr = rng.uniform(0.012, 0.056) if ip < 900 else rng.uniform(0.024, 0.092)
        pf = pr * rng.uniform(0.68, 1.30)
        ph = pr * rng.uniform(0.24, 0.44)
        yaw_p = rng.uniform(0.0, 6.283)
        res_p = bmesh.ops.create_icosphere(bm_peb, subdivisions=2, radius=1.0)
        mp_p = Matrix.Translation((px, py, pz)) @ Matrix.Rotation(yaw_p, 4, "Z") @ Matrix.Diagonal((pr, pf, ph, 1.0))
        for v in res_p["verts"]:
            c_l = v.co
            mod = 1.0 + 0.14 * math.sin(c_l.x * 3.1 + ip * 0.7) * math.cos(c_l.y * 2.7 - ip * 0.3)
            flat_top = lerp(c_l.z, 0.55, 0.35) if c_l.z > 0.35 else c_l.z
            v.co = mp_p @ Vector((c_l.x * mod, c_l.y * mod, flat_top))
    finalize_mesh_obj("GEO-ShorePebbles", bm_peb, mats["shore"], smooth=True)

    # 420 Delicate Velvety Subterranean Moss Cushions clustered naturally in boulder crevices (R10/world02!)
    bm_ms = bmesh.new()
    for im in range(140):
        if im < len(boulders) * 6:
            bx, by, sx, sy, _ = boulders[im % len(boulders)]
            ang = rng.uniform(0.0, 6.283)
            mx0 = bx + (sx * rng.uniform(0.65, 1.02)) * math.cos(ang)
            my0 = by + (sy * rng.uniform(0.65, 1.02)) * math.sin(ang)
        else:
            mx0 = rng.uniform(-12.5, 13.5)
            my0 = rng.uniform(-56.5, -51.4)
        for ic in range(3):
            mx = mx0 + rng.uniform(-0.07, 0.07)
            my = my0 + rng.uniform(-0.07, 0.07)
            mz = shore_surface_z(mx, my, w["shore_z"])
            if mz < 0.28:
                continue
            mr = rng.uniform(0.026, 0.076)
            mh = mr * rng.uniform(0.20, 0.34)
            res_m = bmesh.ops.create_icosphere(bm_ms, subdivisions=2, radius=1.0)
            for v in res_m["verts"]:
                vz_f = max(-0.02, v.co.z)
                lump = 1.0 + 0.20 * math.sin(v.co.x * 4.5 + ic) * math.cos(v.co.y * 4.1 + im)
                v.co = Vector((mx + v.co.x * mr * lump, my + v.co.y * mr * lump, mz - 0.006 + vz_f * mh))
    finalize_mesh_obj("GEO-ShoreMossTufts", bm_ms, mats["shore_moss"], smooth=True)

    # 3. Plumb Dual-Tier Classical Aqueduct + Pantheon-Parthenon Sanctuary + 4-Tier Winter Milky Way!
    aurora_mode = spec.get("aurora_mode", "sky_veil")
    bridge = build_ruined_arch_bridge(w["arch_bridge"], mats["stone"], rng)
    sunken_city = build_sunken_sanctuary_city(mats["sunken_city"], rng)
    cavern_roof = build_cavern_roof_canopy(mats["cavern_roof"], rng)
    cavern_walls, cavern_headlands = build_cavern_walls_and_headlands(mats["cavern_roof"], mats["shore"], rng)
    cavern_stalactites = build_cavern_stalactites(mats["cavern_roof"], rng)
    star_vault = build_cavern_star_vault(mats["star_vault"], rng, aurora_mode=aurora_mode)
    starburst_hero = build_winter_starburst_heroes(mats["starburst_hero"], rng)
    aurora_veil = build_aurora_veils(mats["aurora_veil"], aurora_mode=aurora_mode)

    # 4. Sculpted Organic Karst Limestone Columns & Hanging Stalactite Curtains (ZERO smooth traffic cones!)
    bm_pil = bmesh.new()

    def add_karst_column(cx: float, cy: float, r_base: float, r_mid: float, r_top: float, h: float, seed_off: float, hanging_only: bool = False):
        n_rings, n_seg = 22, 18
        rings = []
        for ir in range(n_rings):
            u = ir / (n_rings - 1)
            z = lerp(146.0 - h, 146.0, u) if hanging_only else lerp(-4.0, h, u)
            if hanging_only:
                r_env = lerp(0.55, r_top, u ** 1.35)
            else:
                # Organic hourglass limestone flowstone column swelling near floor & ceiling
                r_env = r_mid + (r_base - r_mid) * ((1.0 - u) ** 2.2) + (r_top - r_mid) * (u ** 2.4)
            # Subtle meandering spine drift
            dx = 2.4 * math.sin(u * 4.2 + seed_off)
            dy = 1.8 * math.cos(u * 3.5 + seed_off * 1.3)
            ring = []
            for j in range(n_seg):
                ang = 2.0 * math.pi * j / n_seg
                # Multi-frequency fluted limestone ribs + terraced flowstone shelves
                flute = 1.0 + 0.16 * math.sin(ang * 5.0 + seed_off + u * 2.5) + 0.10 * math.cos(ang * 9.0 - u * 4.0)
                terrace = 1.0 + 0.12 * math.sin(u * 19.0 + seed_off * 2.0) * math.cos(ang * 3.0 + seed_off)
                rr = max(0.35, r_env * flute * terrace)
                ring.append(bm_pil.verts.new((cx + dx + rr * math.cos(ang), cy + dy + rr * math.sin(ang), z)))
            rings.append(ring)
        for ir in range(n_rings - 1):
            for j in range(n_seg):
                jn = (j + 1) % n_seg
                bm_pil.faces.new((rings[ir][j], rings[ir][jn], rings[ir + 1][jn], rings[ir + 1][j]))
        bm_pil.faces.new(list(reversed(rings[0])))
        bm_pil.faces.new(rings[-1])

    for i_p, p in enumerate(w["far_pillars"]):
        add_karst_column(p["x"], p["y"], p["r_base"] * 1.20, p["r_top"] * 0.85, p["r_top"] * 0.72, p["h"], i_p * 1.73, hanging_only=False)
    finalize_mesh_obj("GEO-FarPillars", bm_pil, mats["pillar"], smooth=False)

    # 5. TYPE-MOON High-Res Full Moon (disk-projected Northern Hemisphere maria) + Atmospheric Corona Halo
    m_pos = Vector(w["moon"]["pos"])
    m_rad = float(w["moon"]["radius"])
    bm_m = bmesh.new()
    uv_m = bm_m.loops.layers.uv.new("UVMap")
    bmesh.ops.create_uvsphere(bm_m, u_segments=96, v_segments=48, radius=m_rad)
    # Orthographic disk UV onto moon_sky.jpg center (cx=0.5, cy=0.5, r_px=135.5 of 1376x768) facing -Y_local!
    r_uv_x = 135.5 / 1376.0
    r_uv_y = 135.5 / 768.0
    for f in bm_m.faces:
        for loop in f.loops:
            co = loop.vert.co
            dx_n = clamp(co.x / m_rad, -1.0, 1.0)
            dz_n = clamp(co.z / m_rad, -1.0, 1.0)
            loop[uv_m].uv = (0.5 + dx_n * r_uv_x, 0.5 + dz_n * r_uv_y)
    moon_obj = finalize_mesh_obj("GEO-FullMoon", bm_m, mats["moon"], smooth=True)
    moon_obj.location = m_pos
    moon_obj.rotation_mode = "QUATERNION"
    if hasattr(moon_obj, "visible_shadow"):
        moon_obj.visible_shadow = False

    # Outer 2-layer ethereal corona disc (4.5x moon radius, parented cleanly behind Moon toward -Y_local camera view!)
    bm_mc = bmesh.new()
    uv_mc = bm_mc.loops.layers.uv.new("UVMap")
    cr = m_rad * 4.5
    v0 = bm_mc.verts.new((-cr, m_rad * 0.45, -cr))
    v1 = bm_mc.verts.new(( cr, m_rad * 0.45, -cr))
    v2 = bm_mc.verts.new(( cr, m_rad * 0.45,  cr))
    v3 = bm_mc.verts.new((-cr, m_rad * 0.45,  cr))
    f_mc = bm_mc.faces.new((v0, v1, v2, v3))
    for loop, uv_co in zip(f_mc.loops, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))):
        loop[uv_mc].uv = uv_co
    moon_corona = finalize_mesh_obj("GEO-MoonCorona", bm_mc, mats["moon_corona"], smooth=False)
    moon_corona.parent = moon_obj
    moon_corona.location = (0.0, 0.0, 0.0)
    if hasattr(moon_corona, "visible_shadow"):
        moon_corona.visible_shadow = False

    # Main diagonal moonlight shaft intersecting C5a broadside awakening point (27.5, -39.5, 16.5)!
    shaft_bot = Vector((20.5, -30.5, -2.0))
    shaft_vec = m_pos - shaft_bot
    bm_shaft = bmesh.new()
    bmesh.ops.create_cone(bm_shaft, cap_ends=False, segments=40, radius1=19.0, radius2=10.5, depth=shaft_vec.length)
    shaft = finalize_mesh_obj("GEO-MoonShaft", bm_shaft, mats["shaft"], smooth=True)
    shaft.location = 0.5 * (shaft_bot + m_pos)
    shaft.rotation_mode = "QUATERNION"
    shaft.rotation_quaternion = shaft_vec.normalized().to_track_quat("Z", "Y")
    if hasattr(shaft, "visible_shadow"):
        shaft.visible_shadow = False

    # Soft gossamer sliver of moonlight falling diagonally onto P0 in C1 & C8 (no mist wall!)
    bm_p0b = bmesh.new()
    bmesh.ops.create_cone(bm_p0b, cap_ends=False, segments=32, radius1=0.62, radius2=0.22, depth=12.0)
    p0_beam = finalize_mesh_obj("GEO-P0_MoonBeam", bm_p0b, mats["p0_beam"], smooth=True)
    p0_beam.location = p0_pos + Vector((0.85, 0.60, 5.7))
    p0_beam.rotation_euler = (math.radians(-6.0), math.radians(10.0), 0.0)
    if hasattr(p0_beam, "visible_shadow"):
        p0_beam.visible_shadow = False

    # 5b. High-res Smooth Organic 3D Rocky Ceiling Fissure Arch for C7b (128x10 stratified cavern opening — ZERO PS2 flats!)
    bm_fis = bmesh.new()
    n_fseg = 128
    tiers = [
        (32.0, 23.5, 15.2, 54.0, 36.0),
        (35.0, 21.8, 14.0, 52.0, 35.0),
        (38.0, 20.4, 13.0, 50.0, 34.0),
        (41.5, 19.6, 12.4, 49.0, 33.5),
        (45.5, 20.6, 13.1, 49.0, 33.5),
        (50.5, 22.8, 14.6, 51.0, 35.0),
    ]
    tier_in = []
    tier_out = []
    crags = [
        1.0
        + 0.11 * math.sin(2.0 * math.pi * i / n_fseg * 4.0 + 0.4)
        + 0.06 * math.cos(2.0 * math.pi * i / n_fseg * 7.0)
        + 0.035 * math.sin(2.0 * math.pi * i / n_fseg * 13.0)
        + 0.018 * math.cos(2.0 * math.pi * i / n_fseg * 21.0)
        for i in range(n_fseg)
    ]
    for ti, (y_t, rx_i, rz_i, rx_o, rz_o) in enumerate(tiers):
        in_r, out_r = [], []
        for i in range(n_fseg):
            ang = 2.0 * math.pi * i / n_fseg
            ca, sa = math.cos(ang), math.sin(ang)
            cr = crags[i] * (1.0 + 0.02 * math.sin(ang * 9.0 + ti * 1.1))
            in_r.append(bm_fis.verts.new((m_pos.x + rx_i * cr * ca, y_t, m_pos.z + rz_i * cr * sa)))
            out_r.append(bm_fis.verts.new((m_pos.x + rx_o * ca, y_t, m_pos.z + rz_o * sa)))
        tier_in.append(in_r)
        tier_out.append(out_r)
    for i in range(n_fseg):
        ni = (i + 1) % n_fseg
        bm_fis.faces.new((tier_in[0][i], tier_out[0][i], tier_out[0][ni], tier_in[0][ni]))
        for ti in range(len(tiers) - 1):
            bm_fis.faces.new((tier_in[ti][i], tier_in[ti][ni], tier_in[ti + 1][ni], tier_in[ti + 1][i]))
    fissure_obj = finalize_mesh_obj("GEO-CeilingFissure3D", bm_fis, mats["fissure"], smooth=True)
    if hasattr(fissure_obj, "visible_shadow"):
        fissure_obj.visible_shadow = False
    fissure_obj.hide_render = True

    # 6. Botanical Lone Young P0 Flower (stays open & intact 0..96s, never sheds, NON-EMISSIVE per FL-01 v0.8!)
    stem_mesh, bud_mesh, open_heart_mesh, petal_mesh = _create_botanical_flower_meshes(
        mats["stem_leaf"],
        mats["calyx_bud"],
        mats["bud_seam"],
        mats["receptacle"],
        mats["stamen_pistil"],
        mats["petal"],
        mats["seed_capsule"],
    )

    p0_stem = bpy.data.objects.new("GEO-P0_Flower", stem_mesh)
    bpy.context.scene.collection.objects.link(p0_stem)
    p0_stem.location = p0_pos - Vector((0.0, 0.0, 0.012))
    p0_stem.scale = (1.38, 1.38, 1.38)
    p0_heart = bpy.data.objects.new("GEO-P0_OpenHeart", open_heart_mesh)
    bpy.context.scene.collection.objects.link(p0_heart)
    p0_heart.parent = p0_stem
    p0_heart.location = (0.0, 0.0, 0.142)
    p0_petals = []
    for k in range(5):
        ang = 2.0 * math.pi * k / 5.0
        pp = bpy.data.objects.new(f"GEO-P0_Petal_{k}", petal_mesh)
        bpy.context.scene.collection.objects.link(pp)
        pp.parent = p0_stem
        pp.location = (0.0, -0.0032, 0.141 + k * 0.0007)
        pp.rotation_euler = (math.radians(4.8 if (k % 2 == 0) else -4.8), math.radians(-11.0), ang)
        # G=0.0 so young P0 basal dry fruit stays attached matte honey-ochre (no self-glow!)
        pp.color = (1.0, 0.0, 1.0, 1.0)
        p0_petals.append(pp)

    # Crystal nocturnal dew bead trembling gently on top of petal #0 cup of young P0 (physical catchlight!)
    bm_dw = bmesh.new()
    bmesh.ops.create_uvsphere(bm_dw, u_segments=14, v_segments=10, radius=0.0042)
    p0_dew = finalize_mesh_obj("GEO-P0_DewBead", bm_dw, mats["water_fx"], smooth=True)
    p0_dew.parent = p0_stem
    p0_dew.location = (0.052, -0.002, 0.168)
    if hasattr(p0_dew, "visible_shadow"):
        p0_dew.visible_shadow = False

    # 7. Clustered 450-Flower Shore Meadow (140 Hero Interactive Flowers + 310 Colony Flowers!)
    pc_xy = [(p["pos"][0], p["pos"][1]) for p in w["pcs"]]
    # Organic cluster centers tucked along wet rock crevices & water's edge (true 疎密!)
    cluster_centers = [
        ( 4.1, -52.5, 1.35), ( 5.5, -52.2, 1.15), ( 2.8, -52.3, 1.25), ( 6.9, -53.0, 1.30),
        ( 4.8, -53.8, 1.15), ( 2.2, -53.8, 1.10), ( 7.8, -52.1, 1.35), ( 1.4, -52.6, 1.10),
        ( 5.8, -54.5, 1.25), ( 3.1, -54.7, 1.10), (-1.5, -52.4, 1.50), (-3.8, -52.8, 1.60),
        ( 9.2, -53.2, 1.80), (-6.2, -53.4, 1.90), (11.0, -53.8, 2.00), (-0.4, -52.2, 1.20),
        ( 3.9, -51.7, 0.90), ( 6.2, -51.8, 1.00),
        # v7.7 2=A Act 1 botanical scale clusters tucked around C2/C3 foreground basalt ridges
        (-1.1, -51.8, 0.95), ( 0.45, -51.9, 0.85), ( 2.35, -52.0, 0.85),
    ]

    def sample_clustered_shore_pt(hero: bool) -> tuple[float, float] | None:
        for _ in range(28):
            if hero:
                cx, cy, rad = cluster_centers[rng.randrange(12 if rng.random() < 0.85 else len(cluster_centers))]
            else:
                cx, cy, rad = cluster_centers[rng.randrange(len(cluster_centers))]
            ang = rng.uniform(0.0, 6.283)
            r = rad * (rng.random() ** 0.65)
            bx = cx + r * math.cos(ang)
            by = cy + r * math.sin(ang) * 0.72
            if not (-13.0 <= bx <= 14.5 and -56.8 <= by <= -52.0):
                continue
            if any(abs(bx - b_x) < b_sx * 0.85 and abs(by - b_y) < b_sy * 0.85 for b_x, b_y, b_sx, b_sy, _ in boulders):
                continue
            if math.hypot(bx - p0_pos.x, by - p0_pos.y) < 0.24:
                continue
            if any(math.hypot(bx - px, by - py) < 0.45 for px, py in pc_xy):
                continue
            # Keep narrow 0.34m camera-lens lane clear in C5b so no flower clips inside the lens
            if -56.0 <= by <= -52.8 and abs(bx - lerp(3.4, 3.8, clamp((by + 55.8) / 3.0, 0.0, 1.0))) < 0.36:
                continue
            return bx, by
        return None

    # 7a. 140 Hero Foreground Flowers — clean living closed buds before bloom, 10% shadow-edge dormant buds!
    hero_blooms = []
    for idx in range(140):
        pt = sample_clustered_shore_pt(hero=True)
        if pt is None:
            continue
        bx, by = pt
        bz = shore_surface_z(bx, by, w["shore_z"]) - 0.022
        sc = rng.uniform(0.95, 1.36)
        yaw = rng.uniform(0.0, 6.283)
        droop_deg = rng.uniform(16.0, 26.0)
        dist_p0 = math.hypot(bx - p0_pos.x, by - p0_pos.y)
        wave_u = clamp((by + 55.8) / 4.2 * 0.68 + abs(bx - 4.0) / 8.5 * 0.32, 0.0, 1.0)
        stay_dormant = (dist_p0 >= 2.6) and (idx % 10 == 9)
        t_bloom = 999.0 if stay_dormant else (lerp(30.25, 32.65, wave_u) + rng.uniform(-0.12, 0.12))

        roll_mat = rng.random()
        if dist_p0 < 2.2:
            shed_count = 5
        elif roll_mat < 0.64:
            shed_count = 5
        elif roll_mat < 0.80:
            shed_count = rng.choice((2, 3, 4))
        else:
            shed_count = 0

        stem_o = bpy.data.objects.new(f"GEO-HeroStem_{idx:03d}", stem_mesh)
        bpy.context.scene.collection.objects.link(stem_o)
        stem_o.location = (bx, by, bz)
        stem_o.scale = (sc, sc, sc)

        bud_cup = bpy.data.objects.new(f"GEO-HeroBud_{idx:03d}", bud_mesh)
        bpy.context.scene.collection.objects.link(bud_cup)
        bud_cup.parent = stem_o
        bud_cup.location = (0.0, -0.0032, 0.140)

        heart_o = bpy.data.objects.new(f"GEO-HeroHeart_{idx:03d}", open_heart_mesh)
        bpy.context.scene.collection.objects.link(heart_o)
        heart_o.parent = stem_o
        heart_o.location = (0.0, 0.0, 0.142)
        heart_o.hide_render = True

        petals_5 = []
        shed_order = list(range(5))
        rng.shuffle(shed_order)
        shed_set = set(shed_order[:shed_count])
        for k in range(5):
            po = bpy.data.objects.new(f"GEO-HeroPetal_{idx:03d}_{k}", petal_mesh)
            bpy.context.scene.collection.objects.link(po)
            if hasattr(po, "visible_shadow"):
                po.visible_shadow = False
            will_shed = (not stay_dormant) and (k in shed_set)
            if will_shed:
                if idx < 18 and k < 2:
                    t_det = rng.uniform(33.3, 34.75)
                else:
                    t_det = rng.uniform(34.95, 35.65)
            else:
                t_det = 999.0
            hx = bx + rng.uniform(-0.45, 0.65)
            hy = by + rng.uniform(0.25, 1.55)
            hz = bz + 0.14 * sc + rng.uniform(0.55, 2.85)
            petals_5.append({
                "obj": po,
                "az": 2.0 * math.pi * k / 5.0,
                "stag": k * 0.06,
                "t_det": t_det,
                "hover": Vector((hx, hy, hz)),
                "phase": (bx * 0.12 + by * 0.09) + rng.uniform(-0.4, 0.4),
                "speed": rng.uniform(0.85, 1.35),
                "ribbon": (idx + k) % 3,
            })
        hero_blooms.append((stem_o, bud_cup, heart_o, petals_5, t_bloom, sc, yaw, droop_deg))

    # 7b. 310 Smooth Organic Shore Colony Flowers (clean stems + REAL closed buds before bloom + shed calyxes after dispersal!)
    bm_cs = bmesh.new()
    colony_data = []
    for idx in range(310):
        pt = sample_clustered_shore_pt(hero=False)
        if pt is None:
            bx = rng.uniform(-11.0, 13.0)
            by = rng.uniform(-56.6, -52.05)
        else:
            bx, by = pt
        bz = shore_surface_z(bx, by, w["shore_z"]) - 0.022
        sc = rng.uniform(0.84, 1.24)
        yaw = rng.uniform(0.0, 6.283)
        m_st = Matrix.Translation((bx, by, bz)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Scale(sc, 4)
        nb_s = len(bm_cs.faces)
        st_rows = []
        for ir in range(5):
            u = ir / 4.0
            cx_u = 0.005 * math.sin(u * math.pi)
            cz_u = u * 0.142
            rr = lerp(0.0044, 0.0024, u)
            row = []
            for j in range(8):
                aj = 2.0 * math.pi * j / 8.0
                row.append(bm_cs.verts.new(m_st @ Vector((cx_u + rr * math.cos(aj), rr * math.sin(aj), cz_u))))
            st_rows.append(row)
        for ir in range(4):
            for j in range(8):
                jn = (j + 1) % 8
                bm_cs.faces.new((st_rows[ir][j], st_rows[ir][jn], st_rows[ir + 1][jn], st_rows[ir + 1][j]))
        for u_lf, az_l, pitch_l, ln_l, wd_l in ((0.18, 0.3, -0.45, 0.082, 0.013), (0.34, 3.4, -0.50, 0.074, 0.012), (0.54, 1.8, -0.35, 0.060, 0.010)):
            ml_f = m_st @ Matrix.Translation((0.005 * math.sin(u_lf * math.pi), 0.0, u_lf * 0.142)) @ Matrix.Rotation(az_l, 4, "Z") @ Matrix.Rotation(pitch_l, 4, "Y")
            nu_l, nv_l = 5, 3
            gl = []
            for iu in range(nu_l):
                u = iu / (nu_l - 1)
                hw = wd_l * math.sin((u ** 0.7) * math.pi) * lerp(0.25, 1.0, smoothstep(0.0, 0.18, u))
                az_z = 0.010 * math.sin(u * math.pi) - 0.007 * (u ** 2.2)
                r_lf = []
                for iv in range(nv_l):
                    v = (iv / (nv_l - 1)) * 2.0 - 1.0
                    r_lf.append(bm_cs.verts.new(ml_f @ Vector((u * ln_l, v * hw, az_z + abs(v) * 0.0024 * math.sin(u * math.pi)))))
                gl.append(r_lf)
            for iu in range(nu_l - 1):
                for iv in range(nv_l - 1):
                    bm_cs.faces.new((gl[iu][iv], gl[iu + 1][iv], gl[iu + 1][iv + 1], gl[iu][iv + 1]))
        bm_cs.faces.ensure_lookup_table()
        for f in bm_cs.faces[nb_s:]:
            f.material_index = 0

        # Tiny lateral closed bud along upper node on every colony stem
        nb_sb = len(bm_cs.faces)
        sb_m = m_st @ Matrix.Translation((0.004, 0.0, 0.088)) @ Matrix.Rotation(math.radians(28.0), 4, "Y")
        res_sb = bmesh.ops.create_cone(bm_cs, cap_ends=True, segments=6, radius1=0.0058, radius2=0.0012, depth=0.024)
        bmesh.ops.transform(bm_cs, matrix=sb_m @ Matrix.Translation((0.0, 0.0, 0.014)), verts=res_sb["verts"])
        bm_cs.faces.ensure_lookup_table()
        for f in bm_cs.faces[nb_sb:]:
            f.material_index = 1

        in_p0_spot = math.hypot(bx - p0_pos.x, by - p0_pos.y) < 2.2
        stay_dormant = (not in_p0_spot) and (idx % 9 == 8)
        wave_u = clamp((by + 55.8) / 4.2 * 0.65 + abs(bx - 4.0) / 11.0 * 0.35, 0.0, 1.0)
        t_bl = 999.0 if stay_dormant else (lerp(30.3, 32.85, wave_u) + rng.uniform(-0.15, 0.15))
        t_shed = 999.0 if stay_dormant else (rng.uniform(34.7, 36.2) if (in_p0_spot or rng.random() < 0.78) else 999.0)
        colony_data.append((bx, by, bz + 0.140 * sc, sc, yaw, t_bl, t_shed))

    cs_mesh = bpy.data.meshes.new("MESH-ColonyStems")
    bm_cs.to_mesh(cs_mesh)
    bm_cs.free()
    for p in cs_mesh.polygons:
        p.use_smooth = True
    cs_mesh.materials.append(mats["stem_leaf"])
    cs_mesh.materials.append(mats["calyx_bud"])
    cs_obj = bpy.data.objects.new("GEO-ColonyStems", cs_mesh)
    bpy.context.scene.collection.objects.link(cs_obj)

    colony_buds_obj, colony_bud_tpl = _build_colony_bud_mesh(
        "GEO-ColonyBuds",
        len(colony_data),
        mats["calyx_bud"],
        mats["bud_seam"],
    )
    colony_shed_obj, colony_shed_tpl = _build_colony_shed_calyx_mesh(
        "GEO-ColonyShedCalyxes",
        len(colony_data),
        mats["calyx_bud"],
        mats["stamen_pistil"],
    )
    colony_crowns_obj, colony_tpl = _build_colony_crown_mesh(
        "GEO-ColonyCrowns",
        len(colony_data),
        mats["flower_white"],
        mats["stamen_pistil"],
        mats["calyx_bud"],
    )
    colony_pos = np.array([[d[0], d[1], d[2]] for d in colony_data], dtype=np.float32)
    colony_sc = np.array([d[3] for d in colony_data], dtype=np.float32)
    colony_yaw = np.array([d[4] for d in colony_data], dtype=np.float32)
    colony_tbl = np.array([d[5] for d in colony_data], dtype=np.float32)
    colony_tshed = np.array([d[6] for d in colony_data], dtype=np.float32)

    # 7c. Aqueduct Crown Blossoms resting flush ONLY along surviving masonry (never over collapsed water bays!)
    bridge_data = []
    for idx in range(180):
        bx = None
        dz_b = None
        for _ in range(32):
            cand_x = rng.uniform(37.6, 84.0) if idx < 110 else rng.uniform(-84.0, -37.6)
            dz_c = viaduct_deck_z(cand_x)
            if dz_c is not None:
                bx = cand_x
                dz_b = dz_c
                break
        if bx is None or dz_b is None:
            continue
        vy, _ = viaduct_curve(bx)
        by = vy + rng.uniform(-1.35, 1.35)
        bz = dz_b + 0.16 + rng.uniform(-0.06, 0.10)
        wave_b = clamp((abs(bx) - 36.0) / 50.0, 0.0, 1.0)
        t_bl = lerp(32.25, 34.35, wave_b) + rng.uniform(-0.15, 0.15)
        t_shed = rng.uniform(35.1, 36.6) if rng.random() < 0.80 else 999.0
        b_sc = rng.uniform(3.6, 6.2)
        bridge_data.append((bx, by, bz, b_sc, rng.uniform(0, 6.283), t_bl, t_shed))
    bridge_crowns_obj, bridge_tpl = _build_colony_crown_mesh(
        "GEO-BridgeCrowns",
        len(bridge_data),
        mats["flower_white"],
        mats["stamen_pistil"],
        mats["calyx_bud"],
    )
    bridge_pos = np.array([[d[0], d[1], d[2]] for d in bridge_data], dtype=np.float32)
    bridge_sc = np.array([d[3] for d in bridge_data], dtype=np.float32)
    bridge_yaw = np.array([d[4] for d in bridge_data], dtype=np.float32)
    bridge_tbl = np.array([d[5] for d in bridge_data], dtype=np.float32)
    bridge_tshed = np.array([d[6] for d in bridge_data], dtype=np.float32)

    # 8. Act 1 & Act 3 Physical Consequence FX (Water drop, concentric ripples, breach rings, spray curtains, belly drops, awakening mist!)
    # 8a. Falling water droplet (C1 at t=2.12..2.40s)
    bm_wd = bmesh.new()
    res_wd = bmesh.ops.create_uvsphere(bm_wd, u_segments=12, v_segments=8, radius=1.0)
    for v in res_wd["verts"]:
        tz = clamp((v.co.z + 1.0) * 0.5, 0.0, 1.0)
        v.co.x *= 0.022 * lerp(1.1, 0.25, tz ** 1.3)
        v.co.y *= 0.022 * lerp(1.1, 0.25, tz ** 1.3)
        v.co.z *= 0.055
    water_drop = finalize_mesh_obj("GEO-WaterDrop", bm_wd, mats["water_fx"], smooth=True)
    water_drop.hide_render = True

    # 8b. Concentric lake ripples cleanly on offshore mirror water (never clipping into shore!)
    ripples = []
    for i in range(3):
        bm_r = bmesh.new()
        res = bmesh.ops.create_circle(bm_r, cap_ends=False, radius=1.0, segments=56)
        bmesh.ops.extrude_edge_only(bm_r, edges=bm_r.edges[:])
        outer = [v for v in bm_r.verts if v not in res["verts"]]
        for v in outer:
            v.co *= 1.038
        r_obj = finalize_mesh_obj(f"GEO-Ripple_{i}", bm_r, mats["water_fx"], smooth=True)
        r_obj.location = (p0_pos.x + 1.2, -46.8, w["lake_z"] + 0.015)
        r_obj.hide_render = True
        ripples.append(r_obj)

    # 8c. Whale water breach rings (C2-C3: 9.0..17.5s)
    breach_rings = []
    for i in range(4):
        bm_br = bmesh.new()
        res = bmesh.ops.create_circle(bm_br, cap_ends=False, radius=1.0, segments=64)
        bmesh.ops.extrude_edge_only(bm_br, edges=bm_br.edges[:])
        outer = [v for v in bm_br.verts if v not in res["verts"]]
        for v in outer:
            v.co *= 1.10
        br_obj = finalize_mesh_obj(f"GEO-BreachRing_{i}", bm_br, mats["spray"], smooth=True)
        if hasattr(br_obj, "visible_shadow"):
            br_obj.visible_shadow = False
        br_obj.hide_render = True
        breach_rings.append(br_obj)

    # 8d. Sleek low curved translucent V-wake splash sheets skimming water surface (ZERO puffy cotton balls!)
    spray_objs = []
    for side, tag in ((-1.0, "L"), (1.0, "R")):
        bm_sp = bmesh.new()
        n_u, n_v = 14, 6
        grid = []
        for iu in range(n_u):
            u = iu / (n_u - 1)
            row = []
            for iv in range(n_v):
                v = iv / (n_v - 1)
                cx = side * (lerp(1.8, 7.2, u) + v * 1.6 * math.sin(u * math.pi))
                cy = lerp(7.2, -5.5, u)
                cz = -1.1 + v * lerp(0.35, 1.35 * math.sin(u * math.pi) ** 0.75 + 0.15, u)
                row.append(bm_sp.verts.new((cx, cy, cz)))
            grid.append(row)
        for iu in range(n_u - 1):
            for iv in range(n_v - 1):
                bm_sp.faces.new((grid[iu][iv], grid[iu + 1][iv], grid[iu + 1][iv + 1], grid[iu][iv + 1]))
        sp_o = finalize_mesh_obj(f"GEO-Spray_{tag}", bm_sp, mats["spray"], smooth=True)
        if hasattr(sp_o, "visible_shadow"):
            sp_o.visible_shadow = False
        sp_o.hide_render = True
        spray_objs.append(sp_o)

    # 8e. Falling belly water streaks in C4a (18.2..21.4s)
    belly_drops = []
    bm_bd = bmesh.new()
    bmesh.ops.create_cone(bm_bd, cap_ends=True, segments=6, radius1=0.012, radius2=0.005, depth=0.32)
    bd_mesh = bpy.data.meshes.new("MESH-BellyDrop")
    bm_bd.to_mesh(bd_mesh)
    bm_bd.free()
    bd_mesh.materials.append(mats["spray"])
    for i in range(18):
        bdo = bpy.data.objects.new(f"GEO-BellyDrop_{i:02d}", bd_mesh)
        bpy.context.scene.collection.objects.link(bdo)
        if hasattr(bdo, "visible_shadow"):
            bdo.visible_shadow = False
        bdo["ox"] = rng.uniform(-2.6, 2.8)
        bdo["oy"] = rng.uniform(-49.0, -40.0)
        bdo["ph"] = rng.uniform(0.0, 1.0)
        bdo.hide_render = True
        belly_drops.append(bdo)

    # 8f. Awakening V-shaped silver mist breath plume in C5a (27.0..30.0s)
    bm_bm = bmesh.new()
    for side in (-1.0, 1.0):
        for k in range(5):
            u = k / 4.0
            res = bmesh.ops.create_icosphere(bm_bm, subdivisions=2, radius=1.0)
            m = Matrix.Translation((side * lerp(0.5, 4.2, u), lerp(0.0, -2.5, u), lerp(0.5, 6.5, u))) @ Matrix.Diagonal((lerp(0.8, 2.6, u), lerp(0.8, 2.2, u), lerp(1.0, 2.8, u), 1.0))
            bmesh.ops.transform(bm_bm, matrix=m, verts=res["verts"])
    breath_mist = finalize_mesh_obj("GEO-BreathMist", bm_bm, mats["breath"], smooth=True)
    if hasattr(breath_mist, "visible_shadow"):
        breath_mist.visible_shadow = False
    breath_mist.hide_render = True

    # 8g. Low subtle mirror lake mist veils (Act 1 moving environmental layer!)
    lake_mists = []
    for i in range(2):
        bm_lm = bmesh.new()
        res = bmesh.ops.create_uvsphere(bm_lm, u_segments=16, v_segments=8, radius=1.0)
        bmesh.ops.transform(bm_lm, matrix=Matrix.Diagonal((18.0, 8.0, 0.35, 1.0)), verts=res["verts"])
        lm = finalize_mesh_obj(f"GEO-LakeMist_{i}", bm_lm, mats["lake_mist"], smooth=True)
        if hasattr(lm, "visible_shadow"):
            lm.visible_shadow = False
        lm.location = (-8.0 + i * 16.0, -18.0 + i * 24.0, 0.35)
        lake_mists.append(lm)

    # 8h. Single hero final petal drifting down onto the lake at C8 (90.2..92.1s)
    final_petal = bpy.data.objects.new("GEO-FinalPetal", petal_mesh)
    bpy.context.scene.collection.objects.link(final_petal)
    final_petal.color = (1.0, 1.0, 1.0, 1.0)
    final_petal.hide_render = True

    # 9. Controlled 4-Layer 2,020-Petal Floral Snowstorm (NumPy Dynamic Mesh Buffers — Zero Teleport!)
    # Layer 0: 120 Side-Framing Bokeh Petals (10.5..21.5m ahead along left/right frame margins -> ZERO C6b smear across Whale/Sanctuary!)
    n_l0 = 120
    snow_l0_obj, snow_l0_tpl = _build_dynamic_petal_mesh("GEO-Snow_L0_NearBokeh", n_l0, mats["snow_near"], mat_seed=mats["seed_glow"])
    snow_l0_cfg = {
        "u_x": np.array([rng.choice([-1.0, 1.0]) * rng.uniform(0.48, 0.98) for _ in range(n_l0)], dtype=np.float32),
        "u_y": np.array([rng.uniform(-0.85, 0.85) for _ in range(n_l0)], dtype=np.float32),
        "depth": np.array([rng.uniform(10.5, 21.5) for _ in range(n_l0)], dtype=np.float32),
        "ph": np.array([rng.uniform(0.0, 6.283) for _ in range(n_l0)], dtype=np.float32),
        "spd": np.array([rng.uniform(0.65, 1.15) for _ in range(n_l0)], dtype=np.float32),
        "sc": np.array([rng.uniform(0.38, 0.72) for _ in range(n_l0)], dtype=np.float32),
    }

    # Layer 1: 700 Guided Whale-Wake Ribbon Petals (organic river trailing & orbiting whale, detaching smoothly at 67s!)
    n_l1 = 700
    snow_l1_obj, snow_l1_tpl = _build_dynamic_petal_mesh("GEO-Snow_L1_WakeGuided", n_l1, mats["snow_wake"], mat_seed=mats["seed_glow"])
    snow_l1_cfg = {
        "lag": np.array([rng.uniform(0.15, 8.2) for _ in range(n_l1)], dtype=np.float32),
        "rad": np.array([rng.uniform(3.2, 16.5) for _ in range(n_l1)], dtype=np.float32),
        "ang": np.array([rng.uniform(0.0, 6.283) for _ in range(n_l1)], dtype=np.float32),
        "ph": np.array([rng.uniform(0.0, 6.283) for _ in range(n_l1)], dtype=np.float32),
        "spd": np.array([rng.uniform(0.8, 1.35) for _ in range(n_l1)], dtype=np.float32),
        "sc": np.array([rng.uniform(0.85, 1.85) for _ in range(n_l1)], dtype=np.float32),
        "t_launch": np.array([rng.uniform(35.0, 35.55) for _ in range(n_l1)], dtype=np.float32),
        "orig": np.array([[rng.uniform(-16.0, 30.0), rng.uniform(-50.0, 40.0), rng.uniform(0.6, 4.0)] for _ in range(n_l1)], dtype=np.float32),
        "hov": np.array([[rng.uniform(-18.0, 32.0), rng.uniform(-48.0, 42.0), rng.uniform(2.0, 14.0)] for _ in range(n_l1)], dtype=np.float32),
    }

    # Layer 2: 800 Midground Cathedral Blizzard Petals (shore/bridge launch -> 1s freeze -> smooth continuous rise->hang->snowfall!)
    n_l2 = 800
    snow_l2_obj, snow_l2_tpl = _build_dynamic_petal_mesh("GEO-Snow_L2_CathedralMid", n_l2, mats["snow_mid"], mat_seed=mats["seed_glow"])
    orig_l2 = np.empty((n_l2, 3), dtype=np.float32)
    hov_l2 = np.empty((n_l2, 3), dtype=np.float32)
    for i in range(n_l2):
        if i < 260:
            # Foreground & shore-to-lake corridor (dense dramatic freeze in C6a!)
            ox = rng.uniform(-12.0, 18.0)
            oy = rng.uniform(-52.5, -24.0)
            oz = rng.uniform(0.95, 1.35)
            hx = ox + rng.uniform(-0.6, 0.6)
            hy = oy + rng.uniform(-0.5, 0.8)
            hz = rng.uniform(1.5, 6.2)
        else:
            # Wide midground arches & lake volume (denser in central light cone, thinner toward outer abyss)
            ox = rng.gauss(4.0, 26.0)
            ox = clamp(ox, -58.0, 62.0)
            oy = rng.uniform(-42.0, 56.0)
            oz = rng.uniform(0.6, 2.8)
            hx = ox + rng.uniform(-1.2, 1.2)
            hy = oy + rng.uniform(-1.2, 1.2)
            hz = rng.uniform(2.2, 22.0)
        orig_l2[i] = (ox, oy, oz)
        hov_l2[i] = (hx, hy, hz)
    snow_l2_cfg = {
        "orig": orig_l2,
        "hov": hov_l2,
        "ph": (hov_l2[:, 0] * 0.07 + hov_l2[:, 1] * 0.05 + np.array([rng.uniform(-0.4, 0.4) for _ in range(n_l2)], dtype=np.float32)).astype(np.float32),
        "spd": np.array([rng.uniform(0.78, 1.38) for _ in range(n_l2)], dtype=np.float32),
        "rid": (np.arange(n_l2) % 3).astype(np.float32),
        "sc": np.array([rng.uniform(0.55, 1.15) if i < 260 else rng.uniform(0.95, 2.10) for i in range(n_l2)], dtype=np.float32),
        "t_launch": np.array([rng.uniform(35.0, 35.55) for _ in range(n_l2)], dtype=np.float32),
        "keep_c7c": np.array([rng.random() < 0.56 for _ in range(n_l2)], dtype=bool),
    }

    # Layer 3: 400 Far Mist Snow Sparks (soft low-contrast distant depth, zero TV static!)
    n_l3 = 400
    snow_l3_obj, snow_l3_tpl = _build_dynamic_petal_mesh("GEO-Snow_L3_FarMist", n_l3, mats["snow_far"])
    hov_l3 = np.array([[rng.uniform(-85.0, 88.0), rng.uniform(34.0, 118.0), rng.uniform(3.0, 58.0)] for _ in range(n_l3)], dtype=np.float32)
    snow_l3_cfg = {
        "hov": hov_l3,
        "ph": np.array([rng.uniform(0.0, 6.283) for _ in range(n_l3)], dtype=np.float32),
        "spd": np.array([rng.uniform(0.65, 1.15) for _ in range(n_l3)], dtype=np.float32),
        "sc": np.array([rng.uniform(1.5, 2.8) for _ in range(n_l3)], dtype=np.float32),
    }

    # 10. Dedicated C7b lunar-absorption peeling petals (96) + sparse delicate fissure snow (44)
    n_mp = 96
    c7b_peel_obj, c7b_peel_tpl = _build_dynamic_petal_mesh("GEO-C7b_MoonPeel", n_mp, mats["moon_petal"])
    c7b_peel_cfg = {
        "u_body": np.clip(np.linspace(0.02, 0.96, n_mp) + np.array([rng.uniform(-0.015, 0.015) for _ in range(n_mp)]), 0.02, 0.96).astype(np.float32),
        "off_z": np.array([rng.uniform(-1.6, 1.6) for _ in range(n_mp)], dtype=np.float32),
        "off_x": np.array([rng.uniform(-0.8, 0.8) for _ in range(n_mp)], dtype=np.float32),
        "ph": np.array([rng.uniform(0.0, 6.283) for _ in range(n_mp)], dtype=np.float32),
        "pull": np.array([rng.uniform(0.75, 1.35) for _ in range(n_mp)], dtype=np.float32),
        "sc": np.array([rng.uniform(0.85, 1.60) for _ in range(n_mp)], dtype=np.float32),
    }

    n_cs = 44
    c7b_snow_obj, c7b_snow_tpl = _build_dynamic_petal_mesh("GEO-C7b_RimSnow", n_cs, mats["moon_petal"])
    c7b_snow_cfg = {
        "sx": np.array([m_pos.x + rng.uniform(-24.0, 24.0) for _ in range(n_cs)], dtype=np.float32),
        "sy": np.array([rng.uniform(32.0, 56.0) for _ in range(n_cs)], dtype=np.float32),
        "sz": np.array([m_pos.z + rng.uniform(-14.0, 15.0) for _ in range(n_cs)], dtype=np.float32),
        "ph": np.array([rng.uniform(0.0, 6.283) for _ in range(n_cs)], dtype=np.float32),
        "spd": np.array([rng.uniform(0.7, 1.45) for _ in range(n_cs)], dtype=np.float32),
        "sc": np.array([rng.uniform(0.45, 1.05) for _ in range(n_cs)], dtype=np.float32),
    }

    return {
        "bridge": bridge, "sunken_city": sunken_city, "cavern_roof": cavern_roof,
        "cavern_walls": cavern_walls, "cavern_headlands": cavern_headlands, "cavern_stalactites": cavern_stalactites,
        "star_vault": star_vault, "starburst_hero": starburst_hero, "aurora_veil": aurora_veil,
        "moon": moon_obj, "moon_corona": moon_corona, "shaft": shaft, "p0_beam": p0_beam, "fissure": fissure_obj,
        "p0": p0_stem, "p0_petals": p0_petals, "hero_blooms": hero_blooms,
        "colony_buds": (colony_buds_obj, colony_bud_tpl, colony_pos, colony_sc, colony_yaw, colony_tbl),
        "colony_shed": (colony_shed_obj, colony_shed_tpl, colony_pos, colony_sc, colony_yaw, colony_tshed),
        "colony_crowns": (colony_crowns_obj, colony_tpl, colony_pos, colony_sc, colony_yaw, colony_tbl, colony_tshed),
        "bridge_crowns": (bridge_crowns_obj, bridge_tpl, bridge_pos, bridge_sc, bridge_yaw, bridge_tbl, bridge_tshed),
        "water_drop": water_drop, "ripples": ripples, "breach_rings": breach_rings,
        "spray_objs": spray_objs, "belly_drops": belly_drops, "breath_mist": breath_mist,
        "lake_mists": lake_mists, "final_petal": final_petal,
        "snow_l0": (snow_l0_obj, snow_l0_tpl, snow_l0_cfg),
        "snow_l1": (snow_l1_obj, snow_l1_tpl, snow_l1_cfg),
        "snow_l2": (snow_l2_obj, snow_l2_tpl, snow_l2_cfg),
        "snow_l3": (snow_l3_obj, snow_l3_tpl, snow_l3_cfg),
        "c7b_peel": (c7b_peel_obj, c7b_peel_tpl, c7b_peel_cfg),
        "c7b_snow": (c7b_snow_obj, c7b_snow_tpl, c7b_snow_cfg),
    }


def setup_lighting_and_world(spec: dict):
    """v7.1 'Darkness -> World Revealed by Whale -> Return to Darkness' 3-Tier Practical Lighting Rig!
    - Act 1 (C1-C4b): Deep true nocturnal darkness (~8-14% faint ruin silhouettes) + P0 spot + crisp Act 1 Whale Rim
    - Act 2 (C5a-C6d): Whale ignites with 3 synchronized lights (Near + Wide Cathedral Bounce + Shore Glow) revealing
      the hidden oblique sunken cathedral, watch-pier & karst cavern while deepest far void stays mysterious dark slate!
    - Act 3 (C7a-C8): Whale light recedes to 0W, sinking the revealed ruins gracefully back into quiet sleep."""
    scene = bpy.context.scene
    world = bpy.data.worlds.new("WORLD-ClayCavern_v7_1")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.006, 0.010, 0.018, 1.0)
        bg.inputs["Strength"].default_value = 0.15

    # 1. Ultra-restrained cold moonlight key (Act 1 ruins sit in deep mystery; whale carries the illumination!)
    key_d = bpy.data.lights.new("LGT-MoonKey", type="SUN")
    key_d.energy = 0.20
    key_d.color = (0.80, 0.88, 1.0)
    key_d.angle = math.radians(6.0)
    key = bpy.data.objects.new("LGT-MoonKey", key_d)
    scene.collection.objects.link(key)
    key.rotation_euler = (math.radians(36), math.radians(-20), math.radians(-24))

    # 2. Whisper-low projector-safe shadow floor (prevents RGB 0,0,0 crush without spoiling Act 1 darkness!)
    fill_d = bpy.data.lights.new("LGT-ClayFill", type="AREA")
    fill_d.energy = 340.0
    fill_d.size = 52.0
    fill_d.color = (0.58, 0.68, 0.84)
    fill = bpy.data.objects.new("LGT-ClayFill", fill_d)
    scene.collection.objects.link(fill)
    fill.location = (-28.0, -78.0, 32.0)
    fill.rotation_euler = (math.radians(68), 0.0, math.radians(-20))

    # 3. Localized pale silver moonlight spotlight illuminating ONLY P0 & water drop spot in C1 & C8!
    p0_pos = Vector(spec["world"]["p0_flower"]["pos"])
    p0l_d = bpy.data.lights.new("LGT-P0_MoonSpot", type="SPOT")
    p0l_d.energy = 520.0
    p0l_d.spot_size = math.radians(32.0)
    p0l_d.spot_blend = 0.96
    p0l_d.shadow_soft_size = 0.45
    p0l_d.color = (0.88, 0.94, 1.0)
    p0l = bpy.data.objects.new("LGT-P0_MoonSpot", p0l_d)
    scene.collection.objects.link(p0l)
    p0l.location = p0_pos + Vector((1.2, -1.6, 7.6))
    direction = (p0_pos - p0l.location).normalized()
    p0l.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    # 4. Act 1 dedicated Whale Back/Rim Light (carves razor-crisp silver silhouette edge out of true Act 1 darkness!)
    rim_d = bpy.data.lights.new("LGT-WhaleRim", type="AREA")
    rim_d.energy = 0.0
    rim_d.size = 14.0
    rim_d.color = (0.84, 0.92, 1.0)
    rim = bpy.data.objects.new("LGT-WhaleRim", rim_d)
    scene.collection.objects.link(rim)

    # 5a. Whale Tier-1 Near Practical Light (soft 9m radius -> illuminates environment cleanly without blowing out whale belly!)
    aw_d = bpy.data.lights.new("LGT-WhaleAwaken", type="POINT")
    aw_d.energy = 0.0
    aw_d.shadow_soft_size = 9.0
    aw_d.color = (0.86, 0.93, 1.0)
    aw = bpy.data.objects.new("LGT-WhaleAwaken", aw_d)
    scene.collection.objects.link(aw)

    # 5b. Whale Tier-2 Wide Cathedral Reveal Light (soft directional AREA travelling WITH whale to unveil hidden ruins!)
    cat_d = bpy.data.lights.new("LGT-WhaleCathedral", type="AREA")
    cat_d.energy = 0.0
    cat_d.size = 42.0
    cat_d.color = (0.82, 0.90, 1.0)
    cat_lgt = bpy.data.objects.new("LGT-WhaleCathedral", cat_d)
    scene.collection.objects.link(cat_lgt)

    # 5c. Whale Tier-3 Shore Bloom Wash (physically lights up the 450-flower meadow in C5b-C6a as whale light arrives!)
    shw_d = bpy.data.lights.new("LGT-WhaleShoreGlow", type="SPOT")
    shw_d.energy = 0.0
    shw_d.spot_size = math.radians(64.0)
    shw_d.spot_blend = 0.85
    shw_d.shadow_soft_size = 4.0
    shw_d.color = (0.88, 0.94, 1.0)
    shw_lgt = bpy.data.objects.new("LGT-WhaleShoreGlow", shw_d)
    scene.collection.objects.link(shw_lgt)

    # 5d. Dedicated Far Classical Sanctuary Key Light (positioned BEHIND viaduct at y=86m, tighter 28m area -> sharp Chiaroscuro across fluted columns & dome coffers!)
    sanc_d = bpy.data.lights.new("LGT-SanctuaryReveal", type="AREA")
    sanc_d.energy = 0.0
    sanc_d.size = 28.0
    sanc_d.color = (0.66, 0.80, 1.0)
    sanc_lgt = bpy.data.objects.new("LGT-SanctuaryReveal", sanc_d)
    scene.collection.objects.link(sanc_lgt)
    sanc_lgt.location = (-40.0, 94.0, 72.0)
    sanc_lgt.rotation_euler = (Vector((2.0, 178.0, 52.0)) - sanc_lgt.location).normalized().to_track_quat("-Z", "Y").to_euler()

    # 5e. High Starlight Rim Light carving the open Pantheon Oculus Crown against the Winter Milky Way!
    srim_d = bpy.data.lights.new("LGT-SanctuaryTopRim", type="AREA")
    srim_d.energy = 0.0
    srim_d.size = 78.0
    srim_d.color = (0.68, 0.84, 1.00)
    srim_lgt = bpy.data.objects.new("LGT-SanctuaryTopRim", srim_d)
    scene.collection.objects.link(srim_lgt)
    srim_lgt.location = (28.0, 238.0, 132.0)
    srim_lgt.rotation_euler = (Vector((2.0, 184.0, 62.0)) - srim_lgt.location).normalized().to_track_quat("-Z", "Y").to_euler()

    # 6. Dedicated subtle eye pinpoint catchlight (C4b & C6d)
    eye_d = bpy.data.lights.new("LGT-EyeCatchlight", type="POINT")
    eye_d.energy = 0.0
    eye_d.shadow_soft_size = 0.035
    eye_d.color = (0.95, 0.98, 1.0)
    eye_lgt = bpy.data.objects.new("LGT-EyeCatchlight", eye_d)
    scene.collection.objects.link(eye_lgt)

    # 7. Subterranean Cavern Vault Rim Bounce + Far Abyss Horizon Backlight (Act 1-3 cliff & stalactite separation!)
    cav_d = bpy.data.lights.new("LGT-CavernVaultBounce", type="AREA")
    cav_d.energy = 95000.0
    cav_d.size = 118.0
    cav_d.color = (0.42, 0.56, 0.84)
    cav_lgt = bpy.data.objects.new("LGT-CavernVaultBounce", cav_d)
    scene.collection.objects.link(cav_lgt)
    cav_lgt.location = (24.0, 22.0, 122.0)
    cav_lgt.rotation_euler = (Vector((0.0, 68.0, 26.0)) - cav_lgt.location).normalized().to_track_quat("-Z", "Y").to_euler()

    cdeep_d = bpy.data.lights.new("LGT-CavernDeepFill", type="AREA")
    cdeep_d.energy = 36000.0
    cdeep_d.size = 135.0
    cdeep_d.color = (0.36, 0.50, 0.78)
    cdeep_lgt = bpy.data.objects.new("LGT-CavernDeepFill", cdeep_d)
    scene.collection.objects.link(cdeep_lgt)
    cdeep_lgt.location = (0.0, 165.0, 28.0)
    cdeep_lgt.rotation_euler = (Vector((0.0, -10.0, 32.0)) - cdeep_lgt.location).normalized().to_track_quat("-Z", "Y").to_euler()

    # ZERO fake lamp slabs or orbs reflecting in the mirror lake!
    for l_obj in (fill, p0l, rim, aw, cat_lgt, shw_lgt, sanc_lgt, srim_lgt, cav_lgt, cdeep_lgt):
        if hasattr(l_obj, "visible_camera"):
            l_obj.visible_camera = False
        if hasattr(l_obj, "visible_glossy"):
            l_obj.visible_glossy = False
    if hasattr(eye_lgt, "visible_camera"):
        eye_lgt.visible_camera = False

    return {
        "world_bg": bg, "moon_key": key, "clay_fill": fill, "p0_spot": p0l,
        "whale_rim": rim, "awaken_light": aw, "cathedral_light": cat_lgt,
        "shore_light": shw_lgt, "sanctuary_light": sanc_lgt, "sanctuary_rim": srim_lgt,
        "eye_catchlight": eye_lgt, "cavern_bounce": cav_lgt, "cavern_deep": cdeep_lgt,
    }


def setup_render_engine(spec: dict, quality: str = "cycles"):
    scene = bpy.context.scene
    scene.render.fps = spec["fps"]
    scene.render.resolution_x, scene.render.resolution_y = spec["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = spec["shutter"]
    if hasattr(scene.render, "motion_blur_position"):
        scene.render.motion_blur_position = "CENTER"
    scene.render.use_persistent_data = True

    if hasattr(scene.render.image_settings, "media_type"):
        scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            scene.view_settings.view_transform = "AgX"
            scene.view_settings.look = "AgX - Medium Contrast"
        except Exception:
            scene.view_settings.view_transform = "Filmic"
    scene.view_settings.exposure = 0.20

    if quality == "cycles":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 24
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.03
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 6
        scene.cycles.diffuse_bounces = 3
        scene.cycles.glossy_bounces = 3
        scene.cycles.transparent_max_bounces = 10
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            for dev_type in ("OPTIX", "METAL", "CUDA", "HIP"):
                try:
                    prefs.compute_device_type = dev_type
                    prefs.get_devices()
                    if any(d.type == dev_type for d in prefs.devices):
                        for d in prefs.devices:
                            d.use = (d.type == dev_type)
                        scene.cycles.device = "GPU"
                        if dev_type == "OPTIX":
                            scene.cycles.denoiser = "OPTIX"
                        break
                except Exception:
                    continue
        except Exception:
            scene.cycles.device = "CPU"
    else:
        try:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        except (TypeError, ValueError):
            scene.render.engine = "BLENDER_EEVEE"

    setup_compositor(scene)


def setup_compositor(scene):
    """Blender 5.3.0 / 4.x Fog Glow Compositor halo tuned cleanly above diffuse stonework (Threshold=1.12)."""
    try:
        if hasattr(scene, "use_nodes"):
            scene.use_nodes = True
        if hasattr(scene, "compositing_node_group"):
            old_ng = scene.compositing_node_group
            ng = bpy.data.node_groups.new("COMP-Kousetsuka_Bloom", "CompositorNodeTree")
            ng.interface.new_socket(name="Image", in_out="INPUT", socket_type="NodeSocketColor")
            ng.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
            rl = ng.nodes.new("CompositorNodeRLayers")
            gl = ng.nodes.new("CompositorNodeGlare")
            co = ng.nodes.new("NodeGroupOutput")
            gl.inputs["Type"].default_value = "Fog Glow"
            gl.inputs["Quality"].default_value = "High"
            gl.inputs["Threshold"].default_value = 1.12
            gl.inputs["Smoothness"].default_value = 0.16
            gl.inputs["Strength"].default_value = 0.42
            gl.inputs["Size"].default_value = 0.62
            ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
            ng.links.new(gl.outputs["Image"], co.inputs["Image"])
            scene.compositing_node_group = ng
            if old_ng is not None and old_ng.users == 0:
                bpy.data.node_groups.remove(old_ng)
    except Exception as exc:
        print(f"WARN: Compositor setup skipped: {exc}")


# ---------------------------------------------------------------------------
# Unbroken C1-Continuous Whale Spline & Cinematographic Camera Evaluator
# ---------------------------------------------------------------------------

def _hermite_vec_and_deriv(kfs: list[dict], t: float) -> tuple[Vector, Vector]:
    n = len(kfs)
    if t <= kfs[0]["t"]:
        p0, p1 = Vector(kfs[0]["pos"]), Vector(kfs[1]["pos"])
        return p0, (p1 - p0) / max(1e-6, kfs[1]["t"] - kfs[0]["t"])
    if t >= kfs[-1]["t"]:
        p0, p1 = Vector(kfs[-2]["pos"]), Vector(kfs[-1]["pos"])
        return p1, (p1 - p0) / max(1e-6, kfs[-1]["t"] - kfs[-2]["t"])

    idx = 0
    for i in range(n - 1):
        if kfs[i]["t"] <= t <= kfs[i + 1]["t"]:
            idx = i
            break

    def tangent(k: int) -> Vector:
        if k <= 0:
            return (Vector(kfs[1]["pos"]) - Vector(kfs[0]["pos"])) / max(1e-6, kfs[1]["t"] - kfs[0]["t"])
        if k >= n - 1:
            return (Vector(kfs[-1]["pos"]) - Vector(kfs[-2]["pos"])) / max(1e-6, kfs[-1]["t"] - kfs[-2]["t"])
        return (Vector(kfs[k + 1]["pos"]) - Vector(kfs[k - 1]["pos"])) / max(1e-6, kfs[k + 1]["t"] - kfs[k - 1]["t"])

    t0, t1 = kfs[idx]["t"], kfs[idx + 1]["t"]
    h = max(1e-6, t1 - t0)
    u = clamp((t - t0) / h, 0.0, 1.0)
    u2, u3 = u * u, u * u * u
    p0, p1 = Vector(kfs[idx]["pos"]), Vector(kfs[idx + 1]["pos"])
    m0, m1 = tangent(idx) * h, tangent(idx + 1) * h

    pos = (2*u3 - 3*u2 + 1)*p0 + (u3 - 2*u2 + u)*m0 + (-2*u3 + 3*u2)*p1 + (u3 - u2)*m1
    vel = ((6*u2 - 6*u)*p0 + (3*u2 - 4*u + 1)*m0 + (-6*u2 + 6*u)*p1 + (3*u2 - 2*u)*m1) / h
    return pos, vel


def _hermite_scalar_and_deriv(kfs: list[dict], key: str, t: float, default: float = 0.0) -> tuple[float, float]:
    n = len(kfs)
    if t <= kfs[0]["t"]:
        return kfs[0].get(key, default), 0.0
    if t >= kfs[-1]["t"]:
        return kfs[-1].get(key, default), 0.0
    idx = 0
    for i in range(n - 1):
        if kfs[i]["t"] <= t <= kfs[i + 1]["t"]:
            idx = i
            break

    def slp(k: int) -> float:
        if k <= 0:
            return (kfs[1].get(key, default) - kfs[0].get(key, default)) / max(1e-6, kfs[1]["t"] - kfs[0]["t"])
        if k >= n - 1:
            return (kfs[-1].get(key, default) - kfs[-2].get(key, default)) / max(1e-6, kfs[-1]["t"] - kfs[-2]["t"])
        return (kfs[k + 1].get(key, default) - kfs[k - 1].get(key, default)) / max(1e-6, kfs[k + 1]["t"] - kfs[k - 1]["t"])

    t0, t1 = kfs[idx]["t"], kfs[idx + 1]["t"]
    h = max(1e-6, t1 - t0)
    u = clamp((t - t0) / h, 0.0, 1.0)
    u2, u3 = u * u, u * u * u
    v0, v1 = kfs[idx].get(key, default), kfs[idx + 1].get(key, default)
    m0, m1 = slp(idx) * h, slp(idx + 1) * h
    val = (2*u3 - 3*u2 + 1)*v0 + (u3 - 2*u2 + u)*m0 + (-2*u3 + 3*u2)*v1 + (u3 - u2)*m1
    dval = ((6*u2 - 6*u)*v0 + (3*u2 - 4*u + 1)*m0 + (-6*u2 + 6*u)*v1 + (3*u2 - 2*u)*m1) / h
    return val, dval


def eval_whale_state(spec: dict, t: float) -> dict:
    if t >= 75.0:
        # C7b: Graceful upward & depth-receding ascension straight INTO the sculpted full moon's heart!
        u_g = clamp((t - 75.0) / 6.8, 0.0, 1.0)
        e_g = 1.0 - (1.0 - u_g) ** 1.55
        p_start = Vector((35.5, 24.0, 121.0))
        p_end = Vector((43.5, 72.0, 131.6))
        pos = p_start.lerp(p_end, e_g) + Vector((0.0, 0.0, 1.4 * math.sin(e_g * math.pi)))
        e_g2 = 1.0 - (1.0 - clamp((t + 0.06 - 75.0) / 6.8, 0.0, 1.0)) ** 1.55
        pos2 = p_start.lerp(p_end, e_g2) + Vector((0.0, 0.0, 1.4 * math.sin(e_g2 * math.pi)))
        fwd = (pos2 - pos) if (pos2 - pos).length > 1e-4 else (p_end - p_start)
        fwd.normalize()
        roll = 6.283 + lerp(-0.22, 0.0, e_g)
        dissolve = smoothstep(76.8, 81.6, t)
        glow = 1.0 if t < 82.0 else 0.0
        return {"pos": pos, "fwd": fwd, "roll": roll, "roll_rate": 0.0, "yaw_rate": 0.0, "glow": glow, "ignite": 1.0, "dissolve": dissolve}

    # ONE SINGLE UNBROKEN C1 SPLINE across C2..C7a (ZERO 31m teleport at t=25.0!)
    # Apply subtle propulsion-velocity coupling (+0.11s forward phase swell on each 5.2s tail downstroke)
    # and tender 0.6x slow-motion time dilation during C6d's affectionate glance (62.5..65.5s)!
    t_eff = t
    if 60.5 <= t <= 67.5:
        u_sl = (t - 60.5) / 7.0
        t_eff = t - 0.32 * math.sin(u_sl * math.pi) * smoothstep(0.0, 0.25, u_sl) * smoothstep(1.0, 0.75, u_sl)

    kfs = [k for k in spec["whale"]["keyframes"] if k["t"] <= 75.5]
    pos, vel = _hermite_vec_and_deriv(kfs, t_eff)
    _, vel_dt = _hermite_vec_and_deriv(kfs, min(75.0, t_eff + 0.08))
    fwd = vel.normalized() if vel.length > 1e-4 else Vector((0.0, 1.0, 0.0))
    fwd2 = vel_dt.normalized() if vel_dt.length > 1e-4 else fwd
    yaw_rate = (math.atan2(fwd2.y, fwd2.x) - math.atan2(fwd.y, fwd.x)) / 0.08
    # Wrap yaw_rate cleanly
    if yaw_rate > math.pi / 0.08:
        yaw_rate -= 2.0 * math.pi / 0.08
    elif yaw_rate < -math.pi / 0.08:
        yaw_rate += 2.0 * math.pi / 0.08

    roll, roll_rate = _hermite_scalar_and_deriv(kfs, "roll", t_eff, 0.0)
    idx = 0
    for i in range(len(kfs) - 1):
        if kfs[i]["t"] <= t <= kfs[i + 1]["t"]:
            idx = i
            break
    k1, k2 = kfs[idx], kfs[min(len(kfs) - 1, idx + 1)]
    u = clamp((t - k1["t"]) / max(1e-6, k2["t"] - k1["t"]), 0.0, 1.0)
    return {
        "pos": pos,
        "fwd": fwd,
        "roll": roll,
        "roll_rate": roll_rate,
        "yaw_rate": yaw_rate,
        "glow": lerp(k1.get("glow", 0.0), k2.get("glow", 0.0), u),
        "ignite": lerp(k1.get("ignite", k1.get("glow", 0.0)), k2.get("ignite", k2.get("glow", 0.0)), u),
        "dissolve": lerp(k1.get("dissolve", 0.0), k2.get("dissolve", 0.0), u),
    }


def shot_at_time(spec: dict, t: float) -> dict:
    for sh in spec["shots"]:
        if sh["start"] <= t < sh["end"]:
            return sh
    return spec["shots"][-1]


def eval_camera(spec: dict, t: float) -> tuple[dict, Vector, Vector]:
    sh = shot_at_time(spec, t)
    dur = max(1e-6, sh["end"] - sh["start"])
    local = t - sh["start"]
    hi, ho = sh.get("hold_in", 0.5), sh.get("hold_out", 0.5)
    move_dur = max(1e-6, dur - hi - ho)
    raw = clamp((local - hi) / move_dur, 0.0, 1.0)
    u = ease_cubic(raw)

    mode = sh.get("pos_mode")
    if mode == "c6a_freeze_tilt":
        raw_r = clamp((local - 1.8) / max(1e-6, dur - 2.6), 0.0, 1.0)
        u = 1.0 - (1.0 - smoothstep(0.0, 1.0, raw_r)) ** 1.35
        pos = lerp_vec(sh["pos0"], sh["pos1"], u)
        look = lerp_vec(sh["look0"], sh["look1"], u)
    elif mode == "c6c_orbit":
        oc = Vector(sh["orbit_center"])
        deg = lerp(sh["orbit_deg0"], sh["orbit_deg1"], u)
        rad = math.radians(deg)
        pos = Vector((oc.x + sh["orbit_rx"] * math.cos(rad), oc.y + sh["orbit_ry"] * math.sin(rad), oc.z))
        look = lerp_vec(sh["look0"], sh["look1"], u)
    elif mode == "c6d_train_pan":
        # Fixed aerial vantage "train-watching" fluid-head pan tracking the whale with tender 0.35s human inertia lag!
        pos = Vector(sh["pos0"])
        ws_lag = eval_whale_state(spec, clamp(t - 0.32, 60.0, 69.0))
        # Blend whale tracking softly into final upward send-off vector
        look = ws_lag["pos"] + Vector((1.5, 0.0, -0.5))
        look = look.lerp(Vector(sh["look1"]), smoothstep(66.5, 69.0, t) * 0.35)
    else:
        pos = lerp_vec(sh["pos0"], sh["pos1"], u)
        look = lerp_vec(sh["look0"], sh["look1"], u)

    # Subtle human breathing handheld feel ONLY on pure adventurer look-up POV shots (C4a & C7a; rulebook §3!)
    if sh["rig"] == "pov_tilt_up":
        breath_z = 0.022 * math.sin(t * 1.45) + 0.008 * math.sin(t * 3.8)
        breath_x = 0.015 * math.cos(t * 1.10)
        pos = pos + Vector((breath_x, 0.0, breath_z))
    return sh, pos, look


# ---------------------------------------------------------------------------
# Master Time-State Evaluator (Chiaroscuro + Shedding + 4-Layer Snow + FX)
# ---------------------------------------------------------------------------

def apply_state_at_time(handles: dict, spec: dict, t: float):
    sh, cam_pos, cam_look = eval_camera(spec, t)
    cam = handles["cam"]
    target = handles["cam_target"]
    cam.data.lens = sh["focal_mm"]
    cam.location = cam_pos
    target.location = cam_look

    # Whale transform + NumPy stroke-and-glide deformation + shader ignition/dissolve
    ws = eval_whale_state(spec, t)
    whale = handles["whale"]
    whale.location = ws["pos"]
    q_align = ws["fwd"].to_track_quat("Y", "Z")
    q_roll = Euler((0.0, ws["roll"], 0.0), "XYZ").to_quaternion()
    whale.rotation_mode = "QUATERNION"
    whale.rotation_quaternion = q_align @ q_roll

    # Negative glance in C6d bends head softly TOWARD +X_local (the viewer's shore side!) for tender eye contact!
    glance_deg = -16.0 * math.sin(smoothstep(62.2, 66.2, t) * math.pi) if 60.0 <= t <= 69.0 else 0.0
    deform_whale_sway(
        whale, handles["whale_base"], t,
        glance_deg=glance_deg, yaw_rate=ws["yaw_rate"], roll_rate=ws["roll_rate"]
    )

    # CRITICAL FIX: strictly t < 6.0 hides whale during ALL of C1 (zero 5.8s leak!)
    whale.hide_render = (t < 6.0 or t >= 82.0)

    # Real Optical Depth of Field per shot (dynamically tracks whale distance when whale is primary!)
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = sh.get("fstop", 4.0)
    if sh["id"] in ("C2", "C3", "C4a", "C4b", "C5a", "C6b", "C6d") and not whale.hide_render:
        cam.data.dof.focus_distance = max(2.5, (ws["pos"] - cam_pos).length)
    else:
        cam.data.dof.focus_distance = sh.get("focus_dist", 20.0)

    mat_w = handles["mat_whale"]
    mat_w.node_tree.nodes["VAL_GLOW"].outputs[0].default_value = ws["glow"]
    mat_w.node_tree.nodes["VAL_IGNITE"].outputs[0].default_value = ws["ignite"]
    mat_w.node_tree.nodes["VAL_DISSOLVE"].outputs[0].default_value = ws["dissolve"]
    if "VAL_WHALE_TIME" in mat_w.node_tree.nodes:
        mat_w.node_tree.nodes["VAL_WHALE_TIME"].outputs[0].default_value = t

    # Sync carved anatomical almond eyes with exact whale socket displacement & glance turn!
    eye_alpha = smoothstep(0.92, 0.74, ws["dissolve"])
    handles["mat_eye"].node_tree.nodes["VAL_EYE_ALPHA"].outputs[0].default_value = eye_alpha
    glance_rad = math.radians(glance_deg)
    eye_r_world = ws["pos"]
    for eye_obj, base_loc in handles["whale_eyes"]:
        eye_obj.hide_render = whale.hide_render or (eye_alpha <= 0.02)
        loc_def = eval_whale_local_point(
            base_loc, t,
            glance_deg=glance_deg, yaw_rate=ws["yaw_rate"], roll_rate=ws["roll_rate"],
        )
        eye_obj.location = loc_def
        hw_e = clamp((base_loc.y - 2.0) / 8.5, 0.0, 1.0)
        hw_e = hw_e * hw_e * (3.0 - 2.0 * hw_e)
        eye_obj.rotation_euler = (0.0, 0.0, glance_rad * hw_e)
        if eye_obj.name.endswith("_R"):
            eye_r_world = ws["pos"] + (whale.rotation_quaternion @ loc_def)

    # v7.1 Dramatic 'Darkness -> Whale Unveils Hidden Ancient Cathedral -> Return to Darkness' Lighting!
    lgts = handles["lights"]
    in_c7b = (75.0 <= t < 83.0)
    act2_bright = smoothstep(25.8, 29.8, t) * smoothstep(81.5, 72.0, t)
    # Keep far abyss dark so white whale & snow ALWAYS gleam like jewels; ruins wake up via Whale Practical Lights!
    if lgts["world_bg"] is not None:
        lgts["world_bg"].inputs["Color"].default_value = (
            lerp(0.005, 0.013, act2_bright),
            lerp(0.008, 0.021, act2_bright),
            lerp(0.015, 0.036, act2_bright),
            1.0,
        )
        lgts["world_bg"].inputs["Strength"].default_value = lerp(0.14, 0.26, act2_bright)
    # Act 1 ruins sit in deep dark mystery (0.18 SUN / 320W fill); C7c gently settles from 0.28 / 540W toward C8 stillness!
    sun_e = lerp(0.18, 0.42, act2_bright) if t < 75.0 else lerp(0.42, 0.28, smoothstep(75.0, 84.0, t)) * smoothstep(89.5, 86.5, t) + 0.22 * smoothstep(86.5, 89.5, t)
    fill_e = lerp(320.0, 820.0, act2_bright) if t < 75.0 else lerp(820.0, 540.0, smoothstep(75.0, 84.0, t)) * smoothstep(89.5, 86.5, t) + 380.0 * smoothstep(86.5, 89.5, t)
    lgts["moon_key"].data.energy = sun_e
    lgts["clay_fill"].data.energy = fill_e

    # Localized P0 Moonlight Spot & Beam (shines in C1 & C8!)
    p0_light_on = (t < 6.0) or (t >= 89.0)
    lgts["p0_spot"].data.energy = 520.0 if p0_light_on else 0.0
    handles["p0_beam"].hide_render = not p0_light_on
    handles["shaft"].hide_render = in_c7b or (t < 6.0) or (t >= 89.0)
    handles["fissure"].hide_render = not in_c7b
    handles["moon"].hide_render = (18.0 <= t < 25.0)
    if "moon_corona" in handles:
        handles["moon_corona"].hide_render = handles["moon"].hide_render
    if not handles["moon"].hide_render:
        to_cam_m = (cam_pos - handles["moon"].location)
        if to_cam_m.length > 1e-4:
            handles["moon"].rotation_mode = "QUATERNION"
            handles["moon"].rotation_quaternion = to_cam_m.normalized().to_track_quat("-Y", "Z")

    # Act 1 Whale Rim Light (C2-C4b: razor-sharp silver edge tracing the dark whale out of pitch darkness!)
    rim = lgts["whale_rim"]
    if 6.0 <= t < 25.6:
        rim_pos = ws["pos"] + Vector((14.0, 12.0, 18.0))
        rim.location = rim_pos
        rim.rotation_euler = (ws["pos"] - rim_pos).normalized().to_track_quat("-Z", "Y").to_euler()
        rim.data.energy = 36000.0 * smoothstep(6.0, 7.5, t) * smoothstep(25.6, 24.5, t)
    else:
        rim.data.energy = 0.0

    # 3-Tier Whale Practical Light Rig calibrated to non-clipping 4-value sculptural silver chiaroscuro!
    # Ruins jump dramatically from Act 1 dark ~10% silhouette to Act 2 sculpted ~55-68% silver stone,
    # while ALWAYS staying below the 95% glowing white whale & preserving sculpted 3D pearl shading!
    aw = lgts["awaken_light"]
    cat_l = lgts["cathedral_light"]
    shw_l = lgts["shore_light"]
    if 25.5 <= t < 82.0:
        pulse = 1.0 + 0.14 * math.sin(2.0 * math.pi * (t / 5.2))
        c6d_boost = 1.0 + 0.14 * smoothstep(60.0, 63.5, t) * smoothstep(68.5, 65.5, t)
        aw.location = ws["pos"] + Vector((0.0, 4.0, -14.0))
        aw.data.color = (0.76, 0.85, 1.0)
        # Position Cathedral light cleanly high/side-raking over y=40m Aqueduct (zero flat camera-side flash on whale!)
        cat_pos = Vector((ws["pos"].x * 0.45 - 18.0, 14.0, 54.0))
        cat_tgt = Vector((ws["pos"].x * 0.25, 42.0, 10.0))
        cat_l.location = cat_pos
        cat_l.rotation_euler = (cat_tgt - cat_pos).normalized().to_track_quat("-Z", "Y").to_euler()
        cat_l.data.color = (0.74, 0.84, 1.0)

        if t < 30.5:
            ig_e = smoothstep(26.2, 29.6, t)
            burst = math.sin(smoothstep(26.0, 30.5, t) * math.pi)
            aw.data.energy = 38000.0 * burst + 22000.0 * ig_e
            cat_l.data.energy = 82000.0 * ig_e
        elif t < 69.0:
            aw.data.energy = 22000.0 * pulse * c6d_boost
            cat_l.data.energy = 72000.0 * pulse * c6d_boost
        elif t < 75.0:
            fade_u = smoothstep(69.0, 75.0, t)
            aw.data.energy = lerp(22000.0, 12000.0, fade_u)
            cat_l.data.energy = lerp(72000.0, 22000.0, fade_u)
        else:
            # C7b: whale softly silver-rims the organic 3D ceiling fissure, then fades gracefully!
            aw.location = ws["pos"] + Vector((0.0, -12.0, -8.0))
            aw.data.energy = 16000.0 * (1.0 - ws["dissolve"]) ** 1.4
            cat_l.data.energy = 0.0

        # Tier-3 Shore Bloom Wash softly illuminating the 450 blooming flowers during C5b & C6a takeoff (backlit SSS + stamens!)
        if 29.6 <= t <= 38.5:
            shw_pos = ws["pos"] + Vector((-6.0, -4.0, 5.0))
            shw_tgt = Vector((4.0, -52.5, 1.0))
            shw_l.location = shw_pos
            shw_l.rotation_euler = (shw_tgt - shw_pos).normalized().to_track_quat("-Z", "Y").to_euler()
            shw_l.data.energy = 125000.0 * smoothstep(29.6, 31.2, t) * smoothstep(38.5, 36.2, t)
        else:
            shw_l.data.energy = 0.0
    else:
        aw.data.energy = 0.0
        cat_l.data.energy = 0.0
        shw_l.data.energy = 0.0

    # Drive gentle living micro-ripple phase on the mirror lake
    if "mat_water" in handles:
        handles["mat_water"].node_tree.nodes["VAL_WATER_TIME"].outputs[0].default_value = t

    # v8.1 Museum-Scale Sanctuary + Clean Organic Sky Rift + Poetic Cave Return (C7c -> C8):
    # - Act 2 (30..75s): Whale ignites Sanctuary & silver-rims the diagonal Sky Rift open to Winter Galaxy.
    # - C7c (83..89s): Sanctuary holds quiet 30% twilight afterglow & mirror reflections below the closing cavern roof while snow & dying stars dim smoothly into C8 stillness!
    city_rev = smoothstep(30.2, 39.2, t) * (smoothstep(79.5, 69.5, t) + 0.30 * smoothstep(79.0, 82.8, t) * smoothstep(88.8, 84.5, t))
    handles["mat_sunken_city"].node_tree.nodes["VAL_CITY_REVEAL"].outputs[0].default_value = city_rev
    handles["sunken_city"].hide_render = in_c7b or (city_rev <= 0.01)
    roof_rev = lerp(0.24, 1.0, smoothstep(26.5, 36.0, t) * (smoothstep(82.0, 74.0, t) + 0.52 * smoothstep(74.5, 81.0, t) * smoothstep(88.8, 84.5, t)))
    if "mat_cavern_roof" in handles:
        handles["mat_cavern_roof"].node_tree.nodes["VAL_ROOF_REVEAL"].outputs[0].default_value = roof_rev
    if "mat_pillar" in handles:
        handles["mat_pillar"].node_tree.nodes["VAL_ROOF_REVEAL"].outputs[0].default_value = roof_rev
    if "mat_fissure" in handles:
        handles["mat_fissure"].node_tree.nodes["VAL_ROOF_REVEAL"].outputs[0].default_value = lerp(0.28, 0.72, 1.0 - ws["dissolve"])
    # Cavern interior (walls, headlands, stalactites, roof canopy) ALWAYS encloses Act 1-3 (only hide broad canopy in C7b where C7b fissure dome swaps in!)
    if "cavern_roof" in handles:
        handles["cavern_roof"].hide_render = in_c7b
    if "cavern_walls" in handles:
        handles["cavern_walls"].hide_render = in_c7b
    if "cavern_stalactites" in handles:
        handles["cavern_stalactites"].hide_render = in_c7b
    if "cavern_headlands" in handles:
        handles["cavern_headlands"].hide_render = in_c7b
    if "cavern_bounce" in lgts:
        lgts["cavern_bounce"].data.energy = lerp(95000.0, 145000.0, act2_bright) if not in_c7b else 0.0
    if "cavern_deep" in lgts:
        lgts["cavern_deep"].data.energy = lerp(36000.0, 68000.0, act2_bright) if not in_c7b else 0.0
    sanc_l = lgts["sanctuary_light"]
    srim_l = lgts["sanctuary_rim"]
    if city_rev > 0.01 and not in_c7b:
        # Positioned at y=94m BEHIND Aqueduct (zero spill on foreground bridge!), carving Museum-scale Sanctuary!
        wx_u = clamp((ws["pos"].x + 30.0) / 80.0, 0.0, 1.0)
        wz_u = clamp((ws["pos"].z - 12.0) / 55.0, 0.0, 1.0)
        sanc_pos = Vector((lerp(-48.0, -14.0, wx_u), 94.0, lerp(58.0, 92.0, wz_u)))
        sanc_l.location = sanc_pos
        sanc_l.rotation_euler = (Vector((2.0, 178.0, 52.0)) - sanc_pos).normalized().to_track_quat("-Z", "Y").to_euler()
        sanc_l.data.energy = 215000.0 * city_rev
        srim_l.data.energy = 98000.0 * city_rev
    else:
        sanc_l.data.energy = 0.0
        srim_l.data.energy = 0.0

    # v8.1 4-Tier Winter Milky Way Panorama inside Sky Rift -> graceful lingering twilight embers at C7c -> dark cave C8!
    aurora_mode = spec.get("aurora_mode", "sky_veil")
    star_wake = smoothstep(28.5, 37.5, t) * (smoothstep(82.0, 70.5, t) + 0.42 * smoothstep(79.5, 83.0, t) * smoothstep(88.8, 84.5, t))
    if aurora_mode == "canon_starry_opal":
        aurora_w = star_wake
    elif aurora_mode == "starry_aurora_whale":
        aurora_w = 0.0
    else:
        aurora_w = smoothstep(29.5, 40.0, t) * smoothstep(81.5, 69.5, t)
    if "mat_star_vault" in handles:
        c7b_stars = 0.28 if in_c7b else star_wake
        handles["mat_star_vault"].node_tree.nodes["VAL_STAR_WAKE"].outputs[0].default_value = c7b_stars
        if "VAL_STAR_TIME" in handles["mat_star_vault"].node_tree.nodes:
            handles["mat_star_vault"].node_tree.nodes["VAL_STAR_TIME"].outputs[0].default_value = t
        handles["star_vault"].hide_render = (c7b_stars <= 0.01)
    if "mat_starburst_hero" in handles:
        handles["mat_starburst_hero"].node_tree.nodes["VAL_STAR_WAKE"].outputs[0].default_value = star_wake
        handles["mat_starburst_hero"].node_tree.nodes["VAL_STAR_TIME"].outputs[0].default_value = t
        handles["starburst_hero"].hide_render = in_c7b or (star_wake <= 0.01)
    if "mat_aurora_veil" in handles:
        handles["mat_aurora_veil"].node_tree.nodes["VAL_AURORA"].outputs[0].default_value = aurora_w
        handles["mat_aurora_veil"].node_tree.nodes["VAL_AURORA_TIME"].outputs[0].default_value = t
        handles["aurora_veil"].hide_render = in_c7b or (aurora_w <= 0.01)
    for mp_k in ("mat_snow_near", "mat_snow_wake", "mat_snow_mid"):
        if mp_k in handles and "VAL_PETAL_TIME" in handles[mp_k].node_tree.nodes:
            handles[mp_k].node_tree.nodes["VAL_PETAL_TIME"].outputs[0].default_value = t
    # Keep high citadel rim crisp starlight-silver in starry/canon_starry_opal modes
    if aurora_mode in ("starry_aurora_whale", "canon_starry_opal"):
        srim_l.data.color = (0.68, 0.84, 1.00)
    else:
        srim_l.data.color = (0.90, 0.68, 0.96)

    # Dedicated pinpoint specular catchlight right beside the camera-eye reflection vector in C4b & C6d
    ec = lgts["eye_catchlight"]
    if 21.5 <= t < 25.0:
        ec.location = eye_r_world + (cam_pos - eye_r_world).normalized() * 3.2 + Vector((0.45, -0.30, 0.85))
        ec.data.energy = 95.0
    elif 61.5 <= t <= 66.5:
        ec.location = eye_r_world + (cam_pos - eye_r_world).normalized() * 3.4 + Vector((0.45, -0.35, 0.85))
        ec.data.energy = 110.0
    else:
        ec.data.energy = 0.0

    # P0 subtle dew tremble at C1 (2.4s) & gentle 8 deg nod toward camera showcasing 5 veined petals & golden heart!
    p0_trem = math.radians(3.2) * math.sin((t - 2.4) * 18.0) * math.exp(-max(0.0, t - 2.4) * 2.4) if 2.4 <= t <= 4.2 else 0.0
    handles["p0"].rotation_euler = (math.radians(8.0) + math.radians(1.2) * math.sin(t * 1.2) + p0_trem, 0.0, 0.0)

    # 140 Hero Interactive Flowers: clean dormant buds -> swell & open heart -> ACTUAL PETAL DETACHMENT revealing bare calyxes!
    iu_g, idn_g, isw_g = eval_snow_integrals(max(0.0, t - 36.8))
    for stem_o, bud_cup, heart_o, petals_5, t_bloom, sc, yaw, droop_deg in handles["hero_blooms"]:
        dt_b = t - t_bloom
        ant = smoothstep(-0.26, 0.0, dt_b)
        raw = clamp(dt_b / 0.90, 0.0, 1.0)
        sway = math.radians(1.5) * math.sin(t * 1.45 + yaw)
        cur_droop = math.radians(lerp(droop_deg, 0.0, smoothstep(-0.20, 0.65, dt_b)))
        stem_o.rotation_euler = (cur_droop + sway, sway * 0.5, yaw)

        bud_hide = (raw >= 0.42)
        bud_cup.hide_render = bud_hide
        if not bud_hide:
            swell = 1.0 + 0.16 * ant * (1.0 - smoothstep(0.05, 0.38, raw))
            shrink = smoothstep(0.42, 0.12, raw)
            bud_cup.scale = (swell * shrink, swell * shrink, swell * shrink)

        heart_open = smoothstep(0.16, 0.72, raw)
        heart_o.hide_render = (heart_open <= 0.02)
        if not heart_o.hide_render:
            heart_o.scale = (heart_open, heart_open, heart_open)

        # World position of the exact stem calyx tip hinge
        stem_rot_m = stem_o.rotation_euler.to_matrix()
        hinge_world = stem_o.location + (stem_rot_m @ Vector((0.0, -0.0032 * sc, 0.141 * sc)))

        for pd in petals_5:
            po = pd["obj"]
            t_det = pd["t_det"]
            p_raw = clamp((dt_b - pd["stag"]) / 0.78, 0.0, 1.0)
            if p_raw <= 0.01:
                po.hide_render = True
                continue

            if t < t_det:
                # Still attached to the flower stem — unfurling gracefully!
                po.hide_render = False
                u_op = ease_cubic(p_raw)
                over = 0.08 * math.sin(clamp((p_raw - 0.65) / 0.35, 0.0, 1.0) * math.pi) if p_raw > 0.65 else 0.0
                # Gentle wind tremor just before detachment
                pre_trem = math.radians(5.5) * math.sin(t * 12.0 + yaw) * smoothstep(t_det - 0.45, t_det, t) if t_det < 900.0 else 0.0
                pitch_deg = lerp(-76.0, -9.0, u_op) + 6.5 * over
                imb_k = int(round(pd["az"] / (2.0 * math.pi / 5.0)))
                imb_roll = math.radians(4.8 if (imb_k % 2 == 0) else -4.8) * u_op
                local_e = Euler((imb_roll, math.radians(pitch_deg) + pre_trem, pd["az"]), "XYZ")
                po.location = hinge_world + (stem_rot_m @ Vector((0.0, 0.0, imb_k * 0.0006 * sc)))
                po.rotation_euler = (stem_rot_m @ local_e.to_matrix()).to_euler("XYZ")
                p_sc = sc * lerp(0.30, 1.0, smoothstep(0.0, 0.70, p_raw))
                po.scale = (p_sc, p_sc * lerp(0.58, 1.0, u_op), p_sc)
                po.color = (smoothstep(0.0, 0.55, p_raw), 0.0, 1.0, 1.0)
            else:
                # PHYSICALLY DETACHED FROM THE STEM! Leaves the bare dark 5-sepal calyx behind forever (C6a & C8!)
                if t >= 44.5 or in_c7b:
                    po.hide_render = True
                    continue
                po.hide_render = False
                hov = pd["hover"]
                ph = pd["phase"]
                sp = pd["speed"]
                rid = pd["ribbon"]
                if t < 35.8:
                    u_l = clamp((t - t_det) / max(0.32, 35.8 - t_det), 0.0, 1.0)
                    e_l = 1.0 - (1.0 - u_l) ** 3
                    p_cur = hinge_world.lerp(hov, e_l)
                    po.location = p_cur
                    po.rotation_euler = (0.45 * math.sin(t * 2.1 + ph), 0.35 * math.cos(t * 1.7 + ph), yaw + pd["az"] + u_l * 1.5)
                    po.scale = (sc, sc, sc)
                    po.color = (1.0, smoothstep(0.0, 0.35, u_l), 1.0, 1.0)
                elif t < 36.8:
                    # 1.0s TRUE GRAVITY FREEZE — dead-still suspended breath!
                    u_f = t - 35.8
                    eb = math.sin(u_f * math.pi)
                    po.location = hov + Vector((0.014 * eb * math.sin(ph), 0.014 * eb * math.cos(ph), 0.020 * eb))
                    po.rotation_euler = (0.45 * math.sin(35.8 * 2.1 + ph), 0.35 * math.cos(35.8 * 1.7 + ph), yaw + pd["az"] + 1.5 + 0.02 * u_f)
                    po.scale = (sc, sc, sc)
                    po.color = (1.0, 1.0, 1.0, 1.0)
                else:
                    # Sweeping smoothly skyward with the blizzard ribbons!
                    u = t - 36.8
                    ang_s = u * 0.45 + rid * 2.094 + ph * 0.4
                    ang_0 = rid * 2.094 + ph * 0.4
                    sx = 4.6 * (math.sin(ang_s) - math.sin(ang_0)) + 1.25 * isw_g
                    sy = 3.2 * (math.cos(ang_s) - math.cos(ang_0)) + 0.85 * isw_g
                    sz = iu_g * 2.4 * sp
                    po.location = hov + Vector((sx, sy, sz))
                    po.rotation_euler = (0.7 * math.sin(u * 2.4 * sp + ph), 0.55 * math.cos(u * 1.9 * sp + ph), yaw + pd["az"] + 1.52 + u * 1.5 * sp)
                    po.scale = (sc * 1.15, sc * 1.15, sc * 1.15)
                    po.color = (1.0, 1.0, 1.0, 1.0)

    # 310 Colony Dormant Closed Buds (visible in C1/C2/C3 & on shadowed edges!) + Open Crowns + Post-Shed Calyxes!
    cb_obj, cb_tpl, cb_pos, cb_sc, cb_yaw, cb_tbl = handles["colony_buds"]
    bud_sc_cur = cb_sc * np.clip((cb_tbl + 0.36 - t) / 0.28, 0.0, 1.0)
    bud_pos_cur = np.where((bud_sc_cur > 0.02)[:, None], cb_pos, np.array([[0.0, 0.0, -500.0]], dtype=np.float32))
    bud_rot_cur = np.zeros_like(bud_pos_cur)
    bud_rot_cur[:, 2] = cb_yaw
    _update_dynamic_petal_mesh(cb_obj, cb_tpl, bud_pos_cur, bud_rot_cur, bud_sc_cur.astype(np.float32))

    cs_obj, cs_tpl, cs_pos, cs_sc, cs_yaw, cs_tshed = handles["colony_shed"]
    shed_cx_cur = cs_sc * np.where(cs_tshed < 900.0, np.clip((t - cs_tshed) / 0.35, 0.0, 1.0), 0.0)
    cx_pos_cur = np.where((shed_cx_cur > 0.02)[:, None], cs_pos, np.array([[0.0, 0.0, -500.0]], dtype=np.float32))
    cx_rot_cur = np.zeros_like(cx_pos_cur)
    cx_rot_cur[:, 2] = cs_yaw
    _update_dynamic_petal_mesh(cs_obj, cs_tpl, cx_pos_cur, cx_rot_cur, shed_cx_cur.astype(np.float32))

    # 310 Mid/Far Shore Colony Crowns + 180 Bridge Parapet Crowns (NumPy vectorized bloom -> 82% shed!)
    for key_name in ("colony_crowns", "bridge_crowns"):
        c_obj, c_tpl, c_pos, c_sc, c_yaw, c_tbl, c_tshed = handles[key_name]
        # Only visible from bloom wave onward; mature ~82% cleanly shed by t=36.5s leaving bare dark calyxes!
        open_u = np.clip((t - c_tbl) / 0.75, 0.0, 1.0)
        open_u = open_u * open_u * (3.0 - 2.0 * open_u)
        shed_u = np.clip((c_tshed + 0.45 - t) / 0.45, 0.0, 1.0)
        shed_u = np.where(c_tshed > 900.0, 1.0, shed_u * shed_u * (3.0 - 2.0 * shed_u))
        sc_cur = c_sc * open_u * shed_u
        # Park zero-scale crowns below floor so Cycles BVH stays ultra-clean
        pos_cur = np.where((sc_cur > 0.02)[:, None], c_pos, np.array([[0.0, 0.0, -500.0]], dtype=np.float32))
        rot_cur = np.zeros_like(pos_cur)
        rot_cur[:, 2] = c_yaw
        _update_dynamic_petal_mesh(c_obj, c_tpl, pos_cur, rot_cur, sc_cur.astype(np.float32))

    # v7.1 Director's Cut: ZERO adventurers in ALL 96s (100% immersive first-person POV for the 4 players!)
    hide_pcs = not spec["world"].get("show_pcs", False)
    for body_obj, head_obj, pc_spec in handles["pcs"]:
        body_obj.hide_render = hide_pcs
        head_obj.hide_render = hide_pcs
        if hide_pcs:
            continue
        base_p = Vector(pc_spec["pos"])
        idx = int(pc_spec["id"][-1])
        # Staggered overlapping anticipation in C2 (6..12s): PC2 steps half a pace back, all 4 turn heads toward whale!
        step = -0.32 * smoothstep(8.2, 11.4, t) if (idx == 2 and 6.0 <= t <= 12.0) else 0.0
        brace = math.radians(3.5) * smoothstep(8.8 + idx * 0.25, 11.5, t) if 6.0 <= t <= 12.0 else 0.0
        body_obj.location = base_p + Vector((0.0, step, 0.0))
        body_obj.rotation_euler = (-brace, 0.0, 0.0)
        # Head looks cleanly toward the emerging dark shadow in C2
        to_w = ws["pos"] - (body_obj.location + Vector((0.0, 0.0, pc_spec["height"])))
        yaw_h = clamp(math.atan2(-to_w.x, max(1.0, to_w.y)), math.radians(-28.0), math.radians(28.0))
        pitch_h = clamp(math.atan2(to_w.z, max(1.0, math.hypot(to_w.x, to_w.y))), math.radians(-10.0), math.radians(35.0))
        head_obj.rotation_euler = (pitch_h, 0.0, yaw_h)

    # Act 1/2/3 Physical Consequence FX updates!
    p0_loc = Vector(spec["world"]["p0_flower"]["pos"])
    # 1. C1 Falling water droplet (2.10..2.40s) cleanly onto open lake surface
    wd = handles["water_drop"]
    if 2.08 <= t <= 2.40:
        wd.hide_render = False
        u_d = clamp((t - 2.08) / 0.32, 0.0, 1.0)
        wd.location = (p0_loc.x + 1.2, -46.8, lerp(2.8, spec["world"]["lake_z"] + 0.02, u_d * u_d))
    else:
        wd.hide_render = True

    # 2. Concentric lake ripples (C1 2.4s & C8 92.0s) kept cleanly offshore
    for i, r_obj in enumerate(handles["ripples"]):
        age = -1.0
        if 2.4 <= t <= 6.0:
            age = (t - 2.4) - i * 0.35
        elif 92.0 <= t <= 96.0:
            age = (t - 92.0) - i * 0.35
        if 0.0 <= age <= 2.6:
            rad = 0.25 + age * 0.68
            r_obj.scale = (rad, rad, 1.0)
            r_obj.hide_render = False
        else:
            r_obj.hide_render = True

    # 3. C2-C3 Whale water breach rings (9.0..17.8s)
    for i, br in enumerate(handles["breach_rings"]):
        t0_b = 9.0 + i * 2.0
        age = t - t0_b
        if 0.0 <= age <= 3.6:
            ws_b = eval_whale_state(spec, t0_b)
            br.location = (ws_b["pos"].x, ws_b["pos"].y, spec["world"]["lake_z"] + 0.03)
            rad = 2.8 + age * 5.2
            br.scale = (rad, rad, 1.0)
            br.hide_render = False
        else:
            br.hide_render = True

    # 4. C3 Twin sculpted water spray plumes flaring off jaw while whale skims water (11.8..17.9s)
    sp_env = smoothstep(11.8, 13.0, t) * smoothstep(18.0, 16.5, t)
    handles["mat_spray"].node_tree.nodes["VAL_ALPHA"].outputs[0].default_value = 0.28 * max(sp_env, 0.65 if 9.0 <= t <= 21.5 else 0.0)
    for sp_o in handles["spray_objs"]:
        if sp_env > 0.02:
            sp_o.hide_render = False
            sp_o.location = ws["pos"] + Vector((0.0, 0.0, -ws["pos"].z * 0.35))
            sp_o.rotation_mode = "QUATERNION"
            sp_o.rotation_quaternion = q_align
            sp_o.scale = (0.7 + 0.55 * sp_env, 0.8 + 0.4 * sp_env, 0.6 + 0.65 * sp_env)
        else:
            sp_o.hide_render = True

    # 5. C4a Falling belly water streaks dripping past look-up POV (18.2..21.4s)
    in_c4a = (18.2 <= t <= 21.4)
    for bdo in handles["belly_drops"]:
        if not in_c4a:
            bdo.hide_render = True
            continue
        bdo.hide_render = False
        cycle_d = ((t - 18.2) * 1.15 + bdo["ph"]) % 1.0
        bdo.location = (ws["pos"].x * 0.5 + bdo["ox"], bdo["oy"], lerp(6.2, 0.4, cycle_d * cycle_d))

    # 6. Keep C5a pure & uncluttered (zero blobby smoke spheres behind whale; let moonlight shaft + VAL_IGNITE shine!)
    handles["breath_mist"].hide_render = True

    # 7. Act 1 subtle low mirror-lake mist wisps
    show_lm = (t < 24.0)
    for i, lm in enumerate(handles["lake_mists"]):
        lm.hide_render = not show_lm
        if show_lm:
            lm.location = (-8.0 + i * 16.0 + math.sin(t * 0.18 + i) * 3.5, -18.0 + i * 24.0, 0.32)

    # 8. Single hero final petal drifting down onto open mirror water at C8 (90.2..92.2s)
    fp = handles["final_petal"]
    if 90.2 <= t <= 92.25:
        fp.hide_render = False
        u_fp = clamp((t - 90.2) / 1.8, 0.0, 1.0)
        land_x, land_y = p0_loc.x + 1.2, -46.8
        fp.location = (
            land_x + 0.50 * math.sin(u_fp * math.pi * 1.8) * (1.0 - u_fp),
            land_y - 0.32 * (1.0 - u_fp),
            lerp(3.0, spec["world"]["lake_z"] + 0.025, smoothstep(0.0, 1.0, u_fp)),
        )
        fp.rotation_euler = (0.45 * math.sin(u_fp * 5.0) * (1.0 - u_fp), 0.35 * math.cos(u_fp * 4.0) * (1.0 - u_fp), u_fp * 2.2)
        sc_fp = 1.45 * smoothstep(92.25, 91.95, t)
        fp.scale = (sc_fp, sc_fp, sc_fp)
    else:
        fp.hide_render = True

    # -----------------------------------------------------------------------
    # 4-Layer 2,020-Petal Continuous Snowstorm Update (ZERO t=70s Teleport!)
    # -----------------------------------------------------------------------
    show_snow = (t >= 35.0) and (not in_c7b) and (t < 89.0)

    # Compute camera orthonormal basis for Layer 0 near-lens bokeh petals
    cam_fwd = (cam_look - cam_pos).normalized()
    cam_right = cam_fwd.cross(Vector((0.0, 0.0, 1.0)))
    cam_right = cam_right.normalized() if cam_right.length > 1e-4 else Vector((1.0, 0.0, 0.0))
    cam_up = cam_right.cross(cam_fwd).normalized()

    # Layer 0: 120 Near-Lens Bokeh Petals (active during peak blizzard C6a 37.5s .. C6d 68.5s + gentle C7c!)
    l0_obj, l0_tpl, l0_cfg = handles["snow_l0"]
    if show_snow and ((37.2 <= t < 69.0) or (83.0 <= t < 89.0)):
        l0_obj.hide_render = False
        n0 = len(l0_cfg["ph"])
        u0 = max(0.0, t - 36.8)
        env0 = smoothstep(37.2, 39.2, t) * smoothstep(69.0, 67.5, t) if t < 69.0 else 0.55 * smoothstep(83.0, 84.0, t)
        fov_x = math.atan(0.5 * spec["sensor_width_mm"] / sh["focal_mm"])
        fov_y = math.atan(0.5 * (spec["sensor_width_mm"] * 9.0 / 16.0) / sh["focal_mm"])
        d_arr = l0_cfg["depth"]
        # Continuous drift across camera frame edges (never blocking whale face in center!)
        ux = l0_cfg["u_x"] + 0.08 * np.sin(u0 * 0.65 * l0_cfg["spd"] + l0_cfg["ph"])
        if t < 69.0:
            uy = ((l0_cfg["u_y"] + iu_g * 0.10 * l0_cfg["spd"] + 1.0) % 2.0) - 1.0
        else:
            uy = ((l0_cfg["u_y"] - (t - 83.0) * 0.22 * l0_cfg["spd"] + 1.0) % 2.0) - 1.0
        wx_off = ux * d_arr * math.tan(fov_x)
        wy_off = uy * d_arr * math.tan(fov_y)
        cp = np.array(cam_pos, dtype=np.float32)
        cf = np.array(cam_fwd, dtype=np.float32)
        cr = np.array(cam_right, dtype=np.float32)
        cu = np.array(cam_up, dtype=np.float32)
        pos0 = cp[None, :] + d_arr[:, None] * cf[None, :] + wx_off[:, None] * cr[None, :] + wy_off[:, None] * cu[None, :]
        rot0 = np.stack([
            0.7 * np.sin(u0 * 2.2 * l0_cfg["spd"] + l0_cfg["ph"]),
            0.5 * np.cos(u0 * 1.8 * l0_cfg["spd"] + l0_cfg["ph"]),
            l0_cfg["ph"] + u0 * 1.4 * l0_cfg["spd"],
        ], axis=-1).astype(np.float32)
        edge_seam = np.minimum(np.clip((uy + 1.0) / 0.25, 0.0, 1.0), np.clip((1.0 - uy) / 0.25, 0.0, 1.0))
        sc0 = (l0_cfg["sc"] * env0 * edge_seam).astype(np.float32)
        _update_dynamic_petal_mesh(l0_obj, l0_tpl, pos0, rot0, sc0)
    else:
        l0_obj.hide_render = True

    # Layer 1: 700 Guided Whale-Wake Ribbon Petals (follows whale smoothly 36.8..67.0s, detaches into lingering snow 67..75s!)
    l1_obj, l1_tpl, l1_cfg = handles["snow_l1"]
    if show_snow and t < 75.0:
        l1_obj.hide_render = False
        n1 = len(l1_cfg["ph"])
        u1 = max(0.0, t - 36.8)
        # Sample 24 points along the whale's recent wake (or frozen wake once whale climbs out after t=67.0s = '置いていかれる雪'!)
        t_anchor = min(t, 67.2)
        dt_left = max(0.0, t - 67.2)
        # Build quick wake interpolation table across lag in [0, 8.5s]
        lag_grid = np.linspace(0.0, 8.5, 22)
        w_pts = np.array([eval_whale_state(spec, max(32.0, t_anchor - float(lg)))["pos"] for lg in lag_grid], dtype=np.float32)
        # Interpolate whale anchor per petal lag
        lags = l1_cfg["lag"]
        gx = np.interp(lags, lag_grid, w_pts[:, 0])
        gy = np.interp(lags, lag_grid, w_pts[:, 1])
        gz = np.interp(lags, lag_grid, w_pts[:, 2])
        ang1 = l1_cfg["ang"] + u1 * 0.32 * l1_cfg["spd"]
        # Gentle organic wake spread widening with lag + gentle downward drift once whale leaves after 67.2s!
        r1 = l1_cfg["rad"] * (0.55 + 0.09 * lags + 0.06 * dt_left)
        wake_x = gx + r1 * np.cos(ang1)
        wake_y = gy + r1 * np.sin(ang1)
        wake_z = gz + (r1 * 0.42) * np.sin(ang1 * 1.3 + l1_cfg["ph"]) - (dt_left ** 1.35) * 0.55 * l1_cfg["spd"]
        wake_pos = np.stack([wake_x, wake_y, np.maximum(1.2, wake_z)], axis=-1).astype(np.float32)

        if t < 35.8:
            ul = np.clip((t - l1_cfg["t_launch"]) / np.maximum(0.25, 35.8 - l1_cfg["t_launch"]), 0.0, 1.0)
            el = 1.0 - (1.0 - ul) ** 3
            pos1 = l1_cfg["orig"] * (1.0 - el[:, None]) + l1_cfg["hov"] * el[:, None]
            sc1 = l1_cfg["sc"] * np.clip(ul / 0.3, 0.0, 1.0)
        elif t < 36.8:
            # 1s TRUE GRAVITY FREEZE!
            eb = math.sin((t - 35.8) * math.pi)
            pos1 = l1_cfg["hov"] + np.stack([0.02 * eb * np.sin(l1_cfg["ph"]), 0.02 * eb * np.cos(l1_cfg["ph"]), np.full(n1, 0.025 * eb)], axis=-1).astype(np.float32)
            sc1 = l1_cfg["sc"]
        else:
            # Smoothly blend from hover position into the living whale wake river across 36.8..42.5s!
            bl = smoothstep(36.8, 42.5, t)
            rise_p = l1_cfg["hov"] + np.stack([
                2.5 * np.sin(u1 * 0.5 + l1_cfg["ph"]),
                2.0 * np.cos(u1 * 0.4 + l1_cfg["ph"]),
                iu_g * 2.2 * l1_cfg["spd"],
            ], axis=-1).astype(np.float32)
            pos1 = rise_p * (1.0 - bl) + wake_pos * bl
            sc1 = l1_cfg["sc"] * smoothstep(75.0, 72.5, t)
        rot1 = np.stack([
            0.55 * np.sin(u1 * 1.9 * l1_cfg["spd"] + l1_cfg["ph"]),
            0.45 * np.cos(u1 * 1.5 * l1_cfg["spd"] + l1_cfg["ph"]),
            l1_cfg["ph"] + u1 * 1.05 * l1_cfg["spd"],
        ], axis=-1).astype(np.float32)
        _update_dynamic_petal_mesh(l1_obj, l1_tpl, pos1.astype(np.float32), rot1.astype(np.float32), sc1.astype(np.float32))
    else:
        l1_obj.hide_render = True

    # Layer 2: 800 Midground Cathedral Blizzard Petals (100% continuous from 35.0s through 89.0s — ZERO t=70s teleport!)
    l2_obj, l2_tpl, l2_cfg = handles["snow_l2"]
    if show_snow:
        l2_obj.hide_render = False
        n2 = len(l2_cfg["ph"])
        ph2 = l2_cfg["ph"]
        sp2 = l2_cfg["spd"]
        if t < 35.8:
            ul = np.clip((t - l2_cfg["t_launch"]) / np.maximum(0.25, 35.8 - l2_cfg["t_launch"]), 0.0, 1.0)
            el = 1.0 - (1.0 - ul) ** 3
            pos2 = l2_cfg["orig"] * (1.0 - el[:, None]) + l2_cfg["hov"] * el[:, None]
            rot2 = np.stack([0.35 * np.sin(t * 1.6 + ph2), 0.25 * np.cos(t * 1.3 + ph2), ph2 + ul * 1.2], axis=-1)
            sc2 = l2_cfg["sc"] * np.clip(ul / 0.25, 0.0, 1.0)
        elif t < 36.8:
            # 1.0s TRUE GRAVITY FREEZE!
            eb = math.sin((t - 35.8) * math.pi)
            pos2 = l2_cfg["hov"] + np.stack([0.018 * eb * np.sin(ph2), 0.018 * eb * np.cos(ph2), np.full(n2, 0.025 * eb)], axis=-1)
            rot2 = np.stack([0.35 * np.sin(35.8 * 1.6 + ph2), 0.25 * np.cos(35.8 * 1.3 + ph2), ph2 + 1.2 + 0.02 * (t - 35.8)], axis=-1)
            sc2 = l2_cfg["sc"]
        else:
            u2 = t - 36.8
            s_ang = isw_g * 0.44 + l2_cfg["rid"] * 2.094 + ph2 * 0.35
            s_ang0 = l2_cfg["rid"] * 2.094 + ph2 * 0.35
            sw_x = 5.0 * (np.sin(s_ang) - np.sin(s_ang0)) + 1.15 * isw_g + 1.6 * np.sin(idn_g * 0.55 + ph2)
            sw_y = 3.4 * (np.cos(s_ang) - np.cos(s_ang0)) + 0.80 * isw_g + 1.0 * np.cos(idn_g * 0.45 + ph2)
            # Continuous integrated height: lifts smoothly in C6a-C6d, pauses at apex around 69-71s, falls smoothly in C7a & C7c!
            z_raw = l2_cfg["hov"][:, 2] + (iu_g * 2.25 - idn_g * 1.75) * sp2
            z_wrap = 1.0 + ((z_raw - 1.0) % 48.0)
            seam = np.minimum(np.clip((z_wrap - 1.0) / 2.6, 0.0, 1.0), np.clip((49.0 - z_wrap) / 3.2, 0.0, 1.0))
            # Gently thin to ~450 calm snow petals during C7c (83..89s)
            c7c_fade = 1.0 if t < 82.0 else np.where(l2_cfg["keep_c7c"], 0.85, 0.0)
            pos2 = np.stack([l2_cfg["hov"][:, 0] + sw_x, l2_cfg["hov"][:, 1] + sw_y, z_wrap], axis=-1)
            rot2 = np.stack([
                0.60 * np.sin(u2 * 2.1 * sp2 + ph2),
                0.48 * np.cos(u2 * 1.7 * sp2 + ph2),
                ph2 + 1.22 + (isw_g * 1.3 + idn_g * 0.55) * sp2,
            ], axis=-1)
            sc2 = l2_cfg["sc"] * seam * c7c_fade
        _update_dynamic_petal_mesh(l2_obj, l2_tpl, pos2.astype(np.float32), rot2.astype(np.float32), sc2.astype(np.float32))
    else:
        l2_obj.hide_render = True

    # Layer 3: 400 Far Mist Snow Sparks (deep cathedral atmosphere 37.5..89.0s!)
    l3_obj, l3_tpl, l3_cfg = handles["snow_l3"]
    if show_snow and t >= 37.2:
        l3_obj.hide_render = False
        ph3 = l3_cfg["ph"]
        sp3 = l3_cfg["spd"]
        fade3 = smoothstep(37.2, 41.0, t) * (0.65 if t >= 83.0 else 1.0)
        z_raw3 = l3_cfg["hov"][:, 2] + (iu_g * 1.65 - idn_g * 1.35) * sp3
        z3 = 2.0 + ((z_raw3 - 2.0) % 62.0)
        seam3 = np.minimum(np.clip((z3 - 2.0) / 4.0, 0.0, 1.0), np.clip((64.0 - z3) / 4.0, 0.0, 1.0))
        pos3 = np.stack([
            l3_cfg["hov"][:, 0] + 3.0 * np.sin(isw_g * 0.3 + ph3),
            l3_cfg["hov"][:, 1] + 2.0 * np.cos(isw_g * 0.25 + ph3),
            z3,
        ], axis=-1).astype(np.float32)
        rot3 = np.stack([0.4 * np.sin(t + ph3), 0.3 * np.cos(t * 0.8 + ph3), ph3 + t * 0.4], axis=-1).astype(np.float32)
        sc3 = (l3_cfg["sc"] * seam3 * fade3).astype(np.float32)
        _update_dynamic_petal_mesh(l3_obj, l3_tpl, pos3, rot3, sc3)
    else:
        l3_obj.hide_render = True

    # C7b Lunar-Absorption Peeling Petals + Sparse Delicate Rim Snow
    cp_obj, cp_tpl, cp_cfg = handles["c7b_peel"]
    cs_obj, cs_tpl, cs_cfg = handles["c7b_snow"]
    if in_c7b:
        cp_obj.hide_render = False
        cs_obj.hide_render = False
        moon_c = np.array([spec["world"]["moon"]["pos"][0], 76.0, spec["world"]["moon"]["pos"][2]], dtype=np.float32)
        n_mp = len(cp_cfg["u_body"])
        pos_p = np.full((n_mp, 3), -500.0, dtype=np.float32)
        rot_p = np.zeros((n_mp, 3), dtype=np.float32)
        sc_p = np.zeros(n_mp, dtype=np.float32)
        for i in range(n_mp):
            ub = float(cp_cfg["u_body"][i])
            t_peel = lerp(76.7, 81.5, ub)
            age = t - t_peel
            if 0.0 <= age <= 2.3:
                ws_p = eval_whale_state(spec, t_peel)
                yl = lerp(-12.0, 11.5, ub)
                spw = ws_p["pos"] + ws_p["fwd"] * yl + Vector((float(cp_cfg["off_x"][i]), 0.0, float(cp_cfg["off_z"][i])))
                pu = smoothstep(0.0, 2.2, age) * 0.62 * float(cp_cfg["pull"][i])
                ph = float(cp_cfg["ph"][i])
                pc = spw.lerp(Vector(moon_c), pu)
                pos_p[i] = (pc.x + 0.45 * math.sin(age * 2.0 + ph), pc.y, pc.z + 0.35 * math.cos(age * 1.8 + ph))
                rot_p[i] = (0.6 * math.sin(age * 2.5 + ph), 0.5 * math.cos(age * 2.0 + ph), ph + age * 1.4)
                sc_p[i] = float(cp_cfg["sc"][i]) * smoothstep(0.0, 0.20, age) * smoothstep(2.3, 1.15, age) * 0.85
        _update_dynamic_petal_mesh(cp_obj, cp_tpl, pos_p, rot_p, sc_p)

        dt_c = t - 75.0
        mz = spec["world"]["moon"]["pos"][2]
        zc = mz - 14.0 + ((cs_cfg["sz"] - (mz - 14.0) - dt_c * cs_cfg["spd"]) % 29.0)
        xc = cs_cfg["sx"] + 1.1 * np.sin(dt_c * 0.7 + cs_cfg["ph"])
        pos_s = np.stack([xc, cs_cfg["sy"], zc], axis=-1).astype(np.float32)
        rot_s = np.stack([0.5 * np.sin(dt_c * 1.4 + cs_cfg["ph"]), 0.4 * np.cos(dt_c * 1.1 + cs_cfg["ph"]), cs_cfg["ph"] + dt_c * 0.6], axis=-1).astype(np.float32)
        seam_s = np.minimum(np.clip((zc - (mz - 14.0)) / 2.5, 0.0, 1.0), np.clip(((mz + 15.0) - zc) / 2.5, 0.0, 1.0))
        _update_dynamic_petal_mesh(cs_obj, cs_tpl, pos_s, rot_s, (cs_cfg["sc"] * seam_s).astype(np.float32))
    else:
        cp_obj.hide_render = True
        cs_obj.hide_render = True

    bpy.context.view_layer.update()


def prepare_motion_blur_frame(handles: dict, spec: dict, t: float):
    """Set 3-point sub-frame keyframes around `t` (clamped strictly inside current shot to prevent cross-cut smear!)
    so Cycles renders genuine 180-degree shutter motion blur on camera moves, whale strokes, & near-lens petals."""
    scene = bpy.context.scene
    if not scene.render.use_motion_blur:
        apply_state_at_time(handles, spec, t)
        return

    sh = shot_at_time(spec, t)
    dt = 1.0 / float(spec["fps"])
    t_prev = max(sh["start"], t - dt)
    t_next = min(sh["end"] - 1e-4, t + dt)

    cam = handles["cam"]
    tgt = handles["cam_target"]
    whale = handles["whale"]
    for obj in (cam, tgt, whale):
        if obj.animation_data:
            obj.animation_data_clear()

    # Sample f=1 (prev), f=3 (next), then land cleanly on f=2 (exact center time `t` so all NumPy meshes match `t`!)
    for fr, tt in ((1, t_prev), (3, t_next), (2, t)):
        scene.frame_set(fr)
        apply_state_at_time(handles, spec, tt)
        cam.keyframe_insert("location", frame=fr)
        tgt.keyframe_insert("location", frame=fr)
        whale.keyframe_insert("location", frame=fr)
        whale.keyframe_insert("rotation_quaternion", frame=fr)
    scene.frame_set(2)


# ---------------------------------------------------------------------------
# Comprehensive v7.0 Measured Framing, Continuity, Shedding & Snow QA
# ---------------------------------------------------------------------------

def evaluated_world_verts(obj: bpy.types.Object) -> list[Vector]:
    deps = bpy.context.evaluated_depsgraph_get()
    eo = obj.evaluated_get(deps)
    em = eo.to_mesh()
    verts = [obj.matrix_world @ v.co for v in em.vertices]
    eo.to_mesh_clear()
    return verts


def run_measured_qa(handles: dict, spec: dict) -> dict:
    scene = bpy.context.scene
    cam = handles["cam"]
    checks = []
    fails = []

    # 1. Ground contact on all 4 PCs
    shore_z = spec["world"]["shore_z"]
    for body_obj, _, pc_spec in handles["pcs"]:
        verts = evaluated_world_verts(body_obj)
        min_z = min(v.z for v in verts)
        err = abs(min_z - shore_z)
        ok = err <= 0.03
        checks.append({"label": f"ground_contact:{pc_spec['id']}", "ok": ok, "min_z": round(min_z, 4)})
        if not ok:
            fails.append(f"{pc_spec['id']} ground error {err:.3f}m")

    # 2. C1 zero whale leak check (t = 5.9s)
    apply_state_at_time(handles, spec, 5.90)
    ok_c1 = handles["whale"].hide_render
    checks.append({"label": "C1_zero_whale_leak", "ok": ok_c1})
    if not ok_c1:
        fails.append("C1 whale visible before 6.0s!")

    # 3. C4b whale eye centered check (t = 23.25s)
    apply_state_at_time(handles, spec, 23.25)
    eye_r = next(e for e, _ in handles["whale_eyes"] if e.name.endswith("_R"))
    eye_w = eye_r.matrix_world.translation
    co_eye = world_to_camera_view(scene, cam, eye_w)
    ok_eye = (0.20 <= co_eye.x <= 0.80 and 0.25 <= co_eye.y <= 0.80 and co_eye.z > 0)
    checks.append({"label": "C4b_eye_centered", "ok": ok_eye, "uv": [round(co_eye.x, 3), round(co_eye.y, 3)], "dist_m": round(co_eye.z, 2)})
    if not ok_eye:
        fails.append(f"C4b eye off center: uv=({co_eye.x:.2f},{co_eye.y:.2f}) dist={co_eye.z:.1f}m")

    # 4. C6b top headroom check (zero pectoral/dorsal fin top-edge crop across 44.5..51.5s!)
    max_v_c6b = 0.0
    for tt in (45.0, 47.0, 48.5, 50.0, 51.5):
        apply_state_at_time(handles, spec, tt)
        wv = evaluated_world_verts(handles["whale"])
        vs = [world_to_camera_view(scene, cam, v).y for v in wv[::12]]
        max_v_c6b = max(max_v_c6b, max(vs))
    ok_c6b = max_v_c6b <= 0.96
    checks.append({"label": "C6b_top_headroom", "ok": ok_c6b, "max_v": round(max_v_c6b, 3)})
    if not ok_c6b:
        fails.append(f"C6b whale cropped at top edge (max_v={max_v_c6b:.3f})")

    # 5. C6c Mirror-lake symmetry check (both sky whale & inverted reflection inside frame!)
    apply_state_at_time(handles, spec, 56.0)
    wp = handles["whale"].location
    co_sky = world_to_camera_view(scene, cam, wp)
    co_ref = world_to_camera_view(scene, cam, Vector((wp.x, wp.y, -wp.z)))
    ok_c6c = (0.48 <= co_sky.y <= 0.88) and (0.04 <= co_ref.y <= 0.42)
    checks.append({"label": "C6c_mirror_symmetry", "ok": ok_c6c, "sky_v": round(co_sky.y, 3), "ref_v": round(co_ref.y, 3)})
    if not ok_c6c:
        fails.append(f"C6c mirror symmetry off: sky_v={co_sky.y:.3f}, ref_v={co_ref.y:.3f}")

    # 6. C7a zero snow teleport across t=69.5..70.5s!
    apply_state_at_time(handles, spec, 69.96)
    l2_obj = handles["snow_l2"][0]
    nv = len(l2_obj.data.vertices)
    v_a = np.empty((nv, 3), dtype=np.float32)
    l2_obj.data.vertices.foreach_get("co", v_a.ravel())
    apply_state_at_time(handles, spec, 70.00)
    v_b = np.empty((nv, 3), dtype=np.float32)
    l2_obj.data.vertices.foreach_get("co", v_b.ravel())
    # Ignore wrap-around vertices crossing z=1/49 boundary
    dz_step = np.abs(v_b[:, 2] - v_a[:, 2])
    valid = dz_step < 20.0
    max_jump = float(np.linalg.norm(v_b[valid] - v_a[valid], axis=1).max()) if np.any(valid) else 0.0
    ok_snow = max_jump < 0.35
    checks.append({"label": "C7a_zero_snow_teleport", "ok": ok_snow, "max_1frame_jump_m": round(max_jump, 4)})
    if not ok_snow:
        fails.append(f"C7a snow teleport detected at 70.0s ({max_jump:.3f}m/frame)")

    # 7. C8 true petal shedding check (mature shore flowers shed petals, P0 remains intact!)
    apply_state_at_time(handles, spec, 91.0)
    tot_p = 0
    shed_p = 0
    for _, _, _, p5, _, _, _, _ in handles["hero_blooms"]:
        for pd in p5:
            tot_p += 1
            if pd["obj"].hide_render:
                shed_p += 1
    shed_ratio = shed_p / max(1, tot_p)
    p0_intact = all(not pp.hide_render for pp in handles["p0_petals"])
    ok_shed = (shed_ratio >= 0.72) and p0_intact
    checks.append({"label": "C8_true_petal_shedding", "ok": ok_shed, "shed_ratio": round(shed_ratio, 3), "p0_intact": p0_intact})
    if not ok_shed:
        fails.append(f"C8 shedding check failed: ratio={shed_ratio:.2f}, p0_intact={p0_intact}")

    # 8. Unbroken C1 whale spline smoothness check (C2..C7a: zero jitter / zero teleport!)
    max_ang_step = 0.0
    max_pos_step = 0.0
    prev_w = eval_whale_state(spec, 6.0)
    for fi in range(6 * 24 + 1, 75 * 24):
        cur_w = eval_whale_state(spec, fi / 24.0)
        dp = (cur_w["pos"] - prev_w["pos"]).length
        da = math.degrees(prev_w["fwd"].angle(cur_w["fwd"], 0.0))
        max_pos_step = max(max_pos_step, dp)
        max_ang_step = max(max_ang_step, da)
        prev_w = cur_w
    ok_spl = (max_pos_step < 1.2) and (max_ang_step < 2.8)
    checks.append({"label": "whale_unbroken_spline", "ok": ok_spl, "max_m_per_f": round(max_pos_step, 3), "max_deg_per_f": round(max_ang_step, 3)})
    if not ok_spl:
        fails.append(f"Whale spline spike: {max_pos_step:.2f}m/f, {max_ang_step:.2f}deg/f")

    # 9. Shot-by-shot whale tracking table
    for sh in spec["shots"]:
        for tag, tt in (("IN", sh["start"] + 0.3), ("MID", 0.5 * (sh["start"] + sh["end"])), ("OUT", sh["end"] - 0.3)):
            apply_state_at_time(handles, spec, tt)
            row = {"shot": sh["id"], "beat": tag, "t": round(tt, 2), "focal_mm": sh["focal_mm"]}
            if "whale" in sh.get("subjects", []) and not handles["whale"].hide_render:
                co_w = world_to_camera_view(scene, cam, handles["whale"].location)
                row["whale_uv"] = [round(co_w.x, 3), round(co_w.y, 3)]
                row["whale_depth_m"] = round(co_w.z, 2)
            checks.append(row)

    # 10. Camera Line-of-Sight Terrain/Cavern Clearance check across every shot MID (catches buried cameras!)
    deps_cam = bpy.context.evaluated_depsgraph_get()
    cam_tgt_o = handles["cam_target"]
    obs_names = {"GEO-Shore", "GEO-ShoreBoulders", "GEO-CavernWalls", "GEO-CavernHeadlands", "GEO-CavernStalactites", "GEO-CavernRoofCanopy"}
    for sh in spec["shots"]:
        tt = 0.5 * (sh["start"] + sh["end"])
        apply_state_at_time(handles, spec, tt)
        deps_cam.update()
        c_p = cam.matrix_world.translation
        c_d = (cam_tgt_o.matrix_world.translation - c_p).normalized()
        hit, loc, _, _, obj, _ = scene.ray_cast(deps_cam, c_p, c_d)
        hit_dist = (loc - c_p).length if hit else 999.0
        blocked = hit and (obj is not None) and (obj.name in obs_names) and (hit_dist < 2.2)
        checks.append({"label": f"cam_clearance:{sh['id']}", "ok": not blocked, "hit_obj": obj.name if blocked else None, "dist_m": round(hit_dist, 3) if hit else None})
        if blocked:
            fails.append(f"Camera {sh['id']} blocked at {hit_dist:.2f}m by {obj.name}")

    report = {
        "version": spec["version"],
        "status": "PASS" if not fails else f"FAIL ({len(fails)})",
        "fails": fails,
        "hero_flowers": len(handles["hero_blooms"]),
        "colony_flowers": len(handles["colony_crowns"][2]),
        "bridge_blooms": len(handles["bridge_crowns"][2]),
        "snow_petals_total": (
            len(handles["snow_l0"][2]["ph"])
            + len(handles["snow_l1"][2]["ph"])
            + len(handles["snow_l2"][2]["ph"])
            + len(handles["snow_l3"][2]["ph"])
        ),
        "checks": checks,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    QA_REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"QA_REPORT: {QA_REPORT_PATH} -> {report['status']} (flowers={report['hero_flowers']}+{report['colony_flowers']}, snow={report['snow_petals_total']})")
    for f in fails:
        print(f"  FAIL: {f}")
    return report


# ---------------------------------------------------------------------------
# Build Full Scene & Render Entrypoints
# ---------------------------------------------------------------------------

def build_scene_in_current_blender(spec: dict | None = None, quality: str = "cycles", set_time: float = 56.0) -> dict:
    spec = spec or json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    clear_scene()

    aurora_mode = spec.get("aurora_mode", "sky_veil")
    mats = {
        "whale": make_whale_dissolve_material("MAT-Whale_Clay", aurora_mode=aurora_mode),
        "eye": make_whale_eye_material("MAT-Whale_Eye"),
        "pc": make_clay_material("MAT-PC_Silhouette", (0.09, 0.10, 0.13, 1.0), roughness=0.90),
        "stone": make_watergate_stone_material("MAT-ArchStone_Clay"),
        "sunken_city": make_sunken_city_material("MAT-SunkenCity"),
        "cavern_roof": make_cavern_roof_material("MAT-CavernRoof"),
        "star_vault": make_star_vault_material("MAT-StarVault", aurora_mode=aurora_mode),
        "starburst_hero": make_starburst_hero_material("MAT-StarburstHero"),
        "aurora_veil": make_aurora_veil_material("MAT-AuroraVeil", aurora_mode=aurora_mode),
        "shore": make_shore_rock_material("MAT-Shore_Rock"),
        "shore_moss": make_shore_moss_material("MAT-ShoreMoss"),
        "pillar": make_cavern_roof_material("MAT-FarPillar_Karst"),
        "water": make_mirror_lake_material("MAT-MirrorLake_Clay"),
        "moon": make_moon_maria_material("MAT-FullMoon"),
        "moon_corona": make_moon_corona_material("MAT-MoonCorona"),
        "fissure": make_cavern_roof_material("MAT-CeilingFissure3D"),
        "shaft": make_soft_beam_material("MAT-MoonShaft", base_atten=0.21),
        "p0_beam": make_soft_beam_material("MAT-P0_MoonBeam", base_atten=0.026, fade_z_half=6.0, edge_power=4.2),
        "stem_leaf": make_clay_material("MAT-StemLeaf", (0.068, 0.140, 0.116, 1.0), roughness=0.64, specular=0.24, subsurface=0.14, subsurf_radius=(0.20, 0.65, 0.54), sheen=0.48, sheen_tint=(0.82, 0.92, 0.98, 1.0)),
        "calyx_bud": make_calyx_bud_material("MAT-CalyxBud"),
        "bud_seam": make_bud_seam_material("MAT-BudInnerSeam"),
        "receptacle": make_clay_material("MAT-Receptacle", (0.48, 0.44, 0.26, 1.0), roughness=0.68, subsurface=0.12, subsurf_radius=(0.50, 0.58, 0.42)),
        "stamen_pistil": make_clay_material("MAT-StamenPistil", (0.82, 0.76, 0.54, 1.0), roughness=0.46, specular=0.36, subsurface=0.18, subsurf_radius=(0.68, 0.68, 0.52)),
        "petal": make_bloom_petal_material("MAT-Kousetsuka_Petal", always_open=False),
        "seed_capsule": make_kousetsuka_seed_material("MAT-Kousetsuka_Seed", always_glow=False),
        "seed_glow": make_kousetsuka_seed_material("MAT-Snow_SeedGlow", always_glow=True),
        "flower_white": make_bloom_petal_material("MAT-FlowerWhite", always_open=True),
        "water_fx": make_clay_material("MAT-WaterFX", (0.28, 0.36, 0.48, 1.0), roughness=0.06, metallic=0.18, specular=0.88),
        "snow_near": make_aurora_petal_material("MAT-Snow_Near", em_strength=0.36, far_muted=False, aurora_mode=aurora_mode, near_whale=False),
        "snow_wake": make_aurora_petal_material("MAT-Snow_Wake", em_strength=0.52, far_muted=False, aurora_mode=aurora_mode, near_whale=True),
        "snow_mid": make_aurora_petal_material("MAT-Snow_Mid", em_strength=0.32, far_muted=False, aurora_mode=aurora_mode, near_whale=False),
        "snow_far": make_aurora_petal_material("MAT-Snow_Far", em_strength=0.14, far_muted=True, aurora_mode=aurora_mode, near_whale=False),
        "moon_petal": make_clay_material("MAT-MoonPetal_Glow", (0.64, 0.74, 0.88, 1.0), roughness=0.65, emission_color=(0.72, 0.82, 0.96, 1.0), emission_strength=0.75),
        "spray": make_translucent_fx_material("MAT-Spray", color=(0.78, 0.86, 0.96, 1.0), em_strength=0.45, alpha_default=0.26),
        "breath": make_translucent_fx_material("MAT-BreathMist", color=(0.88, 0.94, 1.0, 1.0), em_strength=0.62, alpha_default=0.28),
        "lake_mist": make_translucent_fx_material("MAT-LakeMist", color=(0.45, 0.55, 0.70, 1.0), em_strength=0.18, alpha_default=0.10),
    }

    whale, whale_base, whale_eyes = build_anatomical_whale(mats["whale"], mats["eye"])
    pcs = [(*build_grounded_adventurer(pc, mats["pc"]), pc) for pc in spec["world"]["pcs"]]
    env = build_environment(spec, mats)
    lights = setup_lighting_and_world(spec)

    cam_target = bpy.data.objects.new("EMPTY-CamTarget", None)
    bpy.context.scene.collection.objects.link(cam_target)

    cam_data = bpy.data.cameras.new("CAM-Main")
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.sensor_width = spec["sensor_width_mm"]
    cam_data.clip_start = 0.1
    cam_data.clip_end = 600.0
    cam_data.show_composition_thirds = True

    cam = bpy.data.objects.new("CAM-Main", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    track = cam.constraints.new("TRACK_TO")
    track.target = cam_target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    bpy.context.scene.camera = cam

    setup_render_engine(spec, quality=quality)

    handles = {
        "cam": cam, "cam_target": cam_target,
        "whale": whale, "whale_base": whale_base, "whale_eyes": whale_eyes,
        "mat_whale": mats["whale"], "mat_eye": mats["eye"],
        "mat_spray": mats["spray"], "mat_breath": mats["breath"],
        "mat_sunken_city": mats["sunken_city"], "mat_cavern_roof": mats["cavern_roof"], "mat_pillar": mats["pillar"], "mat_fissure": mats["fissure"], "mat_water": mats["water"],
        "mat_star_vault": mats["star_vault"], "mat_starburst_hero": mats["starburst_hero"], "mat_aurora_veil": mats["aurora_veil"],
        "mat_snow_near": mats["snow_near"], "mat_snow_wake": mats["snow_wake"], "mat_snow_mid": mats["snow_mid"],
        "lights": lights, "pcs": pcs, **env,
    }
    apply_state_at_time(handles, spec, set_time)
    return handles


def render_still(handles: dict, spec: dict, t: float, out_path: Path, motion_blur: bool = True):
    scene = bpy.context.scene
    if scene.camera is None:
        raise RuntimeError("Camera guard failed: scene.camera is None")
    prev_mb = scene.render.use_motion_blur
    scene.render.use_motion_blur = motion_blur
    try:
        prepare_motion_blur_frame(handles, spec, t)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(out_path)
        bpy.ops.render.render(write_still=True)
        print(f"RENDERED_STILL: {out_path}")
    finally:
        scene.render.use_motion_blur = prev_mb


def build_contact_sheet_ffmpeg(image_paths: list[Path], cols: int, rows: int, out_path: Path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not image_paths:
        return
    list_txt = out_path.with_suffix(".concat.txt")
    list_txt.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in image_paths) + "\n", encoding="utf-8")
    subprocess.check_call([
        ffmpeg, "-y", "-v", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_txt),
        "-vf", f"scale=480:270,tile={cols}x{rows}:padding=6:margin=8:color=0x0d1118",
        "-frames:v", "1",
        str(out_path),
    ])
    list_txt.unlink(missing_ok=True)
    print(f"CONTACT_SHEET: {out_path}")


def render_full_film(handles: dict, spec: dict, overwrite: bool = False, samples: int = 10, res_scale: int = 75):
    import time as _time
    scene = bpy.context.scene
    scene.render.resolution_percentage = res_scale
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = samples
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = spec["shutter"]

    prog_path = OUT_DIR / "render_progress.json"
    fps = spec["fps"]
    total_frames = int(round(spec["duration"] * fps))
    done_frames = 0
    t_start = _time.time()
    clip_mp4s = []

    def write_prog(status: str, cur_clip: str):
        elapsed = _time.time() - t_start
        eta = (elapsed / max(1, done_frames)) * (total_frames - done_frames) if done_frames > 0 else 0.0
        prog_path.write_text(json.dumps({
            "version": spec["version"], "status": status, "current_clip": cur_clip,
            "done_frames": done_frames, "total_frames": total_frames,
            "pct": round(100.0 * done_frames / total_frames, 1),
            "elapsed_s": round(elapsed, 1), "eta_s": round(eta, 1),
            "engine": scene.render.engine, "samples": samples, "res_scale": res_scale,
        }, indent=2), encoding="utf-8")

    write_prog("running", spec["clips"][0]["id"])
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg not found on PATH")

    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    for cl in spec["clips"]:
        cid = cl["id"]
        f0 = int(round(cl["start"] * fps))
        f1 = int(round(cl["end"] * fps))
        dur = int(round(cl["end"] - cl["start"]))
        seq_dir = Path(tempfile.gettempdir()) / "ruosuen_v7_seq" / f"_seq_{cid}"
        if overwrite and seq_dir.exists():
            shutil.rmtree(seq_dir)
        seq_dir.mkdir(parents=True, exist_ok=True)
        for idx, fi in enumerate(range(f0, f1)):
            t = fi / fps
            frame_png = seq_dir / f"frame_{idx:04d}.png"
            if overwrite or not frame_png.exists():
                prepare_motion_blur_frame(handles, spec, t)
                scene.render.filepath = str(frame_png)
                bpy.ops.render.render(write_still=True)
            done_frames += 1
            if done_frames % 24 == 0 or done_frames == total_frames:
                write_prog("running", cid)
        out_mp4 = CLIPS_DIR / f"v7_clay_{cid}_{dur}s.mp4"
        subprocess.check_call([
            ffmpeg, "-y", "-v", "error", "-framerate", str(fps),
            "-i", str(seq_dir / "frame_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-movflags", "+faststart", str(out_mp4),
        ])
        clip_mp4s.append(out_mp4)
        print(f"CLIP_DONE: {out_mp4.name} ({done_frames}/{total_frames})")

    list_txt = OUT_DIR / "full_concat.txt"
    list_txt.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in clip_mp4s) + "\n", encoding="utf-8")
    full_mp4 = OUT_DIR / "v7_full_96s_clay_previs.mp4"
    subprocess.check_call([
        ffmpeg, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(list_txt),
        "-vf", "fade=t=out:st=94.6:d=1.4",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-movflags", "+faststart", str(full_mp4),
    ])
    list_txt.unlink(missing_ok=True)
    wav_cands = list(ROOT.parent.rglob("kousetsuka_v5_master_audio_96s.wav"))
    if wav_cands:
        audio_mp4 = OUT_DIR / "v7_full_96s_clay_previs_with_audio.mp4"
        subprocess.check_call([
            ffmpeg, "-y", "-v", "error", "-i", str(full_mp4), "-i", str(wav_cands[0]),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
            "-movflags", "+faststart", str(audio_mp4),
        ])
        top_copy = ROOT.parent / "v7_0_full_96s_clay_previs_with_audio.mp4"
        shutil.copy2(audio_mp4, top_copy)
        print(f"MUXED_FULL_AUDIO: {audio_mp4} & {top_copy}")
    write_prog("done", "ALL")
    print(f"FULL_FILM_DONE: {full_mp4} elapsed={_time.time() - t_start:.1f}s")
    return full_mp4


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["qa", "stills", "full_film"], default="stills")
    ap.add_argument("--quality", choices=["preview", "cycles"], default="cycles")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--res-scale", type=int, default=75)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args(argv)

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    handles = build_scene_in_current_blender(spec, quality=args.quality, set_time=56.0)
    scene = bpy.context.scene
    scene.render.resolution_percentage = args.res_scale
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = args.samples

    if args.mode == "qa":
        rep = run_measured_qa(handles, spec)
        if rep["fails"]:
            raise SystemExit(1)
    elif args.mode == "stills":
        run_measured_qa(handles, spec)
        one_per_shot = []
        mid_overrides = {"C1": 2.35, "C4b": 23.25, "C5a": 27.6, "C5b": 33.8, "C6a": 36.3, "C6c": 56.0, "C7b": 78.8, "C8": 92.2}
        for sh in spec["shots"]:
            mt = mid_overrides.get(sh["id"], 0.5 * (sh["start"] + sh["end"]))
            p = STILLS_DIR / f"{sh['id']}_mid.png"
            render_still(handles, spec, mt, p, motion_blur=True)
            one_per_shot.append(p)
        p_extra = STILLS_DIR / "C6a_reveal.png"
        render_still(handles, spec, 42.0, p_extra, motion_blur=True)
        one_per_shot.append(p_extra)
        build_contact_sheet_ffmpeg(one_per_shot, 4, 4, STILLS_DIR / "v7_one_per_shot_4x4.jpg")
    elif args.mode == "full_film":
        render_full_film(handles, spec, overwrite=args.overwrite, samples=args.samples, res_scale=args.res_scale)


if __name__ == "__main__":
    main()
