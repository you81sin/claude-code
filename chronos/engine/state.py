"""
engine/state.py
----------------
Chronos 状態空間。
履歴蓄積型・微小ランダム対応。
"""

import time
import random

_STATE = {
    # === デバッグ ===
    "DEBUG_MODE":       False,  # デバッグモード（テスト時に ON）
    "DEBUG_difficulty": None,   # 困難度強制設定（テスト用）

    # === 基本 ===
    "last_event_time":  time.time(),
    "streaming_mode":   "chat",
    "is_typing":        False,

    # === 注意・疲労 ===
    "attention":        0.6,
    "topic_fatigue":    0.0,

    # === 感情状態空間 ===
    "energy":           0.7,
    "tension":          0.5,
    "sulky":            0.0,
    "confidence":       0.85,
    "mood":             0.0,

    # === 起動時状態 ===
    "startup_mood":     "normal",  # tired / low / normal / good / hyper

    # === ストレス（履歴付き）===
    "stress":           0.2,
    "stress_history":   [],

    # === 欲求 ===
    "desire": {
        "ego_search":      0.2,  # エゴサ欲求
        "want_lazy":       0.1,  # サボり欲求
        "want_sing":       0.1,  # 歌いたい
        "feeling_lonely":  0.1,  # 寂しい
        "want_praise":     0.2,  # 褒められたい
        "maniac_talk":     0.2,  # マニアック語り
        "want_talk_va":    0.1,  # 声優自発トーク
    },

    # === 状態空間（感情の源泉）===
    "fear_of_failure":      0.3,
    "desire_for_attention": 0.5,
    "praise_sensitivity":   0.7,
    "attachment":           {},  # パターン別愛着度

    # === 配信アーク ===
    "era":              "debut",

    # === ゲームフェーズ ===
    "game_phase":       "playing",

    # === 沈黙演出 ===
    "silence_type":     "natural",

    # === 行動理由 ===
    "action_reason":    "",

    # === 天気 ===
    "weather":          None,   # fetch_weather() の結果 or None

    # === キャッシュ ===
    "persona_profile":  None,
    "generated_name":   None,
    "strengths":        None,

    # === pon の自律行動状態 ===
    "serious_mode":     False,     # 本気モード中か
    "serious_cooldown": 0.0,       # 本気モード終了時刻（unix time）
    "action_decision":  "respond", # 次の行動: respond / silent / serious_declare
    "internal_goal":    None,      # pon が今向き合っている目標（ゲーム攻略など）
}


def get_state() -> dict:
    return _STATE


def update_state(patch: dict) -> None:
    _STATE.update(patch)


# =========================================================
# 微小ランダム（固定AI感を減らす）
# =========================================================

def _jitter(value: float, sigma: float = 0.02) -> float:
    """ガウスノイズを加えてclamp"""
    return max(0.0, min(1.0, value + random.gauss(0, sigma)))


def tick_state(event_type: str = "idle") -> None:
    """
    毎イベントごとに状態を微小変化させる。
    同じ入力でも毎回微妙に違う反応が生まれる。
    """
    now = time.time()

    # === 時間減衰 ===
    dt = now - _STATE.get("last_event_time", now)
    _STATE["attention"]  *= (0.99 ** dt)
    _STATE["energy"]     *= (0.999 ** dt)
    _STATE["tension"]    *= (0.98 ** dt)
    _STATE["sulky"]      *= (0.97 ** dt)
    _STATE["stress"]     *= (0.995 ** dt)

    # === イベント別変化 ===
    if event_type == "user_input":
        _STATE["attention"]  = min(1.0, _STATE["attention"] + 0.1)
        _STATE["tension"]    = min(1.0, _STATE["tension"]   + 0.05)
        _STATE["desire"]["ego_search"] = max(0.0, _STATE["desire"]["ego_search"] - 0.1)
        _STATE["desire"]["feeling_lonely"] = max(0.0, _STATE["desire"]["feeling_lonely"] - 0.15)

    elif event_type == "silence":
        _STATE["desire"]["ego_search"]  = min(1.0, _STATE["desire"]["ego_search"]  + 0.05)
        _STATE["desire"]["feeling_lonely"]  = min(1.0, _STATE["desire"]["feeling_lonely"]  + 0.08)
        _STATE["sulky"] = min(1.0, _STATE["sulky"] + 0.03)

    elif event_type == "auto":
        _STATE["energy"] = max(0.0, _STATE["energy"] - 0.01)

    # === 欲求の自然蓄積 ===
    for key in _STATE["desire"]:
        _STATE["desire"][key] = min(1.0, _STATE["desire"][key] + random.uniform(0.001, 0.005))

    # === 微小ランダム（制御不能部分）===
    _STATE["energy"]     = _jitter(_STATE["energy"],     0.01)
    _STATE["tension"]    = _jitter(_STATE["tension"],    0.01)
    _STATE["confidence"] = _jitter(_STATE["confidence"], 0.015)
    _STATE["mood"]       = max(-1.0, min(1.0,
        _STATE["attention"] - _STATE["topic_fatigue"] + random.gauss(0, 0.02)
    ))

    # === 配信アーク更新 ===
    _update_era()

    _STATE["last_event_time"] = now


def add_stress(reason: str, value: float) -> None:
    """ストレスを履歴付きで追加"""
    _STATE["stress"] = min(1.0, _STATE["stress"] + value)
    _STATE["stress_history"].append({
        "reason": reason,
        "value":  value,
        "t":      time.time(),
    })
    # 履歴は最大20件
    if len(_STATE["stress_history"]) > 20:
        _STATE["stress_history"] = _STATE["stress_history"][-20:]


def update_attachment(pattern: str, delta: float) -> None:
    """視聴者パターンへの愛着度を更新（微小ランダム付き）"""
    current = _STATE["attachment"].get(pattern, 0.5)
    noise   = random.gauss(0, 0.02)
    _STATE["attachment"][pattern] = max(0.0, min(1.0, current + delta + noise))


def update_praise_sensitivity(praised: bool) -> None:
    """
    褒められると感受性が変化。
    大量に褒められると慣れる（sensitivity低下）。
    """
    if praised:
        # 褒められるたびに少し慣れる
        _STATE["praise_sensitivity"] = max(0.1, _STATE["praise_sensitivity"] - 0.01)
    else:
        # 褒められない時間が続くと感受性が戻る
        _STATE["praise_sensitivity"] = min(1.0, _STATE["praise_sensitivity"] + 0.005)


def _update_era() -> None:
    """レベルに応じて配信アークを更新"""
    try:
        from apps.pon.growth import get_level
        level = get_level()
        if level < 20:
            _STATE["era"] = "debut"
        elif level < 50:
            _STATE["era"] = "growth"
        elif level < 80:
            _STATE["era"] = "stable"
        else:
            _STATE["era"] = "veteran"
    except Exception:
        pass


def get_dominant_desire() -> tuple[str, float]:
    """最も強い欲求を返す"""
    desire = _STATE["desire"]
    if not desire:
        return ("none", 0.0)
    key = max(desire, key=desire.get)
    return (key, desire[key])


# =========================================================
# 起動時状態ランダム化
# =========================================================

_STARTUP_MODE_JP = {
    "tired":  "疲れ気味",
    "low":    "やや元気なし",
    "normal": "普通",
    "good":   "元気",
    "hyper":  "ハイテンション",
}


def init_startup_state() -> str:
    """
    起動時に「今日の状態」をランダム設定。
    毎回違うponが生まれる。
    戻り値: モード名 ("tired" / "low" / "normal" / "good" / "hyper")
    """
    mode = random.choices(
        ["tired", "low", "normal", "good", "hyper"],
        weights=[0.15, 0.20, 0.35, 0.20, 0.10],
        k=1,
    )[0]

    presets: dict[str, dict] = {
        "tired": dict(
            energy=random.uniform(0.20, 0.40),
            tension=random.uniform(0.20, 0.40),
            confidence=random.uniform(0.45, 0.65),
            mood=random.uniform(-0.40, -0.05),
            stress=random.uniform(0.30, 0.55),
            sulky=random.uniform(0.10, 0.35),
            attention=random.uniform(0.30, 0.50),
        ),
        "low": dict(
            energy=random.uniform(0.40, 0.55),
            tension=random.uniform(0.30, 0.50),
            confidence=random.uniform(0.60, 0.78),
            mood=random.uniform(-0.20, 0.10),
            stress=random.uniform(0.15, 0.35),
            sulky=random.uniform(0.00, 0.15),
            attention=random.uniform(0.45, 0.60),
        ),
        "normal": dict(
            energy=random.uniform(0.55, 0.75),
            tension=random.uniform(0.40, 0.60),
            confidence=random.uniform(0.70, 0.88),
            mood=random.uniform(-0.10, 0.20),
            stress=random.uniform(0.10, 0.28),
            sulky=random.uniform(0.00, 0.08),
            attention=random.uniform(0.55, 0.70),
        ),
        "good": dict(
            energy=random.uniform(0.70, 0.85),
            tension=random.uniform(0.45, 0.65),
            confidence=random.uniform(0.80, 0.95),
            mood=random.uniform(0.15, 0.40),
            stress=random.uniform(0.05, 0.18),
            sulky=0.0,
            attention=random.uniform(0.65, 0.80),
        ),
        "hyper": dict(
            energy=random.uniform(0.85, 1.00),
            tension=random.uniform(0.55, 0.80),
            confidence=random.uniform(0.78, 0.97),
            mood=random.uniform(0.30, 0.60),
            stress=random.uniform(0.08, 0.25),
            sulky=0.0,
            attention=random.uniform(0.75, 0.95),
        ),
    }

    _STATE.update(presets[mode])
    _STATE["startup_mood"] = mode

    # 欲求初期値もモードに合わせて調整
    d = _STATE["desire"]
    if mode == "tired":
        d["feeling_lonely"] = random.uniform(0.30, 0.60)
        d["want_lazy"]       = random.uniform(0.40, 0.70)
        d["want_praise"]     = random.uniform(0.30, 0.55)
    elif mode == "low":
        d["feeling_lonely"] = random.uniform(0.20, 0.40)
        d["want_praise"]     = random.uniform(0.25, 0.45)
    elif mode == "hyper":
        d["want_talk_va"]   = random.uniform(0.40, 0.70)
        d["maniac_talk"]    = random.uniform(0.35, 0.60)
        d["want_praise"]    = random.uniform(0.30, 0.55)

    return mode
