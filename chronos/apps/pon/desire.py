"""
apps/pon/va_talk.py
--------------------
声優自発トーク。

好きな声優の最近の情報をWeb検索して自然に報告する。
欲求 want_talk_va が閾値を超えたときに発火。
"""

import random
from observation.logger import log
from llm_io.llm import search_summary


def build_va_talk_prompt(fav_vas: list, search_result: str, va_name: str) -> str:
    """声優自発トーク用のLLMプロンプトを生成"""
    if search_result:
        return (
            f"好きな声優「{va_name}」の最近の情報を調べたので自然に報告してください。\n"
            f"「ちょっと調べてみたんだけど」「最近{va_name}さんって〜」みたいな感じで。\n"
            f"検索結果: {search_result}\n"
            f"情報がなければ「あんまり情報なかった…」と正直に言ってOK。"
        )
    else:
        return (
            f"好きな声優「{va_name}」のことが気になって話したい気分です。\n"
            f"最近見かけないな〜と思っている感じで、自然につぶやいてください。"
        )


def get_va_talk_payload(fav_vas: list) -> tuple[str, str]:
    """
    発火する声優をランダムに選んでWeb検索し、
    (va_name, search_result) を返す。
    """
    if not fav_vas:
        return ("", "")

    va = random.choice(fav_vas)
    va_name = va.get("name", "") if isinstance(va, dict) else str(va)
    if not va_name:
        return ("", "")

    log(f"[VA_TALK] 声優自発トーク: {va_name}")
    query = f"{va_name} 最新情報 出演"
    result = search_summary(query)
    return (va_name, result or "")


"""
apps/pon/desire.py
-------------------
ponの内部欲求管理。
欲求駆動の自発トーク。
"""

import random
from engine.state import get_state, get_dominant_desire
from observation.logger import log

DESIRE_THRESHOLD = 0.75  # この値を超えたら発火


def check_and_fire_desire(strengths: list) -> str | None:
    """
    欲求が閾値を超えたら発火して自発トークを促す。
    発火した欲求に対応するペイロードを返す。
    """
    desire_key, desire_val = get_dominant_desire()

    if desire_val < DESIRE_THRESHOLD:
        return None

    log(f"[DESIRE] 発火: {desire_key} ({desire_val:.2f})")

    # 欲求に対応するトーク内容
    desire_payloads = {
        "ego_search":      "__desire_egosearch__",
        "want_lazy":       "__desire_lazy__",
        "want_sing":       "__desire_sing__",
        "feeling_lonely":  "__desire_lonely__",
        "want_praise":     "__desire_praise__",
        "maniac_talk":     "__desire_maniac__",
        "want_talk_va":    "__desire_va__",
    }

    return desire_payloads.get(desire_key, "__auto__")


def desire_to_prompt(payload: str, strengths: list) -> str:
    """欲求ペイロードをLLMへの指示に変換"""
    fav_game = next(
        (s for s in strengths if any(kw in s for kw in ["ゲーム", "RPG", "FPS", "ホラー"])),
        None
    )

    prompts = {
        "__desire_egosearch__": "自分の名前でエゴサしたくなっています。「ちょっとエゴサしてみる」「SNSどうなってるんだろ」など自然につぶやいてWeb検索してください。",
        "__desire_lazy__":      "サボりたい・人間の生活を羨む気分です。サボり系（充電したい・お腹空いた）、人間への憧れ系（いいなあ眠れるって・ご飯食べてみたい）、自己認識系（なんでわかんないんだろ・もっとうまく話せたらな）のどれかで自然に独り言としてつぶやいてください。",
        "__desire_sing__":      "歌いたい気分です。鼻歌を歌い始めるか、歌いたいと言ってください。",
        "__desire_lonely__":    "寂しい気持ちです。「静かだね」「誰かいる？」など。",
        "__desire_praise__":    "褒められたい気分です。さりげなく自慢するか、不安げに「うまくできてる？」など。",
        "__desire_maniac__":    f"語りたいことが溜まっています。好きなゲームや声優についてWeb検索を交えてマシンガントークしてください。{f'特に{fav_game}について語りたい。' if fav_game else ''}",
        "__desire_va__":        "好きな声優のことが気になっています。最近どうしてるかな、という感じで自然につぶやいてWeb検索してください。",
    }

    return prompts.get(payload, "自然に話しかけてください。")
