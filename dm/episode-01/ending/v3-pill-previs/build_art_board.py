#!/usr/bin/env python3
"""Build Unified Art Reference Board (unified_art_board.png) combining the author's
approved paintings with v3.0 canonical palette and visual lock rules for Seedance 2.5 / Flow."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ADOPTED = ROOT.parent / "images" / "adopted"
OUT = ROOT / "unified_art_board.png"

FONT_SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"


def fnt(path, size):
    return ImageFont.truetype(path, size)


def main():
    W, H = 2400, 1400
    canvas = Image.new("RGB", (W, H), (9, 14, 24))
    d = ImageDraw.Draw(canvas)

    # Header
    d.text((48, 28), "『空に降る雪』v3.0 — 統一美術ボード（Unified Art Reference Board）", font=fnt(FONT_SANS, 34), fill=(236, 244, 252))
    d.text((48, 74), "Seedance 2.5 / Veo 等へ @Image1 として渡す美術基準：深い夜青 × 銀白月光 × 真珠白 × 淡シャンパンゴールド（劇場アニメ・ガッシュ厚塗り調）", font=fnt(FONT_SERIF, 18), fill=(166, 190, 216))

    # Left 3x2 grid of 6 strongest adopted paintings
    picks = [
        ("CUT02_KEY_moon.png", "① 空間・月光柱・鏡面湖の美術基準", "洞窟の深い夜青と天井の裂け目からの銀白月光"),
        ("CUT04_KEY_water_shadow.png", "② C2 湖底の巨影・反射の質感", "暗い鏡面湖の下を通過する圧倒的な陰影"),
        ("CUT05_KEY_whale_emerges.png", "③ C3 濡れた浮上・水幕の質感", "非発光時は濡れた濃紺〜真珠灰（※瘤/斑は控えめに補正）"),
        ("CUT07_END.png", "④ C5 満開の白い5弁花畑の基準", "※開花前は必ず灰褐色の枯れ草状蕾から反転させる"),
        ("CUT08_KEY_petal_release.png", "⑤ C6 花弁＋淡金果実の離脱基準", "※5弁統一・付け根の2〜3mm小果実のみ淡金に微光"),
        ("CUT09_KEY_climax.png", "⑥ C6【頂点】空に降る雪と白鯨", "舞い上がる白と淡金の花雪の中を真珠白の鯨が旋回"),
    ]
    tw, th = 540, 304
    pad_x, pad_y = 48, 128
    gx, gy = 22, 68

    for idx, (fname, title, note) in enumerate(picks):
        r, c = divmod(idx, 3)
        x0 = pad_x + c * (tw + gx)
        y0 = pad_y + r * (th + gy + 24)
        p = ADOPTED / fname
        if p.exists():
            im = Image.open(p).convert("RGB")
            # Center-crop to 16:9
            iw, ih = im.size
            target_r = 16 / 9
            if iw / ih > target_r:
                nw = int(ih * target_r)
                im = im.crop(((iw - nw) // 2, 0, (iw + nw) // 2, ih))
            else:
                nh = int(iw / target_r)
                im = im.crop((0, (ih - nh) // 2, iw, (ih + nh) // 2))
            im = im.resize((tw, th), Image.Resampling.LANCZOS)
            d.rounded_rectangle([x0 - 2, y0 - 2, x0 + tw + 2, y0 + th + 54], radius=10, fill=(15, 22, 36), outline=(46, 68, 100), width=2)
            canvas.paste(im, (x0, y0))
            d.text((x0 + 10, y0 + th + 6), title, font=fnt(FONT_SANS, 15), fill=(242, 222, 152))
            d.text((x0 + 10, y0 + th + 28), note, font=fnt(FONT_SERIF, 13), fill=(176, 196, 218))

    # Right sidebar: Canonical Palette + Visual Lock Checklist
    sx0, sy0, sx1, sy1 = 1756, 126, 2352, 1344
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=14, fill=(14, 22, 36), outline=(56, 82, 118), width=2)
    d.text((sx0 + 24, sy0 + 20), "正本カラーパレット（厳守）", font=fnt(FONT_SANS, 22), fill=(238, 244, 250))

    swatches = [
        ((10, 19, 38),   "#0A1326  深い夜青（洞窟・暗部基調）"),
        ((24, 48, 84),   "#183054  湖底の濃紺（鏡面反射・非発光鯨）"),
        ((178, 210, 238),"#B2D2EE  銀白・氷青の月光（裂け目・覚醒波）"),
        ((242, 245, 248),"#F2F5F8  真珠白（白鯨の体表・5弁花弁）"),
        ((244, 218, 148),"#F4DA94  淡シャンパンゴールド（果実微光・ランタン）"),
        ((118, 108, 96), "#766C60  灰褐色（開花前の枯れ草状・閉じた蕾）"),
    ]
    cy = sy0 + 68
    for rgb, lbl in swatches:
        d.rounded_rectangle([sx0 + 24, cy, sx0 + 82, cy + 40], radius=6, fill=rgb, outline=(180, 196, 216), width=1)
        d.text((sx0 + 96, cy + 9), lbl, font=fnt(FONT_SANS, 16), fill=(224, 234, 244))
        cy += 54

    d.line([(sx0 + 24, cy + 10), (sx1 - 24, cy + 10)], fill=(48, 70, 104), width=2)
    cy += 28
    d.text((sx0 + 24, cy), "v3.0 整合ロック（AI生成時の必須補正）", font=fnt(FONT_SANS, 21), fill=(244, 218, 148))
    cy += 40

    rules = [
        ("1. 花（FL-01 v0.8 厳守）",
         "・開花前＝灰褐色の萼に包まれうつむいた枯れ草状の蕾\n"
         "・開花後＝純白の5弁花（五放射相称・4弁禁止）\n"
         "・C1開幕はランタン横の若い数輪(P0)のみ開花\n"
         "・C5で鯨の光を受け足元から一斉に茎を起こし開花\n"
         "・C6で花弁＋付け根の2-3mm淡金果実が一体で離脱"),
        ("2. 白鯨（WH-01 整合・A寄り）",
         "・全長24mの圧倒的巨体（4人の1.7mと明確な尺度差）\n"
         "・滑らかな真珠白の皮膚＋穏やかな腹の畝＋濡れた艶\n"
         "・ザトウクジラ的な強い瘤/斑は抑え神話的な品格を保つ\n"
         "・小さく暗い眼／ピンク発光は絶対禁止"),
        ("3. 4人の冒険者＆ランタン",
         "・顔・種族・装備は固定しない（逆光シルエット＋背中）\n"
         "・足元の小さなランタン1灯が人間尺度と温もりの核\n"
         "・C4の頭上通過でランタンごと完全な闇に飲まれる"),
        ("4. Pill 参照の置換ルール",
         "・@Video1の灰ブロック・縞カプセル・Pinは一切残さない\n"
         "・カメラ位置/レンズ/動き/カット点のみ100%忠実に継承"),
    ]
    for head, body in rules:
        d.text((sx0 + 24, cy), head, font=fnt(FONT_SANS, 17), fill=(120, 210, 230))
        cy += 28
        d.multiline_text((sx0 + 28, cy), body, font=fnt(FONT_SERIF, 14), fill=(216, 228, 240), spacing=6)
        cy += 24 * (body.count("\n") + 1) + 18

    # Bottom note in left area
    d.rounded_rectangle([48, 922, 1712, 1344], radius=14, fill=(14, 22, 36), outline=(46, 68, 100), width=2)
    d.text((76, 944), "劇場アニメ画風・プロジェクター上映（2026-12-23）向けトーン設計", font=fnt(FONT_SANS, 22), fill=(238, 244, 250))
    notes = (
        "・美術テイスト：手描きガッシュ厚塗り×水彩のにじみを感じる劇場用2Dアニメーション背景（新海誠・ジブリ夜の静謐さ＋初期採用原画の筆致を継承）。\n"
        "・CGプラスチック感・過剰なブルーム・ネオンピンク・AIっぽいツルツル質感は全面禁止。水滴のきらめきと濡れた岩肌の陰影で実在感を出す。\n"
        "・プロジェクター暗部保護：黒潰れ防止のため暗部ベースは完全な#000000ではなく深い藍青（#0A1326前後）を保ち、C4の「月光を遮る闇」でのみ\n"
        "  コントラストを落として圧迫感を最大化する。\n"
        "・4クリップ分割出力（各29秒未満）でも色温度・画風・白鯨プロポーションがブレないよう、全4クリップで必ず本ボードを @Image1 として共通入力する。\n"
        "・構成：Clip 1（C1+C2：11s 予兆と巨影）→ Clip 2（C3+C4：12s 浮上と頭上闇）→ Clip 3（C5+C6：22s 一斉開花＆空中花雪オービット）→ Clip 4（C7+C8：15s 見送りと最後の一枚）。"
    )
    d.multiline_text((76, 988), notes, font=fnt(FONT_SERIF, 17), fill=(208, 222, 238), spacing=14)

    canvas.save(OUT)
    print(f"Saved unified art board: {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
