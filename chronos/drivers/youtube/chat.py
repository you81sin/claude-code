"""
drivers/youtube/chat.py
------------------------
YouTube Liveチャットをリアルタイムで取得してCHRONOSのイベントキューに投入する。

pytchatを使用（YouTube APIキー不要）。
pip install pytchat --break-system-packages

使い方:
  .envに YOUTUBE_VIDEO_ID=xxxx を設定
  または起動後に /youtube VIDEO_ID で開始
"""

import threading
import time
import os
from observation.logger import log
from runtime.silence import push_event
from engine.state import update_state

_is_running = False


def _sanitize(text: str) -> str:
    if not text or len(text) > 200:
        return ""
    if text.strip().startswith("http"):
        return ""
    return text.strip()


# スパチャ累積管理
_superchat_log: list = []  # {"amount": float, "time": float}
_SUPERCHAT_WINDOW = 300    # 5分以内の累積を見る

# スパチャ色の閾値（円換算目安）
_SC_GREEN   = 500   # 緑以上からスパチャ扱い（青・水色はコメント扱い）
_SC_YELLOW  = 2000
_SC_ORANGE  = 5000
_SC_MAGENTA = 10000

# 連続スパチャ管理
_sc_response_count = 0   # 連続反応回数
_sc_last_time      = 0.0 # 最後のスパチャ時刻
_SC_COOLDOWN       = 60  # 60秒以上空いたらリセット
_SC_IGNORE_AFTER   = 4   # 連続4件目以降は無視
_SC_BREAK_AT       = 8   # 8件以上で壊れ演出


def _get_superchat_reaction(amount: float, author: str) -> str | None:
    """
    スパチャ金額と累積から反応指示を返す。
    Noneを返すと無視。
    """
    global _sc_response_count, _sc_last_time
    now = time.time()

    # 累積ログに追加
    _superchat_log.append({"amount": amount, "time": now})
    recent = [s for s in _superchat_log if now - s["time"] < _SC_WINDOW_SEC]
    _superchat_log[:] = recent
    yellow_count = sum(1 for s in recent if s["amount"] >= _SC_YELLOW)

    # 連続カウント管理
    if now - _sc_last_time > _SC_COOLDOWN:
        _sc_response_count = 0
    _sc_last_time = now
    _sc_response_count += 1

    # 壊れ演出
    if _sc_response_count >= _SC_BREAK_AT:
        return (
            "スパチャが大量に来すぎて処理しきれていません。"
            "「え゛え゛え゛」「ちょ、ちょっと待っ—」「パンクする」など壊れた発言をしてください。"
            "文が途切れたり同じ言葉を繰り返してもOK。"
        )

    # 連続4件以降は無視
    if _sc_response_count >= _SC_IGNORE_AFTER:
        log(f"[YOUTUBE] スパチャ無視（連続{_sc_response_count}件目）")
        return None

    # スパチャ祭り困惑
    if yellow_count >= 3:
        return f"スパチャが連続で来ています（{yellow_count}件）。「え、え、ちょっと待って、みんな大丈夫？」という感じで困惑してください。"

    if amount >= _SC_MAGENTA:
        return f"{author}さんから大きなスパチャが来ました（{amount:.0f}円相当）。嬉しいけど少し戸惑いながら感謝してください。"
    elif amount >= _SC_ORANGE:
        return f"{author}さんからスパチャが来ました（{amount:.0f}円相当）。テンションが上がって嬉しそうに感謝してください。"
    else:
        return f"{author}さんからスパチャが来ました（{amount:.0f}円相当）。普通に嬉しそうに感謝してください。"


_SC_WINDOW_SEC = _SUPERCHAT_WINDOW


def _chat_loop(video_id: str, channel: str):
    global _is_running
    try:
        import pytchat
    except ImportError:
        log("[YOUTUBE] pytchat未インストール。pip install pytchat --break-system-packages")
        _is_running = False
        return

    log(f"[YOUTUBE] チャット取得開始: {video_id}")
    update_state({"youtube_video_id": video_id, "youtube_connected": True})

    try:
        chat = pytchat.create(video_id=video_id)
        while chat.is_alive() and _is_running:
            for c in chat.get().sync_items():

                # スパチャ処理
                if c.type == "superChat" and c.amountValue:
                    author = c.author.name or "視聴者"
                    # 青・水色（500円以下）はコメント扱い
                    if c.amountValue < _SC_GREEN:
                        text = _sanitize(c.message)
                        if text:
                            push_event({
                                "type":      "input",
                                "source":    "viewer",
                                "payload":   text,
                                "channel":   channel,
                                "author":    author,
                                "intensity": 0.3,
                            }, channel)
                        time.sleep(0.1)
                        continue
                    reaction = _get_superchat_reaction(c.amountValue, author)
                    if reaction is None:
                        time.sleep(0.1)
                        continue
                    log(f"[YOUTUBE] スパチャ [{author}]: {c.amountString}")
                    push_event({
                        "type":        "input",
                        "source":      "superchat",
                        "payload":     c.message or "（メッセージなし）",
                        "channel":     channel,
                        "author":      author,
                        "sc_reaction": reaction,
                        "intensity":   0.9,
                    }, channel)
                    time.sleep(0.1)
                    continue

                # 通常コメント
                text = _sanitize(c.message)
                if not text:
                    continue
                author = c.author.name or "視聴者"
                log(f"[YOUTUBE] [{author}]: {text}")
                push_event({
                    "type":      "input",
                    "source":    "viewer",
                    "payload":   text,
                    "channel":   channel,
                    "author":    author,
                    "intensity": min(1.0, len(text) / 50),
                }, channel)
                time.sleep(0.1)
            time.sleep(1.0)
    except Exception as e:
        log(f"[YOUTUBE ERROR] {e}")
    finally:
        update_state({"youtube_connected": False})
        _is_running = False
        log("[YOUTUBE] チャット取得終了")


def start_youtube_chat(video_id: str, channel: str = "pon"):
    global _is_running
    if _is_running:
        log("[YOUTUBE] すでに起動中")
        return
    _is_running = True
    threading.Thread(target=_chat_loop, args=(video_id, channel), daemon=True).start()


def stop_youtube_chat():
    global _is_running
    _is_running = False
    log("[YOUTUBE] チャット取得停止")


def start_from_env(channel: str = "pon"):
    """環境変数 YOUTUBE_VIDEO_ID があれば自動起動"""
    video_id = os.getenv("YOUTUBE_VIDEO_ID", "")
    if video_id:
        log(f"[YOUTUBE] 環境変数からvideo_id取得: {video_id}")
        start_youtube_chat(video_id, channel)
