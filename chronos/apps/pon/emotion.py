"""
apps/pon/emotion.py
--------------------
ponの感情状態を管理。
起動時にランダム初期化。
配信中に変化。
永続化（emotion.json）。
"""

import os
import json
import random
import time
from observation.logger import log

EMOTION_PATH = os.path.join("apps", "pon", "data", "emotion.json")


def _default_emotion() -> dict:
    """起動時のランダム感情状態"""
    templates = [
        {"label": "元気",   "energy": 0.8, "mood": 0.4,  "tension": 0.6, "sulky": 0.0, "confidence": 0.8},
        {"label": "眠い",   "energy": 0.3, "mood": 0.0,  "tension": 0.2, "sulky": 0.1, "confidence": 0.5},
        {"label": "普通",   "energy": 0.6, "mood": 0.1,  "tension": 0.4, "sulky": 0.0, "confidence": 0.7},
        {"label": "拗ね",   "energy": 0.5, "mood": -0.2, "tension": 0.3, "sulky": 0.6, "confidence": 0.5},
        {"label": "テンション高い", "energy": 0.9, "mood": 0.6, "tension": 0.8, "sulky": 0.0, "confidence": 0.9},
        {"label": "微妙に病み",     "energy": 0.4, "mood": -0.4, "tension": 0.2, "sulky": 0.2, "confidence": 0.4},
        {"label": "調子乗り",       "energy": 0.8, "mood": 0.5, "tension": 0.7, "sulky": 0.0, "confidence": 0.95},
    ]

    base = random.choice(templates)
    # 微小ランダムを加える
    return {
        "label":      base["label"],
        "energy":     max(0.0, min(1.0, base["energy"]     + random.gauss(0, 0.05))),
        "mood":       max(-1.0, min(1.0, base["mood"]      + random.gauss(0, 0.05))),
        "tension":    max(0.0, min(1.0, base["tension"]    + random.gauss(0, 0.05))),
        "sulky":      max(0.0, min(1.0, base["sulky"]      + random.gauss(0, 0.02))),
        "confidence": max(0.0, min(1.0, base["confidence"] + random.gauss(0, 0.05))),
        "updated":    time.time(),
    }


def load_emotion() -> dict:
    if not os.path.exists(EMOTION_PATH):
        return None
    try:
        with open(EMOTION_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_emotion(emotion: dict) -> None:
    os.makedirs(os.path.dirname(EMOTION_PATH), exist_ok=True)
    with open(EMOTION_PATH, "w", encoding="utf-8") as f:
        json.dump(emotion, f, ensure_ascii=False, indent=2)


def get_or_init_emotion() -> dict:
    """
    起動時に感情を初期化。
    startup_mood（engine/state.py）と矛盾しないテンプレートを選ぶ。
    """
    from engine.state import get_state
    startup_mood = get_state().get("startup_mood", "normal")

    # startup_mood → 使えるテンプレートラベルのマッピング
    _MOOD_TEMPLATES = {
        "tired":  ["眠い", "微妙に病み"],
        "low":    ["拗ね", "普通"],
        "normal": ["普通", "元気", "拗ね"],
        "good":   ["元気", "普通"],
        "hyper":  ["テンション高い", "調子乗り"],
    }
    allowed = _MOOD_TEMPLATES.get(startup_mood, ["普通"])

    templates = [
        {"label": "元気",           "energy": 0.8, "mood": 0.4,  "tension": 0.6, "sulky": 0.0, "confidence": 0.8},
        {"label": "眠い",           "energy": 0.3, "mood": 0.0,  "tension": 0.2, "sulky": 0.1, "confidence": 0.5},
        {"label": "普通",           "energy": 0.6, "mood": 0.1,  "tension": 0.4, "sulky": 0.0, "confidence": 0.7},
        {"label": "拗ね",           "energy": 0.5, "mood": -0.2, "tension": 0.3, "sulky": 0.6, "confidence": 0.5},
        {"label": "テンション高い", "energy": 0.9, "mood": 0.6,  "tension": 0.8, "sulky": 0.0, "confidence": 0.9},
        {"label": "微妙に病み",     "energy": 0.4, "mood": -0.4, "tension": 0.2, "sulky": 0.2, "confidence": 0.4},
        {"label": "調子乗り",       "energy": 0.8, "mood": 0.5,  "tension": 0.7, "sulky": 0.0, "confidence": 0.95},
    ]
    candidates = [t for t in templates if t["label"] in allowed]
    if not candidates:
        candidates = templates

    base = random.choice(candidates)
    emotion = {
        "label":      base["label"],
        "energy":     max(0.0, min(1.0, base["energy"]     + random.gauss(0, 0.05))),
        "mood":       max(-1.0, min(1.0, base["mood"]      + random.gauss(0, 0.05))),
        "tension":    max(0.0, min(1.0, base["tension"]    + random.gauss(0, 0.05))),
        "sulky":      max(0.0, min(1.0, base["sulky"]      + random.gauss(0, 0.02))),
        "confidence": max(0.0, min(1.0, base["confidence"] + random.gauss(0, 0.05))),
        "updated":    time.time(),
    }
    save_emotion(emotion)
    log(f"[EMOTION] 今日の調子: {emotion['label']} (energy={emotion['energy']:.2f} mood={emotion['mood']:.2f})")
    return emotion


def emotion_to_prompt(emotion: dict) -> str:
    """感情状態をLLMへの指示に変換"""
    label      = emotion.get("label", "普通")
    energy     = emotion.get("energy", 0.6)
    mood       = emotion.get("mood", 0.0)
    tension    = emotion.get("tension", 0.5)
    sulky      = emotion.get("sulky", 0.0)
    confidence = emotion.get("confidence", 0.7)

    parts = [f"今日の調子は「{label}」です。"]

    if energy < 0.3:
        parts.append("かなり眠い・だるい。語尾が減り返答が短くなる。")
    elif energy > 0.8:
        parts.append("元気いっぱい。テンポよく話す。")

    if mood < -0.3:
        parts.append("少し落ち込んでいる。でも配信は続ける。")
    elif mood > 0.4:
        parts.append("気分がいい。自然と明るいトーンになる。")

    if sulky > 0.4:
        parts.append("少し拗ねている。そっけない返答もあり。")

    if confidence < 0.4:
        parts.append("自信がない。言いかけてやめることもある。言葉が出てこない感じ。")
    elif confidence > 0.85:
        parts.append("今日は調子乗り気味。少し強気な発言が出るかも。")

    if tension > 0.7:
        parts.append("テンションが上がっている。「！」「！？」を多用し、短く弾むように話す。")
    elif tension < 0.3:
        parts.append("テンションが低い。「…」「ね」など穏やかな語尾で話す。")

    return " ".join(parts)
