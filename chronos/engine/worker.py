# === event.pyより統合 ===
import time
import uuid

def compute_intensity(text: str) -> float:
    return min(1.0, len(text) / 100)

def create_event(text: str):
    return {
        "id": str(uuid.uuid4()),
        "type": "input",
        "source": "user",
        "payload": text,
        "intensity": compute_intensity(text),
        "timestamp": time.time()
    }


# === transition.pyより統合 ===
import random

INTEREST_WORDS = ["何", "なに", "どう", "教えて", "ジャンル", "おすすめ", "理由"]
CHAT_WORDS     = ["草", "w", "笑"]

def transition(state, event):
    new_state = dict(state)
    pressure  = state.get("pressure", 0.0)
    entropy   = state.get("entropy", 0.0)
    drift     = state.get("drift", 0.0)
    attention = state.get("attention", 0.5)
    payload   = event.get("payload", "")

    if event.get("type") == "input":
        attention += 0.15
        if any(w in payload for w in INTEREST_WORDS): attention += 0.2
        if any(w in payload for w in CHAT_WORDS):     entropy += 0.1; attention += 0.05
        if len(payload) < 3:  attention -= 0.05
        if len(payload) > 10: attention += 0.05
        pressure += random.uniform(-0.02, 0.02)

    pressure  *= 0.98
    entropy   *= 0.98
    drift     *= 0.98
    attention *= 0.99

    clamp = lambda x: max(0.0, min(1.0, x))
    new_state["pressure"]  = clamp(pressure)
    new_state["entropy"]   = clamp(entropy)
    new_state["drift"]     = clamp(drift)
    new_state["attention"] = clamp(attention)
    return new_state


"""
engine/worker.py
-----------------
チャンネルごとにworkerを立てる。
event の "channel" フィールドで振り分ける。
"""

import threading
import time
from runtime.silence import pop_event, push_event
from observation.logger import log
from drivers.audio.player import play_voice
from engine.state import get_state, update_state

# 処理済みイベントIDを管理して重複処理を防ぐ
import uuid

def handle_action(event):
    payload = event.get("payload", {})
    if "voice"  in payload: play_voice(payload["voice"], payload.get("voice_type"))
    if "motion" in payload: log(f"[MOTION] {payload['motion']}")


def _make_worker_loop(channel: str, on_event_fn):
    """
    チャンネルごとのworkerループを生成する。
    自分のチャンネル宛のイベントだけ処理する。
    """
    processed_ids = set()

    def loop():
        while True:
            event = pop_event(channel)
            if not event:
                time.sleep(0.05)  # キューが空の時はsleep（CPU暴走防止）
                continue

            # 重複処理防止
            event_id = event.get("_id")
            if event_id and event_id in processed_ids:
                continue
            if event_id:
                processed_ids.add(event_id)
                # 古いIDは削除（メモリ節約）
                if len(processed_ids) > 1000:
                    processed_ids.clear()

            log(f"[{channel.upper()}] EVENT: {event}")

            if event["type"] == "action":
                update_state({"channel": channel})
                handle_action(event)
                # VSeeFace に表情をOSCで送る
                if channel == "pon":
                    try:
                        from drivers.vtube.osc import send_expression
                        from engine.state import get_state as _gs
                        send_expression(_gs())
                    except Exception:
                        pass
                continue

            if event.get("source") in ("user", "viewer"):
                update_state({"last_event_time": time.time()})
                import random as _r
                import time as _t
                payload = event.get("payload", "")
                state   = get_state()
                now     = _t.time()

                # =========================================================
                # 盛り上がり検知
                # =========================================================
                _HYPE_KEYWORDS = [
                    "きたー", "来た", "神", "すごい", "やばい", "草", "ｗｗｗ",
                    "wwww", "えぇ", "えええ", "マジ", "まじ", "ほんと", "天才",
                    "好き", "かわいい", "かっこいい", "最高", "優勝", "草生える",
                ]
                is_hype_comment = any(kw in payload for kw in _HYPE_KEYWORDS)

                # 盛り上がりログを更新（直近30秒のhypeコメント数を管理）
                hype_log = state.get("hype_comment_log", [])
                if is_hype_comment:
                    hype_log.append(now)
                hype_log = [t for t in hype_log if now - t < 30]  # 30秒以内だけ保持
                update_state({"hype_comment_log": hype_log})
                is_hyping = len(hype_log) >= 5  # 30秒以内に5件以上でhype状態

                # =========================================================
                # 優先度判定
                # =========================================================
                is_question  = "？" in payload or "?" in payload or any(w in payload for w in ["なに","どう","なぜ","教えて","いつ","どこ"])
                is_long      = len(payload) >= 15
                is_superchat = event.get("source") == "superchat"
                is_repeat    = payload == state.get("last_processed_payload", "")
                is_short_ack = len(payload) <= 3 or payload in ("w","ww","www","草","笑","ｗ","ｗｗ","ｗｗｗ","！","!","…","、")
                is_greeting  = any(w in payload.lower() for w in ["おはよ","こんにち","こんばん","やっほ","やほ","はじめまして","おっは","ちわ","きたよ","来た"])

                # キャラ名を含むコメントは必ず処理
                try:
                    import json as _json, os as _os
                    _id_path = _os.path.join("apps", channel, "data", "identity.json")
                    with open(_id_path, encoding="utf-8") as _f:
                        _id = _json.load(_f)
                    _name = _id.get("name", "")
                    _short_name = _name.split("　")[0].split(" ")[0] if _name else ""
                    is_name_call = bool(_short_name) and _short_name in payload
                except Exception:
                    is_name_call = False

                if is_question or is_long or is_superchat or is_greeting or is_name_call:
                    prob = 1.0   # 必ず処理
                elif is_hyping:
                    prob = 0.80  # 盛り上がり中は高確率（短い相槌も含む）
                    if is_hype_comment and not is_repeat:
                        prob = 0.90
                elif is_repeat:
                    prob = 0.10
                elif is_short_ack:
                    prob = 0.20
                else:
                    prob = 0.70

                if _r.random() > prob:
                    log(f"[{channel.upper()}] 間引きスキップ (prob={prob:.0%}): {payload[:15]}")
                    continue

                # 盛り上がり状態をstateに反映（emotion/tensionに影響させる）
                if is_hyping and not state.get("hype_notified"):
                    log(f"[{channel.upper()}] 盛り上がり検知 ({len(hype_log)}件/30秒)")
                    update_state({"hype_notified": True, "tension": min(1.0, state.get("tension", 0.5) + 0.2)})
                elif not is_hyping:
                    update_state({"hype_notified": False})

                update_state({"last_processed_payload": payload})
                # やる気ゲージ：コメントが来るたびに少し上昇
                cur_energy = get_state().get("energy", 0.6)
                if cur_energy < 0.95:
                    update_state({"energy": min(1.0, cur_energy + 0.005)})

            action = on_event_fn(event)
            if action:
                action["channel"] = channel
                log(f"[{channel.upper()}] ACTION: {action}")
                push_event(action, channel)

    return loop


def start_worker(channel: str):
    """選択されたチャンネルのworker/auto/silenceループだけ起動する"""
    from runtime.silence import make_auto_loop, make_silence_loop

    if channel == "pon":
        from apps.pon.app import on_event as pon_on_event
        threading.Thread(target=_make_worker_loop("pon", pon_on_event), daemon=True).start()
        threading.Thread(target=make_auto_loop("pon"),                   daemon=True).start()
        threading.Thread(target=make_silence_loop("pon"),                daemon=True).start()
        log("[WORKER] pon 起動完了")

    elif channel == "mlm":
        from apps.mlm.app import on_event as mlm_on_event
        threading.Thread(target=_make_worker_loop("mlm", mlm_on_event), daemon=True).start()
        threading.Thread(target=make_auto_loop("mlm"),                   daemon=True).start()
        threading.Thread(target=make_silence_loop("mlm"),                daemon=True).start()
        log("[WORKER] mlm 起動完了")

    else:
        raise ValueError(f"[WORKER] 未知のchannel: {channel}")
