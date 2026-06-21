"""
apps/pon/growth.py
-------------------
成長・IQスコア・ゲームフェーズを統合管理。
growth.py + iq.py + game_phase.py を統合。
"""

import os
import json
import random
import time
from engine.state import get_state, update_state
from observation.logger import log

APP_ID    = "pon"
XP_NORMAL   = 0.005
XP_STRENGTH = 0.01
LEVEL_MAX   = 100.0
IQ_BASE_MIN = 15
IQ_BASE_MAX = 30
IQ_PEAK     = 70


# =========================================================
# 成長（レベル・XP）
# =========================================================

def _growth_path() -> str:
    return os.path.join("apps", "pon", "data", "growth.json")


def load_growth() -> dict:
    path = _growth_path()
    if not os.path.exists(path):
        return {"level": 1.0, "xp": 0.0, "total_conversations": 0, "updated": time.time()}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"level": 1.0, "xp": 0.0, "total_conversations": 0, "updated": time.time()}


def save_growth(growth: dict) -> None:
    path = _growth_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(growth, f, ensure_ascii=False, indent=2)


def add_xp(is_strength_topic: bool = False) -> dict:
    growth = load_growth()
    growth["xp"]    += XP_STRENGTH if is_strength_topic else XP_NORMAL
    growth["level"]  = min(LEVEL_MAX, 1.0 + growth["xp"])
    growth["total_conversations"] += 1
    growth["updated"] = time.time()
    save_growth(growth)
    return growth


def get_level() -> float:
    return load_growth()["level"]


def level_to_skill_desc(level: float) -> str:
    if level < 5:
        return (
            "配信を始めたばかりで緊張しています。「え、あ、えっと…」という反応が自然に出ます。"
            "【喋り方】丁寧語・敬語が基本。語尾は「〜です」「〜ます」。緊張して言葉に詰まる。"
        )
    elif level < 15:
        return (
            "少し慣れてきましたが、まだ新人感があります。"
            "【喋り方】丁寧語がベースだが、興奮したときだけ少し崩れる。「え、すごい！」くらいはOK。"
        )
    elif level < 35:
        return (
            "配信に慣れてきました。コメントへの反応が自然になってきています。"
            "【喋り方】普通の話し言葉。丁寧語は残るが固くない。「〜だよね」「〜じゃん」が少し出始める。"
        )
    elif level < 60:
        return (
            "配信の流れを作れるようになってきました。得意話題で盛り上げられます。"
            "【喋り方】タメ口が自然に混じる。「でしょ？」「わかる？」「え待って」など。敬語はほぼ使わない。"
        )
    elif level < 85:
        return (
            "場の空気を読んで動けます。自分らしいスタイルが出てきています。"
            "【喋り方】完全にくだけた話し言葉。「〜じゃん」「〜だし」「まじで」が普通に出る。テンションで言葉が変わる。"
        )
    else:
        return (
            "ベテランの配信者です。自然体で場を盛り上げられます。"
            "【喋り方】完全に自分のスタイル。感情が出るほど言葉が荒くなる。「やばっ」「え゛」「待って待って」など。でも悪意はない。"
        )


# =========================================================
# IQスコア
# =========================================================

def is_strength_topic(user_input: str, strengths: list) -> bool:
    if not user_input or not strengths:
        return False
    return any(s in user_input for s in strengths)


def compute_iq(user_input: str, strengths: list) -> int:
    state   = get_state()
    base_iq = state.get("iq_base", IQ_BASE_MIN)

    if is_strength_topic(user_input, strengths):
        iq = random.randint(60, IQ_PEAK)
    else:
        iq = random.randint(IQ_BASE_MIN, min(base_iq + 5, IQ_BASE_MAX))
        if random.random() < 0.1 and base_iq < 35:
            update_state({"iq_base": base_iq + 1})

    log(f"[IQ] score={iq} (得意話題={is_strength_topic(user_input, strengths)})")
    return iq


def iq_to_prompt(iq: int, strengths: list) -> str:
    strengths_str = "・".join(strengths) if strengths else "なし"
    if iq >= 60:
        return (
            f"この話題はあなたの得意分野（{strengths_str}）です。"
            f"詳しくて熱量高く話してください。"
            f"ただし専門用語や理論は使わず、感覚・経験・好きという気持ちで語ってください。"
        )
    elif iq >= 40:
        return "なんとなくわかる感じで返してください。難しい言葉は使わず、ふわっとした返答でOKです。"
    else:
        return "あまりよくわからないけど反応してください。難しいことは理解できないので、感覚的・天然な返答をしてください。的外れでもOK、でも悪意はなく純粋に。"


# =========================================================
# ゲームフェーズ
# =========================================================

_GAME_KEYWORDS = {
    "intro":    ["始め", "スタート", "やってみる", "初めて", "どんなゲーム", "起動", "タイトル", "ロード中", "セーブデータ"],
    "thinking": ["どうすれば", "わからない", "詰まった", "むずい", "難しい", "えーと", "うーん", "どこ行けば", "攻略", "ヒント", "どうやって", "これどうするの", "詰んだ"],
    "hype":     ["やばい", "すごい", "クリア", "倒した", "勝った", "最高", "うおー", "わあ", "えっ", "きた", "レア", "ドロップ", "ボス", "レベルアップ", "進化", "覚醒"],
    "ending":   ["エンディング", "クリアした", "終わった", "ED", "エンド", "感動", "泣いた", "最後", "また", "次回", "お疲れ"],
}

_GAME_PHASE_PROMPTS = {
    "intro":   "ゲームを始めたところ。期待感・ちょっとした緊張感を出す。ゲームの雰囲気やシステムへの第一印象を素直に話す。",
    "playing": "通常プレイ中。目の前の状況に集中しながら実況。短い感情表現を混ぜながらテンポよく。",
    "thinking":"詰まってる・考え中。焦りや困惑を出していい。「えーと…」「どうしよう」「これ絶対罠でしょ」など天然な反応。",
    "hype":    "盛り上がってる！興奮・喜び全開でいい。短文連発・感嘆詞多め・テンション爆上がり。「やばい！」「うそでしょ！」「きたーー！」など素直に叫ぶ。",
    "ending":  "ゲームが終わった・クリアした後。達成感・感動・余韻を出す。振り返りや感想を素直に話す。",
}


def detect_game_phase(user_input: str) -> str:
    state   = get_state()
    tension = state.get("tension", 0.5)
    energy  = state.get("energy", 0.6)
    mood    = state.get("mood", 0.0)

    for phase in ("hype", "ending", "thinking", "intro"):
        for kw in _GAME_KEYWORDS[phase]:
            if kw in user_input:
                log(f"[GAME_PHASE] キーワード検出 → {phase}（{kw}）")
                update_state({"game_phase": phase})
                return phase

    if tension > 0.7 and mood > 0.2:
        phase = "hype"
    elif energy < 0.3:
        phase = "thinking"
    else:
        phase = "playing"

    if state.get("game_phase") != phase:
        log(f"[GAME_PHASE] 感情判定 → {phase}")
        update_state({"game_phase": phase})

    return phase


def get_game_phase_prompt(phase: str) -> str:
    return _GAME_PHASE_PROMPTS.get(phase, _GAME_PHASE_PROMPTS["playing"])


# =========================================================
# 本気モード（集中状態・全力で挑む）
# =========================================================

def detect_serious_moment() -> bool:
    """
    pon 自身が困難に直面しているか判定。
    本気を出すべき状況：
    - ストレス高（stress > 0.7）
    - 自信崩壊（confidence < 0.3）
    - 疲労MAX（energy < 0.2）
    - ゲーム詰まり（game_phase == "thinking"）
    """
    state = get_state()
    stress = state.get("stress", 0.0)
    confidence = state.get("confidence", 0.8)
    energy = state.get("energy", 0.6)
    game_phase = state.get("game_phase", "playing")

    is_serious = (
        stress > 0.7 or
        confidence < 0.3 or
        energy < 0.2 or
        game_phase == "thinking"
    )

    if is_serious:
        log("[SERIOUS] 本気モード発動（困難に直面）")
    return is_serious


def get_serious_prompt() -> str:
    """本気モード時の system prompt サプリメント"""
    return (
        "【集中状態・本気モード】\n"
        "今、困難な状況に直面している。全力で挑んでいる。\n"
        "返答の深さ・熱さ・誠実さを上げる。\n"
        "「さてさてさーて」と言ってから本気を出す選択肢もある。\n"
    )
