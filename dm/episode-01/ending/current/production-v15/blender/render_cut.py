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
    'guide': dict(exposure=0.0, vol_density=0.00035, vol_aniso=0.55, moon_strength=4.0,
                  moon_color=(0.70, 0.80, 1.0), whale_light_w=1.5e5, whale_light_vol=0.5, whale_emit=0.95,
                  petal_emit=2.2, fruit_emit=0.4, petal_min_px=0.8, rock=0.018, bg=(0.003, 0.005, 0.012),
                  whale_form=0.6, whale_opal=1.0, whale_self_light=0.0, eye_out=1.08,
                  air_color=(0.6, 0.74, 1.0), filter_px=0.8,
                  whale_tex=0.7, whale_belly=0.35, whale_top=(0.8, 1.1)),
}
PEARL = (0.86, 0.93, 1.0)
BELLY = (0.55, 0.68, 0.95)          # the shaded underside goes blue (originals CUT05 / CUT09)
# previs whale_layer (v14.9b): pearl-opal colours along the body, by hue = 0 at the tail .. 1 at the head
OPAL = ((0.08, (228, 226, 212)), (0.30, (214, 208, 238)), (0.55, (234, 238, 242)), (0.85, (184, 216, 240)))
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
    ap.add_argument('--control', default='', choices=['', 'depth', 'depth_petals', 'petals', 'base', 'whale_matte'],
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
        for i, (pos, rgb) in enumerate(OPAL):
            e = cr.elements[i] if i < len(cr.elements) else cr.elements.new(pos)
            e.position = pos; e.color = (*[(c / 255.0) ** 2.2 for c in rgb], 1)
        L.new(inv.outputs[0], ramp.inputs['Fac'])
        mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
        mix.inputs['Factor'].default_value = self.look['whale_opal']
        mix.inputs[6].default_value = (*PEARL, 1)
        L.new(ramp.outputs['Color'], mix.inputs[7])
        col = mix.outputs[2]
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
        L.new(neg.outputs[0], mb.inputs['Factor']); L.new(col, mb.inputs[6]); mb.inputs[7].default_value = (*BELLY, 1)
        L.new(mb.outputs[2], b.inputs['Emission Color'])
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

    def update(self, fr, npz):
        d = np.load(npz)
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
        colv = (np.array(PETAL)[None] * (self.look['petal_emit'] * bright * flick * vis)[:, None]
                + np.array(FRUIT)[None] * (self.look['fruit_emit'] * 0.45 * fruit * np.clip(bright, 0, 1) * vis)[:, None])
        me.update(calc_edges=True)
        uvl = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
        uvl.data.foreach_set('uv', np.tile(np.array([0, 0, 1, 0, 1, 1, 0, 1], np.float32), n))
        at = me.attributes.get('pv_col') or me.attributes.new('pv_col', 'FLOAT_COLOR', 'POINT')
        C = np.ones((n, 4, 4), np.float32); C[:, :, :3] = colv[:, None, :]
        at.data.foreach_set('color', C.ravel())
        me.update()


class WhaleLight:
    def __init__(self, look):
        ld = bpy.data.lights.new('WhaleLight', 'POINT'); ld.color = PEARL
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


def to_base():
    """The beauty without the petals (post/finish.py paints the petals from the petal layer)."""
    bpy.context.scene.objects['Petals'].hide_render = True


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
        look[k] = tuple(float(x) for x in v.split(',')) if ',' in v else float(v)
    if a.exposure is not None:
        look['exposure'] = a.exposure
    meta = json.loads((a.cache / 'cut.json').read_text(encoding='utf-8'))
    frames = {f['k']: f for f in meta['frames']}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    t0 = time.time()
    build_world(look)
    build_camera(meta)
    setup_render(a, meta, look)
    whale = Whale(look, meta); wl = WhaleLight(look); pet = Petals(look, a.res)
    if look.get('whale_self_light', 0.0) < 0.5:
        wl.exclude(whale.ob)
    if a.control in ('depth', 'depth_petals'):
        to_depth_control(a, keep_petals=a.control == 'depth_petals')
    elif a.control == 'petals':
        to_petal_layer()
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
    for i, k in enumerate(ks):
        fr = frames[k]
        sc.frame_set(k)
        whale.update(fr); wl.update(fr)
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
    print(f'done {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
