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

# 8近傍
_NEIGHBORS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]


def _simplify(path: list, step: float = 2.0) -> list:
    """近すぎる点を間引いて線を滑らかにする（手描きのガタつき・細切れを減らす）。"""
    if len(path) <= 2:
        return path
    out = [path[0]]
    for p in path[1:-1]:
        lx, ly = out[-1]
        if (p[0] - lx) ** 2 + (p[1] - ly) ** 2 >= step * step:
            out.append(p)
    out.append(path[-1])
    return out


def bitmap_to_strokes(bitmap, min_len: int = 3, simplify_step: float = 2.0) -> list:
    """
    2値ビットマップ（2次元リスト, 1=線, 0=余白）を、連続した線（ストローク）に分解。

    返り値: ストロークのリスト。各ストローク = [[x,y], ...]（x,y は 0〜1 正規化）。
    - 人が描く順に近づけるため、開始点は左上→右下の読み順で選ぶ。
    - なぞる時は「直前の進行方向に一番近い隣」を優先＝ジグザグ/逆走を防いで線を追う。
    - 仕上げに近すぎる点を間引いて滑らかにする。
    """
    h = len(bitmap)
    w = len(bitmap[0]) if h else 0
    if h == 0 or w == 0:
        return []

    ink = {(x, y) for y in range(h) for x in range(w) if bitmap[y][x]}
    visited = set()
    strokes = []

    def _best_neighbor(cur, prev_dir):
        """進行方向 prev_dir に最も近い未訪問の隣を返す（無ければ None）。"""
        best, best_score = None, -2.0
        for dx, dy in _NEIGHBORS:
            c = (cur[0] + dx, cur[1] + dy)
            if c not in ink or c in visited:
                continue
            if prev_dir is None:
                return c  # 描き始めは最初に見つかった隣
            # 方向の内積（大きいほど直進）。斜めは正規化して比較。
            norm = (dx * dx + dy * dy) ** 0.5
            score = (dx / norm) * prev_dir[0] + (dy / norm) * prev_dir[1]
            if score > best_score:
                best, best_score = c, score
        return best

    # 読み順（上→下, 左→右）で描き出し＝人間の手順に近い
    for start in sorted(ink, key=lambda p: (p[1], p[0])):
        if start in visited:
            continue
        path = [start]
        visited.add(start)
        cur, prev_dir = start, None
        while True:
            nxt = _best_neighbor(cur, prev_dir)
            if nxt is None:
                break
            ndx, ndy = nxt[0] - cur[0], nxt[1] - cur[1]
            nlen = (ndx * ndx + ndy * ndy) ** 0.5
            prev_dir = (ndx / nlen, ndy / nlen)
            visited.add(nxt)
            path.append(nxt)
            cur = nxt

        if len(path) >= min_len:
            path = _simplify(path, step=simplify_step)
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
