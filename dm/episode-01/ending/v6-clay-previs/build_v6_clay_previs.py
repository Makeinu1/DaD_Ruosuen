#!/usr/bin/env python3
"""Blender 4.x / 5.x Deterministic Clay Previs Engine for Episode 1 Ending 'Kousetsuka' (v6.0).

Follows:
  - cinematic-previs (matte grey/off-white clay look, S35/FF optics, 24fps, 180deg shutter, stills-first QA)
  - blender-python-previs (cross-version 4.x/5.x API safety, evaluated-vertex QA, PNG sequence -> Rec.709 H.264)
  - animation-principles (Disney 12 principles: S-wave follow-through, anticipation, Bezier easing, arcs, silhouette staging)

Run headless:
  blender --background --factory-startup --python-exit-code 1 \
    --python dm/episode-01/ending/v6-clay-previs/build_v6_clay_previs.py -- --mode look
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

import bpy
import bmesh
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "spec_v6.json"
OUT_DIR = ROOT / "out"
LOOK_DIR = OUT_DIR / "look"
STILLS_DIR = OUT_DIR / "stills"
CLIPS_DIR = OUT_DIR / "clips"
QA_REPORT_PATH = OUT_DIR / "qa_v6_report.json"


# ---------------------------------------------------------------------------
# Math & easing helpers (Disney Principle #6 Slow In / Slow Out + #7 Arcs)
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
    va, vb = Vector(a), Vector(b)
    return va.lerp(vb, t)


def catmull_rom(p0: Vector, p1: Vector, p2: Vector, p3: Vector, t: float) -> Vector:
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2.0 * p1)
        + (-p0 + p2) * t
        + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
        + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
    )


def get_fcurves_compat(action):
    """Cross-version Blender 4.x / 5.x Action fcurve accessor."""
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    fcurves = []
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cb in getattr(strip, "channelbags", []):
                fcurves.extend(cb.fcurves)
    return fcurves


# ---------------------------------------------------------------------------
# Scene reset & Clay Materials (cinematic-previs matte clay + AgX)
# ---------------------------------------------------------------------------

def clear_scene():
    """Safely clear all scene objects & data-blocks without resetting user preferences or unloading MCP addons."""
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.materials, bpy.data.worlds, bpy.data.actions):
        for item in list(col):
            if item.users == 0:
                col.remove(item)
    scene.camera = None


def make_clay_material(
    name: str,
    base_color=(0.52, 0.54, 0.58, 1.0),
    roughness: float = 0.82,
    metallic: float = 0.0,
    emission_color=None,
    emission_strength: float = 0.0,
    mist_range: tuple[float, float] | None = None,
    mist_color=(0.13, 0.16, 0.21, 1.0),
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
        bsdf.inputs["Specular IOR Level"].default_value = 0.25
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
        mr.inputs["To Max"].default_value = 0.82
        nt.links.new(cam_data.outputs["View Z Depth"], mr.inputs["Value"])
        mist_em = nt.nodes.new("ShaderNodeEmission")
        mist_em.inputs["Color"].default_value = mist_color
        mist_em.inputs["Strength"].default_value = 0.65
        mix_sh = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(mr.outputs["Result"], mix_sh.inputs["Fac"])
        nt.links.new(bsdf.outputs["BSDF"], mix_sh.inputs[1])
        nt.links.new(mist_em.outputs["Emission"], mix_sh.inputs[2])
        nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    else:
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_whale_dissolve_material(name: str = "MAT-Whale_Clay"):
    """Matte clay shader with smooth glow transition (dark slate -> pearl white),
    organic 3D-noise misty tail-to-head dissolve, and lunar-luminance merge as it dissolves into the moon."""
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
    bsdf.inputs["Roughness"].default_value = 0.78
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.28

    # Glow & Head-to-Tail Moonlight Ignition wave (C5a: nose +12.5m -> tail -12.5m!)
    glow_val = nt.nodes.new("ShaderNodeValue")
    glow_val.name = "VAL_GLOW"
    glow_val.outputs[0].default_value = 0.0

    ignite_val = nt.nodes.new("ShaderNodeValue")
    ignite_val.name = "VAL_IGNITE"
    ignite_val.outputs[0].default_value = 0.0

    # Tail-to-head dissolve driver (0.0 = 100% solid, 1.0 = 100% dissolved into full moon)
    dissolve_val = nt.nodes.new("ShaderNodeValue")
    dissolve_val.name = "VAL_DISSOLVE"
    dissolve_val.outputs[0].default_value = 0.0

    # Local Y in [-12.5, +12.5] -> u in [0 (tail), 1 (head)] perturbed by soft 3D misty noise
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tex_coord.outputs["Object"], sep.inputs["Vector"])

    map_u = nt.nodes.new("ShaderNodeMapRange")
    map_u.inputs["From Min"].default_value = -12.5
    map_u.inputs["From Max"].default_value = 12.5
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

    # Head-to-tail moonlight ignition mask: u_head = 1 - map_u (0 at snout, 1 at tail) + gentle 0.10 noise
    u_head = nt.nodes.new("ShaderNodeMath")
    u_head.operation = "SUBTRACT"
    u_head.inputs[0].default_value = 1.0
    nt.links.new(map_u.outputs["Result"], u_head.inputs[1])

    n_ig = nt.nodes.new("ShaderNodeMath")
    n_ig.operation = "MULTIPLY"
    n_ig.inputs[1].default_value = 0.10
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

    # lit_fac = 1 - ig_raw (1 where moonlight wave has swept past from nose -> tail, 0 where still dark!)
    lit_fac = nt.nodes.new("ShaderNodeMath")
    lit_fac.operation = "SUBTRACT"
    lit_fac.inputs[0].default_value = 1.0
    nt.links.new(ig_raw.outputs["Result"], lit_fac.inputs[1])

    # Brilliant silver ignition wave crest right at the moving frontier: 4 * lit_fac * (1 - lit_fac)
    crest_mul = nt.nodes.new("ShaderNodeMath")
    crest_mul.operation = "MULTIPLY"
    nt.links.new(lit_fac.outputs[0], crest_mul.inputs[0])
    nt.links.new(ig_raw.outputs["Result"], crest_mul.inputs[1])

    crest_em = nt.nodes.new("ShaderNodeMath")
    crest_em.operation = "MULTIPLY"
    crest_em.inputs[1].default_value = 7.2  # peak 1.80 silver flash right at the awakening wave edge!
    nt.links.new(crest_mul.outputs[0], crest_em.inputs[0])

    mix_col = nt.nodes.new("ShaderNodeMix")
    mix_col.data_type = "RGBA"
    mix_col.inputs["A"].default_value = (0.12, 0.15, 0.20, 1.0)  # unlit wet dark slate
    mix_col.inputs["B"].default_value = (0.74, 0.81, 0.92, 1.0)  # cool sculpted silver-pearl clay
    nt.links.new(lit_fac.outputs[0], mix_col.inputs["Factor"])
    nt.links.new(mix_col.outputs["Result"], bsdf.inputs["Base Color"])

    # Scale dissolve [0..1] -> [-0.24 .. +1.26] so d=0 is 100% solid and d=1 is 100% dissolved despite noise
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
        bsdf.inputs["Emission Color"].default_value = (0.94, 0.97, 1.0, 1.0)
        mul_em = nt.nodes.new("ShaderNodeMath")
        mul_em.operation = "MULTIPLY"
        mul_em.inputs[1].default_value = 0.34
        nt.links.new(lit_fac.outputs[0], mul_em.inputs[0])

        inv_op = nt.nodes.new("ShaderNodeMath")
        inv_op.operation = "SUBTRACT"
        inv_op.inputs[0].default_value = 1.0
        nt.links.new(smooth_op.outputs["Result"], inv_op.inputs[1])

        edge_em = nt.nodes.new("ShaderNodeMath")
        edge_em.operation = "MULTIPLY"
        edge_em.inputs[1].default_value = 1.55
        nt.links.new(inv_op.outputs[0], edge_em.inputs[0])

        d_sq = nt.nodes.new("ShaderNodeMath")
        d_sq.operation = "POWER"
        d_sq.inputs[1].default_value = 2.0
        nt.links.new(dissolve_val.outputs[0], d_sq.inputs[0])

        mul_lunar = nt.nodes.new("ShaderNodeMath")
        mul_lunar.operation = "MULTIPLY"
        mul_lunar.inputs[1].default_value = 1.35
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


def make_bloom_transition_material(name: str = "MAT-Kousetsuka_Bloom"):
    """Per-object color-driven shader transitioning smoothly from grey-brown closed bud (obj.color.r=0)
    to luminous matte white 5-petal Kousetsuka blossom (obj.color.r=1)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.74
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.22

    obj_info = nt.nodes.new("ShaderNodeObjectInfo")
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(obj_info.outputs["Color"], sep.inputs["Color"])

    mix_col = nt.nodes.new("ShaderNodeMix")
    mix_col.data_type = "RGBA"
    mix_col.inputs["A"].default_value = (0.42, 0.39, 0.35, 1.0)  # closed drooping bud
    mix_col.inputs["B"].default_value = (0.93, 0.95, 0.98, 1.0)  # open pure white Kousetsuka
    nt.links.new(sep.outputs["Red"], mix_col.inputs["Factor"])
    nt.links.new(mix_col.outputs["Result"], bsdf.inputs["Base Color"])

    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (0.92, 0.95, 1.0, 1.0)
        mul_em = nt.nodes.new("ShaderNodeMath")
        mul_em.operation = "MULTIPLY"
        mul_em.inputs[1].default_value = 0.24
        nt.links.new(sep.outputs["Red"], mul_em.inputs[0])
        nt.links.new(mul_em.outputs[0], bsdf.inputs["Emission Strength"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_whale_eye_material(name: str = "MAT-Whale_Eye"):
    """Quiet dark reflective whale eye with soft dissolve fade so eyes never detach in C7b."""
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
    bsdf.inputs["Base Color"].default_value = (0.04, 0.05, 0.08, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.14
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.85
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (0.68, 0.74, 0.86, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 0.18
    alpha_val = nt.nodes.new("ShaderNodeValue")
    alpha_val.name = "VAL_EYE_ALPHA"
    alpha_val.outputs[0].default_value = 1.0
    nt.links.new(alpha_val.outputs[0], mix_sh.inputs["Fac"])
    nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(bsdf.outputs["BSDF"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_soft_beam_material(name: str = "MAT-MoonShaft"):
    """Fresnel + vertical-feathered volumetric moonlight cone (zero hard cylinder edges or top/lake rings)."""
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
    em.inputs["Color"].default_value = (0.76, 0.84, 0.94, 1.0)
    em.inputs["Strength"].default_value = 0.55

    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.45
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])

    pwr = nt.nodes.new("ShaderNodeMath")
    pwr.operation = "POWER"
    pwr.inputs[1].default_value = 2.8
    nt.links.new(inv.outputs[0], pwr.inputs[0])

    # Vertical fade at both bottom (lake intersection) and top (fissure) using local Z in [-68, +68]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])

    fade_bot = nt.nodes.new("ShaderNodeMapRange")
    fade_bot.interpolation_type = "SMOOTHSTEP"
    fade_bot.clamp = True
    fade_bot.inputs["From Min"].default_value = -66.0
    fade_bot.inputs["From Max"].default_value = -42.0
    nt.links.new(sep.outputs["Z"], fade_bot.inputs["Value"])

    fade_top = nt.nodes.new("ShaderNodeMapRange")
    fade_top.interpolation_type = "SMOOTHSTEP"
    fade_top.clamp = True
    fade_top.inputs["From Min"].default_value = 66.0
    fade_top.inputs["From Max"].default_value = 44.0
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
    atten.operation = "MULTIPLY"
    atten.inputs[1].default_value = 0.22
    nt.links.new(f_mul.outputs[0], atten.inputs[0])

    nt.links.new(atten.outputs[0], mix_sh.inputs["Fac"])
    nt.links.new(transp.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(em.outputs["Emission"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    return mat


# ---------------------------------------------------------------------------
# Procedural Clean Clay Geometry Builders (Zero Z-fighting, True Proportions)
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
        obj.data.materials.append(mat)
    return obj


def build_anatomical_whale(mat_whale, mat_eye) -> tuple[bpy.types.Object, list[Vector], list[tuple[bpy.types.Object, Vector]]]:
    """Build a 24m streamlined baleen whale (+Y = nose, -Y = tail, +Z = dorsal)
    matching SheetA_whale_pcs.jpg proportions: smooth rounded baleen rostrum, gentle dorsal ridge,
    long sweeping pectoral fins, compact crescent horizontal tail fluke."""
    bm = bmesh.new()

    # 1. Main body loft along Y in [-12.0, +12.0] with dense snout rings for silky rostrum silhouette
    s_vals = [i / 40.0 for i in range(38)] + [0.955, 0.972, 0.985, 0.994, 0.999, 1.0]
    n_seg = 28
    rings = []
    for s in s_vals:
        y = lerp(-12.0, 12.0, s)
        if s < 0.04:
            rx = 0.14 + 2.4 * s
            rz_top = 0.14 + 2.4 * s
            rz_bot = 0.12 + 2.0 * s
        elif s < 0.64:
            u = (s - 0.04) / 0.60
            env = math.sin(u * math.pi * 0.5) ** 1.08
            rx = lerp(0.24, 2.35, env)
            rz_top = lerp(0.24, 1.75, env)
            rz_bot = lerp(0.20, 2.25, env)
        else:
            u = (s - 0.64) / 0.36
            # Silky rounded baleen whale rostrum (pure super-ellipse tapering cleanly to tip)
            ell = math.sqrt(max(0.0, 1.0 - (u ** 2.2)))
            rx = max(0.03, 2.35 * (ell ** 0.78))
            rz_top = max(0.03, 1.75 * (1.0 - 0.42 * u) * (ell ** 0.68))
            rz_bot = max(0.03, 2.25 * (1.0 - 0.25 * u) * (ell ** 0.85))
        dorsal_bump = 0.46 * math.exp(-((s - 0.33) / 0.042) ** 2)
        ring = []
        for j in range(n_seg):
            ang = 2.0 * math.pi * j / n_seg
            ca, sa = math.cos(ang), math.sin(ang)
            x = rx * ca
            if sa >= 0:
                z = rz_top * sa + (dorsal_bump * (sa ** 5))
            else:
                z = rz_bot * sa
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)

    for i in range(len(rings) - 1):
        for j in range(n_seg):
            jn = (j + 1) % n_seg
            bm.faces.new((rings[i][j], rings[i][jn], rings[i + 1][jn], rings[i + 1][j]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])

    # 2. Long sweeping pectoral fins (graceful ~1/3 body length swept back, overlapped inside torso)
    for side in (-1.0, 1.0):
        fin_rings = []
        steps = 12
        for k in range(steps + 1):
            u = k / steps
            x = side * lerp(1.2, 6.8, u)
            y = lerp(3.8, -2.4, u ** 1.15)
            z = lerp(-0.85, -2.15, u ** 0.9)
            chord = lerp(1.30, 0.12, u ** 0.85) * (1.0 + 0.16 * math.sin(u * math.pi))
            thick = lerp(0.30, 0.04, u)
            ring = []
            for m in range(10):
                ang = 2.0 * math.pi * m / 10
                ring.append(bm.verts.new((x, y + chord * math.cos(ang), z + thick * math.sin(ang))))
            fin_rings.append(ring)
        for k in range(steps):
            for m in range(10):
                mn = (m + 1) % 10
                if side > 0:
                    bm.faces.new((fin_rings[k][m], fin_rings[k + 1][m], fin_rings[k + 1][mn], fin_rings[k][mn]))
                else:
                    bm.faces.new((fin_rings[k][m], fin_rings[k][mn], fin_rings[k + 1][mn], fin_rings[k + 1][m]))
        bm.faces.new(fin_rings[-1] if side > 0 else list(reversed(fin_rings[-1])))

    # 3. Compact crescent horizontal tail fluke (keeps C5a silhouette unmistakably whale, never biplane!)
    for side in (-1.0, 1.0):
        fluke_rings = []
        steps = 10
        for k in range(steps + 1):
            u = k / steps
            x = side * lerp(0.15, 3.15, u)
            y = lerp(-11.3, -13.3, u ** 1.25)
            z = lerp(0.0, 0.18 * math.sin(u * math.pi), u)
            chord = lerp(1.15, 0.10, u ** 0.9) * (1.0 + 0.22 * math.sin(u * math.pi))
            thick = lerp(0.22, 0.03, u)
            ring = []
            for m in range(10):
                ang = 2.0 * math.pi * m / 10
                ring.append(bm.verts.new((x, y + chord * math.cos(ang), z + thick * math.sin(ang))))
            fluke_rings.append(ring)
        for k in range(steps):
            for m in range(10):
                mn = (m + 1) % 10
                if side > 0:
                    bm.faces.new((fluke_rings[k][m], fluke_rings[k + 1][m], fluke_rings[k + 1][mn], fluke_rings[k][mn]))
                else:
                    bm.faces.new((fluke_rings[k][m], fluke_rings[k][mn], fluke_rings[k + 1][mn], fluke_rings[k + 1][m]))
        bm.faces.new(fluke_rings[-1] if side > 0 else list(reversed(fluke_rings[-1])))

    whale_obj = finalize_mesh_obj("GEO-WH01_Whale", bm, mat_whale, smooth=True)
    base_coords = [v.co.copy() for v in whale_obj.data.vertices]

    # Small calm reflective eyes nestled in the whale cheek (follows head glance & dissolves cleanly in C7b)
    eyes = []
    for side, tag in ((-1.0, "L"), (1.0, "R")):
        bm_e = bmesh.new()
        bmesh.ops.create_uvsphere(bm_e, u_segments=28, v_segments=18, radius=0.22)
        eye = finalize_mesh_obj(f"GEO-WH01_Eye_{tag}", bm_e, mat_eye, smooth=True)
        eye.parent = whale_obj
        base_loc = Vector((side * 2.16, 5.8, -0.30))
        eye.location = base_loc
        eyes.append((eye, base_loc))

    return whale_obj, base_coords, eyes


def deform_whale_sway(whale_obj: bpy.types.Object, base_coords: list[Vector], t: float, glance_deg: float = 0.0):
    """Apply smooth organic S-wave swimming undulation (Disney Principle #5 Follow Through)
    plus subtle head turn toward viewer in C6d."""
    verts = whale_obj.data.vertices
    phase = t * 1.65
    glance_rad = math.radians(glance_deg)
    for idx, base in enumerate(base_coords):
        # Normalized distance from head (0 at nose +12, 1 at tail -12)
        s_tail = clamp((12.0 - base.y) / 24.0, 0.0, 1.0)
        # Vertical S-wave travelling head -> tail
        dz = 0.85 * (s_tail ** 1.75) * math.sin(phase - s_tail * 3.4)
        # Subtle lateral swim sway
        dx = 0.35 * (s_tail ** 1.6) * math.cos(phase * 0.7 - s_tail * 2.8)
        # Gentle head turn in C6d (only anterior third y > 3.0)
        head_w = smoothstep(2.0, 10.5, base.y)
        x = base.x + dx
        y = base.y
        z = base.z + dz
        if abs(glance_rad) > 1e-4 and head_w > 0.0:
            ang = glance_rad * head_w
            ca, sa = math.cos(ang), math.sin(ang)
            y_rel = y - 2.0
            x, y = x * ca - y_rel * sa, 2.0 + x * sa + y_rel * ca
        verts[idx].co = (x, y, z)
    whale_obj.data.update()


def build_grounded_adventurer(pc_spec: dict, mat_pc) -> bpy.types.Object:
    """Build a grounded matte clay human adventurer silhouette matching SheetA bottom-right
    (tapered waist, distinct shoulder/cloak/arm outlines, varied silhouettes, planted at local Z=0)."""
    h = pc_spec["height"]
    sw = pc_spec["shoulder_w"]
    idx = int(pc_spec["id"][-1])
    bm = bmesh.new()

    def add_cone(loc, rx1, ry1, rx2, ry2, depth, rot_x=0.0, rot_y=0.0):
        res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=16, radius1=1.0, radius2=1.0, depth=1.0)
        for v in res["verts"]:
            f = (v.co.z + 0.5)  # 0 at bottom, 1 at top
            v.co.x *= lerp(rx1, rx2, f)
            v.co.y *= lerp(ry1, ry2, f)
            v.co.z *= depth
        m = Matrix.Translation(loc) @ Matrix.Rotation(rot_x, 4, "X") @ Matrix.Rotation(rot_y, 4, "Y")
        bmesh.ops.transform(bm, matrix=m, verts=res["verts"])

    def add_sphere(loc, sx, sy, sz):
        res = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=1.0)
        m = Matrix.Translation(loc) @ Matrix.Diagonal((sx, sy, sz, 1.0))
        bmesh.ops.transform(bm, matrix=m, verts=res["verts"])

    # Grounded boots + legs (Z = 0.0 .. 0.48*h)
    for sx in (-0.11, 0.11):
        add_cone((sx, 0.0, h * 0.24), 0.062, 0.085, 0.078, 0.085, h * 0.48)
    # Tapered tunic / coat (flares slightly outward at bottom hem like SheetA adventurers)
    hem_z = h * (0.16 if idx in (1, 2) else 0.34)
    waist_z = h * 0.56
    chest_z = h * 0.79
    add_cone((0.0, 0.0, 0.5 * (hem_z + waist_z)), sw * 0.56, 0.17, sw * 0.36, 0.13, waist_z - hem_z + 0.06)
    add_cone((0.0, 0.0, 0.5 * (waist_z + chest_z)), sw * 0.36, 0.13, sw * 0.50, 0.16, chest_z - waist_z + 0.06)
    # Distinct outer arms resting slightly away from waist (breaks cylinder silhouette!)
    for side in (-1.0, 1.0):
        add_cone(
            (side * (sw * 0.53), 0.0, h * 0.62),
            0.052, 0.055, 0.068, 0.068, h * 0.34,
            rot_y=side * math.radians(-7.0),
        )
    # Cloak collar / shoulder mantle + pack variation
    add_sphere((0.0, 0.0, h * 0.79), sw * 0.54, 0.16, h * 0.065)
    if idx in (1, 2):
        # Travel cape drape down back
        add_cone((0.0, -0.10, h * 0.48), sw * 0.58, 0.08, sw * 0.44, 0.06, h * 0.60)
    elif idx == 3:
        # Shoulder armor pads (matching 3rd silhouette in SheetA)
        for side in (-1.0, 1.0):
            add_sphere((side * sw * 0.48, 0.0, h * 0.81), 0.11, 0.11, 0.07)
    # Neck & head
    add_cone((0.0, 0.0, h * 0.85), 0.058, 0.058, 0.054, 0.054, h * 0.07)
    add_sphere((0.0, 0.01, h * 0.93), 0.095, 0.11, h * 0.076)

    obj = finalize_mesh_obj(f"GEO-{pc_spec['id']}", bm, mat_pc, smooth=True)
    obj.location = Vector(pc_spec["pos"])
    return obj


def build_ruined_arch_bridge(bridge_spec: dict, mat_stone, mat_moss) -> bpy.types.Object:
    """Build clean smooth-curve semicircular stone aqueduct arches (extruded 2D arch spandrel profile,
    zero stair-stepping, zero gap between pier and arch, jagged broken center collapse)."""
    y_c = bridge_spec["y"]
    deck_z = bridge_spec["deck_z"]
    thick = bridge_spec["thickness"]
    half_t = thick * 0.5
    bm = bmesh.new()

    def add_box(cx, cy, cz, sx, sy, sz):
        res = bmesh.ops.create_cube(bm, size=1.0)
        m = Matrix.Translation((cx, cy, cz)) @ Matrix.Diagonal((sx, sy, sz, 1.0))
        bmesh.ops.transform(bm, matrix=m, verts=res["verts"])

    def add_extruded_arch_span(x0: float, x1: float):
        """Extrude one monolithic clean semicircular arch + piers down to Z=-4.0m (0 gaps, 0 stair steps)."""
        pier_w = 3.8
        xc = 0.5 * (x0 + x1)
        arch_r = max(2.0, (x1 - x0 - pier_w) * 0.5)
        spring_z = deck_z - arch_r - 2.4
        z_bot = -4.0

        # Construct smooth 2D polygon in XZ plane: left outer edge -> top deck -> right outer edge ->
        # right inner pier -> semicircular arch curve (32 smooth segments!) -> left inner pier
        pts_xz = [
            (x0, z_bot),
            (x0, deck_z),
            (x1, deck_z),
            (x1, z_bot),
            (xc + arch_r, z_bot),
            (xc + arch_r, spring_z),
        ]
        n_arc = 32
        for k in range(1, n_arc):
            ang = math.pi * k / n_arc  # 0 (right) -> pi (left)
            pts_xz.append((xc + arch_r * math.cos(ang), spring_z + arch_r * math.sin(ang)))
        pts_xz.extend([
            (xc - arch_r, spring_z),
            (xc - arch_r, z_bot),
        ])

        front_verts = [bm.verts.new((px, y_c - half_t, pz)) for (px, pz) in pts_xz]
        back_verts = [bm.verts.new((px, y_c + half_t, pz)) for (px, pz) in pts_xz]
        bm.faces.new(front_verts)
        bm.faces.new(list(reversed(back_verts)))
        n = len(pts_xz)
        for i in range(n):
            ni = (i + 1) % n
            bm.faces.new((front_verts[i], back_verts[i], back_verts[ni], front_verts[ni]))

        # Slight architectural cornice / parapet coping & pier plinths (overlapped smoothly)
        add_box(xc, y_c, deck_z + 0.55, (x1 - x0) + 0.3, thick * 1.12, 1.15)
        add_box(x0 + pier_w * 0.5, y_c, spring_z, pier_w * 1.08, thick * 1.08, 0.9)
        add_box(x1 - pier_w * 0.5, y_c, spring_z, pier_w * 1.08, thick * 1.08, 0.9)

    for x0, x1 in bridge_spec["left_spans"] + bridge_spec["right_spans"]:
        add_extruded_arch_span(x0, x1)

    # Jagged broken masonry ruins flanking the collapsed central gap (x=-24 and x=+26)
    for bx, sign in ((-23.8, 1.0), (25.8, -1.0)):
        add_box(bx + sign * 1.2, y_c, deck_z * 0.36, 3.2, thick * 0.95, deck_z * 0.72 + 4.0)
        add_box(bx + sign * 2.8, y_c, deck_z * 0.18, 2.2, thick * 0.86, deck_z * 0.36 + 4.0)

    bridge_obj = finalize_mesh_obj("GEO-ArchBridge", bm, mat_stone, smooth=False)
    bev = bridge_obj.modifiers.new("Bevel", type="BEVEL")
    bev.width = 0.12
    bev.segments = 2
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(35.0)
    return bridge_obj


def shore_surface_z(wx: float, wy: float, shore_z: float) -> float:
    """Deterministic rocky shore height (used by both GEO-Shore and planted buds so nothing floats)."""
    edge_drop = smoothstep(-51.8, -49.2, wy)
    flat_zone = math.exp(-((wx - 1.0) / 8.0) ** 2 - ((wy + 54.5) / 4.0) ** 2)
    rock_undul = (1.0 - flat_zone) * (0.25 * math.sin(wx * 0.55) * math.cos(wy * 0.45))
    return lerp(shore_z + rock_undul, -0.35, edge_drop)


def build_environment(spec: dict, mats: dict):
    w = spec["world"]
    # 1. Glassy dark sapphire/clay mirror lake plane
    bm_lake = bmesh.new()
    bmesh.ops.create_grid(bm_lake, x_segments=4, y_segments=4, size=240.0)
    lake = finalize_mesh_obj("GEO-MirrorLake", bm_lake, mats["water"], smooth=True)
    lake.location = (0.0, 20.0, w["lake_z"])

    # 2. Sculpted organic rocky shore (zero floating rectangular slabs!)
    rng = random.Random(spec["seed"])
    bm_sh = bmesh.new()
    bmesh.ops.create_grid(bm_sh, x_segments=40, y_segments=20, size=1.0)
    for v in bm_sh.verts:
        wx = v.co.x * 26.0
        wy = lerp(-74.0, -49.0, (v.co.y + 1.0) * 0.5)
        wz = shore_surface_z(wx, wy, w["shore_z"])
        v.co = Vector((wx, wy, wz))
    finalize_mesh_obj("GEO-Shore", bm_sh, mats["shore"], smooth=True)

    # 3. Ruined stone arch bridge
    bridge = build_ruined_arch_bridge(w["arch_bridge"], mats["stone"], mats["shore"])

    # 4. Far outer-flank colossal stalactite pillars (clear central sky!)
    bm_pil = bmesh.new()
    for p in w["far_pillars"]:
        res = bmesh.ops.create_cone(
            bm_pil, cap_ends=True, segments=18,
            radius1=p["r_base"], radius2=p["r_top"], depth=p["h"]
        )
        m = Matrix.Translation((p["x"], p["y"], p["h"] * 0.48))
        bmesh.ops.transform(bm_pil, matrix=m, verts=res["verts"])
    finalize_mesh_obj("GEO-FarPillars", bm_pil, mats["pillar"], smooth=True)

    # 5. Smooth 64-segment Full Moon + soft Fresnel Moonlight Shaft (no Saturn ring!)
    m_pos = Vector(w["moon"]["pos"])
    bm_m = bmesh.new()
    bmesh.ops.create_uvsphere(bm_m, u_segments=64, v_segments=32, radius=w["moon"]["radius"])
    moon_obj = finalize_mesh_obj("GEO-FullMoon", bm_m, mats["moon"], smooth=True)
    moon_obj.location = m_pos
    if hasattr(moon_obj, "visible_shadow"):
        moon_obj.visible_shadow = False

    # Dramatic diagonal silver moonlight column slanting from ceiling moon straight through C5a awakening point!
    shaft_bot = Vector((18.0, -24.0, -2.0))
    shaft_vec = m_pos - shaft_bot
    shaft_len = shaft_vec.length
    bm_shaft = bmesh.new()
    bmesh.ops.create_cone(bm_shaft, cap_ends=False, segments=40, radius1=20.0, radius2=10.5, depth=shaft_len)
    shaft = finalize_mesh_obj("GEO-MoonShaft", bm_shaft, mats["shaft"], smooth=True)
    shaft.location = 0.5 * (shaft_bot + m_pos)
    shaft.rotation_mode = "QUATERNION"
    shaft.rotation_quaternion = shaft_vec.normalized().to_track_quat("Z", "Y")
    if hasattr(shaft, "visible_shadow"):
        shaft.visible_shadow = False

    # 5b. Rough dark cavern ceiling fissure rock framing ONLY the outer corners of C7b (55mm camera at y=-24!)
    bm_fis = bmesh.new()
    n_fseg = 72
    inner_pts = []
    outer_pts = []
    for i in range(n_fseg):
        ang = 2.0 * math.pi * i / n_fseg
        ca, sa = math.cos(ang), math.sin(ang)
        # Clean jagged opening at y=40 (64m ahead of y=-24): moon proj r=9.1m, opening rx~19.2m, ry~12.2m (0 moon overlap!)
        crag = 1.0 + 0.11 * math.sin(ang * 5.0 + 0.4) + 0.05 * math.cos(ang * 9.0) + 0.03 * math.sin(ang * 15.0) + rng.uniform(-0.02, 0.02)
        ix = m_pos.x + 19.2 * crag * ca
        iz = m_pos.z + 12.2 * crag * sa
        ox = m_pos.x + 42.0 * ca
        oz = m_pos.z + 28.0 * sa
        inner_pts.append(bm_fis.verts.new((ix, 40.0, iz)))
        outer_pts.append(bm_fis.verts.new((ox, 40.0, oz)))
    for i in range(n_fseg):
        ni = (i + 1) % n_fseg
        bm_fis.faces.new((inner_pts[i], outer_pts[i], outer_pts[ni], inner_pts[ni]))
    fissure_obj = finalize_mesh_obj("GEO-CeilingFissure", bm_fis, mats["fissure"], smooth=False)
    if hasattr(fissure_obj, "visible_shadow"):
        fissure_obj.visible_shadow = False
    fissure_obj.hide_render = True

    # 6. Optional brass lantern (hidden when world.show_lantern == False per Director's Cut v6.2!)
    show_lan = w.get("show_lantern", True)
    l_pos = Vector(w["lantern"]["pos"])
    bm_lan = bmesh.new()
    for zc, r1, r2, dp in ((0.05, 0.14, 0.13, 0.10), (0.38, 0.12, 0.08, 0.09)):
        res = bmesh.ops.create_cone(bm_lan, cap_ends=True, segments=16, radius1=r1, radius2=r2, depth=dp)
        bmesh.ops.transform(bm_lan, matrix=Matrix.Translation((0, 0, zc)), verts=res["verts"])
    lan_body = finalize_mesh_obj("GEO-Lantern_Body", bm_lan, mats["lantern_metal"], smooth=True)
    lan_body.location = l_pos
    lan_body.hide_render = not show_lan

    bm_glass = bmesh.new()
    bmesh.ops.create_cone(bm_glass, cap_ends=True, segments=16, radius1=0.095, radius2=0.095, depth=0.24)
    lan_glass = finalize_mesh_obj("GEO-Lantern_Core", bm_glass, mats["lantern_glow"], smooth=True)
    lan_glass.location = l_pos + Vector((0.0, 0.0, 0.22))
    lan_glass.hide_render = not show_lan

    # 7. Natural-scale lone open 5-petal Kousetsuka (P0) + drooping shore buds
    p0_pos = Vector(w["p0_flower"]["pos"])
    bm_p0 = bmesh.new()
    res_st = bmesh.ops.create_cone(bm_p0, cap_ends=True, segments=8, radius1=0.012, radius2=0.008, depth=0.30)
    bmesh.ops.transform(bm_p0, matrix=Matrix.Translation((0, 0, 0.15)), verts=res_st["verts"])
    for k in range(5):
        ang = 2.0 * math.pi * k / 5.0
        res_p = bmesh.ops.create_uvsphere(bm_p0, u_segments=10, v_segments=6, radius=1.0)
        mp = (
            Matrix.Translation((math.cos(ang) * 0.085, math.sin(ang) * 0.085, 0.31))
            @ Matrix.Rotation(ang, 4, "Z")
            @ Matrix.Rotation(math.radians(-14.0), 4, "Y")
            @ Matrix.Diagonal((0.095, 0.048, 0.014, 1.0))
        )
        bmesh.ops.transform(bm_p0, matrix=mp, verts=res_p["verts"])
    p0_obj = finalize_mesh_obj("GEO-P0_Flower", bm_p0, mats["flower"], smooth=True)
    p0_obj.location = p0_pos

    # True organic plump drooping buds + staggered 5-petal sequential unfurling (zero matchsticks, zero popping!)
    bm_st = bmesh.new()
    res_st = bmesh.ops.create_cone(bm_st, cap_ends=True, segments=8, radius1=0.011, radius2=0.007, depth=0.25)
    bmesh.ops.transform(bm_st, matrix=Matrix.Translation((0, 0, 0.125)), verts=res_st["verts"])
    stem_mesh = bpy.data.meshes.new("MESH-FlowerStem")
    bm_st.to_mesh(stem_mesh)
    bm_st.free()
    for poly in stem_mesh.polygons:
        poly.use_smooth = True
    stem_mesh.materials.append(mats["bloom"])

    # Plump organic teardrop closed sepal bud (swells gently before petals unfurl, matching SheetB!)
    bm_bc = bmesh.new()
    res_bc = bmesh.ops.create_uvsphere(bm_bc, u_segments=12, v_segments=8, radius=1.0)
    for v in res_bc["verts"]:
        # Teardrop taper toward tip (+Z), fuller rounded base (-Z)
        t_z = clamp((v.co.z + 1.0) * 0.5, 0.0, 1.0)
        taper = lerp(1.15, 0.35, t_z ** 1.4)
        v.co.x *= 0.036 * taper
        v.co.y *= 0.036 * taper
        v.co.z = (v.co.z + 0.65) * 0.058
    bmesh.ops.transform(bm_bc, matrix=Matrix.Rotation(math.radians(38.0), 4, "X"), verts=res_bc["verts"])
    budcup_mesh = bpy.data.meshes.new("MESH-BudCup")
    bm_bc.to_mesh(budcup_mesh)
    bm_bc.free()
    for poly in budcup_mesh.polygons:
        poly.use_smooth = True
    budcup_mesh.materials.append(mats["bloom"])

    # Cupped almond petal pivoted cleanly at base hinge (0,0,0) extending along +X to x=0.165
    bm_fp = bmesh.new()
    res_fp = bmesh.ops.create_uvsphere(bm_fp, u_segments=10, v_segments=6, radius=1.0)
    bmesh.ops.transform(bm_fp, matrix=Matrix.Translation((0.082, 0.0, 0.0)) @ Matrix.Diagonal((0.084, 0.044, 0.011, 1.0)), verts=res_fp["verts"])
    for v in bm_fp.verts:
        u_len = clamp(v.co.x / 0.166, 0.0, 1.0)
        v.co.z += 0.018 * math.sin(u_len * math.pi)
    fpetal_mesh = bpy.data.meshes.new("MESH-FlowerPetal")
    bm_fp.to_mesh(fpetal_mesh)
    bm_fp.free()
    for poly in fpetal_mesh.polygons:
        poly.use_smooth = True
    fpetal_mesh.materials.append(mats["bloom"])

    pc_xy = [(p["pos"][0], p["pos"][1]) for p in w["pcs"]]
    shore_blooms = []
    for idx in range(78):
        # Rich shore carpet strictly on solid rock (by <= -52.0), keeping a clean 0.65m corridor ahead of C5b lens!
        if idx < 28:
            bx = rng.uniform(-5.5, 11.5)
            by = rng.uniform(-56.8, -52.2)
        elif idx < 56:
            # Framing left/right banks of C5b's low forward slider toward the lake & arches!
            bx = rng.uniform(1.8, 9.2)
            by = rng.uniform(-54.8, -52.1)
        else:
            # Lush water's-edge Kousetsuka meadow directly ahead in C5b mid/out frame (y in [-53.4, -51.9])!
            bx = rng.uniform(2.2, 8.6)
            by = rng.uniform(-53.4, -51.95)
        if math.hypot(bx - p0_pos.x, by - p0_pos.y) < 0.42 or math.hypot(bx - l_pos.x, by - l_pos.y) < 0.46:
            continue
        if any(math.hypot(bx - px, by - py) < 0.55 for px, py in pc_xy):
            continue
        # Keep C5b low 24cm slider centerline clear so NO flower gets sliced right against the lens!
        if -56.2 <= by <= -52.9 and abs(bx - lerp(3.55, 3.95, clamp((by + 55.8) / 2.9, 0.0, 1.0))) < 0.68:
            continue
        bz = shore_surface_z(bx, by, w["shore_z"]) - 0.015
        sc = rng.uniform(0.78, 1.15)
        yaw = rng.uniform(0.0, 6.283)
        droop_deg = rng.uniform(14.0, 22.0)
        # Wave sweeps FORWARD along C5b's path from near lantern/P0 (y=-55.5) toward lake edge (y=-52.1) during 30.3..32.6s!
        wave_u = clamp((by + 55.8) / 3.8 * 0.72 + abs(bx - 4.0) / 8.0 * 0.28, 0.0, 1.0)
        t_bloom = lerp(30.3, 32.6, wave_u) + rng.uniform(-0.10, 0.10)

        stem_o = bpy.data.objects.new(f"GEO-BloomStem_{idx:02d}", stem_mesh)
        bpy.context.scene.collection.objects.link(stem_o)
        stem_o.location = (bx, by, bz)
        stem_o.scale = (sc, sc, sc)
        stem_o.color = (0.0, 1.0, 1.0, 1.0)

        bud_cup = bpy.data.objects.new(f"GEO-BudCup_{idx:02d}", budcup_mesh)
        bpy.context.scene.collection.objects.link(bud_cup)
        bud_cup.parent = stem_o
        bud_cup.location = (0.0, 0.0, 0.235)
        bud_cup.color = (0.0, 1.0, 1.0, 1.0)

        petals_5 = []
        for k in range(5):
            po = bpy.data.objects.new(f"GEO-BloomPetal_{idx:02d}_{k}", fpetal_mesh)
            bpy.context.scene.collection.objects.link(po)
            po.parent = stem_o
            po.location = (0.0, 0.0, 0.245)
            po.color = (0.0, 1.0, 1.0, 1.0)
            petals_5.append((po, 2.0 * math.pi * k / 5.0, k * 0.065))
        shore_blooms.append((stem_o, bud_cup, petals_5, t_bloom, sc, yaw, droop_deg))

    # 7b. 72 Ruined Stone Arch Parapet Blooms (ignite in C5b wave 32.3..34.4s after leaping across the lake!)
    bm_bbl = bmesh.new()
    for k in range(5):
        ang = 2.0 * math.pi * k / 5.0
        res_bp = bmesh.ops.create_uvsphere(bm_bbl, u_segments=8, v_segments=5, radius=1.0)
        mp = (
            Matrix.Translation((math.cos(ang) * 0.42, math.sin(ang) * 0.42, 0.35))
            @ Matrix.Rotation(ang, 4, "Z")
            @ Matrix.Rotation(math.radians(-14.0), 4, "Y")
            @ Matrix.Diagonal((0.46, 0.23, 0.07, 1.0))
        )
        bmesh.ops.transform(bm_bbl, matrix=mp, verts=res_bp["verts"])
    bbloom_mesh = bpy.data.meshes.new("MESH-BridgeBloom")
    bm_bbl.to_mesh(bbloom_mesh)
    bm_bbl.free()
    for poly in bbloom_mesh.polygons:
        poly.use_smooth = True
    bbloom_mesh.materials.append(mats["flower"])

    bridge_blooms = []
    ab = w["arch_bridge"]
    for idx in range(72):
        # Concentrate on right spans (visible in C5b) + left spans (visible in C6a/C6b/C6c)
        if idx < 46:
            bx = rng.uniform(25.5, 98.0)
        else:
            bx = rng.uniform(-92.0, -24.5)
        by = ab["y"] + rng.uniform(-2.1, 1.6)
        bz = ab["deck_z"] + 1.05 + rng.uniform(-0.08, 0.15)
        # Wave sweeps outward from the central collapsed breach (|x|=25 -> |x|=98) during 32.3..34.4s!
        wave_b = clamp((abs(bx) - 24.5) / 74.0, 0.0, 1.0)
        t_bl = lerp(32.35, 34.35, wave_b) + rng.uniform(-0.12, 0.12)
        b_sc = rng.uniform(0.75, 1.55)
        bo = bpy.data.objects.new(f"GEO-BridgeBloom_{idx:02d}", bbloom_mesh)
        bpy.context.scene.collection.objects.link(bo)
        bo.location = (bx, by, bz)
        bo.rotation_euler = (rng.uniform(-0.22, 0.22), rng.uniform(-0.15, 0.15), rng.uniform(0, 6.283))
        bo.scale = (0.01, 0.01, 0.01)
        bo.hide_render = True
        bridge_blooms.append((bo, t_bl, b_sc))

    # 8. Concentric water ripple rings (animated in C1 at t=2.4s and C8 at t=92.0s)
    ripples = []
    for i in range(3):
        bm_r = bmesh.new()
        res = bmesh.ops.create_circle(bm_r, cap_ends=False, radius=1.0, segments=48)
        bmesh.ops.extrude_edge_only(bm_r, edges=bm_r.edges[:])
        outer = [v for v in bm_r.verts if v not in res["verts"]]
        for v in outer:
            v.co *= 1.08
        r_obj = finalize_mesh_obj(f"GEO-Ripple_{i}", bm_r, mats["flower"], smooth=True)
        r_obj.location = (p0_pos.x + 1.2, p0_pos.y + 4.0, w["lake_z"] + 0.02)
        r_obj.scale = (0.01, 0.01, 1.0)
        ripples.append(r_obj)

    # 8b. Single hero final petal drifting down onto the lake at C8 (t=90.3..92.0s) to trigger ripples!
    bm_pt = bmesh.new()
    res_pt = bmesh.ops.create_uvsphere(bm_pt, u_segments=10, v_segments=6, radius=1.0)
    bmesh.ops.transform(bm_pt, matrix=Matrix.Diagonal((0.24, 0.13, 0.022, 1.0)), verts=res_pt["verts"])
    for v in bm_pt.verts:
        # Subtle graceful petal cup curve so petals read as organic blossoms, not flat pills!
        v.co.z += 0.045 * (v.co.x / 0.24) ** 2
    pt_mesh = bpy.data.meshes.new("MESH-Petal")
    bm_pt.to_mesh(pt_mesh)
    bm_pt.free()
    for poly in pt_mesh.polygons:
        poly.use_smooth = True
    pt_mesh.materials.append(mats["flower"])

    final_petal = bpy.data.objects.new("GEO-FinalPetal", pt_mesh)
    bpy.context.scene.collection.objects.link(final_petal)
    final_petal.scale = (0.55, 0.55, 0.55)
    final_petal.hide_render = True

    # 9. Coherent 3-layer helical wind-stream floral snowstorm (320 petals, zero TV-static jitter!)
    petals = []
    for idx in range(320):
        po = bpy.data.objects.new(f"GEO-Petal_{idx:03d}", pt_mesh)
        bpy.context.scene.collection.objects.link(po)
        if hasattr(po, "visible_shadow"):
            po.visible_shadow = False
        if idx < 110:
            # Layer 0: Foreground & C6a crane-corridor blossoms detaching directly off the shore flowers!
            layer = 0
            ox = rng.uniform(-6.5, 14.5)
            oy = rng.uniform(-52.5, -34.0)
            oz = rng.uniform(0.95, 1.25)
            hx = ox + rng.uniform(-0.35, 0.35)
            hy = oy + rng.uniform(-0.35, 0.35)
            hz = rng.uniform(1.45, 4.4)
            base_sc = rng.uniform(0.42, 0.92)
            sp = rng.uniform(0.95, 1.35)
        elif idx < 235:
            # Layer 1: Midground swirling wind ribbons sweeping across arches, mirror lake & whale
            layer = 1
            ox = rng.uniform(-34.0, 42.0)
            oy = rng.uniform(-44.0, 46.0)
            oz = rng.uniform(0.5, 2.2)
            hx = ox + rng.uniform(-1.0, 1.0)
            hy = oy + rng.uniform(-1.0, 1.0)
            hz = rng.uniform(2.0, 12.0)
            base_sc = rng.uniform(0.95, 1.85)
            sp = rng.uniform(0.90, 1.45)
        else:
            # Layer 2: Deep cathedral & high-altitude snowfall curtain (large near-lens & far depth)
            layer = 2
            ox = rng.uniform(-52.0, 52.0)
            oy = rng.uniform(-22.0, 68.0)
            oz = rng.uniform(4.0, 26.0)
            hx = ox
            hy = oy
            hz = rng.uniform(6.0, 32.0)
            base_sc = rng.uniform(1.35, 2.55)
            sp = rng.uniform(0.80, 1.25)

        po["layer"] = layer
        po["origin"] = [ox, oy, oz]
        po["hover"] = [hx, hy, hz]
        # Coherent spatial phase so neighboring petals surf the SAME wind stream ribbons!
        po["phase"] = (hx * 0.08 + hy * 0.06) + rng.uniform(-0.35, 0.35)
        po["speed"] = sp
        po["ribbon_id"] = idx % 3
        po["base_scale"] = base_sc
        # First 24 delicate shore petals detach gently at end of C5b (33.2..34.6s) to bridge seamlessly into C6a!
        if idx < 24:
            po["origin"] = [rng.uniform(2.8, 8.8), rng.uniform(-52.4, -50.8), rng.uniform(1.02, 1.18)]
            po["hover"] = [po["origin"][0] + rng.uniform(-0.3, 0.5), po["origin"][1] + rng.uniform(0.6, 1.8), rng.uniform(1.6, 3.0)]
            po["base_scale"] = rng.uniform(0.28, 0.50)
            po["t_launch"] = rng.uniform(33.2, 34.5)
        else:
            po["t_launch"] = rng.uniform(35.0, 35.45)
        po.scale = (base_sc, base_sc, base_sc)
        petals.append(po)

    # 10. Dedicated C7b lunar-absorption peeling petals + ambient cool-silver rim snow (visible vs BOTH sky & moon!)
    bm_mp = bmesh.new()
    res_mp = bmesh.ops.create_uvsphere(bm_mp, u_segments=8, v_segments=5, radius=1.0)
    bmesh.ops.transform(bm_mp, matrix=Matrix.Diagonal((0.24, 0.13, 0.022, 1.0)), verts=res_mp["verts"])
    mp_mesh = bpy.data.meshes.new("MESH-MoonPetal")
    bm_mp.to_mesh(mp_mesh)
    bm_mp.free()
    for poly in mp_mesh.polygons:
        poly.use_smooth = True
    mp_mesh.materials.append(mats["moon_petal"])

    moon_petals = []
    for idx in range(90):
        mp = bpy.data.objects.new(f"GEO-MoonPetal_{idx:02d}", mp_mesh)
        bpy.context.scene.collection.objects.link(mp)
        if hasattr(mp, "visible_shadow"):
            mp.visible_shadow = False
        u_body = lerp(0.02, 0.96, idx / 89.0) + rng.uniform(-0.015, 0.015)
        u_body = clamp(u_body, 0.02, 0.96)
        r_body = 2.0 * math.sin(u_body * math.pi) ** 0.75 + 0.18
        mp["u_body"] = u_body
        mp["off_z"] = rng.uniform(-r_body * 0.85, r_body * 0.85)
        mp["off_x"] = rng.uniform(-0.6, 0.6)
        mp["phase"] = rng.uniform(0.0, 6.283)
        mp["drift_z"] = rng.uniform(-0.8, 1.6)
        mp["pull_speed"] = rng.uniform(0.75, 1.35)
        mp["base_scale"] = rng.uniform(0.85, 1.65)
        mp.hide_render = True
        moon_petals.append(mp)

    # 55 ambient drifting snow petals framing C7b dark cavern fissure corners & moon edge (alive through 83.0s!)
    c7b_snow = []
    for idx in range(55):
        sp_o = bpy.data.objects.new(f"GEO-C7bSnow_{idx:02d}", mp_mesh)
        bpy.context.scene.collection.objects.link(sp_o)
        if hasattr(sp_o, "visible_shadow"):
            sp_o.visible_shadow = False
        sp_o["sx"] = m_pos.x + rng.uniform(-24.0, 24.0)
        sp_o["sy"] = rng.uniform(32.0, 58.0)
        sp_o["sz"] = m_pos.z + rng.uniform(-14.0, 15.0)
        sp_o["phase"] = rng.uniform(0.0, 6.283)
        sp_o["fall_spd"] = rng.uniform(0.75, 1.55)
        sp_o["base_scale"] = rng.uniform(0.55, 1.25)
        sp_o.hide_render = True
        c7b_snow.append(sp_o)

    return {
        "bridge": bridge, "moon": moon_obj, "shaft": shaft, "fissure": fissure_obj,
        "lantern": lan_body, "p0": p0_obj, "ripples": ripples, "final_petal": final_petal,
        "petals": petals, "moon_petals": moon_petals, "c7b_snow": c7b_snow,
        "shore_blooms": shore_blooms, "bridge_blooms": bridge_blooms,
    }


def setup_lighting_and_world(spec: dict):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("WORLD-ClayCavern")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.06, 0.08, 0.11, 1.0)
        bg.inputs["Strength"].default_value = 0.65

    # Soft directional moonlight key (cast from high ceiling fissure)
    key_d = bpy.data.lights.new("LGT-MoonKey", type="SUN")
    key_d.energy = 2.4
    key_d.color = (0.86, 0.91, 1.0)
    key_d.angle = math.radians(8.0)
    key = bpy.data.objects.new("LGT-MoonKey", key_d)
    scene.collection.objects.link(key)
    key.rotation_euler = (math.radians(38), math.radians(-18), math.radians(-22))

    # Gentle cool rim/fill area light to keep clay silhouettes crisp
    fill_d = bpy.data.lights.new("LGT-ClayFill", type="AREA")
    fill_d.energy = 8500.0
    fill_d.size = 45.0
    fill_d.color = (0.72, 0.78, 0.88)
    fill = bpy.data.objects.new("LGT-ClayFill", fill_d)
    scene.collection.objects.link(fill)
    fill.location = (-28.0, -75.0, 32.0)
    fill.rotation_euler = (math.radians(68), 0.0, math.radians(-20))

    # Warm subtle point light at brass lantern (disabled when show_lantern == False)
    if spec["world"].get("show_lantern", True):
        lan_d = bpy.data.lights.new("LGT-LanternPool", type="POINT")
        lan_d.energy = 65.0
        lan_d.shadow_soft_size = 0.18
        lan_d.color = (1.0, 0.90, 0.72)
        lan = bpy.data.objects.new("LGT-LanternPool", lan_d)
        scene.collection.objects.link(lan)
        l_pos = Vector(spec["world"]["lantern"]["pos"])
        lan.location = l_pos + Vector((0.0, 0.0, 0.25))

    # Dynamic silver moonlight awakening burst light following the whale during C5a transformation!
    aw_d = bpy.data.lights.new("LGT-WhaleAwaken", type="POINT")
    aw_d.energy = 0.0
    aw_d.shadow_soft_size = 6.0
    aw_d.color = (0.86, 0.93, 1.0)
    aw = bpy.data.objects.new("LGT-WhaleAwaken", aw_d)
    scene.collection.objects.link(aw)
    aw.location = (20.0, -28.0, 18.0)
    return aw


def setup_render_engine(spec: dict, quality: str = "preview"):
    scene = bpy.context.scene
    scene.render.fps = spec["fps"]
    scene.render.resolution_x, scene.render.resolution_y = spec["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = spec["shutter"]
    scene.render.use_persistent_data = True

    # Blender 5.2+ requires media_type before file_format
    if hasattr(scene.render.image_settings, "media_type"):
        scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    # AgX color management (never Standard)
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium Contrast"
    except Exception:
        scene.view_settings.view_transform = "Filmic"
    scene.view_settings.exposure = 0.15

    # Prefer Cycles OptiX/Metal GPU for ultra-clean soft-shadow clay & real mirror reflections
    if quality == "cycles":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 36
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.03
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 6
        scene.cycles.diffuse_bounces = 3
        scene.cycles.glossy_bounces = 3
        scene.cycles.transparent_max_bounces = 8
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
        eevee = getattr(scene, "eevee", None)
        if eevee is not None:
            for attr, val in (("taa_render_samples", 32), ("use_gtao", True), ("use_ssr", True)):
                if hasattr(eevee, attr):
                    setattr(eevee, attr, val)


# ---------------------------------------------------------------------------
# Time evaluation (Whale Catmull-Rom + Camera + Petals + Ripples)
# ---------------------------------------------------------------------------

def _hermite_vec_and_deriv(kfs: list[dict], t: float) -> tuple[Vector, Vector]:
    """Time-weighted C1-continuous Cubic Hermite spline with exact analytical velocity derivative.
    Eliminates ALL keyframe boundary clamping & jitter/wobble across non-uniform keyframe spacing!"""
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
        # Catmull-Rom weighted by true elapsed time (smooth physical velocity across uneven intervals!)
        return (Vector(kfs[k + 1]["pos"]) - Vector(kfs[k - 1]["pos"])) / max(1e-6, kfs[k + 1]["t"] - kfs[k - 1]["t"])

    t0, t1 = kfs[idx]["t"], kfs[idx + 1]["t"]
    h = max(1e-6, t1 - t0)
    u = clamp((t - t0) / h, 0.0, 1.0)
    u2 = u * u
    u3 = u2 * u
    p0 = Vector(kfs[idx]["pos"])
    p1 = Vector(kfs[idx + 1]["pos"])
    m0 = tangent(idx) * h
    m1 = tangent(idx + 1) * h

    pos = (
        (2.0 * u3 - 3.0 * u2 + 1.0) * p0
        + (u3 - 2.0 * u2 + u) * m0
        + (-2.0 * u3 + 3.0 * u2) * p1
        + (u3 - u2) * m1
    )
    vel = (
        (6.0 * u2 - 6.0 * u) * p0
        + (3.0 * u2 - 4.0 * u + 1.0) * m0
        + (-6.0 * u2 + 6.0 * u) * p1
        + (3.0 * u2 - 2.0 * u) * m1
    ) / h
    return pos, vel


def _hermite_scalar(kfs: list[dict], key: str, t: float, default: float = 0.0) -> float:
    """Smooth C1 time-weighted Hermite interpolation for scalar tracks (roll, etc. — zero barrel-roll stutter!)."""
    n = len(kfs)
    if t <= kfs[0]["t"]:
        return kfs[0].get(key, default)
    if t >= kfs[-1]["t"]:
        return kfs[-1].get(key, default)
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
    return (2*u3 - 3*u2 + 1)*v0 + (u3 - 2*u2 + u)*m0 + (-2*u3 + 3*u2)*v1 + (u3 - u2)*m1


def eval_whale_state(spec: dict, t: float) -> dict:
    if t >= 75.0:
        # C7b Director's Cut v6.2: NO sideways pass! Whale ascends gracefully UPWARD & DEEP INTO the full moon's heart!
        # Continues C7a's exact upward screen direction, shrinking naturally in depth as it melts tail -> head!
        u_g = clamp((t - 75.0) / 6.8, 0.0, 1.0)
        e_g = 1.0 - (1.0 - u_g) ** 1.55
        p_start = Vector((35.5, 24.0, 121.0))
        p_end = Vector((43.5, 72.0, 131.6))
        # Subtle organic upward arc curve into the glowing center of the full moon
        pos = p_start.lerp(p_end, e_g) + Vector((0.0, 0.0, 1.4 * math.sin(e_g * math.pi)))
        e_g2 = 1.0 - (1.0 - clamp((t + 0.06 - 75.0) / 6.8, 0.0, 1.0)) ** 1.55
        pos2 = p_start.lerp(p_end, e_g2) + Vector((0.0, 0.0, 1.4 * math.sin(e_g2 * math.pi)))
        fwd = (pos2 - pos) if (pos2 - pos).length > 1e-4 else (p_end - p_start)
        fwd.normalize()
        # Gentle subtle bank showing graceful back & sweeping pectoral wings as it swims away into moonlight
        roll = 6.283 + lerp(-0.22, 0.0, e_g)
        dissolve = smoothstep(76.8, 81.6, t)
        glow = 1.0 if t < 82.0 else 0.0
        return {"pos": pos, "fwd": fwd, "roll": roll, "glow": glow, "ignite": 1.0, "dissolve": dissolve}

    kfs_all = spec["whale"]["keyframes"]
    # Decouple C1..C4b (t < 25.0) and C5a..C7a (25.0 <= t < 75.0) cleanly at the C4b->C5a cut boundary
    # so zero 180-deg hairpin velocity reversal ever causes heading jitter!
    if t < 25.0:
        kfs = [k for k in kfs_all if k["t"] < 25.0]
    else:
        kfs = [k for k in kfs_all if k["t"] >= 25.0]
    pos, vel = _hermite_vec_and_deriv(kfs, t)
    fwd = vel.normalized() if vel.length > 1e-4 else Vector((0.0, 1.0, 0.0))
    roll = _hermite_scalar(kfs, "roll", t, 0.0)
    # Linear clamp for glow/ignite/dissolve tracks
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
        # 0.0..1.8s: 100% LOCKED-OFF for visible shore petal takeoff (0.0..0.8s) + 1.0s dead-still gravity freeze (0.8..1.8s)!
        # 1.8..8.2s: smooth crane rise + skyward reveal tilt, landing gently on 0.8s hold!
        raw_r = clamp((local - 1.8) / max(1e-6, dur - 2.6), 0.0, 1.0)
        u = 1.0 - (1.0 - smoothstep(0.0, 1.0, raw_r)) ** 1.35
        pos = lerp_vec(sh["pos0"], sh["pos1"], u)
        look = lerp_vec(sh["look0"], sh["look1"], u)
        return sh, pos, look
    elif mode == "c6c_orbit":
        # True flawless elliptical orbital arc at constant altitude (rulebook.md techvis standard!)
        oc = Vector(sh["orbit_center"])
        deg = lerp(sh["orbit_deg0"], sh["orbit_deg1"], u)
        rad = math.radians(deg)
        pos = Vector((oc.x + sh["orbit_rx"] * math.cos(rad), oc.y + sh["orbit_ry"] * math.sin(rad), oc.z))
        look = lerp_vec(sh["look0"], sh["look1"], u)
        return sh, pos, look
    elif mode == "c6d_slow_glance":
        # Gentle tracking that breathes down to 0.6x slow-motion during the 2.5..5.5s affectionate glance!
        # Piecewise smooth integral of speed (1.0 -> 0.55 during glance -> 1.15 on ascent)
        s_t = clamp((local - hi) / move_dur, 0.0, 1.0)
        u_s = s_t - 0.07 * math.sin(s_t * 2.0 * math.pi)
        u_s = ease_cubic(clamp(u_s, 0.0, 1.0))
        pos = lerp_vec(sh["pos0"], sh["pos1"], u_s)
        look = lerp_vec(sh["look0"], sh["look1"], u_s)
        return sh, pos, look

    pos = lerp_vec(sh["pos0"], sh["pos1"], u)
    look = lerp_vec(sh["look0"], sh["look1"], u)
    return sh, pos, look


def apply_state_at_time(scene_handles: dict, spec: dict, t: float):
    sh, cam_pos, cam_look = eval_camera(spec, t)
    cam = scene_handles["cam"]
    target = scene_handles["cam_target"]
    cam.data.lens = sh["focal_mm"]
    cam.location = cam_pos
    target.location = cam_look

    # Whale transform + organic S-wave + shader state
    ws = eval_whale_state(spec, t)
    whale = scene_handles["whale"]
    whale.location = ws["pos"]
    # Align whale +Y along forward vector with +Z up, then apply local Y roll
    q_align = ws["fwd"].to_track_quat("Y", "Z")
    q_roll = Euler((0.0, ws["roll"], 0.0), "XYZ").to_quaternion()
    whale.rotation_mode = "QUATERNION"
    whale.rotation_quaternion = q_align @ q_roll
    glance_deg = 22.0 * math.sin(smoothstep(62.0, 66.5, t) * math.pi) if 60.0 <= t <= 69.0 else 0.0
    deform_whale_sway(whale, scene_handles["whale_base"], t, glance_deg=glance_deg)

    mat_w = scene_handles["mat_whale"]
    mat_w.node_tree.nodes["VAL_GLOW"].outputs[0].default_value = ws["glow"]
    if "VAL_IGNITE" in mat_w.node_tree.nodes:
        mat_w.node_tree.nodes["VAL_IGNITE"].outputs[0].default_value = ws.get("ignite", ws["glow"])
    mat_w.node_tree.nodes["VAL_DISSOLVE"].outputs[0].default_value = ws["dissolve"]
    whale.hide_render = (t < 5.8 or t >= 82.0)

    # Dynamic silver moonlight awakening burst light during C5a (26.0..30.0s) illuminating lake & arches!
    aw_lgt = scene_handles.get("awaken_light")
    if aw_lgt is not None:
        aw_lgt.location = ws["pos"] + ws["fwd"] * 4.0 + Vector((0.0, 0.0, 2.0))
        if 25.8 <= t <= 30.5:
            # Peak luminous flash right as the head-to-tail ignition wave washes across the whale (26.5..29.2s)!
            burst = math.sin(smoothstep(25.8, 30.2, t) * math.pi)
            aw_lgt.data.energy = 65000.0 * burst + 14000.0 * ws.get("ignite", 0.0)
        elif 30.5 < t < 75.0:
            aw_lgt.data.energy = 14000.0
        else:
            aw_lgt.data.energy = 0.0

    # Sync whale eyes with head glance deformation + linger until head dissolves LAST!
    eye_alpha = smoothstep(0.92, 0.74, ws["dissolve"])
    scene_handles["mat_eye"].node_tree.nodes["VAL_EYE_ALPHA"].outputs[0].default_value = eye_alpha
    glance_rad = math.radians(glance_deg)
    for eye_obj, base_loc in scene_handles["whale_eyes"]:
        eye_obj.hide_render = whale.hide_render or (eye_alpha <= 0.02)
        ex, ey, ez = base_loc.x, base_loc.y, base_loc.z
        head_w = smoothstep(2.0, 10.5, ey)
        if abs(glance_rad) > 1e-4 and head_w > 0.0:
            ang = glance_rad * head_w
            ca, sa = math.cos(ang), math.sin(ang)
            y_rel = ey - 2.0
            ex, ey = ex * ca - y_rel * sa, 2.0 + ex * sa + y_rel * ca
        eye_obj.location = (ex, ey, ez)

    # C7b visibility toggles: hide shaft, show dark rocky cavern ceiling fissure border framing the full moon!
    in_c7b = (75.0 <= t < 83.0)
    if "shaft" in scene_handles:
        scene_handles["shaft"].hide_render = in_c7b
    if "fissure" in scene_handles:
        scene_handles["fissure"].hide_render = not in_c7b

    # Organic plump drooping buds -> Anticipation swell -> Staggered 5-petal sequential unfurl wave!
    for stem_o, bud_cup, petals_5, t_bloom, sc, yaw, droop_deg in scene_handles.get("shore_blooms", []):
        dt_b = t - t_bloom
        # Anticipation beat (0.28s before unfurl): bud gently lifts & swells slightly before bursting open!
        ant = smoothstep(-0.28, 0.0, dt_b)
        raw = clamp(dt_b / 0.95, 0.0, 1.0)
        sway = math.radians(1.6) * math.sin(t * 1.4 + yaw)
        cur_droop = math.radians(lerp(droop_deg, 0.0, smoothstep(-0.22, 0.65, dt_b)))
        stem_o.rotation_euler = (cur_droop + sway, sway * 0.5, yaw)
        col_u = smoothstep(0.02, 0.68, raw)
        stem_o.color = (col_u, 1.0, 1.0, 1.0)

        # Plump closed sepal bud visible until petals peel open past 38%
        bud_hide = (raw >= 0.42)
        bud_cup.hide_render = bud_hide
        if not bud_hide:
            swell = 1.0 + 0.16 * ant * (1.0 - smoothstep(0.05, 0.40, raw))
            shrink = smoothstep(0.42, 0.12, raw)
            bud_cup.scale = (swell * shrink, swell * shrink, swell * shrink)
            bud_cup.color = (col_u * 0.5, 1.0, 1.0, 1.0)

        # 5 petals unfurl with overlapping time stagger (Disney #5 Overlapping Action) + gentle elastic settle!
        # In C6a (t >= 35.0), subtle wind tremble as detached petals lift off the blossoms
        shed_tremble = math.radians(4.5) * math.sin(t * 9.0 + yaw) * smoothstep(34.9, 35.3, t) * smoothstep(36.2, 35.6, t)
        for po, az, stag in petals_5:
            p_raw = clamp((dt_b - stag) / 0.80, 0.0, 1.0)
            if p_raw <= 0.01:
                po.hide_render = True
                continue
            po.hide_render = False
            u_op = ease_cubic(p_raw)
            over = 0.08 * math.sin(clamp((p_raw - 0.65) / 0.35, 0.0, 1.0) * math.pi) if p_raw > 0.65 else 0.0
            pitch_deg = lerp(-76.0, -5.0, u_op) + (7.0 * over)
            po.rotation_euler = (0.0, math.radians(pitch_deg) + shed_tremble, az)
            p_sc = lerp(0.32, 1.0, smoothstep(0.0, 0.72, p_raw))
            po.scale = (p_sc, p_sc * lerp(0.60, 1.0, u_op), p_sc)
            po.color = (smoothstep(0.0, 0.55, p_raw), 1.0, 1.0, 1.0)

    # 72 Ruined Stone Arch Parapet Blooms (ignite in sweeping C5b wave 32.35..34.35s, stay lit through C8!)
    for bo, t_bl, b_sc in scene_handles.get("bridge_blooms", []):
        if t < t_bl:
            bo.hide_render = True
        else:
            bo.hide_render = False
            u_bb = smoothstep(0.0, 0.55, t - t_bl)
            s_bb = b_sc * (0.15 + 0.85 * u_bb)
            bo.scale = (s_bb, s_bb, s_bb)

    # PC visibility & subtle anticipation:
    # - Shown in OTS adventurer POV shots (C2 6..12s, plus PC4 far-right OTS edge in C5a)
    # - Hidden in pure first-person POV shots (C3, C4a, C5b, C6a, C7a) and strictly REMOVED from ending (C7c & C8: t >= 83.0)!
    hide_pcs = (t >= 83.0) or (12.0 <= t < 25.0) or (30.0 <= t < 44.0) or (69.0 <= t < 75.0)
    for pc_obj, pc_spec in scene_handles["pcs"]:
        # In C5a, hide PC1..PC3 directly in front of the left-side look-up lens so ONLY clean open sky/profile reads
        hide_this = hide_pcs or (25.0 <= t < 30.0 and pc_spec["id"] in ("PC1", "PC2"))
        pc_obj.hide_render = hide_this
        base_p = Vector(pc_spec["pos"])
        step = -0.35 * smoothstep(8.0, 11.2, t) if (pc_spec["id"] == "PC2" and 6.0 <= t <= 25.0) else 0.0
        pc_obj.location = base_p + Vector((0.0, step, 0.0))

    # Concentric water ripples (C1 at 2.4s, C8 at 92.0s)
    for i, r_obj in enumerate(scene_handles["ripples"]):
        age = -1.0
        if 2.4 <= t <= 6.0:
            age = (t - 2.4) - i * 0.35
        elif 92.0 <= t <= 96.0:
            age = (t - 92.0) - i * 0.35
        if 0.0 <= age <= 2.6:
            rad = 0.25 + age * 1.45
            r_obj.scale = (rad, rad, 1.0)
            r_obj.hide_render = False
        else:
            r_obj.hide_render = True

    # Single hero final petal drifting down in graceful S-curve onto the glassy lake at C8 (90.3..92.0s)!
    fp = scene_handles.get("final_petal")
    if fp is not None:
        if 90.2 <= t <= 92.25:
            fp.hide_render = False
            u_fp = clamp((t - 90.2) / 1.8, 0.0, 1.0)
            p0_loc = Vector(spec["world"]["p0_flower"]["pos"])
            land_x, land_y = p0_loc.x + 1.2, p0_loc.y + 4.0
            fp.location = (
                land_x + 0.55 * math.sin(u_fp * math.pi * 1.8) * (1.0 - u_fp),
                land_y - 0.35 * (1.0 - u_fp),
                lerp(3.2, spec["world"]["lake_z"] + 0.025, smoothstep(0.0, 1.0, u_fp)),
            )
            fp.rotation_euler = (0.45 * math.sin(u_fp * 5.0) * (1.0 - u_fp), 0.35 * math.cos(u_fp * 4.0) * (1.0 - u_fp), u_fp * 2.2)
            sc_fp = 0.65 * smoothstep(92.25, 91.95, t)
            fp.scale = (sc_fp, sc_fp, sc_fp)
        else:
            fp.hide_render = True

    # Seamless petal continuity: first 24 petals loosen gently in C5b (33.2..35.0s) -> C6a shore lift (35.0..35.8s)
    # -> 1.0s TRUE GRAVITY FREEZE (35.8..36.8s) -> coherent sweeping helical updraft ribbons (36.8s+)!
    show_petals = (t >= 33.2) and (not in_c7b)
    for po in scene_handles["petals"]:
        t_launch = po["t_launch"]
        if (not show_petals) or (t < t_launch):
            po.hide_render = True
            continue
        po.hide_render = False
        orig = Vector(po["origin"])
        hov = Vector(po["hover"])
        ph = po["phase"]
        sp = po["speed"]
        rid = po["ribbon_id"]
        base_sc = po["base_scale"]

        if t < 35.8:
            # Gentle causal detachment lift straight off the bloomed shore flowers (Slow-Out!)
            u_lift = clamp((t - t_launch) / max(0.35, 35.8 - t_launch), 0.0, 1.0)
            e_lift = 1.0 - (1.0 - u_lift) ** 3
            p_cur = orig.lerp(hov, e_lift)
            x, y, z = p_cur.x, p_cur.y, p_cur.z
            sc_cur = base_sc * smoothstep(0.0, 0.25, u_lift)
            rot = (0.35 * math.sin(t * 1.6 + ph), 0.25 * math.cos(t * 1.3 + ph), ph + u_lift * 1.2)
        elif t < 36.8:
            # 35.8..36.8s: TRUE 1.0-SECOND GRAVITY FREEZE — dead-still suspended breath (tiny 1.5cm float)!
            u_fr = t - 35.8
            env_b = math.sin(u_fr * math.pi)
            x = hov.x + 0.018 * env_b * math.sin(ph)
            y = hov.y + 0.018 * env_b * math.cos(ph)
            z = hov.z + 0.025 * env_b
            sc_cur = base_sc
            rot = (0.35 * math.sin(35.8 * 1.6 + ph) + 0.02 * env_b, 0.25 * math.cos(35.8 * 1.3 + ph), ph + 1.2 + 0.03 * u_fr)
        elif t < 70.0:
            # 36.8s+: Coherent sweeping helical updraft ribbons (all neighboring petals surf the SAME wind stream!)
            u = t - 36.8
            rise = (u ** 1.72) / (1.0 + 0.10 * (u ** 0.72)) * 1.75 * sp
            stream_ang = u * 0.42 + rid * 2.094 + ph * 0.35
            stream_ang0 = rid * 2.094 + ph * 0.35
            swirl_x = 5.2 * (math.sin(stream_ang) - math.sin(stream_ang0)) + 1.45 * smoothstep(0.0, 2.8, u) * u
            swirl_y = 3.6 * (math.cos(stream_ang) - math.cos(stream_ang0)) + 0.95 * smoothstep(0.0, 3.2, u) * u
            x = hov.x + swirl_x
            y = hov.y + swirl_y
            z_raw = hov.z + rise
            if t < 44.0:
                z = z_raw
                if po["layer"] == 0 and z > 18.0:
                    z = 2.0 + ((z - 2.0) % 16.0)
                    sc_cur = base_sc * min(smoothstep(2.0, 4.0, z), smoothstep(18.0, 15.5, z))
                else:
                    sc_cur = base_sc
            else:
                z = 1.0 + ((z_raw - 1.0) % 52.0)
                seam = min(smoothstep(1.0, 3.2, z), smoothstep(53.0, 49.5, z))
                sc_cur = base_sc * seam
            rot = (
                0.65 * math.sin(u * 2.3 * sp + ph),
                0.55 * math.cos(u * 1.9 * sp + ph),
                ph + 1.23 + u * 1.35 * sp,
            )
        else:
            dt_dn = t - 70.0
            z_raw = hov.z + 28.0 - dt_dn * 1.55 * sp
            z = 0.9 + ((z_raw - 0.9) % 44.0)
            x = hov.x + 1.8 * math.sin(dt_dn * 0.55 + ph)
            y = hov.y + 1.1 * math.cos(dt_dn * 0.45 + ph)
            seam = min(smoothstep(0.9, 2.2, z), smoothstep(44.9, 42.5, z))
            sc_cur = base_sc * seam
            rot = (0.40 * math.sin(t * 1.2 + ph), 0.30 * math.cos(t * 0.95 + ph), ph + t * 0.45)

        po.location = (x, y, z)
        po.rotation_euler = rot
        po.scale = (sc_cur, sc_cur, sc_cur)

    # Dedicated C7b lunar-absorption peeling petals: stream UPWARD & DEEPER into the moon heart along whale's wake!
    moon_c = Vector((spec["world"]["moon"]["pos"][0], 76.0, spec["world"]["moon"]["pos"][2]))
    for mp in scene_handles.get("moon_petals", []):
        if not in_c7b:
            mp.hide_render = True
            continue
        u_b = mp["u_body"]
        t_peel = lerp(76.7, 81.5, u_b)
        age = t - t_peel
        if age < 0.0 or age > 2.3:
            mp.hide_render = True
            continue
        ws_p = eval_whale_state(spec, t_peel)
        y_local = lerp(-12.0, 11.5, u_b)
        spawn = ws_p["pos"] + ws_p["fwd"] * y_local + Vector((mp["off_x"], 0.0, mp["off_z"]))
        mp.hide_render = False
        pull_u = smoothstep(0.0, 2.2, age)
        ph = mp["phase"]
        p_cur = spawn.lerp(moon_c, pull_u * 0.62 * mp["pull_speed"])
        p_cur.x += 0.45 * math.sin(age * 2.0 + ph)
        p_cur.z += 0.35 * math.cos(age * 1.8 + ph)
        sc_env = smoothstep(0.0, 0.20, age) * smoothstep(2.3, 1.15, age)
        s_mp = mp["base_scale"] * sc_env * 0.85
        mp.location = p_cur
        mp.scale = (s_mp, s_mp, s_mp)
        mp.rotation_euler = (0.6 * math.sin(age * 2.5 + ph), 0.5 * math.cos(age * 2.0 + ph), ph + age * 1.4)

    # Ambient cool-silver snow petals framing C7b cavern fissure corners & moon rim (keeps 81.4..83.0s alive!)
    m_z = spec["world"]["moon"]["pos"][2]
    for sp_o in scene_handles.get("c7b_snow", []):
        if not in_c7b:
            sp_o.hide_render = True
            continue
        sp_o.hide_render = False
        dt_c = t - 75.0
        ph = sp_o["phase"]
        z_cur = m_z - 14.0 + ((sp_o["sz"] - (m_z - 14.0) - dt_c * sp_o["fall_spd"]) % 29.0)
        x_cur = sp_o["sx"] + 1.1 * math.sin(dt_c * 0.7 + ph)
        y_cur = sp_o["sy"]
        seam_c = min(smoothstep(m_z - 14.0, m_z - 11.5, z_cur), smoothstep(m_z + 15.0, m_z + 12.5, z_cur))
        sc_c = sp_o["base_scale"] * seam_c
        sp_o.location = (x_cur, y_cur, z_cur)
        sp_o.scale = (sc_c, sc_c, sc_c)
        sp_o.rotation_euler = (0.5 * math.sin(dt_c * 1.4 + ph), 0.4 * math.cos(dt_c * 1.1 + ph), ph + dt_c * 0.6)

    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------
# Measured Framing & Grounding QA (cinematic-previs + blender-python-previs)
# ---------------------------------------------------------------------------

def evaluated_world_verts(obj: bpy.types.Object) -> list[Vector]:
    deps = bpy.context.evaluated_depsgraph_get()
    eo = obj.evaluated_get(deps)
    em = eo.to_mesh()
    verts = [obj.matrix_world @ v.co for v in em.vertices]
    eo.to_mesh_clear()
    return verts


def run_measured_qa(scene_handles: dict, spec: dict) -> dict:
    scene = bpy.context.scene
    cam = scene_handles["cam"]
    checks = []
    fails = []

    # 1. Ground contact check on all 4 PCs using evaluated vertices (never bound_box!)
    shore_z = spec["world"]["shore_z"]
    for pc_obj, pc_spec in scene_handles["pcs"]:
        verts = evaluated_world_verts(pc_obj)
        min_z = min(v.z for v in verts)
        err = abs(min_z - shore_z)
        ok = err <= 0.03
        checks.append({"label": f"ground_contact:{pc_spec['id']}", "ok": ok, "min_z": round(min_z, 4), "target_z": shore_z})
        if not ok:
            fails.append(f"{pc_spec['id']} floating/sunk by {err:.3f}m")

    # 2. Shot-by-shot IN / MID / OUT framing & head-crop verification
    for sh in spec["shots"]:
        for tag, tt in (("IN", sh["start"] + 0.3), ("MID", 0.5 * (sh["start"] + sh["end"])), ("OUT", sh["end"] - 0.3)):
            apply_state_at_time(scene_handles, spec, tt)
            row = {"shot": sh["id"], "beat": tag, "t": round(tt, 2), "focal_mm": sh["focal_mm"]}

            if "pcs" in sh.get("subjects", []):
                pc_heads_v = []
                for pc_obj, pc_spec in scene_handles["pcs"]:
                    head_pt = pc_obj.location + Vector((0.0, 0.0, pc_spec["height"]))
                    co = world_to_camera_view(scene, cam, head_pt)
                    pc_heads_v.append((pc_spec["id"], round(co.x, 3), round(co.y, 3), round(co.z, 2)))
                min_head_v = min(h[2] for h in pc_heads_v)
                ok_head = min_head_v >= 0.06  # zero bottom-edge head crop!
                row["pc_heads_min_v"] = min_head_v
                if not ok_head:
                    fails.append(f"{sh['id']}[{tag}] PC head cropped near bottom edge (min_v={min_head_v:.3f})")

            if "whale" in sh.get("subjects", []) and not scene_handles["whale"].hide_render:
                co_w = world_to_camera_view(scene, cam, scene_handles["whale"].location)
                row["whale_uv"] = [round(co_w.x, 3), round(co_w.y, 3)]
                row["whale_depth_m"] = round(co_w.z, 2)
                if sh["id"] == "C7b" and tag == "MID":
                    if not (0.20 <= co_w.x <= 0.80 and 0.25 <= co_w.y <= 0.75 and co_w.z > 0):
                        fails.append(f"C7b[MID] whale off moon center: uv=({co_w.x:.2f},{co_w.y:.2f})")

            checks.append(row)

    report = {
        "status": "PASS" if not fails else f"FAIL ({len(fails)})",
        "fails": fails,
        "clip_count": len(spec["clips"]),
        "max_clip_duration_s": max(c["end"] - c["start"] for c in spec["clips"]),
        "checks": checks,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    QA_REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"QA_REPORT: {QA_REPORT_PATH} -> {report['status']} (max_clip={report['max_clip_duration_s']}s)")
    if fails:
        for f in fails:
            print(f"  FAIL: {f}")
    return report


# ---------------------------------------------------------------------------
# Build Full Scene & Render Commands
# ---------------------------------------------------------------------------

def build_scene_in_current_blender(spec: dict | None = None, quality: str = "preview", set_time: float = 56.0) -> dict:
    spec = spec or json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    clear_scene()

    mats = {
        "whale": make_whale_dissolve_material("MAT-Whale_Clay"),
        "eye": make_whale_eye_material("MAT-Whale_Eye"),
        "pc": make_clay_material("MAT-PC_Silhouette", (0.14, 0.15, 0.18, 1.0), roughness=0.88),
        "stone": make_clay_material("MAT-ArchStone_Clay", (0.36, 0.39, 0.44, 1.0), roughness=0.86, mist_range=(65.0, 210.0)),
        "shore": make_clay_material("MAT-Shore_Clay", (0.30, 0.32, 0.36, 1.0), roughness=0.88),
        "pillar": make_clay_material("MAT-FarPillar_Clay", (0.28, 0.32, 0.38, 1.0), roughness=0.92, mist_range=(75.0, 175.0)),
        "water": make_clay_material("MAT-MirrorLake_Clay", (0.05, 0.08, 0.13, 1.0), roughness=0.04, mist_range=(85.0, 220.0)),
        "moon": make_clay_material("MAT-FullMoon", (0.98, 0.98, 0.95, 1.0), roughness=0.9, emission_color=(0.98, 0.98, 0.95, 1.0), emission_strength=1.78),
        "fissure": make_clay_material("MAT-CeilingFissure", (0.04, 0.05, 0.075, 1.0), roughness=0.96),
        "shaft": make_soft_beam_material("MAT-MoonShaft"),
        "lantern_metal": make_clay_material("MAT-LanternMetal", (0.24, 0.22, 0.18, 1.0), roughness=0.65, metallic=0.4),
        "lantern_glow": make_clay_material("MAT-LanternGlow", (1.0, 0.92, 0.72, 1.0), roughness=0.4, emission_color=(1.0, 0.92, 0.72, 1.0), emission_strength=4.2),
        "flower": make_clay_material("MAT-Flower_Clay", (0.92, 0.94, 0.97, 1.0), roughness=0.70, emission_color=(0.92, 0.94, 0.98, 1.0), emission_strength=0.22),
        "moon_petal": make_clay_material("MAT-MoonPetal_Glow", (0.62, 0.72, 0.86, 1.0), roughness=0.65, emission_color=(0.68, 0.78, 0.94, 1.0), emission_strength=0.72),
        "bud": make_clay_material("MAT-Bud_Clay", (0.42, 0.39, 0.35, 1.0), roughness=0.86),
        "bloom": make_bloom_transition_material("MAT-Kousetsuka_Bloom"),
    }

    whale, whale_base, whale_eyes = build_anatomical_whale(mats["whale"], mats["eye"])
    pcs = [(build_grounded_adventurer(pc, mats["pc"]), pc) for pc in spec["world"]["pcs"]]
    env = build_environment(spec, mats)
    awaken_light = setup_lighting_and_world(spec)

    # Camera + Track-To Empty rig (cinematic-previs & cc-blender-skill standard)
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
        "awaken_light": awaken_light,
        "pcs": pcs, **env,
    }
    apply_state_at_time(handles, spec, set_time)
    return handles


def render_still(handles: dict, spec: dict, t: float, out_path: Path):
    scene = bpy.context.scene
    if scene.camera is None:
        raise RuntimeError("Camera guard failed: scene.camera is None")
    apply_state_at_time(handles, spec, t)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)
    print(f"RENDERED_STILL: {out_path}")


def render_clip_mp4(handles: dict, spec: dict, clip_id: str, overwrite: bool = False, samples: int | None = None):
    cl = next((c for c in spec["clips"] if c["id"] == clip_id), None)
    if cl is None:
        raise SystemExit(f"Unknown clip-id '{clip_id}'. Available: {[c['id'] for c in spec['clips']]}")
    scene = bpy.context.scene
    prev_samples = scene.cycles.samples if scene.render.engine == "CYCLES" else None
    prev_mb = scene.render.use_motion_blur
    if samples is not None and scene.render.engine == "CYCLES":
        scene.cycles.samples = samples
    scene.render.use_motion_blur = False
    try:
        fps = spec["fps"]
        f0 = int(round(cl["start"] * fps))
        f1 = int(round(cl["end"] * fps))
        dur = int(round(cl["end"] - cl["start"]))
        import tempfile
        CLIPS_DIR.mkdir(parents=True, exist_ok=True)
        seq_dir = Path(tempfile.gettempdir()) / "ruosuen_v6_seq" / f"_seq_{clip_id}"
        if overwrite and seq_dir.exists():
            shutil.rmtree(seq_dir)
        seq_dir.mkdir(parents=True, exist_ok=True)

        total = f1 - f0
        for idx, fi in enumerate(range(f0, f1)):
            t = fi / fps
            frame_png = seq_dir / f"frame_{idx:04d}.png"
            if overwrite or not frame_png.exists():
                apply_state_at_time(handles, spec, t)
                scene.render.filepath = str(frame_png)
                bpy.ops.render.render(write_still=True)
            if (idx + 1) % 48 == 0 or (idx + 1) == total:
                print(f"CLIP_{clip_id}: {idx + 1}/{total} frames")

        out_mp4 = CLIPS_DIR / f"v6_clay_{clip_id}_{dur}s.mp4"
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise SystemExit("ffmpeg not found on PATH; PNG sequence saved at " + str(seq_dir))
        subprocess.check_call([
            ffmpeg, "-y", "-v", "error",
            "-framerate", str(fps),
            "-i", str(seq_dir / "frame_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-movflags", "+faststart",
            str(out_mp4),
        ])
        print(f"ENCODED_CLIP: {out_mp4} ({total} frames, {dur}s)")
        return out_mp4
    finally:
        if prev_samples is not None:
            scene.cycles.samples = prev_samples
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
        "-vf", f"scale=480:270,tile={cols}x{rows}:padding=8:margin=12:color=0x10141c",
        "-frames:v", "1",
        str(out_path),
    ])
    list_txt.unlink(missing_ok=True)
    print(f"CONTACT_SHEET: {out_path}")


def render_full_film(handles: dict, spec: dict, overwrite: bool = False, samples: int = 12, res_scale: int = 100):
    """Render all 14 <=9s clips (2,304 frames = 96.0s exact) and stitch v6_full_96s_clay_previs.mp4
    with live progress.json updates (designed for headless RTX 3060 batch execution)."""
    import time as _time
    scene = bpy.context.scene
    scene.render.resolution_percentage = res_scale
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = samples
    scene.render.use_motion_blur = False

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
            "status": status,
            "current_clip": cur_clip,
            "done_frames": done_frames,
            "total_frames": total_frames,
            "pct": round(100.0 * done_frames / total_frames, 1),
            "elapsed_s": round(elapsed, 1),
            "eta_s": round(eta, 1),
            "engine": scene.render.engine,
            "samples": samples,
            "res_scale": res_scale,
        }, indent=2), encoding="utf-8")

    write_prog("running", spec["clips"][0]["id"])
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg not found on PATH")

    import tempfile
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    for cl in spec["clips"]:
        cid = cl["id"]
        f0 = int(round(cl["start"] * fps))
        f1 = int(round(cl["end"] * fps))
        dur = int(round(cl["end"] - cl["start"]))
        seq_dir = Path(tempfile.gettempdir()) / "ruosuen_v6_seq" / f"_seq_{cid}"
        if overwrite and seq_dir.exists():
            shutil.rmtree(seq_dir)
        seq_dir.mkdir(parents=True, exist_ok=True)
        for idx, fi in enumerate(range(f0, f1)):
            t = fi / fps
            frame_png = seq_dir / f"frame_{idx:04d}.png"
            if overwrite or not frame_png.exists():
                apply_state_at_time(handles, spec, t)
                scene.render.filepath = str(frame_png)
                bpy.ops.render.render(write_still=True)
            done_frames += 1
            if done_frames % 24 == 0 or done_frames == total_frames:
                write_prog("running", cid)
        out_mp4 = CLIPS_DIR / f"v6_clay_{cid}_{dur}s.mp4"
        subprocess.check_call([
            ffmpeg, "-y", "-v", "error",
            "-framerate", str(fps),
            "-i", str(seq_dir / "frame_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-movflags", "+faststart",
            str(out_mp4),
        ])
        clip_mp4s.append(out_mp4)
        print(f"CLIP_DONE: {out_mp4.name} ({done_frames}/{total_frames})")

    # Stitch all 14 clips into the complete 96.0s continuous film with serene 1.4s fade-to-black at 94.6..96.0s
    list_txt = OUT_DIR / "full_concat.txt"
    list_txt.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in clip_mp4s) + "\n", encoding="utf-8")
    full_mp4 = OUT_DIR / "v6_full_96s_clay_previs.mp4"
    subprocess.check_call([
        ffmpeg, "-y", "-v", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_txt),
        "-vf", "fade=t=out:st=94.6:d=1.4",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-movflags", "+faststart",
        str(full_mp4),
    ])
    list_txt.unlink(missing_ok=True)
    # Auto-mux 96s master audio WAV if found in parent Ruosuen_Render/ or sibling v5 audio folder!
    wav_cands = list(ROOT.parent.rglob("kousetsuka_v5_master_audio_96s.wav"))
    if wav_cands:
        audio_mp4 = OUT_DIR / "v6_full_96s_clay_previs_with_audio.mp4"
        subprocess.check_call([
            ffmpeg, "-y", "-v", "error",
            "-i", str(full_mp4), "-i", str(wav_cands[0]),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
            "-movflags", "+faststart", str(audio_mp4),
        ])
        top_copy = ROOT.parent / f"v{spec.get('version','6').replace('.','_')}_full_96s_clay_previs_with_audio.mp4"
        shutil.copy2(audio_mp4, top_copy)
        print(f"MUXED_FULL_AUDIO: {audio_mp4} & {top_copy}")
    write_prog("done", "ALL")
    print(f"FULL_FILM_DONE: {full_mp4} elapsed={_time.time() - t_start:.1f}s")
    return full_mp4


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["look", "qa", "stills", "clip", "full_film"], default="look")
    ap.add_argument("--quality", choices=["preview", "cycles"], default="preview")
    ap.add_argument("--clip-id", default="C1")
    ap.add_argument("--samples", type=int, default=12)
    ap.add_argument("--res-scale", type=int, default=100)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args(argv)

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    handles = build_scene_in_current_blender(spec, quality=args.quality, set_time=56.0)

    if args.mode == "look":
        for name, tt in (("look_01_C2_shore_pcs.png", 9.0), ("look_02_C6c_grand_abyss.png", 56.0), ("look_03_C7b_moon_dissolve.png", 78.5)):
            render_still(handles, spec, tt, LOOK_DIR / name)
        blend_out = OUT_DIR / "v6_clay_previs.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))
        print(f"SAVED_BLEND: {blend_out}")
    elif args.mode == "qa":
        report = run_measured_qa(handles, spec)
        if report["fails"]:
            raise SystemExit(1)
    elif args.mode == "stills":
        run_measured_qa(handles, spec)
        one_per_shot = []
        for sh in spec["shots"]:
            mid_t = 0.5 * (sh["start"] + sh["end"])
            if sh["id"] == "C7b":
                mid_t = 78.5
            p = STILLS_DIR / f"{sh['id']}_mid.png"
            render_still(handles, spec, mid_t, p)
            one_per_shot.append(p)
        p_end = STILLS_DIR / "C7b_head_last.png"
        render_still(handles, spec, 80.5, p_end)
        one_per_shot.append(p_end)
        build_contact_sheet_ffmpeg(one_per_shot, 4, 4, STILLS_DIR / "one_per_shot_v6.png")
    elif args.mode == "clip":
        render_clip_mp4(handles, spec, args.clip_id, overwrite=args.overwrite, samples=args.samples)
    elif args.mode == "full_film":
        render_full_film(handles, spec, overwrite=args.overwrite, samples=args.samples, res_scale=args.res_scale)


if __name__ == "__main__":
    main()
