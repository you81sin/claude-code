"""
apps/pon/silence.py
--------------------
沈黙・自発トーク・フォールバックのフレーズ管理。
phrases.py + silence_type.py を統合。
"""

import random
from engine.state import get_state, update_state
from observation.logger import log


# =========================================================
# レベル別フレーズ
# =========================================================

_SILENCE_PHRASES = {
    "low":  ["……", "…し、静かだね", "…呼んだ？", "…ん？", "…ちょっと"],
    "mid":  ["静かだね〜", "……ねえ、いる？", "なんか静かだな", "呼んだ？", "……どしたの"],
    "high": ["静かだね、何してるの？", "ねえ、いるー？", "……暇？", "なんか話そうよ", "どしたの、黙ってて"],
}

_AUTO_PHRASES = {
    "low":  ["ね、ねえ…", "…気になってること、ある？", "ちょっと話しかけていい？", "…ねえ、いる？"],
    "mid":  ["ねえ聞いて！", "ちょっと気になったんだけど", "今何してるの？", "なんか話したくなった", "ね、暇？"],
    "high": ["ねえねえ！", "ちょっといい？", "聞いてほしいことあるんだけど", "なんか話しかけたくなった", "今何してるー？"],
}

_FALLBACK_PHRASES = {
    "low":  ["…ちょっと待って", "…うーん", "…あれ", "ちょっと…"],
    "mid":  ["ちょっと待って", "うーん…", "あれ、なんだっけ", "うーん…"],
    "high": ["ちょっと待ってね", "うーん、なんだろ", "少し待って", "…ん"],
}

# =========================================================
# 沈黙タイプ別フレーズ
# =========================================================

_SILENCE_TYPE_PHRASES = {
    "waiting":   ["……", "…ん〜", "ふむ…", "…どうしよっかな", "…ねえ"],
    "loading":   ["ちょっと待って…", "えーと…（考え中）", "…うーん", "少しだけ待って", "…（頭の中で整理してる）"],
    "thinking":  ["うーん…どうすればいいんだろ", "…これ詰まった", "えっと…わかんない", "……どこ行けばいいの", "なんでだろ…", "むずい…"],
    "accident":  ["…あ、えっと", "え…あれ", "……", "…なんだっけ", "あ…ごめ、ちょっと"],
    "emotional": ["……", "…なんか、うまく言えない", "…ちょっと待って", "…落ち着く", "…うん"],
}


def _tier(level: float) -> str:
    if level < 15:  return "low"
    if level < 50:  return "mid"
    return "high"


# =========================================================
# 沈黙タイプ判定
# =========================================================

def _detect_silence_type() -> str:
    state          = get_state()
    stress         = state.get("stress", 0.2)
    confidence     = state.get("confidence", 0.85)
    mood           = state.get("mood", 0.0)
    game_phase     = state.get("game_phase", "playing")
    streaming_mode = state.get("streaming_mode", "chat")

    if abs(mood) > 0.6:
        silence_type = "emotional"
    elif stress > 0.65 or confidence < 0.25:
        silence_type = "accident"
    elif streaming_mode == "game" and game_phase == "thinking":
        silence_type = "thinking"
    elif streaming_mode == "game":
        silence_type = "loading"
    else:
        silence_type = "waiting"

    if state.get("silence_type") != silence_type:
        log(f"[SILENCE] タイプ判定: {silence_type}")
        update_state({"silence_type": silence_type})

    return silence_type


# =========================================================
# 公開インターフェース
# =========================================================

def get_silence_phrase(level: float) -> str:
    """通常の沈黙フレーズ（レベル別）"""
    return random.choice(_SILENCE_PHRASES[_tier(level)])


def get_silence_output() -> str:
    """
    沈黙タイプを判定して常にLLMトークンを返す。
    フレーズリストは使わずLLMで自然な返答を生成する。
    """
    silence_type = _detect_silence_type()
    return f"__silence_llm_{silence_type}__"  # 常にLLMで生成


def get_silence_prompt(silence_type: str) -> str:
    """LLM用の沈黙プロンプトを返す（視聴者に話しかけるスタイル・毎回違う切り口）"""

    # waitingは多様なパターンをランダムに選ぶ
    _waiting_prompts = [
        "静かな時間。視聴者に話しかけて。「ねえ、みんないる？」「何してるの？」など。1文で。冒頭は「え、あ」禁止。",
        "視聴者に自分の今の気分や考えを自然に打ち明ける。雑談のノリで。1文で。冒頭は「え、あ」禁止。",
        "視聴者に何か質問を投げかけて。好きなものや最近のことなど。1文で。冒頭は「え、あ」禁止。",
        "視聴者への軽い独り言。「そういえば〜」「なんか〜な気分」など話題を自由に。1文で。冒頭は「え、あ」禁止。",
        "視聴者に今日あったことや思ったことをひとこと話しかける。自然に。1文で。冒頭は「え、あ」禁止。",
        "視聴者に「暇？」「話しかけてよ〜」という感じで自然に呼びかける。1文で。冒頭は「え、あ」禁止。",
    ]

    if silence_type == "waiting":
        return random.choice(_waiting_prompts)

    prompts = {
        "loading":   "ゲームの読み込み中。「ちょっと待ってて」「今読み込み中だよ〜」など視聴者に話しかけながら待機。1文で。冒頭は「え、あ」禁止。",
        "thinking":  "ゲームで詰まっている。「うーん、どうすればいいと思う？」「助けて〜」など視聴者に助けを求める感じで。1文で。冒頭は「え、あ」禁止。",
        "accident":  "少しパニック。「あっ、ちょっと待って！」「頭真っ白になった〜」など混乱しつつ視聴者に話しかける。1文で。冒頭は「え、あ」禁止。",
        "emotional": "感情が揺れている。「……なんか、うまく言えないけど」など素直に視聴者に気持ちを話しかける。1文で。冒頭は「え、あ」禁止。",
    }
    return prompts.get(silence_type, random.choice(_waiting_prompts))


def get_auto_phrase(level: float) -> str:
    return random.choice(_AUTO_PHRASES[_tier(level)])


def get_fallback_phrase(level: float) -> str:
    return random.choice(_FALLBACK_PHRASES[_tier(level)])
