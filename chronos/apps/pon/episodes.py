"""
apps/pon/episodes.py
---------------------
固定エピソード蓄積システム（viewer-shaped persona）

identity.jsonのepisodic_memory[]を管理する。
配信ごとに失敗エピソードが積み上がり、視聴者が
「ponってこういうやつだよな」と解釈できる余白を作る。

episodic_memory形式:
{
  "id":        "burned_omelet",
  "text":      "料理すると必ず焦がす",
  "weight":    0.8,      # 参照確率 0.0〜1.0
  "decay":     0.02,     # 毎配信ごとに下がる（古いエピソードが自然消滅）
  "last_used": "2026-05-15"
}
"""

import os
import json
import random
import time
from observation.logger import log

IDENTITY_PATH = os.path.join("apps", "pon", "data", "identity.json")

# デフォルトの初期エピソード（identity生成時に追加）
DEFAULT_EPISODES = [
    {"id": "forget_easily",     "text": "すぐ大事なことを忘れる",              "weight": 0.8, "decay": 0.01},
    {"id": "confident_wrong",   "text": "自信満々に言ったことが外れる",          "weight": 0.7, "decay": 0.01},
    {"id": "distracted",        "text": "話しながら急に別のことを考え始める",     "weight": 0.6, "decay": 0.01},
    {"id": "math_weakness",     "text": "数字が出てくるととたんに頭が真っ白になる", "weight": 0.7, "decay": 0.01},
    {"id": "overconfident",     "text": "得意分野の話になると止まらなくなる",     "weight": 0.8, "decay": 0.01},
]


def _load_identity() -> dict:
    if not os.path.exists(IDENTITY_PATH):
        return {}
    try:
        with open(IDENTITY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_identity(data: dict):
    os.makedirs(os.path.dirname(IDENTITY_PATH), exist_ok=True)
    with open(IDENTITY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_episodes():
    """identity.jsonにepisodic_memoryがなければデフォルトを追加"""
    data = _load_identity()
    if not data:
        return
    if "episodic_memory" not in data:
        episodes = []
        for ep in DEFAULT_EPISODES:
            episodes.append({
                **ep,
                "last_used": None,
                "created": time.strftime("%Y-%m-%d"),
            })
        data["episodic_memory"] = episodes
        _save_identity(data)
        log(f"[EPISODE] デフォルトエピソード追加: {len(episodes)}件")


def get_random_episodes(n: int = 2) -> list[str]:
    """
    重みに従ってランダムにエピソードを取得する。
    LLMプロンプトに埋め込む用。
    """
    data = _load_identity()
    episodes = data.get("episodic_memory", [])
    if not episodes:
        return []

    # weight に従って選択
    selected = []
    for ep in episodes:
        if random.random() < ep.get("weight", 0.5):
            selected.append(ep["text"])
        if len(selected) >= n:
            break

    return selected[:n]


def add_episode(text: str, weight: float = 0.7):
    """新しいエピソードを追加する（配信ごとの失敗蓄積）"""
    data = _load_identity()
    if not data:
        return

    episodes = data.get("episodic_memory", [])

    # 重複チェック
    if any(ep["text"] == text for ep in episodes):
        return

    episodes.append({
        "id":        f"ep_{int(time.time())}",
        "text":      text,
        "weight":    weight,
        "decay":     0.02,
        "last_used": None,
        "created":   time.strftime("%Y-%m-%d"),
    })
    data["episodic_memory"] = episodes
    _save_identity(data)
    log(f"[EPISODE] 新エピソード追加: {text}")


def decay_episodes():
    """古いエピソードのweightを下げる（自然消滅）"""
    data = _load_identity()
    if not data:
        return

    episodes = data.get("episodic_memory", [])
    today = time.strftime("%Y-%m-%d")
    changed = False

    new_episodes = []
    for ep in episodes:
        last = ep.get("last_used")
        if last and last != today:
            ep["weight"] = max(0.0, ep["weight"] - ep.get("decay", 0.02))
            changed = True
        if ep["weight"] > 0.05:  # 完全に消えたら除去
            new_episodes.append(ep)
        else:
            log(f"[EPISODE] エピソード消滅: {ep['text']}")

    if changed:
        data["episodic_memory"] = new_episodes
        _save_identity(data)
