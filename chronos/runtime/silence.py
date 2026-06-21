"""
runtime/scheduler.py
---------------------
チャンネルごとに独立したキューを持つ。
"""

from collections import deque

_QUEUES: dict[str, deque] = {}

def _get_queue(channel: str) -> deque:
    if channel not in _QUEUES:
        _QUEUES[channel] = deque()
    return _QUEUES[channel]

def push_event(event: dict, channel: str = "pon"):
    _get_queue(channel).append(event)

def pop_event(channel: str = "pon"):
    q = _get_queue(channel)
    if q:
        return q.popleft()
    return None


import time
import random
from engine.state import get_state

def make_auto_loop(channel: str):
    def loop():
        while True:
            # 3分ごとに自発トーク
            time.sleep(180)
            state = get_state()
            # 入力中はスキップ
            if state.get("is_typing", False):
                continue
            if random.random() < state["attention"]:
                push_event({"type": "input", "source": "ai", "payload": "__auto__", "channel": channel}, channel)
    return loop


"""
runtime/silence.py
-------------------
沈黙検知ループ。
"""

import time
import random
import threading
from engine.state import get_state
from observation.logger import log

"""
沈黙フェーズ設計（人間らしいパターン）:

  【早期フェーズ】 沈黙 0〜2分 かつ 3回未満
      → 30〜40秒ごとに自然につぶやく（間を埋める感じ）
      → 「あれ、静かだな〜」「ねえいる？」「まあいっか…」のイメージ

  【静寂フェーズ】 沈黙 2〜10分
      → 何も言わない（集中してるか、単純に間が空いた状態）

  【長期フェーズ】  沈黙 10分超
      → 10〜20分に1回だけぽつりと一言
"""

def make_silence_loop(channel: str):
    # クロージャで状態を管理（チャンネルごとに独立）
    fired_at     = {"t": 0.0}       # 最後に発火した時刻
    early        = {"count": 0,     # 早期フェーズの発火回数
                    "last_user": None}  # 最後にユーザーが話した時刻
    startup      = {"t": 0.0}       # 起動時刻（初回ループで設定）

    def loop():
        print(f"[SILENCE] スレッド起動: {channel}")
        while True:
            try:
                time.sleep(10)
                state      = get_state()
                now        = time.time()

                # 起動時刻を初回のみ設定
                if startup["t"] == 0.0:
                    startup["t"] = now

                # 沈黙 = ユーザーが最後に話してからの経過時間
                # （AIが話しても沈黙カウントはリセットしない）
                last_user_event = state.get("last_viewer_comment_time") or startup["t"]
                silence = now - last_user_event

                # ユーザーが話した → 早期カウントをリセット
                if early["last_user"] is None:
                    early["last_user"] = last_user_event
                elif last_user_event != early["last_user"]:
                    early["count"]     = 0
                    early["last_user"] = last_user_event
                    log(f"[SILENCE] カウントリセット ch={channel}")

                log(f"[SILENCE] 監視中 ch={channel} silence={silence:.0f}秒 "
                    f"early={early['count']}")

                # 入力中はスキップ
                if state.get("is_typing", False):
                    continue

                if silence < 25:
                    continue

                # =========================================================
                # フェーズ判定
                # =========================================================

                if silence < 120 and early["count"] < 3:
                    # 【早期フェーズ】 2分以内 かつ まだ3回未満
                    # 30〜40秒ごとにつぶやく（自然な間埋め）
                    if now - fired_at["t"] < 30:
                        continue
                    prob  = 0.65
                    phase = "early"

                elif silence < 600:
                    # 【静寂フェーズ】 2〜10分は黙ってる
                    continue

                else:
                    # 【長期フェーズ】 10分超：10〜20分に1回
                    # クールダウン750秒（12.5分）+ 確率0.70 → 平均15分に1回くらい
                    if now - fired_at["t"] < 750:
                        continue
                    prob  = 0.70
                    phase = "long"

                if random.random() < prob:
                    log(f"[SILENCE] 発火 ch={channel} phase={phase} "
                        f"silence={silence:.0f}秒 early_count={early['count']}")
                    fired_at["t"] = now
                    if phase == "early":
                        early["count"] += 1
                    push_event(
                        {"type": "input", "source": "ai", "payload": "__silence__", "channel": channel},
                        channel
                    )

            except Exception as e:
                print(f"[SILENCE ERROR] {channel}: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)

    return loop
