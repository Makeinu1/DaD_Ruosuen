#!/usr/bin/env python3
"""
One-shot Colab L4 GPU runner for Step 5C (8 Additional Cuts -> Complete 16-Cut 90s Storyboard Sheet!):
  1. Provision NVIDIA L4 GPU + Blender 5.0.1
  2. Upload cached /tmp/v7_colab_bundle.tar.gz + render_step5c_extra8_cuts.py
  3. Render 8 x 960x540 Cycles OptiX stills (~65s)
  4. Download all 8 PNGs (using tar+base64 -> fewer requests & faster!)
  5. Build Complete 16-Panel (4x4) 90s Master Storyboard Sheet!
  6. GUARANTEED finally: delete Colab session & runtime!
"""

import base64
import json
import subprocess
import tarfile
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO = Path("/home/antigravity/Makeinu1/DaD_Ruosuen")
V7_DIR = REPO / "dm/episode-01/ending/video-pipeline/v7_blender_cycles"
SCRIPT_PATH = V7_DIR / "scripts/render_step5c_extra8_cuts.py"
OUT_DIR = V7_DIR / "out/step5c_extra8"
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
    tmp_py = Path("/tmp/v7_exec_5c.py")
    tmp_py.write_text(code, encoding="utf-8")
    for attempt in range(6):
        try:
            return extract_stdout(run_mcp(["exec", sess_name, "--file", str(tmp_py)], timeout=timeout))
        except RuntimeError as e:
            if "429" in str(e) and attempt < 5:
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
        print("[5C] Provisioning NVIDIA L4 GPU...")
        rt_txt = extract_stdout(run_mcp([
            "call", "create_runtime", "--args",
            json.dumps({"runtime": {"runtimeSpec": {"variant": "VARIANT_GPU", "accelerator": "L4", "shape": "SHAPE_STANDARD"}}})
        ]))
        rt_name = json.loads(rt_txt)["name"]
        sess_txt = extract_stdout(run_mcp(["call", "create_session", "--args", json.dumps({"parent": rt_name})]))
        sess_name = json.loads(sess_txt)["name"]
        print(f"[5C] Active: {sess_name}")

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

        b64_all = base64.b64encode(BUNDLE_PATH.read_bytes()).decode("ascii")
        chunk_size = 500_000
        n_chunks = (len(b64_all) + chunk_size - 1) // chunk_size
        print(f"[5C] Uploading bundle ({n_chunks} chunks)...")
        for i in range(n_chunks):
            ch = b64_all[i * chunk_size : (i + 1) * chunk_size]
            mode = "w" if i == 0 else "a"
            exec_colab(sess_name, f"with open('/tmp/v7_bundle.b64',{mode!r}) as f: f.write({ch!r})\n")
            time.sleep(0.8)

        script_b64 = base64.b64encode(SCRIPT_PATH.read_bytes()).decode("ascii")
        render_code = f"""
import base64, os, subprocess, tarfile, time
raw = base64.b64decode(open('/tmp/v7_bundle.b64').read())
open('/tmp/v7_bundle.tar.gz', 'wb').write(raw)
with tarfile.open('/tmp/v7_bundle.tar.gz', 'r:gz') as tf:
    tf.extractall('/tmp/v7_work')
open('/tmp/v7_work/render_step5c_extra8_cuts.py','wb').write(base64.b64decode({script_b64!r}))
env = os.environ.copy()
env['V7_WORK_DIR'] = '/tmp/v7_work'
t0 = time.time()
p = subprocess.run(
    ['/tmp/blender/blender', '-b', '--factory-startup', '--python', '/tmp/v7_work/render_step5c_extra8_cuts.py'],
    env=env, capture_output=True, text=True
)
print(f'Exit {{p.returncode}} in {{time.time()-t0:.1f}}s')
for ln in p.stdout.splitlines():
    if any(k in ln for k in ('[GPU]', '[STEP 5C', 'Error', 'Traceback')):
        print(ln)
if p.returncode != 0:
    print(p.stderr[-2500:])
    raise RuntimeError('5C render failed')
# Convert 8 PNGs to high-quality Q93 JPEGs in a single tar (~1.1 MB total!) for ultra-fast download!
from PIL import Image
with tarfile.open('/tmp/v7_5c_out.tar', 'w') as tf:
    for fn in sorted(os.listdir('/tmp/v7_work/out_step5c')):
        if fn.endswith('.png'):
            jp = '/tmp/v7_work/out_step5c/' + fn.replace('.png', '.jpg')
            Image.open('/tmp/v7_work/out_step5c/' + fn).convert('RGB').save(jp, 'JPEG', quality=94, optimize=True)
            tf.add(jp, arcname=os.path.basename(jp))
_b64 = base64.b64encode(open('/tmp/v7_5c_out.tar', 'rb').read()).decode('ascii')
print('TAR_LEN:' + str(len(_b64)))
"""
        print("[5C] Rendering 8 Extra Cuts on NVIDIA L4 GPU...")
        out_r = exec_colab(sess_name, render_code, timeout=290)
        print(out_r)
        total_len = int([ln for ln in out_r.splitlines() if "TAR_LEN:" in ln][-1].split("TAR_LEN:")[1].strip())

        # Download the entire 8-cut tar in ~5-6 fast slices!
        slice_len = 240_000
        parts = []
        n_sl = (total_len + slice_len - 1) // slice_len
        print(f"[5C] Downloading 8-cut archive ({total_len/1e6:.2f} MB b64 in {n_sl} slices)...")
        for idx, off in enumerate(range(0, total_len, slice_len)):
            out = exec_colab(sess_name, f"print('B64S:' + _b64[{off}:{off+slice_len}] + ':B64E')", timeout=90)
            parts.append(out[out.index("B64S:") + 5 : out.index(":B64E")])
            print(f"  slice {idx+1}/{n_sl} ok")
            time.sleep(1.0)

        tar_fp = Path("/tmp/v7_5c_out.tar")
        tar_fp.write_bytes(base64.b64decode("".join(parts)))
        with tarfile.open(tar_fp, "r") as tf:
            tf.extractall(OUT_DIR)
        print("[5C] Extracted:", sorted(p.name for p in OUT_DIR.glob("*.jpg")))

        # Build Complete 16-Panel (4x4) 90-Second Master Storyboard Sheet!
        s5 = V7_DIR / "out/step5_lookdev"
        s5b = V7_DIR / "out/step5b_director_cuts"
        panels16 = [
            (OUT_DIR / "ex01_02s_open_cam_a.jpg",      "01 (02.0s) Opening Stillness (Locked Cam A)"),
            (OUT_DIR / "ex02_08s_p0_flower_macro.jpg", "02 (08.0s) P0 Delicate Star-Lily Macro (58mm)"),
            (s5 / "lookdev_01_shadow_16s.png",         "03 (16.0s) Lake Ripples + 24m Submerged Shadow"),
            (OUT_DIR / "ex03_21s_silent_breach.jpg",   "04 (21.0s) Silent Breach Breaking Mirror Lake"),

            (s5 / "lookdev_02_approach_28s.png",       "05 (25.0s) Close Foreground Approach (Unlit)"),
            (s5b / "dc01_heigei_closeup_28s.png",      "06 (28.5s) Heigei Close-Up (42mm Front-20deg)"),
            (OUT_DIR / "ex04_30s_eye_hold_macro.jpg",  "07 (30.5s) Serene Eye Hold (68mm Glint, 2.5s)"),
            (s5 / "lookdev_03_turnback_33s.png",       "08 (34.0s) Graceful Turn-Back to Moonbeam"),

            (OUT_DIR / "ex05_38s_first_spark.jpg",     "09 (38.5s) First Spark: Snout Touches Moonbeam"),
            (s5 / "lookdev_04_ignite_41s.png",         "10 (41.0s) Phase 1 Ignition Wave + Bloom Start"),
            (s5b / "dc02_ground_bloom_43s.png",        "11 (43.5s) Mirror-Lake Symmetry & Seed Lift"),
            (OUT_DIR / "ex06_45s_petal_liftoff.jpg",   "12 (45.5s) Title Beat: Golden Snow Rising Up"),

            (s5b / "dc03_aerial_track_50s.png",        "13 (51.0s) Gravity Release: Airborne Tracking"),
            (s5b / "dc04_panorama_sym_59s.png",        "14 (59.0s) 18mm 450m Cavern Grand Panorama"),
            (OUT_DIR / "ex07_73s_exit_c_r1.jpg",       "15 (73.0s) Canon Exit C Behind R1 Headland"),
            (OUT_DIR / "ex08_86s_aftermath_cam_a.jpg", "16 (86.0s) Dreamlike Aftermath (Locked Cam A)"),
        ]

        tw, th, pad, hdr_h = 480, 270, 24, 48
        sheet = Image.new("RGB", (tw * 4, hdr_h + (th + pad) * 4), (8, 12, 20))
        draw = ImageDraw.Draw(sheet)
        try:
            f_hdr = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            f_lbl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        except Exception:
            f_hdr = ImageFont.load_default(); f_lbl = f_hdr

        draw.rectangle([0, 0, tw * 4, hdr_h], fill=(12, 18, 30))
        draw.text((16, 13), "EP01 ENDING \"SNOW FALLING TO THE SKY\" — COMPLETE 16-CUT 90s COLOR & CAMERA SCRIPT (CYCLES GPU)", fill=(175, 220, 255), font=f_hdr)

        for idx, (fp, lbl) in enumerate(panels16):
            im = Image.open(fp).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
            c, r = idx % 4, idx // 4
            x0, y0 = c * tw, hdr_h + r * (th + pad)
            draw.rectangle([x0, y0, x0 + tw, y0 + pad], fill=(16, 24, 38))
            draw.text((x0 + 8, y0 + 5), lbl, fill=(230, 240, 255), font=f_lbl)
            sheet.paste(im, (x0, y0 + pad))

        sheet16_fp = V7_DIR / "out/v7_master_16cut_90s_sheet.png"
        sheet.save(sheet16_fp, optimize=True)
        print(f"[SHEET 16] Saved {sheet16_fp} ({sheet16_fp.stat().st_size/1024:.1f} KB)")

        # Also save 4x2 sheet of ONLY the 8 new cuts for crisp inspection
        sheet8 = Image.new("RGB", (tw * 4, hdr_h + (th + pad) * 2), (8, 12, 20))
        d8 = ImageDraw.Draw(sheet8)
        d8.rectangle([0, 0, tw * 4, hdr_h], fill=(12, 18, 30))
        d8.text((16, 13), "STEP 5C — 8 NEWLY ADDED CUTS (02s / 08s / 21s / 30.5s / 38.5s / 45.5s / 73s / 86s)", fill=(255, 225, 165), font=f_hdr)
        new_only = [p for p in panels16 if p[0].parent == OUT_DIR]
        for idx, (fp, lbl) in enumerate(new_only):
            im = Image.open(fp).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
            c, r = idx % 4, idx // 4
            x0, y0 = c * tw, hdr_h + r * (th + pad)
            d8.rectangle([x0, y0, x0 + tw, y0 + pad], fill=(16, 24, 38))
            d8.text((x0 + 8, y0 + 5), lbl, fill=(230, 240, 255), font=f_lbl)
            sheet8.paste(im, (x0, y0 + pad))
        sheet8_fp = OUT_DIR / "v7_step5c_new8_sheet.png"
        sheet8.save(sheet8_fp, optimize=True)
        print(f"[SHEET 8 NEW] Saved {sheet8_fp} ({sheet8_fp.stat().st_size/1024:.1f} KB)")

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
