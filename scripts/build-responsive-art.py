"""Generate responsive derivatives of the currently published WebP artwork.
Never replace originals; use the actual published Markdown and film markup.
"""
from pathlib import Path
import json
import re
from PIL import Image

sources = [
    Path("index.html"),
    Path("docs/01_プレイヤー向け世界観.md"),
    Path("docs/04_自由迷宮都市と組織.md"),
    Path("adventures/次の冒険.md"),
    Path("adventures/最初の冒険.md"),
]
names = set()
for p in sources:
    names.update(re.findall(r"(?:\.\./)?assets/([a-z0-9-]+\.webp)", p.read_text(encoding="utf-8"), re.I))
out = Path("assets/responsive")
out.mkdir(exist_ok=True)
manifest = {}
for name in sorted(names):
    src = Path("assets") / name
    with Image.open(src) as im:
        w, h = im.size
        manifest[name] = [w, h]
        for width in (800, 1200):
            if width >= w:
                continue
            target = out / f"{src.stem}-{width}.webp"
            resized = im.resize((width, round(h*width/w)), Image.Resampling.LANCZOS)
            resized.save(target, format="WEBP", quality=82, method=6)
            with Image.open(target) as check:
                assert check.width == width and check.height == round(h*width/w)
            print(f"{target}: {target.stat().st_size} / {src.stat().st_size} bytes")
(out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
