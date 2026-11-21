#!/usr/bin/env python3
"""
V7 Step 4: Automated Numeric Target Table Measurement from Approved Master Concept Art (Infographic §05).
Measures exact Mean RGB, Relative Luminance L (0..100), Hue Angle (deg), Saturation (%),
and Relative Brightness Ratios (vs Cavern Cliff Wall) for every key region across:
  - Beat 1 (Unlit Heigei):   v74_master_01_heigei_1795222191019.jpg
  - Beat 2 (Ignite Wave):    v74_master_02_ignite_1795222195685.jpg
  - Beat 3 (Opal Climax):    v75_wide_canyon_03_climax_1795222518457.jpg
Saves `v7_step4_target_table.json` so Step 5 (540p Lookdev on Colab L4 GPU) can be verified
mathematically within +/-25% luminance ratio tolerance!
"""

import colorsys
import json
from pathlib import Path
import numpy as np
from PIL import Image

REPO = Path("/home/antigravity/Makeinu1/DaD_Ruosuen")
V7_DIR = REPO / "dm/episode-01/ending/video-pipeline/v7_blender_cycles"
ART_DIR = Path("/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/4733e009-f44e-4728-af83-1f85c37a4d1d")

CONCEPTS = {
    "beat1_heigei": {
        "file": ART_DIR / "v74_master_01_heigei_1795222191019.jpg",
        # Normalized (x0, y0, x1, y1) ROIs (top-left origin)
        "rois": {
            "moon_sky_rift":   (0.45, 0.02, 0.56, 0.22),
            "cavern_cliff":    (0.02, 0.15, 0.16, 0.65),
            "mirror_lake":     (0.18, 0.78, 0.42, 0.94),
            "whale_body":      (0.50, 0.35, 0.72, 0.58),
            "shore_flowers":   (0.62, 0.78, 0.80, 0.88),
        },
    },
    "beat2_ignite": {
        "file": ART_DIR / "v74_master_02_ignite_1795222195685.jpg",
        "rois": {
            "moon_sky_rift":   (0.45, 0.02, 0.56, 0.22),
            "cavern_cliff":    (0.02, 0.15, 0.16, 0.65),
            "mirror_lake":     (0.16, 0.75, 0.36, 0.88),
            "whale_body":      (0.49, 0.36, 0.66, 0.50),
            "shore_flowers":   (0.48, 0.82, 0.85, 0.96),
        },
    },
    "beat3_opal_climax": {
        "file": ART_DIR / "v75_wide_canyon_03_climax_1795222518457.jpg",
        "rois": {
            "moon_sky_rift":   (0.46, 0.02, 0.54, 0.20),
            "cavern_cliff":    (0.01, 0.12, 0.13, 0.68),
            "mirror_lake":     (0.32, 0.74, 0.56, 0.92),
            "whale_body":      (0.40, 0.38, 0.66, 0.56),
            "shore_flowers":   (0.14, 0.84, 0.36, 0.98),
        },
    },
}


def measure_roi(arr: np.ndarray, box):
    H, W, _ = arr.shape
    x0, y0, x1, y1 = int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)
    patch = arr[y0:y1, x0:x1]
    mean_rgb = patch.mean(axis=(0, 1))
    r, g, b = [float(v) / 255.0 for v in mean_rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    # Rec.709 perceptual luminance (0..100)
    luma = (0.2126 * r + 0.7152 * g + 0.0722 * b) * 100.0
    p95_luma = float(np.percentile(0.2126 * patch[..., 0] + 0.7152 * patch[..., 1] + 0.0722 * patch[..., 2], 95) / 2.55)
    return {
        "mean_rgb": [round(float(x), 1) for x in mean_rgb],
        "luma_0_100": round(luma, 1),
        "p95_luma_0_100": round(p95_luma, 1),
        "hue_deg": round(h * 360.0, 1),
        "sat_pct": round(s * 100.0, 1),
    }


def main():
    table = {
        "rule": "Infographic §05/§07/§12: Match Blender Cycles 540p lookdev stills within +/-25% of target luminance & ratios using Material Albedo/Emission multipliers ONLY (Exposure & Lights LOCKED!).",
        "beats": {},
    }
    for slug, cfg in CONCEPTS.items():
        im = Image.open(cfg["file"]).convert("RGB")
        arr = np.asarray(im, dtype=np.float32)
        res = {}
        for k, box in cfg["rois"].items():
            res[k] = measure_roi(arr, box)
        cliff_l = max(1.0, res["cavern_cliff"]["luma_0_100"])
        for k in res:
            res[k]["ratio_vs_cliff"] = round(res[k]["luma_0_100"] / cliff_l, 2)
        table["beats"][slug] = {
            "source_art": cfg["file"].name,
            "global_mean_luma": round(float((0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]).mean() / 2.55), 1),
            "regions": res,
        }

    out_fp = V7_DIR / "v7_step4_target_table.json"
    out_fp.write_text(json.dumps(table, indent=2, ensure_ascii=False))
    print(f"[STEP 4] Saved {out_fp}")
    for slug, b in table["beats"].items():
        print(f"\n=== {slug} (global L={b['global_mean_luma']}) ===")
        for rk, rv in b["regions"].items():
            print(f"  {rk:15s}: RGB={rv['mean_rgb']}  L={rv['luma_0_100']:5.1f} (p95={rv['p95_luma_0_100']:5.1f})  H={rv['hue_deg']:5.1f}°  S={rv['sat_pct']:4.1f}%  ratio_vs_cliff={rv['ratio_vs_cliff']:.2f}x")


if __name__ == "__main__":
    main()
