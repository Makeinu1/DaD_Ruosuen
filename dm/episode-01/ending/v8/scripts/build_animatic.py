"""Build v8 animatic: existing 16 stills on the v8 timing + temp score.

Usage: python3 build_animatic.py STILLS_DIR AUDIO_WAV OUT_MP4
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
TL = json.loads((HERE.parent / "v8_timeline.json").read_text())
STILLS, AUDIO, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
W, H, FPS = 1280, 720, TL["fps"]
SPB = TL["seconds_per_beat"]
WORK = Path(os.environ.get("ANIMATIC_WORK_DIR", "/tmp/v8_animatic_work"))
WORK.mkdir(parents=True, exist_ok=True)
SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Medium.ttc"
fs = ImageFont.truetype(SANS, 22, index=0)
fs_small = ImageFont.truetype(SANS, 17, index=0)


def fr(beat):
    return round(beat * SPB * FPS)


def label_png(c, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, H - 64, W, H], fill=(0, 0, 0, 150))
    t0, t1 = c["beat_in"] * SPB, c["beat_out"] * SPB
    d.text((18, H - 60), f"Cut {c['cut']}  {t0:5.1f}–{t1:5.1f}s  ({t1 - t0:.1f}s)   {c['title']}", font=fs, fill=(235, 240, 255, 255))
    d.text((18, H - 30), f"♪ {c['music']}", font=fs_small, fill=(190, 205, 235, 255))
    d.text((W - 260, 12), "v8 ANIMATIC / 仮曲・仮画", font=fs_small, fill=(255, 255, 255, 170))
    im.save(path)


def end_card(path):
    im = Image.new("RGB", (W, H), (4, 6, 12))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(SERIF, 54, index=0)
    f2 = ImageFont.truetype(SERIF, 26, index=0)
    t1 = "第一話『空に降る雪』　完"
    w1 = d.textlength(t1, font=f1)
    d.text(((W - w1) / 2, H / 2 - 70), t1, font=f1, fill=(236, 230, 214))
    t2 = "（ここに4人のPC名）"
    w2 = d.textlength(t2, font=f2)
    d.text(((W - w2) / 2, H / 2 + 20), t2, font=f2, fill=(180, 190, 210))
    im.save(path)


clips = []
for c in TL["cuts"]:
    n = fr(c["beat_out"]) - fr(c["beat_in"])
    lab = WORK / f"label_{c['cut']}.png"
    label_png(c, lab)
    out = WORK / f"clip_{c['cut']}.mp4"
    if c["still"]:
        src = STILLS / c["still"]
        flt = (f"[0]scale=2560:1440:flags=lanczos,zoompan=z='1+0.05*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
               f":d={n}:s={W}x{H}:fps={FPS}[v];[v][1]overlay=0:0,format=yuv420p")
    else:
        src = WORK / "endcard.png"
        end_card(src)
        flt = f"[0]scale={W}:{H},fps={FPS},fade=t=in:st=0:d=0.8[v];[v][1]overlay=0:0,format=yuv420p"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(src), "-i", str(lab),
                    "-filter_complex", flt, "-frames:v", str(n), "-r", str(FPS), "-c:v", "libx264", "-crf", "18",
                    "-preset", "veryfast", str(out)], check=True)
    clips.append(out)
    print(f"Cut {c['cut']}: {n} frames")

lst = WORK / "concat.txt"
lst.write_text("".join(f"file '{p}'\n" for p in clips))
total = fr(TL["total_beats"])
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(AUDIO),
                "-vf", f"fade=t=in:st=0:d=1.0,fade=t=out:st={total / FPS - 1.0}:d=1.0", "-frames:v", str(total),
                "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "256k", "-shortest", str(OUT)], check=True)
print("wrote", OUT)
