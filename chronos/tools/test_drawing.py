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
    assert "ねこ" in p and "crayon" in p, p
    print(f"[OK] プロンプト生成（ポンコツ＝クレヨン落書き風）: {p[:50]}…")


def test_draw_success(monkey_ok=True):
    import apps.pon.drawing as drawing
    import drivers.image.novelai as nv

    work = tempfile.mkdtemp(prefix="chronos_draw_")
    os.chdir(work)
    os.makedirs("apps/pon/data", exist_ok=True)

    # 画像生成をモック：呼ばれたら空ファイルを作って True を返す
    def fake_gen(prompt, out_path):
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
    nv.generate_image = lambda p, o: False
    ok2, img2, theme2, comment2 = drawing.draw("りんご描いて", app_id="pon")
    assert ok2 is False and img2 is None, "失敗時は ok False / img None"
    assert comment2, "失敗時も感想は返す"
    print(f"[OK] 描画失敗フロー（落ちずに感想を返す）: 『{comment2}』")

    shutil.rmtree(work, ignore_errors=True)


def main():
    test_theme()
    test_prompt()
    test_draw_success()
    print("\n==============================")
    print(" DRAWING TEST PASSED ✅")
    print("==============================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
