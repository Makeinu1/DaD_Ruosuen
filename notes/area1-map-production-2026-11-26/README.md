# AREA 1 携行図改訂03 制作データ

2026-11-26 作者承認。現行発行図は [SVG](../../world/underground/maps/area-1/area-1-institute-ja-r03.svg)、[PDF](../../world/underground/maps/area-1/area-1-institute-ja-r03.pdf)、[PNG](../../world/underground/maps/area-1/area-1-institute-ja-r03.png)。制作モデルの物理・装飾の仮値は正式設定ではない。地理正本は atlas.json。

再現: Python 3、numpy、scipy、shapely>=2.1、matplotlib、plotly、numba、Pillow、cairosvg、Noto Sans/Serif CJK JPを用意し、同一ディレクトリで `python ruosuen_previs12.py --shots ''`（OBJ生成）、`python area-1-institute-ja-r03.py` を実行。OBJは再生成可能な中間データのため未格納。入力座標・線形は area-1-r03-geometry.json、検証は area-1-institute-ja-r03-check.json。原本Git blob SHA: SVG 12a91d5f053548677af737c7845b717ed6e93848 / PDF 804aa9e522984e61fc548450c597b208f59b9a6f / PNG cef2b4c1ec2096efcfb76b5682465fa2147082d0。

机上模擬プレイ、PDFのレンダリング、文字重複検査済み。実卓・実機印刷、物理的運行や建築構造の検証は未実施。候補記号を除去し、概略測量図として発行。旧版は履歴に残す。Pagesには未掲載。
