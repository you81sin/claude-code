"""
tools/test_drawing.py
----------------------
お絵描きの底（お題決定・プロンプト生成・成功/失敗フロー）の検証。
画像生成（ネット）はモックする。LLM も使わない（感想はフォールバック）。

実行:
    python tools/test_drawing.py
"""

import os
import sys
import tempfile
import shutil

CHRONOS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CHRONOS_DIR)
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)


def test_theme():
    from apps.pon import drawing
    assert drawing.decide_theme("ねこ描いて") == "ねこ", drawing.decide_theme("ねこ描いて")
    assert drawing.decide_theme("ドラゴンの絵をかいて") == "ドラゴン"
    # お題が無い→デフォルトから1つ
    t = drawing.decide_theme("こんにちは")
    assert t in drawing._DEFAULT_THEMES, t
    # 自発・沈黙でもランダムお題
    assert drawing.decide_theme("__auto__") in drawing._DEFAULT_THEMES
    print("[OK] お題抽出（『〜描いて』→抽出 / 無ければランダム）")


def test_prompt():
    from apps.pon import drawing
    p = drawing._build_image_prompt("ねこ")
    assert "ねこ" in p and ("line drawing" in p or "hand-drawn" in p), p
    assert "no color" in p or "black lines" in p, "線画（白地に黒線）に寄せる指定が無い"
    print(f"[OK] プロンプト生成（手描き線画・白地に黒線）: {p[:50]}…")


def test_draw_success(monkey_ok=True):
    import apps.pon.drawing as drawing
    import drivers.image.novelai as nv

    work = tempfile.mkdtemp(prefix="chronos_draw_")
    os.chdir(work)
    os.makedirs("apps/pon/data", exist_ok=True)

    # 画像生成をモック：呼ばれたら空ファイルを作って True を返す
    def fake_gen(prompt, out_path, *args, **kwargs):
        with open(out_path, "wb") as f:
            f.write(b"PNGMOCK")
        return True
    nv.generate_image = fake_gen

    ok, img, theme, comment = drawing.draw("おばけ描いて", app_id="pon")
    assert ok is True, "成功するはず"
    assert img and os.path.exists(img), "画像ファイルが保存されてない"
    assert os.path.exists("apps/pon/data/current_drawing.png"), "表示用 current_drawing が更新されてない"
    assert theme == "おばけ", theme
    assert comment, "感想が空"
    print(f"[OK] 描画成功フロー: お題『{theme}』 / 感想『{comment}』")

    # 失敗フロー：生成が False → ok False でも感想は返る
    nv.generate_image = lambda p, o, *a, **k: False
    ok2, img2, theme2, comment2 = drawing.draw("りんご描いて", app_id="pon")
    assert ok2 is False and img2 is None, "失敗時は ok False / img None"
    assert comment2, "失敗時も感想は返す"
    print(f"[OK] 描画失敗フロー（落ちずに感想を返す）: 『{comment2}』")

    shutil.rmtree(work, ignore_errors=True)


def test_sketch():
    from libs.sketch import bitmap_to_strokes, humanize, build_payload, DEFAULT_PEN
    # 5x5 に横線(1行)と縦線(1列)を引いたビットマップ
    bm = [
        [1, 1, 1, 1, 1],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    strokes = bitmap_to_strokes(bm, min_len=3)
    assert len(strokes) >= 1, "線が1本も取れていない"
    # すべての点が 0〜1 に正規化されている
    for s in strokes:
        for x, y in s:
            assert 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0, (x, y)
    total_pts = sum(len(s) for s in strokes)

    h = humanize(strokes, jitter=0.01, seed=1)
    assert sum(len(s) for s in h) == total_pts, "humanizeで点数が変わった"
    for s in h:
        for x, y in s:
            assert 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0

    payload = build_payload(h, theme="テスト")
    assert payload["pen"]["color"] == DEFAULT_PEN["color"], "固定ペン色が入っていない"
    assert payload["pen"]["width"] == DEFAULT_PEN["width"], "固定ペン太さが入っていない"
    assert payload["count"] == len(h) and payload["theme"] == "テスト"
    print(f"[OK] 線分解＋手描き化＋固定ペン: {len(strokes)}本 / 点{total_pts} / pen={payload['pen']['color']}")


def main():
    test_theme()
    test_prompt()
    test_sketch()
    test_draw_success()
    print("\n==============================")
    print(" DRAWING TEST PASSED ✅")
    print("==============================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
