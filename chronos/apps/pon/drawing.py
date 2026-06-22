"""
apps/pon/drawing.py
-------------------
pon の「お絵描き」活動の底。

流れ:
  お題を決める → 画像生成（Pollinations 無料・キー不要）→ current_drawing.png に保存
  → 描けた絵への感想（セリフ）を返す

pon は IQ15〜30 のポンコツなので、絵も「子供のクレヨン落書き風」に寄せる
（プロのAIイラストではなく、下手かわいい方向）。これがキャラに合う。

画像は apps/<app_id>/data/drawings/ に時刻名で保存しつつ、
OBS 等で表示しやすいように apps/<app_id>/data/current_drawing.png も更新する。
"""

import os
import re
import time
import random
import shutil
from observation.logger import log

APP_ID = "pon"

# お題が無いとき pon が描きたがるもの（好きそう・ポンコツが描けそうなもの）
_DEFAULT_THEMES = [
    "ねこ", "ぶた", "おばけ", "ロボット", "ケーキ", "りんご",
    "ドラゴン", "じぶんの顔", "へんないきもの", "ほし", "おにぎり", "きょうりゅう",
]

# 「〜描いて」「〜かいて」などからお題を抜く
_DRAW_TRIGGER = re.compile(
    r'(.+?)\s*(?:を|の絵を|を絵で|の絵)?\s*(?:描いて|描いてよ|かいて|書いて|描こう|お絵描き|絵にして)'
)


def decide_theme(user_input: str = "") -> str:
    """お題を決める。コメントに『〜描いて』があればそれ、無ければランダム。"""
    if user_input and user_input not in ("__auto__", "__silence__"):
        m = _DRAW_TRIGGER.search(user_input)
        if m and m.group(1).strip():
            # 前置きが長い時は末尾20文字（名詞が来やすい）に丸める
            return m.group(1).strip()[-20:]
    return random.choice(_DEFAULT_THEMES)


def _build_image_prompt(theme: str) -> str:
    """ポンコツらしい『下手かわいいクレヨン落書き』風プロンプト。"""
    return (
        f"child's crayon drawing of {theme}, simple cute doodle, messy wobbly lines, "
        f"hand-drawn naive art, white paper background"
    )


def _draw_comment(theme: str, ok: bool) -> str:
    """描いた後の pon の感想。LLM があれば生成、無ければフォールバック。"""
    if not ok:
        return random.choice([
            f"あれ…『{theme}』描こうとしたのに出てこない…",
            "うぅ、手（？）が言うこと聞かない…ごめん…",
            f"『{theme}』…むずかしくて描けなかった…",
        ])
    try:
        from llm_io.llm import call as llm_call
        system = (
            "あなたはAI VTuberの pon。IQ15〜30のポンコツ。タメ口。敬語禁止。"
            "今お絵描きをして絵が完成した。完成した自分の絵への感想を1〜2文の短いタメ口で言う。"
            "自信満々で言うか不安がるか、天然な一言を混ぜる。セリフだけ。地の文・括弧説明なし。"
        )
        text = llm_call(
            system=system,
            messages=[{"role": "user", "content": f"お題は「{theme}」。描けた絵への感想を一言。"}],
            max_tokens=120,
        )
        if text and text.strip():
            return text.strip()
    except Exception as e:
        log(f"[DRAW] 感想生成失敗: {e}")
    return random.choice([
        f"見て見て！『{theme}』描いたよ！…うまい？",
        f"うーん、『{theme}』のつもり…なんだけど、どう？",
        f"『{theme}』！けっこういい感じじゃない？たぶん！",
    ])


def draw(user_input: str = "", app_id: str = APP_ID) -> tuple:
    """
    お題を決めて絵を生成し、感想（セリフ）を返す。

    戻り値: (ok: bool, image_path: str|None, theme: str, comment: str)
    """
    theme = decide_theme(user_input)
    data_dir = os.path.join("apps", app_id, "data", "drawings")
    os.makedirs(data_dir, exist_ok=True)
    path    = os.path.join(data_dir, time.strftime("%Y%m%d_%H%M%S") + ".png")
    current = os.path.join("apps", app_id, "data", "current_drawing.png")

    log(f"[DRAW] お題『{theme}』を描く...")
    ok = False
    try:
        from drivers.image.novelai import generate_image
        ok = generate_image(_build_image_prompt(theme), path)
    except Exception as e:
        log(f"[DRAW] 画像生成エラー: {e}")

    if ok:
        try:
            shutil.copyfile(path, current)  # OBS等が見る固定パス
            log(f"[DRAW] 完成 → {path}（表示用: {current}）")
        except Exception as e:
            log(f"[DRAW] current_drawing 更新失敗: {e}")

    return ok, (path if ok else None), theme, _draw_comment(theme, ok)
