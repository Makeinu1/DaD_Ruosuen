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


def build_world(look):
    sc = bpy.context.scene
    rock = simple_mat('Rock', (look['rock'],) * 3, 0.95)
    rock_soft = simple_mat('RockFar', (look['rock'] * 0.8, look['rock'] * 0.85, look['rock'] * 0.9), 0.95)
    # canopy: bottom rim (190 m) and the narrower top rim (230 m) -> the moon beam is their intersection
    slab_with_hole('Canopy_Rim190', w.RIM_Z, 1.0, rock)
    slab_with_hole('Canopy_Top230', w.TOP_Z, w.TOP_NARROW, rock)
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
        for m in me.materials:
            self._drop_vertex_tint(m)
            self._add_emission(m)

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
        val = g * (0.75 + 0.25 * fr['whale_light']['I']) * (1 + 0.35 * pulse) * (1 - wh.get('melt', 0.0))
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
        return {k: np.concatenate(v) for k, v in out.items()}

    def update(self, fr, npz):
        d = self._densify(np.load(npz))
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
    Built in the camera frame of the cut's first frame (R14's camera is fixed; a moving camera needs a
    world-space volume instead)."""
    def __init__(self, look, meta):
        self.look = look
        c = meta['frames'][0]['cam']
        self.cp, self.r, self.u, self.f = (np.array(c[k], float) for k in ('pos', 'r', 'u', 'f'))
        self.lens = c['lens_mm']
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
        fin = N.new('ShaderNodeMixShader'); L.new(am.outputs[0], fin.inputs['Fac'])
        L.new(tr.outputs[0], fin.inputs[1]); L.new(add.outputs[0], fin.inputs[2])
        L.new(fin.outputs[0], out.inputs['Surface'])
        return m

    @staticmethod
    def _rot(v, k, th):
        c, s_ = np.cos(th)[:, None], np.sin(th)[:, None]
        return v * c + np.cross(k, v) * s_ + k * np.sum(k * v, 1, keepdims=True) * (1 - c)

    def update(self, fr, t):
        ga = self.look.get('near_gust', 0.0)
        gust = ga * self.sv / 0.55 * (np.sin(0.55 * t + self.gp) - np.sin(self.gp))   # integrated 1 + ga*cos(0.55 t)
        sN = np.mod(self.s0 + self.sv * t + gust + 1.6, 3.2) - 1.6
        q = sN[:, None] * self.D + self.l[:, None] * self.N
        x = q[:, 0] * self.hw; y = q[:, 1] * self.hh
        fl = self.fa * np.sin(self.fw * t + self.fp)
        x = x + fl[:, 0]; y = y + fl[:, 1]; z = self.z + self.vz * np.sin(0.3 * t + self.fp[:, 2]) + fl[:, 2]
        C = self.cp + x[:, None] * self.r + y[:, None] * self.u + z[:, None] * self.f
        th = self.om * t + self.ph
        A = self._rot(self.a0, self.ax, th); B = self._rot(self.b0, self.ax, th)
        w = (0.5 * 0.78 * self.s)[:, None]; h = (0.5 * self.s)[:, None]
        V = np.stack([C - w * A - h * B, C + w * A - h * B, C + w * A + h * B, C - w * A + h * B], 1)
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
        me.update()
        self.light.location = fr['whale_light']['p']
        self.light.data.energy = self.look['near_light'] * fr['whale_light']['I']
        self.light.data.color = gold_mix(self.look, pal(self.look).get('near_light', pal(self.look)['light']), 'gold_light', fr)


class WhaleLight:
    def __init__(self, look):
        self.look = look
        ld = bpy.data.lights.new('WhaleLight', 'POINT'); ld.color = pal(look)['light']
        try_set(ld, shadow_soft_size=6.0, use_shadow=False, volume_factor=look['whale_light_vol'])   # it sits inside the body
        self.ob = bpy.data.objects.new('WhaleLight', ld); bpy.context.scene.collection.objects.link(self.ob)
        self.k = look['whale_light_w']

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
        # the air keeps most of its sakura-violet (gold light in the blue air turns a muddy green-grey)
        self.ob.data.color = gold_mix(self.look, pal(self.look)['light'], 'gold_light', fr, 'gold_air_amt', 0.3)


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
    sc.world.node_tree.nodes.get('Background').inputs['Color'].default_value = (0, 0, 0, 1)


def hide_near():
    ob = bpy.context.scene.objects.get('NearSnow')
    if ob is not None:
        ob.hide_render = True


def to_base():
    """The beauty without the petals (post/finish.py paints the petals from the petal layer)."""
    bpy.context.scene.objects['Petals'].hide_render = True
    hide_near()


def to_near_layer():
    """The near blizzard alone on a transparent film (RGBA; laid over the finished frame)."""
    sc = bpy.context.scene
    for ob in list(sc.objects):
        if ob.type == 'MESH' and ob.name != 'NearSnow':
            ob.hide_render = True
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
            ob.data.materials.clear(); ob.data.materials.append(white if ob.name.startswith('WH01') else black)
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
    cam = build_camera(meta)
    setup_render(a, meta, look)
    whale = Whale(look, meta); wl = WhaleLight(look); pet = Petals(look, a.res)
    near = NearSnow(look, meta) if look['near_n'] > 0 else None
    if look['fstop'] > 0:                          # focus on the whale: the near petals go soft
        try_set(cam.data.dof, use_dof=True, aperture_fstop=look['fstop'])
    if look.get('whale_self_light', 0.0) < 0.5:
        wl.exclude(whale.ob)
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
        gold_log[k] = fr.get('_gold', 0.0)
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
