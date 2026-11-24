"""v15 one-command runner for the VideoStudio PC (Windows, Blender 5.3). Run INSIDE Blender:

  blender -b -P pc_run.py -- --cut R14 --steps export,render,encode,paint [--res 1280] [--tag a]
or from the VideoStudio MCP (blender_run), see README.md 「PCでの実行」.

Steps (comma separated, in this order):
  export  previs -> <ROOT>/cache/<cut>            (bridge/export_cut.py, Blender's python + pylib)
  render  EEVEE beauty -> <ROOT>/renders/<cut>_<tag>/beauty/####.png   (blender/render_cut.py)
  encode  beauty -> <cut>_guide.mp4  (ffmpeg)
  paint   方式①  -> paint/####.png + <cut>_paint.mp4                   (post/paint.py)
  wan     方式③  -> wan/<...>.mp4 via local ComfyUI                     (wan/vid2vid.py)
ROOT = C:/VideoStudio/projects/ruosuen (repo/, pylib/, cache/, renders/). Nothing here writes to git.
"""
import os, sys, subprocess, shutil, time, runpy, argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('RUOSUEN_ROOT', r'C:\VideoStudio\projects\ruosuen'))
PYLIB = ROOT / 'pylib'


def sh(cmd, **kw):
    t = time.time()
    env = dict(os.environ); env['PYTHONPATH'] = str(PYLIB)
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, **kw)
    print('$', Path(str(cmd[1])).name if len(cmd) > 1 else cmd[0], '->', r.returncode, f'{time.time() - t:.0f}s')
    print((r.stdout + r.stderr)[-1200:], flush=True)
    if r.returncode:
        raise SystemExit(f'step failed: {cmd[:2]}')


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--cut', required=True)
    ap.add_argument('--steps', default='export,render,encode,paint')
    ap.add_argument('--res', type=int, default=1280)
    ap.add_argument('--samples', type=int, default=32)
    ap.add_argument('--tag', default='a')
    ap.add_argument('--frames', default='')
    ap.add_argument('--render-args', default='', help='extra args for render_cut.py, e.g. "--set petal_emit=1.6"')
    ap.add_argument('--wan-args', default='', help='extra args for vid2vid.py, e.g. "--denoise 0.6 --seed 3"')
    a = ap.parse_args(argv)
    steps = a.steps.split(',')
    cache = ROOT / 'cache' / a.cut
    out = ROOT / 'renders' / f'{a.cut}_{a.tag}'
    py = sys.executable
    ff = shutil.which('ffmpeg') or r'C:\ffmpeg\bin\ffmpeg.exe'
    if 'export' in steps:
        sh([py, HERE / 'bridge' / 'export_cut.py', '--cut', a.cut, '--out', cache])
    if 'render' in steps:
        sys.path.insert(0, str(PYLIB))
        rc = runpy.run_path(str(HERE / 'blender' / 'render_cut.py'), run_name='render_cut')
        ra = ['--cache', str(cache), '--out', str(out), '--res', str(a.res), '--samples', str(a.samples), '--save-blend']
        if a.frames:
            ra += ['--frames', a.frames]
        rc['main'](ra + a.render_args.split())
    if 'encode' in steps:
        sh([ff, '-y', '-loglevel', 'error', '-framerate', '24', '-i', out / 'beauty' / '%04d.png',
            '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out / f'{a.cut}_guide.mp4'])
    if 'paint' in steps:
        sh([py, HERE / 'post' / 'paint.py', '--src', out / 'beauty', '--dst', out / 'paint', '--mp4', out / f'{a.cut}_paint.mp4'])
    if 'wan' in steps:
        sh([py, HERE / 'wan' / 'vid2vid.py', '--video', out / f'{a.cut}_guide.mp4', '--out', out / 'wan'] + a.wan_args.split())
    print('pc_run done', a.cut, steps)


if __name__ == '__main__':
    g = globals().get('ARGS')
    main(g if g is not None else (sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []))
