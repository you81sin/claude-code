"""
memory/engine.py
-----------------
Chronos 永続記憶エンジン。
記憶を2種類に分けて管理する。

memory_self.json  → 自分の発言・好み（重要度高・減衰遅）
memory_chat.json  → 会話内容（重要度低・減衰早）
"""

import os
import json
import time
import math
from hashlib import sha256

# numpy は任意。あれば使い、なければ純Pythonで動く（核を依存ゼロで起動可能にするため）。
try:
    import numpy as np  # noqa: F401
    _HAS_NUMPY = True
except Exception:
    np = None
    _HAS_NUMPY = False

MEM_LIMIT       = 500
DECAY_SEC_SELF  = 86400 * 30   # 30日（自分の記憶）
DECAY_SEC_CHAT  = 86400 * 7    # 7日（会話の記憶）

# 除外ワード（挨拶・リアクション系）
NOISE_WORDS = {
    "草", "w", "笑", "ww", "www", "ｗ", "ｗｗ",
    "おはよう", "こんにちは", "こんばんは", "おやすみ",
    "ありがとう", "ありがとうございます", "よろしく",
    "すごい", "えー", "へー", "なるほど", "そうなんだ",
    "！", "？", "…", "〜",
}


def embed(text: str) -> list:
    """
    テキストを固定長(32次元)ベクトルに変換する。
    ※現状は sha256 ハッシュベースの簡易ベクトル（意味検索ではない）。
      将来ここを本物の埋め込みモデルに差し替えると「似た記憶を引く」が機能する。
    戻り値: 正規化済みの list[float]（JSONにそのまま保存できる）。
    """
    h = sha256(text.encode()).digest()
    v = [float(b) for b in h]                       # uint8 を 0〜255 の float に
    norm = math.sqrt(sum(x * x for x in v)) + 1e-8
    return [x / norm for x in v]


def _dot(a: list, b: list) -> float:
    """内積（純Python。numpy不要）。"""
    return float(sum(x * y for x, y in zip(a, b)))


def _mem_path(app_id: str, mem_type: str) -> str:
    """
    mem_type: "self" or "chat"
    """
    filename = f"memory_{mem_type}.json"
    return os.path.join("apps", app_id, "data", filename)


def load_memory(app_id: str, mem_type: str = "chat") -> list:
    path = _mem_path(app_id, mem_type)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_memory(app_id: str, mem_type: str, mem: list) -> None:
    path = _mem_path(app_id, mem_type)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mem[-MEM_LIMIT:], f, ensure_ascii=False, indent=2)


def _decay(m: dict, mem_type: str) -> float:
    decay_sec = DECAY_SEC_SELF if mem_type == "self" else DECAY_SEC_CHAT
    age = time.time() - m.get("t", time.time())
    return m.get("importance", 1.0) * float(math.exp(-age / decay_sec))


def _is_noise(text: str) -> bool:
    """挨拶・草などのノイズワードを除外する"""
    clean = text.replace("user:", "").replace("pon:", "").strip()
    if len(clean) <= 3:
        return True
    for word in NOISE_WORDS:
        if clean == word:
            return True
    return False


def add_memory(app_id: str, text: str, importance: float = 1.0, mem_type: str = "chat",
               emotion: str = "", impact: float = 0.0) -> None:
    """
    記憶を追加する。

    mem_type:
      "self" → ponの発言・好み（重要度高・減衰遅）
      "chat" → 視聴者コメント（減衰早）
    emotion: その時の感情ラベル（例: "嬉しい" "落ち込んだ" "興奮した"）
    impact:  感情の強さ 0.0〜1.0（高いほど記憶に残りやすい）
    """
    # ノイズワードは保存しない
    if _is_noise(text):
        return

    mem = load_memory(app_id, mem_type)
    entry = {
        "text":       text,
        "vector":     embed(text),
        "importance": float(importance),
        "t":          time.time(),
        "type":       mem_type,
        "emotion":    emotion,
        "impact":     float(impact),
    }
    mem.append(entry)
    save_memory(app_id, mem_type, mem)


def search_memory(app_id: str, query: str, k: int = 5) -> list:
    """
    self + chat 両方から検索。
    self記憶を優先してスコアリング。
    """
    results = []

    for mem_type in ("self", "chat"):
        mem = load_memory(app_id, mem_type)
        if not mem:
            continue

        qv = embed(query)
        for m in mem:
            mv    = m["vector"]
            score = _dot(qv, mv) * _decay(m, mem_type)
            # self記憶はスコアを2倍に
            if mem_type == "self":
                score *= 2.0
            # impactが高い記憶は最大1.5倍（強い感情の記憶は残りやすい）
            impact = m.get("impact", 0.0)
            if impact > 0.0:
                score *= (1.0 + impact * 0.5)
            results.append((score, m))

    results.sort(reverse=True, key=lambda x: x[0])
    return [m for _, m in results[:k]]


def get_recent_memory(app_id: str, n: int = 20) -> list:
    """最新n件の記憶（chat）を返す"""
    mem = load_memory(app_id, "chat")
    return mem[-n:]


def extract_and_save_mannerisms(app_id: str, user_text: str) -> None:
    """
    ユーザーのセリフから口癖パターンを抽出して memory_self.json に保存。

    例: ユーザーが「メンド」と言う
    → memory_self.json に {"type": "mannerism", "phrase": "メンド", ...} を追加
    → 次回, pon が同じ状況で「メンド」を時々使う
    """
    # 検出対象の口癖パターン（ユーザーが言いそうなフレーズ）
    mannerism_patterns = {
        "メンド": "面倒な・気が進まない状況で使う",
        "知らんけど": "確信がない・不確定な時に使う",
        "さてさてさーて": "何か起こった・気になる時に使う",
        "あ、そっか": "気づいた・納得した時に使う",
        "ヤバい": "驚き・困惑・良い悪い両方で使う",
    }

    detected = []
    for phrase, context in mannerism_patterns.items():
        if phrase in user_text:
            detected.append((phrase, context))

    if not detected:
        return

    mem = load_memory(app_id, "self")

    for phrase, context in detected:
        # 既存の口癖を検索
        found = False
        for entry in mem:
            if entry.get("type") == "mannerism" and entry.get("phrase") == phrase:
                # 出現回数をインクリメント・タイムスタンプ更新
                entry["count"] = entry.get("count", 1) + 1
                entry["t"] = time.time()
                entry["last_seen"] = time.time()
                found = True
                break

        if not found:
            # 新しい口癖として追加
            mem.append({
                "type": "mannerism",
                "phrase": phrase,
                "context": context,
                "count": 1,
                "t": time.time(),
                "last_seen": time.time(),
                "importance": 0.6,  # 口癖は中程度の重要度
                "vector": embed(phrase),
            })

    save_memory(app_id, "self", mem)


def get_learned_mannerisms(app_id: str, threshold: int = 1) -> str:
    """
    pon が学習した口癖を取得して、プロンプト用テキストに変換。

    threshold: 出現回数がこの値以上の口癖のみを返す（デフォルト1=全て）
    戻り値: 「ユーザーがよく『メンド』と言う。時々使ってもいい」みたいなテキスト
    """
    mem = load_memory(app_id, "self")

    # type == "mannerism" で絞る
    mannerisms = [m for m in mem if m.get("type") == "mannerism"]

    if not mannerisms:
        return ""

    # 出現回数でソート（多いものを上位に）
    mannerisms.sort(key=lambda m: m.get("count", 0), reverse=True)

    lines = []
    for m in mannerisms:
        count = m.get("count", 0)
        if count >= threshold:
            phrase = m.get("phrase", "")
            context = m.get("context", "")
            lines.append(f"「{phrase}」（{context}。出現{count}回）")

    if not lines:
        return ""

    return "【学習した視聴者の口癖】" + "、".join(lines) + "。時々自分も使ってみてOK。\n"


# === 会話履歴（apps/pon/store.pyより統合）===
from collections import deque

_HISTORY: deque = deque(maxlen=50)

def add_history(role: str, text: str) -> None:
    _HISTORY.append({"role": role, "text": text})

def get_history(n: int = 10) -> list:
    return list(_HISTORY)[-n:]

def clear_history() -> None:
    _HISTORY.clear()
