#!/usr/bin/env python3
"""Assemble a clean, drag-and-drop upload folder for Google Flow (Gemini Omni 1.2 Flash).

Copies clean-rendered v14.10 MP4s and text-free reference art into one bundle directory,
and produces a text-free crop of WH01_identity_sheet.png (side + oblique front views)
so no Japanese header labels leak into video generation.
"""
import argparse
import shutil
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OMNI_DIR = HERE.parent
ENDING_DIR = OMNI_DIR.parent.parent  # dm/episode-01/ending


def make_clean_wh01_crop(src_path: Path, dst_path: Path):
    """Extract the top two panels (side & oblique front) without header/panel text bars."""
    im = Image.open(src_path).convert("RGB")
    w, h = im.size
    # Header bar occupies ~48px at top, panel labels occupy ~36px inside each quadrant top.
    # Middle divider sits around y=496 and x=806 on the 1612x956 sheet.
    y0 = int(h * 0.11)
    y1 = int(h * 0.50)
    left = im.crop((int(w * 0.01), y0, int(w * 0.49), y1))
    right = im.crop((int(w * 0.51), y0, int(w * 0.99), y1))
    gap = 12
    out = Image.new("RGB", (left.width + right.width + gap, left.height), (138, 138, 138))
    out.paste(left, (0, 0))
    out.paste(right, (left.width + gap, 0))
    out.save(dst_path, optimize=True)


def main():
    ap = argparse.ArgumentParser(description="Prepare Google Flow upload bundle for Omni 1.2 Flash PoC.")
    ap.add_argument("--mp4-dir", type=Path, action="append", required=True, help="Directory containing *_v14_10_clean.mp4")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    videos_dir = args.out / "01_base_videos"
    refs_dir = args.out / "02_reference_images"
    videos_dir.mkdir(parents=True, exist_ok=True)
    refs_dir.mkdir(parents=True, exist_ok=True)

    copied_mp4 = []
    for d in args.mp4_dir:
        for p in sorted(d.glob("*_v14_10_clean.mp4")):
            dst = videos_dir / p.name
            shutil.copy2(p, dst)
            copied_mp4.append(dst.name)

    ref_files = [
        ENDING_DIR / "images" / "adopted" / "CUT09_KEY_climax.png",
        ENDING_DIR / "images" / "adopted" / "CUT05_KEY_whale_emerges.png",
        ENDING_DIR / "images" / "adopted" / "CUT02_KEY_moon.png",
        ENDING_DIR / "v8" / "keyframe-test" / "refs" / "style_ref_painterly.png",
    ]
    for src in ref_files:
        if src.exists():
            shutil.copy2(src, refs_dir / src.name)

    wh01_src = ENDING_DIR / "v8" / "keyframe-test" / "refs" / "WH01_identity_sheet.png"
    if wh01_src.exists():
        make_clean_wh01_crop(wh01_src, refs_dir / "WH01_clean_side_oblique.png")

    guide_src = OMNI_DIR / "handoff" / "flow_poc_guide.md"
    if guide_src.exists():
        shutil.copy2(guide_src, args.out / "00_FLOW_PROMPTS_AND_GUIDE.md")

    print(f"Bundle ready at {args.out}")
    print(f"  Videos: {copied_mp4}")
    print(f"  Refs:   {[p.name for p in sorted(refs_dir.iterdir())]}")


if __name__ == "__main__":
    main()
