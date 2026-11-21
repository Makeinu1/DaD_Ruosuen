#!/usr/bin/env python3
"""
One-shot Colab L4 GPU runner for Step 5B (4 Director's Cut Hero Camera Proof Stills):
  1. Provision NVIDIA L4 GPU + Blender 5.0.1
  2. Upload cached /tmp/v7_colab_bundle.tar.gz + render_step5b_director_cuts.py
  3. Render 4 x 960x540 Cycles OptiX stills (~35s)
  4. Download all 4 PNGs + build 2x2 comparison sheet
  5. GUARANTEED finally: delete Colab session & runtime!
"""

import base64
import json
import subprocess
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO = Path("/home/antigravity/Makeinu1/DaD_Ruosuen")
V7_DIR = REPO / "dm/episode-01/ending/video-pipeline/v7_blender_cycles"
SCRIPT_PATH = V7_DIR / "scripts/render_step5b_director_cuts.py"
OUT_DIR = V7_DIR / "out/step5b_director_cuts"
OUT_DIR.mkdir(parents=True, exist_ok=True)
BUNDLE_PATH = Path("/tmp/v7_colab_bundle.tar.gz")
COLAB_MCP = str(Path.home() / ".local/bin/colab-mcp")


def run_mcp(args, timeout=300):
    res = subprocess.run([COLAB_MCP] + args, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"colab-mcp failed ({res.returncode}):\n{res.stdout}\n{res.stderr}")
    return res.stdout


def extract_stdout(raw_out: str) -> str:
    try:
        data = json.loads(raw_out)
        if isinstance(data, dict) and "content" in data:
            inner = "\n".join(c.get("text", "") for c in data["content"] if isinstance(c, dict))
            try:
                inner_d = json.loads(inner)
                if isinstance(inner_d, dict) and ("stdout" in inner_d or "stderr" in inner_d):
                    return inner_d.get("stdout", "")
            except Exception:
                pass
            return inner
    except Exception:
        pass
    return raw_out


def exec_colab(sess_name: str, code: str, timeout: int = 295) -> str:
    tmp_py = Path("/tmp/v7_exec_5b.py")
    tmp_py.write_text(code, encoding="utf-8")
    for attempt in range(5):
        try:
            return extract_stdout(run_mcp(["exec", sess_name, "--file", str(tmp_py)], timeout=timeout))
        except RuntimeError as e:
            if "429" in str(e) and attempt < 4:
                wait_s = 15 * (attempt + 1)
                print(f"  [429] waiting {wait_s}s...")
                time.sleep(wait_s)
            else:
                raise


def main():
    if not BUNDLE_PATH.exists():
        subprocess.run(["python3", str(V7_DIR / "scripts/run_step5_colab.py"), "pack"], check=True)

    rt_name, sess_name = None, None
    try:
        print("[5B] Provisioning NVIDIA L4 GPU...")
        rt_txt = extract_stdout(run_mcp([
            "call", "create_runtime", "--args",
            json.dumps({"runtime": {"runtimeSpec": {"variant": "VARIANT_GPU", "accelerator": "L4", "shape": "SHAPE_STANDARD"}}})
        ]))
        rt_name = json.loads(rt_txt)["name"]
        sess_txt = extract_stdout(run_mcp(["call", "create_session", "--args", json.dumps({"parent": rt_name})]))
        sess_name = json.loads(sess_txt)["name"]
        print(f"[5B] Active: {sess_name}")

        # Install Blender 5.0.1
        install_code = r"""
import os, subprocess
print(subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader']).decode().strip())
os.makedirs('/tmp/v7_work', exist_ok=True)
if not os.path.exists('/tmp/blender/blender'):
    u = 'https://download.blender.org/release/Blender5.0/blender-5.0.1-linux-x64.tar.xz'
    subprocess.run(['curl', '-fSL', u, '-o', '/tmp/blender.tar.xz'], check=True)
    os.makedirs('/tmp/blender', exist_ok=True)
    subprocess.run(['tar', '-xf', '/tmp/blender.tar.xz', '-C', '/tmp/blender', '--strip-components=1'], check=True)
    os.remove('/tmp/blender.tar.xz')
print(subprocess.check_output(['/tmp/blender/blender', '--version']).decode().splitlines()[0])
"""
        print(exec_colab(sess_name, install_code, timeout=280).strip())

        # Upload asset bundle in 500 KB chunks
        b64_all = base64.b64encode(BUNDLE_PATH.read_bytes()).decode("ascii")
        chunk_size = 500_000
        n_chunks = (len(b64_all) + chunk_size - 1) // chunk_size
        print(f"[5B] Uploading bundle ({n_chunks} chunks)...")
        for i in range(n_chunks):
            ch = b64_all[i * chunk_size : (i + 1) * chunk_size]
            mode = "w" if i == 0 else "a"
            exec_colab(sess_name, f"with open('/tmp/v7_bundle.b64',{mode!r}) as f: f.write({ch!r})\n")
            time.sleep(0.8)

        # Extract + push 5B script + render all 4 stills in ONE call!
        script_b64 = base64.b64encode(SCRIPT_PATH.read_bytes()).decode("ascii")
        render_code = f"""
import base64, os, subprocess, tarfile, time
raw = base64.b64decode(open('/tmp/v7_bundle.b64').read())
open('/tmp/v7_bundle.tar.gz', 'wb').write(raw)
with tarfile.open('/tmp/v7_bundle.tar.gz', 'r:gz') as tf:
    tf.extractall('/tmp/v7_work')
open('/tmp/v7_work/render_step5b_director_cuts.py','wb').write(base64.b64decode({script_b64!r}))
env = os.environ.copy()
env['V7_WORK_DIR'] = '/tmp/v7_work'
t0 = time.time()
p = subprocess.run(
    ['/tmp/blender/blender', '-b', '--factory-startup', '--python', '/tmp/v7_work/render_step5b_director_cuts.py'],
    env=env, capture_output=True, text=True
)
print(f'Exit {{p.returncode}} in {{time.time()-t0:.1f}}s')
for ln in p.stdout.splitlines():
    if any(k in ln for k in ('[GPU]', '[STEP 5B', 'Error', 'Traceback')):
        print(ln)
if p.returncode != 0:
    print(p.stderr[-2500:])
    raise RuntimeError('5B render failed')
"""
        print("[5B] Rendering 4 Director's Cut Hero Camera Stills on NVIDIA L4...")
        print(exec_colab(sess_name, render_code, timeout=290))

        slugs = [
            ("dc01_heigei_closeup_28s.png", "Cut 4 (28.5s) 50mm Heigei Close-Up: Front-20deg Snout & Serene Eye"),
            ("dc02_ground_bloom_43s.png",   "Cut 6B (43.5s) Z=0.45m Ground-Skimming Bloom + Mirror Symmetry"),
            ("dc03_aerial_track_50s.png",   "Cut 7A (50.0s) Gravity Release: Airborne Whale Tracking + Golden Snow"),
            ("dc04_panorama_sym_59s.png",   "Cut 7B (59.0s) 18mm Grand Cavern Panorama + Mirror Symmetry"),
        ]
        slice_len = 240_000
        for fn, _ in slugs:
            txt = exec_colab(sess_name, f"import base64\n_b64=base64.b64encode(open('/tmp/v7_work/out_step5b/{fn}','rb').read()).decode('ascii')\nprint('LEN:'+str(len(_b64)))", timeout=60)
            total_len = int([ln for ln in txt.splitlines() if "LEN:" in ln][-1].split("LEN:")[1].strip())
            parts = []
            for off in range(0, total_len, slice_len):
                out = exec_colab(sess_name, f"print('B64S:' + _b64[{off}:{off+slice_len}] + ':B64E')", timeout=90)
                parts.append(out[out.index("B64S:") + 5 : out.index(":B64E")])
                time.sleep(0.8)
            dst = OUT_DIR / fn
            dst.write_bytes(base64.b64decode("".join(parts)))
            print(f"[DOWNLOAD] {fn} ({dst.stat().st_size/1024:.1f} KB)")

        # Build 2x2 Comparison Sheet (1920x1140)
        tw, th, pad = 960, 540, 32
        sheet = Image.new("RGB", (tw * 2, (th + pad) * 2), (10, 14, 22))
        draw = ImageDraw.Draw(sheet)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except Exception:
            font = ImageFont.load_default()
        for idx, (fn, lbl) in enumerate(slugs):
            im = Image.open(OUT_DIR / fn).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
            c, r = idx % 2, idx // 2
            x0, y0 = c * tw, r * (th + pad)
            draw.rectangle([x0, y0, x0 + tw, y0 + pad], fill=(16, 22, 34))
            draw.text((x0 + 12, y0 + 7), lbl, fill=(230, 240, 255), font=font)
            sheet.paste(im, (x0, y0 + pad))
        sheet_fp = OUT_DIR / "v7_step5b_director_cuts_4sheet.png"
        sheet.save(sheet_fp)
        print(f"[SHEET] Saved {sheet_fp}")
    finally:
        if sess_name:
            try:
                run_mcp(["call", "delete_session", "--args", json.dumps({"name": sess_name})])
                print(f"[CLEANUP] Deleted session {sess_name}")
            except Exception as e:
                print(f"[CLEANUP] session note: {e}")
        if rt_name:
            try:
                run_mcp(["delete-runtime", rt_name])
                print(f"[CLEANUP] Deleted runtime {rt_name}")
            except Exception as e:
                print(f"[CLEANUP] runtime note: {e}")
        print("[CLEANUP] Remaining runtimes:", extract_stdout(run_mcp(["runtimes"])).strip())


if __name__ == "__main__":
    main()
