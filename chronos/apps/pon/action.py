"""
apps/pon/action.py
------------------
pon の自律行動決定エンジン。

pon の内部状態から「次に何をするか」を決定する。
- respond: 通常の返答
- serious_declare: 本気宣言（「さてさてさーて」）
- silent: 沈黙
"""

import time
from engine.state import get_state, update_state
from observation.logger import log


def evaluate_difficulty() -> float:
    """
    pon が今、どのくらい困難に直面しているかスコア化。
    0.0（楽） ～ 1.0（絶望的）

    DEBUG_MODE 時は強制値を返す。
    """
    state = get_state()

    # === デバッグモード: 困難度強制設定 ===
    if state.get("DEBUG_MODE") and state.get("DEBUG_difficulty") is not None:
        debug_val = state.get("DEBUG_difficulty")
        log(f"[DEBUG] 困難度強制: {debug_val}")
        return float(debug_val)

    stress = state.get("stress", 0.0)
    confidence = state.get("confidence", 0.8)
    energy = state.get("energy", 0.6)
    game_phase = state.get("game_phase", "playing")

    # 困難スコア計算
    score = 0.0

    # ストレス高い → 困難
    score += stress * 0.3

    # 自信がない → 困難
    score += (1.0 - confidence) * 0.4

    # エネルギーない → 困難
    score += (1.0 - energy) * 0.2

    # ゲーム詰まり → 困難 MAX
    if game_phase == "stuck":
        score += 0.4

    return min(1.0, score)


def should_enter_serious_mode_declared() -> bool:
    """
    宣言型の本気モード（月1-2回）。
    「さてさてさーて」と言ってから本気を出す。
    本気の50-60%を使う。
    """
    state = get_state()

    # 既に宣言型本気モード中 → 継続チェック
    if state.get("serious_mode_declared"):
        cooldown = state.get("serious_cooldown_declared", time.time())
        if time.time() < cooldown:
            return True
        else:
            log("[ACTION] 宣言型本気モード終了")
            update_state({"serious_mode_declared": False, "serious_cooldown_declared": 0.0})
            return False

    # 困難度が 0.85 以上
    difficulty = evaluate_difficulty()
    if difficulty < 0.85:
        return False

    # クールダウン: 30日（月1-2回）
    # DEBUG_MODE 時はクールダウン無視
    if not state.get("DEBUG_MODE"):
        last_declared = state.get("last_serious_declared_time", 0.0)
        if time.time() - last_declared < 30 * 86400:
            return False

    log(f"[ACTION] 宣言型本気発動（月1-2回）difficulty={difficulty:.2f}")
    update_state({
        "serious_mode_declared": True,
        "serious_cooldown_declared": time.time() + 600.0,
        "last_serious_declared_time": time.time(),
    })
    return True


def should_enter_serious_mode_instinct() -> bool:
    """
    本能型の本気モード（半年に1回）。
    黙って計算してから、いきなり本気を出す。
    本気の100%を使う。宣言なし。
    """
    state = get_state()

    # 既に本能型本気モード中 → 継続チェック
    if state.get("serious_mode_instinct"):
        cooldown = state.get("serious_cooldown_instinct", time.time())
        if time.time() < cooldown:
            return True
        else:
            log("[ACTION] 本能型本気モード終了")
            update_state({"serious_mode_instinct": False, "serious_cooldown_instinct": 0.0})
            return False

    # 困難度が 0.95 以上（極限）
    difficulty = evaluate_difficulty()
    if difficulty < 0.95:
        return False

    # クールダウン: 180日（半年に1回）
    # DEBUG_MODE 時はクールダウン無視
    if not state.get("DEBUG_MODE"):
        last_instinct = state.get("last_serious_instinct_time", 0.0)
        if time.time() - last_instinct < 180 * 86400:
            return False

    log(f"[ACTION] 本能型本気発動（半年に1回・真の本気）difficulty={difficulty:.2f}")
    update_state({
        "serious_mode_instinct": True,
        "serious_cooldown_instinct": time.time() + 600.0,
        "last_serious_instinct_time": time.time(),
    })
    return True


def decide_action(user_input: str = "") -> str:
    """
    pon の次の行動を決定。

    戻り値:
      "respond" → 通常の返答
      "serious_declare" → 宣言型本気（「さてさてさーて」+ 本気返答）
      "serious_instinct" → 本能型本気（黙って計算 → いきなり本気返答）
      "silent" → 沈黙（何も言わない）
    """
    state = get_state()

    # === 本能型本気判定（優先度: 最高） ===
    # 極限の困難で、いきなり本気になる
    # ※ should_enter_serious_mode_instinct() が state を変更するため、事前チェックが必須
    if not state.get("serious_mode_instinct"):
        if should_enter_serious_mode_instinct():
            return "serious_instinct"

    # === 宣言型本気判定 ===
    # ※ should_enter_serious_mode_declared() が state を変更するため、事前チェックが必須
    if not state.get("serious_mode_declared"):
        if should_enter_serious_mode_declared():
            return "serious_declare"

    # === エネルギー枯渇 → 沈黙 ===
    energy = state.get("energy", 0.6)
    if energy < 0.1:
        return "silent"

    # === テンション低 + 寂しくない → 沈黙傾向 ===
    mood = state.get("mood", 0.0)
    lonely = state.get("desire", {}).get("feeling_lonely", 0.0)
    if mood < -0.5 and lonely < 0.3:
        import random
        if random.random() < 0.3:  # 30% の確率で沈黙
            return "silent"

    # === デフォルト: 返答 ===
    return "respond"


def get_serious_declaration() -> str:
    """本気宣言のセリフを返す"""
    import random
    declarations = [
        "さてさてさーて…！",
        "よし、本気出そ！",
        "ここは全力だ…！",
        "さてさてさーて、全力でいくぞ！",
    ]
    return random.choice(declarations)
