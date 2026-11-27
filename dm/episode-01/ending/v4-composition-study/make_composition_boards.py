#!/usr/bin/env python3
"""Generate two museum-grade 5-value chiaroscuro composition study boards for
Episode 1 Ending v4.0 (illustration-composition + shot-composition + Sakurai-Skills):
  1) composition_board_A_tension.png   — Sustaining Attack/Collision Dread (C3 -> C4)
  2) composition_board_B_swimming.png  — Vast Abyssal Space, Whale Swimming & Petal Wake Choreography (C6 -> C7)
"""

import math
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent
FONT_SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
FONT_SERIF_B = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"


def fnt(path, size):
    return ImageFont.truetype(path, size)


# 5-Value Chiaroscuro Palette (Deep Night Indigo -> Silver Moonlight + Warm Lantern Accent)
V1_BLACK = np.array([10, 15, 26], dtype=np.float32)      # Value 1: Deepest silhouette
V2_DARK  = np.array([24, 38, 62], dtype=np.float32)      # Value 2: Cavern / dark lake shadow
V3_MID   = np.array([58, 82, 114], dtype=np.float32)     # Value 3: Atmospheric cavern mist
V4_LIGHT = np.array([148, 178, 208], dtype=np.float32)   # Value 4: Moonlight mist / pearl flank
V5_WHITE = np.array([242, 247, 252], dtype=np.float32)   # Value 5: Pure moonlight / foam / petals
ACCENT_GOLD = (248, 218, 134)
ACCENT_RED  = (238, 108, 108)
ACCENT_TEAL = (108, 218, 210)


def make_gradient_canvas(w, h, top_col, bot_col, horizon_y=0.62, lake_col=None):
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    img = np.zeros((h, w, 3), dtype=np.float32)
    sky_t = np.clip(y / max(0.01, horizon_y), 0, 1)
    for c in range(3):
        img[:, :, c] = top_col[c] * (1 - sky_t) + bot_col[c] * sky_t
    if lake_col is not None:
        hy = int(h * horizon_y)
        lt = np.linspace(0, 1, h - hy, dtype=np.float32)[:, None]
        for c in range(3):
            img[hy:, :, c] = bot_col[c] * 0.72 * (1 - lt) + lake_col[c] * lt
    # Subtle atmospheric vignette
    vig = 1.0 - 0.30 * ((x - 0.5) ** 2 * 2.2 + (y - 0.45) ** 2 * 1.4)
    img *= np.clip(vig[:, :, None], 0.55, 1.05)
    return img


def add_light_beam(img, x0, y0, x1, y1, width0, width1, color, strength=0.45):
    h, w, _ = img.shape
    mask = np.zeros((h, w), dtype=np.float32)
    pts = np.array([
        [int((x0 - width0 / 2) * w), int(y0 * h)],
        [int((x0 + width0 / 2) * w), int(y0 * h)],
        [int((x1 + width1 / 2) * w), int(y1 * h)],
        [int((x1 - width1 / 2) * w), int(y1 * h)],
    ], dtype=np.int32)
    cv2.fillPoly(mask, [pts], 1.0)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=w * 0.045, sigmaY=h * 0.06)
    img += mask[:, :, None] * color[None, None, :] * strength


def add_radial_glow(img, cx, cy, rx, ry, color, strength=0.7):
    h, w, _ = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d2 = ((xx / w - cx) / rx) ** 2 + ((yy / h - cy) / ry) ** 2
    g = np.exp(-d2 * 1.8) * strength
    img += g[:, :, None] * color[None, None, :]


def wrap_jp(d, text, font, max_w):
    """Wrap Japanese/mixed paragraphs cleanly to max_w pixels."""
    out_lines = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            test = cur + ch
            if d.textlength(test, font=font) > max_w and cur:
                out_lines.append(cur)
                cur = ch
            else:
                cur = test
        if cur:
            out_lines.append(cur)
    return "\n".join(out_lines)


def draw_4_pcs_and_lantern(pil_img, base_x, base_y, scale=1.0, show_lantern=True):
    """Draw 4 anonymous backlit adventurer silhouettes + delicate warm lantern spark."""
    w, h = pil_img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    offsets = [-0.044, -0.016, 0.014, 0.042]
    heights = [0.105, 0.095, 0.108, 0.098]
    if show_lantern:
        lx = int((base_x + 0.068 * scale) * w)
        ly = int((base_y - 0.016 * scale) * h)
        # Soft radial warm glow halo (properly alpha-composited!)
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow, "RGBA")
        r_outer = max(8, int(24 * scale))
        gd.ellipse([lx - r_outer, ly - r_outer, lx + r_outer, ly + r_outer], fill=(252, 206, 108, 125))
        glow_np = cv2.GaussianBlur(np.asarray(glow), (0, 0), sigmaX=max(4, 12 * scale), sigmaY=max(4, 12 * scale))
        pil_img.alpha_composite(Image.fromarray(glow_np, "RGBA"))
        # Crisp tiny 4px lantern core
        r_core = max(3, int(4.5 * scale))
        d.ellipse([lx - r_core, ly - r_core, lx + r_core, ly + r_core], fill=(255, 240, 192, 255))
    for dx, hh in zip(offsets, heights):
        cx = int((base_x + dx * scale) * w)
        cy = int(base_y * h)
        ph = int(hh * scale * h)
        pw = int(0.018 * scale * w)
        d.polygon([
            (cx - pw, cy), (cx + pw, cy),
            (cx + int(pw * 0.72), cy - int(ph * 0.74)),
            (cx - int(pw * 0.72), cy - int(ph * 0.74)),
        ], fill=(6, 10, 18, 255))
        hr = max(4, int(pw * 0.52))
        d.ellipse([cx - hr, cy - ph, cx + hr, cy - ph + hr * 2], fill=(6, 10, 18, 255))
        # Subtle moonlight shoulder rim
        d.line([(cx - int(pw * 0.7), cy - int(ph * 0.74)), (cx + int(pw * 0.7), cy - int(ph * 0.74))], fill=(195, 220, 245, 165), width=2)
    pil_img.alpha_composite(layer)


def draw_whale_organic_side(pil_img, cx, cy, length_frac, angle_deg, glow=0.85, flip=False, alpha=255, show_eye=False):
    w, h = pil_img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    L = length_frac * w
    rad = math.radians(angle_deg)
    ca, sa = math.cos(rad), math.sin(rad)
    sgn = -1.0 if flip else 1.0

    def pt(lx, ly):
        x = cx * w + (lx * ca - ly * sa) * L * 0.5
        y = cy * h + (lx * sa + ly * ca) * L * 0.5
        return (x, y)

    top_curve = [
        (1.00, 0.02), (0.85, -0.15), (0.55, -0.21), (0.15, -0.18),
        (-0.25, -0.11), (-0.65, -0.05), (-0.88, -0.04),
        (-1.02, -0.20), (-0.96, -0.02), (-1.04, 0.14), (-0.86, 0.03),
    ]
    bot_curve = [
        (-0.62, 0.06), (-0.22, 0.12), (0.20, 0.18), (0.62, 0.17), (0.90, 0.11), (1.00, 0.02)
    ]
    body_pts = [pt(x, y * sgn) for x, y in (top_curve + bot_curve)]
    base_col = (int(24 + glow * 204), int(38 + glow * 198), int(62 + glow * 184), alpha)
    d.polygon(body_pts, fill=base_col)

    fin = [pt(0.32, 0.08 * sgn), pt(0.05, 0.32 * sgn), pt(-0.08, 0.30 * sgn), pt(0.14, 0.09 * sgn)]
    fin_col = (max(0, base_col[0] - 22), max(0, base_col[1] - 18), max(0, base_col[2] - 10), alpha)
    d.polygon(fin, fill=fin_col)

    rim_pts = [pt(x, y * sgn) for x, y in top_curve[:7]]
    d.line(rim_pts, fill=(246, 250, 255, min(255, int(alpha * (0.45 + 0.55 * glow)))), width=max(2, int(L * 0.012)))

    for g in range(3):
        off = 0.08 + g * 0.03
        g_pts = [pt(0.84 - g * 0.05, off * sgn), pt(0.45, (off + 0.03) * sgn), pt(0.10, (off + 0.01) * sgn)]
        d.line(g_pts, fill=(110, 140, 175, int(alpha * 0.35)), width=1)

    if show_eye:
        ex, ey = pt(0.74, 0.03 * sgn)
        d.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], fill=(8, 12, 20, alpha))
        d.ellipse([ex - 1, ey - 2, ex + 2, ey + 1], fill=(245, 250, 255, alpha))

    pil_img.alpha_composite(layer)


def draw_head_on_whale(pil_img, cx, cy, width_frac, dark=True):
    """Colossal HEAD-ON looming whale brow, painterly silver spray curtains & sweeping dark flanks."""
    w, h = pil_img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    rw = width_frac * w * 0.5
    rh = rw * 0.62
    x0, y0 = cx * w, cy * h

    # Soft misty spray cloud exploding left & right from breaching water surface!
    spray = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(spray, "RGBA")
    for side in (-1, 1):
        sd.ellipse([x0 + side * rw * 0.35 - rw * 0.55, y0 + rh * 0.32, x0 + side * rw * 0.35 + rw * 0.55, y0 + rh * 1.15], fill=(165, 198, 228, 85))
    spray_np = cv2.GaussianBlur(np.asarray(spray), (0, 0), sigmaX=18, sigmaY=14)
    pil_img.alpha_composite(Image.fromarray(spray_np, "RGBA"))

    # Massive sweeping pectoral wings left & right
    l_fin = [(x0 - rw * 0.68, y0 + rh * 0.14), (x0 - rw * 1.48, y0 + rh * 0.52), (x0 - rw * 1.32, y0 + rh * 0.72), (x0 - rw * 0.52, y0 + rh * 0.44)]
    r_fin = [(x0 + rw * 0.68, y0 + rh * 0.14), (x0 + rw * 1.48, y0 + rh * 0.52), (x0 + rw * 1.32, y0 + rh * 0.72), (x0 + rw * 0.52, y0 + rh * 0.44)]
    d.polygon(l_fin, fill=(14, 22, 38, 255))
    d.polygon(r_fin, fill=(14, 22, 38, 255))

    # Colossal dark head dome (5-value tonal shading: dark core + subtle mid-slate upper brow + silver rim)
    d.ellipse([x0 - rw, y0 - rh, x0 + rw, y0 + rh * 0.92], fill=(16, 26, 44, 255))
    d.ellipse([x0 - rw * 0.88, y0 - rh * 0.94, x0 + rw * 0.88, y0 + rh * 0.25], fill=(28, 44, 68, 175))
    d.arc([x0 - rw * 0.96, y0 - rh * 0.98, x0 + rw * 0.96, y0 + rh * 0.85], start=200, end=340, fill=(224, 238, 252, 235), width=4)
    # Gentle ventral grooves under lower jaw
    for i in range(-3, 4):
        gx = x0 + i * rw * 0.18
        d.line([(gx, y0 + rh * 0.42), (gx + i * rw * 0.04, y0 + rh * 0.88)], fill=(58, 84, 118, 150), width=2)

    # Cascading silver water curtains falling off jaw flanks
    for side in (-1, 1):
        for k in range(6):
            sx = x0 + side * rw * (0.48 + k * 0.11)
            d.line([(sx, y0 + rh * (0.28 + k * 0.04)), (sx + side * 10, y0 + rh * 1.10)], fill=(208, 230, 248, 130 - k * 14), width=2)

    for side in (-1, 1):
        ex, ey = x0 + side * rw * 0.78, y0 + rh * 0.18
        d.ellipse([ex - 3, ey - 3, ex + 3, ey + 3], fill=(240, 248, 255, 200))

    pil_img.alpha_composite(layer)


def draw_wake_ribbon(pil_img, pts_norm, width_px=26, seed=42):
    """Draw a soft glowing luminous ribbon of white petals + champagne-gold seeds carved by the whale's wake!"""
    w, h = pil_img.size
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer, "RGBA")
    px_pts = [(p[0] * w, p[1] * h) for p in pts_norm]
    gd.line(px_pts, fill=(195, 224, 248, 82), width=int(width_px * 1.65), joint="curve")
    gd.line(px_pts, fill=(246, 224, 152, 58), width=int(width_px * 0.85), joint="curve")
    blur_np = cv2.GaussianBlur(np.asarray(glow_layer), (0, 0), sigmaX=12, sigmaY=10)
    pil_img.alpha_composite(Image.fromarray(blur_np, "RGBA"))

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    rng = np.random.default_rng(seed)
    for i in range(len(px_pts) - 1):
        x0, y0 = px_pts[i]
        x1, y1 = px_pts[i + 1]
        for _ in range(20):
            u = rng.random()
            px = x0 + (x1 - x0) * u + rng.normal(0, width_px * 0.50)
            py = y0 + (y1 - y0) * u + rng.normal(0, width_px * 0.40)
            sz = rng.uniform(1.8, 4.6)
            d.ellipse([px - sz, py - sz * 0.55, px + sz, py + sz * 0.55], fill=(246, 250, 255, int(rng.uniform(160, 245))))
            if rng.random() < 0.72:
                d.ellipse([px - 1.5, py - 1.5, px + 1.5, py + 1.5], fill=(250, 224, 140, 235))
    pil_img.alpha_composite(layer)


def add_ambient_petals(pil_img, count=65, y_range=(0.08, 0.92), seed=7):
    w, h = pil_img.size
    d = ImageDraw.Draw(pil_img, "RGBA")
    rng = np.random.default_rng(seed)
    for _ in range(count):
        px = rng.uniform(0.03, 0.97) * w
        py = rng.uniform(y_range[0], y_range[1]) * h
        sz = rng.uniform(1.6, 4.2)
        d.ellipse([px - sz, py - sz * 0.55, px + sz, py + sz * 0.55], fill=(242, 247, 252, int(rng.uniform(110, 215))))
        if rng.random() < 0.5:
            d.ellipse([px - 1.2, py - 1.2, px + 1.2, py + 1.2], fill=(248, 222, 140, 200))


def draw_arrow_overlay(pil_img, p0, p1, color=(248, 218, 134, 220), label=None):
    w, h = pil_img.size
    d = ImageDraw.Draw(pil_img, "RGBA")
    x0, y0 = p0[0] * w, p0[1] * h
    x1, y1 = p1[0] * w, p1[1] * h
    d.line([(x0, y0), (x1, y1)], fill=color, width=3)
    ang = math.atan2(y1 - y0, x1 - x0)
    sz = 12
    d.polygon([
        (x1, y1),
        (x1 - sz * math.cos(ang - 0.45), y1 - sz * math.sin(ang - 0.45)),
        (x1 - sz * math.cos(ang + 0.45), y1 - sz * math.sin(ang + 0.45)),
    ], fill=color)
    if label:
        mx, my = (x0 + x1) * 0.5, (y0 + y1) * 0.5
        d.text((mx + 6, my - 16), label, font=fnt(FONT_SANS, 13), fill=color)


def draw_pill(d, x, y, text, font, fg, bg=(12, 18, 30), outline=None, pad_x=10, pad_y=4):
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.rounded_rectangle([x, y, x + tw + pad_x * 2, y + th + pad_y * 2], radius=7, fill=bg, outline=outline or fg, width=2)
    d.text((x + pad_x - bbox[0], y + pad_y - bbox[1]), text, font=font, fill=fg)


def to_rgba_pil(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


# ==============================================================================
# BOARD A: Sustaining Lethal Dread & Near-Miss Tension (C3 -> C4)
# ==============================================================================
def build_board_A():
    W, H = 2400, 1380
    board = Image.new("RGB", (W, H), (10, 14, 24))
    d = ImageDraw.Draw(board)

    d.text((48, 26), "構図検討ボード A：『冒険者に襲いかかる緊張（C3→C4）』を途切れさせない3案比較", font=fnt(FONT_SERIF_B, 34), fill=(238, 244, 252))
    d.text((48, 72), "illustration-composition × 桜井Skills #009「ギュッとしてパッと解消」— v3.1の敗因（横アングル＆頭上確定）を構図から根本解決する", font=fnt(FONT_SANS, 18), fill=ACCENT_GOLD)

    # --- Top row: 3 Distinct 5-Value Chiaroscuro Thumbnails (740 x 416 each) ---
    tw, th = 740, 416
    xs = [48, 830, 1612]
    y_thumb = 148

    # Option A-1 (RECOMMENDED): Head-On Symmetrical Looming Wall -> Eye-Level Grazing Near-Miss!
    # Split thumbnail shows BOTH C3 (left 54%) and C4 (right 46%) tension bridge!
    arr1 = make_gradient_canvas(tw, th, V1_BLACK, V2_DARK, horizon_y=0.66, lake_col=V1_BLACK)
    add_light_beam(arr1, 0.50, 0.0, 0.50, 0.72, 0.16, 0.44, V4_LIGHT, 0.34)
    im1 = to_rgba_pil(arr1)
    # Left half: C3 Dead-Center Head-On Whale rushing straight at 4 PCs!
    draw_head_on_whale(im1, 0.50, 0.48, 0.54)
    draw_4_pcs_and_lantern(im1, 0.50, 0.94, scale=1.05, show_lantern=True)
    # Looming expansion arrows (showing Time-to-Collision expansion straight at lens!)
    draw_arrow_overlay(im1, (0.50, 0.46), (0.34, 0.32), (238, 108, 108, 220))
    draw_arrow_overlay(im1, (0.50, 0.46), (0.66, 0.32), (238, 108, 108, 220))
    draw_arrow_overlay(im1, (0.50, 0.58), (0.50, 0.80), (238, 108, 108, 235), "真正面へ直進膨張!")

    # Option A-2: Low Water-Edge Oblique Underside Looming Over Corner PCs
    arr2 = make_gradient_canvas(tw, th, V1_BLACK, V2_DARK, horizon_y=0.74, lake_col=V1_BLACK)
    add_light_beam(arr2, 0.25, 0.0, 0.35, 0.78, 0.14, 0.36, V4_LIGHT, 0.26)
    im2 = to_rgba_pil(arr2)
    draw_whale_organic_side(im2, 0.42, 0.34, 0.92, 16, glow=0.14, show_eye=True)
    draw_4_pcs_and_lantern(im2, 0.78, 0.93, scale=0.95, show_lantern=True)
    draw_arrow_overlay(im2, (0.28, 0.40), (0.72, 0.24), (248, 218, 134, 210), "斜め上へ抜ける気配が漏れる")

    # Option A-3: Reverse-Shot (Looking from Lake toward 4 PCs' Backlit Silhouettes + Looming Reflection)
    arr3 = make_gradient_canvas(tw, th, V2_DARK, V3_MID * 0.75, horizon_y=0.58, lake_col=V1_BLACK)
    add_light_beam(arr3, 0.52, 0.0, 0.52, 0.65, 0.20, 0.50, V4_LIGHT, 0.32)
    im3 = to_rgba_pil(arr3)
    # Huge dark looming shadow behind the camera reflected in foreground water
    d3 = ImageDraw.Draw(im3, "RGBA")
    d3.ellipse([int(tw * 0.10), int(th * 0.66), int(tw * 0.90), int(th * 1.25)], fill=(8, 12, 22, 235))
    d3.arc([int(tw * 0.14), int(th * 0.68), int(tw * 0.86), int(th * 1.20)], 195, 345, fill=(180, 210, 238, 160), width=3)
    draw_4_pcs_and_lantern(im3, 0.50, 0.62, scale=0.95, show_lantern=True)
    draw_arrow_overlay(im3, (0.50, 0.84), (0.50, 0.68), (160, 195, 225, 210), "間接的（反射越し）")

    opts_a = [
        (im1, "★ 案A-1（最有力推奨）｜正面対峙の巨壁 → 目線ニアミス", ACCENT_GOLD,
         "【視点】4人の背中越し・低空・完全正面対称（消失点＝鯨の額）\n"
         "【なぜ緊張が切れないか】横移動ゼロで中央の黒い巨体が画面25%→85%へ膨張するため、人間の視覚が『衝突までの残り時間（TTC）』を計算し『確実にぶつかる！死ぬ！』と錯覚する。\n"
         "【欠点と対策】正面だと全長24mが伝わりにくい → 左右へ弾ける銀の水幕＋直後のC4で目の前を横切る長大な胴体（4秒）で補う。"),
        (im2, "案A-2｜湖面30cmの斜め煽り（覆いかぶさる顎）", (150, 190, 230),
         "【視点】湖面すれすれから斜め正面で鯨の下顎と右下隅の4人を見る\n"
         "【長所】24mのサイズ差と威圧感は非常に派手。\n"
         "【欠点】鯨の進行ベクトルが斜め右上へ抜けて見えるため、経験ある観客ほど『あ、頭上を通過するな』と早々に察してしまい、襲撃の恐怖が薄れる（v3.1の弱点が半分残る）。"),
        (im3, "案A-3｜湖側からの切り返し（4人正面シルエット＋水面の巨影）", (150, 190, 230),
         "【視点】鯨の側から岸辺の4人を見る逆光構図\n"
         "【長所】4人が身構える芝居とランタンの揺れを強調できる。\n"
         "【欠点】主役の鯨が反射・影の間接描写になり初見の衝撃が弱い。さらにPCを正面から撮ると『容姿を固定しない』制約と衝突しやすい。"),
    ]

    for idx, (im, head, col, desc) in enumerate(opts_a):
        x0 = xs[idx]
        d.rounded_rectangle([x0 - 3, y_thumb - 36, x0 + tw + 3, y_thumb + th + 216], radius=12, fill=(16, 24, 38), outline=col, width=3 if idx == 0 else 2)
        d.text((x0 + 10, y_thumb - 29), head, font=fnt(FONT_SANS, 18), fill=col)
        board.paste(im.convert("RGB"), (x0, y_thumb))
        f_desc = fnt(FONT_SERIF, 15)
        d.multiline_text((x0 + 14, y_thumb + th + 12), wrap_jp(d, desc, f_desc, tw - 28), font=f_desc, fill=(214, 226, 240), spacing=7)

    # --- Bottom Panel: How A-1 Connects C3 -> C4a (Near-Miss) -> C4b (Eye Contact) Without Dropping Tension ---
    y_bot = 812
    d.rounded_rectangle([48, y_bot, W - 48, H - 36], radius=14, fill=(14, 22, 36), outline=ACCENT_GOLD, width=2)
    d.text((76, y_bot + 18), "案A-1 の核心：『襲ってくる恐怖』を C4 の最後 0.3秒 まで維持する 3段階ニアミス設計", font=fnt(FONT_SANS, 22), fill=ACCENT_GOLD)

    mw, mh = 680, 320
    mxs = [82, 860, 1638]
    my = y_bot + 66

    # Mini 1: C3 (12-18s) Dead-Center Looming Approach
    a_m1 = make_gradient_canvas(mw, mh, V1_BLACK, V2_DARK, horizon_y=0.68, lake_col=V1_BLACK)
    add_light_beam(a_m1, 0.50, 0.0, 0.50, 0.72, 0.14, 0.36, V4_LIGHT, 0.30)
    m1 = to_rgba_pil(a_m1)
    draw_head_on_whale(m1, 0.50, 0.52, 0.66)
    draw_4_pcs_and_lantern(m1, 0.50, 0.95, scale=1.0, show_lantern=True)

    # Mini 2: C4a (18-21.5s) Last-Second Grazing Pull-Up RIGHT ABOVE THE LANTERN!
    a_m2 = make_gradient_canvas(mw, mh, V2_DARK * 1.1, V3_MID * 0.7, horizon_y=0.78, lake_col=V1_BLACK)
    add_light_beam(a_m2, 0.80, 0.0, 0.82, 0.80, 0.18, 0.42, V4_LIGHT, 0.32)
    m2 = to_rgba_pil(a_m2)
    # Colossal overhanging dark whale head surging down-right and curving UP inches over the lantern!
    d2 = ImageDraw.Draw(m2, "RGBA")
    d2.polygon([(0, 0), (int(mw * 0.86), 0), (int(mw * 0.78), int(mh * 0.42)), (int(mw * 0.56), int(mh * 0.66)), (int(mw * 0.14), int(mh * 0.64)), (0, int(mh * 0.54))], fill=(12, 20, 34, 255))
    d2.line([(0, int(mh * 0.54)), (int(mw * 0.14), int(mh * 0.64)), (int(mw * 0.56), int(mh * 0.66)), (int(mw * 0.78), int(mh * 0.42)), (int(mw * 0.86), 0)], fill=(195, 220, 245, 190), width=3)
    # Warm lantern light grazing the wet underside of the jaw!
    d2.arc([int(mw * 0.24), int(mh * 0.52), int(mw * 0.58), int(mh * 0.70)], 15, 165, fill=(252, 214, 128, 210), width=4)
    draw_4_pcs_and_lantern(m2, 0.42, 0.96, scale=1.18, show_lantern=True)
    draw_arrow_overlay(m2, (0.48, 0.58), (0.68, 0.30), (248, 218, 134, 240), "衝突寸前でわずかに上へ逸らす!")

    # Mini 3: C4b (21.5-25s) Eye Gliding Past in Total Darkness + 1.8s Silence!
    a_m3 = make_gradient_canvas(mw, mh, V2_DARK * 0.85, V1_BLACK, horizon_y=0.95)
    add_radial_glow(a_m3, 0.56, 0.48, 0.16, 0.20, V4_LIGHT, 0.34)
    m3 = to_rgba_pil(a_m3)
    d3 = ImageDraw.Draw(m3, "RGBA")
    d3.rectangle([0, int(mh * 0.10), mw, int(mh * 0.88)], fill=(15, 24, 40, 255))
    d3.line([(0, int(mh * 0.10)), (mw, int(mh * 0.14))], fill=(195, 222, 248, 175), width=3)
    ex, ey = int(mw * 0.56), int(mh * 0.48)
    d3.ellipse([ex - 34, ey - 20, ex + 34, ey + 20], fill=(6, 10, 18, 255), outline=(88, 120, 156, 210), width=2)
    d3.ellipse([ex - 16, ey - 14, ex + 16, ey + 14], fill=(14, 22, 38, 255))
    d3.ellipse([ex - 5, ey - 6, ex + 4, ey + 3], fill=(248, 252, 255, 255))
    draw_arrow_overlay(m3, (0.28, 0.72), (0.76, 0.72), (168, 214, 248, 220), "静かに真横を通過（1.8秒無音）")

    minis = [
        (m1, "① C3：正面直進（12–18s）", "低空・完全正面対称で24m巨体が一直線に迫る。逃げ場なし・衝突確定の恐怖。"),
        (m2, "② C4a：衝突寸前の引き上げ（18–21.5s）", "ランタンの灯りが下顎に映る至近距離まで突っ込み、最後の1秒で頭上すれすれへ逸らす！"),
        (m3, "③ C4b：闇と『眼』の通過（21.5–25s）", "月光を遮る完全な闇の中、小さく静かな眼が横切り『敵意がない』と悟る1.8秒の無音。"),
    ]
    for idx, (im, ttl, cap) in enumerate(minis):
        x0 = mxs[idx]
        d.rounded_rectangle([x0 - 2, my - 2, x0 + mw + 2, my + mh + 78], radius=10, fill=(10, 16, 28), outline=(56, 82, 118), width=2)
        board.paste(im.convert("RGB"), (x0, my))
        d.text((x0 + 10, my + mh + 10), ttl, font=fnt(FONT_SANS, 16), fill=ACCENT_GOLD)
        d.text((x0 + 10, my + mh + 36), cap, font=fnt(FONT_SERIF, 14), fill=(208, 222, 238))

    out = OUT_DIR / "composition_board_A_tension.png"
    board.save(out)
    print(f"Saved Board A: {out} ({W}x{H})")


# ==============================================================================
# BOARD B: Vast Abyssal Space, Whale Swimming & Petal Wake Choreography (C6 -> C7)
# ==============================================================================
def build_board_B():
    W, H = 2400, 1420
    board = Image.new("RGB", (W, H), (10, 14, 24))
    d = ImageDraw.Draw(board)

    d.text((48, 26), "構図検討ボード B：『大空間を悠々と泳ぐ最大のシーン』×『花弁の演出設計』3案比較", font=fnt(FONT_SERIF_B, 34), fill=(238, 244, 252))
    d.text((48, 72), "空間を半径60m→220m級の地底大空洞へ解放し、花弁を『無意味な紙吹雪』から『鯨が描く発光航跡リボン』へ昇華する", font=fnt(FONT_SANS, 18), fill=ACCENT_TEAL)

    tw, th = 740, 416
    xs = [48, 830, 1612]
    y_thumb = 148

    arr1 = make_gradient_canvas(tw, th, V1_BLACK, V2_DARK * 1.15, horizon_y=0.64, lake_col=V1_BLACK)
    add_light_beam(arr1, 0.78, 0.0, 0.72, 0.70, 0.08, 0.24, V4_LIGHT, 0.34)
    add_radial_glow(arr1, 0.78, 0.07, 0.05, 0.08, V5_WHITE, 0.75)
    add_radial_glow(arr1, 0.44, 0.36, 0.22, 0.14, V4_LIGHT, 0.25)
    im1 = to_rgba_pil(arr1)
    draw_wake_ribbon(im1, [(0.06, 0.56), (0.18, 0.48), (0.30, 0.40), (0.40, 0.37)], width_px=24, seed=11)
    draw_wake_ribbon(im1, [(0.04, 0.72), (0.18, 0.79), (0.32, 0.84), (0.44, 0.85)], width_px=16, seed=12)
    draw_whale_organic_side(im1, 0.46, 0.36, 0.30, -8, glow=0.92, show_eye=True)
    draw_whale_organic_side(im1, 0.46, 0.86, 0.30, 8, glow=0.55, flip=True, alpha=125)
    add_ambient_petals(im1, count=48, y_range=(0.10, 0.90), seed=21)
    draw_arrow_overlay(im1, (0.58, 0.33), (0.76, 0.14), (108, 218, 210, 225), "悠々と大旋回→最後に上空の満月へ")

    arr2 = make_gradient_canvas(tw, th, V2_DARK, V3_MID * 0.8, horizon_y=0.92)
    add_radial_glow(arr2, 0.50, 0.50, 0.35, 0.30, V4_LIGHT, 0.42)
    im2 = to_rgba_pil(arr2)
    draw_wake_ribbon(im2, [(0.08, 0.85), (0.28, 0.22), (0.76, 0.26), (0.90, 0.80)], width_px=34, seed=31)
    draw_whale_organic_side(im2, 0.50, 0.50, 0.72, -24, glow=0.90)
    add_ambient_petals(im2, count=140, y_range=(0.05, 0.95), seed=32)

    arr3 = make_gradient_canvas(tw, th, V1_BLACK, V2_DARK, horizon_y=0.66, lake_col=V1_BLACK)
    add_light_beam(arr3, 0.72, 0.0, 0.68, 0.68, 0.10, 0.28, V4_LIGHT, 0.30)
    im3 = to_rgba_pil(arr3)
    draw_whale_organic_side(im3, 0.52, 0.34, 0.42, -5, glow=0.85)
    draw_4_pcs_and_lantern(im3, 0.20, 0.92, scale=0.85, show_lantern=True)
    add_ambient_petals(im3, count=85, y_range=(0.12, 0.88), seed=41)

    opts_b = [
        (im1, "★ 案B-1（最有力推奨）｜無限大空洞 × 花雪の航跡リボン × 広→近→広→上空", ACCENT_TEAL,
         "【空間】洞窟を220m級の地下世界へ解放。水平線まで広がる鏡面湖と深い藍青の『負の空間』。\n"
         "【花弁の役割】ただ舞うのではなく、白鯨の胸びれと尾びれが花雪をかき分けて『2本の発光渦リボン（航跡）』を夜空に描く！\n"
         "【動きの快感】まず大空間を悠々と水平〜大旋回し、味わい切った最後に初めて上空の満月へ昇る。"),
        (im2, "案B-2｜花吹雪に巻かれてカメラが360°回転する没入アクション", (150, 190, 230),
         "【長所】派手でアニメOP的なダイナミズムがある。\n"
         "【欠点】背景の水平線・鏡面湖・大空洞の広さが吹き飛び、画面が粒子で騒がしくなる（illustration-composition §3違反）。白鯨の『悠々とした神話的静謐さ』が損なわれる。"),
        (im3, "案B-3｜岸辺からの固定ロングショット（絵画的鑑賞）", (150, 190, 230),
         "【長所】落ち着いて破綻しにくい。\n"
         "【欠点】Reboot v2.0 と同じく『地上から離れる解放感（桜井 #065）』が弱く、せっかくの広大な地下世界や花雪の航跡の立体感が伝わり切らない。"),
    ]

    for idx, (im, head, col, desc) in enumerate(opts_b):
        x0 = xs[idx]
        d.rounded_rectangle([x0 - 3, y_thumb - 36, x0 + tw + 3, y_thumb + th + 210], radius=12, fill=(16, 24, 38), outline=col, width=3 if idx == 0 else 2)
        d.text((x0 + 10, y_thumb - 29), head, font=fnt(FONT_SANS, 18), fill=col)
        board.paste(im.convert("RGB"), (x0, y_thumb))
        f_desc = fnt(FONT_SERIF, 15)
        d.multiline_text((x0 + 14, y_thumb + th + 12), wrap_jp(d, desc, f_desc, tw - 28), font=f_desc, fill=(214, 226, 240), spacing=7)

    # --- Bottom Panel: The 4-Beat Petal & Grand Swimming Choreography (案B-1 Master Sequence) ---
    y_bot = 804
    d.rounded_rectangle([48, y_bot, W - 48, H - 34], radius=14, fill=(14, 22, 36), outline=ACCENT_TEAL, width=2)
    d.text((76, y_bot + 18), "案B-1 の設計図：『花弁の4段階演出』×『広→近→広→上空（満月へ）』の黄金リズム", font=fnt(FONT_SANS, 22), fill=ACCENT_TEAL)

    mw, mh = 540, 304
    mxs = [76, 648, 1220, 1792]
    my = y_bot + 66

    # Beat 1: C6a 光の絨毯・1.5秒静止 + 空間の解放（21mm超広角）
    b1 = make_gradient_canvas(mw, mh, V1_BLACK, V2_DARK * 1.1, horizon_y=0.66, lake_col=V1_BLACK)
    add_radial_glow(b1, 0.50, 0.72, 0.48, 0.14, V5_WHITE, 0.35)
    im_b1 = to_rgba_pil(b1)
    # Floating luminous carpet of petals hovering just above the black lake!
    draw_wake_ribbon(im_b1, [(0.04, 0.72), (0.35, 0.69), (0.70, 0.71), (0.96, 0.68)], width_px=26, seed=51)
    draw_whale_organic_side(im_b1, 0.62, 0.32, 0.34, -4, glow=0.88)

    # Beat 2: C6b 花雪の航跡リボン・優美な並走遊泳（35mm中近景）
    b2 = make_gradient_canvas(mw, mh, V1_BLACK, V2_DARK * 1.15, horizon_y=0.80, lake_col=V1_BLACK)
    add_radial_glow(b2, 0.52, 0.44, 0.30, 0.22, V4_LIGHT, 0.30)
    im_b2 = to_rgba_pil(b2)
    # Two luminous wingtip/fluke vortex ribbons spiraling behind the close whale!
    draw_wake_ribbon(im_b2, [(0.02, 0.62), (0.20, 0.52), (0.36, 0.45), (0.52, 0.48)], width_px=24, seed=61)
    draw_wake_ribbon(im_b2, [(0.04, 0.40), (0.24, 0.34), (0.44, 0.38)], width_px=16, seed=62)
    draw_whale_organic_side(im_b2, 0.58, 0.44, 0.62, -6, glow=0.95, show_eye=True)
    add_ambient_petals(im_b2, count=36, y_range=(0.08, 0.92), seed=63)

    # Beat 3: C6c 大空洞の悠々大旋回 × 天地鏡面（21mm超広角・負の空間）
    b3 = make_gradient_canvas(mw, mh, V1_BLACK, V2_DARK * 1.1, horizon_y=0.58, lake_col=V1_BLACK)
    add_light_beam(b3, 0.80, 0.0, 0.76, 0.66, 0.08, 0.22, V4_LIGHT, 0.35)
    add_radial_glow(b3, 0.80, 0.08, 0.05, 0.09, V5_WHITE, 0.80)
    im_b3 = to_rgba_pil(b3)
    draw_wake_ribbon(im_b3, [(0.06, 0.42), (0.24, 0.34), (0.44, 0.32)], width_px=18, seed=71)
    draw_wake_ribbon(im_b3, [(0.06, 0.76), (0.24, 0.83), (0.44, 0.84)], width_px=14, seed=72)
    draw_whale_organic_side(im_b3, 0.52, 0.32, 0.28, -5, glow=0.94)
    draw_whale_organic_side(im_b3, 0.52, 0.84, 0.28, 5, glow=0.52, flip=True, alpha=130)
    add_ambient_petals(im_b3, count=42, y_range=(0.08, 0.92), seed=73)

    # Beat 4: C7a→C7b 花雪の河を引き連れて上空の満月へ昇り溶ける
    b4 = make_gradient_canvas(mw, mh, V1_BLACK, V2_DARK * 1.1, horizon_y=0.88, lake_col=V1_BLACK)
    add_light_beam(b4, 0.56, 0.0, 0.52, 0.90, 0.14, 0.34, V4_LIGHT, 0.38)
    add_radial_glow(b4, 0.56, 0.14, 0.09, 0.15, V5_WHITE, 0.92)
    im_b4 = to_rgba_pil(b4)
    # Vertical ascending river of glowing petals trailing behind the ascending whale!
    draw_wake_ribbon(im_b4, [(0.44, 0.92), (0.49, 0.72), (0.53, 0.54), (0.55, 0.36)], width_px=26, seed=81)
    draw_whale_organic_side(im_b4, 0.55, 0.34, 0.36, -78, glow=0.98)
    draw_4_pcs_and_lantern(im_b4, 0.22, 0.95, scale=0.72, show_lantern=True)
    add_ambient_petals(im_b4, count=45, y_range=(0.06, 0.92), seed=82)

    beats = [
        (im_b1, "① C6a：光の絨毯・1.5秒静止（広）",
         "足元から離れた花弁＋淡金果実が湖面の上で\n1.5秒ピタッと静止。重力が解ける魔法の瞬間。"),
        (im_b2, "② C6b：花雪の航跡リボン並走（近）",
         "35mm並走。胸びれと尾びれが花雪を2本の\n発光渦リボンへ巻き上げ、無重力遊泳を体感。"),
        (im_b3, "③ C6c：大空洞の大旋回＆鏡面（広）",
         "220m級の無限空間へ引き、空の鯨と湖の鏡像が\n花雪の航跡を引きながら悠々と水平大旋回。"),
        (im_b4, "④ C7a–b：花雪の河と満月への昇天",
         "泳ぎ切った最後に初めて上空へ！花雪の河を\n尾に引き、頭から尾びれの先まで満月へ溶ける。"),
    ]
    for idx, (im, ttl, cap) in enumerate(beats):
        x0 = mxs[idx]
        d.rounded_rectangle([x0 - 2, my - 2, x0 + mw + 2, my + mh + 104], radius=10, fill=(10, 16, 28), outline=(56, 82, 118), width=2)
        board.paste(im.convert("RGB"), (x0, my))
        d.text((x0 + 10, my + mh + 10), ttl, font=fnt(FONT_SANS, 16), fill=ACCENT_GOLD)
        d.multiline_text((x0 + 10, my + mh + 38), cap, font=fnt(FONT_SERIF, 14), fill=(208, 222, 238), spacing=6)

    out = OUT_DIR / "composition_board_B_swimming.png"
    board.save(out)
    print(f"Saved Board B: {out} ({W}x{H})")


if __name__ == "__main__":
    build_board_A()
    build_board_B()
