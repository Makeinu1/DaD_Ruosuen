#!/usr/bin/env python3
"""v15 方式③（制御つき）: Blender depth control video -> Wan 2.2 Fun-Control 5B (local ComfyUI).

vid2vid.py re-noises the guide and lets TI2V-5B repaint it; the stronger the repaint, the more the whale
drifts (R14 v15a: d78 flipped the whale). Here the motion is held by a control video instead:
  control  = Blender depth of the previs geometry (render_cut.py --control depth -> <cut>_control_depth.mp4)
  ref      = first frame (start image); default: first frame of the guide video, or --ref <png>
  denoise  = 1.0 (the model paints everything; the depth keeps the whale's place, size and heading)
The petals are NOT in the control video (they would read as depth noise). If the model's snow does not
follow the previs flow, add the Blender petal layer on top afterwards.

Model (author approved 2026-11-24; Comfy-Org/Wan_2.2_ComfyUI_Repackaged):
  models/diffusion_models/wan2.2_fun_control_5B_bf16.safetensors  (+ the existing wan2.2_vae, umt5_xxl_fp8)
Node graph follows Comfy-Org workflow_templates video_wan2_2_5B_fun_control.json (Wan22FunControlToVideo).
Talks to the local ComfyUI HTTP API; does not change vid2vid.py or any workflow file.

Usage (on the PC, any Python 3):
  python vid2vid_control.py --control renders/R14_b/R14_control_depth.mp4 --guide renders/R14_b/R14_guide.mp4 \
                            --out renders/R14_b/wanctl [--frames 121] [--start 0] [--width 960 --height 544]
                            [--steps 20] [--cfg 5] [--seed 7] [--ref some.png]
"""
import argparse, json, shutil, sys, time, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vid2vid import COMFY_ROOT, PROMPT, NEGATIVE, call      # noqa: E402  same prompt as the uncontrolled pass

UNET = 'wan2.2_fun_control_5B_bf16.safetensors'


def graph(ctl_name, ref, a):
    g = {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': UNET, 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': 'umt5_xxl_fp8_e4m3fn_scaled.safetensors', 'type': 'wan', 'device': 'default'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'wan2.2_vae.safetensors'}},
        '4': {'class_type': 'CLIPTextEncode', 'inputs': {'text': a.prompt, 'clip': ['2', 0]}},
        '5': {'class_type': 'CLIPTextEncode', 'inputs': {'text': a.negative, 'clip': ['2', 0]}},
        '6': {'class_type': 'ModelSamplingSD3', 'inputs': {'shift': a.shift, 'model': ['1', 0]}},
        # control video (depth)
        '20': {'class_type': 'LoadVideo', 'inputs': {'file': ctl_name}},
        '21': {'class_type': 'GetVideoComponents', 'inputs': {'video': ['20', 0]}},
        '22': {'class_type': 'ImageFromBatch', 'inputs': {'image': ['21', 0], 'batch_index': a.start, 'length': a.frames}},
        '23': {'class_type': 'ImageScale', 'inputs': {'image': ['22', 0], 'upscale_method': 'lanczos', 'width': a.width, 'height': a.height, 'crop': 'center'}},
        '30': {'class_type': 'Wan22FunControlToVideo', 'inputs': {'positive': ['4', 0], 'negative': ['5', 0], 'vae': ['3', 0],
                                                                 'width': a.width, 'height': a.height, 'length': a.frames,
                                                                 'batch_size': 1, 'control_video': ['23', 0]}},
        '8': {'class_type': 'KSampler', 'inputs': {'model': ['6', 0], 'seed': a.seed, 'steps': a.steps, 'cfg': a.cfg,
                                                  'sampler_name': 'uni_pc', 'scheduler': 'simple', 'positive': ['30', 0],
                                                  'negative': ['30', 1], 'latent_image': ['30', 2], 'denoise': 1.0}},
        '9': {'class_type': 'VAEDecode', 'inputs': {'samples': ['8', 0], 'vae': ['3', 0]}},
        '10': {'class_type': 'CreateVideo', 'inputs': {'images': ['9', 0], 'fps': 24}},
        '11': {'class_type': 'SaveVideo', 'inputs': {'video': ['10', 0], 'filename_prefix': f'ruosuen/{a.tag}', 'format': 'auto', 'codec': 'auto'}},
    }
    if ref == 'guide':
        g['40'] = {'class_type': 'LoadVideo', 'inputs': {'file': a.guide_name}}
        g['41'] = {'class_type': 'GetVideoComponents', 'inputs': {'video': ['40', 0]}}
        g['42'] = {'class_type': 'ImageFromBatch', 'inputs': {'image': ['41', 0], 'batch_index': a.start, 'length': 1}}
    elif ref:
        g['42'] = {'class_type': 'LoadImage', 'inputs': {'image': ref}}
    if ref:
        g['43'] = {'class_type': 'ImageScale', 'inputs': {'image': ['42', 0], 'upscale_method': 'lanczos', 'width': a.width, 'height': a.height, 'crop': 'center'}}
        g['30']['inputs']['ref_image'] = ['43', 0]
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--control', type=Path, required=True, help='depth control mp4 from render_cut.py --control depth')
    ap.add_argument('--guide', type=Path, help='guide mp4; its first frame is the start image unless --ref/--no-ref')
    ap.add_argument('--ref', type=Path, help='start image (png) instead of the guide frame')
    ap.add_argument('--no-ref', action='store_true')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--comfy', default='http://127.0.0.1:8188')
    ap.add_argument('--frames', type=int, default=121)      # 4n+1; the model is trained on 121 = 5.0 s at 24 fps
    ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--width', type=int, default=960)
    ap.add_argument('--height', type=int, default=544)
    ap.add_argument('--steps', type=int, default=20)
    ap.add_argument('--cfg', type=float, default=5.0)
    ap.add_argument('--shift', type=float, default=8.0)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--prompt', default=PROMPT)
    ap.add_argument('--negative', default=NEGATIVE)
    ap.add_argument('--tag', default='')
    a = ap.parse_args()
    if not (COMFY_ROOT / 'models' / 'diffusion_models' / UNET).exists():
        raise SystemExit(f'missing model: models/diffusion_models/{UNET}')
    ref_kind = 'none' if a.no_ref else ('img' if a.ref else ('guide' if a.guide else 'none'))
    a.tag = a.tag or f'{a.control.stem}_functl_{ref_kind}_s{a.seed}'
    inp = COMFY_ROOT / 'input'
    ctl_name = f'ruosuen_{a.control.name}'; shutil.copy2(a.control, inp / ctl_name)
    ref = ''
    if ref_kind == 'guide':
        a.guide_name = f'ruosuen_{a.guide.name}'; shutil.copy2(a.guide, inp / a.guide_name); ref = 'guide'
    elif ref_kind == 'img':
        ref = f'ruosuen_ref_{a.ref.name}'; shutil.copy2(a.ref, inp / ref)
    r = call(f'{a.comfy}/prompt', {'prompt': graph(ctl_name, ref, a), 'client_id': uuid.uuid4().hex})
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
                if f.get('type') != 'output':
                    continue
                src = COMFY_ROOT / 'output' / f.get('subfolder', '') / f['filename']
                dst = a.out / f'{a.tag}{src.suffix}'
                shutil.copy2(src, dst)
                print('saved', dst, f'{time.time() - t0:.0f}s')
    (a.out / f'{a.tag}.json').write_text(json.dumps({k: (str(v) if isinstance(v, Path) else v) for k, v in vars(a).items()},
                                                   ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
