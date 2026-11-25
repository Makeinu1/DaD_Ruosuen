"""v15 Blender base: build the cave from the v14.9b previs data and render one cut (EEVEE).

Run inside Blender 5.x (tested 5.3):
  blender -b -P render_cut.py -- --cache <cache/R14> --out <renders/R14_a> [--res 960] [--samples 32]
                                  [--frames 0:192] [--step 1] [--save-blend] [--look guide|night]
From the VideoStudio MCP (blender_run) see ../README.md ("PCでの実行").

Inputs : <cache>/cut.json + <cache>/petals/f_####.npz written by ../bridge/export_cut.py
Assets : ../../../video-pipeline/v7_blender_cycles/assets/wh01_v20_hero.glb (WH-01 hero mesh)
Output : <out>/beauty/####.png (frame index inside the cut), <out>/scene.blend with --save-blend

What comes from the previs unchanged (do not re-animate by hand): camera per frame, whale body
frame + stroke/fin deformation (v14_world.deform on the hero vertices), whale light, petal positions.
What is built here: rock canopy with the fissure (two rims, 190 m and 230 m), ground height field,
water plane, cave wall, moonlight (sun + world volume = the beam), whale emission, petal billboards.
"""
import bpy, bmesh, json, math, sys, time, argparse
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
PREVIS = HERE.parent.parent / 'previs' / 'v14-director-rebuild'
ASSETS = HERE.parent.parent.parent / 'video-pipeline' / 'v7_blender_cycles' / 'assets'
sys.path.insert(0, str(PREVIS))
import v14_world as w           # noqa: E402  numpy only

# ------------------------------------------------------------------ look parameters (tune here)
LOOK = {
    # neutral base for restyling (Flow / Wan) and for the painterly pass; tuned on R14 (v15a)
    # v15c (2026-11-25): matched to the previs v14.9b R14 frames by eye and by region means -
    # navy air, crisp white petals (previs draws far flakes as hard dots), whale as in the previs
    # v15e (2026-11-25, author): brighter (exposure, air, moon), petals x3 along the same flow, and a near
    # blizzard of real petals (NearSnow) - the previs keeps R14's foreground clear; this is the author's change
    'guide': dict(exposure=0.35, vol_density=0.0005, vol_aniso=0.55, moon_strength=6.0,
                  moon_color=(0.70, 0.80, 1.0), whale_light_w=1.5e5, whale_light_vol=0.35, whale_emit=0.95,
                  petal_emit=2.2, fruit_emit=0.4, petal_min_px=0.8, rock=0.018, bg=(0.003, 0.005, 0.012),
                  whale_form=0.6, whale_opal=1.0, whale_self_light=0.0, eye_out=1.08,
                  air_color=(0.6, 0.74, 1.0), filter_px=0.8,
                  whale_tex=0.7, whale_belly=0.35, whale_top=(0.8, 1.1),
                  petal_dense=3.0, dense_r=2.5,
                  near_n=1200.0, near_size=0.045, near_zmin=3.0, near_zmax=30.0, near_emit=0.10,
                  near_light=3.0e6, fstop=8.0, near_band=0.65, near_band_c=0.14, near_gust=0.0, near_size_max=1.3),
    # v15f (2026-11-25, author: the near blizzard reads far better than the stream clinging to the whale;
    # rebuild around it): the near blizzard fills 3-70 m in front of the whale with real petals (a continuous
    # depth of sizes), gusts; the far previs stream goes back to the previs density and becomes light
    'blizzard': None,
}
LOOK['blizzard'] = dict(LOOK['guide'], petal_dense=1.0, near_n=3500.0, near_zmax=60.0, near_zpow=1.6, near_size_max=1.5,
                        near_gust=0.35, fstop=5.6, near_light=4.5e6, near_emit=0.06, near_band_c=-0.12)
# v15g (author 2026-11-25): the whale glows sakura pink; fewer, real-size (3 cm), slow petals ("5 cm per
# second": petals you can follow one by one), a few big soft out-of-focus ones in front (shallow focus)
# (tested with --set lens_mul=1.636 = 90 mm from the previs position: the whale ~40% of the width; 110 mm cuts
# the whale off at the start. The lens is a previs change for the author to decide.)
LOOK['sakura'] = dict(LOOK['blizzard'], palette='sakura', near_n=1300.0, near_size=0.030, near_size_max=1.4,
                      near_zmin=3.0, near_zmax=90.0, near_zpow=1.3, near_speed=0.4, near_gust=0.3, fstop=5.6,
                      whale_emit=1.15, whale_light_vol=0.5)
# v16 R15 (previs v14.10: the closest pass, 18 mm, the camera turns in place to follow): the v15i look, the
# near blizzard in world mode (the peak of R13-R15: more and nearer than R14, riding the snow the whale
# brings, hanging in the slow moment), shallow focus so the nearest petals go soft (previs: bokeh discs)
# The whale fills the frame here: less emission and more of its form (Layer Weight) so the grooves and the eye read.
LOOK['r15'] = dict(LOOK['sakura'], palette='source', near_world=1.0, near_n=2400.0, near_zmin=1.3, near_zmax=24.0,
                   near_size=0.032, near_size_max=1.4, near_fade=(15.0, 40.0), fstop=2.0,
                   near_couple=(0.35, 0.85), whale_emit=0.8, whale_form=0.85, whale_light_vol=0.4, climax_air=1.5)
# v16 R18 (previs v14.10: from the four's shore, 100 mm on the opening; the whale swims up into the moon and
# gives its light back): the opening cut exactly (no stair-steps), the night sky, stars and the composed moon;
# the rock lit by the whale kept darker than the moon (previs kc 0.4); no near blizzard (previs: none in R18)
# Sky, moon and rock calibrated region by region against the previs R18 frames (renders/R18_c6: moon 210/201,
# halo (65,88,137)/(65,85,127), sky (39,62,100)/(38,53,88), slot walls (29,39,54)/(32,38,48), canopy (5,11,21)/(7,11,18))
SKY_MOON = dict(slab_poly=1.0, sky=1.0, sky_emit=1.0, sky_high=(46.0, 58.0, 92.0), sky_low=(58.0, 72.0, 112.0),
                star_emit=3.0, moon_disc=0.6, moon_halo=3.0, rock_emit=0.14, rock_facet_lo=0.45)
# melt_emit = moon_disc: the parts that have taken on the moon's colour glow exactly like it and merge into it
LOOK['r18'] = dict(LOOK['sakura'], palette='source', near_n=0.0, fstop=0.0, melt_emit=0.6, whale_light_w=25000.0, **SKY_MOON)
# v16 R17b (previs v14.10: the four from just behind and below, looking up, 20 mm; the whale, small and glowing,
# rises to the moon; real snow at last - the released petals, their magic gone, come down slowly, white):
# the four built in Blender (Party), the white snow in world mode riding the falling snow of the simulation
LOOK['r17b'] = dict(LOOK['sakura'], palette='source', fstop=0.0, party=1.0, near_world=1.0, near_n=900.0,
                    near_zmin=1.3, near_zmax=20.0, near_couple=(0.8, 1.1), near_drift=(0.0, 0.0, 0.0),
                    near_drift_sd=(0.12, 0.12, 0.08), near_size=0.030, near_size_max=1.3, near_emit=0.3, **SKY_MOON)
# measured against the previs (renders/R17b_t1): the released snow cloud ~x2 brighter, the roof darker (previs: near
# black around the opening), the whale's light on the roof weaker, the four only lit on top (no halo round the heads)
LOOK['r17b'].update(petal_emit=4.5, rock_emit_canopy=0.04, whale_light_w=0.8e5, party_rim=0.35)
# v16 R13 (previs v14.10: among the flowers by R12's flower, 45 cm up, 24 mm; the whole colony lets go in a wave
# from the cape tip and the camera tilts up after the rising snow): the colony as real flowers (FlowerField), the
# rising near snow in world mode (it rides the lifted snow of the simulation once it moves), canvas on the scene
LOOK['r13'] = dict(LOOK['sakura'], palette='source', fstop=0.0, flowers=1.0, near_world=1.0, near_n=550.0,
                   near_zmin=1.5, near_zmax=20.0, near_couple=(0.5, 1.0), near_drift=(0.0, 0.0, 1.2),
                   near_drift_sd=(0.3, 0.3, 0.4), near_size=0.030, near_size_max=1.3, near_light=1.5e6,
                   flower_sxy=0.5, whale_light_ground=0.0, petal_near_r=5.0, flower_emit=0.3,
                   petal_emit=1.1)        # measured (renders/R13_t3): the lifted snow came out ~1.6x the previs level
PEARL = (0.86, 0.93, 1.0)
BELLY = (0.55, 0.68, 0.95)          # the shaded underside goes blue (originals CUT05 / CUT09)
# previs whale_layer (v14.9b): pearl-opal colours along the body, by hue = 0 at the tail .. 1 at the head
OPAL = ((0.08, (228, 226, 212)), (0.30, (214, 208, 238)), (0.55, (234, 238, 242)), (0.85, (184, 216, 240)))
# v15g (author 2026-11-25: "a different whale colour, e.g. a pink glow - more emotional"): palettes.
# light = the whale's light (air, petals), belly = shaded underside, glow = emission ramp tail..head,
# petal_lit = colour the petals take in the whale's light, trl = near-petal translucency when backlit
PALETTES = {
    'pearl': dict(light=PEARL, belly=BELLY, glow=OPAL, petal_lit=(0.93, 0.94, 0.96), trl=(0.88, 0.93, 1.0)),
    'sakura': dict(light=(1.0, 0.62, 0.80), belly=(0.62, 0.46, 0.90),
                   glow=((0.08, (255, 118, 168)), (0.30, (255, 148, 192)), (0.55, (255, 186, 214)), (0.85, (255, 212, 228))),
                   petal_lit=(1.0, 0.80, 0.90), trl=(1.0, 0.70, 0.84)),
    # v15h study (2026-11-25, author: is giving the whale and the petals the same colour right?)
    # 'source': the whale is the light source - a pearl-white core, a sakura rim and sakura light; the
    #   petals stay white snow and blush only where its light reaches them (title: snow falling into the sky)
    'source': dict(light=(1.0, 0.62, 0.80), belly=(0.62, 0.46, 0.90), rim=(1.0, 0.42, 0.68),
                   glow=((0.08, (255, 214, 228)), (0.30, (255, 228, 238)), (0.55, (250, 242, 246)), (0.85, (244, 244, 252))),
                   petal_lit=(1.0, 0.84, 0.92), trl=(0.98, 0.93, 0.97), near_light=(1.0, 0.93, 0.96),
                   # v15i (author: show other hues at times, e.g. pale gold): each stroke sends a pale-gold
                   # wave head->tail through the whale; its light, the near petals and the stream follow
                   gold=(255, 226, 168), gold_rim=(1.0, 0.72, 0.40), gold_light=(1.0, 0.80, 0.62),
                   gold_petal=(1.0, 0.90, 0.66)),
    # 'contrast': a sakura whale against cool white-silver petals
    'contrast': dict(light=(1.0, 0.62, 0.80), belly=(0.62, 0.46, 0.90),
                     glow=((0.08, (255, 118, 168)), (0.30, (255, 148, 192)), (0.55, (255, 186, 214)), (0.85, (255, 212, 228))),
                     petal_lit=(0.92, 0.95, 1.0), trl=(0.86, 0.92, 1.0), near_light=(0.84, 0.91, 1.0)),
}


def pal(look):
    return PALETTES[look.get('palette', 'pearl')]


def gold_mix(look, base, key, fr, amt_key='gold_light_amt', amt=0.85):
    """base colour moved toward the palette's gold by how gold the whale's light is in this frame."""
    P_ = pal(look)
    if key not in P_:
        return tuple(base)
    k = fr.get('_gold', 0.0) * look.get(amt_key, amt)
    return tuple(float(b * (1 - k) + c * k) for b, c in zip(base, P_[key]))
FRUIT = (1.0, 0.80, 0.45)
PETAL = (0.93, 0.94, 0.96)


def args_from_argv(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--res', type=int, default=960)
    ap.add_argument('--samples', type=int, default=32)
    ap.add_argument('--frames', default='')
    ap.add_argument('--step', type=int, default=1)
    ap.add_argument('--save-blend', action='store_true')
    ap.add_argument('--no-render', action='store_true')
    ap.add_argument('--look', default='guide')
    ap.add_argument('--exposure', type=float, default=None)
    ap.add_argument('--set', action='append', default=[], help='look override key=value (floats)')
    ap.add_argument('--engine', default='EEVEE', choices=['EEVEE', 'CYCLES'])
    ap.add_argument('--control', default='', choices=['', 'depth', 'depth_petals', 'petals', 'base', 'whale_matte', 'near'],
                    help='depth: control video for Wan Fun-Control (out/control_depth); depth_petals: the same with '
                         'the previs petals added as light dots; petals: the petal layer alone, the rest black '
                         '(to lay the previs petals over a painted pass); base: the beauty without petals; '
                         'whale_matte: the whale white, the rest black (masks for post/finish.py)')
    ap.add_argument('--depth-near', type=float, default=120.0, help='metres; nearer is white')
    ap.add_argument('--depth-far', type=float, default=700.0, help='metres; farther is black')
    return ap.parse_args(argv)


def try_set(obj, **kv):
    for k, v in kv.items():
        try:
            setattr(obj, k, v)
        except Exception as e:      # API drift between Blender versions: log and continue
            print(f'  [skip] {type(obj).__name__}.{k}: {e}')


# ------------------------------------------------------------------ helpers
def mesh_obj(name, verts, faces, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(map(int, f)) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        me.materials.append(mat)
    return ob


def simple_mat(name, color, rough=0.9, spec=0.2):
    m = bpy.data.materials.new(name)
    try_set(m, use_nodes=True)
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = spec
    return m


def grid_cells(x0, x1, y0, y1, step):
    xs = np.arange(x0, x1, step); ys = np.arange(y0, y1, step)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    return X.ravel(), Y.ravel()


def slab_with_hole(name, z, k, mat, step=4.0, ext=340.0):
    """Horizontal rock surface at height z with the fissure cut out (cell resolution `step`)."""
    cx, cy = grid_cells(-ext, ext, -ext, ext, step)
    inside, _ = w._inside_rim(cx + step / 2, cy + step / 2, k)
    cx, cy = cx[~inside], cy[~inside]
    V = np.zeros((len(cx) * 4, 3)); F = np.arange(len(cx) * 4).reshape(-1, 4)
    for i, (dx, dy) in enumerate(((0, 0), (step, 0), (step, step), (0, step))):
        V[i::4, 0] = cx + dx; V[i::4, 1] = cy + dy; V[i::4, 2] = z
    ob = mesh_obj(name, V, F, mat)
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)
    bm.to_mesh(ob.data); bm.free()
    return ob


def slab_poly(name, z, mat, ext=340.0, sub=8):
    """v16: the canopy with the opening cut exactly along the previs rim polygon (straight segments, as
    the previs draws the opening and as its moonlit() test interpolates the fissure), instead of 4 m cells
    whose stair-steps show through a long lens (R18, 100 mm: ~57 px steps). An annulus of quads between
    the rim and a far outer ring at the same angles (the fissure is star-shaped from its centroid)."""
    P = np.array(w.rim_polygon(z))[:, :2]
    Q = np.array([P[i] + (P[(i + 1) % len(P)] - P[i]) * j / sub for i in range(len(P)) for j in range(sub)])
    c = P.mean(0); ang = np.arctan2(Q[:, 1] - c[1], Q[:, 0] - c[0])
    O = c + np.column_stack([np.cos(ang), np.sin(ang)]) * ext * 1.45
    # v16: rings from the rim outward, small near the opening, then triangles with a random tone each
    # (the previs draws the rock around the opening as flat facets); the rim ring itself stays exact
    ts = (0.0, 0.012, 0.03, 0.06, 0.11, 0.19, 0.32, 0.52, 0.76, 1.0)
    g = np.random.default_rng(int(z))
    rings = []
    for j, t in enumerate(ts):
        R_ = Q + (O - Q) * t
        zz = np.full(len(Q), float(z)) + (g.uniform(-0.7, 0.7, len(Q)) * min(1.0, 40 * t) if j else 0.0)
        rings.append(np.column_stack([R_, zz]))
    return _tri_rings(name, rings, mat, g)


def _tri_rings(name, rings, mat, g):
    """quads between consecutive closed rings, split into triangles (alternating diagonals), each with a
    random tone (face attribute pv_facet, used by _rock_glow)"""
    n = len(rings[0]); V = np.vstack(rings); F = []
    for j in range(len(rings) - 1):
        for i in range(n):
            a, b, c_, d = j * n + i, j * n + (i + 1) % n, (j + 1) * n + (i + 1) % n, (j + 1) * n + i
            F += [(a, b, c_), (a, c_, d)] if (i + j) % 2 else [(a, b, d), (b, c_, d)]
    ob = mesh_obj(name, V, F, mat)
    at = ob.data.attributes.new('pv_facet', 'FLOAT', 'FACE')
    at.data.foreach_set('value', g.random(len(F)).astype(np.float32))
    return ob


def slot_wall(name, mat, sub=8, levels=6):
    """v16: the slot between the bottom rim (190 m) and the narrower top rim (230 m), in facets"""
    def subd(P):
        return np.array([P[i] + (P[(i + 1) % len(P)] - P[i]) * j / sub for i in range(len(P)) for j in range(sub)])
    pb = subd(np.array(w.rim_polygon(w.RIM_Z))); pt = subd(np.array(w.rim_polygon(w.TOP_Z)))
    g = np.random.default_rng(1902)
    c = pb[:, :2].mean(0)
    rings = []
    for j in range(levels + 1):
        t = j / levels; R_ = pb + (pt - pb) * t
        if 0 < j < levels:                                  # a little relief, the rims stay exact
            d = R_[:, :2] - c; d /= np.linalg.norm(d, axis=1, keepdims=True)
            R_ = R_.copy(); R_[:, :2] += d * g.uniform(-1.2, 1.2, len(R_))[:, None]
        rings.append(R_)
    return _tri_rings(name, rings, mat, g)


def build_world(look):
    sc = bpy.context.scene
    rock = simple_mat('Rock', (look['rock'],) * 3, 0.95)
    rock_soft = simple_mat('RockFar', (look['rock'] * 0.8, look['rock'] * 0.85, look['rock'] * 0.9), 0.95)
    rock_slot = rock
    if look.get('rock_emit', 0.0) > 0:
        # v16 (R18): the night sky through the opening lights the rock a dim grey-blue, in flat facets (previs:
        # faceted rock around the opening, ~(37,45,56) on the slot walls that see the sky, the canopy underside
        # much darker)
        rock_slot = simple_mat('RockSlot', (look['rock'],) * 3, 0.95)
        _rock_glow(rock_slot, look, look['rock_emit'])
        _rock_glow(rock, look, look['rock_emit'] * look.get('rock_emit_canopy', 0.2))
    # canopy: bottom rim (190 m) and the narrower top rim (230 m) -> the moon beam is their intersection
    if look.get('slab_poly', 0.0) > 0.5:
        slab_poly('Canopy_Rim190', w.RIM_Z, rock)
        slab_poly('Canopy_Top230', w.TOP_Z, rock)
        slot_wall('SlotWall', rock_slot)      # the slot between the rims (previs: dark faceted rock)
    else:
        slab_with_hole('Canopy_Rim190', w.RIM_Z, 1.0, rock)
        slab_with_hole('Canopy_Top230', w.TOP_Z, w.TOP_NARROW, rock)
    _build_ground_water_air(sc, look, rock_soft)


def _rock_glow(rock, look, strength):
    """dim emission for rock that sees the night sky, one tone per facet (face attribute pv_facet)"""
    nt = rock.node_tree; N = nt.nodes; L = nt.links; b = N.get('Principled BSDF')
    fa = N.new('ShaderNodeAttribute'); fa.attribute_name = 'pv_facet'
    mr = N.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = look.get('rock_facet_lo', 0.3); mr.inputs['To Max'].default_value = 1.0
    L.new(fa.outputs['Fac'], mr.inputs['Value'])
    k = N.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; k.inputs[1].default_value = strength
    L.new(mr.outputs['Result'], k.inputs[0])
    b.inputs['Emission Color'].default_value = (*_lin(look.get('rock_emit_col', (120, 140, 175))), 1)
    L.new(k.outputs[0], b.inputs['Emission Strength'])


def _build_ground_water_air(sc, look, rock_soft):
    # ground height field (land) and water
    xs = np.arange(-300, 301, 4.0); ys = np.arange(-300, 241, 4.0)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    Z = w.ground_z(X, Y) - np.where(w.is_land(X, Y), 0.0, 1.5)
    V = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    nx, ny = len(xs), len(ys)
    ii, jj = np.meshgrid(np.arange(nx - 1), np.arange(ny - 1), indexing='ij')
    a = (ii * ny + jj).ravel()
    F = np.column_stack([a, a + ny, a + ny + 1, a + 1])
    mesh_obj('Ground', V, F, simple_mat('Moss', (0.020, 0.024, 0.021), 0.95))
    water = simple_mat('Water', (0.003, 0.004, 0.006), 0.06, 0.5)
    mesh_obj('Water', [(-340, -340, 0.02), (340, -340, 0.02), (340, 340, 0.02), (-340, 340, 0.02)], [(0, 1, 2, 3)], water)
    # cave wall: a dark cylinder (r 330 m) up to the canopy
    n = 96; r = 330.0
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    V = [(r * math.cos(t), r * math.sin(t), z) for z in (-2.0, w.TOP_Z) for t in ang]
    F = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    mesh_obj('CaveWall', V, F, rock_soft)
    # world: night. The air is a closed volume OBJECT (not a world volume: a world volume is
    # infinite and absorbs the sun completely, so no moon beam would ever reach the cave)
    wo = bpy.data.worlds.new('CaveNight'); sc.world = wo
    try_set(wo, use_nodes=True)
    bgn = wo.node_tree.nodes.get('Background')
    bgn.inputs['Color'].default_value = (*look['bg'], 1); bgn.inputs['Strength'].default_value = 1.0
    air = bpy.data.materials.new('CaveAir'); try_set(air, use_nodes=True)
    nt = air.node_tree
    for nd in list(nt.nodes):
        if nd.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(nd)
    vol = nt.nodes.new('ShaderNodeVolumePrincipled')
    vol.inputs['Density'].default_value = look['vol_density']
    vol.inputs['Anisotropy'].default_value = look['vol_aniso']
    vol.inputs['Color'].default_value = (*look['air_color'], 1)
    nt.links.new(vol.outputs['Volume'], next(nd for nd in nt.nodes if nd.type == 'OUTPUT_MATERIAL').inputs['Volume'])
    e = 335.0; z0, z1 = -1.0, w.TOP_Z - 1.0
    V = [(-e, -e, z0), (e, -e, z0), (e, e, z0), (-e, e, z0), (-e, -e, z1), (e, -e, z1), (e, e, z1), (-e, e, z1)]
    F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mesh_obj('CaveAir', V, F, air)
    # moonlight
    ld = bpy.data.lights.new('Moon', 'SUN'); ld.energy = look['moon_strength']; ld.color = look['moon_color']
    try_set(ld, angle=math.radians(0.6))
    mo = bpy.data.objects.new('Moon', ld); sc.collection.objects.link(mo)
    mo.rotation_mode = 'QUATERNION'
    mo.rotation_quaternion = Vector(tuple(-w.MOON_DIR)).to_track_quat('-Z', 'Y')


MOON_FACE = (236, 232, 212)     # previs draw_moon / melt colour


def _emit_mat(name, color, strength, image=None, blend=False):
    m = bpy.data.materials.new(name); try_set(m, use_nodes=True)
    nt = m.node_tree; N = nt.nodes; L = nt.links
    for nd in list(N):
        if nd.type != 'OUTPUT_MATERIAL':
            N.remove(nd)
    out = next(nd for nd in N if nd.type == 'OUTPUT_MATERIAL')
    em = N.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = strength
    em.inputs['Color'].default_value = (*color, 1)
    if image is not None:
        tx = N.new('ShaderNodeTexImage'); tx.image = image; tx.interpolation = 'Linear'
        mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
        mul.inputs[6].default_value = (*color, 1); L.new(tx.outputs['Color'], mul.inputs[7]); L.new(mul.outputs[2], em.inputs['Color'])
        tr = N.new('ShaderNodeBsdfTransparent'); mx = N.new('ShaderNodeMixShader')
        L.new(tx.outputs['Alpha'], mx.inputs['Fac']); L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2])
        L.new(mx.outputs[0], out.inputs['Surface'])
    else:
        L.new(em.outputs[0], out.inputs['Surface'])
    if blend or image is not None:
        try_set(m, surface_render_method='BLENDED', use_backface_culling=False)
    return m


def _lin(rgb255):
    return tuple((c / 255.0) ** 2.2 for c in rgb255)


def build_sky(look, meta):
    """v16 (R17-R19, R01): the night sky, stars and moon seen through the opening, as the previs draws them:
    a navy sky (lighter low, darker high), its 700 stars (same seed), and the moon composed in the opening
    (cut.json 'moon': the previs anchor just beyond the top rim + angular radius) with its maria and a thin
    bright ring. All emitters outside the cave: they light nothing inside (the moonbeam is the Sun light)."""
    sc = bpy.context.scene
    cam0 = meta['frames'][0]['cam']; cp = np.array(cam0['pos']); W = 1280.0
    # sky dome above the opening (emission by height: horizon (30,46,80) -> zenith (20,32,62))
    Rd = 2500.0; cz = w.TOP_Z
    nu, nv = 48, 12
    V = [(0.0, 137.0, cz + Rd)]
    for j in range(1, nv + 1):
        el = math.pi / 2 * (1 - j / nv)
        for i in range(nu):
            az = 2 * math.pi * i / nu
            V.append((Rd * math.cos(el) * math.cos(az), 137.0 + Rd * math.cos(el) * math.sin(az), cz + Rd * math.sin(el)))
    F = [(0, 1 + (i + 1) % nu, 1 + i) for i in range(nu)]
    for j in range(nv - 1):
        a0 = 1 + j * nu; a1 = a0 + nu
        F += [(a0 + i, a0 + (i + 1) % nu, a1 + (i + 1) % nu, a1 + i) for i in range(nu)]
    m = bpy.data.materials.new('NightSky'); try_set(m, use_nodes=True)
    nt = m.node_tree; N = nt.nodes; L = nt.links
    for nd in list(N):
        if nd.type != 'OUTPUT_MATERIAL':
            N.remove(nd)
    geo = N.new('ShaderNodeNewGeometry'); sz = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], sz.inputs[0])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = cz; mr.inputs['From Max'].default_value = cz + Rd
    L.new(sz.outputs['Z'], mr.inputs['Value'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; L.new(mr.outputs['Result'], mx.inputs['Factor'])
    mx.inputs[6].default_value = (*_lin(look.get('sky_low', (30, 46, 80))), 1); mx.inputs[7].default_value = (*_lin(look.get('sky_high', (20, 32, 62))), 1)
    em = N.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = look.get('sky_emit', 1.0)
    L.new(mx.outputs[2], em.inputs['Color'])
    L.new(em.outputs[0], next(nd for nd in N if nd.type == 'OUTPUT_MATERIAL').inputs['Surface'])
    mesh_obj('NightSky', V, F, m)
    # stars: the previs' 700 (seed 7), ~1.6 px at this cut's lens
    r = np.random.default_rng(7)
    el = np.radians(r.uniform(25, 89, 700)); az = r.uniform(-np.pi, np.pi, 700)
    sd = np.column_stack([np.cos(el) * np.sin(az), np.cos(el) * np.cos(az), np.sin(el)]); sb = r.uniform(0.3, 1.0, 700)
    Rs = 2300.0; P = cp + sd * Rs
    s = 1.6 * (36.0 / cam0['lens_mm'] / W) * Rs
    up = np.array([0, 0, 1.0])
    ex = np.cross(sd, up); ex /= np.linalg.norm(ex, axis=1, keepdims=True) + 1e-9; ey = np.cross(ex, sd)
    h = 0.5 * s
    Vs = np.stack([P - h * ex - h * ey, P + h * ex - h * ey, P + h * ex + h * ey, P - h * ex + h * ey], 1).reshape(-1, 3)
    Fs = np.arange(len(Vs)).reshape(-1, 4)
    ob = mesh_obj('Stars', Vs, Fs, None)
    sm = bpy.data.materials.new('Star'); try_set(sm, use_nodes=True)
    nt = sm.node_tree; N = nt.nodes; L = nt.links
    for nd in list(N):
        if nd.type != 'OUTPUT_MATERIAL':
            N.remove(nd)
    at = N.new('ShaderNodeAttribute'); at.attribute_name = 'pv_col'
    em = N.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = look.get('star_emit', 3.0)
    L.new(at.outputs['Color'], em.inputs['Color'])
    L.new(em.outputs[0], next(nd for nd in N if nd.type == 'OUTPUT_MATERIAL').inputs['Surface'])
    ob.data.materials.append(sm)
    ac = ob.data.attributes.new('pv_col', 'FLOAT_COLOR', 'POINT')
    col = np.repeat((np.array(_lin((210, 220, 240)))[None] * (sb * 0.55)[:, None]), 4, 0)
    C = np.ones((len(col), 4), np.float32); C[:, :3] = col; ac.data.foreach_set('color', C.ravel())
    # the moon, composed in the opening (previs moon_layout + draw_moon)
    mo = meta.get('moon')
    if mo is None:
        return
    Q = np.array(mo['p']); d = Q - cp; dist = np.linalg.norm(d); d /= dist
    rm = dist * math.tan(mo['ang_r'])
    n_ = 512; ext = 1.5
    yy, xx = (np.mgrid[0:n_, 0:n_] + 0.5) / n_ * 2 * ext - ext
    ux, uy = xx, -yy
    dd = np.sqrt(ux ** 2 + uy ** 2)
    rpx = 200.0                                           # the previs' edge softness at ~200 px radius
    disk = np.clip((1.0 + 1.2 / rpx - dd) * rpx / 1.6, 0, 1)
    limb = 0.80 + 0.20 * np.sqrt(np.clip(1 - dd ** 2, 0, 1))
    maria = np.ones_like(dd)
    for (cx_, cy_, r_, k_) in ((-0.40, -0.02, 0.34, 0.17), (-0.20, -0.32, 0.24, 0.19), (-0.48, 0.28, 0.18, 0.10),
                               (0.16, -0.26, 0.16, 0.17), (0.28, -0.02, 0.18, 0.15), (0.44, 0.20, 0.11, 0.11),
                               (0.62, -0.24, 0.08, 0.12), (-0.14, 0.34, 0.12, 0.08)):
        maria = maria - k_ * np.exp(-(((ux - cx_) ** 2 + (-uy - cy_) ** 2) / r_ ** 2) * 2.2)
    face = disk * limb * maria
    ring = np.exp(-((dd - 1.0).clip(0) / 0.08) ** 2) * (1 - disk) * 0.55
    rgb = (face[..., None] * np.array(MOON_FACE) + ring[..., None] * np.array([220, 225, 235])) / 255.0
    al = np.clip(disk + ring / 0.55, 0, 1)
    img = bpy.data.images.new('MoonFace', n_, n_, alpha=True)
    px = np.concatenate([np.clip(rgb, 0, 1), al[..., None]], -1)[::-1].astype(np.float32)   # Blender images start bottom-left
    img.pixels.foreach_set(px.ravel()); img.pack()
    # quad facing the cut's camera, sized to the composed angular radius (texture spans +-1.5 radii)
    up = np.array(cam0['u']); ex = np.cross(d, up); ex /= np.linalg.norm(ex); ey = np.cross(ex, d)
    hq = rm * ext
    Vm = [tuple(Q - hq * ex - hq * ey), tuple(Q + hq * ex - hq * ey), tuple(Q + hq * ex + hq * ey), tuple(Q - hq * ex + hq * ey)]
    ob = mesh_obj('MoonDisc', Vm, [(0, 1, 2, 3)], _emit_mat('MoonDisc', (1, 1, 1), look.get('moon_disc', 6.0), img))
    uvl = ob.data.uv_layers.new(name='UVMap'); uvl.data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
    # its halo (previs: a wide soft glow over the opening, (120,134,160)), added behind the disc; the rock hides it
    n2 = 256; e2 = 4.0
    yy, xx = (np.mgrid[0:n2, 0:n2] + 0.5) / n2 * 2 * e2 - e2
    dd = np.sqrt(xx ** 2 + yy ** 2)
    gl = np.exp(-((dd - 1.0).clip(0) / 0.7) ** 2) * 0.26 + np.exp(-(dd / 3.0) ** 2) * 0.10
    gl = gl * np.clip((e2 - dd) / 0.8, 0, 1)                # fade out before the quad's edge
    im2 = bpy.data.images.new('MoonHalo', n2, n2, alpha=True)
    px = np.zeros((n2, n2, 4), np.float32); px[..., :3] = gl[..., None]; px[..., 3] = 1.0
    im2.pixels.foreach_set(px.ravel()); im2.pack()
    hm = bpy.data.materials.new('MoonHalo'); try_set(hm, use_nodes=True)
    nt = hm.node_tree; N = nt.nodes; L = nt.links
    for nd in list(N):
        if nd.type != 'OUTPUT_MATERIAL':
            N.remove(nd)
    tx = N.new('ShaderNodeTexImage'); tx.image = im2
    em = N.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = look.get('moon_halo', 1.0)
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    mul.inputs[6].default_value = (*_lin((120, 134, 160)), 1); L.new(tx.outputs['Color'], mul.inputs[7]); L.new(mul.outputs[2], em.inputs['Color'])
    tr = N.new('ShaderNodeBsdfTransparent'); ad = N.new('ShaderNodeAddShader')        # additive: light, not paint
    L.new(tr.outputs[0], ad.inputs[0]); L.new(em.outputs[0], ad.inputs[1])
    L.new(ad.outputs[0], next(nd for nd in N if nd.type == 'OUTPUT_MATERIAL').inputs['Surface'])
    try_set(hm, surface_render_method='BLENDED', use_backface_culling=False)
    Qh = Q + d * 2.0; hq = rm * e2
    Vh = [tuple(Qh - hq * ex - hq * ey), tuple(Qh + hq * ex - hq * ey), tuple(Qh + hq * ex + hq * ey), tuple(Qh - hq * ex + hq * ey)]
    ob = mesh_obj('MoonHalo', Vh, [(0, 1, 2, 3)], hm)
    uvl = ob.data.uv_layers.new(name='UVMap'); uvl.data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
    print(f'  sky: moon at {dist:.0f} m, radius {rm:.1f} m ({math.degrees(mo["ang_r"]):.2f} deg), stars {len(sd)}')


def build_camera(meta):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new('PrevisCam'); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0
    cd.clip_start = 0.05; cd.clip_end = 3000.0
    co = bpy.data.objects.new('PrevisCam', cd); sc.collection.objects.link(co); sc.camera = co
    for fr in meta['frames']:
        c = fr['cam']; k = fr['k']
        r, u, f = Vector(c['r']), Vector(c['u']), Vector(c['f'])
        M = Matrix(((r.x, u.x, -f.x, c['pos'][0]), (r.y, u.y, -f.y, c['pos'][1]), (r.z, u.z, -f.z, c['pos'][2]), (0, 0, 0, 1)))
        co.matrix_world = M
        co.keyframe_insert('location', frame=k); co.keyframe_insert('rotation_euler', frame=k)
        cd.lens = c['lens_mm']; cd.keyframe_insert('lens', frame=k)
    return co


class Whale:
    def __init__(self, look, meta):
        bpy.ops.import_scene.gltf(filepath=str(ASSETS / 'wh01_v20_hero.glb'))
        obs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
        self.ob = obs[0]
        self.ob.matrix_world = Matrix.Identity(4)
        me = self.ob.data
        self.V0 = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', self.V0)
        self.V0 = self.V0.reshape(-1, 3)
        # the hero eyes sit ~0.1 m inside their sockets, so at R14's distance the body hides them; the
        # previs always shows a dark eye on the side facing the camera -> bring the eyes out to the skin
        eye_mi = [i for i, m in enumerate(me.materials) if 'Eye' in m.name]
        if eye_mi:
            mi = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('material_index', mi)
            ev = sorted({v for p_, k in zip(me.polygons, mi) if k in eye_mi for v in p_.vertices})
            self.V0[ev, 1] *= look.get('eye_out', 1.08)
        # hero glb -> previs local frame: x forward (head +x), z up, y side (the body is mirror
        # symmetric, so the side sign does not change the shape; checked against BODY_V bounds)
        print('hero bounds', self.V0.min(0).round(2), self.V0.max(0).round(2), 'previs', w.BODY_V.min(0).round(2), w.BODY_V.max(0).round(2))
        self.path = w.WhalePath()
        if 'stroke_phase0' in meta:          # same retime as the previs (else the tail stroke is out of phase)
            self.path.retime(phase0=meta['stroke_phase0'], fast_tau=meta.get('fast_stroke_tau'))
        else:
            print('  [warn] cut.json has no stroke_phase0: re-export the cut (tail stroke will not match the previs)')
        self.contact = meta['ev_contact']
        self.glow = me.attributes.get('pv_glow') or me.attributes.new('pv_glow', 'FLOAT', 'POINT')
        self.hue = me.attributes.get('pv_hue') or me.attributes.new('pv_hue', 'FLOAT', 'POINT')
        self.look = look
        # v16 (R18): the whale gives its light back to the moon (previs melt_alpha)
        self.melt_on = any(f['whale'].get('melt', 0.0) > 0 for f in meta['frames'])
        if self.melt_on:
            self.mlift = me.attributes.new('pv_mlift', 'FLOAT', 'POINT')
            self.malpha = me.attributes.new('pv_malpha', 'FLOAT', 'POINT')
        for m in me.materials:
            self._drop_vertex_tint(m)
            self._add_emission(m)
            if self.melt_on:
                self._add_melt(m)

    def _add_melt(self, m):
        """Each part, tail first, takes on the moon's colour (pv_mlift) and then becomes transparent
        (pv_malpha) - no flash, the moon itself does nothing (previs v14.9b)."""
        nt = m.node_tree; N = nt.nodes; L = nt.links
        b = next((n for n in N if n.type == 'BSDF_PRINCIPLED'), None)
        if b is not None and 'Eye' not in m.name and b.inputs['Emission Strength'].is_linked:
            ml = N.new('ShaderNodeAttribute'); ml.attribute_name = 'pv_mlift'
            src_c = b.inputs['Emission Color'].links[0].from_socket if b.inputs['Emission Color'].is_linked else None
            mc = N.new('ShaderNodeMix'); mc.data_type = 'RGBA'; L.new(ml.outputs['Fac'], mc.inputs['Factor'])
            if src_c is not None:
                L.new(src_c, mc.inputs[6])
            mc.inputs[7].default_value = (*_lin(MOON_FACE), 1)
            L.new(mc.outputs[2], b.inputs['Emission Color'])
            src_s = b.inputs['Emission Strength'].links[0].from_socket
            inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
            L.new(ml.outputs['Fac'], inv.inputs[1])
            t1 = N.new('ShaderNodeMath'); t1.operation = 'MULTIPLY'; L.new(src_s, t1.inputs[0]); L.new(inv.outputs[0], t1.inputs[1])
            t2 = N.new('ShaderNodeMath'); t2.operation = 'MULTIPLY'; L.new(ml.outputs['Fac'], t2.inputs[0])
            t2.inputs[1].default_value = self.look.get('melt_emit', 6.0)
            sm = N.new('ShaderNodeMath'); sm.operation = 'ADD'; L.new(t1.outputs[0], sm.inputs[0]); L.new(t2.outputs[0], sm.inputs[1])
            L.new(sm.outputs[0], b.inputs['Emission Strength'])
        out = next((n for n in N if n.type == 'OUTPUT_MATERIAL'), None)
        if out is None or not out.inputs['Surface'].is_linked:
            return
        src = out.inputs['Surface'].links[0].from_socket
        al = N.new('ShaderNodeAttribute'); al.attribute_name = 'pv_malpha'
        tr = N.new('ShaderNodeBsdfTransparent'); mx = N.new('ShaderNodeMixShader')
        L.new(al.outputs['Fac'], mx.inputs['Fac']); L.new(tr.outputs[0], mx.inputs[1]); L.new(src, mx.inputs[2])
        L.new(mx.outputs[0], out.inputs['Surface'])
        try_set(m, surface_render_method='BLENDED', use_backface_culling=True)

    @staticmethod
    def _drop_vertex_tint(m):
        """The hero glb's COLOR_0 is rig data (R: head->tail, G: fin mask), not paint. The glTF importer
        multiplies it into Base Color, which turned the tail pink and the pectoral fins yellow-green
        (the identity sheet WH01 says: no markings). Feed Base Color from the other Mix input instead."""
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            return
        for l in list(b.inputs['Base Color'].links):
            mix = l.from_node
            if mix.type != 'MIX':
                continue
            cols = [s for s in mix.inputs if s.type == 'RGBA' and s.enabled]
            keep = [s for s in cols if not (s.is_linked and s.links[0].from_node.type == 'ATTRIBUTE')]
            if len(keep) != 1 or len(keep) == len(cols):
                continue
            k = keep[0]
            if k.is_linked:
                nt.links.new(k.links[0].from_socket, b.inputs['Base Color'])
            else:
                nt.links.remove(l); b.inputs['Base Color'].default_value = k.default_value

    def _add_emission(self, m):
        """Self-light as the previs draws it (ruosuen_v14_previs.py whale_layer):
        emission = glow x opal colour along the body x form, form = 1 - whale_form * (grazing),
        i.e. 0.4 + 0.6 * facing for whale_form 0.6 -> the edges stay darker and the body reads as 3D
        inside its own glow. The eye does not glow (previs: a dark eye)."""
        nt = m.node_tree; N = nt.nodes; L = nt.links
        b = next((n for n in N if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            return
        if 'Eye' in m.name:
            b.inputs['Emission Strength'].default_value = 0.0
            b.inputs['Base Color'].default_value = (0.006, 0.008, 0.012, 1)
            try_set(b.inputs['Roughness'], default_value=0.15)
            return
        at = N.new('ShaderNodeAttribute'); at.attribute_name = 'pv_glow'
        lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
        form = N.new('ShaderNodeMath'); form.operation = 'MULTIPLY_ADD'
        L.new(lw.outputs['Facing'], form.inputs[0])
        form.inputs[1].default_value = -self.look['whale_form']; form.inputs[2].default_value = 1.0
        mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
        L.new(at.outputs['Fac'], mul.inputs[0]); L.new(form.outputs[0], mul.inputs[1])
        k = N.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; k.inputs[1].default_value = self.look['whale_emit']
        L.new(mul.outputs[0], k.inputs[0])
        L.new(k.outputs[0], b.inputs['Emission Strength'])
        # opal colour: the glb's COLOR_0.R runs 1 at the tail -> 0 at the head (rig data), so hue = 1 - R
        vc = N.new('ShaderNodeVertexColor'); vc.layer_name = 'Color'
        sep = N.new('ShaderNodeSeparateColor'); L.new(vc.outputs['Color'], sep.inputs['Color'])
        inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
        L.new(sep.outputs[0], inv.inputs[1])
        ramp = N.new('ShaderNodeValToRGB'); cr = ramp.color_ramp
        for i, (pos, rgb) in enumerate(pal(self.look)['glow']):
            e = cr.elements[i] if i < len(cr.elements) else cr.elements.new(pos)
            e.position = pos; e.color = (*[(c / 255.0) ** 2.2 for c in rgb], 1)
        L.new(inv.outputs[0], ramp.inputs['Fac'])
        mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
        mix.inputs['Factor'].default_value = self.look['whale_opal']
        mix.inputs[6].default_value = (*pal(self.look)['light'], 1)
        L.new(ramp.outputs['Color'], mix.inputs[7])
        col = mix.outputs[2]
        P_ = pal(self.look)
        hue_at = None
        if 'gold' in P_:                           # v15i: the pale-gold wave (pv_hue, set per frame)
            hue_at = N.new('ShaderNodeAttribute'); hue_at.attribute_name = 'pv_hue'
            mg_ = N.new('ShaderNodeMix'); mg_.data_type = 'RGBA'
            L.new(hue_at.outputs['Fac'], mg_.inputs['Factor']); L.new(col, mg_.inputs[6])
            mg_.inputs[7].default_value = (*[(c / 255.0) ** 2.2 for c in P_['gold']], 1)
            col = mg_.outputs[2]
        # v15d: paint inside the glow - the gouache albedo (strokes, ventral grooves) modulates the light,
        # the back facing the sky is brighter, the underside cooler and darker (as in the key paintings)
        tex = next((n for n in N if n.type == 'TEX_IMAGE'), None)
        if tex is not None and self.look['whale_tex'] > 0:
            bw = N.new('ShaderNodeRGBToBW'); L.new(tex.outputs['Color'], bw.inputs[0])
            mr = N.new('ShaderNodeMapRange'); mr.clamp = True
            mr.inputs['From Min'].default_value = 0.4; mr.inputs['From Max'].default_value = 1.0
            mr.inputs['To Min'].default_value = 1.0 - self.look['whale_tex']; mr.inputs['To Max'].default_value = 1.0
            L.new(bw.outputs[0], mr.inputs['Value'])
            mt = N.new('ShaderNodeMix'); mt.data_type = 'RGBA'; mt.blend_type = 'MULTIPLY'
            mt.inputs['Factor'].default_value = 1.0
            L.new(col, mt.inputs[6]); L.new(mr.outputs['Result'], mt.inputs[7]); col = mt.outputs[2]
        geo = N.new('ShaderNodeNewGeometry'); sz = N.new('ShaderNodeSeparateXYZ')
        L.new(geo.outputs['Normal'], sz.inputs[0])
        neg = N.new('ShaderNodeMath'); neg.operation = 'MULTIPLY'; neg.use_clamp = True
        neg.inputs[1].default_value = -self.look['whale_belly']; L.new(sz.outputs['Z'], neg.inputs[0])
        mb = N.new('ShaderNodeMix'); mb.data_type = 'RGBA'
        L.new(neg.outputs[0], mb.inputs['Factor']); L.new(col, mb.inputs[6]); mb.inputs[7].default_value = (*pal(self.look)['belly'], 1)
        out_col = mb.outputs[2]
        if 'rim' in P_ and self.look.get('whale_rim', 0.9) > 0:     # the light source: white core, coloured rim
            rf = N.new('ShaderNodeMath'); rf.operation = 'MULTIPLY'; rf.use_clamp = True
            rf.inputs[1].default_value = self.look.get('whale_rim', 0.9) * 1.6
            L.new(lw.outputs['Facing'], rf.inputs[0])
            mr_ = N.new('ShaderNodeMix'); mr_.data_type = 'RGBA'
            L.new(rf.outputs[0], mr_.inputs['Factor']); L.new(out_col, mr_.inputs[6]); mr_.inputs[7].default_value = (*P_['rim'], 1)
            if hue_at is not None:                 # the rim goes gold with the wave too
                rg_ = N.new('ShaderNodeMix'); rg_.data_type = 'RGBA'
                L.new(hue_at.outputs['Fac'], rg_.inputs['Factor'])
                rg_.inputs[6].default_value = (*P_['rim'], 1); rg_.inputs[7].default_value = (*P_['gold_rim'], 1)
                L.new(rg_.outputs[2], mr_.inputs[7])
            out_col = mr_.outputs[2]
        L.new(out_col, b.inputs['Emission Color'])
        lo, hi = self.look['whale_top']
        top = N.new('ShaderNodeMapRange'); top.inputs['From Min'].default_value = -1.0; top.inputs['From Max'].default_value = 1.0
        top.inputs['To Min'].default_value = lo; top.inputs['To Max'].default_value = hi
        L.new(sz.outputs['Z'], top.inputs['Value'])
        k2 = N.new('ShaderNodeMath'); k2.operation = 'MULTIPLY'
        L.new(k.outputs[0], k2.inputs[0]); L.new(top.outputs['Result'], k2.inputs[1])
        L.new(k2.outputs[0], b.inputs['Emission Strength'])

    def update(self, fr):
        wh = fr['whale']; tau = fr['tau']
        V = w.deform(self.V0, tau, self.path, amp=wh['amp'])
        frame = (np.array(wh['p']), np.array(wh['fwd']), np.array(wh['left']), np.array(wh['up']))
        Wv = w.world_vertices(V, frame)
        me = self.ob.data
        me.vertices.foreach_set('co', Wv.ravel())
        # glow: head->tail ignition (previs glow_level) + the light pulse after each stroke (previs pulse)
        x = self.V0[:, 0]
        dt = tau - self.contact
        reach = (w.XMAX - x) / (w.XMAX - w.XMIN) * 4.2
        g = w.smooth((dt - reach) / 1.4)
        q = self.path.stroke_q(tau)
        u = np.mod(q - 0.42 - (w.XMAX - x) / (w.XMAX - w.XMIN) * 0.30, 1.0)
        pulse = np.exp(-(u / 0.07) ** 2) + np.exp(-((u - 1) / 0.07) ** 2)
        val = g * (0.75 + 0.25 * fr['whale_light']['I']) * (1 + 0.35 * pulse)
        if self.melt_on:                    # per part, tail first (previs melt_alpha), instead of dimming it all
            mp = wh.get('melt', 0.0)
            u = (x - w.XMIN) / (w.XMAX - w.XMIN)            # 0 tail .. 1 head
            if mp > 0:
                lift = w.smooth((mp * 1.45 + 0.30 - u) / 0.35); alpha = 1 - w.smooth((mp * 1.45 - u) / 0.40)
            else:
                lift = np.zeros_like(u); alpha = np.ones_like(u)
            self.mlift.data.foreach_set('value', np.asarray(lift, np.float32))
            self.malpha.data.foreach_set('value', np.asarray(alpha, np.float32))
        else:
            val = val * (1 - wh.get('melt', 0.0))
        self.glow.data.foreach_set('value', val.astype(np.float32))
        # v15i: hue. The stroke's light pulse carries a pale-gold wave head->tail (same timing as the previs
        # pulse, a wider band and an afterglow), and in the glide a slow opal play drifts along the body
        xn = (w.XMAX - x) / (w.XMAX - w.XMIN)                 # 0 head .. 1 tail
        ug = np.mod(q - 0.40 - xn * 0.30, 1.0)
        band = np.exp(-(ug / 0.10) ** 2) + np.exp(-((ug - 1) / 0.10) ** 2)
        after = np.where(ug < 0.45, np.exp(-ug / 0.16), 0.0)
        hp = np.clip(band + 0.65 * after, 0, 1) * self.look.get('gold_pulse', 1.0)
        sh = self.look.get('gold_shimmer', 0.25) * (0.5 + 0.5 * np.sin(2 * np.pi * (0.9 * xn - tau / 6.0))) ** 3
        hue = np.clip(hp + sh, 0, 1) * g * ('gold' in pal(self.look))
        self.hue.data.foreach_set('value', hue.astype(np.float32))
        fr['_gold'] = float(np.clip(np.mean(hue) * 1.6, 0, 1))      # how gold the whale's light is now
        me.update()


class Petals:
    """Camera-facing billboards rebuilt every frame from the previs petal positions.
    Far petals are kept at >= petal_min_px pixels (the previs draws far flakes the same way)."""
    def __init__(self, look, res_w):
        self.look = look; self.res_w = res_w
        me = bpy.data.meshes.new('Petals'); self.ob = bpy.data.objects.new('Petals', me)
        bpy.context.scene.collection.objects.link(self.ob)
        m = bpy.data.materials.new('PetalAdd'); try_set(m, use_nodes=True)
        try_set(m, surface_render_method='BLENDED', use_backface_culling=False)
        nt = m.node_tree; N = nt.nodes
        for n in list(N):
            if n.type != 'OUTPUT_MATERIAL':
                N.remove(n)
        out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
        col = N.new('ShaderNodeAttribute'); col.attribute_name = 'pv_col'
        uv = N.new('ShaderNodeUVMap')
        # soft disc mask from UV
        sep = N.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs['UV'], sep.inputs[0])
        vm = N.new('ShaderNodeVectorMath'); vm.operation = 'DISTANCE'; vm.inputs[1].default_value = (0.5, 0.5, 0.0)
        nt.links.new(uv.outputs['UV'], vm.inputs[0])
        ramp = N.new('ShaderNodeMapRange'); ramp.inputs['From Min'].default_value = 0.5; ramp.inputs['From Max'].default_value = 0.0
        nt.links.new(vm.outputs['Value'], ramp.inputs['Value'])
        em = N.new('ShaderNodeEmission'); nt.links.new(col.outputs['Color'], em.inputs['Color'])
        nt.links.new(ramp.outputs['Result'], em.inputs['Strength'])
        tr = N.new('ShaderNodeBsdfTransparent')
        add = N.new('ShaderNodeAddShader')
        nt.links.new(tr.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
        nt.links.new(add.outputs[0], out.inputs['Surface'])
        me.materials.append(m)

    @staticmethod
    def _h(i, j, c):
        """Stable pseudo-random 0..1 from (petal id, clone, channel): the same every frame."""
        return np.mod(np.sin(i * 12.9898 + j * 78.233 + c * 37.719) * 43758.5453, 1.0)

    def _densify(self, d):
        """v15e: more petals along the same flow. Each previs petal gets K-1 companions at a fixed offset
        (keyed by its id, so they move with it and never jump), like the previs' own statistical layers."""
        K = int(round(self.look['petal_dense']))
        arr = {k: np.asarray(d[k]) for k in ('p', 'fruit', 'spin', 'bright', 'kind')}
        ids = np.asarray(d['idx']).astype(np.float64) if 'idx' in d.files else None
        arr['idx'] = ids if ids is not None else np.zeros(len(arr['p']))
        if self.look.get('near_n', 0) > 0:
            # v14.10: the previs near-camera snow (kind 1) is drawn by NearSnow as real petals instead
            keep = arr['kind'] == 0
            arr = {k: v[keep] for k, v in arr.items()}
            ids = None if ids is None else ids[keep]
        if K <= 1 or ids is None or len(arr['p']) == 0:
            return arr
        out = {k: [v] for k, v in arr.items()}
        for j in range(1, K):
            v = np.stack([self._h(ids, j, c) - 0.5 for c in range(3)], 1)
            v /= np.linalg.norm(v, axis=1, keepdims=True) + 1e-9
            rad = self.look['dense_r'] * (0.15 + 0.85 * self._h(ids, j, 3)) ** (1 / 3)
            out['p'].append(arr['p'] + v * rad[:, None])
            out['fruit'].append(arr['fruit'] * (self._h(ids, j, 4) < 0.5))
            out['spin'].append(np.mod(arr['spin'].astype(np.float64) + 2 * np.pi * self._h(ids, j, 5), 2 * np.pi))
            out['bright'].append(arr['bright'] * (0.7 + 0.3 * self._h(ids, j, 6)))
            out['kind'].append(arr['kind'])
            out['idx'].append(arr['idx'] + 1e7 * j)
        return {k: np.concatenate(v) for k, v in out.items()}

    def add_near(self, look):
        """v16 (R13): the camera stands inside the colony, so simulated petals pass within a metre or two of the
        lens; as soft additive discs they read as blobs. Those within petal_near_r are drawn instead as real
        petals (the near blizzard's texture, light and glints), tumbling by their previs spin."""
        import types
        me = bpy.data.meshes.new('PetalsNear'); self.obn = bpy.data.objects.new('PetalsNear', me)
        bpy.context.scene.collection.objects.link(self.obn)
        me.materials.append(NearSnow._material(types.SimpleNamespace(look=look)))
        coll = bpy.data.collections.get('NearReceivers')
        if coll is not None:
            coll.objects.link(self.obn)

    def _update_near(self, d):
        me = self.obn.data; me.clear_geometry()
        n = len(d['p'])
        if n == 0:
            return
        ids = d['idx']; H = lambda j, c: self._h(ids, j, c) - 0.5
        def nrm(v):
            return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
        ax = nrm(np.stack([H(11, c) for c in range(3)], 1)); a0 = nrm(np.stack([H(12, c) for c in range(3)], 1))
        b0 = nrm(np.cross(a0, np.stack([H(13, c) for c in range(3)], 1)))
        th = d['spin'].astype(np.float64)
        A = NearSnow._rot(a0, ax, th); B = NearSnow._rot(b0, ax, th)
        sz = self.look.get('near_size', 0.03) * (0.85 + 0.4 * self._h(ids, 14, 0))
        C = d['p'].astype(np.float64); w_ = (0.39 * sz)[:, None]; h_ = (0.5 * sz)[:, None]
        V = np.stack([C - w_ * A - h_ * B, C + w_ * A - h_ * B, C + w_ * A + h_ * B, C - w_ * A + h_ * B], 1)
        me.vertices.add(n * 4); me.vertices.foreach_set('co', V.ravel())
        me.loops.add(n * 4); me.loops.foreach_set('vertex_index', np.arange(n * 4, dtype=np.int32))
        me.polygons.add(n); me.polygons.foreach_set('loop_start', np.arange(0, n * 4, 4, dtype=np.int32))
        try:
            me.polygons.foreach_set('loop_total', np.full(n, 4, np.int32))
        except Exception:
            pass
        me.update(calc_edges=True)
        uvl = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
        uvl.data.foreach_set('uv', np.tile(np.array([0, 0, 1, 0, 1, 1, 0, 1], np.float32), n))
        at = me.attributes.get('pv_alpha') or me.attributes.new('pv_alpha', 'FLOAT', 'POINT')
        at.data.foreach_set('value', np.ones(n * 4, np.float32))
        me.update()

    def update(self, fr, npz):
        d = self._densify(np.load(npz))
        if getattr(self, 'obn', None) is not None:
            cp0 = np.array(fr['cam']['pos'])
            nr = np.linalg.norm(d['p'].astype(np.float64) - cp0, axis=1) < self.look.get('petal_near_r', 5.0)
            self._update_near({k: v[nr] for k, v in d.items()})
            d = {k: v[~nr] for k, v in d.items()}
        p = d['p'].astype(np.float64); n = len(p)
        me = self.ob.data
        me.clear_geometry()
        if n == 0:
            return
        c = fr['cam']; cp = np.array(c['pos']); r = np.array(c['r']); u = np.array(c['u'])
        dist = np.linalg.norm(p - cp, axis=1)
        px = (36.0 / c['lens_mm']) / self.res_w            # metres per pixel at 1 m
        real = np.where(d['kind'] == 1, 0.028, 0.032)       # petal ~3 cm
        s = np.maximum(real, dist * px * self.look['petal_min_px'])
        vis = np.clip(real / s, 0.0, 1.0) ** 0.5            # tiny far flakes: dimmer, not invisible
        spin = d['spin'].astype(np.float64)
        flick = 0.35 + 0.65 * np.abs(np.cos(spin))
        wdt = s * (0.45 + 0.55 * np.abs(np.cos(spin)))      # edge-on flutter for the near ones
        a = (spin * 0.37)[:, None]
        ex = np.cos(a) * r + np.sin(a) * u; ey = -np.sin(a) * r + np.cos(a) * u
        hx = (wdt / 2)[:, None] * ex; hy = (s / 2)[:, None] * ey
        V = np.empty((n, 4, 3))
        V[:, 0] = p - hx - hy; V[:, 1] = p + hx - hy; V[:, 2] = p + hx + hy; V[:, 3] = p - hx + hy
        me.vertices.add(n * 4); me.vertices.foreach_set('co', V.ravel())
        me.loops.add(n * 4); me.loops.foreach_set('vertex_index', np.arange(n * 4, dtype=np.int32))
        me.polygons.add(n); me.polygons.foreach_set('loop_start', np.arange(0, n * 4, 4, dtype=np.int32))
        try:
            me.polygons.foreach_set('loop_total', np.full(n, 4, np.int32))
        except Exception:
            pass
        bright = np.clip(d['bright'].astype(np.float64), 0, 3)
        fruit = d['fruit'].astype(np.float64)
        lit = np.clip((bright - 0.35) / 1.0, 0, 0.85)[:, None]
        plit = np.array(gold_mix(self.look, pal(self.look)['petal_lit'], 'gold_petal', fr))
        pc = np.array(PETAL)[None] * (1 - lit) + plit[None] * lit
        colv = (pc * (self.look['petal_emit'] * bright * flick * vis)[:, None]
                + np.array(FRUIT)[None] * (self.look['fruit_emit'] * 0.45 * fruit * np.clip(bright, 0, 1) * vis)[:, None])
        me.update(calc_edges=True)
        uvl = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
        uvl.data.foreach_set('uv', np.tile(np.array([0, 0, 1, 0, 1, 1, 0, 1], np.float32), n))
        at = me.attributes.get('pv_col') or me.attributes.new('pv_col', 'FLOAT_COLOR', 'POINT')
        C = np.ones((n, 4, 4), np.float32); C[:, :, :3] = colv[:, None, :]
        at.data.foreach_set('color', C.ravel())
        me.update()


class NearSnow:
    """v15e (author's request 2026-11-25): a natural petal blizzard near the camera - real petal shapes
    (petal_rgba: white with a golden base), tumbling on three axes, rising while drifting toward the whale
    (the 'snow falling into the sky' of v14.9b), backlit by the whale (translucent) and catching its light
    as they turn. Deterministic: positions are a closed-form function of time, so any frame renders alone.
    NOTE: the previs keeps R14's foreground clear; this layer is an author-requested change.
    Built in the camera frame of the cut's first frame (R14's camera is fixed).
    v16 world mode (look near_world=1, for a camera that turns in place, e.g. R15): the petals live in a
    world-space sector around the camera position that covers every view of the cut (so they stay put while
    the camera pans), ride the flow of the simulated snow around the camera (cut.json near_flow: the river the
    whale brings, then lets go), and move in world time (R15's slow moment slows them; the previs local_snow
    does the same)."""
    def __init__(self, look, meta):
        self.look = look
        c = meta['frames'][0]['cam']
        self.cp, self.r, self.u, self.f = (np.array(c[k], float) for k in ('pos', 'r', 'u', 'f'))
        self.lens = c['lens_mm']
        self.world = look.get('near_world', 0.0) > 0.5
        if self.world:
            self._init_world(look, meta)
        else:
            self._init_screen(look)
        me = bpy.data.meshes.new('NearSnow'); self.ob = bpy.data.objects.new('NearSnow', me)
        bpy.context.scene.collection.objects.link(self.ob)
        me.materials.append(self._material())
        # the whale's light, for the near petals only (light linking): backlight + glints
        ld = bpy.data.lights.new('NearGlint', 'POINT'); ld.color = pal(look).get('near_light', pal(look)['light']); ld.energy = look['near_light']
        try_set(ld, shadow_soft_size=8.0, use_shadow=False, volume_factor=0.0)
        self.light = bpy.data.objects.new('NearGlint', ld); bpy.context.scene.collection.objects.link(self.light)
        try:
            coll = bpy.data.collections.new('NearReceivers'); coll.objects.link(self.ob)
            self.light.light_linking.receiver_collection = coll
        except Exception as e:
            print('  [skip] near light linking:', e)

    def _init_world(self, look, meta):
        g = np.random.default_rng(20261126)
        cams = [f['cam'] for f in meta['frames']]
        if np.ptp(np.array([c['pos'] for c in cams]), 0).max() > 0.05:
            print('  [warn] NearSnow world mode: the camera moves; the sector is centred on its first position')
        fm = np.array([c['f'] for c in cams]).mean(0); fm /= np.linalg.norm(fm)
        sr = np.cross(fm, (0.0, 0.0, 1.0)); sr /= np.linalg.norm(sr); su = np.cross(sr, fm)
        self.B = np.stack([sr, su, fm])
        # nested periodic boxes around the camera, one per distance band (near / mid / far): a periodic box
        # keeps its density exactly under any flow (wrapping in spherical shells piled the petals up at the lens),
        # and each band shows only its own shell, crossfading into the next. near_n = petals in one view, spread
        # evenly in depth like the previs local_snow (so more of them near the lens than uniform air would give).
        edges = list(look.get('near_edges', (look['near_zmin'], 4.0, 9.0, look['near_zmax'])))
        self.z0, self.z1 = edges[0], edges[-1]
        ax_, ay_ = 18.0 / self.lens, 10.125 / self.lens
        per_m = look['near_n'] / (self.z1 - self.z0)
        nb_ = len(edges) - 1
        cx = [0.3 * min(edges[j] - edges[j - 1], edges[j + 1] - edges[j]) for j in range(1, nb_)]   # crossfade half-widths
        P0, band, half, fades = [], [], [], []
        for i in range(nb_):
            a, b = edges[i], edges[i + 1]
            lo, lw = (a, 0.3 * (b - a)) if i == 0 else (a - cx[i - 1], 2 * cx[i - 1])          # fade in
            hi, hw = (b - 0.3 * (b - a), 0.3 * (b - a)) if i == nb_ - 1 else (b - cx[i], 2 * cx[i])   # fade out
            dens = per_m * (b - a) / ((b ** 3 - a ** 3) / 3 * 4 * ax_ * ay_)
            hb = hi + hw + 0.5
            nb = int(dens * (2 * hb) ** 3)
            P0.append(g.uniform(-hb, hb, (nb, 3))); band.append(np.full(nb, i)); half.append(np.full(nb, hb))
            fades.append((lo, lw, hi, hw))
            print(f'  NearSnow band {a}-{b} m: {nb} petals ({dens:.3f} per m3)')
        self.P0 = self.cp + np.concatenate(P0) @ self.B; self.half = np.concatenate(half)
        self.band = np.concatenate(band); fd = np.array(fades)[self.band]
        self.blo, self.blw, self.bhi, self.bhw = fd[:, 0], fd[:, 1], fd[:, 2], fd[:, 3]
        n = len(self.P0)
        # each petal rides the snow's flow a little differently, plus its own drift (previs local_snow R15)
        k0, k1 = look.get('near_couple', (0.35, 0.85))
        self.cpl = g.uniform(k0, k1, n)
        dm = np.array(look.get('near_drift', (-0.4, 0.5, -0.55))); ds = np.array(look.get('near_drift_sd', (0.9, 0.9, 0.35)))
        self.vd = dm[None] + g.standard_normal((n, 3)) * ds[None]
        fl = np.array([f.get('near_flow', (0.0, 0.0, 0.0)) for f in meta['frames']], float)
        tau = np.array([f['tau'] for f in meta['frames']], float)
        D = np.cumsum(fl * np.diff(tau, prepend=tau[0])[:, None], 0)
        self.flowD = {f['k']: D[i] for i, f in enumerate(meta['frames'])}
        dtau = np.diff(tau, append=tau[-1] + (tau[-1] - tau[-2] if len(tau) > 1 else 1 / 24))
        self.dtau = {f['k']: float(dtau[i]) for i, f in enumerate(meta['frames'])}   # world time per frame
        self.tau0 = tau[0]
        self.wa = g.uniform(0.15, 0.5, (n, 3)); self.ww = g.uniform(0.5, 1.7, (n, 3)); self.wp = g.uniform(0, 2 * np.pi, (n, 3))
        ax = g.standard_normal((n, 3)); self.ax = ax / np.linalg.norm(ax, axis=1, keepdims=True)
        self.om = g.uniform(1.5, 5.0, n) * np.where(g.random(n) < 0.5, -1, 1); self.ph = g.uniform(0, 2 * np.pi, n)
        q = g.standard_normal((n, 3)); self.a0 = q / np.linalg.norm(q, axis=1, keepdims=True)
        b = np.cross(self.a0, g.standard_normal((n, 3))); self.b0 = b / np.linalg.norm(b, axis=1, keepdims=True)
        self.s = look['near_size'] * g.uniform(0.8, look.get('near_size_max', 1.3), n)
        self.grow = g.random(n)
        self.wt = np.ones(n)
        print(f'  NearSnow world: {n} petals in {nb_} bands, r {self.z0}-{self.z1} m')

    def _init_screen(self, look):
        n = int(look['near_n'])
        g = np.random.default_rng(20261125)
        z0, z1 = look['near_zmin'], look['near_zmax']
        zp = look.get('near_zpow', 0.0)
        if zp > 0:                                  # v15f: most where a petal reads as a petal (3-25 m)
            self.z = z0 + (z1 - z0) * g.random(n) ** zp
        else:
            self.z = np.sqrt(z0 ** 2 + g.random(n) * (z1 ** 2 - z0 ** 2))      # more of the far ones (volume)
        self.hw = self.z * (18.0 / self.lens); self.hh = self.z * (10.125 / self.lens)
        # they travel along the stream (normalised screen: from lower right up toward the whale's wake) and
        # gather around it, leaving the dark side calm; s wraps far off screen, the lateral offset is fixed
        D = np.array(look.get('near_dir', (-0.66, 0.75))); D = D / np.linalg.norm(D); Nn = np.array([D[1], -D[0]])
        self.D, self.N = D, Nn
        band = g.random(n) < look.get('near_band', 0.65)
        self.l = np.where(band, g.normal(look.get('near_band_c', 0.07), 0.28, n), g.uniform(-1.4, 1.4, n))
        sp = look.get('near_speed', 1.0)
        self.s0 = g.uniform(-1.6, 1.6, n); self.sv = g.uniform(0.20, 0.42, n) * sp  # normalised units / s
        # gusts: the speed swells and eases in slow waves that travel across the stream and in depth
        self.gp = 2.0 * self.l + 0.08 * self.z + g.normal(0, 0.3, n)
        self.vz = g.uniform(-0.15, 0.15, n)
        self.fa = g.uniform(0.010, 0.030, (n, 3)) * self.z[:, None]; self.fw = g.uniform(0.5, 1.6, (n, 3)); self.fp = g.uniform(0, 2 * np.pi, (n, 3))
        ax = g.standard_normal((n, 3)); self.ax = ax / np.linalg.norm(ax, axis=1, keepdims=True)
        self.om = g.uniform(1.2, 4.0, n) * np.sqrt(sp) * np.where(g.random(n) < 0.5, -1, 1); self.ph = g.uniform(0, 2 * np.pi, n)
        q = g.standard_normal((n, 3)); self.a0 = q / np.linalg.norm(q, axis=1, keepdims=True)
        b = np.cross(self.a0, g.standard_normal((n, 3))); self.b0 = b / np.linalg.norm(b, axis=1, keepdims=True)
        self.s = look['near_size'] * g.uniform(0.8, look.get('near_size_max', 1.3), n)

    def _material(self):
        m = bpy.data.materials.new('NearPetal'); try_set(m, use_nodes=True)
        try_set(m, surface_render_method='DITHERED', use_backface_culling=False)
        nt = m.node_tree; N = nt.nodes; L = nt.links
        for n in list(N):
            if n.type != 'OUTPUT_MATERIAL':
                N.remove(n)
        out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
        tex = N.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(ASSETS.parent / 'textures' / 'petal_rgba.png'))
        dif = N.new('ShaderNodeBsdfDiffuse'); L.new(tex.outputs['Color'], dif.inputs['Color'])
        # whiter than the photo (its golden base stays at the root), a cool translucent glow when backlit,
        # and a glossy sheen that flashes as a petal turns toward the whale's light
        wht = N.new('ShaderNodeMix'); wht.data_type = 'RGBA'; wht.inputs['Factor'].default_value = 0.35
        L.new(tex.outputs['Color'], wht.inputs[6]); wht.inputs[7].default_value = (0.95, 0.97, 1.0, 1)
        L.new(wht.outputs[2], dif.inputs['Color'])
        trl = N.new('ShaderNodeBsdfTranslucent'); trl.inputs['Color'].default_value = (*pal(self.look)['trl'], 1)
        mx = N.new('ShaderNodeMixShader'); mx.inputs['Fac'].default_value = 0.35
        L.new(dif.outputs[0], mx.inputs[1]); L.new(trl.outputs[0], mx.inputs[2])
        gl = N.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.32
        gl.inputs['Color'].default_value = (0.95, 0.96, 1.0, 1)
        mg = N.new('ShaderNodeAddShader'); L.new(mx.outputs[0], mg.inputs[0]); L.new(gl.outputs[0], mg.inputs[1])
        em = N.new('ShaderNodeEmission'); L.new(wht.outputs[2], em.inputs['Color']); em.inputs['Strength'].default_value = self.look['near_emit']
        add = N.new('ShaderNodeAddShader'); L.new(mg.outputs[0], add.inputs[0]); L.new(em.outputs[0], add.inputs[1])
        tr = N.new('ShaderNodeBsdfTransparent')
        # air between: the farther petals fade into the haze (the near layer is rendered without the air)
        cd = N.new('ShaderNodeCameraData')
        fade = N.new('ShaderNodeMapRange'); fade.clamp = True
        fade.inputs['From Min'].default_value = self.look.get('near_fade', (20.0, 60.0))[0]
        fade.inputs['From Max'].default_value = self.look.get('near_fade', (20.0, 60.0))[1]
        fade.inputs['To Min'].default_value = 1.0; fade.inputs['To Max'].default_value = 0.35
        L.new(cd.outputs['View Distance'], fade.inputs['Value'])
        am = N.new('ShaderNodeMath'); am.operation = 'MULTIPLY'
        L.new(tex.outputs['Alpha'], am.inputs[0]); L.new(fade.outputs['Result'], am.inputs[1])
        pa = N.new('ShaderNodeAttribute'); pa.attribute_name = 'pv_alpha'      # v16: thinned shutter streaks
        am2 = N.new('ShaderNodeMath'); am2.operation = 'MULTIPLY'
        L.new(am.outputs[0], am2.inputs[0]); L.new(pa.outputs['Fac'], am2.inputs[1])
        fin = N.new('ShaderNodeMixShader'); L.new(am2.outputs[0], fin.inputs['Fac'])
        L.new(tr.outputs[0], fin.inputs[1]); L.new(add.outputs[0], fin.inputs[2])
        L.new(fin.outputs[0], out.inputs['Surface'])
        return m

    @staticmethod
    def _rot(v, k, th):
        c, s_ = np.cos(th)[:, None], np.sin(th)[:, None]
        return v * c + np.cross(k, v) * s_ + k * np.sum(k * v, 1, keepdims=True) * (1 - c)

    def _world_pos(self, fr):
        dt = fr['tau'] - self.tau0
        P = (self.P0 + self.cpl[:, None] * self.flowD.get(fr['k'], np.zeros(3))[None] + self.vd * dt
             + self.wa * np.sin(self.ww * dt + self.wp))
        rel = (P - self.cp) @ self.B.T
        h = self.half[:, None]
        rel = np.mod(rel + h, 2 * h) - h                  # periodic box per band: the density never drifts
        rr = np.linalg.norm(rel, axis=1)
        sm = lambda x: (lambda y: y * y * (3 - 2 * y))(np.clip(x, 0.0, 1.0))
        self.wt = sm((rr - self.blo) / self.blw) * (1 - sm((rr - self.bhi) / self.bhw))   # this band's shell only
        return self.cp + rel @ self.B, dt

    def _vel(self, fr, dt):
        fl = np.array(fr.get('near_flow', (0.0, 0.0, 0.0)), float)
        return self.cpl[:, None] * fl[None] + self.vd + self.wa * self.ww * np.cos(self.ww * dt + self.wp)

    def update(self, fr, t):
        if self.world:
            C, t = self._world_pos(fr)                    # t: world time (slows in R15's slow moment)
            grow = self.grow < fr.get('near_k', 1.0)     # a fixed subset grows with the density (no popping)
            s = self.s * ((self.wt > 0.01) & grow)
        else:
            ga = self.look.get('near_gust', 0.0)
            gust = ga * self.sv / 0.55 * (np.sin(0.55 * t + self.gp) - np.sin(self.gp))   # integrated 1 + ga*cos(0.55 t)
            sN = np.mod(self.s0 + self.sv * t + gust + 1.6, 3.2) - 1.6
            q = sN[:, None] * self.D + self.l[:, None] * self.N
            x = q[:, 0] * self.hw; y = q[:, 1] * self.hh
            fl = self.fa * np.sin(self.fw * t + self.fp)
            x = x + fl[:, 0]; y = y + fl[:, 1]; z = self.z + self.vz * np.sin(0.3 * t + self.fp[:, 2]) + fl[:, 2]
            C = self.cp + x[:, None] * self.r + y[:, None] * self.u + z[:, None] * self.f
            s = self.s
        th = self.om * t + self.ph
        A = self._rot(self.a0, self.ax, th); B = self._rot(self.b0, self.ax, th)
        w = (0.5 * 0.78 * s)[:, None]; h = (0.5 * s)[:, None]
        V = np.stack([C - w * A - h * B, C + w * A - h * B, C + w * A + h * B, C - w * A + h * B], 1)
        alpha = self.wt.copy() if self.world else np.ones(len(C))
        if self.world and self.look.get('near_shutter', 0.5) > 0:
            # shutter streak (no render-time motion blur for geometry rebuilt in Python): stretch each petal
            # along its own motion during the open shutter, and thin it so it carries the same light
            S = self._vel(fr, t) * (self.dtau.get(fr['k'], 1 / 24) * self.look.get('near_shutter', 0.5))
            for j in range(4):
                sg = np.sign(np.sum((V[:, j] - C) * S, 1))
                V[:, j] += 0.5 * sg[:, None] * S
            alpha = np.clip(s / (s + np.linalg.norm(S, axis=1) + 1e-9), 0.0, 1.0) ** self.look.get('near_thin', 0.6)
            alpha = np.clip(alpha, 0.3, 1.0) * self.wt
        n = len(C); me = self.ob.data
        me.clear_geometry()
        me.vertices.add(n * 4); me.vertices.foreach_set('co', V.ravel())
        me.loops.add(n * 4); me.loops.foreach_set('vertex_index', np.arange(n * 4, dtype=np.int32))
        me.polygons.add(n); me.polygons.foreach_set('loop_start', np.arange(0, n * 4, 4, dtype=np.int32))
        try:
            me.polygons.foreach_set('loop_total', np.full(n, 4, np.int32))
        except Exception:
            pass
        me.update(calc_edges=True)
        uvl = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
        uvl.data.foreach_set('uv', np.tile(np.array([0, 0, 1, 0, 1, 1, 0, 1], np.float32), n))
        at = me.attributes.get('pv_alpha') or me.attributes.new('pv_alpha', 'FLOAT', 'POINT')
        at.data.foreach_set('value', np.repeat(alpha, 4).astype(np.float32))
        me.update()
        self.light.location = fr['whale_light']['p']
        col = gold_mix(self.look, pal(self.look).get('near_light', pal(self.look)['light']), 'gold_light', fr)
        sl = fr.get('slow', 0.0)                       # R15's slow moment: the near petals hang and glint gold
        if sl > 0:
            gl = pal(self.look).get('gold_light', (1.0, 0.80, 0.62)); k = self.look.get('slow_gold', 0.6) * sl
            col = tuple(a * (1 - k) + b * k for a, b in zip(col, gl))
        self.light.data.energy = self.look['near_light'] * fr['whale_light']['I'] * (1 + self.look.get('slow_glint', 0.5) * sl)
        self.light.data.color = col


class FlowerField:
    """v16 (R13; R10-R12 later): the colony as real flowers. The FL-01 model (fl01_open.glb: stem, seed, five
    petals) instanced (Geometry Nodes) at every flower the cut sees (cache flowers.npz from the previs FLOWERS),
    in four variants: 0-3 petals gone. Per frame each flower shows round(0.8 x its released petals) gone, as the
    previs draw_flower does; the released petals themselves are the Petals layer (they sit on the flower until
    the lift-off wave, then rise). Lit by the moon and the whale like everything else, plus a faint floor
    (previs light 0.10 + ...)."""
    def __init__(self, look, cache):
        d = np.load(cache / 'flowers.npz')
        self.p = d['p'].astype(np.float64); self.det = d['det'].astype(np.float64)
        n = len(self.p)
        g = np.random.default_rng(1313)
        rot = g.uniform(0, 2 * np.pi, n).astype(np.float32)
        scl = (look.get('flower_scale', 0.1) * g.uniform(0.85, 1.15, n)).astype(np.float32)
        coll = self._variants(look)
        me = bpy.data.meshes.new('FlowerPoints'); me.from_pydata(self.p.tolist(), [], [])
        me.attributes.new('variant', 'INT', 'POINT')
        me.attributes.new('rot', 'FLOAT', 'POINT').data.foreach_set('value', rot)
        me.attributes.new('scl', 'FLOAT', 'POINT').data.foreach_set('value', scl)
        self.ob = bpy.data.objects.new('FlowerField', me); bpy.context.scene.collection.objects.link(self.ob)
        md = self.ob.modifiers.new('FlowerInst', 'NODES'); md.node_group = self._tree(coll)
        print(f'  flowers: {n} instanced')

    def _variants(self, look):
        bpy.ops.import_scene.gltf(filepath=str(ASSETS / 'fl01_open.glb'))
        obs = {o.name.split('.')[0]: o for o in bpy.context.selected_objects if o.type == 'MESH'}
        def arr(o):
            me = o.data; V = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', V); V = V.reshape(-1, 3)
            M = np.array(o.matrix_world); V = V @ M[:3, :3].T + M[:3, 3]
            return V, [tuple(p_.vertices) for p_ in me.polygons]
        Vs, Fs = arr(obs['FL01_Stem']); Vd, Fd = arr(obs['FL01_Seed']); Vp, Fp = arr(obs['FL01_Petals'])
        # the FL-01 head is much wider than the previs flower (petal 2 cm on a 7.5 cm stem): narrow it
        k3 = np.array([look.get('flower_sxy', 1.0), look.get('flower_sxy', 1.0), 1.0])
        Vs, Vd, Vp = Vs * k3, Vd * k3, Vp * k3
        # the five petals = the connected pieces of the petal mesh, ordered around the flower
        par = list(range(len(Vp)))
        def find(i):
            while par[i] != i:
                par[i] = par[par[i]]; i = par[i]
            return i
        for f in Fp:
            for v in f[1:]:
                a_, b_ = find(f[0]), find(v)
                if a_ != b_:
                    par[a_] = b_
        roots = sorted({find(i) for i in range(len(Vp))})
        isl = [[f for f in Fp if find(f[0]) == r] for r in roots]
        cen = [Vp[[v for f in fs for v in f]].mean(0) for fs in isl]
        isl = [fs for _, fs in sorted(zip([math.atan2(c[1], c[0]) for c in cen], isl), key=lambda t: t[0])]
        mats = [simple_mat('FlowerStem', _lin((40, 60, 52)), 0.8), simple_mat('FlowerSeed', _lin((214, 180, 104)), 0.6),
                simple_mat('FlowerPetal', _lin((236, 231, 214)), 0.55)]
        for m_, (col, k) in zip(mats, (((40, 60, 52), 0.02), ((214, 180, 104), 0.15), ((236, 231, 214), look.get('flower_emit', 0.12)))):
            b = m_.node_tree.nodes.get('Principled BSDF')
            b.inputs['Emission Color'].default_value = (*_lin(col), 1); b.inputs['Emission Strength'].default_value = k
        coll = bpy.data.collections.new('FlowerVariants')          # not linked to the scene: instanced only
        for r in range(4):
            keep = [f for fs in isl[r:] for f in fs]
            V = np.vstack([Vs, Vd, Vp]); o1 = len(Vs); o2 = o1 + len(Vd)
            F = Fs + [tuple(v + o1 for v in f) for f in Fd] + [tuple(v + o2 for v in f) for f in keep]
            mi = [0] * len(Fs) + [1] * len(Fd) + [2] * len(keep)
            me = bpy.data.meshes.new(f'FlowerV{r}')
            me.from_pydata([tuple(map(float, v)) for v in V], [], F); me.update()
            for m_ in mats:
                me.materials.append(m_)
            me.polygons.foreach_set('material_index', np.array(mi, np.int32))
            for p_ in me.polygons:
                p_.use_smooth = True
            coll.objects.link(bpy.data.objects.new(f'FlowerV{r}', me))
        for o in obs.values():
            bpy.data.objects.remove(o, do_unlink=True)
        return coll

    @staticmethod
    def _tree(coll):
        ng = bpy.data.node_groups.new('FlowerInst', 'GeometryNodeTree')
        ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
        ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        N = ng.nodes; L = ng.links
        gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
        iop = N.new('GeometryNodeInstanceOnPoints')
        ci = N.new('GeometryNodeCollectionInfo'); ci.inputs['Collection'].default_value = coll
        ci.inputs['Separate Children'].default_value = True; ci.inputs['Reset Children'].default_value = True
        def attr(name, typ):
            na = N.new('GeometryNodeInputNamedAttribute'); na.data_type = typ; na.inputs['Name'].default_value = name
            return na.outputs['Attribute']
        cx = N.new('ShaderNodeCombineXYZ'); L.new(attr('rot', 'FLOAT'), cx.inputs['Z'])
        try:
            er = N.new('FunctionNodeEulerToRotation'); L.new(cx.outputs[0], er.inputs[0]); rot_out = er.outputs[0]
        except Exception:
            rot_out = cx.outputs[0]
        L.new(gi.outputs[0], iop.inputs['Points']); L.new(ci.outputs[0], iop.inputs['Instance'])
        iop.inputs['Pick Instance'].default_value = True
        L.new(attr('variant', 'INT'), iop.inputs['Instance Index'])
        L.new(rot_out, iop.inputs['Rotation']); L.new(attr('scl', 'FLOAT'), iop.inputs['Scale'])
        L.new(iop.outputs[0], go.inputs[0])
        return ng

    def update(self, fr):
        gone = np.round((self.det <= fr['tau']).sum(1) * 0.8).astype(np.int32).clip(0, 3)
        self.ob.data.attributes['variant'].data.foreach_set('value', gone)
        self.ob.data.update()


class Party:
    """v16 (R17b; also R06): the four adventurers, built in Blender (never drawn by an AI), seen from behind
    as dark silhouettes. Their looks are undecided, so - as in the previs draw_party - they are anonymous
    cloaked figures of different builds (cut.json party: dx, dy from the PCs' spot, height, shoulder width),
    nothing that fixes a race, class or weapon. Cloak = a lathe of ellipses on the previs outline; the head
    tips back to look up; a cool rim where the light of the opening grazes the shoulders and head."""
    PROF = ((0.00, 0.30), (0.30, 0.37), (0.55, 0.44), (0.72, 0.48), (0.80, 0.50), (0.84, 0.40), (0.86, 0.12))

    def __init__(self, look, meta):
        self.look = look
        cam0 = meta['frames'][0]['cam']; f0 = np.array(cam0['f']); r0 = np.array(cam0['r'])
        fh = f0 * np.array([1, 1, 0.0]); fh /= np.linalg.norm(fh)          # they face away from the camera
        rh = np.cross(fh, (0.0, 0.0, 1.0)); rh /= np.linalg.norm(rh)
        if rh @ r0 < 0:
            rh = -rh
        pc = np.array(meta['pc']); mat = self._material()
        self.obs = []
        lean = look.get('party_lean', 0.07)
        for k, (dx, dy, h, sw) in enumerate(meta['party']):
            base = np.array([pc[0] + dx, pc[1] + dy, 0.0]); base[2] = float(w.ground_z(base[0], base[1]))
            n = 20; ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
            V = []
            for zf, wf in self.PROF:
                a_ = wf * sw; b_ = 0.62 * a_
                for t in ang:
                    V.append(base + rh * (a_ * np.cos(t)) + fh * (b_ * np.sin(t)) + np.array([0, 0, zf * h]))
            F = [(j * n + i, j * n + (i + 1) % n, (j + 1) * n + (i + 1) % n, (j + 1) * n + i)
                 for j in range(len(self.PROF) - 1) for i in range(n)]
            top = len(V); V.append(base + np.array([0, 0, 0.86 * h])); F += [((len(self.PROF) - 1) * n + i, (len(self.PROF) - 1) * n + (i + 1) % n, top) for i in range(n)]
            # head: an ellipsoid (r 0.105 h, a little taller), tipped back toward the camera to look up
            hc = base + np.array([0, 0, 0.935 * h]) - fh * lean; hr = 0.105 * h
            nu_, nv_ = 16, 10; h0 = len(V)
            for j in range(nv_ + 1):
                ph = math.pi * j / nv_
                for i in range(nu_):
                    t = 2 * math.pi * i / nu_
                    V.append(hc + rh * (hr * math.sin(ph) * math.cos(t)) + fh * (hr * math.sin(ph) * math.sin(t)) + np.array([0, 0, 1.12 * hr * math.cos(ph)]))
            F += [(h0 + j * nu_ + i, h0 + j * nu_ + (i + 1) % nu_, h0 + (j + 1) * nu_ + (i + 1) % nu_, h0 + (j + 1) * nu_ + i)
                  for j in range(nv_) for i in range(nu_)]
            ob = mesh_obj(f'Party{k}', V, F, mat)
            for p_ in ob.data.polygons:
                p_.use_smooth = True
            self.obs.append(ob)
        print(f'  party: {len(self.obs)} figures')

    def _material(self):
        m = bpy.data.materials.new('PartyCloak'); try_set(m, use_nodes=True)
        nt = m.node_tree; N = nt.nodes; L = nt.links; b = N.get('Principled BSDF')
        b.inputs['Base Color'].default_value = (*_lin((7, 9, 13)), 1); b.inputs['Roughness'].default_value = 0.9
        lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
        geo = N.new('ShaderNodeNewGeometry'); sz = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sz.inputs[0])
        upk = N.new('ShaderNodeMapRange'); upk.inputs['From Min'].default_value = 0.25; upk.inputs['From Max'].default_value = 1.0
        L.new(sz.outputs['Z'], upk.inputs['Value'])
        rim = N.new('ShaderNodeMath'); rim.operation = 'MULTIPLY'; L.new(lw.outputs['Fresnel'], rim.inputs[0]); L.new(upk.outputs['Result'], rim.inputs[1])
        k = N.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; k.inputs[1].default_value = self.look.get('party_rim', 0.6)
        L.new(rim.outputs[0], k.inputs[0])
        b.inputs['Emission Color'].default_value = (*_lin((62, 76, 96)), 1)
        L.new(k.outputs[0], b.inputs['Emission Strength'])
        return m


class WhaleLight:
    def __init__(self, look):
        self.look = look
        ld = bpy.data.lights.new('WhaleLight', 'POINT'); ld.color = pal(look)['light']
        try_set(ld, shadow_soft_size=6.0, use_shadow=False, volume_factor=look['whale_light_vol'])   # it sits inside the body
        self.ob = bpy.data.objects.new('WhaleLight', ld); bpy.context.scene.collection.objects.link(self.ob)
        self.k = look['whale_light_w']

    def exclude_more(self, names):
        """v16 (R13): the whale's light reaches the flowers, the petals and the air, not the ground or the lake
        (previs: only the flowers take the whale's light, the ground stays dark)"""
        coll = bpy.data.collections.get('WhaleLightReceivers')
        if coll is None:
            return
        for nm in names:
            ob = bpy.data.objects.get(nm)
            if ob is not None and ob.name not in coll.objects:
                coll.objects.link(ob)
        for i in range(len(coll.objects)):                  # every member is excluded (same order as .objects)
            coll.collection_objects[i].light_linking.link_state = 'EXCLUDE'

    def exclude(self, ob):
        """The whale's own light lights the air, the petals and the rocks, not the whale's skin (previs:
        the body shows only its emission x form). Without this the point light inside the body burns the
        thin flukes and fins to flat white."""
        try:
            coll = bpy.data.collections.new('WhaleLightReceivers')
            coll.objects.link(ob)
            self.ob.light_linking.receiver_collection = coll
            coll.collection_objects[0].light_linking.link_state = 'EXCLUDE'    # the whale is its only member
            print('  whale light: excludes', ob.name)
        except Exception as e:
            print('  [skip] light linking:', e)

    def update(self, fr):
        self.ob.location = fr['whale_light']['p']
        self.ob.data.energy = self.k * fr['whale_light']['I'] * (1 - fr['whale'].get('melt', 0.0))
        # v16: at R15's closest pass the lit air swells around the whale (previs: glow 0.12 + 0.30 x climax)
        try_set(self.ob.data, volume_factor=self.look['whale_light_vol'] * (1 + self.look.get('climax_air', 0.0) * fr.get('climax', 0.0)))
        # the air keeps most of its sakura-violet (gold light in the blue air turns a muddy green-grey)
        self.ob.data.color = gold_mix(self.look, pal(self.look)['light'], 'gold_light', fr, 'gold_air_amt', 0.3)


def _swap_variant_mats(mat):
    """the instanced flower variants live outside the scene: give them the same layer material (3 slots)"""
    c = bpy.data.collections.get('FlowerVariants')
    for ob in (list(c.objects) if c else []):
        ob.data.materials.clear()
        for _ in range(3):
            ob.data.materials.append(mat)


def to_petal_layer():
    """Petals exactly as in the beauty; every other surface is matte black (it still hides the petals
    behind it); no air, no lights. Add it over a painted pass to keep the previs petal flow."""
    sc = bpy.context.scene
    m = bpy.data.materials.new('BlackMatte'); try_set(m, use_nodes=True)
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 0.0
    nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL').inputs['Surface'])
    for ob in list(sc.objects):
        if ob.type == 'LIGHT' or ob.name == 'CaveAir':
            ob.hide_render = True
        elif ob.type == 'MESH' and ob.name != 'Petals':
            ob.data.materials.clear(); ob.data.materials.append(m)
    _swap_variant_mats(m)
    sc.world.node_tree.nodes.get('Background').inputs['Color'].default_value = (0, 0, 0, 1)


def hide_near():
    for nm in ('NearSnow', 'PetalsNear'):
        ob = bpy.context.scene.objects.get(nm)
        if ob is not None:
            ob.hide_render = True


def to_base():
    """The beauty without the petals (post/finish.py paints the petals from the petal layer)."""
    bpy.context.scene.objects['Petals'].hide_render = True
    hide_near()


def to_near_layer():
    """The near blizzard alone on a transparent film (RGBA; laid over the finished frame).
    v16: the other surfaces are holdouts, not hidden, so a petal behind the whale, the four or the ground
    does not show through them (R17b: the four stand inside the snow)."""
    sc = bpy.context.scene
    hold = bpy.data.materials.new('NearHoldout'); try_set(hold, use_nodes=True); nt = hold.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    ho = nt.nodes.new('ShaderNodeHoldout')
    nt.links.new(ho.outputs[0], next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL').inputs['Surface'])
    for ob in list(sc.objects):
        if ob.type != 'MESH' or ob.name in ('NearSnow', 'PetalsNear'):
            continue
        if ob.name in ('CaveAir', 'Petals', 'NightSky', 'Stars', 'MoonDisc', 'MoonHalo'):
            ob.hide_render = True
        else:
            ob.data.materials.clear(); ob.data.materials.append(hold)
    _swap_variant_mats(hold)
    try_set(sc.render, film_transparent=True)
    sc.render.image_settings.color_mode = 'RGBA'


def to_whale_matte():
    sc = bpy.context.scene
    def flat(name, v):
        m = bpy.data.materials.new(name); try_set(m, use_nodes=True); nt = m.node_tree
        for n in list(nt.nodes):
            if n.type != 'OUTPUT_MATERIAL':
                nt.nodes.remove(n)
        em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = v
        em.inputs['Color'].default_value = (1, 1, 1, 1)
        nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL').inputs['Surface'])
        return m
    white, black = flat('MatteWhite', 1.0), flat('MatteBlack', 0.0)
    for ob in list(sc.objects):
        if ob.type == 'LIGHT' or ob.name in ('CaveAir', 'Petals'):
            ob.hide_render = True
        elif ob.type == 'MESH':
            mat = white if ob.name.startswith('WH01') else black
            if mat is white and ob.data.attributes.get('pv_malpha') is not None:
                # v16 (R18): the matte melts with the whale (its strength follows pv_malpha)
                mat = flat('MatteWhiteMelt', 1.0); nt = mat.node_tree
                at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'pv_malpha'
                em = next(n for n in nt.nodes if n.type == 'EMISSION'); nt.links.new(at.outputs['Fac'], em.inputs['Strength'])
            ob.data.materials.clear(); ob.data.materials.append(mat)
    _swap_variant_mats(black)
    sc.world.node_tree.nodes.get('Background').inputs['Color'].default_value = (0, 0, 0, 1)
    try_set(sc.view_settings, view_transform='Standard', look='None', exposure=0.0)
    try_set(sc.eevee, taa_render_samples=8)


def to_depth_control(a, keep_petals=False):
    """Swap every surface for a camera-distance ramp (near white -> far black, log scale), drop the air
    volume, the petals and the lights. The geometry, camera and whale deformation are untouched, so the
    control video carries exactly the previs composition and whale motion."""
    sc = bpy.context.scene
    m = bpy.data.materials.new('DepthControl'); try_set(m, use_nodes=True)
    nt = m.node_tree; N = nt.nodes
    for n in list(N):
        if n.type != 'OUTPUT_MATERIAL':
            N.remove(n)
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
    cam = N.new('ShaderNodeCameraData')
    q = N.new('ShaderNodeMath'); q.operation = 'DIVIDE'; q.inputs[1].default_value = a.depth_near
    nt.links.new(cam.outputs['View Z Depth'], q.inputs[0])
    lg = N.new('ShaderNodeMath'); lg.operation = 'LOGARITHM'; lg.inputs[1].default_value = a.depth_far / a.depth_near
    nt.links.new(q.outputs[0], lg.inputs[0])
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.use_clamp = True; inv.inputs[0].default_value = 1.0
    nt.links.new(lg.outputs[0], inv.inputs[1])
    em = N.new('ShaderNodeEmission'); nt.links.new(inv.outputs[0], em.inputs['Strength'])
    em.inputs['Color'].default_value = (1, 1, 1, 1)
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    for ob in list(sc.objects):
        if ob.type == 'LIGHT' or ob.name == 'CaveAir' or (ob.name == 'Petals' and not keep_petals):
            ob.hide_render = True
        elif ob.name == 'Petals':
            continue                     # keeps its additive light-dot material on top of the depth
        elif ob.type == 'MESH':
            ob.data.materials.clear(); ob.data.materials.append(m)
            for poly_mat in ob.material_slots:
                poly_mat.link = 'DATA'
    bgn = sc.world.node_tree.nodes.get('Background')
    bgn.inputs['Color'].default_value = (0, 0, 0, 1)
    try_set(sc.view_settings, view_transform='Standard', look='None', exposure=0.0)
    try_set(sc.eevee, taa_render_samples=8)


def setup_render(a, meta, look):
    sc = bpy.context.scene
    if a.engine == 'CYCLES':
        sc.render.engine = 'CYCLES'
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
            for d in prefs.devices:
                d.use = True
            sc.cycles.device = 'GPU' if any(d.type != 'CPU' for d in prefs.devices) else 'CPU'
        except Exception as e:
            print('  [cycles] CPU only:', e); sc.cycles.device = 'CPU'
        try_set(sc.cycles, samples=a.samples, use_denoising=True, volume_step_rate=4.0, volume_max_steps=256,
                max_bounces=4, transparent_max_bounces=64)
    else:
        sc.render.engine = 'BLENDER_EEVEE'
    sc.render.fps = meta['fps']; sc.render.resolution_x = a.res; sc.render.resolution_y = a.res * 9 // 16
    sc.render.resolution_percentage = 100
    sc.frame_start = 0; sc.frame_end = meta['n_frames'] - 1
    ee = sc.eevee
    try_set(ee, taa_render_samples=a.samples, volumetric_start=1.0, volumetric_end=700.0,
            volumetric_tile_size='4', volumetric_samples=96, volumetric_sample_distribution=0.35,
            volumetric_shadow_samples=32, use_volumetric_shadows=True)
    try_set(sc.view_settings, view_transform='AgX', look='None', exposure=look['exposure'])
    sc.render.image_settings.file_format = 'PNG'
    try_set(sc.render, filter_size=look['filter_px'])      # smaller = crisper sub-pixel petals (previs draws them as hard dots)


def main(argv):
    a = args_from_argv(argv)
    look = dict(LOOK[a.look])
    for kv in a.set:
        k, v = kv.split('=')
        try:
            look[k] = tuple(float(x) for x in v.split(',')) if ',' in v else float(v)
        except ValueError:
            look[k] = v                                     # e.g. palette=sakura
    if a.exposure is not None:
        look['exposure'] = a.exposure
    meta = json.loads((a.cache / 'cut.json').read_text(encoding='utf-8'))
    if look.get('lens_mul', 1.0) != 1.0:      # test only: a longer lens from the same previs position/aim
        for f in meta['frames']:
            f['cam']['lens_mm'] *= look['lens_mul']
        print('  [test] lens x', look['lens_mul'], '->', meta['frames'][0]['cam']['lens_mm'], 'mm (NOT the previs)')
    frames = {f['k']: f for f in meta['frames']}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    t0 = time.time()
    build_world(look)
    if look.get('sky', 0.0) > 0.5:
        build_sky(look, meta)
    cam = build_camera(meta)
    setup_render(a, meta, look)
    whale = Whale(look, meta); wl = WhaleLight(look); pet = Petals(look, a.res)
    near = NearSnow(look, meta) if look['near_n'] > 0 else None
    if look.get('party', 0.0) > 0.5 and meta.get('party'):
        Party(look, meta)
    flowers = FlowerField(look, a.cache) if look.get('flowers', 0.0) > 0.5 and (a.cache / 'flowers.npz').exists() else None
    if look.get('petal_near_r', 0.0) > 0:
        pet.add_near(look)
    if look['fstop'] > 0:                          # focus on the whale: the near petals go soft
        try_set(cam.data.dof, use_dof=True, aperture_fstop=look['fstop'])
    if look.get('whale_self_light', 0.0) < 0.5:
        wl.exclude(whale.ob)
        if look.get('whale_light_ground', 1.0) < 0.5:
            wl.exclude_more(('Ground', 'Water'))
    if a.control in ('depth', 'depth_petals', 'petals', 'whale_matte'):
        hide_near()
    if a.control in ('depth', 'depth_petals'):
        to_depth_control(a, keep_petals=a.control == 'depth_petals')
    elif a.control == 'petals':
        to_petal_layer()
    elif a.control == 'near':
        to_near_layer()
    elif a.control == 'base':
        to_base()
    elif a.control == 'whale_matte':
        to_whale_matte()
    out = a.out / (f'control_{a.control}' if a.control else 'beauty'); out.mkdir(parents=True, exist_ok=True)
    ks = sorted(frames)
    if a.frames:
        f0, f1 = (int(x) for x in a.frames.split(':'))
        ks = [k for k in ks if f0 <= k < f1]
    ks = ks[::a.step]
    print(f'built in {time.time() - t0:.1f}s, rendering {len(ks)} frames')
    sc = bpy.context.scene
    gold_log = {}
    for i, k in enumerate(ks):
        fr = frames[k]
        sc.frame_set(k)
        whale.update(fr); wl.update(fr)
        if flowers is not None:
            flowers.update(fr)
        # finish.py tints the near petals by this; R15's slow moment adds its gold glint (previs local_snow fk)
        gold_log[k] = max(fr.get('_gold', 0.0), fr.get('slow', 0.0) * look.get('slow_gold', 0.6))
        if near is not None:
            near.update(fr, k / meta['fps'])
        if look['fstop'] > 0:
            cam.data.dof.focus_distance = float(np.linalg.norm(np.array(fr['whale']['p']) - np.array(fr['cam']['pos'])))
        npz = a.cache / 'petals' / f'f_{k:04d}.npz'
        if npz.exists():
            pet.update(fr, npz)
        if a.save_blend and i == 0:
            bpy.ops.wm.save_as_mainfile(filepath=str(a.out / 'scene.blend'))
        if a.no_render:
            continue
        sc.render.filepath = str(out / f'{k:04d}.png')
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f'frame {k} ({i + 1}/{len(ks)}) {time.time() - t1:.1f}s', flush=True)
    if gold_log:                                   # per-frame gold of the whale's light, for post/finish.py
        gp = a.out / 'whale_gold.json'
        old = json.loads(gp.read_text(encoding='utf-8')) if gp.exists() else {}
        old.update({f'{k:04d}': round(v, 4) for k, v in gold_log.items()})
        gp.write_text(json.dumps(old, indent=0), encoding='utf-8')
    print(f'done {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
