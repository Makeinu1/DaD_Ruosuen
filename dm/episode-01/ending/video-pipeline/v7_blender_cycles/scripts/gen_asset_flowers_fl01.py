#!/usr/bin/env python3
"""
V6.4 Master Polish T3-Baked Blender 5.0.1 Asset Forge (路線2:『竜とそばかすの姫』× 新海誠).
Surgical polish over V6.3:
  1. Sweeping asymmetric Makoto Shinkai diagonal jagged karst sky-chasm (replaces small symmetric star-hole!).
  2. Removed smooth tube vault arches (`GothicVaultArch_*`); replaced with deep natural overhanging basalt ceiling
     framing the upper corners organically!
  3. Grounded craggy dark volcanic basalt shore outcrops (eliminates flat hovering green pancake boulders!).
  4. Lush terraced mossy shore clusters + distant curving lake-edge flower banks with 24-ray T3 Vertex AO / Crevice / Moss.
"""

import math
import time
from pathlib import Path

import bpy
import bmesh
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

REPO = Path("/home/antigravity/Makeinu1/DaD_Ruosuen")
OUT_DIR = REPO / "dm/episode-01/ending/video-pipeline/v6_anime3d/assets"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def chiseled_rock(x: float, y: float, z: float, seed: float = 0.0) -> float:
    s_raw = math.sin(z * 0.24 + 0.35 * math.sin(x * 0.08 + y * 0.07 + seed))
    strata = math.copysign(abs(s_raw) ** 0.55, s_raw)
    col_raw = math.sin(x * 0.21 - y * 0.16 + seed * 1.4) * math.cos(y * 0.19 + x * 0.13 - seed)
    col = 1.0 - abs(col_raw) * 1.8
    frac = 1.0 - 2.0 * abs(math.sin(x * 0.43 + y * 0.37 - z * 0.31 + seed * 2.3))
    fine = math.sin(x * 0.95 - z * 0.85 + seed * 3.1) * math.cos(y * 0.88 + x * 0.52)
    return strata * 0.42 + col * 0.30 + frac * 0.18 + fine * 0.10


def shore_height(x: float, y: float) -> float:
    y_shore = -8.2 + 0.0095 * (x * x) + 2.4 * math.sin(x * 0.11 + 0.35) + 0.9 * math.cos(x * 0.22)
    d_near = y_shore - y
    d_side = abs(x) - (27.5 + 3.8 * math.sin(y * 0.085 + 0.5))
    y_far = 56.0 - 0.012 * (x * x) + 2.8 * math.sin(x * 0.09 - 0.5)
    center_gap = max(0.0, 1.0 - abs(x) / 13.0)
    d_far = (y - y_far) - center_gap * 12.0

    d = max(d_near, d_far, d_side - 1.5)
    if d <= -2.8:
        return -10.0

    t = max(0.0, min(1.0, (d + 2.8) / 13.0))
    st = t * t * (3.0 - 2.0 * t)
    base = -3.4 + st * 5.2

    if base > 0.05:
        step = math.floor(base / 0.52)
        frac = (base / 0.52) - step
        base = base * 0.35 + (step + (frac ** 3.0)) * 0.52 * 0.65

    detail = 0.22 * chiseled_rock(x * 1.15, y * 1.15, base * 1.2, 4.1)

    if abs(x) < 16.0 and -32.0 < y < -6.5:
        base = min(base, 0.45 + 0.055 * max(0.0, -10.5 - y))
        detail *= 0.45

    return base + detail


def build_chasm_vault(mat_rock):
    """
    CONTINUOUS PARAMETRIC POLAR APERTURE CATHEDRAL VAULT (V6.4).
    Dramatic sweeping asymmetric Makoto Shinkai cave rift (wider, more organic rocky canyon opening
    without symmetric star lobes!) centered high at Blender (5.0, 74.0, 50.0) -> Three.js (5.0, 50.0, -74.0).
    """
    bm = bmesh.new()
    n_ang = 128
    n_rad = 36
    rc = Vector((5.0, 74.0, 50.0))

    rings = []
    for j in range(n_rad):
        t = j / (n_rad - 1)
        s = t ** 1.42
        row = []
        for i in range(n_ang):
            ang = 2.0 * math.pi * i / n_ang
            # Asymmetric natural karst chasm (taller upper-right rift opening cleanly onto starry night sky!)
            wobble = (
                1.0
                + 0.16 * math.sin(ang * 2.0 + 0.8)
                + 0.12 * math.cos(ang * 3.0 - 0.5)
                + 0.07 * math.sin(ang * 5.0 + 1.1)
                + 0.04 * math.cos(ang * 9.0 - 0.3)
            )
            rx = (16.5 * wobble) * (1.0 - s) + 94.0 * s
            rz = (19.5 * wobble) * (1.0 - s) + 88.0 * s

            ca = math.cos(ang)
            sa = math.sin(ang)
            # Sweeping diagonal rock rift tilt (reminiscent of v2_hero_a_cathedral_v2!)
            lx = ca * rx + sa * rx * 0.24 * (1.0 - s)
            lz = sa * rz

            px = rc.x + lx
            py = rc.y - 108.0 * (s ** 1.26) + 10.0 * (1.0 - s) * math.cos(ang * 2.0)
            pz = rc.z + lz * (0.64 if sa > 0 else 1.02) - 24.0 * (s ** 1.58) * max(0.0, -sa)

            disp_amp = 0.7 + 5.2 * math.sin(t * math.pi)
            crag = chiseled_rock(px * 0.22, py * 0.22, pz * 0.34, 6.4) * disp_amp
            px += ca * crag
            pz += sa * crag * 0.65

            if j < 3:
                py += (2 - j) * 2.4

            row.append(bm.verts.new((px, py, pz)))
        rings.append(row)

    for j in range(n_rad - 1):
        for i in range(n_ang):
            inext = (i + 1) % n_ang
            bm.faces.new((rings[j][i], rings[j + 1][i], rings[j + 1][inext], rings[j][inext]))

    me = bpy.data.meshes.new("Cavern_ChasmVault")
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new("Cavern_ChasmVault", me)
    ob.data.materials.append(mat_rock)
    bpy.context.collection.objects.link(ob)
    return ob


def build_chiseled_column(name: str, base_pos: Vector, rad_xy, height: float, lean_xy, seed: float, mat_rock):
    bm = bmesh.new()
    segs, rings = 48, 44
    rx_c, ry_c = rad_xy
    rgrid = []
    for r in range(rings):
        t = r / (rings - 1)
        z = base_pos.z + height * t
        st_raw = math.sin(t * 24.0 + seed)
        strata = 1.0 + 0.075 * math.copysign(abs(st_raw) ** 0.55, st_raw) + 0.03 * math.cos(t * 52.0 - seed)
        flare = 1.0 + 0.48 * ((1.0 - t) ** 3.2) - 0.16 * math.sin(t * math.pi) + 0.28 * (t ** 3.0)
        cx_r = base_pos.x + lean_xy[0] * height * (t ** 1.55)
        cy_r = base_pos.y + lean_xy[1] * height * (t ** 1.55)
        row = []
        for s in range(segs):
            a = 2.0 * math.pi * s / segs
            poly_rib = 0.88 + 0.15 * abs(math.cos(a * 3.5 + seed)) + 0.07 * abs(math.sin(a * 6.0 - seed))
            crag = 0.10 * chiseled_rock(cx_r * 0.24 + math.cos(a) * 5.0, cy_r * 0.24 + math.sin(a) * 5.0, z * 0.5, seed)
            px = cx_r + math.cos(a) * rx_c * flare * strata * (poly_rib + crag)
            py = cy_r + math.sin(a) * ry_c * flare * strata * (poly_rib + crag)
            row.append(bm.verts.new((px, py, z)))
        rgrid.append(row)
    for r in range(rings - 1):
        for s in range(segs):
            sn = (s + 1) % segs
            bm.faces.new((rgrid[r][s], rgrid[r][sn], rgrid[r + 1][sn], rgrid[r + 1][s]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat_rock)
    bpy.context.collection.objects.link(ob)
    return ob


def build_tapered_promontory(name: str, base_pos: Vector, rad_xy, height: float, seed: float, mat_rock):
    bm = bmesh.new()
    segs, rings = 40, 28
    rx_c, ry_c = rad_xy
    rgrid = []
    for r in range(rings):
        t = r / (rings - 1)
        z = base_pos.z + height * t
        taper = max(0.06, (1.0 - t) ** 0.72) * (1.0 + 0.25 * ((1.0 - t) ** 2.5))
        strata = 1.0 + 0.09 * math.sin(t * 18.0 + seed)
        shift_x = math.sin(t * 2.2 + seed) * 1.4
        row = []
        for s in range(segs):
            a = 2.0 * math.pi * s / segs
            ridge = 0.85 + 0.24 * abs(math.cos(a * 2.5 + seed))
            crag = 0.14 * chiseled_rock(math.cos(a) * 6.0, math.sin(a) * 6.0, z * 0.65, seed)
            px = base_pos.x + shift_x + math.cos(a) * rx_c * taper * strata * (ridge + crag)
            py = base_pos.y + math.sin(a) * ry_c * taper * strata * (ridge + crag)
            row.append(bm.verts.new((px, py, z)))
        rgrid.append(row)
    for r in range(rings - 1):
        for s in range(segs):
            sn = (s + 1) % segs
            bm.faces.new((rgrid[r][s], rgrid[r][sn], rgrid[r + 1][sn], rgrid[r + 1][s]))
    top_c = bm.verts.new((base_pos.x + math.sin(2.2 + seed) * 1.4, base_pos.y, base_pos.z + height + 0.4))
    for s in range(segs):
        sn = (s + 1) % segs
        bm.faces.new((rgrid[-1][s], rgrid[-1][sn], top_c))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat_rock)
    bpy.context.collection.objects.link(ob)
    return ob


def build_grounded_basalt_outcrop(name: str, bx: float, by: float, bz_base: float, sc, seed: float, mat_rock):
    """
    Craggy, fractured volcanic basalt rock outcrop ROOTED DEEPLY into the shoreline terrain
    (ZERO floating flat-topped green pancake boulders!!).
    """
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
    planes = [
        Vector((math.cos(seed + k * 1.4), math.sin(seed * 1.3 + k * 2.1), 0.52 * math.cos(k * 1.6 + seed))).normalized()
        for k in range(8)
    ]
    for v in bm.verts:
        p = v.co.copy()
        # Grounded pyramidal rock skirt (wider at base, fractured angular crag crest on top!)
        base_spread = 1.0 + 0.45 * max(0.0, -p.z)
        p.x *= base_spread
        p.y *= base_spread
        for pl in planes:
            d = p.dot(pl)
            if d > 0.62:
                p -= pl * ((d - 0.62) * 0.78)
        crag = 1.0 + 0.18 * chiseled_rock(p.x * 4.2, p.y * 4.2, p.z * 5.2, seed)
        # Push bottom deep below shore terrain so it never floats!
        z_local = p.z * sc[2] * crag
        if p.z < -0.2:
            z_local -= 0.85
        v.co = Vector((p.x * sc[0] * crag + bx, p.y * sc[1] * crag + by, z_local + bz_base))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat_rock)
    bpy.context.collection.objects.link(ob)
    return ob


def bake_vertex_ao_and_masks(objs, ray_count: int = 24, max_dist: float = 34.0):
    t0 = time.time()
    bm_all = bmesh.new()
    for ob in objs:
        bm_tmp = bmesh.new()
        bm_tmp.from_mesh(ob.data)
        bm_tmp.transform(ob.matrix_world)
        vmap = {v.index: bm_all.verts.new(v.co) for v in bm_tmp.verts}
        for f in bm_tmp.faces:
            try:
                bm_all.faces.new([vmap[v.index] for v in f.verts])
            except ValueError:
                pass
        bm_tmp.free()
    bvh = BVHTree.FromBMesh(bm_all)
    bm_all.free()

    dirs = []
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(ray_count):
        z = (i + 0.5) / ray_count
        r = math.sqrt(max(0.0, 1.0 - z * z))
        theta = golden * i
        dirs.append(Vector((math.cos(theta) * r, math.sin(theta) * r, z)))

    up_z = Vector((0.0, 0.0, 1.0))
    for ob in objs:
        me = ob.data
        me.update()
        col_attr = me.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
        mw = ob.matrix_world
        mw_n = mw.to_3x3().inverted().transposed()
        vert_colors = {}
        for v in me.vertices:
            p = mw @ v.co
            n = (mw_n @ v.normal).normalized()
            if n.length < 1e-5:
                n = Vector((0.0, 0.0, 1.0))
            ref = Vector((1.0, 0.0, 0.0)) if abs(n.z) > 0.9 else up_z
            t1 = n.cross(ref).normalized()
            t2 = n.cross(t1).normalized()
            occ_sum = 0.0
            near_occ = 0.0
            origin = p + n * 0.09
            for d in dirs:
                rd = (t1 * d.x + t2 * d.y + n * d.z).normalized()
                hit_loc, _, _, hit_dist = bvh.ray_cast(origin, rd, max_dist)
                if hit_loc is not None:
                    w = 1.0 - (hit_dist / max_dist)
                    occ_sum += w
                    if hit_dist < 5.5:
                        near_occ += 1.0 - (hit_dist / 5.5)
            ao = max(0.06, min(1.0, 1.0 - (occ_sum / ray_count) * 1.05))
            crevice = max(0.0, min(1.0, 1.0 - (near_occ / ray_count) * 1.35))
            # Subtle mossy pockets ONLY in damp cracks near waterline (preserves dark basalt stone texture!)
            up_fac = max(0.0, min(1.0, (n.z - 0.58) / 0.36))
            h_fac = max(0.0, min(1.0, 1.0 - max(0.0, p.z - 0.8) / 7.5)) * (1.0 if p.z > 0.04 else 0.0)
            moss_noise = 0.5 + 0.5 * math.sin(p.x * 0.55 + p.y * 0.42) * math.cos(p.x * 0.28 - p.y * 0.62)
            moss = max(0.0, min(1.0, up_fac * h_fac * (0.25 + 0.85 * moss_noise)))
            vert_colors[v.index] = (ao, crevice, moss, 1.0)
        for poly in me.polygons:
            for li in poly.loop_indices:
                col_attr.data[li].color = vert_colors[me.loops[li].vertex_index]
    print(f"[T3 BAKE] Baked 24-ray Vertex AO + Crevice + UpwardMoss for {len(objs)} meshes in {time.time() - t0:.1f}s")


def build_cavern_v6():
    clear_scene()
    mat_rock = bpy.data.materials.new("Mat_CavernRock_V6")
    objs = []

    # 1. Terraced Basalt Foreground Shore, Expansive Lake Basin & Distant Flower Cove Banks
    bm = bmesh.new()
    nx, ny = 128, 108
    xs = [-82.0 + 164.0 * i / (nx - 1) for i in range(nx)]
    ys = [-44.0 + 136.0 * j / (ny - 1) for j in range(ny)]
    grid = []
    for y in ys:
        row = []
        for x in xs:
            z = shore_height(x, y)
            edge_l = max(0.0, (-48.0 - x) / 34.0)
            edge_r = max(0.0, (x - 48.0) / 34.0)
            z += (edge_l ** 2.0 + edge_r ** 2.0) * 32.0
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(ny - 1):
        for i in range(nx - 1):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    me = bpy.data.meshes.new("Cavern_ShoreTerrain")
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new("Cavern_ShoreTerrain", me)
    ob.data.materials.append(mat_rock)
    bpy.context.collection.objects.link(ob)
    objs.append(ob)

    # 2. Continuous Sweeping Diagonal Polar Aperture Cathedral Vault (ZERO tube bridges, ZERO squares!)
    objs.append(build_chasm_vault(mat_rock))

    # 3. Towering Chiseled Gothic Cathedral Columns Framing the Vast Open Central Nave
    col_specs = [
        ("GothicPortal_FL", Vector((-40.0, 2.0,  -4.0)), (9.5,  10.5), 76.0, (0.10,  0.02), 11.2),
        ("GothicPortal_FR", Vector((42.0,  4.0,  -4.0)), (10.0, 11.0), 78.0, (-0.10, 0.02), 23.7),
        ("GothicNave_ML",   Vector((-35.0, 32.0, -5.0)), (8.5,  10.0), 82.0, (0.11,  0.01), 35.4),
        ("GothicNave_MR",   Vector((37.0,  34.0, -5.0)), (8.8,  10.2), 82.0, (-0.10, 0.01), 47.9),
        ("GothicChasm_BL",  Vector((-34.0, 66.0, -5.0)), (10.5, 10.5), 86.0, (0.04, -0.02), 59.1),
        ("GothicChasm_BR",  Vector((40.0,  64.0, -5.0)), (10.5, 10.5), 86.0, (-0.04, -0.02), 71.8),
    ]
    for name, c, rxy, h, lean, seed in col_specs:
        objs.append(build_chiseled_column(name, c, rxy, h, lean, seed, mat_rock))

    # 4. Craggy Tapered Basalt Promontories Jutting Into the Obsidian Lake
    objs.append(build_tapered_promontory("LakePromontory_R", Vector((24.5, 42.0, -4.0)), (10.5, 12.5), 22.5, 83.2, mat_rock))
    objs.append(build_tapered_promontory("LakePromontory_L", Vector((-26.0, 48.0, -4.0)), (9.5, 11.0), 18.0, 94.6, mat_rock))

    # 5. Grounded Craggy Volcanic Basalt Shore Outcrops (ZERO hovering green pancakes!)
    outcrop_specs = [
        ("ShoreOutcrop_FL", -13.5, -15.5, 0.45, (3.8, 2.8, 1.35), 11.4),
        ("ShoreOutcrop_FR",  14.0, -15.0, 0.42, (4.0, 2.9, 1.40), 22.8),
        ("ShoreOutcrop_ML", -21.5,  -3.5, 0.20, (7.0, 4.4, 2.40), 55.2),
        ("ShoreOutcrop_MR",  22.5,  -2.8, 0.25, (7.4, 4.8, 2.60), 66.7),
        # Grounded rocky left overlook ledges for Shot 3 foreground depth framing!
        ("ShoreOutcrop_OL1", -9.4, -15.2, 0.65, (3.4, 2.6, 1.15), 77.3),
        ("ShoreOutcrop_OL2", -14.0, -16.4, 0.95, (3.8, 2.8, 1.40), 88.1),
    ]
    for name, bx, by, bz, sc, seed in outcrop_specs:
        objs.append(build_grounded_basalt_outcrop(name, bx, by, bz, sc, seed, mat_rock))

    bake_vertex_ao_and_masks(objs, ray_count=24, max_dist=34.0)

    out_glb = OUT_DIR / "cavern_v6.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(out_glb),
        export_format="GLB",
        export_yup=True,
        export_attributes=True,
        export_materials="PLACEHOLDER",
    )
    print(f"[T3 EXPORT] {out_glb} ({out_glb.stat().st_size / (1024*1024):.2f} MB)")


if __name__ == "__main__":
    build_cavern_v6()
    print("[DONE] V6.4 cavern_v6.glb rebuilt!")
