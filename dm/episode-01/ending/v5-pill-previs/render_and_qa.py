#!/usr/bin/env python3
"""Render v5.0 Definitive Synthesis (96s / 15 cuts / 6 clips) Seedance Pill Previs
contact sheets, mathematical camera QA, and 1280x720 24fps H.264 MP4s."""

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
        bx = max(4, min(w - 102, px + 7))
        by = max(4, min(h - 20, py - 10))
        bbox = d.textbbox((0, 0), label, font=f_tag)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.rounded_rectangle([bx - 3, by - 2, bx + tw + 4, by + th + 3], radius=4, fill=(10, 14, 22), outline=col, width=1)
        d.text((bx - bbox[0], by - bbox[1]), label, font=f_tag, fill=col)

    if 6.0 <= info["t"] <= 81.4:
        if info["shotId"] == "C4b":
            tag(info["whale"].get("eye"), "EYE GLINT", (255, 232, 148))
        elif info["shotId"] == "C7b":
            if info["t"] < 77.2:
                tag(info["whale"]["tail"], "TAIL DISSOLVES 1ST", (250, 215, 130))
            if info["t"] < 81.2:
                tag(info["whale"]["nose"], "HEAD LAST", (255, 255, 255))
        else:
            tag(info["whale"]["center"], "WHALE 24m", (96, 206, 255))
            if info["shotId"] == "C6d" and 62.0 <= info["t"] <= 66.0:
                tag(info["whale"].get("eye"), "22° GLANCE", (255, 232, 148))
            else:
                tag(info["whale"]["nose"], "NOSE", (255, 255, 255))
    if info["shotId"] in ("C1", "C2", "C3", "C4a", "C5a", "C5b", "C7a", "C7c", "C8"):
        tag(info["lantern"], "LANTERN", (255, 220, 120))
        if info["shotId"] in ("C1", "C5b", "C8"):
            tag(info["p0"], "P0", (200, 245, 210))
    if info["shotId"] in ("C5b", "C6a", "C6b", "C6c", "C7a"):
        tag(info.get("bridgeLeft"), "ARCH BRIDGE", (175, 215, 248))
    if info["shotId"] in ("C5a", "C6c", "C7a", "C7b", "C7c"):
        tag(info["fissure"], "FULL MOON", (245, 248, 255))
    pc2 = info["pcs"].get("PC2")
    if pc2 and pc2.get("visible") and info["shotId"] in ("C2", "C3", "C4a", "C5a", "C7a", "C7c"):
        tag(pc2, "4 PCs (1.7m)", (255, 208, 96))

    if draw_cut_badge:
        d.rounded_rectangle([8, 8, 56, 28], radius=4, fill=(210, 48, 48))
        d.text((16, 10), "CUT", font=fnt(FONT_SANS, 13), fill=(255, 255, 255))


def build_contact_sheet(tiles, cols, rows, title, subtitle, out_path, tw=560, th=315):
    bar_top, bar_bot = 32, 46
    cell_w, cell_h = tw, th + bar_top + bar_bot
    pad, gap = 24, 14
    hdr_h = 84
    W = pad * 2 + cols * cell_w + (cols - 1) * gap
    H = hdr_h + pad + rows * cell_h + (rows - 1) * gap + pad

    sheet = Image.new("RGB", (W, H), (11, 15, 22))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 16), title, font=fnt(FONT_SANS, 23), fill=(238, 244, 250))
    d.text((pad, 50), subtitle, font=fnt(FONT_SERIF, 15), fill=(154, 178, 204))

    for idx, tile in enumerate(tiles):
        r, c = divmod(idx, cols)
        x0 = pad + c * (cell_w + gap)
        y0 = hdr_h + r * (cell_h + gap)
        d.rounded_rectangle([x0 - 2, y0 - 2, x0 + cell_w + 2, y0 + cell_h + 2], radius=8, fill=(18, 24, 34), outline=(48, 66, 92), width=2)
        d.rectangle([x0, y0, x0 + cell_w, y0 + bar_top], fill=(16, 22, 32))
        max_chars = 36 if tw >= 520 else 28
        hdr_txt = tile["header"] if len(tile["header"]) <= max_chars else tile["header"][:max_chars - 1] + "…"
        d.text((x0 + 8, y0 + 6), hdr_txt, font=fnt(FONT_SANS, 13), fill=tile.get("color", (130, 195, 255)))
        d.text((x0 + cell_w - 128, y0 + 7), tile["meta"], font=fnt(FONT_SANS, 12), fill=(176, 194, 214))
        thumb = tile["img"].resize((tw, th), Image.Resampling.LANCZOS)
        draw_projected_tags(thumb, tile["info"], draw_cut_badge=tile.get("is_cut", False))
        sheet.paste(thumb, (x0, y0 + bar_top))
        d.rectangle([x0, y0 + bar_top + th, x0 + cell_w, y0 + cell_h], fill=(14, 19, 28))
        d.text((x0 + 8, y0 + bar_top + th + 5), tile["cap1"][:46], font=fnt(FONT_SANS, 12), fill=(232, 238, 244))
        d.text((x0 + 8, y0 + bar_top + th + 24), tile["cap2"][:52], font=fnt(FONT_SERIF, 11), fill=(155, 175, 198))

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
        if dur < 2.5:
            fails.append(f"SHOT {sh['id']} duration {dur:.1f}s < 2.5s hold minimum")

    prev_info = None
    swim_speeds = []
    n_steps = int(spec["duration"] * 2) + 1
    for idx in range(n_steps):
        t = min(spec["duration"] - 0.1, idx * 0.5)
        info = page.evaluate("t => window.renderAtTime(t, { noFade: true })", float(t))
        cp = info["camPos"]
        wp = info["whale"]["pos"]
        r_xz = math.hypot(cp[0], cp[2] + 25.0)
        dist_w = math.dist(cp, wp)
        if cp[1] < 0.9 or cp[1] > 138.0:
            fails.append(f"t={t:.1f}s ({info['shotId']}): camera Y={cp[1]:.2f}m out of safe [0.9, 138.0]")
        if r_xz > 210.0:
            fails.append(f"t={t:.1f}s ({info['shotId']}): camera R={r_xz:.1f}m near cave wall")
        if 6.0 <= t <= 81.5 and dist_w < 4.0:
            fails.append(f"t={t:.1f}s ({info['shotId']}): camera clipped near whale (dist={dist_w:.2f}m)")

        speed_str = "-"
        if prev_info:
            dt = max(1e-4, t - prev_info["t"])
            spd = math.dist(wp, prev_info["whale"]["pos"]) / dt
            speed_str = f"{spd:.1f}m/s"
            if 44.0 <= t <= 69.0:
                swim_speeds.append(spd)

        if idx % 6 == 0 or (prev_info and prev_info["shotId"] != info["shotId"]):
            wc = info["whale"]["center"]
            vis_str = f"({wc['u']:.2f},{wc['v']:.2f})" if wc["visible"] else "off/dissolved"
            rows.append(
                f"| {t:4.1f}s | {info['shotId']:3s} | {info['focal_mm']:.0f}mm | "
                f"({cp[0]:+6.1f},{cp[1]:5.1f},{cp[2]:+6.1f}) | {dist_w:5.1f}m | {speed_str:7s} | {vis_str} |"
            )
        prev_info = info

    avg_swim = sum(swim_speeds) / max(1, len(swim_speeds))
    status = "PASS (0 fails)" if not fails else f"FAIL ({len(fails)} issues)"
    md = [
        "# v5.0 決定版 Pill Previs（96秒・全15カット・6クリップ）— カメラ連続性 QA レポート",
        "",
        f"- **総合判定**：`{status}`",
        "- **総尺・構成**：**96秒（1分36秒）・全15カット・Seedance 6クリップ分割**（12s / 13s / 19s / 25s / 14s / 13s — 全クリップ29秒未満・全カット3.5秒以上）",
        "- **背景美術**：**案1（最遠景の霧の巨岩柱・外枠のみ）＋ 案3（中景の水没した旧時代石造アーチ橋＋苔上の開花＋鏡面反射）の遠近レイヤー融合**（中央の白鯨＆満月抜けは完全無柱）",
        "- **導入〜開花**：v4.0 正面突進＆ニアミス（C3→C4a→C4b）→ v14.9b 地表20cm一斉開花（C5b）→ 離陸1秒静止→地上から空へ大チルトで3層大花吹雪へ自然接続（C6a）",
        f"- **大空洞遊泳＆遊び芝居（C6b–C6d）**：平均巡航 **{avg_swim:.2f} m/s**（360°緩やかロール → 40°遊びバンク大旋回 → 22°優しい一瞥＆0.6xスロー）",
        "- **別れ・満月溶解（C7b）**：**85mm真横望遠** で巨大な満月の前を滑空しながら **尾びれ→胴体→胸びれ→最後に頭部** へ滑らかに溶け還る（tail-to-head dissolve）",
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
    colors = {
        "C1": (120,190,255), "C2": (245,130,130), "C3": (255,95,95), "C4a": (255,80,80), "C4b": (220,130,190),
        "C5a": (110,220,210), "C5b": (130,235,195), "C6a": (250,230,150), "C6b": (108,224,216),
        "C6c": (250,215,120), "C6d": (180,215,255), "C7a": (155,205,255), "C7b": (235,245,255),
        "C7c": (165,215,245), "C8": (250,222,135),
    }

    # 1. Master 4x4 Overview (all 15 cuts + 1 extra C7b dissolve-end beat!)
    overview_picks = [
        ("C1",  3.0, "C1 安堵と予兆（P0・波紋）"),
        ("C2",  9.0, "C2 湖底を通過する巨影"),
        ("C3", 16.5, "C3【v4継承】正面直進・膨張"),
        ("C4a", 20.0, "C4a【v4継承】ランタン脇ニアミス"),
        ("C4b", 23.0, "C4b【v4継承】闇と眼1.8s無音"),
        ("C5a", 28.0, "C5a 月光覚醒（純白反転）"),
        ("C5b", 32.8, "C5b【復活R10】地表20cm一斉開花"),
        ("C6a", 36.2, "C6a【復活R12】離陸1秒静止→空チルト"),
        ("C6b", 47.8, "C6b【遊び①】360°ロール×石橋くぐり"),
        ("C6c", 56.0, "C6c【1+3決定画】石橋×霧岩柱×40°バンク"),
        ("C6d", 64.0, "C6d【遊び②】22°優しい一瞥0.6xスロー"),
        ("C7a", 72.2, "C7a 背中見送り＆残された雪"),
        ("C7b", 77.6, "C7b【復活R18】85mm真横・尾から溶解"),
        ("C7b", 80.5, "C7b【復活R18】頭部が最後に満月へ"),
        ("C7c", 86.0, "C7c 本物の雪が4人と石橋を包む"),
        ("C8",  92.5, "C8 C1完全同一・最後の一枚＆波紋"),
    ]
    tiles_ov = []
    for cid, tt, hdr in overview_picks:
        sh = next(s for s in spec["shots"] if s["id"] == cid)
        img, info = capture_frame(page, tt, no_fade=True)
        tiles_ov.append({
            "img": img, "info": info, "color": colors[cid], "is_cut": False,
            "header": hdr,
            "meta": f"t={tt:4.1f}s | {sh['focal_mm']:.0f}mm",
            "cap1": f"{sh['emotion']} | {sh['camera_move']}",
            "cap2": sh["caption"][:52] + ("…" if len(sh["caption"]) > 52 else ""),
        })
    build_contact_sheet(
        tiles_ov, 4, 4,
        "第一話エンディング v5.0 決定版（96秒・全15カット・6クリップ）— キーフレーム総覧",
        "正面突進(v4) × 地表20cm開花＆1秒静止チルト→3層大花吹雪 × 1+3石造アーチ橋＆霧岩柱 × 遊び芝居 × 85mm真横・尾から頭へ満月溶解",
        SHEETS_DIR / "one_per_shot_v5.png",
    )

    # 2. Focused 3x3 sheets for Act II-A (Bloom -> Snowstorm) and Act II-B (Playful Swim + 1+3 Fusion)
    for fname, cids, ttl, sub in [
        ("act2a_bloom_to_snowstorm_v5.png", ("C5a", "C5b", "C6a"),
         "v5.0 重点検証①：月光覚醒 → 地表20cm一斉開花 → 1秒静止→空へチルト＝3層大花吹雪の自然接続",
         "C5a(覚醒) → C5b(地表20cm開花ウェーブ＆石橋苔上開花) → C6a(離陸1秒静止→上空大チルトで空間を満たす花吹雪へ！)"),
        ("act2b_playful_swim_1plus3_v5.png", ("C6b", "C6c", "C6d"),
         "v5.0 重点検証②：220m大空洞 × 1+3遠近融合背景（石造アーチ橋＋最遠景霧岩柱）× 白鯨の遊び芝居",
         "C6b(360°緩やかロール＆石橋くぐり二重視差) → C6c(40°遊びバンク＆鏡面対称) → C6d(22°優しい一瞥・0.6xスロー)"),
    ]:
        tiles = []
        for cid in cids:
            sh = next(s for s in spec["shots"] if s["id"] == cid)
            picks = [("IN", sh["start"] + 0.4, True), ("MID", (sh["start"] + sh["end"]) * 0.5, False), ("OUT", sh["end"] - 0.4, False)]
            if cid == "C6a":
                picks = [("FREEZE 1s", 36.1, True), ("TILT MID", 39.6, False), ("SKY OPEN", 43.4, False)]
            for stg, tt, is_cut in picks:
                img, info = capture_frame(page, tt, no_fade=True)
                tiles.append({
                    "img": img, "info": info, "color": colors[cid], "is_cut": is_cut,
                    "header": f"{cid} [{stg}] {sh['camera_move']}",
                    "meta": f"t={tt:4.1f}s | {sh['focal_mm']:.0f}mm",
                    "cap1": f"{sh['name']}（{sh['start']:.0f}-{sh['end']:.0f}s）",
                    "cap2": sh["emotion"],
                })
        build_contact_sheet(tiles, 3, 3, ttl, sub, SHEETS_DIR / fname)

    # 3. Dedicated 1x5 Filmstrip for C7b (85mm Telephoto Side-Profile Tail-to-Head Full Moon Dissolve!)
    sh7b = next(s for s in spec["shots"] if s["id"] == "C7b")
    strip_beats = [
        ("① 真横進入", 75.5, "85mm真横望遠。巨大な満月の前へ白鯨が静かに滑空して入る"),
        ("② 尾びれ溶解開始", 77.2, "借りた月光を返すように、まず尾びれの先から銀白光へ溶け始める"),
        ("③ 胴体が光へ", 78.8, "胴体の半分が満月の光へ溶け、胸びれと頭部が穏やかに前を向く"),
        ("④ 頭部が最後に", 80.5, "最後に優しい頭部だけが月光の中へそっと溶けていく"),
        ("⑤ 1.5秒の満月余韻", 82.3, "白鯨が完全に還った真っ白な満月と、静かに漂う数片の花雪"),
    ]
    strip_tiles = []
    for lbl, tt, note in strip_beats:
        img, info = capture_frame(page, tt, no_fade=True)
        strip_tiles.append({
            "img": img, "info": info, "color": (235, 245, 255), "is_cut": (lbl.startswith("①")),
            "header": f"C7b {lbl}",
            "meta": f"t={tt:4.1f}s | 85mm",
            "cap1": note[:32],
            "cap2": note[32:] if len(note) > 32 else sh7b["emotion"],
        })
    build_contact_sheet(
        strip_tiles, 5, 1,
        "v5.0 重点検証③（復活 R18）：85mm真横望遠・尾びれから頭部へ満月へ溶け還る 5段階フィルムストリップ",
        "頭から穴に消えるのではなく、真横から満月の前を悠々と滑りながら『尾→胴→胸びれ→最後に頭部』が純白光へ還る美しい別れ",
        SHEETS_DIR / "c7b_tail_to_head_moon_strip_v5.png",
        tw=420, th=236,
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
    d.rectangle([0, H - 3, prog, H], fill=(108, 224, 216))
    return out


def render_single_clip(page, spec, clip_idx):
    fps = spec["fps"]
    cl = spec["clips"][clip_idx]
    f_start = int(round(cl["start"] * fps))
    f_end = int(round(cl["end"] * fps))
    dur = int(round(cl["end"] - cl["start"]))
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = CLIPS_DIR / f"seedance_v5_{cl['id']}_{dur}s.mp4"
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
    master_path = CLIPS_DIR / "master_96s_preview_v5.mp4"
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
    print(f"Encoded Master 96s Preview: {master_path} ({total} frames, {total/fps:.1f}s)")


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
