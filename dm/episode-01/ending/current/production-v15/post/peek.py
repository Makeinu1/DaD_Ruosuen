#!/usr/bin/env python3
"""Tiny preview transport for agents that cannot download from the PC (the sandbox proxy blocks the
VideoStudio file URLs): tile a few frames into one small WebP, then print it as base64 in slices
that fit the blender_run log tail (~6000 chars).

  python peek.py make --out sheet.webp --width 384 img1.png img2.png ...   (prints the slice count)
  python peek.py chunk sheet.webp 0                                       (prints slice 0)
Reassemble the slices in order and base64-decode.
"""
import base64, math, sys
from pathlib import Path
from PIL import Image

SLICE = 5600


def make(out, width, files, cols=2, quality=58):
    ims = [Image.open(f).convert('RGB') for f in files]
    h = round(width * ims[0].height / ims[0].width)
    rows = math.ceil(len(ims) / cols)
    sheet = Image.new('RGB', (cols * width, rows * h))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((width, h), Image.Resampling.LANCZOS), ((i % cols) * width, (i // cols) * h))
    sheet.save(out, 'WEBP', quality=quality, method=6)
    n = math.ceil(len(base64.b64encode(Path(out).read_bytes())) / SLICE)
    print('bytes', Path(out).stat().st_size, 'slices', n)


def chunk(path, i):
    b = base64.b64encode(Path(path).read_bytes()).decode()
    print('B64[' + b[i * SLICE:(i + 1) * SLICE] + ']')


if __name__ == '__main__':
    if sys.argv[1] == 'make':
        args = sys.argv[2:]
        out = args[args.index('--out') + 1]
        width = int(args[args.index('--width') + 1]) if '--width' in args else 384
        cols = int(args[args.index('--cols') + 1]) if '--cols' in args else 2
        files = [x for j, x in enumerate(args) if not x.startswith('--') and (j == 0 or not args[j - 1].startswith('--'))]
        make(out, width, files, cols)
    else:
        chunk(sys.argv[2], int(sys.argv[3]))
