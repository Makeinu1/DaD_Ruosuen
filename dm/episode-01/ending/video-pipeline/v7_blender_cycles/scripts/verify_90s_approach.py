#!/usr/bin/env python3
"""
V7 Step 3 (90s Master Pacing Update): Adds the dramatic Foreground Approach (28.0s Close Heigei)
and Graceful Turn-Back toward the Moonbeam (33.5s) to the 90-second Master Timeline!
Renders a crisp 2-panel verification still (28.0s Close Approach | 33.5s Turn-Back) in ~40s
and updates `v7_layout_master.json` + `v7_greybox_master.blend`.
"""

import json
import math
import time
from pathlib import Path

import bpy
from mathutils import Euler, Vector

REPO = Path("/home/antigravity/Makeinu1/DaD_Ruosuen")
V7_DIR = REPO / "dm/episode-01/ending/video-pipeline/v7_blender_cycles"
BLEND_PATH = V7_DIR / "v7_greybox_master.blend"
OUT_DIR = V7_DIR / "out/step3_greybox"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ART_DIR = Path("/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/4733e009-f44e-4728-af83-1f85c37a4d1d")


def update_master_json():
    fp = V7_DIR / "v7_layout_master.json"
    d = json.loads(fp.read_text())
    d["version"] = "V7.6_90s_Master_Approach_Turnback"
    d["production_windows"]["full_master_s"] = [0.0, 90.0]
    d["production_windows"]["full_frames_24fps"] = 2160
    d["master_90s_beats"] = [
        {"t_s": [0.0, 12.0],  "name": "01 Quiet Subterranean Silence (P0 moonlight + grey-brown buds)", "phase": "Phase 0"},
        {"t_s": [12.0, 20.0], "name": "02 Anomaly & Submerged Shadow Ripples",                           "phase": "Phase 0"},
        {"t_s": [20.0, 30.0], "name": "03 Quiet Breach -> Close Foreground Approach & Heigei Gaze",      "phase": "Phase 0 (Unlit)"},
        {"t_s": [30.0, 37.0], "name": "04 Graceful Turn-Back Away from Shore -> Ascending to Moonbeam",  "phase": "Phase 0 -> 1"},
        {"t_s": [37.0, 46.0], "name": "05 Moonlight Contact & Chromatic Awakening Wave + Bloom Begins",  "phase": "Phase 1 (Ice-Cyan x Violet)"},
        {"t_s": [46.0, 66.0], "name": "06 Free BELLE Opal Flight x Full Shore Bloom x Golden Snow",      "phase": "Phase 2 (Opal/Aqua) -> Phase 3 (Warm Gold)"},
        {"t_s": [66.0, 80.0], "name": "07 Exit C Departure Behind R1 Headland (Light Occluded)",         "phase": "Phase 3 (Occluded)"},
        {"t_s": [80.0, 90.0], "name": "08 Dreamlike Aftermath (Cam A Locked, Identical to 0s)",          "phase": "Quiet"},
    ]
    fp.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    print("[90s MASTER] Updated v7_layout_master.json to 90s (2,160f @ 24fps)")


def render_approach_and_turnback():
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    sc = bpy.context.scene
    sc.cycles.samples = 8
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.render.use_persistent_data = False

    cam_o = sc.camera
    whale = next(o for o in bpy.data.objects if o.type == "MESH" and "WH01" in o.name)
    whale.rotation_mode = "XYZ"

    # Two new dramatic beats added to the 90s Master Timeline:
    # 1. 28.0s CLOSE APPROACH & HEIGEI: Whale glides boldly forward to Y=-22m, Z=12.5m (just 38m from Cam A!),
    #    curving its massive smooth head & calm dark eye down toward the adventurers on the S1 shore!
    # 2. 33.5s GRACEFUL TURN-BACK: Whale banks smoothly away from the shore (Y=-6m, Z=21m), curving gracefully
    #    back into the wide cavern and upward toward the overhead vertical canyon moonbeam!
    shots = [
        ("03b_approach_28s", "28.0s CLOSE FOREGROUND APPROACH & HEIGEI (Whale Glides Close to Adventurers, Y=-22m)",
         Vector((-10.0, -62.0, 5.2)), Vector((2.0, 35.0, 26.0)), 21.0,
         Vector((-1.5, -22.0, 12.2)), Euler((math.radians(8.0), math.radians(10.0), math.radians(-122.0)), "XYZ")),
        ("03c_turnback_33s", "33.5s GRACEFUL TURN-BACK (Banking Away from Shore Toward Canyon Moonbeam, Y=-4m)",
         Vector((-9.0, -59.0, 5.6)), Vector((4.0, 48.0, 31.0)), 20.5,
         Vector((3.5, -4.0, 21.5)), Euler((math.radians(-14.0), math.radians(-22.0), math.radians(38.0)), "XYZ")),
    ]

    imgs = []
    for slug, label, c_pos, c_tgt, focal, w_pos, w_rot in shots:
        cam_o.location = c_pos
        cam_o.data.lens = focal
        cam_o.rotation_euler = (c_tgt - c_pos).to_track_quat("-Z", "Y").to_euler()
        whale.location = w_pos
        whale.rotation_euler = w_rot
        out_png = OUT_DIR / f"greybox_{slug}.png"
        sc.render.filepath = str(out_png)
        bpy.ops.render.render(write_still=True)
        imgs.append((out_png, label))
        print(f"[GREYBOX 90s] Rendered {out_png.name}")

    from PIL import Image, ImageDraw
    tw, th = 960, 540
    sheet = Image.new("RGB", (tw * 2, th), (8, 12, 20))
    dr = ImageDraw.Draw(sheet)
    for i, (fp, lbl) in enumerate(imgs):
        im = Image.open(fp).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        sheet.paste(im, (i * tw, 0))
        dr.rectangle([i * tw, 0, i * tw + tw, 28], fill=(0, 0, 0))
        dr.text((i * tw + 10, 7), lbl, fill=(210, 240, 255))
    out_sheet = OUT_DIR / "v7_step3_approach_turnback.png"
    sheet.save(out_sheet, "PNG", compress_level=4)
    (ART_DIR / out_sheet.name).write_bytes(out_sheet.read_bytes())
    print(f"[DONE] Saved {out_sheet.name} in {time.time() - t0:.1f}s!")


if __name__ == "__main__":
    update_master_json()
    render_approach_and_turnback()
