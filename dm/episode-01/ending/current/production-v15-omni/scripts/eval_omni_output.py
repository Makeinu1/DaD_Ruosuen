#!/usr/bin/env python3
"""Evaluate Gemini Omni 1.2 Flash outputs against clean v14.10 previs cuts.

Computes metrics compatible with production-v15/post/compare.py, plus:
  - adherence        : blurred luma correlation vs. previs guide (position & motion lock)
  - flicker          : high-frequency temporal frame-to-frame delta vs. guide
  - mean_luma        : average brightness (start / mid / end) to check night/projector range
  - invented_bright  : fraction of bright pixels (>0.35) where guide is dark (<0.12),
                       which flags invented rock walls or unwanted moonbeams
  - side-by-side mp4 : left = v14.10 clean previs, right = Omni candidate
  - review sheet jpg : compact comparison strip suitable for GitHub PR review

Usage:
  python3 scripts/eval_omni_output.py \
      --guide work/pilot_v14_10/R14_v14_10_clean.mp4 \
      --cand omniA=outputs/R14_flow_01.mp4 \
      --times 1.0,2.5,4.5,6.8 \
      --sheet review/R14_omni_vs_previs.jpg \
      --sbs outputs/R14_previs_vs_omniA.mp4
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

FFMPEG = shutil.which("ffmpeg")
if not FFMPEG:
    raise RuntimeError("ffmpeg not found on PATH")


def decode_frames(path, w=320, h=180):
    tmp = Path(tempfile.mkdtemp(prefix="omni_eval_"))
    subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf", f"scale={w}:{h}", str(tmp / "%04d.png")],
        check=True,
    )
    fs = sorted(tmp.glob("*.png"))
    if not fs:
        raise RuntimeError(f"No frames decoded from {path}")
    arr = np.stack([np.asarray(Image.open(f).convert("L"), np.float32) / 255.0 for f in fs])
    return arr, fs, tmp


def measure_candidate(g, x):
    n = min(len(g), len(x))
    g, x = g[:n], x[:n]
    gb = ndi.gaussian_filter(g, (0, 3, 3))
    xb = ndi.gaussian_filter(x, (0, 3, 3))
    corrs = []
    for i in range(n):
        gs, xs = gb[i].ravel(), xb[i].ravel()
        if gs.std() > 1e-5 and xs.std() > 1e-5:
            corrs.append(float(np.corrcoef(gs, xs)[0, 1]))
    adherence = float(np.mean(corrs)) if corrs else 0.0

    hp = lambda v: v - ndi.gaussian_filter(v, (0, 2, 2))
    dx = float(np.abs(np.diff(hp(x), axis=0)).mean()) if n > 1 else 0.0
    dg = float(np.abs(np.diff(hp(g), axis=0)).mean()) if n > 1 else 0.0

    # Flag invented bright structures (e.g. rock walls, extra moonbeams) in dark guide regions
    dark_guide = gb < 0.12
    invented = float(((xb > 0.30) & dark_guide).sum() / max(1, dark_guide.sum()))

    idxs = [0, n // 2, n - 1]
    luma_x = [round(float(x[i].mean() * 255.0), 1) for i in idxs]
    luma_g = [round(float(g[i].mean() * 255.0), 1) for i in idxs]

    return {
        "frames_compared": n,
        "adherence": round(adherence, 3),
        "flicker": round(dx, 4),
        "guide_flicker": round(dg, 4),
        "invented_bright_ratio": round(invented, 4),
        "mean_luma_start_mid_end": luma_x,
        "guide_luma_start_mid_end": luma_g,
    }


def make_side_by_side(guide_mp4, cand_mp4, out_mp4, width_each=640):
    h = width_each * 9 // 16
    fc = (
        f"[0:v]scale={width_each}:{h}:flags=lanczos,setsar=1[left];"
        f"[1:v]scale={width_each}:{h}:flags=lanczos,setsar=1[right];"
        f"[left][right]hstack=inputs=2[v]"
    )
    subprocess.run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(guide_mp4), "-i", str(cand_mp4),
            "-filter_complex", fc, "-map", "[v]", "-an",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-shortest", "-movflags", "+faststart",
            str(out_mp4),
        ],
        check=True,
    )


def main():
    ap = argparse.ArgumentParser(description="Compare Gemini Omni 1.2 Flash outputs against clean v14.10 previs.")
    ap.add_argument("--guide", type=Path, required=True)
    ap.add_argument("--cand", action="append", required=True, help="name=path/to/video.mp4")
    ap.add_argument("--times", default="1.0,2.5,4.5,6.8", help="Comma-separated timestamps (s) for review sheet")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--sheet", type=Path, help="Output review sheet jpg/png/webp")
    ap.add_argument("--sheet-width", type=int, default=360)
    ap.add_argument("--sbs", type=Path, help="Optional side-by-side mp4 for the first candidate")
    ap.add_argument("--json-out", type=Path, help="Optional JSON report path")
    args = ap.parse_args()

    tmp_dirs = []
    try:
        G, gfs, gtmp = decode_frames(args.guide)
        tmp_dirs.append(gtmp)
        rows = [("previs_v14.10", gfs)]
        report = {"guide": str(args.guide), "guide_frames": len(G), "candidates": {}}
        first_cand_path = None

        for spec in args.cand:
            name, path_str = spec.split("=", 1)
            cand_path = Path(path_str)
            if first_cand_path is None:
                first_cand_path = cand_path
            C, cfs, ctmp = decode_frames(cand_path)
            tmp_dirs.append(ctmp)
            report["candidates"][name] = {"path": str(cand_path), "frames": len(C), **measure_candidate(G, C)}
            rows.append((name, cfs))

        print(json.dumps(report, ensure_ascii=False, indent=2))
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        if args.sheet:
            args.sheet.parent.mkdir(parents=True, exist_ok=True)
            ts = [float(t) for t in args.times.split(",") if t.strip()]
            w = args.sheet_width
            h = w * 9 // 16
            pad = 6
            lbl_h = 22
            sheet = Image.new("RGB", (len(ts) * (w + pad) + pad, len(rows) * (h + lbl_h + pad) + pad), (8, 12, 20))
            draw = ImageDraw.Draw(sheet)
            for r_i, (name, fs) in enumerate(rows):
                for c_i, t in enumerate(ts):
                    f_i = min(len(fs) - 1, max(0, int(round(t * args.fps))))
                    im = Image.open(fs[f_i]).convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
                    x = pad + c_i * (w + pad)
                    y = pad + r_i * (h + lbl_h + pad)
                    sheet.paste(im, (x, y))
                    draw.text((x + 4, y + h + 4), f"{name}  {t:.2f}s", fill=(225, 232, 240))
            sheet.save(args.sheet, quality=86)
            print(f"Saved sheet: {args.sheet}")

        if args.sbs and first_cand_path is not None:
            args.sbs.parent.mkdir(parents=True, exist_ok=True)
            make_side_by_side(args.guide, first_cand_path, args.sbs)
            print(f"Saved side-by-side: {args.sbs}")
    finally:
        for d in tmp_dirs:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
