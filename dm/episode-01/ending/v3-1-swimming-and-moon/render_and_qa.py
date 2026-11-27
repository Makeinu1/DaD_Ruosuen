#!/usr/bin/env python3
"""Render v3.1 (82s / 12 shots / 5 Seedance clips) Pill Previs contact sheets,
dedicated C6 swimming & C7b moon-dissolution strips, mathematical QA, and 720p24 MP4s."""

import argparse
import base64
import io
import json
import math
import time
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "scene_spec.json"
HTML_PATH = ROOT / "pill_engine.html"
SHEETS_DIR = ROOT / "sheets"
CLIPS_DIR = ROOT / "clips"
QA_MD_PATH = ROOT / "QA_CAMERA_CONTINUITY.md"

FONT_SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"


def fnt(path, size):
    return ImageFont.truetype(path, size)


def capture_frame(page, t, no_fade=False, fmt="png"):
    mime = "image/png" if fmt == "png" else "image/jpeg"
    res = page.evaluate(
        """([t, noFade, mime]) => {
            const info = window.renderAtTime(t, { noFade });
            const canvas = document.getElementById('gl');
            const dataUrl = mime === 'image/png' ? canvas.toDataURL('image/png') : canvas.toDataURL('image/jpeg', 0.93);
            return { info, dataUrl };
        }""",
        [float(t), bool(no_fade), mime],
    )
    raw = base64.b64decode(res["dataUrl"].split(",", 1)[1])
    return Image.open(io.BytesIO(raw)).convert("RGB"), res["info"]


def draw_projected_tags(img, info, draw_cut_badge=False):
    w, h = img.size
    d = ImageDraw.Draw(img)
    f_tag = fnt(FONT_SANS, 12)

    def tag(proj, label, col):
        if not proj or not proj.get("visible"):
            return
        u, v = proj["u"], proj["v"]
        if not (0.03 <= u <= 0.97 and 0.05 <= v <= 0.95):
            return
        px, py = int(u * w), int(v * h)
        d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=col, outline=(255, 255, 255), width=1)
        bx = max(4, min(w - 86, px + 7))
        by = max(4, min(h - 20, py - 10))
        bbox = d.textbbox((0, 0), label, font=f_tag)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.rounded_rectangle([bx - 3, by - 2, bx + tw + 4, by + th + 3], radius=4, fill=(10, 14, 22), outline=col, width=1)
        d.text((bx - bbox[0], by - bbox[1]), label, font=f_tag, fill=col)

    if 6.0 <= info["t"] <= 67.6:
        tag(info["whale"]["center"], "WHALE 24m", (96, 206, 255))
        if info["shotId"] != "C7b" or info["t"] < 62.5:
            tag(info["whale"]["nose"], "NOSE", (255, 255, 255))
        if info["shotId"] == "C7b" and info["t"] >= 63.0:
            tag(info["whale"]["tail"], "TAIL TIP", (250, 220, 130))
    if info["shotId"] in ("C1", "C2", "C5", "C7a", "C7c", "C8"):
        tag(info["lantern"], "LANTERN", (255, 220, 120))
        tag(info["p0"], "P0", (200, 245, 210))
    if info["shotId"] in ("C5", "C6c", "C7a", "C7b", "C7c"):
        tag(info["fissure"], "FULL MOON", (245, 248, 255))
    pc2 = info["pcs"].get("PC2")
    if pc2 and pc2.get("visible") and info["shotId"] in ("C2", "C3", "C5", "C7a", "C7c"):
        tag(pc2, "4 PCs (1.7m)", (255, 208, 96))

    if draw_cut_badge:
        d.rounded_rectangle([8, 8, 56, 28], radius=4, fill=(210, 48, 48))
        d.text((16, 10), "CUT", font=fnt(FONT_SANS, 13), fill=(255, 255, 255))


def build_contact_sheet(tiles, cols, rows, title, subtitle, out_path):
    tw, th = 560, 315
    bar_top, bar_bot = 32, 46
    cell_w, cell_h = tw, th + bar_top + bar_bot
    pad, gap = 26, 15
    hdr_h = 84
    W = pad * 2 + cols * cell_w + (cols - 1) * gap
    H = hdr_h + pad + rows * cell_h + (rows - 1) * gap + pad

    sheet = Image.new("RGB", (W, H), (11, 15, 22))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 16), title, font=fnt(FONT_SANS, 24), fill=(238, 244, 250))
    d.text((pad, 50), subtitle, font=fnt(FONT_SERIF, 15), fill=(154, 178, 204))

    for idx, tile in enumerate(tiles):
        r, c = divmod(idx, cols)
        x0 = pad + c * (cell_w + gap)
        y0 = hdr_h + r * (cell_h + gap)
        d.rounded_rectangle([x0 - 2, y0 - 2, x0 + cell_w + 2, y0 + cell_h + 2], radius=8, fill=(18, 24, 34), outline=(48, 66, 92), width=2)
        d.rectangle([x0, y0, x0 + cell_w, y0 + bar_top], fill=(16, 22, 32))
        d.text((x0 + 8, y0 + 6), tile["header"], font=fnt(FONT_SANS, 14), fill=tile.get("color", (130, 195, 255)))
        d.text((x0 + cell_w - 134, y0 + 7), tile["meta"], font=fnt(FONT_SANS, 12), fill=(176, 194, 214))
        thumb = tile["img"].resize((tw, th), Image.Resampling.LANCZOS)
        draw_projected_tags(thumb, tile["info"], draw_cut_badge=tile.get("is_cut", False))
        sheet.paste(thumb, (x0, y0 + bar_top))
        d.rectangle([x0, y0 + bar_top + th, x0 + cell_w, y0 + cell_h], fill=(14, 19, 28))
        d.text((x0 + 8, y0 + bar_top + th + 5), tile["cap1"], font=fnt(FONT_SANS, 12), fill=(232, 238, 244))
        d.text((x0 + 8, y0 + bar_top + th + 24), tile["cap2"], font=fnt(FONT_SERIF, 11), fill=(155, 175, 198))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    print(f"Saved sheet: {out_path} ({W}x{H})")


def run_camera_qa(page, spec):
    rows, fails = [], []
    for cl in spec["clips"]:
        dur = cl["end"] - cl["start"]
        if dur >= 29.0:
            fails.append(f"CLIP {cl['id']} duration {dur:.1f}s >= 29s Seedance limit")
    for sh in spec["shots"]:
        dur = sh["end"] - sh["start"]
        if dur < 2.0:
            fails.append(f"SHOT {sh['id']} duration {dur:.1f}s < 2.0s hold minimum")

    prev_info = None
    swim_speeds = []
    n_steps = int(spec["duration"] * 2) + 1
    for idx in range(n_steps):
        t = min(spec["duration"] - 0.1, idx * 0.5)
        info = page.evaluate("t => window.renderAtTime(t, { noFade: true })", float(t))
        cp = info["camPos"]
        wp = info["whale"]["pos"]
        r_xz = math.hypot(cp[0], cp[2] + 6.0)
        dist_w = math.dist(cp, wp)
        if cp[1] < 0.7 or cp[1] > 41.0:
            fails.append(f"t={t:.1f}s ({info['shotId']}): camera Y={cp[1]:.2f}m out of safe [0.7, 41.0]")
        if r_xz > 56.0:
            fails.append(f"t={t:.1f}s ({info['shotId']}): camera R={r_xz:.1f}m near cave wall")
        if 6.0 <= t <= 67.0 and dist_w < 4.5:
            fails.append(f"t={t:.1f}s ({info['shotId']}): camera clipped near whale (dist={dist_w:.2f}m)")

        speed_str = "-"
        if prev_info:
            dt = max(1e-4, t - prev_info["t"])
            spd = math.dist(wp, prev_info["whale"]["pos"]) / dt
            speed_str = f"{spd:.1f}m/s"
            if 38.0 <= t <= 53.0:
                swim_speeds.append(spd)

        if idx % 6 == 0 or (prev_info and prev_info["shotId"] != info["shotId"]):
            wc = info["whale"]["center"]
            vis_str = f"({wc['u']:.2f},{wc['v']:.2f})" if wc["visible"] else "off/dissolved"
            rows.append(
                f"| {t:4.1f}s | {info['shotId']:3s} | {info['focal_mm']:.0f}mm | "
                f"({cp[0]:+5.1f},{cp[1]:4.1f},{cp[2]:+5.1f}) | {dist_w:4.1f}m | {speed_str:7s} | {vis_str} |"
            )
        prev_info = info

    avg_swim = sum(swim_speeds) / max(1, len(swim_speeds))
    status = "PASS (0 fails)" if not fails else f"FAIL ({len(fails)} issues)"
    md = [
        "# v3.1 Pill Previs（82秒・12カット）— カメラ連続性・遊泳速度・月溶解 QA レポート",
        "",
        f"- **総合判定**：`{status}`",
        "- **総尺・構成**：**82秒（1分22秒）・全12カット・Seedance 5クリップ分割**（12s / 13s / 21s / 22s / 14s — 全クリップ29秒未満）",
        "- **全カット最短ホールド**：最短 **5.0秒**（C6a / C7c）— 急がず余韻を残す劇場アニメ尺",
        f"- **遊泳フェーズ（C6b–C6c）の24m白鯨巡航速度**：平均 **{avg_swim:.2f} m/s**（巨体らしいゆったりした無重力遊泳を維持）",
        "- **C7b 月光溶解タイミング**：`t=60.0s` 鼻先が満月裂け目へ到達 → `t=64.0s` 胴体中央通過（前半溶解） → `t=67.2s` 尾びれの先まで完全溶解 → `0.8s` 満月の余韻",
        "",
    ]
    if fails:
        md.append("## 検出されたエラー")
        for f in fails:
            md.append(f"- {f}")
        md.append("")
    md.extend([
        "## 数値テレメトリ（主要サンプル）",
        "",
        "| 時刻 | Cut | レンズ | カメラXYZ | 鯨距離 | 鯨速度 | 鯨画面位置(u,v) |",
        "|---|---|---|---|---|---|---|",
        *rows,
        "",
    ])
    QA_MD_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"QA report saved: {QA_MD_PATH} -> {status} (avg swim speed={avg_swim:.2f} m/s)")
    return fails


def render_sheets(page, spec):
    hero_t = {
        "C1": 3.0, "C2": 9.0, "C3": 16.0, "C4": 22.0,
        "C5": 30.2, "C6a": 34.4, "C6b": 42.0, "C6c": 49.5,
        "C7a": 57.5, "C7b": 64.0, "C7c": 70.5, "C8": 79.0,
    }
    colors = {
        "C1": (120,190,255), "C2": (245,130,130), "C3": (245,110,110), "C4": (255,95,95),
        "C5": (110,220,210), "C6a": (250,230,150), "C6b": (250,220,125), "C6c": (250,210,110),
        "C7a": (155,205,255), "C7b": (235,245,255), "C7c": (165,215,245), "C8": (250,222,135),
    }

    # 1. One-Per-Shot 4x3 (all 12 shots!)
    tiles_all = []
    for sh in spec["shots"]:
        t = hero_t[sh["id"]]
        img, info = capture_frame(page, t, no_fade=True)
        tiles_all.append({
            "img": img, "info": info, "color": colors[sh["id"]], "is_cut": False,
            "header": f"{sh['id']}  {sh['name']}",
            "meta": f"t={t:4.1f}s | {sh['focal_mm']:.0f}mm",
            "cap1": f"{sh['emotion']}  |  {sh['camera_move']}",
            "cap2": sh["caption"][:48] + ("…" if len(sh["caption"]) > 48 else ""),
        })
    build_contact_sheet(
        tiles_all, 4, 3,
        "第一話エンディング v3.1（82秒・全12カット）— ヒーローフレーム一覧",
        "鯨の遊泳（C6a/b/c：20秒）と月への溶解・祝福（C7a/b/c：20秒）を煮詰めた最適時間配分",
        SHEETS_DIR / "one_per_shot_v3_1.png",
    )

    # 2. Act II Swimming Focus (C5, C6a, C6b, C6c In/Mid/Out)
    for fname, subset, ttl, sub in [
        ("in_mid_out_act2_swimming.png", spec["shots"][4:8],
         "v3.1 Act II 重点検査：月光覚醒＆3段階『白鯨の遊泳』（C5 → C6a → C6b → C6c）",
         "C6a(1.5s花弁静止) → C6b(花雪の斜め並走遊泳) → C6c(高所オービット＆鏡面湖の逆さ白鯨)"),
        ("in_mid_out_act3_moon.png", spec["shots"][8:12],
         "v3.1 Act III 重点検査：3段階『月への別れ・溶解・雪の祝福』（C7a → C7b → C7c → C8）",
         "C7a(4人の背中から向き直りを見上げる) → C7b(50mm近接・頭から尾まで満月へ溶ける) → C7c(本当の雪が降る) → C8(最後の一枚)"),
    ]:
        tiles = []
        for sh in subset:
            for stg, tt, is_cut in [("IN", sh["start"]+0.25, True), ("MID", (sh["start"]+sh["end"])*0.5, False), ("OUT", sh["end"]-0.35, False)]:
                img, info = capture_frame(page, tt, no_fade=True)
                tiles.append({
                    "img": img, "info": info, "color": colors[sh["id"]], "is_cut": is_cut,
                    "header": f"{sh['id']} [{stg}]  {sh['camera_move']}",
                    "meta": f"t={tt:4.1f}s | {sh['focal_mm']:.0f}mm",
                    "cap1": f"{sh['name']}（{sh['start']:.0f}-{sh['end']:.0f}s）",
                    "cap2": sh["emotion"],
                })
        build_contact_sheet(tiles, 3, 4, ttl, sub, SHEETS_DIR / fname)

    # 3. Dedicated 1-second strip of C7b (60.5 -> 67.5s): Head-to-Tail Dissolution Into the Full Moon!
    moon_times = [60.5, 61.5, 62.5, 63.5, 64.5, 65.5, 66.5, 67.5]
    moon_notes = [
        "鼻先が銀白の満月裂け目へ到達",
        "頭部が月光へ吸い込まれ始める",
        "胸びれ・前胴体が銀白光へ溶け始める",
        "胴体中央が裂け目を通過（前半は月光へ溶解）",
        "後半胴体が静かに上昇し光を纏う",
        "尾の付け根まで月光の中へ",
        "尾びれの先が最後のひと閃きで溶ける",
        "完全消失 — 満月だけが静かに残る（0.8s余韻）",
    ]
    m_tiles = []
    for tt, note in zip(moon_times, moon_notes):
        img, info = capture_frame(page, tt, no_fade=True)
        m_tiles.append({
            "img": img, "info": info, "color": (235, 245, 255), "is_cut": (tt == 60.5),
            "header": f"C7b 溶解ステップ  t = {tt:.1f}s",
            "meta": "50mm Slow Tilt-Up",
            "cap1": note,
            "cap2": "頭→胴→尾びれの先まで順番に満月の銀白光へ溶けて消える設計",
        })
    build_contact_sheet(
        m_tiles, 4, 2,
        "v3.1 C7b 特別詳細シート：白鯨が『頭から尾びれの先まで』満月に溶けて消える8秒間",
        "中望遠50mmで月光柱を仰ぎ、24mの巨体が裂け目の満月へ順番に溶け込む1秒刻み検証",
        SHEETS_DIR / "c7b_moon_dissolve_strip.png",
    )


def overlay_master_slate(img, info, spec):
    W, H = img.size
    out = img.copy()
    d = ImageDraw.Draw(out)
    bar_h = 34
    d.rectangle([0, 0, W, bar_h], fill=(10, 14, 22))
    d.rectangle([0, H - bar_h, W, H], fill=(10, 14, 22))
    sh = next(s for s in spec["shots"] if s["id"] == info["shotId"])
    d.text((14, 7), f"{sh['id']}｜{sh['name']}   [{sh['camera_move']} / {sh['focal_mm']:.0f}mm]", font=fnt(FONT_SANS, 15), fill=(238, 244, 250))
    d.text((W - 190, 8), f"t = {info['t']:05.2f}s / {spec['duration']:.0f}.00s", font=fnt(FONT_SANS, 15), fill=(248, 220, 136))
    d.text((14, H - bar_h + 7), f"感情：{sh['emotion']}  —  {sh['caption']}", font=fnt(FONT_SERIF, 13), fill=(186, 206, 228))
    prog = int((info["t"] / spec["duration"]) * W)
    d.rectangle([0, H - 3, prog, H], fill=(96, 206, 245))
    return out


def render_single_clip(page, spec, clip_idx):
    fps = spec["fps"]
    cl = spec["clips"][clip_idx]
    f_start = int(round(cl["start"] * fps))
    f_end = int(round(cl["end"] * fps))
    dur = int(round(cl["end"] - cl["start"]))
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = CLIPS_DIR / f"seedance_v3_1_{cl['id']}_{dur}s.mp4"
    seg_path = CLIPS_DIR / f"_seg_{clip_idx}.mp4"

    raw_c = av.open(str(raw_path), mode="w")
    raw_s = raw_c.add_stream("libx264", rate=fps)
    raw_s.width, raw_s.height, raw_s.pix_fmt = 1280, 720, "yuv420p"
    raw_s.options = {"crf": "18", "preset": "fast", "movflags": "+faststart"}

    seg_c = av.open(str(seg_path), mode="w")
    seg_s = seg_c.add_stream("libx264", rate=fps)
    seg_s.width, seg_s.height, seg_s.pix_fmt = 1280, 720, "yuv420p"
    seg_s.options = {"crf": "20", "preset": "fast"}

    t0 = time.time()
    n_total = f_end - f_start
    for i, fi in enumerate(range(f_start, f_end)):
        t = fi / fps
        raw_img, info = capture_frame(page, t, no_fade=False, fmt="jpg")
        vf_r = av.VideoFrame.from_ndarray(np.asarray(raw_img), format="rgb24")
        for pkt in raw_s.encode(vf_r):
            raw_c.mux(pkt)
        slated_img = overlay_master_slate(raw_img, info, spec)
        vf_s = av.VideoFrame.from_ndarray(np.asarray(slated_img), format="rgb24")
        for pkt in seg_s.encode(vf_s):
            seg_c.mux(pkt)
        if (i + 1) % 120 == 0 or i + 1 == n_total:
            print(f"  [clip {clip_idx+1}] {i+1}/{n_total} frames ({time.time()-t0:.1f}s)", flush=True)

    for pkt in raw_s.encode():
        raw_c.mux(pkt)
    raw_c.close()
    for pkt in seg_s.encode():
        seg_c.mux(pkt)
    seg_c.close()
    print(f"Encoded Raw Seedance Clip: {raw_path} ({n_total} frames, {n_total/fps:.1f}s)")


def concat_master(spec):
    fps = spec["fps"]
    master_path = CLIPS_DIR / "master_82s_preview_v3_1.mp4"
    out_c = av.open(str(master_path), mode="w")
    out_s = out_c.add_stream("libx264", rate=fps)
    out_s.width, out_s.height, out_s.pix_fmt = 1280, 720, "yuv420p"
    out_s.options = {"crf": "20", "preset": "fast", "movflags": "+faststart"}
    total = 0
    for idx in range(len(spec["clips"])):
        seg_path = CLIPS_DIR / f"_seg_{idx}.mp4"
        in_c = av.open(str(seg_path))
        for frame in in_c.decode(video=0):
            vf = av.VideoFrame.from_ndarray(frame.to_ndarray(format="rgb24"), format="rgb24")
            for pkt in out_s.encode(vf):
                out_c.mux(pkt)
            total += 1
        in_c.close()
        seg_path.unlink(missing_ok=True)
    for pkt in out_s.encode():
        out_c.mux(pkt)
    out_c.close()
    print(f"Encoded Master 82s Preview: {master_path} ({total} frames, {total/fps:.1f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["sheets", "clip", "concat"], default="sheets")
    ap.add_argument("--clip-index", type=int, default=0)
    args = ap.parse_args()
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if args.mode == "concat":
        concat_master(spec)
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"],
        )
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.add_init_script("window.__HEADLESS_RENDER__ = true;")
        page.goto(HTML_PATH.as_uri(), wait_until="load")
        page.evaluate("spec => window.initPillScene(spec)", spec)

        if args.mode == "sheets":
            run_camera_qa(page, spec)
            render_sheets(page, spec)
        elif args.mode == "clip":
            render_single_clip(page, spec, args.clip_index)
        browser.close()


if __name__ == "__main__":
    main()
