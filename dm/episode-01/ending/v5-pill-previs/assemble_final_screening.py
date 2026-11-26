#!/usr/bin/env python3
"""One-command Final 2026-12-23 Projector Screening Master Assembler for Episode 1 Ending v5.0.
Uses native PyAV (zero external ffmpeg CLI dependency!) + NumPy.

After generating the 6 Seedance 2.0 anime clips (placed in final_clips/ as final_clip1.mp4 .. final_clip6.mp4),
run:
  python3 dm/episode-01/ending/v5-pill-previs/assemble_final_screening.py

This script:
  1. Trims/normalizes each clip to its exact v5.0 timeline duration (12s / 13s / 19s / 25s / 14s / 13s = 96.0s)
     at 1920x1080 24fps.
  2. Applies subtle unified cinema finishing (gentle 2.5% anti-banding grain + soft projector vignette).
  3. Muxes audio/kousetsuka_v5_master_audio_96s.wav (-14.2 LUFS, true peak -3.2 dBFS).
  4. Embeds explicit Rec.709 (bt709) color tags so Windows / macOS / Chrome / projector render identical deep blues.
"""

import argparse
import json
import wave
from pathlib import Path

import av
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "scene_spec.json"
DEFAULT_AUDIO = ROOT / "audio" / "kousetsuka_v5_master_audio_96s.wav"


def build_vignette(w, h, strength=0.14):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r2 = ((xx / w - 0.5) * 2.0) ** 2 + ((yy / h - 0.5) * 2.0) ** 2
    return np.clip(1.0 - strength * r2, 0.72, 1.0)[:, :, None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips-dir", type=Path, default=ROOT / "final_clips", help="Folder with final_clip1.mp4 .. final_clip6.mp4")
    ap.add_argument("--audio", type=Path, default=DEFAULT_AUDIO, help="Master 96s WAV audio")
    ap.add_argument("--out", type=Path, default=ROOT / "kousetsuka_v5_FINAL_SCREENING_1080p.mp4", help="Output screening master MP4")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--no-grade", action="store_true", help="Skip subtle anti-banding grain & vignette")
    args = ap.parse_args()

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    fps = int(spec["fps"])
    clips = spec["clips"]
    for idx in range(len(clips)):
        fp = args.clips_dir / f"final_clip{idx + 1}.mp4"
        if not fp.exists():
            raise SystemExit(f"Missing Seedance output clip: {fp}\nPlace final_clip1.mp4 .. final_clip6.mp4 in {args.clips_dir}")
    if not args.audio.exists():
        raise SystemExit(f"Missing master audio WAV: {args.audio}")

    out_c = av.open(str(args.out), mode="w")
    out_v = out_c.add_stream("libx264", rate=fps)
    out_v.width = args.width
    out_v.height = args.height
    out_v.pix_fmt = "yuv420p"
    out_v.codec_context.color_primaries = 1  # bt709
    out_v.codec_context.color_trc = 1        # bt709
    out_v.codec_context.colorspace = 1       # bt709
    out_v.options = {"crf": "16", "preset": "slow", "movflags": "+faststart"}

    with wave.open(str(args.audio), "rb") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32767.0
        pcm = raw.reshape(-1, nch).T  # (2, N)

    out_a = out_c.add_stream("aac", rate=sr)
    out_a.layout = "stereo"
    out_a.bit_rate = 256000

    vig = build_vignette(args.width, args.height) if not args.no_grade else None
    rng = np.random.default_rng(20261223)

    total_frames = 0
    for idx, cl in enumerate(clips):
        fp = args.clips_dir / f"final_clip{idx + 1}.mp4"
        target_n = int(round((cl["end"] - cl["start"]) * fps))
        in_c = av.open(str(fp))
        decoded = []
        for fr in in_c.decode(video=0):
            decoded.append(fr.to_ndarray(format="rgb24"))
        in_c.close()
        if not decoded:
            raise SystemExit(f"No video frames decoded from {fp}")

        # Resample/trim cleanly to exact target_n frames at 24fps
        for fi in range(target_n):
            src_idx = min(len(decoded) - 1, int(round(fi * (len(decoded) / target_n))))
            arr = decoded[src_idx]
            if arr.shape[1] != args.width or arr.shape[0] != args.height:
                arr = np.asarray(Image.fromarray(arr).resize((args.width, args.height), Image.Resampling.LANCZOS))
            if vig is not None:
                f_arr = arr.astype(np.float32) * vig + rng.normal(0.0, 1.8, size=arr.shape).astype(np.float32)
                arr = np.clip(f_arr, 0, 255).astype(np.uint8)
            vf = av.VideoFrame.from_ndarray(arr, format="rgb24")
            for pkt in out_v.encode(vf):
                out_c.mux(pkt)
            total_frames += 1
        print(f"  Assembled Clip {idx + 1}: {target_n} frames ({target_n / fps:.1f}s)")

    for pkt in out_v.encode():
        out_c.mux(pkt)

    chunk = 1024
    pts = 0
    for s0 in range(0, pcm.shape[1], chunk):
        blk = pcm[:, s0 : s0 + chunk]
        if blk.shape[1] < chunk:
            blk = np.hstack([blk, np.zeros((2, chunk - blk.shape[1]), dtype=np.float32)])
        af = av.AudioFrame.from_ndarray(blk, format="fltp", layout="stereo")
        af.sample_rate = sr
        af.pts = pts
        pts += chunk
        for pkt in out_a.encode(af):
            out_c.mux(pkt)
    for pkt in out_a.encode():
        out_c.mux(pkt)
    out_c.close()
    print(f"DONE: {args.out} ({total_frames} frames / {total_frames / fps:.2f}s, 1080p Rec.709 + -14 LUFS AAC)")


if __name__ == "__main__":
    main()
