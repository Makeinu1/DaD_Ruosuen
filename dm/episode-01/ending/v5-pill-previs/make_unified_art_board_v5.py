#!/usr/bin/env python3
"""Assemble unified_art_board_v5.png — the definitive @Image1 visual style bible
combining all 4 painted v5.0 keyframes, OKLCH/Hex palette swatches, and strict Seedance 2.0 canon rules."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
KF_DIR = ROOT / "keyframes"
OUT = ROOT / "unified_art_board_v5.png"

FONT_SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
FONT_SERIF_B = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"


def fnt(path, size):
    return ImageFont.truetype(path, size)


def main():
    W, H = 2400, 1540
    board = Image.new("RGB", (W, H), (10, 14, 24))
    d = ImageDraw.Draw(board)

    d.text((48, 24), "第一話エンディング『空に降る雪』v5.0 決定版 — 統一美術ボード（Seedance 2.0 共通参照 @Image1）", font=fnt(FONT_SERIF_B, 33), fill=(240, 246, 254))
    d.text((48, 70), "手描き劇場アニメ・ガッシュ画調｜遠近レイヤー分離 1+3融合（中景：水没石造アーチ橋×苔上開花 / 最遠景：霧の巨岩柱）｜5弁純白空雪花＋淡シャンパン金果実｜ネオンピンク完全禁止", font=fnt(FONT_SANS, 17), fill=(248, 218, 134))

    panels = [
        ("v5_keyframe_01_c1_shore_omen.jpg",     "① C1 & C8｜安堵と予兆・最後の一枚（Clip 1 / Clip 6 共通アンカー）", "ランタン暖光・若齢花P0（厳密5弁）・灰褐色の垂れた蕾・一滴の銀波紋・霧奥の水没石橋"),
        ("v5_keyframe_02_c3_headon_rush.jpg",    "② C3 & C4a｜正面直進膨張・衝突寸前（Clip 2 緊張アンカー）",      "完全正面対称・無発光の濡れた暗藍色の24m巨体・左右へ炸裂する銀の水幕・4人の極小シルエット"),
        ("v5_keyframe_03_c6c_1plus3_master.jpg", "③ C6b–C6c｜1+3融合・220m大空洞決定画（Clip 3–4 最重要アンカー）", "中景の崩れた石造アーチ橋＆苔上開花＋鏡面反射／霧のベール／最遠景外枠のみの巨岩柱／3層大花吹雪"),
        ("v5_keyframe_04_c7b_moon_dissolve.jpg", "④ C7b｜85mm真横望遠・尾から頭へ満月溶解（Clip 5 別れアンカー）",  "巨大な純白満月の前を真横滑空・借りた月光を返すように尾びれ→胴→胸びれ→頭部が最後に銀霧へ還る"),
    ]

    pw, ph = 1120, 560
    coords = [(48, 118), (1232, 118), (48, 754), (1232, 754)]
    for idx, (fname, title, sub) in enumerate(panels):
        x0, y0 = coords[idx]
        is_crown = (idx == 2)
        col = (248, 218, 134) if is_crown else (142, 188, 232)
        d.rounded_rectangle([x0 - 3, y0 - 3, x0 + pw + 3, y0 + ph + 56], radius=10, fill=(16, 23, 36), outline=col, width=3 if is_crown else 2)
        im = Image.open(KF_DIR / fname).convert("RGB").resize((pw, ph), Image.Resampling.LANCZOS)
        board.paste(im, (x0, y0))
        d.text((x0 + 12, y0 + ph + 8), title, font=fnt(FONT_SANS, 16), fill=col)
        d.text((x0 + 12, y0 + ph + 32), sub, font=fnt(FONT_SERIF, 14), fill=(208, 222, 238))

    # Bottom Color Management & OKLCH Palette Strip
    sy = 1390
    d.rounded_rectangle([48, sy, W - 48, H - 24], radius=10, fill=(15, 22, 34), outline=(54, 78, 108), width=2)
    d.text((68, sy + 12), "厳守カラーパレット（Rec.709 / OKLCH 統一設計・全6クリップ共通グレーディング基準）", font=fnt(FONT_SANS, 16), fill=(236, 244, 252))

    swatches = [
        ("#0A1326", (10, 19, 38),    "深淵ミッドナイト藍", "oklch(0.18 0.04 260)"),
        ("#183054", (24, 48, 84),    "暗サファイア鏡面湖", "oklch(0.31 0.07 254)"),
        ("#4A6A92", (74, 106, 146),  "空気遠近の青銀霧",   "oklch(0.52 0.07 248)"),
        ("#B2D2EE", (178, 210, 238), "銀青色の月光柱",     "oklch(0.84 0.05 240)"),
        ("#F2F5F8", (242, 245, 248), "真珠白・白鯨＆5弁花", "oklch(0.97 0.006 240)"),
        ("#F4DA94", (244, 218, 148), "淡シャンパン金・果実", "oklch(0.89 0.09 88)"),
        ("#766C60", (118, 108, 96),  "灰褐色・枯れ草の蕾", "oklch(0.54 0.02 72)"),
    ]
    sx = 68
    sw_w = 315
    for hex_c, rgb, name, ok in swatches:
        d.rounded_rectangle([sx, sy + 44, sx + 54, sy + 106], radius=6, fill=rgb, outline=(180, 196, 214), width=1)
        d.text((sx + 64, sy + 44), name, font=fnt(FONT_SANS, 14), fill=(234, 242, 250))
        d.text((sx + 64, sy + 66), hex_c, font=fnt(FONT_SANS, 13), fill=(248, 218, 134))
        d.text((sx + 64, sy + 86), ok, font=fnt(FONT_SERIF, 12), fill=(154, 178, 204))
        sx += sw_w

    board.save(OUT)
    print(f"Saved unified v5.0 art board: {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
