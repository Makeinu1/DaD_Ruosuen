#!/usr/bin/env python3
"""Slice the approved 96s v5.0 Pill Previs into 9 Gemini-Omni-1.2-Flash-native clips (ALL 8s-14s <= 15s limit!)
and extract exact 1280x720 PNG layout frames for Nano Banana Pro wireframe-to-painting keyframe generation."""

import json
from pathlib import Path

import av
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
V5_CLIPS = ROOT.parent / "v5-pill-previs" / "clips"
OUT_CLIPS = ROOT / "previs_clips_gemini"
OUT_FRAMES = ROOT / "previs_frames"

# 9 Gemini-native clips (EVERY clip 8s-14s <= 15s Omni 1.2 Flash limit!) mapped cleanly from the 6 raw v5.0 clips
GEMINI_CLIPS = [
    # (id, src_file, local_start_s, local_end_s, cuts_label, key_frame_offsets_s)
    ("G1_C1_C2_omen_shadow_12s",      "seedance_v5_clip1_C1_C2_omen_and_shadow_12s.mp4",          0.0, 12.0, "C1+C2 (0-12s)",      [("start", 2.4), ("C2", 9.0)]),
    ("G2_C3_C4ab_headon_13s",         "seedance_v5_clip2_C3_C4ab_headon_nearmiss_13s.mp4",        0.0, 13.0, "C3+C4a+C4b (12-25s)",[("start", 4.5), ("C4a", 7.8), ("C4b", 11.0)]),
    ("G3_C5ab_ignite_bloom_10s",      "seedance_v5_clip3_C5ab_C6a_bloom_to_snowstorm_19s.mp4",    0.0, 10.0, "C5a+C5b (25-35s)",   [("start", 2.8), ("C5b", 7.8)]),
    ("G4_C6a_freeze_tilt_9s",         "seedance_v5_clip3_C5ab_C6a_bloom_to_snowstorm_19s.mp4",   10.0, 19.0, "C6a (35-44s)",       [("start", 1.1), ("end", 8.4)]),
    ("G5_C6b_barrel_roll_8s",         "seedance_v5_clip4_C6bcd_playful_abyss_arch_25s.mp4",       0.0,  8.0, "C6b (44-52s)",       [("start", 0.5), ("mid", 4.0)]),
    ("G6_C6c_abyss_1plus3_8s",        "seedance_v5_clip4_C6bcd_playful_abyss_arch_25s.mp4",       8.0, 16.0, "C6c (52-60s)",       [("start", 4.0)]),
    ("G7_C6d_warm_glance_9s",         "seedance_v5_clip4_C6bcd_playful_abyss_arch_25s.mp4",      16.0, 25.0, "C6d (60-69s)",       [("start", 4.2)]),
    ("G8_C7ab_moon_dissolve_14s",     "seedance_v5_clip5_C7ab_ascent_and_moon_dissolve_14s.mp4",  0.0, 14.0, "C7a+C7b (69-83s)",   [("start", 3.0), ("C7b_mid", 9.6)]),
    ("G9_C7c_C8_true_snow_13s",       "seedance_v5_clip6_C7c_C8_true_snow_and_petal_13s.mp4",     0.0, 13.0, "C7c+C8 (83-96s)",    [("start", 3.0), ("C8", 9.5)]),
]


def main():
    OUT_CLIPS.mkdir(parents=True, exist_ok=True)
    OUT_FRAMES.mkdir(parents=True, exist_ok=True)
    fps = 24
    manifest = []

    # Cache decoded source clips (only 6 small files!)
    cache = {}
    for cid, src_name, s0, s1, cuts_lbl, kf_offs in GEMINI_CLIPS:
        if src_name not in cache:
            src_path = V5_CLIPS / src_name
            in_c = av.open(str(src_path))
            cache[src_name] = [fr.to_ndarray(format="rgb24") for fr in in_c.decode(video=0)]
            in_c.close()
        frames = cache[src_name]
        f0 = int(round(s0 * fps))
        f1 = min(len(frames), int(round(s1 * fps)))
        seg = frames[f0:f1]

        out_mp4 = OUT_CLIPS / f"gemini_previs_{cid}.mp4"
        out_c = av.open(str(out_mp4), mode="w")
        out_s = out_c.add_stream("libx264", rate=fps)
        out_s.width, out_s.height, out_s.pix_fmt = 1280, 720, "yuv420p"
        out_s.codec_context.color_primaries = 1
        out_s.codec_context.color_trc = 1
        out_s.codec_context.colorspace = 1
        out_s.options = {"crf": "18", "preset": "fast", "movflags": "+faststart"}
        for arr in seg:
            vf = av.VideoFrame.from_ndarray(arr, format="rgb24")
            for pkt in out_s.encode(vf):
                out_c.mux(pkt)
        for pkt in out_s.encode():
            out_c.mux(pkt)
        out_c.close()

        saved_kfs = []
        for tag, off_s in kf_offs:
            k_idx = min(len(seg) - 1, max(0, int(round(off_s * fps))))
            kf_name = f"previs_{cid.split('_')[0]}_{tag}.png"
            Image.fromarray(seg[k_idx]).save(OUT_FRAMES / kf_name)
            saved_kfs.append(kf_name)

        dur = len(seg) / fps
        manifest.append({
            "id": cid,
            "file": out_mp4.name,
            "duration_s": dur,
            "frames": len(seg),
            "cuts": cuts_lbl,
            "layout_frames": saved_kfs,
        })
        print(f"Prepared {out_mp4.name} ({len(seg)} frames, {dur:.1f}s) | layout PNGs: {saved_kfs}")

    (ROOT / "gemini_clips_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Total clips: {len(manifest)} | Total duration: {sum(m['duration_s'] for m in manifest):.1f}s")


if __name__ == "__main__":
    main()
