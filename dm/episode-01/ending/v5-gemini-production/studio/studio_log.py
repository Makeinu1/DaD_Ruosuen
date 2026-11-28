#!/usr/bin/env python3
"""Zero-Extra-Spend Google AI Pro + Antigravity Studio Ledger & Asset Registrar.

Enforces:
  - 0 JPY extra spend (no paid API calls, no credit top-ups).
  - Hard quota/credit guard: refuses to approve a run if Google AI Pro monthly+daily allowance would be exceeded.
  - Full provenance logging (model, prompt, reference assets + hashes, output file + hash, media metadata, credits)
    into logs/generation_log.jsonl and per-file <output>.meta.json sidecars.
"""

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

try:
    import av
except ImportError:
    av = None
try:
    from PIL import Image
except ImportError:
    Image = None

STUDIO_ROOT = Path(__file__).resolve().parent
IMAGES_DIR = STUDIO_ROOT / "images"
VIDEOS_DIR = STUDIO_ROOT / "videos"
LOGS_DIR = STUDIO_ROOT / "logs"
LEDGER_PATH = LOGS_DIR / "generation_log.jsonl"
BUDGET_PATH = LOGS_DIR / "quota_budget.json"

DEFAULT_BUDGET = {
    "plan": "Google AI Pro (0 JPY extra spend)",
    "monthly_flow_credits_limit": 1000,
    "daily_flow_credits_limit": 50,
    "daily_nano_banana_pro_images_limit": 100,
    "monthly_flow_credits_used": 0,
    "daily_flow_credits_used": 0,
    "daily_nano_banana_pro_images_used": 0,
    "last_daily_reset_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
    "allow_paid_topup": False,
    "allow_paid_api": False,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_budget() -> dict:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not BUDGET_PATH.exists():
        BUDGET_PATH.write_text(json.dumps(DEFAULT_BUDGET, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return dict(DEFAULT_BUDGET)
    b = json.loads(BUDGET_PATH.read_text(encoding="utf-8"))
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    if b.get("last_daily_reset_utc") != today:
        b["daily_flow_credits_used"] = 0
        b["daily_nano_banana_pro_images_used"] = 0
        b["last_daily_reset_utc"] = today
        BUDGET_PATH.write_text(json.dumps(b, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return b


def save_budget(b: dict):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    BUDGET_PATH.write_text(json.dumps(b, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def estimate_omni_credits(duration_s: float, resolution: str) -> int:
    """Official Nov 2026 Google Flow Omni Flash 1.2 credit cost (360p: 1/s up to 10s, 2/s 11-15s; 720p: 3/s up to 10s, 6/s 11-15s)."""
    d = max(1, int(round(duration_s)))
    base_s = min(10, d)
    extra_s = max(0, d - 10)
    if resolution == "360p":
        return base_s * 1 + extra_s * 2
    return base_s * 3 + extra_s * 6


def check_budget_or_stop(b: dict, media_type: str, credits_cost: int, model: str):
    if media_type == "image" and "nano-banana-pro" in model.lower():
        rem_img = b["daily_nano_banana_pro_images_limit"] - b["daily_nano_banana_pro_images_used"]
        if rem_img < 1:
            raise SystemExit("STOP: Daily Nano Banana Pro image quota reached (0 remaining). Wait 24h; 0 JPY extra spend enforced.")
    if credits_cost > 0:
        daily_rem = max(0, b["daily_flow_credits_limit"] - b["daily_flow_credits_used"])
        monthly_rem = max(0, b["monthly_flow_credits_limit"] - b["monthly_flow_credits_used"])
        if daily_rem + monthly_rem < credits_cost:
            raise SystemExit(
                f"STOP: Requested {credits_cost} Flow credits exceeds remaining plan allowance "
                f"(daily={daily_rem}, monthly={monthly_rem}). Extra credit purchase is forbidden (0 JPY cap)."
            )


def consume_budget(b: dict, media_type: str, credits_cost: int, model: str):
    if media_type == "image" and "nano-banana-pro" in model.lower():
        b["daily_nano_banana_pro_images_used"] += 1
    if credits_cost > 0:
        daily_rem = max(0, b["daily_flow_credits_limit"] - b["daily_flow_credits_used"])
        from_daily = min(daily_rem, credits_cost)
        b["daily_flow_credits_used"] += from_daily
        b["monthly_flow_credits_used"] += (credits_cost - from_daily)
    save_budget(b)


def _probe_with_ffprobe(path: Path, media_type: str) -> dict | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        out = subprocess.check_output(
            [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)],
            text=True,
        )
        data = json.loads(out)
        streams = data.get("streams", [])
        v = next((s for s in streams if s.get("codec_type") == "video"), None)
        if not v:
            return None
        if media_type == "image":
            return {
                "width": int(v.get("width", 0)),
                "height": int(v.get("height", 0)),
                "format": (v.get("codec_name") or path.suffix.lstrip(".")).upper(),
                "mode": v.get("pix_fmt", "unknown"),
            }
        rate_str = v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1"
        num, _, den = rate_str.partition("/")
        fps = float(num) / float(den) if den and float(den) != 0 else 0.0
        dur = float(data.get("format", {}).get("duration") or v.get("duration") or 0.0)
        return {
            "width": int(v.get("width", 0)),
            "height": int(v.get("height", 0)),
            "fps": round(fps, 3),
            "duration_s": round(dur, 3),
            "codec": v.get("codec_name", "unknown"),
            "has_audio": any(s.get("codec_type") == "audio" for s in streams),
        }
    except Exception:
        return None


def inspect_media(path: Path, media_type: str) -> dict:
    if media_type == "image":
        if Image is not None:
            with Image.open(path) as im:
                return {"width": im.width, "height": im.height, "format": im.format, "mode": im.mode}
        probed = _probe_with_ffprobe(path, "image")
        if probed:
            return probed
        return {"bytes": path.stat().st_size, "format": path.suffix.lstrip(".").upper()}
    if av is not None:
        c = av.open(str(path))
        v = c.streams.video[0]
        dur = float(c.duration) / 1e6 if c.duration else 0.0
        info = {
            "width": v.width,
            "height": v.height,
            "fps": float(v.average_rate) if v.average_rate else 0.0,
            "duration_s": round(dur, 3),
            "codec": v.codec_context.name,
            "has_audio": len(c.streams.audio) > 0,
        }
        c.close()
        return info
    probed = _probe_with_ffprobe(path, "video")
    if probed:
        return probed
    return {"bytes": path.stat().st_size}


def cmd_check(args):
    b = load_budget()
    est = estimate_omni_credits(args.duration, args.resolution) if args.media_type == "video" else 0
    check_budget_or_stop(b, args.media_type, est, args.model)
    print(json.dumps({
        "status": "OK_WITHIN_PLAN",
        "estimated_flow_credits": est,
        "daily_flow_credits_remaining": b["daily_flow_credits_limit"] - b["daily_flow_credits_used"],
        "monthly_flow_credits_remaining": b["monthly_flow_credits_limit"] - b["monthly_flow_credits_used"],
        "daily_nbp_images_remaining": b["daily_nano_banana_pro_images_limit"] - b["daily_nano_banana_pro_images_used"],
    }, indent=2, ensure_ascii=False))


def cmd_record(args):
    b = load_budget()
    src = Path(args.source).resolve()
    if not src.exists():
        raise SystemExit(f"Source file not found: {src}")

    dest_dir = IMAGES_DIR if args.media_type == "image" else VIDEOS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_name = args.name if args.name else src.name
    dest = (dest_dir / dest_name).resolve()
    if src != dest:
        shutil.copy2(src, dest)

    credits_cost = args.credits
    if credits_cost < 0:
        credits_cost = estimate_omni_credits(args.duration, args.resolution) if args.media_type == "video" else 0

    check_budget_or_stop(b, args.media_type, credits_cost, args.model)
    consume_budget(b, args.media_type, credits_cost, args.model)

    refs_info = []
    for rp in args.ref or []:
        p = Path(rp)
        refs_info.append({
            "path": str(p),
            "sha256": sha256_file(p) if p.exists() else None,
        })

    prompt_text = Path(args.prompt_file).read_text(encoding="utf-8") if args.prompt_file else (args.prompt or "")
    media_meta = inspect_media(dest, args.media_type)
    entry = {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "media_type": args.media_type,
        "surface": args.surface,
        "model": args.model,
        "prompt": prompt_text,
        "references": refs_info,
        "output_path": str(dest),
        "output_sha256": sha256_file(dest),
        "output_bytes": dest.stat().st_size,
        "media_meta": media_meta,
        "flow_credits_spent": credits_cost,
        "extra_spend_jpy": 0,
        "qa_status": args.qa_status,
        "notes": args.notes or "",
    }

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as lf:
        lf.write(json.dumps(entry, ensure_ascii=False) + "\n")
    sidecar = dest.with_suffix(dest.suffix + ".meta.json")
    sidecar.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Recorded {args.media_type}: {dest}")
    print(f"Sidecar : {sidecar}")
    print(f"Ledger  : {LEDGER_PATH}")


def cmd_status(_args):
    b = load_budget()
    count = sum(1 for _ in LEDGER_PATH.open(encoding="utf-8")) if LEDGER_PATH.exists() else 0
    print(json.dumps({"budget": b, "logged_generations": count}, indent=2, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description="Zero-Extra-Spend Google AI Pro + Antigravity Studio Logger")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_st = sub.add_parser("status", help="Show remaining Google AI Pro quota/credits & log count")
    p_st.set_defaults(fn=cmd_status)

    p_ck = sub.add_parser("check", help="Check if a planned generation fits within 0 JPY extra-spend limits")
    p_ck.add_argument("--media-type", choices=["image", "video"], required=True)
    p_ck.add_argument("--model", required=True)
    p_ck.add_argument("--duration", type=float, default=8.0)
    p_ck.add_argument("--resolution", choices=["360p", "720p"], default="720p")
    p_ck.set_defaults(fn=cmd_check)

    p_rec = sub.add_parser("record", help="Copy/save output into studio/ and record full provenance + quota")
    p_rec.add_argument("--media-type", choices=["image", "video"], required=True)
    p_rec.add_argument("--surface", required=True, help="e.g. antigravity-generate-image | google-flow-browser")
    p_rec.add_argument("--model", required=True, help="e.g. antigravity-standard-image | nano-banana-pro | gemini-omni-1.2-flash")
    p_rec.add_argument("--source", required=True, help="Path to generated PNG/JPG/MP4")
    p_rec.add_argument("--name", default="", help="Optional target filename in studio/images or studio/videos")
    p_rec.add_argument("--prompt", default="")
    p_rec.add_argument("--prompt-file", default="")
    p_rec.add_argument("--ref", action="append", default=[])
    p_rec.add_argument("--credits", type=int, default=-1, help="Flow credits spent (0 for images or Antigravity built-in)")
    p_rec.add_argument("--duration", type=float, default=8.0)
    p_rec.add_argument("--resolution", choices=["360p", "720p"], default="720p")
    p_rec.add_argument("--qa-status", default="needs_review", choices=["needs_review", "approved", "rejected"])
    p_rec.add_argument("--notes", default="")
    p_rec.set_defaults(fn=cmd_record)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
