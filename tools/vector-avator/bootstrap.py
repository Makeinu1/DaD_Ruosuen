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
SOURCE = ROOT / "world/npcs/art/bell-tucker-character-sheet.webp"
SOURCE_HASH = "1aac09b8d9f152e9caccce471dc4240a14e79363876b34d8213b7d0d05ac3190"

CHARACTERS = {
    "bell": {
        "name": "ベル",
        "notes": """# ベル — アニメーション用補足（試作）
承認済みの共同キャラクターシートのベルだけを対象にする。狐は描かない。
- 小柄で丸みのある女性の兎人。象牙色の毛、茶色がかった長い耳、琥珀色の瞳。
- 青緑の配達員ジャケット、山吹色のスカーフ、茶色の短いズボン、配達鞄。
- タッカーより明確に小柄なシルエットを維持。頭身の数値は原画を見て判断し、正本の設定としない。
- 時計を気にする慌ただしさと親しみやすさ。待機は小さく軽快、耳は頭部に遅れて揺れる。
- 懐中時計はタッカーと同型。正面Aポーズでは手に固定せず、別の小道具として後で演技に追加する。
- 斜め掛け鞄は体と腕の重なりに注意。表情は通常・笑顔・驚き・困りの差を明瞭に。
- ベクター化用のフラットな色面に簡略化してよいが、元の衣装・色・体格を優先する。
""",
        "acting": {"status": "draft", "gestureScale": 1.15, "tempo": 1.15},
        "persona": {"status": "draft", "firstPerson": "私", "tone": "親しみのある敬語。個人の事情から話す。"},
    },
    "tucker": {
        "name": "タッカー",
        "notes": """# タッカー — アニメーション用補足（試作）
承認済みの共同キャラクターシートのタッカーだけを対象にする。兎は描かない。
- 長身で細身の男性の狐人。赤褐色の毛、生成りの口元と胸元、狐らしい鼻先、豊かな尾。
- 葡萄酒色のロングコート、ベスト、革靴、帳簿、ベルと同型の懐中時計。
- 共通スタイルの2〜2.5頭身制限を適用しない。承認画の細身・長身の相対比率を優先し、ベルと並んだ時の差を維持する。数値は原画レビューで決める。
- 動きは余裕があり、ゆっくりした重心移動、片手の説明、短いうなずき。尾は体と遅れて揺れる。
- コートの裾・襟・ベストを大きい色面で整理し、脚・腕・尾の前後関係と隠れる領域を補完する。
- 懐中時計と帳簿は正面Aポーズの手に固定しない。小道具として後で演技に追加する。
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
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_HASH:
        raise SystemExit("Canonical source image hash differs; review the source first.")
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
    original = engine / "inputs/ruosuen/bell-tucker-character-sheet.webp"
    put(original, SOURCE.read_bytes())
    png = original.with_suffix(".png")
    if not png.exists():
        run([py, "-c", "from PIL import Image; import sys; Image.open(sys.argv[1]).convert('RGB').save(sys.argv[2])", original, png])
    # Verify existing PNG too: the shared original must remain pixel-identical.
    run([py, "-c", "from PIL import Image; import sys; a,b=[Image.open(p).convert('RGB') for p in sys.argv[1:]]; assert a.size==b.size and a.tobytes()==b.tobytes()", original, png])
    for cid, spec in CHARACTERS.items():
        rel = png.relative_to(engine).as_posix()
        put(engine / f"tools/vector/sheets/characters/{cid}.md", spec["notes"])
        put(engine / f"tools/vector/sheets/characters/{cid}.json", json_text({
            "id": cid, "name": spec["name"], "notes": f"characters/{cid}.md",
            "refs": {"original": [rel]},
            "roles": {rel: f"Approved joint sheet: use ONLY {spec['name']}; the other figure is not the subject. Preserve outfit and relative silhouette; ignore original pose for the neutral A-pose."}
        }))
        # Stage rather than advertise incomplete characters in the viewer.
        put(engine / f"var/vector/{cid}/pending-character.json", json_text({
            "schemaVersion": 1, "id": cid, "label": spec["name"],
            "vector": {"url": f"characters/{cid}/vector/vector.json"},
            "rig": {"turn": "parallax30"}, "persona": spec["persona"], "acting": spec["acting"]
        }))
    print(f"Setup complete: {engine}")
    print("Sample engine tests/build passed; custom avatars NOT yet generated.")
    print("External commands still needed for full creation: codex, claude (Fable 5.2), resvg, ffmpeg.")
    print("Follow the project README and upstream SKILL.md; review generated art before adoption.")


if __name__ == "__main__":
    main()
