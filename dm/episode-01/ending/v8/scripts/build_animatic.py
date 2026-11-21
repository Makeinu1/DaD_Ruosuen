"""Build an animatic from stills on a timeline JSON + temp score.

Usage: python3 build_animatic.py STILLS_DIR AUDIO_WAV OUT_MP4 [TIMELINE_JSON]
Default timeline: ../v8_timeline.json. A cut with "overlay": "petal" gets one falling petal,
"dark" (0-1) darkens and vignettes the still, and "card" (text) renders a placeholder card instead of a still.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
TL = json.loads(Path(sys.argv[4] if len(sys.argv) > 4 else HERE.parent / "v8_timeline.json").read_text())
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
    d.text((W - 300, 12), f"{TL['version']} ANIMATIC / 仮曲・仮画", font=fs_small, fill=(255, 255, 255, 170))
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


def petal_png(path):
    im = Image.new("RGBA", (40, 26), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([4, 6, 36, 20], fill=(250, 246, 236, 235))
    d.ellipse([6, 10, 12, 16], fill=(255, 214, 140, 255))
    im.filter(ImageFilter.GaussianBlur(0.8)).save(path)


def text_card(text, path):
    im = Image.new("RGB", (W, H), (3, 5, 10))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(SANS, 34, index=0)
    lines = text.split("\n")
    y = H / 2 - 30 * len(lines)
    for i, line in enumerate(lines):
        w = d.textlength(line, font=f)
        d.text(((W - w) / 2, y), line, font=f, fill=(150, 165, 190) if i == 0 else (215, 222, 236))
        y += 56
    im.save(path)


clips = []
for c in TL["cuts"]:
    n = fr(c["beat_out"]) - fr(c["beat_in"])
    lab = WORK / f"label_{c['cut']}.png"
    label_png(c, lab)
    out = WORK / f"clip_{c['cut']}.mp4"
    if c.get("card"):
        src = WORK / f"card_{c['cut']}.png"
        text_card(c["card"], src)
        flt = f"[0]scale={W}:{H},fps={FPS}[v];[v][1]overlay=0:0,format=yuv420p"
    elif c["still"]:
        src = STILLS / c["still"]
        flt = (f"[0]scale=2560:1440:flags=lanczos,zoompan=z='1+0.05*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
               f":d={n}:s={W}x{H}:fps={FPS}[v];[v][1]overlay=0:0,format=yuv420p")
        if c.get("dark"):
            k = c["dark"]
            flt = flt.replace("[v];", f",eq=gamma={1 - 0.45 * k:.3f}:saturation={1 - 0.2 * k:.3f},vignette=angle={0.35 + 0.9 * k:.3f}[v];", 1)
        if c.get("overlay") == "petal":
            pet = WORK / "petal.png"
            petal_png(pet)
            flt = flt.replace(",format=yuv420p", "[l];[2]format=rgba[p];[l][p]overlay=x='W*0.52+34*sin(t*1.5)':y='if(lt(t,3.2),-60,-40+(t-3.2)*120)',format=yuv420p")
    else:
        src = WORK / "endcard.png"
        end_card(src)
        flt = f"[0]scale={W}:{H},fps={FPS},fade=t=in:st=0:d=0.8[v];[v][1]overlay=0:0,format=yuv420p"
    extra = ["-loop", "1", "-i", str(WORK / "petal.png")] if c.get("overlay") == "petal" else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(src), "-loop", "1", "-i", str(lab), *extra,
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
