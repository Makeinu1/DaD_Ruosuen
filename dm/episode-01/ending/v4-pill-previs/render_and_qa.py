#!/usr/bin/env python3
"""Render v4.0 (90s / 13 cuts / 5 clips) Seedance Pill Previs contact sheets,
mathematical camera QA, and 1280x720 24fps H.264 MP4s."""

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
        bx = max(4, min(w - 92, px + 7))
        by = max(4, min(h - 20, py - 10))
        bbox = d.textbbox((0, 0), label, font=f_tag)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.rounded_rectangle([bx - 3, by - 2, bx + tw + 4, by + th + 3], radius=4, fill=(10, 14, 22), outline=col, width=1)
        d.text((bx - bbox[0], by - bbox[1]), label, font=f_tag, fill=col)

    if 6.0 <= info["t"] <= 70.6:
        if info["shotId"] == "C4b":
            tag(info["whale"].get("eye"), "EYE GLINT", (255, 232, 148))
        else:
            tag(info["whale"]["center"], "WHALE 24m", (96, 206, 255))
            if info["shotId"] != "C7b" or info["t"] < 65.5:
                tag(info["whale"]["nose"], "NOSE", (255, 255, 255))
            if info["shotId"] == "C7b" and info["t"] >= 66.0:
                tag(info["whale"]["tail"], "TAIL TIP", (250, 220, 130))
    if info["shotId"] in ("C1", "C2", "C3", "C4a", "C5", "C7a", "C7c", "C8"):
        tag(info["lantern"], "LANTERN", (255, 220, 120))
        if info["shotId"] in ("C1", "C8"):
            tag(info["p0"], "P0", (200, 245, 210))
    if info["shotId"] in ("C5", "C6c", "C7a", "C7b", "C7c"):
        tag(info["fissure"], "FULL MOON", (245, 248, 255))
    pc2 = info["pcs"].get("PC2")
    if pc2 and pc2.get("visible") and info["shotId"] in ("C2", "C3", "C4a", "C5", "C7a", "C7c"):
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
        hdr_txt = tile["header"] if len(tile["header"]) <= 38 else tile["header"][:37] + "…"
        d.text((x0 + 8, y0 + 6), hdr_txt, font=fnt(FONT_SANS, 14), fill=tile.get("color", (130, 195, 255)))
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
        r_xz = math.hypot(cp[0], cp[2] + 25.0)
        dist_w = math.dist(cp, wp)
        if cp[1] < 0.7 or cp[1] > 120.0:
            fails.append(f"t={t:.1f}s ({info['shotId']}): camera Y={cp[1]:.2f}m out of safe [0.7, 120.0]")
        if r_xz > 210.0:
            fails.append(f"t={t:.1f}s ({info['shotId']}): camera R={r_xz:.1f}m near cave wall")
        if 6.0 <= t <= 70.0 and dist_w < 4.0:
            fails.append(f"t={t:.1f}s ({info['shotId']}): camera clipped near whale (dist={dist_w:.2f}m)")

        speed_str = "-"
        if prev_info:
            dt = max(1e-4, t - prev_info["t"])
            spd = math.dist(wp, prev_info["whale"]["pos"]) / dt
            speed_str = f"{spd:.1f}m/s"
            if 39.0 <= t <= 56.0:
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
        "# v4.0 Pill Previs（90秒・全13カット・220m大空洞）— カメラ連続性 QA レポート",
        "",
        f"- **総合判定**：`{status}`",
        "- **総尺・構成**：**90秒（1分30秒）・全13カット・Seedance 5クリップ分割**（12s / 13s / 22s / 24s / 19s — 全クリップ29秒未満）",
        "- **空間スケール**：半径 **225m × 天井高 128m** の地底大空洞（旧v3.1の約3.7倍の開放空間）",
        "- **案A-1 緊張設計**：C3 正面直進（`X=0` 軸上・目線高さ維持）→ C4a ランタン脇での衝突寸前引き上げ → C4b 闇と眼の1.8秒無音",
        f"- **案B-1 大空洞遊泳（C6b–C6c）巡航速度**：平均 **{avg_swim:.2f} m/s**（220m空間に対する体長比 ~0.27 BL/s の悠々巡航＋60m花雪航跡リボン）",
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
        "C5": (110,220,210), "C6a": (250,230,150), "C6b": (108,224,216), "C6c": (250,215,120),
        "C7a": (155,205,255), "C7b": (235,245,255), "C7c": (165,215,245), "C8": (250,222,135),
    }

    # 1. Master 4x4 Overview (all 13 cuts + 3 signature key-moment doubles!)
    overview_picks = [
        ("C1",  3.0, "C1 安堵と予兆"),
        ("C2",  9.0, "C2 湖底の巨影"),
        ("C3", 15.2, "C3【案A-1】正面直進・膨張中"),
        ("C3", 17.6, "C3【案A-1】衝突直前（画面85%！）"),
        ("C4a", 19.6, "C4a【案A-1】ランタン脇・衝突寸前"),
        ("C4a", 21.2, "C4a【案A-1】ラスト1秒の引き上げ"),
        ("C4b", 23.0, "C4b【案A-1】闇と『眼』1.8秒無音"),
        ("C5",  30.4, "C5 月光覚醒＆枯れ草→白花畑"),
        ("C6a", 34.4, "C6a【案B-1①】光の絨毯1.5s＆220m大空洞"),
        ("C6b", 43.0, "C6b【案B-1②】花雪の航跡リボン並走"),
        ("C6c", 51.5, "C6c【案B-1③】220m大旋回＆鏡面対称"),
        ("C7a", 59.8, "C7a【案B-1④】最後に上空へ・花雪の河"),
        ("C7b", 66.5, "C7b 50mm満月溶解（胴体通過）"),
        ("C7b", 69.2, "C7b 50mm満月溶解（尾びれ消失）"),
        ("C7c", 74.5, "C7c 本当の雪が4人に降る祝福"),
        ("C8",  85.6, "C8 C1同一構図・最後の一枚＆波紋"),
    ]
    tiles_ov = []
    for cid, tt, hdr in overview_picks:
        sh = next(s for s in spec["shots"] if s["id"] == cid)
        img, info = capture_frame(page, tt, no_fade=True)
        tiles_ov.append({
            "img": img, "info": info, "color": colors[cid], "is_cut": False,
            "header": hdr,
            "meta": f"t={tt:4.1f}s | {sh['focal_mm']:.0f}mm",
            "cap1": f"{sh['emotion']}  |  {sh['camera_move']}",
            "cap2": sh["caption"][:48] + ("…" if len(sh["caption"]) > 48 else ""),
        })
    build_contact_sheet(
        tiles_ov, 4, 4,
        "第一話エンディング v4.0（90秒・全13カット）— 決定版キーフレーム総覧",
        "案A-1（正面直進→ランタン脇ニアミス→闇と眼）× 案B-1（220m大空洞×花雪の航跡リボン×広→近→広→上空満月）",
        SHEETS_DIR / "one_per_shot_v4.png",
    )

    # 2. Act I Tension Focus (C3, C4a, C4b In/Mid/Out — 3x3!)
    t_tiles = []
    for cid in ("C3", "C4a", "C4b"):
        sh = next(s for s in spec["shots"] if s["id"] == cid)
        for stg, tt, is_cut in [("IN", sh["start"]+0.25, True), ("MID", (sh["start"]+sh["end"])*0.5, False), ("OUT", sh["end"]-0.25, False)]:
            img, info = capture_frame(page, tt, no_fade=True)
            t_tiles.append({
                "img": img, "info": info, "color": colors[cid], "is_cut": is_cut,
                "header": f"{cid} [{stg}]  {sh['camera_move']}",
                "meta": f"t={tt:4.1f}s | {sh['focal_mm']:.0f}mm",
                "cap1": f"{sh['name']}（{sh['start']:.1f}-{sh['end']:.1f}s）",
                "cap2": sh["emotion"],
            })
    build_contact_sheet(
        t_tiles, 3, 3,
        "v4.0 重点検証①（案A-1）：『襲いかかる緊張』がラスト0.3秒まで途切れない C3 → C4a → C4b",
        "正面直進の膨張(C3) → ランタン脇での衝突寸前引き上げ(C4a) → 闇の中を横切る静かな眼と1.8秒無音(C4b)",
        SHEETS_DIR / "act1_tension_A1.png",
    )

    # 3. Act II Abyss Swimming & Wake Ribbons Focus (C5, C6a, C6b, C6c In/Mid/Out — 3x4!)
    for fname, cids, ttl, sub in [
        ("act2_abyss_swimming_B1.png", ("C5", "C6a", "C6b", "C6c"),
         "v4.0 重点検証②（案B-1）：220m大空洞 × 花雪の航跡リボン × 広→近→広の黄金リズム",
         "C5(一斉開花) → C6a(21mm光の絨毯1.5s) → C6b(35mm航跡リボン並走) → C6c(21mm 220m大旋回＆鏡面対称)"),
        ("act3_moon_dissolve_v4.png", ("C7a", "C7b", "C7c", "C8"),
         "v4.0 重点検証③：泳ぎ切った最後に上空の満月へ昇り溶ける別れと祝福（C7a → C7b → C7c → C8）",
         "C7a(花雪の河と上空への旅立ち) → C7b(50mm頭→尾びれ満月溶解) → C7c(本当の雪が降る) → C8(最後の一枚)"),
    ]:
        tiles = []
        for cid in cids:
            sh = next(s for s in spec["shots"] if s["id"] == cid)
            for stg, tt, is_cut in [("IN", sh["start"]+0.25, True), ("MID", (sh["start"]+sh["end"])*0.5, False), ("OUT", sh["end"]-0.35, False)]:
                img, info = capture_frame(page, tt, no_fade=True)
                tiles.append({
                    "img": img, "info": info, "color": colors[cid], "is_cut": is_cut,
                    "header": f"{cid} [{stg}]  {sh['camera_move']}",
                    "meta": f"t={tt:4.1f}s | {sh['focal_mm']:.0f}mm",
                    "cap1": f"{sh['name']}（{sh['start']:.0f}-{sh['end']:.0f}s）",
                    "cap2": sh["emotion"],
                })
        build_contact_sheet(tiles, 3, 4, ttl, sub, SHEETS_DIR / fname)


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
    raw_path = CLIPS_DIR / f"seedance_v4_{cl['id']}_{dur}s.mp4"
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
    master_path = CLIPS_DIR / "master_90s_preview_v4.mp4"
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
    print(f"Encoded Master 90s Preview: {master_path} ({total} frames, {total/fps:.1f}s)")


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
