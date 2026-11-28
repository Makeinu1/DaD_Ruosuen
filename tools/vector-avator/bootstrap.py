#!/usr/bin/env python3
"""Prepare an isolated, pinned vector-avator checkout for Bell and Tucker."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
URL = "https://github.com/grmchn/vector-avator.git"
REV = "7357ccae4271fed46482a63c87c480457b9afd61"
SOURCE_DIR = ROOT / "world/npcs/art/avatar-fronts"
MANIFEST = Path(__file__).with_name("approved-fronts.json")

CHARACTERS = {
    "bell": {
        "name": "ベル",
        "notes": """# ベル — アニメーション用補足（試作）
2026-11-28作者指定の個別Aポーズを正本とする。新規の髪型・人間的な顔にしない。共通2〜2.5頭身制限を適用しない。丸い頬、短い首、丸みのある胴、露出した兎の足先、垂れ耳と自然な頭頂の体毛を維持する。
- 小柄で丸みのある女性の兎人。象牙色の毛、茶色がかった長い耳、琥珀色の瞳。
- 青緑の配達員ジャケット、山吹色のスカーフ、茶色の短いズボン、配達鞄。
- タッカーより明確に小柄なシルエットを維持。頭身の数値は原画を見て判断し、正本の設定としない。
- 時計を気にする慌ただしさと親しみやすさ。待機は小さく軽快、耳は頭部に遅れて揺れる。
- 懐中時計はタッカーと同型。腰に時計本体と鎖を明示し、後で手に持てる独立部品として扱う。省略しない。
- 斜め掛け鞄は体と腕の重なりに注意。表情は通常・笑顔・驚き・困りの差を明瞭に。
- ベクター化用のフラットな色面に簡略化してよいが、元の衣装・色・体格を優先する。
""",
        "acting": {"status": "draft", "gestureScale": 1.15, "tempo": 1.15},
        "persona": {"status": "draft", "firstPerson": "私", "tone": "親しみのある敬語。個人の事情から話す。"},
    },
    "tucker": {
        "name": "タッカー",
        "notes": """# タッカー — アニメーション用補足（試作）
2026-11-28作者指定の個別Aポーズを正本とする。成熟した細身の狐人。人間の長い五指や子狐のような大きすぎる頭・丸い手は避け、親指＋短い三指の手袋を維持する。
- 長身で細身の男性の狐人。赤褐色の毛、生成りの口元と胸元、狐らしい鼻先、豊かな尾。
- 葡萄酒色のロングコート、ベスト、革長靴、革鞄、ベルと同型の懐中時計。帳簿はAポーズに描かない。
- 共通スタイルの2〜2.5頭身制限を適用しない。承認画の細身・長身の相対比率を優先し、ベルと並んだ時の差を維持する。数値は原画レビューで決める。
- 動きは余裕があり、ゆっくりした重心移動、片手の説明、短いうなずき。尾は体と遅れて揺れる。
- コートの裾・襟・ベストを大きい色面で整理し、脚・腕・尾の前後関係と隠れる領域を補完する。
- 懐中時計と鎖は正面Aポーズの腰に明示する。別部品として後で手に持てるようにする。帳簿は不要。
- ベクター化用に簡略化してよいが、マスコット化でベルと同じ体格にしない。
""",
        "acting": {"status": "draft", "gestureScale": 0.8, "tempo": 0.85},
        "persona": {"status": "draft", "firstPerson": "俺", "tone": "軽口と皮肉。商談では丁寧な敬語。"},
    },
}


def run(args, cwd=None, capture=False):
    return subprocess.run([str(a) for a in args], cwd=cwd, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def command(name):
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"Required command not found: {name}")
    return path


def put(path, value):
    data = value.encode("utf-8") if isinstance(value, str) else value
    if path.exists():
        if path.read_bytes() != data:
            raise SystemExit(f"Refusing to overwrite existing edited file: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, default=ROOT.parent / "vector-avator-ruosuen")
    args = parser.parse_args()
    engine = args.engine.resolve()
    if engine == ROOT or ROOT in engine.parents:
        raise SystemExit("Use a separate checkout outside DaD_Ruosuen.")
    parser_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for a in parser_manifest["assets"]:
        src = SOURCE_DIR / a["path"]
        if not src.is_file() or src.stat().st_size != a["bytes"] or hashlib.sha256(src.read_bytes()).hexdigest() != a["sha256"]:
            raise SystemExit(f"Missing or mismatched approved original: {src}")
    git, node, npm = map(command, ("git", "node", "npm"))
    if not run([node, "--version"], capture=True).strip().startswith("v22."):
        raise SystemExit("Upstream requires Node 22.")
    if not engine.exists():
        run([git, "clone", "--no-checkout", URL, engine])
        run([git, "checkout", "--detach", REV], engine)
    else:
        origin = run([git, "remote", "get-url", "origin"], engine, True).strip()
        head = run([git, "rev-parse", "HEAD"], engine, True).strip()
        if origin != URL or head != REV:
            raise SystemExit("Existing engine has a different origin or revision; use a fresh path.")
    run([npm, "ci"], engine)
    run([npm, "test"], engine)
    run([npm, "run", "build"], engine)
    venv = engine / ".venv"
    run([sys.executable, "-m", "venv", venv], engine)
    py = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    run([py, "-m", "pip", "install", "-r", "requirements.txt"], engine)
    run([npm, "exec", "--", "playwright", "install", "chromium"], engine)
    for cid, spec in CHARACTERS.items():
        original = engine / f"inputs/ruosuen/{cid}-front.png"
        put(original, (SOURCE_DIR / f"{cid}-front.png").read_bytes())
        rel = original.relative_to(engine).as_posix()
        # Letterbox, never crop or distort the approved full-body silhouette.
        front = engine / f"public/characters/{cid}/vector/ref/front.png"
        front.parent.mkdir(parents=True, exist_ok=True)
        if not front.exists():
            run([py, "-c", "from PIL import Image,ImageOps; import sys; im=Image.open(sys.argv[1]).convert('RGB'); fit=ImageOps.contain(im,(1024,1536)); canvas=Image.new('RGB',(1024,1536),im.getpixel((0,0))); canvas.paste(fit,((1024-fit.width)//2,(1536-fit.height)//2)); canvas.save(sys.argv[2])", original, front])
        put(engine / f"tools/vector/sheets/characters/{cid}.md", spec["notes"])
        put(engine / f"tools/vector/sheets/characters/{cid}.json", json_text({
            "id": cid, "name": spec["name"], "notes": f"characters/{cid}.md",
            "refs": {"original": [rel]},
            "roles": {rel: f"Approved individual A-pose of {spec['name']}. Preserve proportions, silhouette, clothing, satchel and pocket watch; do not restyle the identity."}
        }))
        # Stage rather than advertise incomplete characters in the viewer.
        put(engine / f"var/vector/{cid}/pending-character.json", json_text({
            "schemaVersion": 1, "id": cid, "label": spec["name"],
            "vector": {"url": f"characters/{cid}/vector/vector.json"},
            "rig": {"turn": "parallax30", "hands": {"type": "beast"}}, "persona": spec["persona"], "acting": spec["acting"]
        }))
    print(f"Setup complete: {engine}")
    print("Sample engine tests/build passed; custom avatars NOT yet generated.")
    print("External commands still needed for full creation: codex, claude (Fable 5.2), resvg, ffmpeg.")
    print("Follow the project README and upstream SKILL.md; review generated art before adoption.")


if __name__ == "__main__":
    main()
