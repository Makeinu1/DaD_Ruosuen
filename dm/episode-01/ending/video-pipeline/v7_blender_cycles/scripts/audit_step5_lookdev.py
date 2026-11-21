#!/usr/bin/env python3
"""
Step 5 Automated ±25% Numeric Target Audit + 5-Frame Lookdev Contact Sheet Builder.
Compares Blender Cycles 540p renders against v7_step4_target_table.json.
"""

import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = Path("/home/antigravity/Makeinu1/DaD_Ruosuen")
V7_DIR = REPO / "dm/episode-01/ending/video-pipeline/v7_blender_cycles"
TARGET_JSON = V7_DIR / "v7_step4_target_table.json"
OUT_DIR = V7_DIR / "out/step5_lookdev"
AUDIT_JSON = OUT_DIR / "step5_numeric_audit.json"
SHEET_PNG = OUT_DIR / "v7_step5_lookdev_5sheet.png"

ROIS = {
    "moon_sky_rift": (0.40, 0.00, 0.62, 0.25),
    "cavern_cliff":  (0.02, 0.12, 0.24, 0.62),
    "mirror_lake":   (0.22, 0.64, 0.78, 0.80),
    "whale_body":    (0.32, 0.30, 0.68, 0.62),
    "shore_flowers": (0.10, 0.82, 0.90, 0.99),
}

SHOT_MAP = [
    ("01_shadow_16s",   "01 (16.0s) Lake Ripples + Giant Submerged Shadow", None),
    ("02_approach_28s", "02 (28.0s) Close Foreground Approach & Heigei",    "beat1_heigei"),
    ("03_turnback_33s", "03 (33.5s) Graceful Turn-Back Toward Moonbeam",    None),
    ("04_ignite_41s",   "04 (41.0s) Phase 1 Ignition + Shore Awakening",    "beat2_ignite"),
    ("05_climax_56s",   "05 (56.0s) Phase 2->3 Pearl-Opal x Golden Snow",   "beat3_opal_climax"),
]


def measure_image(fp: Path):
    arr = np.asarray(Image.open(fp).convert("RGB"), dtype=np.float32)
    h, w, _ = arr.shape
    luma_full = (0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]) / 2.55
    res = {"global_luma": round(float(luma_full.mean()), 2), "regions": {}}
    for rname, (x0, y0, x1, y1) in ROIS.items():
        crop = arr[int(y0 * h) : int(y1 * h), int(x0 * w) : int(x1 * w)]
        luma = (0.2126 * crop[:, :, 0] + 0.7152 * crop[:, :, 1] + 0.0722 * crop[:, :, 2]) / 2.55
        # For whale_body & shore_flowers, also compute p90/p95 so localized hero contrast is visible
        res["regions"][rname] = {
            "luma": round(float(luma.mean()), 2),
            "p95": round(float(np.percentile(luma, 95)), 2),
            "mean_rgb": [round(float(crop[:, :, c].mean()), 1) for c in range(3)],
        }
    cliff_l = max(1.0, res["regions"]["cavern_cliff"]["luma"])
    for rname, d in res["regions"].items():
        d["ratio_vs_cliff"] = round(d["luma"] / cliff_l, 2)
    return res


def main():
    targets = json.loads(TARGET_JSON.read_text())["beats"]
    report = {"shots": {}, "pass_summary": []}

    print("=" * 84)
    print("STEP 5 CYCLES GPU 540p LOOKDEV — AUTOMATED +/-25% TARGET AUDIT")
    print("=" * 84)

    for slug, label, beat_key in SHOT_MAP:
        fp = OUT_DIR / f"lookdev_{slug}.png"
        if not fp.exists():
            print(f"[MISSING] {fp}")
            continue
        m = measure_image(fp)
        entry = {"label": label, "measured": m, "comparisons": {}}
        print(f"\n[{slug}] {label} | global_L={m['global_luma']:.1f}")
        if beat_key and beat_key in targets:
            t_beat = targets[beat_key]
            g_tgt = t_beat["global_mean_luma"]
            g_err = (m["global_luma"] - g_tgt) / max(1.0, g_tgt) * 100.0
            print(f"  Global Luma: {m['global_luma']:5.1f} vs target {g_tgt:5.1f} ({g_err:+5.1f}%)")
            for rname, r_tgt in t_beat["regions"].items():
                ml = m["regions"][rname]["luma"]
                tl = r_tgt["luma_0_100"]
                err = (ml - tl) / max(1.0, tl) * 100.0
                ok = abs(err) <= 25.0
                flag = "PASS" if ok else "TUNE"
                entry["comparisons"][rname] = {
                    "measured_luma": ml,
                    "target_luma": tl,
                    "err_pct": round(err, 1),
                    "p95": m["regions"][rname]["p95"],
                    "status": flag,
                }
                print(f"    {rname:14s}: L={ml:5.1f} (p95={m['regions'][rname]['p95']:5.1f}) vs tgt={tl:5.1f} | {err:+6.1f}% [{flag}]")
        else:
            for rname, rd in m["regions"].items():
                print(f"    {rname:14s}: L={rd['luma']:5.1f} (p95={rd['p95']:5.1f}, vs_cliff={rd['ratio_vs_cliff']:.2f}x)")
        report["shots"][slug] = entry

    AUDIT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n[AUDIT] Wrote {AUDIT_JSON}")

    # Build 3x2 labeled Contact Sheet (1920x900)
    tw, th = 640, 360
    pad_top = 28
    sheet = Image.new("RGB", (tw * 3, (th + pad_top) * 2), (10, 14, 22))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
        font_sm = font

    for idx, (slug, label, beat_key) in enumerate(SHOT_MAP):
        fp = OUT_DIR / f"lookdev_{slug}.png"
        if not fp.exists():
            continue
        im = Image.open(fp).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        col, row = idx % 3, idx // 3
        x0, y0 = col * tw, row * (th + pad_top)
        draw.rectangle([x0, y0, x0 + tw, y0 + pad_top], fill=(16, 22, 34))
        draw.text((x0 + 8, y0 + 6), label[:64], fill=(225, 238, 255), font=font)
        sheet.paste(im, (x0, y0 + pad_top))

    # Slot 6: Numeric QA Summary Card
    sx0, sy0 = 2 * tw, th + pad_top
    draw.rectangle([sx0, sy0, sx0 + tw, sy0 + th + pad_top], fill=(12, 18, 28))
    draw.text((sx0 + 14, sy0 + 10), "STEP 5 CYCLES L4 GPU — +/-25% QA SUMMARY", fill=(140, 210, 255), font=font)
    yy = sy0 + 38
    for slug, _, beat_key in SHOT_MAP:
        if not beat_key or slug not in report["shots"]:
            continue
        draw.text((sx0 + 14, yy), f"{slug} vs {beat_key}:", fill=(255, 230, 160), font=font_sm)
        yy += 18
        for rname, c in report["shots"][slug]["comparisons"].items():
            col_txt = (120, 240, 160) if c["status"] == "PASS" else (255, 165, 110)
            line = f"  {rname:13s} {c['measured_luma']:4.1f}/{c['target_luma']:4.1f} ({c['err_pct']:+5.1f}%) {c['status']}"
            draw.text((sx0 + 14, yy), line, fill=col_txt, font=font_sm)
            yy += 16
        yy += 8

    sheet.save(SHEET_PNG)
    print(f"[SHEET] Saved {SHEET_PNG}")


if __name__ == "__main__":
    main()
