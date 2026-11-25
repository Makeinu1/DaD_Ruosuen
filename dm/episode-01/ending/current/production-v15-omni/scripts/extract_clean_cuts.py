#!/usr/bin/env python3
"""Extract clean (HUD-free) per-cut clips from v14.10 previs for Gemini Omni 1.2 Flash.

Supports two modes:
  --mode clean-render : Re-renders exact cuts from ruosuen_v14_previs.py with the bottom-left
                        HUD label disabled (zero text artifacts, exact 1280x720 24fps).
  --mode fast-delogo  : Slices v14-full-1280x720-24fps.mp4 directly via ffmpeg and removes
                        the bottom-left HUD label box with delogo (runs in ~1 second).

Also supports --pad-min 3.0 to pad cuts shorter than Gemini Omni 1.2 Flash's 3-second minimum
by holding/mirroring edge frames, recording trim offsets in cuts_manifest.json.

Examples:
  python3 scripts/extract_clean_cuts.py --cuts R14,R09,R15 --out work/pilot_v14_10
  python3 scripts/extract_clean_cuts.py --cuts R14,R09,R15 --mode fast-delogo --out work/pilot_fast
  python3 scripts/extract_clean_cuts.py --all --pad-min 3.0 --out work/all_clean
"""
import argparse
import json
import math
import multiprocessing as mp
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OMNI_DIR = HERE.parent
CURRENT_DIR = OMNI_DIR.parent
PREVIS_DIR = CURRENT_DIR / "previs" / "v14-director-rebuild"
SHOTLIST_PATH = CURRENT_DIR / "shotlist-v14-director-rebuild.json"
FULL_MP4_PATH = PREVIS_DIR / "artifacts" / "v14-full" / "v14-full-1280x720-24fps.mp4"

FFMPEG = shutil.which("ffmpeg")
if not FFMPEG:
    raise RuntimeError("ffmpeg not found on PATH")


def load_cuts(selected):
    data = json.loads(SHOTLIST_PATH.read_text(encoding="utf-8"))
    cuts = data["cuts"]
    by_id = {c["id"]: c for c in cuts}
    if selected == "ALL":
        return cuts
    out = []
    for cid in selected:
        if cid not in by_id:
            raise ValueError(f"Unknown cut id {cid!r}. Available: {', '.join(by_id)}")
        out.append(by_id[cid])
    return out


# Worker globals for clean-render multiprocessing
_WORKER_RENDERER = None


def _init_worker(width, height):
    global _WORKER_RENDERER
    sys.path.insert(0, str(PREVIS_DIR))
    import ruosuen_v14_previs as previs_mod

    r = previs_mod.Renderer(width, height)
    r.label = lambda *a, **k: None  # Disable bottom-left HUD label
    _WORKER_RENDERER = r


def _render_one_frame(args):
    idx, t = args
    im, info = _WORKER_RENDERER.frame(t)
    return idx, im.tobytes(), info["cut"], round(float(im.convert("L").resize((64, 36)).tobytes().__len__()), 1)


def compute_frame_times(start_s, end_s, fps, pad_min_s):
    """Return exact frame timestamps in the global timeline, plus optional symmetric padding."""
    raw_frames = int(round((end_s - start_s) * fps))
    raw_dur = raw_frames / fps
    pad_head = 0
    pad_tail = 0
    if pad_min_s and raw_dur < pad_min_s:
        target_frames = int(math.ceil(pad_min_s * fps))
        extra = target_frames - raw_frames
        pad_head = extra // 2
        pad_tail = extra - pad_head

    # Sample strictly inside [start_s, end_s) using k / fps aligned to the full movie grid
    start_k = int(round(start_s * fps))
    base_times = [(start_k + i) / fps for i in range(raw_frames)]
    times = [base_times[0]] * pad_head + base_times + [base_times[-1]] * pad_tail
    return times, {
        "raw_frames": raw_frames,
        "raw_duration_s": round(raw_dur, 4),
        "pad_head_frames": pad_head,
        "pad_tail_frames": pad_tail,
        "output_frames": len(times),
        "output_duration_s": round(len(times) / fps, 4),
    }


def write_mp4_from_rgb_frames(rgb_frames, width, height, fps, out_path, crf=16):
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for buf in rgb_frames:
            proc.stdin.write(buf)
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed writing {out_path}")


def extract_fast_delogo(cut, fps, pad_min_s, out_mp4, width, height, crf=16):
    start_s = float(cut["start_s"])
    end_s = float(cut["end_s"])
    times, meta = compute_frame_times(start_s, end_s, fps, pad_min_s)

    # Bottom-left HUD box in 1280x720: (8, 684) .. (~285, 712)
    # Delogo covers (6, 678, w=294, h=38) which is strictly inside frame bounds.
    vf_parts = ["delogo=x=6:y=678:w=294:h=38:show=0"]
    if width != 1280 or height != 720:
        vf_parts.append(f"scale={width}:{height}:flags=lanczos")
    if meta["pad_head_frames"] > 0 or meta["pad_tail_frames"] > 0:
        ph = meta["pad_head_frames"] / fps
        pt = meta["pad_tail_frames"] / fps
        vf_parts.append(f"tpad=start_duration={ph:.6f}:start_mode=clone:stop_duration={pt:.6f}:stop_mode=clone")

    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start_s:.6f}", "-t", f"{end_s - start_s:.6f}",
        "-i", str(FULL_MP4_PATH),
        "-vf", ",".join(vf_parts),
        "-r", str(fps), "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True)
    return meta


def build_contact_sheet(cut_outputs, out_sheet, thumb_w=420):
    thumb_h = thumb_w * 9 // 16
    cols = 3  # start, mid, end
    rows = len(cut_outputs)
    pad = 8
    header_h = 26
    sheet = Image.new("RGB", (cols * (thumb_w + pad) + pad, rows * (thumb_h + header_h + pad) + pad), (8, 12, 20))
    draw = ImageDraw.Draw(sheet)

    for r_idx, item in enumerate(cut_outputs):
        mp4 = Path(item["mp4"])
        dur = item["output_duration_s"]
        sample_ts = [min(0.25, dur * 0.1), dur * 0.5, max(0.0, dur - 0.25)]
        for c_idx, ts in enumerate(sample_ts):
            cmd = [
                FFMPEG, "-hide_banner", "-loglevel", "error",
                "-ss", f"{ts:.3f}", "-i", str(mp4),
                "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-vf", f"scale={thumb_w}:{thumb_h}:flags=lanczos", "-",
            ]
            raw = subprocess.check_output(cmd)
            im = Image.frombytes("RGB", (thumb_w, thumb_h), raw)
            x = pad + c_idx * (thumb_w + pad)
            y = pad + r_idx * (thumb_h + header_h + pad)
            sheet.paste(im, (x, y))
            label = f"{item['cut_id']}  t={ts:.2f}s / {dur:.1f}s ({item['mode']})"
            draw.text((x + 4, y + thumb_h + 5), label, fill=(225, 232, 240))

    out_sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_sheet, quality=88)


def main():
    ap = argparse.ArgumentParser(description="Extract HUD-free v14.10 previs cuts for Gemini Omni 1.2 Flash.")
    ap.add_argument("--cuts", default="R14,R09,R15", help="Comma-separated cut IDs (e.g. R14,R09,R15)")
    ap.add_argument("--all", action="store_true", help="Extract all 18 cuts from shotlist")
    ap.add_argument("--mode", choices=["clean-render", "fast-delogo"], default="clean-render")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--pad-min", type=float, default=0.0, help="Pad cuts shorter than N seconds (e.g. 3.0 for Omni)")
    ap.add_argument("--workers", type=int, default=1, help="1 keeps ruosuen_v14_previs petal cache warm")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sheet", type=Path, help="Optional verification contact sheet path (jpg/png)")
    args = ap.parse_args()

    width = args.width
    height = width * 9 // 16
    selected = "ALL" if args.all else [s.strip() for s in args.cuts.split(",") if s.strip()]
    cuts = load_cuts(selected)

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source_previs": "v14.10",
        "mode": args.mode,
        "width": width,
        "height": height,
        "fps": args.fps,
        "pad_min_s": args.pad_min,
        "cuts": [],
    }

    t_all = time.time()
    pool = None
    seq_renderer = None
    if args.mode == "clean-render":
        if args.workers <= 1:
            print(f"Starting sequential clean-render at {width}x{height}@{args.fps}fps...", flush=True)
            _init_worker(width, height)
            seq_renderer = _WORKER_RENDERER
        else:
            print(f"Starting clean-render with {args.workers} workers at {width}x{height}@{args.fps}fps...", flush=True)
            pool = mp.Pool(processes=args.workers, initializer=_init_worker, initargs=(width, height))

    try:
        for cut in cuts:
            cid = cut["id"]
            t0 = time.time()
            out_mp4 = args.out / f"{cid}_v14_10_clean.mp4"
            if args.mode == "fast-delogo":
                meta = extract_fast_delogo(cut, args.fps, args.pad_min, out_mp4, width, height, crf=args.crf)
            else:
                times, meta = compute_frame_times(float(cut["start_s"]), float(cut["end_s"]), args.fps, args.pad_min)
                if seq_renderer is not None:
                    rgb_frames = [seq_renderer.frame(t)[0].tobytes() for t in times]
                else:
                    tasks = list(enumerate(times))
                    results = pool.map(_render_one_frame, tasks)
                    results.sort(key=lambda x: x[0])
                    rgb_frames = [r[1] for r in results]
                write_mp4_from_rgb_frames(rgb_frames, width, height, args.fps, out_mp4, crf=args.crf)

            size_mb = out_mp4.stat().st_size / (1024 * 1024)
            elapsed = time.time() - t0
            entry = {
                "cut_id": cid,
                "start_s": cut["start_s"],
                "end_s": cut["end_s"],
                "mode": args.mode,
                "mp4": str(out_mp4),
                "size_mb": round(size_mb, 2),
                **meta,
            }
            manifest["cuts"].append(entry)
            print(
                f"  {cid}: {meta['output_duration_s']:.2f}s ({meta['output_frames']}f) -> {out_mp4.name} "
                f"[{size_mb:.2f} MB, {elapsed:.1f}s]",
                flush=True,
            )
    finally:
        if pool is not None:
            pool.close()
            pool.join()

    manifest_path = args.out / "cuts_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sheet_path = args.sheet or (args.out / "clean_cuts_preview.jpg")
    build_contact_sheet(manifest["cuts"], sheet_path)
    print(f"Done in {time.time() - t_all:.1f}s. Manifest: {manifest_path}  Preview: {sheet_path}", flush=True)


if __name__ == "__main__":
    main()
