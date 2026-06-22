"""
libs/sketch.py
---------------
「絵を線（ストローク）に分解する」層。お絵描きを“線を一本ずつ”描くための底。

方針:
  - 画像 → 線画ビットマップ → ストローク（連続した線の集まり）に分解。
  - ストロークは [x, y] を 0〜1 に正規化した点列。順番つき。
  - ビューアがこれを 1本ずつアニメで描く＝「線を一本一本書く」。
  - 仕上がりのタッチ（線の色・太さ）はビューア側の固定ペンで決まる
    ＝元画像の絵柄がブレても毎回同じタッチになる。
  - 人間らしさ：humanize() で線に微妙な手の揺れを足す。

画像読み込みは Pillow があれば使う。無くても bitmap_to_strokes() は純Pythonで動く
（＝この層の中核ロジックは依存ゼロでテストできる）。
"""

import json
import math
import os
import random
from observation.logger import log


# =========================================================
# 中核: ビットマップ → ストローク（純Python・依存ゼロ）
# =========================================================

# 8近傍（直進を優先するため上下左右を先に）
_NEIGHBORS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]


def bitmap_to_strokes(bitmap, min_len: int = 3) -> list:
    """
    2値ビットマップ（2次元リスト, 1=線, 0=余白）を、連続した線（ストローク）に分解。

    返り値: ストロークのリスト。各ストローク = [[x,y], ...]（x,y は 0〜1 正規化）。
    人が描く順に近づけるため、開始点は左上→右下の読み順で選ぶ。
    """
    h = len(bitmap)
    w = len(bitmap[0]) if h else 0
    if h == 0 or w == 0:
        return []

    ink = {(x, y) for y in range(h) for x in range(w) if bitmap[y][x]}
    visited = set()
    strokes = []

    # 読み順（上→下, 左→右）で開始点を選ぶ＝人間の描き出しに近い
    for start in sorted(ink, key=lambda p: (p[1], p[0])):
        if start in visited:
            continue
        path = [start]
        visited.add(start)
        cur = start
        # 線をたどれるだけたどる（貪欲・8近傍）
        while True:
            nxt = None
            for dx, dy in _NEIGHBORS:
                c = (cur[0] + dx, cur[1] + dy)
                if c in ink and c not in visited:
                    nxt = c
                    break
            if nxt is None:
                break
            visited.add(nxt)
            path.append(nxt)
            cur = nxt

        if len(path) >= min_len:
            denom_x = max(1, w - 1)
            denom_y = max(1, h - 1)
            strokes.append([[round(x / denom_x, 4), round(y / denom_y, 4)] for x, y in path])

    return strokes


def humanize(strokes: list, jitter: float = 0.004, seed: int = None) -> list:
    """
    線に微妙な手の揺れを足して“手描き感”を出す（人間らしさ）。
    jitter は正規化座標での揺れ幅。seed 固定で再現可能。
    """
    rnd = random.Random(seed)
    out = []
    for stroke in strokes:
        out.append([
            [
                max(0.0, min(1.0, x + rnd.gauss(0, jitter))),
                max(0.0, min(1.0, y + rnd.gauss(0, jitter))),
            ]
            for x, y in stroke
        ])
    return out


# =========================================================
# 画像 → ストローク（Pillow があれば）
# =========================================================

def image_to_strokes(path: str, max_dim: int = 140, threshold: int = 128) -> list:
    """
    線画画像を読み込み、ストロークに分解する。
    Pillow が無い場合は空リストを返す（呼び出し側でフォールバック）。
    """
    try:
        from PIL import Image
    except Exception:
        log("[SKETCH] Pillow 未インストール → 線分解スキップ（pip install Pillow）")
        return []

    if not os.path.exists(path):
        return []

    try:
        img = Image.open(path).convert("L")
    except Exception as e:
        log(f"[SKETCH] 画像読み込み失敗: {e}")
        return []

    w, h = img.size
    scale = max_dim / max(w, h) if max(w, h) > max_dim else 1.0
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    img = img.resize((nw, nh))
    px = list(img.getdata())  # 0(黒)〜255(白)

    # 線画＝白地に黒線。暗い画素を「線」とみなす。
    bitmap = [[1 if px[y * nw + x] < threshold else 0 for x in range(nw)] for y in range(nh)]

    ink = sum(sum(row) for row in bitmap)
    # 画面の大半が黒（暗い背景の画像）なら反転して線だけ拾う
    if ink > nw * nh * 0.5:
        bitmap = [[1 - v for v in row] for row in bitmap]

    return bitmap_to_strokes(bitmap)


# =========================================================
# ビューア用ペイロード（固定ペン＝同じタッチ）
# =========================================================

# pon の固定ペン（毎回同じタッチにするための基準）
DEFAULT_PEN = {
    "color": "#2b2b2b",   # 鉛筆っぽい濃いグレー
    "width": 2.6,         # 線の太さ（一定）
    "wobble": 0.6,        # 描画時の手ブレ量(px相当)
    "speed": 220,         # 1秒あたりに進む点の数（描く速さ）
}


def build_payload(strokes: list, theme: str = "", pen: dict = None) -> dict:
    """ビューアが読む JSON。固定ペン情報を必ず含める＝タッチ統一。"""
    return {
        "theme":   theme,
        "pen":     {**DEFAULT_PEN, **(pen or {})},
        "strokes": strokes,
        "count":   len(strokes),
        "ts":      __import__("time").time(),
    }


def save_payload(payload: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
