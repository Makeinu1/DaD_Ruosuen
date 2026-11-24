#!/usr/bin/env python3
"""v15 方式③: Blender guide video -> local Wan 2.2 TI2V-5B restyle (video-to-video by partial denoise).

Only the TI2V-5B model is installed on the VideoStudio PC (no VACE / Fun-Control), so the guide is
VAE-encoded and re-noised to --denoise (0 = keep the guide, 1 = ignore it), then denoised with the
style prompt. Composition and motion come from the guide; texture and light come from the model.
Talks to the local ComfyUI HTTP API (default http://127.0.0.1:8188); does not change any workflow file.

Usage (on the PC, any Python 3):
  python vid2vid.py --video renders/R14_a/R14_guide.mp4 --out renders/R14_a/wan [--frames 121]
                    [--start 0] [--width 960 --height 544] [--denoise 0.55] [--steps 20] [--seed 7]
"""
import argparse, json, shutil, time, urllib.request, uuid
from pathlib import Path

COMFY_ROOT = Path(r'C:\VideoStudio\ComfyUI_windows_portable\ComfyUI')
PROMPT = ('hand-painted animated film background art, gouache and watercolour on paper, visible soft brush '
          'strokes; a vast dark underground cavern at night; a giant pale pearl-white whale with a soft inner '
          'glow swims slowly through the air of the cavern; around and behind it a river of countless tiny '
          'white flower petals drifts like snow, glinting faint gold; a faint cold moonbeam slants down from '
          'above; deep blue-violet night palette, quiet, solemn, beautiful, cinematic, steady camera')
NEGATIVE = ('photorealistic, 3D render, CGI, plastic, video game, text, subtitles, watermark, logo, '
            'oversaturated, overexposed, blurry, jpeg artifacts, extra fins, deformed whale, two whales, '
            'flickering, camera shake, people, buildings')


def graph(video_name, a):
    return {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'wan2.2_ti2v_5B_fp16.safetensors', 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': 'umt5_xxl_fp8_e4m3fn_scaled.safetensors', 'type': 'wan', 'device': 'default'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'wan2.2_vae.safetensors'}},
        '4': {'class_type': 'CLIPTextEncode', 'inputs': {'text': a.prompt, 'clip': ['2', 0]}},
        '5': {'class_type': 'CLIPTextEncode', 'inputs': {'text': a.negative, 'clip': ['2', 0]}},
        '6': {'class_type': 'ModelSamplingSD3', 'inputs': {'shift': a.shift, 'model': ['1', 0]}},
        '20': {'class_type': 'LoadVideo', 'inputs': {'file': video_name}},
        '21': {'class_type': 'GetVideoComponents', 'inputs': {'video': ['20', 0]}},
        '22': {'class_type': 'ImageFromBatch', 'inputs': {'image': ['21', 0], 'batch_index': a.start, 'length': a.frames}},
        '23': {'class_type': 'ImageScale', 'inputs': {'image': ['22', 0], 'upscale_method': 'lanczos', 'width': a.width, 'height': a.height, 'crop': 'center'}},
        '24': {'class_type': 'VAEEncode', 'inputs': {'pixels': ['23', 0], 'vae': ['3', 0]}},
        '8': {'class_type': 'KSampler', 'inputs': {'model': ['6', 0], 'seed': a.seed, 'steps': a.steps, 'cfg': a.cfg,
                                                  'sampler_name': 'uni_pc', 'scheduler': 'simple', 'positive': ['4', 0],
                                                  'negative': ['5', 0], 'latent_image': ['24', 0], 'denoise': a.denoise}},
        '9': {'class_type': 'VAEDecode', 'inputs': {'samples': ['8', 0], 'vae': ['3', 0]}},
        '10': {'class_type': 'CreateVideo', 'inputs': {'images': ['9', 0], 'fps': 24}},
        '11': {'class_type': 'SaveVideo', 'inputs': {'video': ['10', 0], 'filename_prefix': f'ruosuen/{a.tag}', 'format': 'auto', 'codec': 'auto'}},
    }


def call(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=60))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--comfy', default='http://127.0.0.1:8188')
    ap.add_argument('--frames', type=int, default=121)      # 4n+1; 121 = 5.0 s at 24 fps
    ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--width', type=int, default=960)
    ap.add_argument('--height', type=int, default=544)
    ap.add_argument('--denoise', type=float, default=0.55)
    ap.add_argument('--steps', type=int, default=20)
    ap.add_argument('--cfg', type=float, default=5.0)
    ap.add_argument('--shift', type=float, default=8.0)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--prompt', default=PROMPT)
    ap.add_argument('--negative', default=NEGATIVE)
    ap.add_argument('--tag', default='')
    a = ap.parse_args()
    a.tag = a.tag or f'{a.video.stem}_wan_d{int(a.denoise * 100)}_s{a.seed}'
    name = f'ruosuen_{a.video.name}'
    shutil.copy2(a.video, COMFY_ROOT / 'input' / name)
    cid = uuid.uuid4().hex
    r = call(f'{a.comfy}/prompt', {'prompt': graph(name, a), 'client_id': cid})
    pid = r['prompt_id']; t0 = time.time()
    print('queued', pid, a.tag, flush=True)
    while True:
        time.sleep(10)
        h = call(f'{a.comfy}/history/{pid}')
        if pid in h:
            st = h[pid].get('status', {})
            if st.get('status_str') == 'error' or not st.get('completed', True):
                print(json.dumps(st)[-1500:]); raise SystemExit('ComfyUI error')
            outs = h[pid]['outputs']
            break
        if time.time() - t0 > 3 * 3600:
            raise SystemExit('timeout')
    a.out.mkdir(parents=True, exist_ok=True)
    for node in outs.values():
        for key in ('images', 'videos', 'gifs'):
            for f in node.get(key, []):
                src = COMFY_ROOT / 'output' / f.get('subfolder', '') / f['filename']
                dst = a.out / f'{a.tag}{src.suffix}'
                shutil.copy2(src, dst)
                print('saved', dst, f'{time.time() - t0:.0f}s')
    (a.out / f'{a.tag}.json').write_text(json.dumps({k: (str(v) if isinstance(v, Path) else v) for k, v in vars(a).items()},
                                                   ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
