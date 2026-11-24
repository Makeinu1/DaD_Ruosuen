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
    'guide': dict(exposure=0.0, vol_density=0.0012, vol_aniso=0.55, moon_strength=4.0,
                  moon_color=(0.70, 0.80, 1.0), whale_light_w=4.0e6, whale_emit=2.2,
                  petal_emit=3.0, fruit_emit=2.4, petal_min_px=1.1, rock=0.018, bg=(0.004, 0.006, 0.010)),
}
PEARL = (0.86, 0.93, 1.0)
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
    # world: night + thin volume so that the moonlight through the fissure becomes a beam
    wo = bpy.data.worlds.new('CaveAir'); sc.world = wo
    try_set(wo, use_nodes=True)
    nt = wo.node_tree; nodes = nt.nodes
    bgn = nodes.get('Background'); bgn.inputs['Color'].default_value = (*look['bg'], 1); bgn.inputs['Strength'].default_value = 1.0
    vol = nodes.new('ShaderNodeVolumePrincipled')
    vol.inputs['Density'].default_value = look['vol_density']
    vol.inputs['Anisotropy'].default_value = look['vol_aniso']
    vol.inputs['Color'].default_value = (0.8, 0.86, 1.0, 1)
    out = nodes.get('World Output')
    nt.links.new(vol.outputs['Volume'], out.inputs['Volume'])
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
        # hero glb -> previs local frame: x forward (head +x), z up, y side (the body is mirror
        # symmetric, so the side sign does not change the shape; checked against BODY_V bounds)
        print('hero bounds', self.V0.min(0).round(2), self.V0.max(0).round(2), 'previs', w.BODY_V.min(0).round(2), w.BODY_V.max(0).round(2))
        self.path = w.WhalePath()
        self.contact = meta['ev_contact']
        self.glow = me.attributes.get('pv_glow') or me.attributes.new('pv_glow', 'FLOAT', 'POINT')
        self.look = look
        for m in me.materials:
            self._add_emission(m)

    def _add_emission(self, m):
        nt = m.node_tree
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            return
        at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'pv_glow'
        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = self.look['whale_emit'] * (0.25 if 'Eye' in m.name else 1.0)
        nt.links.new(at.outputs['Fac'], mul.inputs[0])
        b.inputs['Emission Color'].default_value = (*PEARL, 1)
        nt.links.new(mul.outputs[0], b.inputs['Emission Strength'])

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
        try_set(ld, shadow_soft_size=6.0)
        self.ob = bpy.data.objects.new('WhaleLight', ld); bpy.context.scene.collection.objects.link(self.ob)
        self.k = look['whale_light_w']

    def update(self, fr):
        self.ob.location = fr['whale_light']['p']
        self.ob.data.energy = self.k * fr['whale_light']['I'] * (1 - fr['whale'].get('melt', 0.0))


def setup_render(a, meta, look):
    sc = bpy.context.scene
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


def main(argv):
    a = args_from_argv(argv)
    look = LOOK[a.look]
    meta = json.loads((a.cache / 'cut.json').read_text(encoding='utf-8'))
    frames = {f['k']: f for f in meta['frames']}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    t0 = time.time()
    build_world(look)
    build_camera(meta)
    setup_render(a, meta, look)
    whale = Whale(look, meta); wl = WhaleLight(look); pet = Petals(look, a.res)
    out = a.out / 'beauty'; out.mkdir(parents=True, exist_ok=True)
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
