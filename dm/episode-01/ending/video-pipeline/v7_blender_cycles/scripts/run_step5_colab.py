#!/usr/bin/env python3
"""
Step 5 Google Colab L4 GPU Orchestrator.
Subcommands:
  pack    - Build compact /tmp/v7_colab_bundle.tar.gz (~2.3 MB)
  setup   - Provision Colab L4 GPU runtime + Jupyter session + install Blender 4.3/5.0 + upload bundle
  render  - Upload latest render_step5_lookdev_cycles.py, run Cycles GPU render, download 5 PNGs
  cleanup - Delete Colab session & runtime and verify 0 runtimes remain
"""

import base64
import json
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from PIL import Image

REPO = Path("/home/antigravity/Makeinu1/DaD_Ruosuen")
V7_DIR = REPO / "dm/episode-01/ending/video-pipeline/v7_blender_cycles"
SCRIPT_PATH = V7_DIR / "scripts/render_step5_lookdev_cycles.py"
OUT_DIR = V7_DIR / "out/step5_lookdev"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BUNDLE_PATH = Path("/tmp/v7_colab_bundle.tar.gz")
STATE_PATH = Path("/tmp/v7_colab_session.json")
COLAB_MCP = str(Path.home() / ".local/bin/colab-mcp")


def run_mcp(args, timeout=300):
    cmd = [COLAB_MCP] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"colab-mcp failed ({res.returncode}):\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return res.stdout


def extract_mcp_text(raw_out: str) -> str:
    try:
        data = json.loads(raw_out)
        if isinstance(data, dict) and "content" in data and isinstance(data["content"], list):
            parts = [c.get("text", "") for c in data["content"] if isinstance(c, dict)]
            inner = "\n".join(parts)
            try:
                inner_d = json.loads(inner)
                if isinstance(inner_d, dict) and ("stdout" in inner_d or "stderr" in inner_d):
                    out = inner_d.get("stdout", "")
                    if inner_d.get("outputTruncated"):
                        out += "\n[WARNING: outputTruncated=True]"
                    return out
            except Exception:
                pass
            return inner
    except Exception:
        pass
    return raw_out


def exec_colab(session_name: str, code: str, timeout: int = 295) -> str:
    tmp_py = Path("/tmp/v7_exec_tmp.py")
    tmp_py.write_text(code, encoding="utf-8")
    for attempt in range(5):
        try:
            raw = run_mcp(["exec", session_name, "--file", str(tmp_py)], timeout=timeout)
            return extract_mcp_text(raw)
        except RuntimeError as e:
            if "429" in str(e) and attempt < 4:
                wait_s = 15 * (attempt + 1)
                print(f"  [429 rate-limit] waiting {wait_s}s before retry {attempt+2}/5...")
                time.sleep(wait_s)
            else:
                raise


def cmd_pack():
    stage = Path("/tmp/v7_bundle_stage")
    if stage.exists():
        import shutil
        shutil.rmtree(stage)
    (stage / "assets").mkdir(parents=True)
    (stage / "textures").mkdir(parents=True)

    # Copy script
    (stage / "render_step5_lookdev_cycles.py").write_bytes(SCRIPT_PATH.read_bytes())

    # Copy GLBs
    glbs = [
        REPO / "dm/episode-01/ending/video-pipeline/v2/assets/processed/wh01_v20_hero.glb",
        REPO / "dm/episode-01/ending/video-pipeline/v6_anime3d/assets/fl01_open.glb",
        REPO / "dm/episode-01/ending/video-pipeline/v6_anime3d/assets/fl01_bud.glb",
        REPO / "dm/episode-01/ending/video-pipeline/v6_anime3d/assets/sakura_petal_3d.glb",
    ]
    for g in glbs:
        (stage / "assets" / g.name).write_bytes(g.read_bytes())

    # Convert RGB textures to high-quality JPEG, keep normal & alpha PNGs
    jpg_maps = [
        (REPO / "dm/episode-01/ending/video-pipeline/v6_anime3d/textures/anime_cliff_albedo.png", "anime_cliff_albedo.jpg"),
        (REPO / "dm/episode-01/ending/video-pipeline/v5_cycles/textures/whale_skin_albedo.png", "whale_skin_albedo.jpg"),
        (REPO / "dm/episode-01/ending/video-pipeline/v5_cycles/textures/moon_sky.png", "moon_sky.jpg"),
    ]
    for src, dst_name in jpg_maps:
        im = Image.open(src).convert("RGB")
        im.save(stage / "textures" / dst_name, "JPEG", quality=92, optimize=True)

    png_maps = [
        (REPO / "dm/episode-01/ending/video-pipeline/v6_anime3d/textures/anime_cliff_normal.png", "anime_cliff_normal.png", "RGB", 512),
        (REPO / "dm/episode-01/ending/video-pipeline/v5_cycles/textures/petal_rgba.png", "petal_rgba.png", "RGBA", 512),
    ]
    for src, dst_name, mode, max_dim in png_maps:
        im = Image.open(src).convert(mode)
        if max(im.size) > max_dim:
            im = im.resize((max_dim, max_dim), Image.Resampling.LANCZOS)
        im.save(stage / "textures" / dst_name, "PNG", optimize=True)

    with tarfile.open(BUNDLE_PATH, "w:gz") as tf:
        for p in sorted(stage.rglob("*")):
            if p.is_file():
                tf.add(p, arcname=str(p.relative_to(stage)))

    sz_mb = BUNDLE_PATH.stat().st_size / (1024 * 1024)
    print(f"[PACK] Built {BUNDLE_PATH} ({sz_mb:.2f} MB)")


def cmd_setup():
    if not BUNDLE_PATH.exists():
        cmd_pack()

    # 1. Create L4 GPU runtime
    print("[COLAB] Provisioning NVIDIA L4 GPU runtime...")
    raw_rt = run_mcp([
        "call", "create_runtime", "--args",
        json.dumps({"runtime": {"runtimeSpec": {"variant": "VARIANT_GPU", "accelerator": "L4", "shape": "SHAPE_STANDARD"}}})
    ])
    txt_rt = extract_mcp_text(raw_rt)
    print("[COLAB] create_runtime response:", txt_rt[:500])
    rt_json = json.loads(txt_rt)
    rt_name = rt_json.get("name") or rt_json.get("runtime", {}).get("name")
    if not rt_name:
        rts = json.loads(extract_mcp_text(run_mcp(["runtimes"])))
        rt_list = rts.get("runtimes", [])
        rt_name = rt_list[0]["name"]
    print(f"[COLAB] Active runtime: {rt_name}")

    # 2. Create Jupyter session
    raw_sess = run_mcp(["call", "create_session", "--args", json.dumps({"parent": rt_name})])
    txt_sess = extract_mcp_text(raw_sess)
    print("[COLAB] create_session response:", txt_sess[:500])
    sess_json = json.loads(txt_sess)
    sess_name = sess_json.get("name") or sess_json.get("session", {}).get("name")
    STATE_PATH.write_text(json.dumps({"runtime": rt_name, "session": sess_name}, indent=2))
    print(f"[COLAB] Active session: {sess_name}")

    # 3. Verify nvidia-smi & install standalone Blender 5.0 (fallback 4.3.2)
    print("[COLAB] Checking GPU and installing standalone Blender...")
    install_code = r"""
import os, subprocess
print(subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader']).decode().strip())
os.makedirs('/tmp/v7_work', exist_ok=True)
if not os.path.exists('/tmp/blender/blender'):
    urls = [
        'https://download.blender.org/release/Blender5.0/blender-5.0.1-linux-x64.tar.xz',
        'https://download.blender.org/release/Blender5.0/blender-5.0.0-linux-x64.tar.xz',
        'https://download.blender.org/release/Blender4.3/blender-4.3.2-linux-x64.tar.xz',
    ]
    chosen = None
    for u in urls:
        r = subprocess.run(['curl', '-fsIL', u], capture_output=True)
        if r.returncode == 0:
            chosen = u
            break
    assert chosen, 'No Blender tarball URL reachable!'
    print('Downloading:', chosen)
    subprocess.run(['curl', '-fSL', chosen, '-o', '/tmp/blender.tar.xz'], check=True)
    os.makedirs('/tmp/blender', exist_ok=True)
    subprocess.run(['tar', '-xf', '/tmp/blender.tar.xz', '-C', '/tmp/blender', '--strip-components=1'], check=True)
    os.remove('/tmp/blender.tar.xz')
print(subprocess.check_output(['/tmp/blender/blender', '--version']).decode().splitlines()[0])
"""
    print(exec_colab(sess_name, install_code, timeout=280))


def cmd_upload():
    state = json.loads(STATE_PATH.read_text())
    sess_name = state["session"]
    raw_bytes = BUNDLE_PATH.read_bytes()
    b64_all = base64.b64encode(raw_bytes).decode("ascii")
    chunk_size = 500_000  # ~500 KB per request -> safely under payload & RPM limits!
    n_chunks = (len(b64_all) + chunk_size - 1) // chunk_size
    print(f"[COLAB] Uploading bundle ({len(raw_bytes)/1e6:.2f} MB) in {n_chunks} chunks...")
    for i in range(n_chunks):
        ch = b64_all[i * chunk_size : (i + 1) * chunk_size]
        mode = "w" if i == 0 else "a"
        code = f"with open('/tmp/v7_bundle.b64',{mode!r}) as f: f.write({ch!r})\nprint('chunk {i+1}/{n_chunks} ok')"
        print(" ", exec_colab(sess_name, code).strip())
        time.sleep(1.0)

    extract_code = r"""
import base64, tarfile, os
raw = base64.b64decode(open('/tmp/v7_bundle.b64').read())
open('/tmp/v7_bundle.tar.gz', 'wb').write(raw)
with tarfile.open('/tmp/v7_bundle.tar.gz', 'r:gz') as tf:
    tf.extractall('/tmp/v7_work')
print('Extracted files:', sorted(os.listdir('/tmp/v7_work')), 'assets:', sorted(os.listdir('/tmp/v7_work/assets')), 'textures:', sorted(os.listdir('/tmp/v7_work/textures')))
"""
    print(exec_colab(sess_name, extract_code))


def cmd_render():
    state = json.loads(STATE_PATH.read_text())
    sess_name = state["session"]

    # Always push latest render_step5_lookdev_cycles.py AND run Blender in ONE single execute_code call!
    script_b64 = base64.b64encode(SCRIPT_PATH.read_bytes()).decode("ascii")
    print("[COLAB] Syncing script & running Blender Cycles L4 GPU render (5 x 960x540 @ 48spp)...")
    render_code = f"""
import base64, os, subprocess, time
open('/tmp/v7_work/render_step5_lookdev_cycles.py','wb').write(base64.b64decode({script_b64!r}))
env = os.environ.copy()
env['V7_WORK_DIR'] = '/tmp/v7_work'
t0 = time.time()
p = subprocess.run(
    ['/tmp/blender/blender', '-b', '--factory-startup', '--python', '/tmp/v7_work/render_step5_lookdev_cycles.py'],
    env=env, capture_output=True, text=True
)
print(f'Exit code: {{p.returncode}} in {{time.time()-t0:.1f}}s')
for line in p.stdout.splitlines():
    if any(k in line for k in ('[GPU]', '[FLOWERS]', '[STEP 5', 'Error', 'Traceback')):
        print(line)
if p.returncode != 0:
    print('--- STDERR ---')
    print(p.stderr[-3000:])
    print('--- STDOUT TAIL ---')
    print(p.stdout[-3000:])
    raise RuntimeError('Blender render failed')
"""
    print(exec_colab(sess_name, render_code, timeout=290))

def cmd_download():
    state = json.loads(STATE_PATH.read_text())
    sess_name = state["session"]

    # Download all 5 rendered PNGs safely in 160 KB base64 slices
    slugs = [
        "lookdev_01_shadow_16s.png",
        "lookdev_02_approach_28s.png",
        "lookdev_03_turnback_33s.png",
        "lookdev_04_ignite_41s.png",
        "lookdev_05_climax_56s.png",
    ]
    slice_len = 240_000
    for fn in slugs:
        prep_code = (
            "import base64\n"
            f"_b64 = base64.b64encode(open('/tmp/v7_work/out_step5/{fn}', 'rb').read()).decode('ascii')\n"
            "print(f'LEN:{len(_b64)}')\n"
        )
        txt = exec_colab(sess_name, prep_code, timeout=60)
        total_len = int([ln for ln in txt.splitlines() if "LEN:" in ln][-1].split("LEN:")[1].strip())
        parts = []
        for off in range(0, total_len, slice_len):
            sl_code = f"print('B64S:' + _b64[{off}:{off+slice_len}] + ':B64E')"
            out = exec_colab(sess_name, sl_code, timeout=90)
            if "outputTruncated=True" in out:
                raise RuntimeError(f"Output truncated at slice_len={slice_len}")
            s = out.index("B64S:") + 5
            e = out.index(":B64E")
            parts.append(out[s:e])
            time.sleep(0.8)
        dst = OUT_DIR / fn
        dst.write_bytes(base64.b64decode("".join(parts)))
        print(f"[DOWNLOAD] {dst.name} ({dst.stat().st_size/1024:.1f} KB)")


def cmd_cleanup():
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text())
        try:
            run_mcp(["call", "delete_session", "--args", json.dumps({"name": state["session"]})])
            print(f"[CLEANUP] Deleted session {state['session']}")
        except Exception as e:
            print(f"[CLEANUP] delete_session note: {e}")
        try:
            run_mcp(["delete-runtime", state["runtime"]])
            print(f"[CLEANUP] Deleted runtime {state['runtime']}")
        except Exception as e:
            print(f"[CLEANUP] delete-runtime note: {e}")
        STATE_PATH.unlink(missing_ok=True)
    print("[CLEANUP] Remaining runtimes:", extract_mcp_text(run_mcp(["runtimes"])).strip())


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "pack":
        cmd_pack()
    elif cmd == "setup":
        cmd_setup()
        cmd_upload()
    elif cmd == "upload":
        cmd_upload()
    elif cmd == "render":
        cmd_render()
        cmd_download()
    elif cmd == "download":
        cmd_download()
    elif cmd == "cleanup":
        cmd_cleanup()
    else:
        print("Usage: run_step5_colab.py [pack|setup|upload|render|download|cleanup]")
