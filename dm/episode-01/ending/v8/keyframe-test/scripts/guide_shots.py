import math, random
import bpy, bmesh
from mathutils import Vector, Euler
import sys
from pathlib import Path
# probe helpers (eye_fix / opal_fix / light_link_fix) live in v8/diagnosis/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "diagnosis"))
import v7_probe_test_shots as T

def dim_fills(F, k):
    for key in ("sky_d", "lk_d"):
        F[key].energy *= k
    F["world"].node_tree.nodes["Background"].inputs["Strength"].default_value = 1.4 * k

def c08_hook(F):
    dim_fills(F, 0.35)
    T.build.__globals__  # noqa
    # reuse the eye fix from the probe (pushes eye 20 cm, turns head to camera, focuses eye)
    shots = T.build({**F, "CONFIG": G["CONFIG"], "shore_z": G["shore_z"]})
    eye = next(s for s in shots if s["slug"] == "B_cut07_after")
    eye["hook"](F)

def make_vortex(F, cx=3.0, cy=6.0, z0=4.0, zh=78.0, r0=8.0, rh=34.0):
    rng = random.Random(23)
    bm = bmesh.new()
    for i in range(5200):
        u = rng.random()
        z = z0 + zh * u
        r = r0 + rh * u ** 0.8 + rng.gauss(0, 2.2)
        ang = u * 7.5 * math.pi + rng.gauss(0, 0.18) + (math.pi if i % 2 else 0)   # two interleaved arms
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
        s = 0.16 + 0.12 * rng.random()
        rot = Euler((rng.random() * 6.28, rng.random() * 6.28, rng.random() * 6.28)).to_matrix()
        vs = [bm.verts.new(Vector((x, y, z)) + rot @ Vector(p) * s) for p in ((-1, -0.55, 0), (1, -0.55, 0), (1, 0.55, 0), (-1, 0.55, 0))]
        bm.faces.new(vs)
    me = bpy.data.meshes.new("Vortex"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("PetalVortex", me); bpy.context.collection.objects.link(ob)
    m = bpy.data.materials.new("VortexPetal"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (1.0, 0.95, 0.85, 1)
    b.inputs["Emission Color"].default_value = (1.0, 0.86, 0.55, 1)
    b.inputs["Emission Strength"].default_value = 2.2
    me.materials.append(m)
    return ob

def c16_hook(F):
    dim_fills(F, 0.12)
    T.light_link_fix(F, 0.36)
    wn = F["mat_water"].node_tree.nodes
    for nd in wn:
        if nd.type == "BUMP":
            nd.inputs["Strength"].default_value = 0.01
    make_vortex(F)

def c16b_hook(F):
    dim_fills(F, 0.12)
    T.light_link_fix(F, 0.36)
    for nd in F["mat_water"].node_tree.nodes:
        if nd.type == "BUMP":
            nd.inputs["Strength"].default_value = 0.0
    make_vortex(F, cx=3.0, cy=16.0, z0=2.0, zh=58.0, r0=6.0, rh=26.0)

G = {}

def build(L):
    CONFIG, shore_z = L["CONFIG"], L["shore_z"]
    G.update(CONFIG=CONFIG, shore_z=shore_z)
    base = dict(dof=False, fstop=8.0, whale_vis=True, wake=0.0, eye_catch=None, w_wave=(-20.0, -14.0),
                w_lcol=(1.0, 0.88, 0.76), petal_mode=None)
    c08 = dict(base, slug="G_C08_glance", cam_pos=Vector((-9.5, -34.5, max(4.5, shore_z(-9.5, -34.5) + 2.2))),
               cam_tgt=Vector((-1.8, -19.5, 8.6)), focal=68.0, w_pos=Vector((1.5, -16.0, 9.2)),
               w_rot=Euler((0, 0, 0)), w_emit=0.0, w_phase=0.0, w_wave=(15, 20), w_light=0.0, fl_mode="p0_only", hook=c08_hook)
    c16 = dict(base, slug="G_C16_vortex", cam_pos=Vector((-10.0, -62.0, max(5.2, shore_z(-10.0, -62.0) + 1.7))), cam_tgt=Vector((3.0, 6.0, 30.0)), focal=18.0,
               w_pos=Vector((10.0, 4.0, 34.0)), w_rot=Euler((math.radians(-6), math.radians(-18), math.radians(105))),
               w_emit=1.2, w_phase=1.0, w_light=CONFIG["whale_light_power"] * 0.6, fl_mode="all_open", hook=c16_hook)
    ce = Vector((3.0, -26.5, max(1.3, shore_z(3.0, -26.5) + 1.0)))
    c16b = dict(base, slug="G_C16b_mirror", cam_pos=ce, cam_tgt=Vector((3.0, 16.0, ce.z + 42.5 * math.tan(math.radians(11)))), focal=18.0,
                w_pos=Vector((8.0, 14.0, 15.0)), w_rot=Euler((math.radians(25), math.radians(-5), math.radians(168))),
                w_emit=1.2, w_phase=1.0, w_light=CONFIG["whale_light_power"] * 0.6, fl_mode="all_open", hook=c16b_hook)
    import os
    if os.environ.get("ONLY16B"):
        print("C16B cam", ce, "shore_z", shore_z(3.0, -26.5))
        return [c16b]
    return [c16] if os.environ.get("ONLY16") else [c08, c16]
