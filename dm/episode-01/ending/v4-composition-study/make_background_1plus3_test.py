#!/usr/bin/env python3
"""Visual proof comparing:
  LEFT  : Naive 1+3 mix (same depth & contrast -> cluttered / noisy behind whale!)
  RIGHT : ★ Depth-Stratified 1+3 Fusion (Far misty giant stalactites + Midground ruined stone arch bridge + Open center sky)
Uses the EXACT same whale, 3-layer floral snowstorm, full moon, and 4 PCs as make_background_4way.py."""

import math
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw

from make_background_4way import (
    fnt, FONT_SANS, FONT_SERIF, FONT_SERIF_B, GOLD,
    wrap_jp, base_cavern_sky, draw_whale_and_snow_and_pcs,
    paint_bg_1_natural_stalactites, paint_bg_3_sunken_aqueduct_nature_fusion,
)

OUT = Path(__file__).resolve().parent / "background_1plus3_fusion_test.png"


def paint_bg_naive_mix(img, horizon=0.63):
    """BAD example: stacking stalactites and stone arches at the SAME depth & contrast."""
    paint_bg_1_natural_stalactites(img, horizon)
    paint_bg_3_sunken_aqueduct_nature_fusion(img, horizon)


def paint_bg_layered_fusion(img, horizon=0.63):
    """★ GOOD example: Depth-Stratified 1+3 Fusion!
      Layer 1 (Far misty deep background, low contrast + soft blur):
        Giant natural stalactites ONLY on outer flanks & deep mist — NEVER behind the whale's center path or Moon!
      Layer 2 (Atmospheric mist band separating Far from Mid):
        Soft cool blue-silver veil so the stone arches pop cleanly in front of the far rocks!
      Layer 3 (Midground hero architecture, crisp silhouette + silver rim + mirror reflection):
        Sunken ruined stone arch bridge with wide broken central span & glowing white Kousetsuka on broken parapets.
    """
    w, h = img.size
    hy = int(h * horizon)

    # --- LAYER 1: Far misty colossal natural stalactites (soft, low contrast, far outer flanks only!) ---
    far = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fd = ImageDraw.Draw(far, "RGBA")
    # Placed far back & only flanking the sides (x=0.07, 0.24, 0.94) + faint distant shadow at 0.62 — leaving center & moon wide open!
    far_cols = [
        (0.06, 0.075, 165),
        (0.24, 0.048, 105),
        (0.61, 0.038, 82),
        (0.95, 0.072, 165),
    ]
    for cx, bw, a in far_cols:
        x = cx * w
        hw = bw * w
        pts = [
            (x - hw * 1.35, 0), (x + hw * 1.25, 0),
            (x + hw * 0.78, hy * 0.28), (x + hw * 0.56, hy * 0.55), (x + hw * 0.72, hy * 0.80),
            (x + hw * 1.15, hy), (x - hw * 1.20, hy),
            (x - hw * 0.70, hy * 0.78), (x - hw * 0.52, hy * 0.52), (x - hw * 0.80, hy * 0.25),
        ]
        fd.polygon(pts, fill=(17, 29, 52, a))
        # Very soft atmospheric scatter on inner flank (gets blurred by sigma=5.5 -> NO harsh line!)
        edge = pts[1:6] if cx < 0.5 else pts[6:10]
        fd.line(edge, fill=(92, 128, 168, int(a * 0.55)), width=5)
        # Subtle soft reflection of distant pillars in water
        fd.polygon([(x - hw * 1.1, hy), (x + hw * 1.1, hy), (x + hw * 0.6, h), (x - hw * 0.6, h)], fill=(11, 20, 38, int(a * 0.38)))

    # Soft ceiling stalactite teeth only on outer 0..32% and 90..100% so sky/moon stays totally pure!
    rng = np.random.default_rng(77)
    for sx in list(np.linspace(0.02, 0.30, 10)) + list(np.linspace(0.90, 0.98, 4)):
        sh = rng.uniform(0.05, 0.14) * h
        sw = rng.uniform(0.014, 0.032) * w
        fd.polygon([(sx * w - sw, 0), (sx * w + sw, 0), (sx * w, sh)], fill=(12, 22, 40, 160))

    # Heavy atmospheric perspective blur on far rock pillars so they NEVER compete with crisp midground arches!
    far_blur = cv2.GaussianBlur(np.asarray(far), (0, 0), sigmaX=5.5, sigmaY=5.5)
    img.alpha_composite(Image.fromarray(far_blur, "RGBA"))

    # --- LAYER 2: Atmospheric depth-separation mist band along the horizon ---
    mist = np.zeros((h, w, 4), dtype=np.float32)
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    band = np.exp(-((yy - (horizon - 0.04)) / 0.14) ** 2)
    mist[:, :, 0] = 64
    mist[:, :, 1] = 96
    mist[:, :, 2] = 136
    mist[:, :, 3] = band * 52.0
    img.alpha_composite(Image.fromarray(np.clip(mist, 0, 255).astype(np.uint8), "RGBA"))

    # --- LAYER 3: Crisp midground sunken ruined stone arch bridge (clearer silhouette & rim than far rocks!) ---
    mid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    md = ImageDraw.Draw(mid, "RGBA")

    def draw_arch_span(x0, x1, deck_y, pw, alpha):
        span_w = x1 - x0
        mid_x = (x0 + x1) // 2
        arch_r = max(12, span_w // 2 - pw // 2)
        arch_cy = min(hy - 8, deck_y + 24 + int(arch_r * 0.85))
        poly = [(x0, hy), (x0, deck_y), (x1, deck_y), (x1, hy), (mid_x + arch_r, hy)]
        for k in range(25):
            ang = math.pi * (k / 24.0)
            ax = mid_x + math.cos(ang) * arch_r
            ay = arch_cy - math.sin(ang) * arch_r
            poly.append((ax, min(hy, ay)))
        poly.append((mid_x - arch_r, hy))
        md.polygon(poly, fill=(22, 37, 62, alpha))
        arch_rim = [(mid_x + math.cos(math.pi * k / 24.0) * arch_r, min(hy, arch_cy - math.sin(math.pi * k / 24.0) * arch_r)) for k in range(25)]
        md.line(arch_rim, fill=(168, 202, 236, int(alpha * 0.78)), width=2)
        md.line([(x0, deck_y), (x1, deck_y)], fill=(186, 214, 242, int(alpha * 0.72)), width=2)
        for fx in np.linspace(x0 + 10, x1 - 10, 6):
            md.ellipse([fx - 3, deck_y - 3, fx + 3, deck_y + 2], fill=(242, 248, 255, int(alpha * 0.88)))
        r_poly = [(px, min(h - 2, hy + (hy - py) * 0.58)) for px, py in poly]
        md.polygon(r_poly, fill=(14, 24, 42, int(alpha * 0.46)))

    arch_y = int(hy * 0.57)
    left_piers = [0.02, 0.14, 0.26, 0.37]
    for i in range(len(left_piers) - 1):
        draw_arch_span(int(left_piers[i] * w), int(left_piers[i + 1] * w), arch_y + i * 5, 22 - i * 3, 215 - i * 22)
    bx = int(0.37 * w)
    md.polygon([(bx - 4, arch_y + 16), (bx + 15, arch_y + 27), (bx + 8, hy), (bx - 6, hy)], fill=(22, 37, 62, 150))

    right_piers = [0.66, 0.79, 0.94]
    for i in range(len(right_piers) - 1):
        draw_arch_span(int(right_piers[i] * w), int(right_piers[i + 1] * w), arch_y + 12 - i * 6, 18 + i * 3, 155 + i * 38)
    rx = int(0.66 * w)
    md.polygon([(rx + 4, arch_y + 16), (rx - 15, arch_y + 28), (rx - 8, hy), (rx + 6, hy)], fill=(22, 37, 62, 148))

    # Very subtle 1px softness only so arches remain crisp in front of soft far rock pillars
    mid_soft = cv2.GaussianBlur(np.asarray(mid), (0, 0), sigmaX=0.9, sigmaY=0.9)
    img.alpha_composite(Image.fromarray(mid_soft, "RGBA"))


def main():
    W, H = 2400, 920
    board = Image.new("RGB", (W, H), (10, 14, 24))
    d = ImageDraw.Draw(board)

    d.text((48, 24), "『案1（巨大岩柱）＋ 案3（崩れた石造アーチ橋）』両立検証：ごちゃつくか？ 映画級に化けるか？", font=fnt(FONT_SERIF_B, 33), fill=(238, 244, 252))
    d.text((48, 70), "結論：同じ奥行き・同じ濃さで混ぜると確実にごちゃつく（左）。しかし『遠近レイヤー分離＋空気遠近の霧』を徹底すれば、むしろ案3単体を超える100点になる（右）！", font=fnt(FONT_SANS, 18), fill=GOLD)

    pw, ph = 1120, 500
    coords = [(48, 142), (1232, 142)]

    specs = [
        ("× NG例｜同じ奥行き・同じ輪郭の強さで 1＋3 を混ぜた場合", (235, 130, 130), paint_bg_naive_mix,
         "【なぜごちゃつくのか】\n"
         "・岩柱のリム光とアーチ橋の輪郭線が『同じ濃さ・同じピント』で重なり合い、線が大渋滞する。\n"
         "・白鯨と大花吹雪の背後にノイズが増えて、せっかくの『静謐さと神話感』が削がれる。\n"
         "・AI動画生成（Seedance）でも、同じ奥行きに岩と石橋が重なると境界が溶けて破綻しやすい。"),
        ("★ 正解例（100点・映画級）｜遠近レイヤー分離による『1＋3 融合』", GOLD, paint_bg_layered_fusion,
         "【なぜごちゃつかず、むしろ案3単体より化けるのか】\n"
         "・最遠景（霧の奥・輪郭ボカシ）：左右端のみに巨大な天然鍾乳石柱を沈め、中央（白鯨と満月の抜け）は完全無柱！\n"
         "・中景（クッキリ＋銀リム光）：崩れた石造アーチ橋＋苔上の開花。霧のベールが岩柱と橋を完全に分離する。\n"
         "・動画で絶大な効果：カメラ並走時に『中景の橋（速い）』と『遠景の岩柱（遅い）』で二重パララックスが生まれ、地下大空洞の圧倒的スケール＋大自然が人工物を飲み込んだ歴史ロマンが同時に成立する！"),
    ]

    for idx, (title, col, bg_fn, desc) in enumerate(specs):
        x0, y0 = coords[idx]
        is_good = (idx == 1)
        d.rounded_rectangle([x0 - 3, y0 - 34, x0 + pw + 3, y0 + ph + 240], radius=12, fill=(16, 24, 38), outline=col, width=3 if is_good else 2)
        d.text((x0 + 12, y0 - 28), title, font=fnt(FONT_SANS, 19), fill=col)

        panel = base_cavern_sky(pw, ph)
        bg_fn(panel)
        draw_whale_and_snow_and_pcs(panel)
        board.paste(panel.convert("RGB"), (x0, y0))

        f_d = fnt(FONT_SERIF, 16)
        d.multiline_text((x0 + 14, y0 + ph + 14), wrap_jp(d, desc, f_d, pw - 28), font=f_d, fill=(220, 232, 246), spacing=8)

    board.save(OUT)
    print(f"Saved 1+3 fusion visual test: {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
