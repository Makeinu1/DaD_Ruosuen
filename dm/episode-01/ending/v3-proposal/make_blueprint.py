#!/usr/bin/env python3
"""Generate visual blueprint (Emotion Curve + Top-Down 3D Camera Plan + Elevation Profile)
for Episode 1 Ending v3.0 'Kousetsuka' reboot proposal."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "camera_and_emotion_blueprint.png"
FONT_SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
FONT_SERIF_B = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"

W, H = 1920, 1280
BG = (10, 17, 32)
PANEL = (15, 25, 45)
BORDER = (44, 68, 108)
INK = (232, 241, 248)
MUTED = (146, 172, 206)
BLUE = (92, 162, 232)
GOLD = (244, 219, 150)
RED = (235, 112, 112)
TEAL = (96, 205, 195)


def fnt(path, size):
    return ImageFont.truetype(path, size)


def draw_pill(d, x, y, text, font, fg, bg=(11, 20, 36), outline=None, pad_x=10, pad_y=5):
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    rect = [x, y, x + tw + pad_x * 2, y + th + pad_y * 2]
    d.rounded_rectangle(rect, radius=8, fill=bg, outline=outline or fg, width=1)
    d.text((x + pad_x - bbox[0], y + pad_y - bbox[1]), text, font=font, fill=fg)
    return rect


def draw_arrow_polyline(d, pts, color, width=5, dashed=False):
    import math
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        if not dashed:
            d.line([(x0, y0), (x1, y1)], fill=color, width=width)
        else:
            dist = math.hypot(x1 - x0, y1 - y0)
            steps = max(1, int(dist / 16))
            for s in range(0, steps, 2):
                t0 = s / steps
                t1 = min(1.0, (s + 1.15) / steps)
                d.line(
                    [(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0),
                     (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)],
                    fill=color, width=width
                )
    # Arrowhead at end
    x0, y0 = pts[-2]
    x1, y1 = pts[-1]
    ang = math.atan2(y1 - y0, x1 - x0)
    size = 13
    p1 = (x1 - size * math.cos(ang - 0.45), y1 - size * math.sin(ang - 0.45))
    p2 = (x1 - size * math.cos(ang + 0.45), y1 - size * math.sin(ang + 0.45))
    d.polygon([(x1, y1), p1, p2], fill=color)


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Header
    d.text((56, 36), "第一話エンディング『空に降る雪』v3.0 — 感情曲線 × 3Dカメラワーク設計図", font=fnt(FONT_SERIF_B, 34), fill=INK)
    d.text((56, 84), "桜井Skills「ギュッとしてパッと解消」「ほめてやれ！」「スケール感」 × Seedance 2.5 Pill Pipeline（全8カット・60秒）", font=fnt(FONT_SANS, 20), fill=GOLD)

    # --- Panel 1: Emotion Curve (Top full width) ---
    p1 = (56, 134, 1864, 534)
    d.rounded_rectangle(p1, radius=16, fill=PANEL, outline=BORDER, width=2)
    d.text((84, 152), "1. プレイヤーの感情曲線（『ギュッ→無音の頂点→パッと解放→祝福の余韻』）", font=fnt(FONT_SANS, 22), fill=INK)

    # Plot area
    gx0, gy0, gx1, gy1 = 120, 210, 1810, 446
    d.line([(gx0, gy1), (gx1, gy1)], fill=BORDER, width=2)
    mid_y = (gy0 + gy1) // 2 + 18
    d.line([(gx0, mid_y), (gx1, mid_y)], fill=(35, 54, 86), width=1)
    d.text((66, gy0 - 6), "感動", font=fnt(FONT_SANS, 16), fill=GOLD)
    d.text((66, mid_y - 10), "安堵", font=fnt(FONT_SANS, 16), fill=MUTED)
    d.text((66, gy1 - 20), "畏怖", font=fnt(FONT_SANS, 16), fill=RED)

    shots = [
        ("C1", 0, 5, "安堵と予兆", "固定→微プッシュ", 0.45, BLUE),
        ("C2", 5, 11, "不穏な巨影", "超低空ドリーバック", 0.22, RED),
        ("C3", 11, 18, "ボスか!? 浮上", "仰角チルト＋後退", 0.08, RED),
        ("C4", 18, 23, "頭上通過・闇", "真上90°仰ぎ(無音)", 0.04, RED),
        ("C5", 23, 31, "月光覚醒＆開花", "足元→空へ振り上げ", 0.72, BLUE),
        ("C6", 31, 45, "【頂点】空に降る雪", "ArcAndRise + Orbit", 0.96, GOLD),
        ("C7", 45, 52, "別れ・見送り", "4人の背中越し仰角", 0.64, BLUE),
        ("C8", 52, 60, "静寂・最後の一枚", "C1同一固定(波紋)", 0.56, GOLD),
    ]

    def tx(sec):
        return int(gx0 + (sec / 60.0) * (gx1 - gx0))

    def ty(val):
        return int(gy1 - val * (gy1 - gy0))

    for cid, s0, s1, title, cam, val, col in shots:
        x0, x1 = tx(s0), tx(s1)
        if cid == "C6":
            d.rectangle([x0, gy0, x1, gy1], fill=(34, 40, 34))
        elif cid in ("C3", "C4"):
            d.rectangle([x0, gy0, x1, gy1], fill=(36, 22, 34))
        d.line([(x0, gy0), (x0, gy1)], fill=(38, 56, 88), width=1)
        d.text((x0 + 8, gy1 + 10), f"{cid} ({s0}-{s1}s)", font=fnt(FONT_SANS, 16), fill=col)
        d.text((x0 + 8, gy1 + 34), title, font=fnt(FONT_SANS, 15), fill=INK)
        d.text((x0 + 8, gy1 + 56), cam, font=fnt(FONT_SERIF, 13), fill=MUTED)

    curve_pts = [
        (0, 0.48), (3, 0.45), (5, 0.42), (8, 0.28), (11, 0.16), (14, 0.08),
        (18, 0.05), (21, 0.03), (23, 0.18), (26, 0.55), (29, 0.78), (31, 0.86),
        (34, 0.94), (39, 0.98), (44, 0.92), (48, 0.72), (52, 0.50), (54, 0.46),
        (57, 0.64), (60, 0.58),
    ]
    px_pts = [(tx(t), ty(v)) for t, v in curve_pts]
    for i in range(len(px_pts) - 1):
        t_mid = (curve_pts[i][0] + curve_pts[i + 1][0]) * 0.5
        c_line = RED if t_mid < 23 else (GOLD if 30 <= t_mid <= 46 or t_mid >= 56 else BLUE)
        d.line([px_pts[i], px_pts[i + 1]], fill=c_line, width=5)

    # Callout 1: Max compression (placed cleanly above-left inside C3-C4 dark zone)
    p_c4 = (tx(21), ty(0.03))
    d.line([p_c4, (tx(19.2), ty(0.32))], fill=RED, width=2)
    d.ellipse([p_c4[0] - 8, p_c4[1] - 8, p_c4[0] + 8, p_c4[1] + 8], fill=RED, outline=INK, width=2)
    draw_pill(d, tx(11.3), ty(0.46), "ギュッの極致：月光を遮る闇＋1.5秒の無音", fnt(FONT_SANS, 15), RED, bg=(28, 16, 28))

    # Callout 2: Dead grass -> white flowers (placed cleanly upper-left of curve)
    p_c5 = (tx(27), ty(0.64))
    d.line([p_c5, (tx(25.2), ty(0.81))], fill=TEAL, width=2)
    d.ellipse([p_c5[0] - 8, p_c5[1] - 8, p_c5[0] + 8, p_c5[1] + 8], fill=TEAL, outline=INK, width=2)
    draw_pill(d, tx(18.0), ty(0.95), "足元の枯れ草が一斉に白花へ！", fnt(FONT_SANS, 15), TEAL, bg=(12, 28, 36))

    # Callout 3: Climax release (placed cleanly below top curve inside C6 band)
    p_c6 = (tx(39), ty(0.98))
    d.line([p_c6, (tx(39), ty(0.75))], fill=GOLD, width=2)
    d.ellipse([p_c6[0] - 9, p_c6[1] - 9, p_c6[0] + 9, p_c6[1] + 9], fill=GOLD, outline=INK, width=2)
    draw_pill(d, tx(31.4), ty(0.73), "パッと解放：花吹雪と空へ飛び白鯨を回り込む", fnt(FONT_SANS, 15), GOLD, bg=(28, 32, 24))

    # Callout 4: Final petal (placed cleanly upper-right with plenty of clearance)
    p_c8 = (tx(57), ty(0.64))
    d.line([p_c8, (tx(56.5), ty(0.80))], fill=GOLD, width=2)
    d.ellipse([p_c8[0] - 8, p_c8[1] - 8, p_c8[0] + 8, p_c8[1] + 8], fill=GOLD, outline=INK, width=2)
    draw_pill(d, tx(51.8), ty(0.95), "最後の一枚＝夢じゃなかった", fnt(FONT_SANS, 15), GOLD, bg=(24, 28, 36))

    # --- Panel 2: Top-Down 3D Camera Plan (Bottom-Left) ---
    p2 = (56, 558, 1090, 1236)
    d.rounded_rectangle(p2, radius=16, fill=PANEL, outline=BORDER, width=2)
    d.text((84, 578), "2. 空間俯瞰図（Top-Down）：白鯨の軌跡 × 3Dカメラワーク（Pill Pipeline 設計）", font=fnt(FONT_SANS, 21), fill=INK)
    d.text((84, 608), "旧v2.0「1点固定の横絵」を脱却し、地上目線(C1-C4) → 足元振上(C5) → 空中追従＆回り込み(C6) → 地上帰還(C7-C8)", font=fnt(FONT_SERIF, 15), fill=MUTED)

    # Lake ellipse
    d.ellipse([145, 675, 1005, 1135], fill=(16, 36, 68), outline=(52, 92, 146), width=2)
    d.text((435, 920), "地底湖（暗い鏡面）", font=fnt(FONT_SERIF, 18), fill=(110, 150, 200))

    # Shore & 4 PCs + Lantern (bottom-left)
    d.polygon([(88, 1035), (378, 1015), (468, 1190), (88, 1190)], fill=(30, 40, 56), outline=(74, 96, 128))
    d.text((108, 1144), "冒険者の岸（灰褐色の閉花群落＋P0＋小さなランタン）", font=fnt(FONT_SANS, 15), fill=MUTED)
    for px, py in [(206, 1082), (238, 1074), (270, 1080), (300, 1092)]:
        d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=GOLD, outline=(20, 20, 20), width=2)
    d.text((192, 1106), "4人のPC (Pin)", font=fnt(FONT_SANS, 14), fill=GOLD)
    d.ellipse([338, 1064, 354, 1080], fill=(255, 210, 120), outline=INK, width=1)
    d.text((360, 1062), "ランタン & P0", font=fnt(FONT_SANS, 13), fill=GOLD)

    # Blooming mature cape S1 (bottom-right)
    d.polygon([(675, 1055), (975, 960), (1048, 1185), (620, 1185)], fill=(36, 52, 68), outline=TEAL)
    d.text((705, 1126), "成熟群落 S1（枯れ草→一斉白花）", font=fnt(FONT_SANS, 15), fill=TEAL)

    # Moonlight fissure zone (upper-right)
    d.ellipse([785, 675, 1020, 860], fill=(34, 68, 116), outline=BLUE, width=2)
    d.text((848, 816), "月光柱・裂け目", font=fnt(FONT_SANS, 16), fill=INK)

    # Non-intersecting sweeping Whale 3D path (S-curve: left-emerge -> overhead pass -> S1 moonlight ignition -> central climax -> moon exit)
    leg_fear = [(230, 840), (242, 945), (292, 1042)]
    leg_ignite = [(292, 1042), (485, 1030), (748, 955)]
    leg_climax = [(748, 955), (715, 860), (595, 820)]
    leg_exit = [(595, 820), (745, 765), (900, 745)]

    draw_arrow_polyline(d, leg_fear, RED, width=6)
    draw_arrow_polyline(d, leg_ignite, BLUE, width=6)
    draw_arrow_polyline(d, leg_climax, GOLD, width=6)
    draw_arrow_polyline(d, leg_exit, BLUE, width=6)

    # C6 Orbit + ArcAndRise camera trajectory (dashed teal curve hugging north-west of ④ with zero collision)
    cam_pts = [(338, 1012), (378, 895), (425, 770), (528, 718), (655, 738)]
    draw_arrow_polyline(d, cam_pts, TEAL, width=4, dashed=True)
    draw_pill(d, 378, 650, "C6 カメラ軌跡：花弁と上昇し白鯨を回り込む (ArcAndRise+Orbit)", fnt(FONT_SANS, 14), TEAL, bg=(12, 28, 36))

    # Waypoint markers + clean non-overlapping pill labels
    waypoints = [
        ((230, 840), "① 浮上(C3)", 100, 792, RED),
        ((292, 1042), "② 頭上通過(C4)", 102, 990, RED),
        ((748, 955), "③ 月光覚醒(C5)", 770, 938, BLUE),
        ((595, 820), "④ 花雪の頂点(C6)", 492, 845, GOLD),
        ((900, 745), "⑤ 月へ昇る(C7)", 845, 695, INK),
    ]
    for pt, lbl, lx, ly, col in waypoints:
        d.ellipse([pt[0] - 8, pt[1] - 8, pt[0] + 8, pt[1] + 8], fill=col, outline=INK, width=2)
        draw_pill(d, lx, ly, lbl, fnt(FONT_SANS, 14), col, bg=(12, 22, 38), pad_x=8, pad_y=4)

    # Legend strip at bottom-left of Panel 2
    d.text((88, 1204), "凡例： ━━ 畏怖フェーズ(C2-C4)   ━━ 月光＆帰還(C5/C7)   ━━ 花雪クライマックス(C6)   ┄┄ C6空中カメラ軌跡", font=fnt(FONT_SANS, 13), fill=MUTED)

    # --- Panel 3: Seedance Pill Pipeline & Canonical Alignment (Bottom-Right) ---
    p3 = (1116, 558, 1864, 1236)
    d.rounded_rectangle(p3, radius=16, fill=PANEL, outline=BORDER, width=2)
    d.text((1144, 578), "3. 新制作方式：Pill カメラ制御 × 原画美術ボード", font=fnt(FONT_SANS, 21), fill=INK)

    boxes = [
        ("STEP 1｜Three.js カメラプリヴィズ（Pill Clip）", GOLD,
         "・粗い無彩色の洞窟ブロックアウト（ライティング無し）\n"
         "・4人のPC＝4本のストライプPin／24m白鯨＝巨大カプセル\n"
         "・『コピーすべきチープな体』を隠し、神カメラワークだけ固定"),
        ("STEP 2｜整合済み・統一美術ボード（1枚の手本）", BLUE,
         "・閉花＝灰褐色の枯れ草状蕾 → 開花＝5弁乳白花（FL-01 v0.8）\n"
         "・白鯨＝滑らかな真珠白＋腹の畝（WH-01整合／ピンク廃止）\n"
         "・色彩＝深い夜青 × 銀白月光 × 淡いシャンパンゴールドのみ"),
        ("STEP 3｜動画生成AI（Seedance 2.5 / Veo 等）＋仕上げ", TEAL,
         "・Pill動画（カメラ＆尺）＋ 美術ボード（画風＆質感）を同時入力\n"
         "・旧v15-omniの失敗（宇宙イルカ化）を根本構造から解消\n"
         "・最終出力で Rec.709 / プロジェクター暗部保護 / 音響同期"),
    ]
    by = 626
    for head, col, body in boxes:
        d.rounded_rectangle([1144, by, 1836, by + 168], radius=12, fill=(20, 34, 58), outline=col, width=2)
        d.text((1164, by + 14), head, font=fnt(FONT_SANS, 18), fill=col)
        d.multiline_text((1164, by + 48), body, font=fnt(FONT_SERIF, 16), fill=INK, spacing=8)
        by += 186

    # Footer note
    d.rounded_rectangle([1144, 1184, 1836, 1222], radius=8, fill=(32, 46, 70))
    d.text((1162, 1193), "※本図は GitHub ブランチ & Google Drive の両方に配置（localhost不使用）", font=fnt(FONT_SANS, 15), fill=GOLD)

    img.save(OUT)
    print(f"Saved blueprint: {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
