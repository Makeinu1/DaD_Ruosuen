"""Test shots for before/after lookdev probes (low-res, CPU)."""
import math
import bpy
from mathutils import Vector, Euler

EYE_LOCAL = Vector((6.95, 2.58, 0.44))  # built-in WH01_Calm_Eye (+Y side) in the GLB


def build(L):
    CONFIG, shore_z = L["CONFIG"], L["shore_z"]
    cam07 = Vector((-9.5, -34.5, max(4.5, shore_z(-9.5, -34.5) + 2.2)))

    def eye_fix(F):
        """Re-block Cut 07: whale lowers its head toward the shore and turns its
        near eye to the adventurer; camera focuses on the model's own eye."""
        whale, cam_o, eye_l = F["whale"], F["cam_o"], F["eye_l"]
        eye_o, eye_d, sc = F["eye_o"], F["eye_d"], F["sc"]
        eye_l.hide_render = True  # buried helper sphere: remove
        n_local = Vector((0.09, 0.94, 0.34)).normalized()
        best = None
        for yaw in range(-180, -40, 4):
            for roll in (0, -10, -20, -30):
                rot = Euler((math.radians(roll), math.radians(6.0), math.radians(yaw)), "XYZ")
                e = Vector((1.5, -18.0, 6.2)) + rot.to_matrix() @ EYE_LOCAL
                score = (rot.to_matrix() @ n_local).dot((cam07 - e).normalized()) - abs(yaw + 142) * 0.002
                if best is None or score > best[0]:
                    best = (score, yaw, roll)
        _, yaw, roll = best
        whale.location = Vector((1.5, -18.0, 6.2))
        whale.rotation_euler = Euler((math.radians(roll), math.radians(6.0), math.radians(yaw)), "XYZ")
        if not whale.get("eye_pushed"):
            ids = {vi for p in whale.data.polygons if p.material_index == 1 for vi in p.vertices}
            for vi in ids:
                whale.data.vertices[vi].co += n_local * 0.20
            whale.data.update(); whale["eye_pushed"] = True
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        eye_vs = [v.co for v in whale.data.vertices if False]
        e = whale.matrix_world @ EYE_LOCAL
        vis = 0; tot = 0
        polys = [p for p in whale.data.polygons if p.material_index == 1]
        for p in polys[::12]:
            pw = whale.matrix_world @ p.center
            d = pw - cam07
            ok, loc, nrm, idx, ob, _m = sc.ray_cast(dg, cam07, d.normalized(), distance=d.length + 0.5)
            tot += 1
            if ok and ob.name == whale.name and whale.data.polygons[idx].material_index == 1:
                vis += 1
        print(f"[EYE FIX] best alignment={best[0]:.2f} visible eye samples {vis}/{tot}")
        chosen = (yaw, roll, e)
        yaw, roll, e = chosen
        print(f"[EYE FIX] yaw={yaw} roll={roll} eye_world={tuple(round(x, 2) for x in e)} dist={(e - cam07).length:.2f}")
        # eye on the right third: aim slightly left of the eye
        right = (e - cam07).normalized().cross(Vector((0, 0, 1))).normalized()
        tgt = e - right * ((e - cam07).length * 0.11)
        cam_o.location = cam07
        cam_o.rotation_euler = (tgt - cam07).to_track_quat("-Z", "Y").to_euler()
        cam_o.data.dof.use_dof = True
        cam_o.data.dof.focus_distance = (e - cam07).length
        cam_o.data.dof.aperture_fstop = 2.8
        # catchlight: small source just above/beside the lens so the glint faces camera
        eye_o.location = cam07 + Vector((0.0, 0.0, 1.4)) - right * 0.8
        eye_d.energy = 2600.0
        eye_d.shadow_soft_size = 0.35

    def emit_only(F):
        pass

    def thin_film(F):
        nt = F["mat_whale"].node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        if "Thin Film Thickness" in bsdf.inputs:
            bsdf.inputs["Thin Film Thickness"].default_value = 460.0
            bsdf.inputs["Thin Film IOR"].default_value = 1.45
            print("[THIN FILM] enabled 460nm")
        else:
            print("[THIN FILM] input not available in this Blender")

    base07 = {
        "cam_pos": cam07, "cam_tgt": Vector((-1.8, -19.5, 8.6)), "focal": 68.0,
        "dof": True, "fstop": 2.8, "whale_vis": True,
        "w_pos": Vector((1.5, -16.0, 9.2)),
        "w_rot": Euler((math.radians(5.0), math.radians(10.0), math.radians(-142.0)), "XYZ"),
        "wake": 0.4, "eye_catch": (Vector((-9.5, -26.0, 11.2)), 9500.0),
        "w_emit": 0.0, "w_phase": 0.0, "w_wave": (15, 20),
        "w_light": 0.0, "w_lcol": (0.7, 0.85, 1.0), "fl_mode": "p0_only", "petal_mode": None,
    }
    base13 = {
        "cam_pos": Vector((-17.5, -1.5, 27.0)), "cam_tgt": Vector((5.5, 28.0, 34.5)), "focal": 28.0,
        "dof": True, "fstop": 4.0, "whale_vis": True,
        "w_pos": Vector((4.0, 24.0, 32.0)),
        "w_rot": Euler((math.radians(-18.0), math.radians(-10.0), math.radians(32.0)), "XYZ"),
        "wake": 0.0, "eye_catch": None,
        "w_emit": CONFIG["whale_climax_emit"], "w_phase": 1.0, "w_wave": (-20.0, -14.0),
        "w_light": CONFIG["whale_light_power"], "w_lcol": (1.0, 0.88, 0.76),
        "fl_mode": "all_open", "petal_mode": None,
    }
    return [
        dict(base07, slug="A_cut07_before"),
        dict(base07, slug="B_cut07_after", hook=eye_fix),
        dict(base13, slug="C_phase3_before"),
        dict(base13, slug="F_emit0_light0", w_emit=0.0, w_light=0.0),
        dict(base13, slug="G_light0_only", w_light=0.0),
        dict(base13, slug="H_beam_off", hook=lambda F: setattr(F["beam_ob"], "hide_render", True)),
        dict(base13, slug="J_opal_fix", w_emit=0.9, hook=lambda F: opal_fix(F)),
        dict(base13, slug="K_opal_emit0", w_emit=0.0, hook=lambda F: opal_fix(F)),
        dict(base13, slug="L_opal_standard_view", w_emit=0.9, hook=lambda F: (opal_fix(F), setattr(F["sc"].view_settings, "view_transform", "Standard"))),
        dict(base13, slug="M_opal_lightlink", w_emit=0.9, hook=lambda F: light_link_fix(F)),
        dict(base13, slug="N_opal_lightlink_emit06", w_emit=0.6, hook=lambda F: light_link_fix(F)),
        dict(base13, slug="O_opal_balanced", w_emit=0.9, hook=lambda F: light_link_fix(F, 0.36)),
        dict(base13, slug="I_fills_off", hook=lambda F: [setattr(F[k], "energy", 0.0) for k in ("sky_d", "lk_d")]),
        dict(base13, slug="D_phase3_emit09", w_emit=0.9),
        dict(base13, slug="E_phase3_emit09_thinfilm", w_emit=0.9, hook=thin_film),
    ]


def opal_fix(F):
    """Phase 2-3: keep fog clean (whale light ignores volume) and spread the
    emission ramp across saturated opal hues instead of near-white."""
    F["wlight_o"].visible_volume_scatter = False
    nt = F["mat_whale"].node_tree
    ramps = [n for n in nt.nodes if n.type == "VALTORGB"]
    r3 = ramps[1].color_ramp
    while len(r3.elements) > 2:
        r3.elements.remove(r3.elements[1])
    r3.elements[0].position = 0.0; r3.elements[0].color = (0.10, 0.62, 1.00, 1.0)   # ice cyan
    r3.elements[1].position = 0.92; r3.elements[1].color = (1.00, 0.70, 0.28, 1.0)  # champagne gold
    e = r3.elements.new(0.34); e.color = (0.80, 0.74, 1.00, 1.0)                     # pearl lavender-white
    e = r3.elements.new(0.62); e.color = (1.00, 0.48, 0.70, 1.0)                     # pale sakura
    mix = next(n for n in nt.nodes if n.type == "MATH" and n.operation == "MULTIPLY_ADD" and round(n.inputs[1].default_value, 2) in (0.36, 0.85))
    mix.inputs[1].default_value = 0.85
    print("[OPAL FIX] applied")


def light_link_fix(F, mixw=0.85):
    """Whale radiance light lights the cavern/flowers but NOT the whale itself."""
    opal_fix(F)
    nt = F["mat_whale"].node_tree
    mix = next(n for n in nt.nodes if n.type == "MATH" and n.operation == "MULTIPLY_ADD" and round(n.inputs[1].default_value, 2) in (0.36, 0.85))
    mix.inputs[1].default_value = mixw
    wl, whale = F["wlight_o"], F["whale"]
    coll = bpy.data.collections.get("WhaleLight_Receivers") or bpy.data.collections.new("WhaleLight_Receivers")
    if whale.name not in coll.objects:
        coll.objects.link(whale)
    wl.light_linking.receiver_collection = coll
    for co in coll.collection_objects:
        co.light_linking.link_state = "EXCLUDE"
    print("[LIGHT LINK] whale excluded from its own radiance light")
