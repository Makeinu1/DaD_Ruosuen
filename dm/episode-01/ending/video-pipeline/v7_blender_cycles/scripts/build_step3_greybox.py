#!/usr/bin/env python3
"""
V7 Step 3 (Rev C — Final Greybox): High-Craft Natural Basalt Matte-Grey 3D Greybox (Gate 3).
Fixes both Rev B findings cleanly:
  1. Canyon fissure rims flare OUTWARD toward the sky (ZERO inward pinch!), revealing the 100% unobstructed
     circular Full Moon inside a soaring V-shaped jagged vertical canyon cleft!
  2. High-res tapered natural rock headlands (ZERO low-poly box tops!) + terraced foreground S1 shore ledges
     clearly visible across the lower ~18% of ALL 6 frames alongside the 24m whale & 450m enclosed cavern!
"""

import math
import time
from pathlib import Path

import bpy
import bmesh
from mathutils import Euler, Vector

# ==============================================================================
# SINGLE MASTER CONFIG BLOCK (Infographic §06)
# ==============================================================================
CONFIG = {
    "render_res": (960, 540),
    "samples": 8,
    "fissure_x_center": 4.0,
    "fissure_y_range": (28.0, 235.0),
    "fissure_half_width": 26.0,
    "ceiling_max_z": 185.0,
    "moon_pos": (4.0, 185.0, 228.0),
    "moon_radius": 14.0,
    "whale_scale": 1.0,  # Exact canon 24.28m WH-01 v2.0!
    "shots": [
        ("01_opening_00s",  0.0,  "00.0s OPENING (Cam A 20mm) - Enclosed Wide Cavern + Canyon Moon + S1 Shore",   0.0,   0.0,   0.0),
        ("02_breach_21s",  21.6,  "21.6s BREACH (24m Whale Emerging from Obsidian Lake Z=0)",                      24.0,  28.0,  -8.0),
        ("03_heigei_26s",  26.0,  "26.0s HEIGEI (24m Whale 3/4 Downward Calm Gaze over S1 Shore)",               -130.0, -10.0,  10.0),
        ("04_ignite_31s",  31.5,  "31.5s IGNITE (Ascending Directly into Vertical Canyon Moonbeam)",               28.0,  24.0,  -8.0),
        ("05_soar_42s",    42.0,  "42.0s OPAL SOAR (Heroic 24m Aerial Bank Across Wide 450m Cavern)",              18.0,  12.0, -14.0),
        ("06_exitc_58s",   58.0,  "58.0s EXIT C (Occluded Behind R1 Basalt Headland, Cam A Fixed)",                20.0,  -4.0,  -6.0),
    ],
}

REPO = Path("/home/antigravity/Makeinu1/DaD_Ruosuen")
WHALE_GLB = REPO / "dm/episode-01/ending/video-pipeline/v2/assets/processed/wh01_v20_hero.glb"
V7_DIR = REPO / "dm/episode-01/ending/video-pipeline/v7_blender_cycles"
OUT_DIR = V7_DIR / "out/step3_greybox"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ART_DIR = Path("/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/4733e009-f44e-4728-af83-1f85c37a4d1d")


def catmull_rom(pts, t_norm):
    n = len(pts) - 1
    u = max(0.0, min(1.0, t_norm)) * n
    i = min(int(math.floor(u)), n - 1)
    f = u - i
    p0 = Vector(pts[max(0, i - 1)])
    p1 = Vector(pts[i])
    p2 = Vector(pts[min(n, i + 1)])
    p3 = Vector(pts[min(n, i + 2)])
    f2 = f * f
    f3 = f2 * f
    return 0.5 * (
        (2.0 * p1)
        + (-p0 + p2) * f
        + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * f2
        + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * f3
    )


def whale_pos_at(t_sec: float) -> Vector:
    keyframes = [
        (0.0,  -38.0,  28.0, -14.0),
        (12.0, -22.0,  10.0,  -6.0),
        (17.0, -12.0,  -4.0,  -2.0),
        (21.6,  -5.0,  -4.0,   9.0),
        (26.0,   1.0,  -6.0,  15.5),
        (31.5,   4.0,  12.0,  25.5),
        (36.0,   2.0,  22.0,  31.0),
        (42.0,  -2.0,  16.0,  29.0),
        (48.0,  18.0,  32.0,  30.0),
        (54.0,  72.0,  62.0,  24.0),
        (60.0, 128.0,  95.0,  20.0),
    ]
    ts = [k[0] for k in keyframes]
    pts = [k[1:] for k in keyframes]
    if t_sec <= ts[0]:
        u = 0.0
    elif t_sec >= ts[-1]:
        u = 1.0
    else:
        u = 0.0
        for idx in range(len(ts) - 1):
            if ts[idx] <= t_sec <= ts[idx + 1]:
                u = (idx + (t_sec - ts[idx]) / (ts[idx + 1] - ts[idx])) / (len(ts) - 1)
                break
    p = catmull_rom(pts, u)
    if t_sec > 17.0:
        p.z += 0.55 * math.sin((t_sec - 17.0) * 0.72)
    return p


def camera_at(t_sec: float):
    # 20mm ultra-wide cinema lens frames ALL 3 planes: S1 shore (lower 18%) + 450m cavern/24m whale (mid) + Full Moon Canyon (top 22%)!
    if t_sec < 17.0:
        pos = Vector((-10.0, -62.0, 5.2))
        focal = 20.0
    elif t_sec < 29.0:
        a = (t_sec - 17.0) / 12.0
        s = a * a * (3.0 - 2.0 * a)
        pos = Vector((-10.0 + 2.5 * s, -62.0 + 4.5 * s, 5.2 + 0.6 * s))
        focal = 20.0 + 2.8 * s
    elif t_sec < 51.0:
        a = (t_sec - 29.0) / 22.0
        s = a * a * (3.0 - 2.0 * a)
        pos = Vector((-7.5 - 2.5 * s, -57.5 - 4.5 * s, 5.8 - 0.6 * s))
        focal = 22.8 - 2.8 * s
    else:
        pos = Vector((-10.0, -62.0, 5.2))
        focal = 20.0

    target = Vector((4.0, 48.0, 31.0))
    return pos, target, focal


def angular_basalt_noise(x: float, y: float, z: float, seed: float = 0.0) -> float:
    s_raw = math.sin(z * 0.14 + 0.30 * math.sin(x * 0.035 + y * 0.03 + seed))
    strata = math.copysign(abs(s_raw) ** 0.50, s_raw)
    col = 1.0 - 2.0 * abs(math.sin(x * 0.065 - y * 0.05 + seed) * math.cos(y * 0.06 + x * 0.045))
    crag = 1.0 - 2.0 * abs(math.sin(x * 0.19 + y * 0.16 - z * 0.18 + seed * 1.9))
    return strata * 0.42 + col * 0.36 + crag * 0.22


def make_clay_mat(name: str, rgba, roughness: float = 0.82, emission: float = 0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = roughness
    if emission > 0.0:
        bsdf.inputs["Emission Color"].default_value = rgba
        bsdf.inputs["Emission Strength"].default_value = emission
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def resample_polyline(pts, n_out: int):
    res = []
    n_seg = len(pts) - 1
    for i in range(n_out):
        u = i / (n_out - 1) * n_seg
        idx = min(int(math.floor(u)), n_seg - 1)
        f = u - idx
        x = pts[idx][0] * (1.0 - f) + pts[idx + 1][0] * f
        y = pts[idx][1] * (1.0 - f) + pts[idx + 1][1] * f
        res.append((x, y))
    return res


def build_natural_cliff_ridge(name: str, pts_xy, z_base: float, z_top: float, seed: float, mat_rock, taper_top: bool = False):
    """High-res natural volcanic basalt cliff wall / rocky headland cape (ZERO low-poly box blocks!)."""
    pts = resample_polyline(pts_xy, 36)
    bm = bmesh.new()
    n_seg = len(pts)
    n_z = 26
    grid = []
    for k in range(n_z):
        tz = k / (n_z - 1)
        row = []
        for m in range(n_seg):
            tm = m / (n_seg - 1)
            x0, y0 = pts[m]
            # Natural mountain ridge height profile if taper_top=True (peaks organically instead of flat box top!)
            h_env = (0.35 + 0.65 * math.sin(tm * math.pi) ** 0.6) if taper_top else 1.0
            z = z_base + (z_top - z_base) * h_env * tz
            crag = 6.2 * angular_basalt_noise(x0, y0, z, seed)
            to_c = Vector((0.0 - x0, 60.0 - y0)).normalized()
            # Natural sloped talus skirt at base, craggy receding cliff face upward
            slope_back = -18.0 * (tz ** 1.35) if taper_top else -6.0 * (tz ** 1.4)
            px = x0 + to_c.x * (crag + slope_back)
            py = y0 + to_c.y * (crag + slope_back)
            row.append(bm.verts.new((px, py, z)))
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


def build_enclosed_canyon_cavern(mat_rock, mat_shore):
    fx_c = CONFIG["fissure_x_center"]
    fy0, fy1 = CONFIG["fissure_y_range"]
    f_hw = CONFIG["fissure_half_width"]
    z_max = CONFIG["ceiling_max_z"]

    # 1. 100% Enclosed 450m x 620m Cavern Vault with wide soaring overhead V-Canyon Fissure
    bm = bmesh.new()
    nu, nv = 128, 64
    cx, cy = 0.0, 170.0
    rx, ry = 225.0, 310.0

    sgrid = []
    for j in range(nv):
        phi = -0.06 + (math.pi * 0.495 + 0.06) * (j / (nv - 1))
        cp = max(0.0, math.cos(phi))
        sp = math.sin(phi)
        row = []
        for i in range(nu):
            theta = 2.0 * math.pi * i / nu
            px = cx + rx * cp * math.cos(theta)
            py = cy + ry * cp * math.sin(theta)
            north_lift = 0.62 + 0.38 * max(0.0, min(1.0, (py + 90.0) / 260.0))
            pz = -12.0 + (z_max * north_lift) * (max(0.0, sp) ** 0.72 if sp >= 0 else sp * 0.4)
            disp = 12.0 * angular_basalt_noise(px, py, pz, 3.1) * (0.35 + 0.65 * cp)
            px -= math.cos(theta) * cp * disp
            py -= math.sin(theta) * cp * disp
            pz += sp * disp * 0.38
            row.append(bm.verts.new((px, py, pz)))
        sgrid.append(row)

    cut_n = 0
    for j in range(nv - 1):
        for i in range(nu):
            inext = (i + 1) % nu
            v0, v1, v2, v3 = sgrid[j][i], sgrid[j][inext], sgrid[j + 1][inext], sgrid[j + 1][i]
            fc = (v0.co + v1.co + v2.co + v3.co) * 0.25
            if fc.z > 62.0 and fy0 <= fc.y <= fy1:
                t_y = (fc.y - fy0) / max(1.0, (fy1 - fy0))
                env_w = (0.45 + 0.85 * (t_y ** 0.55)) * math.sin(min(1.0, t_y * 1.05) * math.pi) ** 0.30
                jagged = 1.0 + 0.20 * math.sin(fc.y * 0.11 + 0.4) + 0.10 * math.cos(fc.y * 0.23 - 0.7)
                if abs(fc.x - fx_c) < (f_hw * env_w * jagged):
                    cut_n += 1
                    continue
            bm.faces.new((v0, v3, v2, v1))

    me_cav = bpy.data.meshes.new("V7_EnclosedCavernVault")
    bm.to_mesh(me_cav)
    bm.free()
    me_cav.polygons.foreach_set("use_smooth", [True] * len(me_cav.polygons))
    ob_cav = bpy.data.objects.new("V7_EnclosedCavernVault", me_cav)
    ob_cav.data.materials.append(mat_rock)
    bpy.context.collection.objects.link(ob_cav)
    print(f"[GREYBOX] Built 100% enclosed 450x620m cavern vault (overhead V-canyon fissure: {cut_n} quads)")

    # 2. Outward-Flaring Jagged Vertical Canyon Fissure Cliffs (ZERO inward pinch -> Full Moon 100% unobstructed!)
    for side in (-1.0, 1.0):
        bm = bmesh.new()
        ny_r, nz_r = 34, 14
        grid = []
        for k in range(nz_r):
            tz = k / (nz_r - 1)  # 0 = lower vault lip .. 1 = high sky crest
            row = []
            for m in range(ny_r):
                ty = m / (ny_r - 1)
                py = fy0 + (fy1 - fy0) * ty
                env_w = (0.45 + 0.85 * (ty ** 0.55)) * math.sin(min(1.0, ty * 1.05) * math.pi) ** 0.30
                jagged = 1.0 + 0.20 * math.sin(py * 0.11 + 0.4) + 0.10 * math.cos(py * 0.23 - 0.7)
                # Flare OUTWARD as tz increases (true V-shaped natural canyon gorge opening to the Full Moon!)
                px = fx_c + side * (f_hw * env_w * jagged + 16.0 * (tz ** 1.15))
                base_z = 88.0 + 78.0 * ty
                pz = base_z - 10.0 + tz * 58.0
                crag = 4.5 * angular_basalt_noise(px, py, pz, side * 7.3)
                row.append(bm.verts.new((px + side * crag * 0.4, py, pz + crag * 0.3)))
            grid.append(row)
        for k in range(nz_r - 1):
            for m in range(ny_r - 1):
                if side > 0:
                    bm.faces.new((grid[k][m], grid[k][m+1], grid[k+1][m+1], grid[k+1][m]))
                else:
                    bm.faces.new((grid[k][m], grid[k+1][m], grid[k+1][m+1], grid[k][m+1]))
        me = bpy.data.meshes.new(f"CanyonRimGorge_{'R' if side > 0 else 'L'}")
        bm.to_mesh(me)
        bm.free()
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        ob = bpy.data.objects.new(me.name, me)
        ob.data.materials.append(mat_rock)
        bpy.context.collection.objects.link(ob)

    # 3. Wide Receding Natural Basalt Cliffs & Tapered Canon R1 Exit-C Headland Cape
    build_natural_cliff_ridge("Cliff_L_Near", [(-82, -55), (-98, -15), (-125, 25), (-155, 65)], -6.0, 155.0, 11.2, mat_rock, taper_top=False)
    build_natural_cliff_ridge("Cliff_L_Mid",  [(-102, 85), (-120, 135), (-142, 185)], -6.0, 165.0, 23.4, mat_rock, taper_top=False)
    build_natural_cliff_ridge("Cliff_L_Far",  [(-130, 225), (-78, 285), (-15, 330)], -6.0, 175.0, 35.6, mat_rock, taper_top=False)
    build_natural_cliff_ridge("Cliff_R_Near", [(148, 50), (118, 12), (96, -22), (82, -55)], -6.0, 155.0, 47.8, mat_rock, taper_top=False)
    # Tapered natural mountain headland on far right for Canon Exit C (X=64..155m, Y=54..115m)
    build_natural_cliff_ridge("Canon_R1_ExitHeadland", [(158, 72), (110, 56), (66, 56), (62, 82), (84, 124)], -6.0, 94.0, 59.1, mat_rock, taper_top=True)
    build_natural_cliff_ridge("Cliff_R_Far",  [(22, 330), (88, 282), (145, 212)], -6.0, 175.0, 71.3, mat_rock, taper_top=False)

    # 4. Foreground Terraced Rocky Shore S1 (clearly visible across lower 18% of ALL 6 frames!)
    bm = bmesh.new()
    nx, ny = 96, 64
    xs = [-110.0 + 220.0 * i / (nx - 1) for i in range(nx)]
    ys = [-82.0 + 92.0 * j / (ny - 1) for j in range(ny)]
    grid = []
    for y in ys:
        row = []
        for x in xs:
            # Curved natural rocky shoreline cradling the lake at Y=-26..-32m, rising cleanly on foreground flanks!
            y_shore = -24.0 + 0.0045 * (x * x) + 4.0 * math.sin(x * 0.068 + 0.3)
            d = y_shore - y
            if d <= -5.0:
                z = -8.0
            else:
                t = max(0.0, min(1.0, (d + 5.0) / 30.0))
                st = t * t * (3.0 - 2.0 * t)
                z = -2.4 + st * 9.0
                if z > 0.2:
                    step = math.floor(z / 0.85)
                    frac = (z / 0.85) - step
                    z = z * 0.45 + (step + (frac ** 2.6)) * 0.85 * 0.55
                z += 0.52 * angular_basalt_noise(x * 1.8, y * 1.8, z, 9.1)
                # Keep Cam A (-10, -62, 5.2m) vantage cleanly above while S1 terraced ledges sit at Z=2.2..3.6m in lower 18%!
                if abs(x + 6.0) < 34.0 and -68.0 < y < -24.0:
                    z = min(z, 2.35 + 0.065 * max(0.0, -34.0 - y)) + 0.24 * angular_basalt_noise(x * 2.2, y * 2.2, 0.0, 9.1)
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(ny - 1):
        for i in range(nx - 1):
            bm.faces.new((grid[j][i], grid[j][i+1], grid[j+1][i+1], grid[j+1][i]))
    me_sh = bpy.data.meshes.new("V7_ShoreTerrace_S1")
    bm.to_mesh(me_sh)
    bm.free()
    me_sh.polygons.foreach_set("use_smooth", [True] * len(me_sh.polygons))
    ob_sh = bpy.data.objects.new("V7_ShoreTerrace_S1", me_sh)
    ob_sh.data.materials.append(mat_shore)
    bpy.context.collection.objects.link(ob_sh)


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = CONFIG["samples"]
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.05
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 3
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2
    sc.render.use_persistent_data = False

    sc.render.resolution_x, sc.render.resolution_y = CONFIG["render_res"]
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"

    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Base Contrast"
    except Exception:
        pass
    sc.view_settings.exposure = 0.35

    world = bpy.data.worlds.new("Greybox_World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.06, 0.11, 0.22, 1.0)
    bg.inputs["Strength"].default_value = 2.0

    mat_rock  = make_clay_mat("Mat_Greybox_Rock",  (0.22, 0.25, 0.30, 1.0), roughness=0.86)
    mat_shore = make_clay_mat("Mat_Greybox_Shore", (0.28, 0.34, 0.31, 1.0), roughness=0.88)
    mat_water = make_clay_mat("Mat_Greybox_Water", (0.05, 0.08, 0.12, 1.0), roughness=0.05)
    mat_whale = make_clay_mat("Mat_Greybox_Whale", (0.60, 0.65, 0.72, 1.0), roughness=0.42)
    mat_moon  = make_clay_mat("Mat_Greybox_Moon",  (0.96, 0.98, 1.00, 1.0), roughness=1.0, emission=20.0)
    mat_p0    = make_clay_mat("Mat_Greybox_P0",    (0.96, 0.86, 0.45, 1.0), roughness=0.5, emission=4.5)

    build_enclosed_canyon_cavern(mat_rock, mat_shore)

    bpy.ops.mesh.primitive_plane_add(size=750.0, location=(0.0, 180.0, 0.0))
    lake = bpy.context.active_object
    lake.name = "V7_UndergroundLake_Z0"
    lake.data.materials.append(mat_water)

    bpy.ops.mesh.primitive_uv_sphere_add(segments=36, ring_count=18, radius=CONFIG["moon_radius"], location=CONFIG["moon_pos"])
    moon = bpy.context.active_object
    moon.name = "V7_FullMoon"
    moon.data.materials.append(mat_moon)

    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=2.8, depth=0.14, location=(2.0, -34.0, 2.55))
    p0_ob = bpy.context.active_object
    p0_ob.name = "V7_P0_Marker"
    p0_ob.data.materials.append(mat_p0)

    bpy.ops.import_scene.gltf(filepath=str(WHALE_GLB))
    whale = None
    for ob in bpy.data.objects:
        if ob.type == "MESH" and "WH01" in ob.name:
            whale = ob
            break
    whale.rotation_mode = "XYZ"
    whale.scale = (CONFIG["whale_scale"],) * 3
    whale.data.materials.clear()
    whale.data.materials.append(mat_whale)

    sun_d = bpy.data.lights.new("Key_MoonSun", type="SUN")
    sun_d.energy = 3.8
    sun_d.angle = math.radians(3.0)
    sun_o = bpy.data.objects.new("Key_MoonSun", sun_d)
    bpy.context.collection.objects.link(sun_o)
    moon_vec = Vector(CONFIG["moon_pos"]) - Vector((2.0, -34.0, 2.5))
    sun_o.rotation_euler = moon_vec.to_track_quat("Z", "Y").to_euler()

    fill_d = bpy.data.lights.new("Fill_CavernAmbient", type="AREA")
    fill_d.energy = 165000.0
    fill_d.size = 160.0
    fill_d.color = (0.72, 0.84, 1.0)
    fill_o = bpy.data.objects.new("Fill_CavernAmbient", fill_d)
    fill_o.location = (0.0, 40.0, 120.0)
    bpy.context.collection.objects.link(fill_o)

    cam_d = bpy.data.cameras.new("V7_MainCam")
    cam_d.sensor_width = 36.0
    cam_d.clip_start = 0.5
    cam_d.clip_end = 1200.0
    cam_o = bpy.data.objects.new("V7_MainCam", cam_d)
    bpy.context.collection.objects.link(cam_o)
    sc.camera = cam_o

    return sc, cam_o, whale


def render_all():
    t0 = time.time()
    sc, cam_o, whale = setup_scene()

    blend_path = V7_DIR / "v7_greybox_master.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[GREYBOX] Saved {blend_path} ({blend_path.stat().st_size / (1024*1024):.2f} MB)")

    rendered = []
    for slug, t_sec, label, yaw, pitch, roll in CONFIG["shots"]:
        c_pos, c_tgt, focal = camera_at(t_sec)
        cam_o.location = c_pos
        cam_o.data.lens = focal
        cam_o.rotation_euler = (c_tgt - c_pos).to_track_quat("-Z", "Y").to_euler()

        w_pos = whale_pos_at(t_sec)
        whale.location = w_pos
        whale.rotation_euler = Euler((math.radians(roll), math.radians(-pitch), math.radians(yaw)), "XYZ")

        out_png = OUT_DIR / f"greybox_{slug}.png"
        sc.render.filepath = str(out_png)
        t_s = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[GREYBOX] {slug} ({t_sec:.1f}s) rendered in {time.time() - t_s:.1f}s -> {out_png.name}")
        rendered.append((out_png, label))

    from PIL import Image, ImageDraw
    tw, th = 640, 360
    sheet = Image.new("RGB", (tw * 3, th * 2), (8, 12, 20))
    dr = ImageDraw.Draw(sheet)
    for idx, (fp, lbl) in enumerate(rendered):
        r, c = divmod(idx, 3)
        im = Image.open(fp).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        sheet.paste(im, (c * tw, r * th))
        dr.rectangle([c * tw, r * th, c * tw + 640, r * th + 24], fill=(0, 0, 0))
        dr.text((c * tw + 8, r * th + 6), lbl, fill=(210, 240, 255))
    sheet_path = OUT_DIR / "v7_step3_greybox_6sheet.png"
    sheet.save(sheet_path, "PNG", compress_level=4)
    (ART_DIR / sheet_path.name).write_bytes(sheet_path.read_bytes())
    for fp, _ in [rendered[2], rendered[4]]:
        (ART_DIR / fp.name).write_bytes(fp.read_bytes())
    print(f"[GREYBOX DONE] All 6 Rev-C frames + sheet finished in {time.time() - t0:.1f}s!")


if __name__ == "__main__":
    render_all()
