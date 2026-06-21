"""
apps/pon/app.py
---------------
感情・欲求・視聴者認識・行動理由・配信事故・配信アーク全対応。
"""
import random
import re
from memory.identity import get_or_create_identity
from apps.pon.growth import add_xp, get_level, level_to_skill_desc
from apps.pon.episodes import ensure_episodes, add_episode, decay_episodes
from apps.pon.emotion import get_or_init_emotion, save_emotion
from apps.pon.desire import check_and_fire_desire
from memory.engine import add_memory, search_memory
from libs.persona.base import get_streaming_mode as get_mode
from apps.pon.policy import generate_text
from engine.state import get_state, update_state, tick_state, add_stress, update_praise_sensitivity
from observation.logger import log

APP_ID = "pon"

# 起動時に感情を初期化
_emotion = None


def _get_emotion():
    global _emotion
    if _emotion is None:
        _emotion = get_or_init_emotion()
    return _emotion


def _generate_identity() -> dict:
    from libs.persona.base import build_concept, generate_full_identity
    concept  = build_concept(persona_id="pon")
    identity = generate_full_identity(concept)
    identity["traits"] = concept["traits"]
    return identity


def _detect_sentiment(text: str) -> str:
    """簡易センチメント判定"""
    positive = ["好き", "すごい", "最高", "ありがとう", "かわいい", "うまい", "楽しい", "面白い"]
    negative = ["嫌い", "つまらない", "下手", "最悪", "うざい", "きもい"]
    for w in positive:
        if w in text:
            return "positive"
    for w in negative:
        if w in text:
            return "negative"
    return "neutral"


def on_event(event):
    global _emotion

    if event.get("type") != "input":
        return None

    user_input = event.get("payload", "")
    state      = get_state()

    # state tick（微小ランダム含む）
    tick_state("user_input" if event.get("source") == "user" else "auto")

    # identity
    identity   = get_or_create_identity(APP_ID, _generate_identity)
    name       = re.sub(r'[（(][^）)]*[）)]', '', identity["name"]).strip()
    traits     = identity["traits"]
    strengths  = identity.get("strengths", [])
    weaknesses = identity.get("weaknesses", [])
    fav_chars  = identity.get("fav_characters", [])
    dis_chars  = identity.get("dislike_characters", [])
    fav_vas    = identity.get("fav_voice_actors", [])
    complex_f  = identity.get("complex_feelings", [])
    greeting    = identity.get("greeting", "")
    appearance  = identity.get("appearance", {})
    profile     = identity.get("profile", {})

    # エピソード初期化（初回のみ）・decay（低確率で）
    ensure_episodes()
    import random as _ep_r2
    if _ep_r2.random() < 0.001:  # 0.1%確率（長期配信で自然消滅）
        decay_episodes()
    level      = get_level()
    skill_desc = level_to_skill_desc(level)
    emotion    = _get_emotion()

    # 関連記憶検索
    mem_hits    = search_memory(APP_ID, user_input, k=5)
    mem_context = "\n".join([m["text"] for m in mem_hits]) if mem_hits else ""

    streaming_mode = state.get("streaming_mode", "chat")

    # 欲求チェック（自発トーク時）
    desire_payload = None

    # 視聴者コメント時刻を記録（沈黙LLM判定に使う）
    if event.get("source") in ("viewer", "superchat", "user"):
        import time as _t
        update_state({"last_viewer_comment_time": _t.time()})

    # スパチャ処理（sc_reactionをdesire_payloadに差し込む）
    if event.get("source") == "superchat" and event.get("sc_reaction"):
        desire_payload = event["sc_reaction"]
        # 育成ゲーム化：スパチャでtension+5演出
        cur_tension = get_state().get("tension", 0.5)
        update_state({"tension": min(1.0, cur_tension + 0.05)})
        log(f"[GROWTH] スパチャ → tension+0.05")

    if user_input == "__silence__":
        # 沈黙LLM判定（直近5分以内にコメントがあればLLMで生成）
        from apps.pon.policy import get_silence_llm_prompt
        silence_prompt = get_silence_llm_prompt(user_input)
        if silence_prompt:
            desire_payload = silence_prompt
        else:
            # フレーズリストから返す
            from apps.pon.silence import get_silence_output
            result = get_silence_output()
            if result and not result.startswith("__silence_llm_"):
                return {"type": "action", "payload": {
                    "voice": f"{name}：{result}", "motion": "none", "voice_type": name}}
            return None
    elif user_input == "__auto__":
        desire_payload = check_and_fire_desire(strengths)

    # 視聴者センチメント更新（1回のみ）
    sentiment = _detect_sentiment(user_input)
    if event.get("source") in ("user", "viewer"):
        update_praise_sensitivity(praised=(sentiment == "positive"))

    # 声優自発トーク処理
    va_name       = ""
    va_search     = ""
    if desire_payload == "__desire_va__" and fav_vas:
        from apps.pon.desire import get_va_talk_payload, build_va_talk_prompt
        va_name, va_search = get_va_talk_payload(fav_vas)
        if va_name:
            desire_payload = build_va_talk_prompt(fav_vas, va_search, va_name)

    # =========================================================
    # 思考待機（確率ベース・状況で変化）沈黙・自発は対象外
    # =========================================================
    import random as _random
    import time as _time

    def _should_wait(inp: str, emo: dict, recent_count: int, strengths: list = None) -> float:
        """待機秒数を返す（0なら即時）"""
        from apps.pon.growth import is_strength_topic as _ist
        # 短い相槌・草は即返し
        if len(inp) <= 4 or inp in ("w", "ww", "www", "笑", "ｗ", "草"):
            return 0.0
        # 連続コメント中はテンポ重視
        if recent_count >= 3:
            if _random.random() > 0.10: return 0.0
        energy     = emo.get("energy", 0.6) if emo else 0.6
        confidence = emo.get("confidence", 0.85) if emo else 0.85
        # 確率計算
        prob = 0.0
        wait_range = (1.0, 2.0)
        if "？" in inp or "?" in inp or any(w in inp for w in ["なに", "どう", "なぜ", "いつ", "どこ", "だれ", "教えて"]):
            prob = 0.60; wait_range = (1.0, 3.0)
        elif len(inp) >= 30:
            prob = 0.50; wait_range = (1.0, 2.5)
        elif strengths and _ist(inp, strengths) and len(inp) >= 5:
            prob = 0.40; wait_range = (0.5, 1.5)
        elif energy < 0.35:
            prob = 0.70; wait_range = (2.0, 4.0)
        else:
            prob = 0.20; wait_range = (0.5, 1.5)
        # confidence高め（ドヤ顔）は少し速め
        if confidence > 0.8:
            prob *= 0.7
        if _random.random() < prob:
            return _random.uniform(*wait_range)
        return 0.0

    _recent_count = len([e for e in get_state().get("recent_events", []) if e.get("source") == "viewer"])
    # 沈黙・自発イベントは思考待機しない
    if user_input in ("__silence__", "__auto__"):
        _wait_sec = 0.0
    else:
        _wait_sec = _should_wait(user_input, emotion, _recent_count, strengths)
    if _wait_sec > 0:
        log(f"[PON] 思考中... {_wait_sec:.1f}秒")
        try:
            from drivers.vtube.osc import send_osc
            send_osc("/avatar/parameters/expression_neutral", 0.3)
        except Exception:
            pass
        _time.sleep(_wait_sec)

    text = generate_text(
        user_input     = user_input,
        name           = name,
        strengths      = strengths,
        weaknesses     = weaknesses,
        skill_desc     = skill_desc,
        mem_context    = mem_context,
        streaming_mode = streaming_mode,
        fav_chars      = fav_chars,
        dis_chars      = dis_chars,
        fav_vas        = fav_vas,
        complex_f      = complex_f,
        emotion        = emotion,
        desire_payload = desire_payload,
        greeting       = greeting,
        mem_hits       = mem_hits,
        appearance     = appearance,
        profile        = profile,
    )

    # 得意話題チェック
    is_strength = any(
        any(kw.strip() in user_input
            for kw in s.replace("（"," ").replace("）"," ").replace("、"," ").split()
            if len(kw.strip()) >= 2)
        for s in strengths
    )

    # 感情ラベルとimpact算出
    def _emotion_label(emo: dict) -> str:
        if not emo:
            return ""
        mood   = emo.get("mood", 0.0)
        energy = emo.get("energy", 0.6)
        sulky  = emo.get("sulky", 0.0)
        tension = emo.get("tension", 0.5)
        if sulky > 0.6:   return "拗ねた"
        if mood < -0.3:   return "落ち込んだ"
        if mood > 0.4 and tension > 0.6: return "興奮した"
        if mood > 0.3:    return "嬉しい"
        if energy < 0.3:  return "疲れた"
        return ""

    def _emotion_impact(emo: dict, sentiment: str) -> float:
        if not emo:
            return 0.0
        base   = abs(emo.get("mood", 0.0))
        stress = emo.get("stress", 0.0)
        bonus  = 0.3 if sentiment == "positive" else (0.2 if sentiment == "negative" else 0.0)
        return min(1.0, base + stress * 0.3 + bonus)

    sentiment    = _detect_sentiment(user_input)
    emo_label    = _emotion_label(emotion)
    emo_impact   = _emotion_impact(emotion, sentiment)

    # 記憶保存（感情付き）
    add_memory(APP_ID, f"user: {user_input}",
               importance=1.0, mem_type="chat",
               emotion=emo_label, impact=emo_impact)
    add_memory(APP_ID, f"pon: {text}",
               importance=3.0 if is_strength else 2.0,
               mem_type="self",
               emotion=emo_label, impact=emo_impact)

    add_xp(is_strength_topic=is_strength)
    # フォールバック時は失敗エピソードとして記録（10%確率）
    import random as _ep_r
    if _ep_r.random() < 0.1:
        pass  # 将来: add_episode(失敗内容)

    mode = get_mode(state)

    if mode == "ignore":
        if random.random() < 0.5:
            return None
        return {"type": "action", "payload": {"voice": f"{name}：……", "motion": "none", "voice_type": name}}

    return {"type": "action", "payload": {"voice": f"{name}：{text}", "motion": "none", "voice_type": name}}
