#!/usr/bin/env python3
"""Generate an apples-to-apples 4-way 5-value chiaroscuro visual comparison board
for the subterranean lake background of Episode 1 Ending 'Kousetsuka':
  1) Natural Giant Stalactite/Limestone Rock Pillars
  2) Grand Ancient Temple Ruins (Siofra-style)
  3) ★ Sunken Old-Era Ruined Stone Aqueduct / Broken Pilgrim Arch Bridges fused with Nature
  4) Pure Minimal Void & Mirror Lake (No Pillars)
Every panel uses the EXACT same whale, space-filling floral snowstorm, 4 PCs + lantern,
and moonlit fissure so the author can compare PURE VISUAL IMPACT fairly!"""

import math
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "background_design_4way_comparison.png"
FONT_SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
FONT_SERIF_B = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"


def fnt(path, size):
    return ImageFont.truetype(path, size)


V1_BLACK = np.array([9, 14, 24], dtype=np.float32)
V2_DARK  = np.array([22, 36, 60], dtype=np.float32)
V3_MID   = np.array([52, 76, 108], dtype=np.float32)
V4_LIGHT = np.array([150, 182, 214], dtype=np.float32)
V5_WHITE = np.array([244, 248, 254], dtype=np.float32)
GOLD = (248, 218, 134)
TEAL = (108, 220, 214)


KINSOKU_HEAD = set("、。」』）)】・：；！？")


def wrap_jp(d, text, font, max_w):
    out = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            if d.textlength(cur + ch, font=font) > max_w and cur:
                if ch in KINSOKU_HEAD:
                    cur += ch
                    out.append(cur)
                    cur = ""
                else:
                    out.append(cur)
                    cur = ch
            else:
                cur += ch
        if cur:
            out.append(cur)
    return "\n".join(out)


def base_cavern_sky(w, h, horizon=0.63):
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    img = np.zeros((h, w, 3), dtype=np.float32)
    sky_t = np.clip(y / horizon, 0, 1)
    for c in range(3):
        img[:, :, c] = V1_BLACK[c] * (1 - sky_t) + V2_DARK[c] * 1.15 * sky_t
    hy = int(h * horizon)
    lt = np.linspace(0, 1, h - hy, dtype=np.float32)[:, None]
    for c in range(3):
        img[hy:, :, c] = V2_DARK[c] * 0.85 * (1 - lt) + V1_BLACK[c] * lt
    # Distant misty moonlight shaft from upper-right fissure
    mask = np.zeros((h, w), dtype=np.float32)
    pts = np.array([[int(0.75 * w), 0], [int(0.84 * w), 0], [int(0.80 * w), int(0.72 * h)], [int(0.62 * w), int(0.72 * h)]], dtype=np.int32)
    cv2.fillPoly(mask, [pts], 1.0)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=w * 0.045, sigmaY=h * 0.055)
    img += mask[:, :, None] * V4_LIGHT[None, None, :] * 0.36
    # Full Moon glow in upper-right fissure
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d2 = ((xx / w - 0.80) / 0.055) ** 2 + ((yy / h - 0.09) / 0.085) ** 2
    img += np.exp(-d2 * 1.9)[:, :, None] * V5_WHITE[None, None, :] * 0.85
    # Whale ambient light pool in center-left sky & lake reflection
    d2w = ((xx / w - 0.48) / 0.26) ** 2 + ((yy / h - 0.38) / 0.19) ** 2
    img += np.exp(-d2w * 1.6)[:, :, None] * V4_LIGHT[None, None, :] * 0.28
    d2r = ((xx / w - 0.48) / 0.24) ** 2 + ((yy / h - 0.84) / 0.12) ** 2
    img += np.exp(-d2r * 1.8)[:, :, None] * V4_LIGHT[None, None, :] * 0.18
    # Subtle vignette
    vig = 1.0 - 0.26 * ((x - 0.5) ** 2 * 2.0 + (y - 0.48) ** 2 * 1.3)
    img *= np.clip(vig[:, :, None], 0.58, 1.05)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")


def draw_whale_and_snow_and_pcs(pil_img, horizon=0.63):
    """Draw identical hero whale (gentle 40-deg joyful roll/glide!), space-filling 3-layer floral snowstorm,
    mirror lake whale twin, and 4 tiny backlit silhouettes + warm lantern on EVERY panel."""
    w, h = pil_img.size
    hy = int(h * horizon)

    # 1. Mirrored whale twin in dark lake
    def draw_whale(cx, cy, lf, ang, glow, flip=False, alpha=255):
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer, "RGBA")
        L = lf * w
        r = math.radians(ang)
        ca, sa = math.cos(r), math.sin(r)
        sgn = -1.0 if flip else 1.0

        def pt(lx, ly):
            return (cx * w + (lx * ca - ly * sa) * L * 0.5, cy * h + (lx * sa + ly * ca) * L * 0.5)

        top = [(1.0, 0.02), (0.85, -0.15), (0.55, -0.21), (0.15, -0.18), (-0.25, -0.11),
               (-0.65, -0.05), (-0.88, -0.04), (-1.03, -0.20), (-0.96, -0.02), (-1.04, 0.14), (-0.86, 0.03)]
        bot = [(-0.62, 0.06), (-0.22, 0.12), (0.20, 0.18), (0.62, 0.17), (0.90, 0.11), (1.0, 0.02)]
        col = (int(28 + glow * 206), int(44 + glow * 196), int(68 + glow * 180), alpha)
        d.polygon([pt(x, y * sgn) for x, y in (top + bot)], fill=col)
        fin = [pt(0.32, 0.08 * sgn), pt(0.04, 0.34 * sgn), pt(-0.09, 0.31 * sgn), pt(0.14, 0.09 * sgn)]
        d.polygon(fin, fill=(max(0, col[0] - 20), max(0, col[1] - 16), max(0, col[2] - 8), alpha))
        d.line([pt(x, y * sgn) for x, y in top[:7]], fill=(248, 252, 255, min(255, int(alpha * 0.9))), width=3)
        pil_img.alpha_composite(layer)

    draw_whale(0.49, 0.85, 0.34, 8, glow=0.52, flip=True, alpha=118)
    draw_whale(0.49, 0.37, 0.34, -8, glow=0.94, flip=False, alpha=255)

    # 2. Space-filling 3-layer floral snowstorm (far mist dots -> mid luminous swirl -> few soft bokeh fg petals)
    snow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(snow, "RGBA")
    rng = np.random.default_rng(2026)
    # Far + mid space-filling floral snow (softly denser around whale's 65m light sphere, fading into outer dark!)
    for _ in range(210):
        px = rng.uniform(0.02, 0.98) * w
        py = rng.uniform(0.05, 0.94) * h
        dist_w = math.hypot((px / w - 0.49) / 0.38, (py / h - 0.44) / 0.38)
        bright = max(0.28, 1.0 - dist_w * 0.55)
        sz = rng.uniform(1.4, 3.6) * (0.75 + 0.45 * bright)
        sd.ellipse([px - sz, py - sz * 0.55, px + sz, py + sz * 0.55], fill=(244, 248, 254, int(190 * bright)))
        if rng.random() < 0.55:
            sd.ellipse([px - 1.2, py - 1.2, px + 1.2, py + 1.2], fill=(250, 224, 142, int(215 * bright)))
    pil_img.alpha_composite(snow)

    # Few large softly blurred foreground petals for 3-layer parallax!
    fg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fg, "RGBA")
    for fx, fy, fs in [(0.08, 0.24, 9), (0.91, 0.36, 11), (0.84, 0.78, 8), (0.28, 0.14, 7), (0.68, 0.60, 8)]:
        fd.ellipse([fx * w - fs, fy * h - fs * 0.5, fx * w + fs, fy * h + fs * 0.5], fill=(246, 250, 255, 165))
    fg_blur = cv2.GaussianBlur(np.asarray(fg), (0, 0), sigmaX=4, sigmaY=4)
    pil_img.alpha_composite(Image.fromarray(fg_blur, "RGBA"))

    # 3. Foreground shore ledge + 4 tiny backlit PCs + warm lantern spark (lower-left scale anchor!)
    fg_shore = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shd = ImageDraw.Draw(fg_shore, "RGBA")
    shd.polygon([(0, h), (int(w * 0.34), h), (int(w * 0.26), int(h * 0.87)), (0, int(h * 0.84))], fill=(10, 16, 28, 255))
    # Subtle white 5-petal flowers glowing softly on foreground rock edge
    for bx, by in [(0.03, 0.87), (0.07, 0.89), (0.24, 0.90), (0.28, 0.93), (0.19, 0.89)]:
        shd.ellipse([bx * w - 4, by * h - 2, bx * w + 4, by * h + 2], fill=(238, 245, 252, 200))
    # Lantern glow
    lx, ly = int(0.215 * w), int(0.89 * h)
    lg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(lg, "RGBA").ellipse([lx - 18, ly - 18, lx + 18, ly + 18], fill=(252, 208, 112, 130))
    pil_img.alpha_composite(fg_shore)
    pil_img.alpha_composite(Image.fromarray(cv2.GaussianBlur(np.asarray(lg), (0, 0), sigmaX=10, sigmaY=10), "RGBA"))

    pcs = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pcs, "RGBA")
    pd.ellipse([lx - 3, ly - 3, lx + 3, ly + 3], fill=(255, 242, 198, 255))
    for ox, hh in [(-0.042, 0.080), (-0.022, 0.074), (-0.002, 0.083), (0.018, 0.076)]:
        cx, cy = int((0.155 + ox) * w), int(0.91 * h)
        ph, pw = int(hh * h), int(0.011 * w)
        pd.polygon([(cx - pw, cy), (cx + pw, cy), (cx + int(pw * 0.7), cy - int(ph * 0.74)), (cx - int(pw * 0.7), cy - int(ph * 0.74))], fill=(6, 10, 18, 255))
        pd.ellipse([cx - 4, cy - ph, cx + 4, cy - ph + 8], fill=(6, 10, 18, 255))
    pil_img.alpha_composite(pcs)


# --- Background Painters (Drawn BEFORE Whale & Snow!) ---
def paint_bg_1_natural_stalactites(img, horizon=0.63):
    w, h = img.size
    hy = int(h * horizon)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    # 4 natural tapered organic stalactite-stalagmite rock columns placed cleanly clear of the moon!
    cols = [(0.10, 0.062, 205), (0.26, 0.038, 138), (0.58, 0.036, 128), (0.94, 0.056, 210)]
    for cx, bw, a in cols:
        x = cx * w
        hw = bw * w
        pts = [
            (x - hw * 1.25, 0), (x + hw * 1.15, 0),
            (x + hw * 0.72, hy * 0.30), (x + hw * 0.54, hy * 0.55), (x + hw * 0.68, hy * 0.78),
            (x + hw * 1.10, hy), (x - hw * 1.15, hy),
            (x - hw * 0.66, hy * 0.76), (x - hw * 0.50, hy * 0.52), (x - hw * 0.76, hy * 0.26),
        ]
        d.polygon(pts, fill=(18, 30, 50, a))
        if cx < 0.49:
            d.line(pts[1:6], fill=(138, 174, 210, int(a * 0.55)), width=2)
        else:
            d.line(pts[6:10], fill=(138, 174, 210, int(a * 0.55)), width=2)
        d.polygon([(x - hw * 1.1, hy), (x + hw * 1.1, hy), (x + hw * 0.65, h), (x - hw * 0.65, h)], fill=(12, 22, 38, int(a * 0.42)))
    rng = np.random.default_rng(11)
    for sx in np.linspace(0.02, 0.96, 26):
        if 0.71 <= sx <= 0.89:
            continue
        sh = rng.uniform(0.04, 0.13) * h
        sw = rng.uniform(0.012, 0.030) * w
        d.polygon([(sx * w - sw, 0), (sx * w + sw, 0), (sx * w, sh)], fill=(14, 24, 42, 185))
    img.alpha_composite(layer)


def paint_bg_2_ancient_temple_ruins(img, horizon=0.63):
    w, h = img.size
    hy = int(h * horizon)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    col_xs = [0.09, 0.21, 0.33, 0.66, 0.78, 0.91]
    for cx in col_xs:
        x = cx * w
        cw = (0.028 if abs(cx - 0.5) > 0.32 else 0.020) * w
        top_y = int(hy * (0.14 if cx not in (0.33, 0.66) else 0.32))
        a = 215 if abs(cx - 0.5) > 0.32 else 145
        d.rectangle([x - cw, top_y, x + cw, hy], fill=(20, 34, 56, a))
        d.rectangle([x - cw * 1.35, hy - 14, x + cw * 1.35, hy], fill=(24, 40, 64, a))
        if cx not in (0.33, 0.66):
            d.rectangle([x - cw * 1.35, top_y - 10, x + cw * 1.35, top_y + 4], fill=(28, 46, 74, a))
        rim_x = x + cw if cx < 0.5 else x - cw
        d.line([(rim_x, top_y), (rim_x, hy)], fill=(170, 202, 232, int(a * 0.72)), width=2)
        d.rectangle([x - cw, hy, x + cw, min(h, hy + int((hy - top_y) * 0.55))], fill=(14, 24, 42, int(a * 0.45)))
    d.rectangle([int(0.05 * w), int(hy * 0.10), int(0.25 * w), int(hy * 0.16)], fill=(22, 36, 58, 210))
    d.rectangle([int(0.75 * w), int(hy * 0.10), int(0.96 * w), int(hy * 0.16)], fill=(22, 36, 58, 210))
    img.alpha_composite(layer)


def paint_bg_3_sunken_aqueduct_nature_fusion(img, horizon=0.63):
    """★ RECOMMENDED: Sunken Old-Kingdom Ruined Stone Aqueduct / Broken Pilgrim Arch Bridge
    with solid weathered masonry spandrels, mossy blooming flowers on broken ledges, and mirror reflection!"""
    w, h = img.size
    hy = int(h * horizon)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")

    # Subtle organic cavern ceiling rock framing far corners (leaving moon fissure clean!)
    rock_l = [(0, 0), (int(w * 0.18), 0), (int(w * 0.12), int(h * 0.08)), (int(w * 0.07), int(h * 0.17)),
              (int(w * 0.04), int(h * 0.28)), (0, int(h * 0.42))]
    rock_r = [(w, 0), (int(w * 0.90), 0), (int(w * 0.93), int(h * 0.09)), (int(w * 0.96), int(h * 0.21)),
              (w, int(h * 0.38))]
    d.polygon(rock_l, fill=(10, 17, 30, 185))
    d.polygon(rock_r, fill=(10, 17, 30, 185))

    def draw_arch_span(x0, x1, deck_y, pw, alpha):
        # Solid masonry bridge mask with true semicircular arch cutout!
        span_w = x1 - x0
        mid_x = (x0 + x1) // 2
        arch_r = max(12, span_w // 2 - pw // 2)
        arch_cy = min(hy - 8, deck_y + 24 + int(arch_r * 0.85))
        # Draw solid masonry polygon with arch cutout approximation (smooth 24-pt arch!)
        poly = [(x0, hy), (x0, deck_y), (x1, deck_y), (x1, hy), (mid_x + arch_r, hy)]
        for k in range(25):
            ang = math.pi * (k / 24.0)
            ax = mid_x + math.cos(ang) * arch_r
            ay = arch_cy - math.sin(ang) * arch_r
            poly.append((ax, min(hy, ay)))
        poly.append((mid_x - arch_r, hy))
        d.polygon(poly, fill=(20, 34, 56, alpha))
        # Silver moonlit rim along arch inner curve & broken parapet top
        arch_rim = [(mid_x + math.cos(math.pi * k / 24.0) * arch_r, min(hy, arch_cy - math.sin(math.pi * k / 24.0) * arch_r)) for k in range(25)]
        d.line(arch_rim, fill=(154, 188, 224, int(alpha * 0.72)), width=2)
        d.line([(x0, deck_y), (x1, deck_y)], fill=(176, 206, 236, int(alpha * 0.65)), width=2)
        # Blooming white Kousetsuka clusters on mossy parapet!
        for fx in np.linspace(x0 + 10, x1 - 10, 6):
            d.ellipse([fx - 3, deck_y - 3, fx + 3, deck_y + 2], fill=(238, 246, 254, int(alpha * 0.85)))
        # Mirrored reflection of solid masonry arch in glassy dark lake!
        r_poly = [(px, min(h - 2, hy + (hy - py) * 0.58)) for px, py in poly]
        d.polygon(r_poly, fill=(14, 24, 42, int(alpha * 0.45)))

    arch_y = int(hy * 0.56)
    left_piers = [0.02, 0.14, 0.26, 0.37]
    for i in range(len(left_piers) - 1):
        draw_arch_span(int(left_piers[i] * w), int(left_piers[i + 1] * w), arch_y + i * 5, 22 - i * 3, 195 - i * 24)
    # Jagged broken masonry edge at central breach (whale sails effortlessly over the collapse!)
    bx = int(0.37 * w)
    d.polygon([(bx - 4, arch_y + 16), (bx + 14, arch_y + 26), (bx + 8, hy), (bx - 6, hy)], fill=(20, 34, 56, 130))

    right_piers = [0.66, 0.79, 0.94]
    for i in range(len(right_piers) - 1):
        draw_arch_span(int(right_piers[i] * w), int(right_piers[i + 1] * w), arch_y + 12 - i * 6, 18 + i * 3, 140 + i * 36)
    rx = int(0.66 * w)
    d.polygon([(rx + 4, arch_y + 16), (rx - 14, arch_y + 28), (rx - 8, hy), (rx + 6, hy)], fill=(20, 34, 56, 128))

    blur_ruin = cv2.GaussianBlur(np.asarray(layer), (0, 0), sigmaX=1.2, sigmaY=1.2)
    img.alpha_composite(Image.fromarray(blur_ruin, "RGBA"))


def paint_bg_4_pure_void(img, horizon=0.63):
    # Only a very faint distant rocky shoreline shadow on the horizon; pure negative space
    w, h = img.size
    hy = int(h * horizon)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    d.line([(0, hy), (w, hy)], fill=(64, 90, 122, 75), width=2)
    img.alpha_composite(layer)


def main():
    W, H = 2400, 1440
    board = Image.new("RGB", (W, H), (10, 14, 24))
    d = ImageDraw.Draw(board)

    d.text((48, 26), "『空に降る雪』背景美術 4案ガチ比較：ここで「誠に映える絵」は何か？", font=fnt(FONT_SERIF_B, 34), fill=(238, 244, 252))
    d.text((48, 72), "白鯨・大花吹雪・4人のシルエット・満月を完全に同一条件に固定し、「背景の違いだけで絵の格がどう変わるか」を公平に比較", font=fnt(FONT_SANS, 18), fill=GOLD)

    pw, ph = 1120, 460
    coords = [(48, 140), (1232, 140), (48, 796), (1232, 796)]

    specs = [
        ("案1｜天然の巨大鍾乳石柱（自然洞窟型）", (152, 192, 232), paint_bg_1_natural_stalactites,
         "【映えの評価：78点】奥行きと地下感は出るが、岩柱の有機的シルエットが白鯨と似るため対比がやや弱い。暗部では岩壁と溶け合い『普通の暗い洞窟』に寄りやすい。\n"
         "【世界設定との整合】◎ 既存設定どおり（変更不要）。"),
        ("案2｜壮大な超古代神殿の列柱（シーフラ河型）", (152, 192, 232), paint_bg_2_ancient_temple_ruins,
         "【映えの評価：90点】人工の直線・列柱と、有機的な白鯨・花雪の対比が強烈で一発で息を呑む『映え』になる。\n"
         "【世界設定との整合】△ 正本（world/01_世界の骨格.md）は『独立した滅亡超古代文明は設定しない』方針。神殿を置くと第一話の主題から遺跡謎解きへ意識が逸れる懸念あり。"),
        ("★ 案3（最有力・誠の映え）｜水没した旧時代の崩れた石造アーチ橋 × 大自然の融合", GOLD, paint_bg_3_sunken_aqueduct_nature_fusion,
         "【映えの評価：98点】崩れた石造アーチの繊細な幾何学曲線が鏡面湖に上下対称に映り、その崩落口を純白の白鯨が花雪と共に悠々くぐり抜ける『ラピュタ×ワンダと巨像』級の鳥肌構図！アーチの苔の上からも空雪花が一斉開花する。\n"
         "【世界設定との整合】◎ 設定変更すら不要！『大断裂（約270年前）で沈んだ旧王国の石橋』または『星路教会の失われた古い巡礼路』として正本と100%合致し、「まだこの先に冒険がある」という第一話のゴールを最高に強める！"),
        ("案4｜柱なし・無限の暗黒鏡面と月光のみ（ミニマル絵画型）", (152, 192, 232), paint_bg_4_pure_void,
         "【映えの評価：80点】最も静謐で白鯨と花吹雪に100%集中できるが、カメラが並走・旋回したときの立体視差（スピード感・地下空間の広さ）が出にくく、再び『暗い宇宙』に見えやすいリスクが残る。\n"
         "【世界設定との整合】◎ 既存設定どおり（変更不要）。"),
    ]

    for idx, (title, col, bg_fn, desc) in enumerate(specs):
        x0, y0 = coords[idx]
        is_best = (idx == 2)
        d.rounded_rectangle([x0 - 3, y0 - 34, x0 + pw + 3, y0 + ph + 144], radius=12, fill=(16, 24, 38), outline=col, width=3 if is_best else 2)
        d.text((x0 + 12, y0 - 28), title, font=fnt(FONT_SANS, 19), fill=col)

        panel = base_cavern_sky(pw, ph)
        bg_fn(panel)
        draw_whale_and_snow_and_pcs(panel)
        board.paste(panel.convert("RGB"), (x0, y0))

        f_d = fnt(FONT_SERIF, 15)
        d.multiline_text((x0 + 14, y0 + ph + 10), wrap_jp(d, desc, f_d, pw - 28), font=f_d, fill=(216, 228, 242), spacing=7)

    board.save(OUT)
    print(f"Saved 4-way background comparison: {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
