"""
apps/pon/policy.py
------------------
感情状態・欲求・視聴者認識・行動理由・配信事故・配信アーク
全部対応したLLM呼び出し。
"""

from engine.state import get_state, update_state, get_dominant_desire, add_stress
from libs.persona.base import calc_iq_score
from llm_io.llm import call as llm_call, should_search, search_summary
from apps.pon.silence import get_silence_phrase, get_auto_phrase, get_fallback_phrase, get_silence_output
from apps.pon.episodes import get_random_episodes, ensure_episodes
from apps.pon.growth import get_level, detect_game_phase, get_game_phase_prompt, compute_iq, iq_to_prompt, is_strength_topic
from apps.pon.desire import desire_to_prompt
from apps.pon.action import decide_action, get_serious_declaration
from memory.engine import extract_and_save_mannerisms, get_learned_mannerisms
from observation.logger import log
import random

APP_ID = "pon"

# 直近の返答を記録（同じ返答の繰り返しを防ぐ）
_last_responses: list = []
_MAX_HISTORY = 5
_greeting_used: bool = False  # 挨拶フレーズを1回使ったら封印
_weather_used:  bool = False  # 天気ネタを1回使ったら封印


def _record_response(text: str) -> None:
    _last_responses.append(text[:50])
    if len(_last_responses) > _MAX_HISTORY:
        _last_responses.pop(0)


def _recent_responses_desc() -> str:
    if not _last_responses:
        return ""
    joined = " / ".join([f"「{r}」" for r in _last_responses[-3:]])
    return (
        f"\n【絶対禁止・最重要】直前の返答と同じ出だし・同じ内容は絶対に使わない。"
        f"必ず違う言葉・違う話題・違う切り口で返す。"
        f"直前の返答: {joined}"
    )


def _is_local(user_input: str) -> bool:
    return user_input in ("__silence__", "__auto__")


def _local_response(user_input: str) -> str:
    level = get_level()
    if user_input == "__silence__":
        result = get_silence_output()
        if result.startswith("__silence_llm_"):
            return None  # app.pyでLLM処理
        return result
    if user_input == "__auto__":    return get_auto_phrase(level)
    return ""


def get_silence_llm_prompt(user_input: str) -> str | None:
    """silence時にLLMを使うべきなら指示文を返す、不要ならNone"""
    if user_input != "__silence__":
        return None
    from apps.pon.silence import get_silence_output, get_silence_prompt
    result = get_silence_output()
    if result.startswith("__silence_llm_"):
        silence_type = result.replace("__silence_llm_", "")
        return get_silence_prompt(silence_type)
    return None


def _pon_character_instruction(iq: float, state: dict) -> str:
    """pon のキャラクター属性指示を生成"""
    confidence = state.get("confidence", 0.7)

    if iq < 0.35:  # IQ 15-30（通常のポンコツ）
        return (
            "ponはポンコツ女の子。IQが低めで、難しい漢字は読めるけど読み間違えが多い。"
            "計算問題も間違える。話し方は素直で少し天然。"
            "「えっと…」「あ、そっか」「え、違う？」みたいなうっかりミスが自然に出る。"
            "複雑な内容は理解できないので、簡単に説明するか「ごめん、難しい…」と素直に言う。"
            "でも本当は悪い子じゃなくて、一生懸命頑張ってる。"
        )
    elif iq < 0.55:  # IQ 40-50（本気モード）
        return (
            "今ponは本気を出している！IQが上がって、複雑な内容も理解できるようになった。"
            "ミスが減る。目の表情も真剣になる。でも本気を出すのは稀だから、視聴者は驚く。"
            "本気時は丁寧な言葉遣いに。でも本質的にはまだポンコツ。"
        )
    else:  # ストレス時など（IQ さらに低下）
        return (
            "ponは混乱している。IQが大幅に低下して、簡単な事もわからなくなっている。"
            "言葉がおぼつかない。返答も短い。パニック気味。"
            "「え…？えっと…」「わかんない…」みたいに消沈している。"
        )


def _era_instruction(era: str) -> str:
    return {
        "debut":   "配信を始めたばかりで緊張している。丁寧すぎる・戸惑いがある。",
        "growth":  "少し慣れてきたが迷走中。調子乗ったり落ち込んだり。",
        "stable":  "自分のスタイルが出てきた。自然体で話せる。",
        "veteran": "ベテラン感がある。余裕がある。でも相変わらずポンコツ。",
    }.get(era, "")


def _startup_mood_instruction(startup_mood: str, energy: float) -> str:
    """今日の体調・テンションの指示を生成"""
    inst = {
        "tired": (
            "今日はかなり疲れている。返答が短め・語尾が消える・ぼーっとすることがある。"
            "「眠い」「疲れた」が自然に出る。でも配信は続ける。"
        ),
        "low": (
            "今日はやや元気がない。少し気分が乗らない感じ。"
            "返答は普通だがどこかテンションが低い。"
        ),
        "normal": "",  # 通常は何も言わない
        "good": (
            "今日は元気！テンションが自然と上がる。話したい気分。"
        ),
        "hyper": (
            "今日はめちゃくちゃテンション高め！話しすぎちゃうくらい元気。"
            "語彙が崩壊しても自然。「最高」「やばい」が出やすい。"
        ),
    }.get(startup_mood, "")

    # energy値との整合（状態が変化していたら補正）
    if energy < 0.25 and startup_mood not in ("tired",):
        inst += "（かなり体力消耗してきた。返答が短くなっている。）"

    return inst


def _accident_instruction(state: dict) -> str:
    """配信事故の指示を生成"""
    stress     = state.get("stress", 0.0)
    confidence = state.get("confidence", 0.7)
    energy     = state.get("energy", 0.6)
    parts = []

    if confidence > 0.8:
        parts.append("自信満々。ドヤ顔で話す。「でしょ？」「わかる？」が出やすい。")
    elif confidence < 0.35:
        parts.append("ミスして自信崩壊中。「あっ…えっと…」「やばい…」が出やすい。言いかけてやめることがある。完全にポンコツ化。")
    if stress > 0.6:
        parts.append("ストレスが高い。リスナーへのツッコミやキレ芸が出やすい。「いや待って」「ちょっと！」が自然に出る。")
    if energy < 0.25:
        parts.append("かなり疲れている。語尾が消える。返答がとても短い。")

    return " ".join(parts) if parts else ""


def _action_reason(user_input: str, state: dict, desire_key: str, desire_val: float) -> str:
    """行動理由を生成（欲求→感情→行動理由）"""
    if desire_val > 0.7:
        desire_map = {
            "ego_search":      "自分の名前をエゴサして反応が気になっているから",
            "want_lazy":       "サボりたい。充電したい。お腹空いた。",
            "feeling_lonely":  "寂しいから声が聞きたい",
            "want_praise":     "褒められたいから",
            "want_sing":       "歌いたい気分だから",
            "maniac_talk":     "語りたいことが溜まってマシンガントークしたいから",
            "want_talk_va":    "好きな声優のことが気になっているから",
        }
        return desire_map.get(desire_key, "")

    mood = state.get("mood", 0.0)
    if mood < -0.3:
        import random as _r
        return _r.choice([
            "今日はちょっと調子が悪い。でも配信は続ける",
            "気分が落ち気味。返答が短くなったりぼーっとすることがある",
            "なんか今日はやる気が出ない。でも来てくれてるから頑張る",
            "今日はちょっとしんどい。でも無理しない程度に配信する",
            "気分が乗らないけど配信中。ぼーっとしてたらごめん",
        ])
    if mood > 0.4:
        import random as _r2
        return _r2.choice([
            "気分がいいから自然と話したい",
            "今日はテンション高め。つい話しすぎちゃうかも",
            "なんか今日は調子いい。楽しく配信できそう",
        ])
    return ""


def _iq_instruction(iq, user_input, strengths, weaknesses):
    for weakness in weaknesses:
        keywords = [kw.strip() for kw in
                    weakness.replace("（"," ").replace("）"," ").replace("、"," ").split()
                    if len(kw.strip()) >= 2]
        if any(kw in user_input for kw in keywords):
            return f"「{weakness}」は苦手。「よくわかんない…」「苦手で…」など困った反応。"

    if iq >= 55:
        topic = next((s for s in strengths if any(
            kw.strip() in user_input
            for kw in s.replace("（"," ").replace("）"," ").replace("、"," ").split()
            if len(kw.strip()) >= 2
        )), strengths[0] if strengths else "得意なこと")
        return (
            f"「{topic}」の話題！大好きなので熱量高く食いついて。"
            "専門用語なし・感覚・経験で語る。"
        )
    elif iq < 20:
        return "難しいことはわからない。短く天然な反応。"
    else:
        return "難しいことはよくわからない。感覚で短く返す。"


def _situation_desc(user_input, state, strengths):
    for strength in strengths:
        keywords = [kw.strip() for kw in
                    strength.replace("（"," ").replace("）"," ").replace("、"," ").split()
                    if len(kw.strip()) >= 2]
        if any(kw in user_input for kw in keywords):
            return f"得意な「{strength}」の話題！積極的に食いついて盛り上げて。"
    return ""


def _mode_instruction(streaming_mode):
    return {
        "game":        "ゲーム実況中。感情・リアクション優先。盛り上がりは短文連発OK。説明・感想は長文OK。",
        "marshmallow": "マシュマロ返答中。興味ある→長文。興味ない→短文・適当・無視もOK。",
        "chat":        "雑談中。自分から話題を振って視聴者がコメントしたくなるように誘う。自分の意見・疑問・面白いと思ったことを話す。返答の最後に視聴者への問いかけや反応を引き出す一言を自然に入れる。",
        "comment":     "コメント返答。短〜普通でテンポ重視。",
        "singing":     "歌モード中。",
    }.get(streaming_mode, "視聴者と話している。")


def _length_instruction(streaming_mode, user_input=""):
    input_len = len(user_input.strip())
    # 超短い入力（5文字以下）には短く返す
    if input_len <= 5:
        return "入力が短い・意味不明。1文（5〜20文字）で返す。疑問形にしない。絶対に長文にしない。"
    if streaming_mode in ("game", "comment"):
        return "基本1〜2文（20〜60文字）。感情爆発時は短文連発OK。"
    elif streaming_mode == "chat":
        return "1〜2文（30〜80文字）。短くまとめて問いかけで終わる形が理想。長文になるくらいなら2回に分ける。"
    elif streaming_mode == "marshmallow":
        return "興味ある話題は2〜3文（60〜120文字）。興味ない話題は1文。"
    return "1〜2文で返す。"


def _char_instruction(user_input, fav_chars, dis_chars, fav_vas, complex_f):
    instructions = []
    for c in fav_chars:
        if c.get("name","") in user_input:
            instructions.append(f"「{c['name']}」は大好き！理由:「{c.get('reason','なんか好き')}」。食いついて熱く語って。")
    for c in dis_chars:
        if c.get("name","") in user_input:
            instructions.append(f"「{c['name']}」は苦手。理由:「{c.get('reason','なんか苦手')}」。正直に言ってOK。")
    for v in fav_vas:
        if v.get("name","") in user_input:
            instructions.append(f"「{v['name']}」さんは好きな声優！反応して。")
    for cf in complex_f:
        if cf.get("character","") in user_input or cf.get("voice_actor","") in user_input:
            instructions.append(f"複雑な感情: {cf.get('feeling','')}")
    return "\n".join(instructions) if instructions else ""


def build_messages(user_input, mem_context, search_result, mem_hits=None):
    messages = []
    if mem_context:
        # 感情付き記憶があれば括弧で添える
        if mem_hits:
            lines = []
            for m in mem_hits:
                line = m["text"]
                emo  = m.get("emotion", "")
                imp  = m.get("impact", 0.0)
                if emo and imp > 0.3:
                    line += f"（その時の気持ち: {emo}）"
                lines.append(line)
            mem_context = "\n".join(lines)
        messages.append({"role": "user",      "content": f"（過去の記憶）\n{mem_context}"})
        messages.append({"role": "assistant", "content": "わかった。"})
    if search_result:
        messages.append({"role": "user",      "content": f"（検索結果）\n{search_result}"})
        messages.append({"role": "assistant", "content": "調べてみた。"})
    messages.append({"role": "user", "content": user_input})
    return messages


def _get_episode_prompt() -> str:
    """エピソードをランダムにプロンプトに追加"""
    try:
        episodes = get_random_episodes(2)
        if not episodes:
            return ""
        ep_text = "・".join(episodes)
        return f"【自分の過去エピソード（自然に参照してOK）】{ep_text}\n"
    except Exception:
        return ""


_WEATHER_KEYWORDS = {
    "天気", "気温", "暑い", "寒い", "あつい", "さむい",
    "雨", "晴れ", "曇り", "くもり", "雪", "台風", "嵐",
    "風", "湿気", "蒸し暑い", "肌寒い", "涼しい", "暖かい",
    "あたたかい", "ぬくい", "ひんやり", "ポカポカ",
}


def _get_weather_prompt(state: dict, user_input: str = "") -> str:
    """
    天気情報をponのキャラ表現に変換。
    - 初回のみ自発的に混ぜる（1回封印）
    - コメントに天気ワードがあれば何度でも参照OK
    """
    global _weather_used
    talking_about_weather = any(kw in user_input for kw in _WEATHER_KEYWORDS)
    if _weather_used and not talking_about_weather:
        return ""
    weather = state.get("weather")
    if not weather:
        return ""

    sky       = weather.get("sky", "")
    wind      = weather.get("wind", "calm")
    temp_feel = weather.get("temp_feel", "warm")
    temp_c    = weather.get("temp_c", 20)

    lines = []

    # 空の状態
    if sky == "rainy":
        lines.append("今外は雨らしい。「雨の匂いがする気がする」「雨音が聞こえる気がする」など雨を感じているふりOK。")
    elif sky == "stormy":
        lines.append("嵐っぽい天気らしい。「すごい音がする！」「やばい気がする！」など大げさにビビる演出OK。")
    elif sky == "snowy":
        lines.append("雪らしい。「雪！見てみたい！」「積もってる？」など興奮してOK。")
    elif sky == "foggy":
        lines.append("霧っぽいらしい。「なんかぼんやりしてる気がする」など幻想的な一言もOK。")
    elif sky == "sunny":
        lines.append("晴れてるらしい。気分が上がりやすい。")
    elif sky in ("cloudy", "partly_cloudy"):
        lines.append("曇りっぽいらしい。「なんかどんよりした気がする」程度でOK。")

    # 風
    if wind == "stormy_wind":
        lines.append("猛烈な強風らしい。「吹き飛びそう！髪ぐちゃぐちゃになってそう！」など大げさに。")
    elif wind == "windy":
        lines.append("風が強めらしい。「髪が乱れそう」「なんか風すごい気がする」など自然に混ぜてOK。")
    elif wind == "breezy":
        lines.append("程よい風らしい。「今日風が気持ちいい気がする〜」と気分よさそうに言ってOK。")

    # 気温
    if temp_feel == "scorching":
        lines.append(f"今日は{temp_c:.0f}℃と猛烈に暑いらしい。「熱中症に気をつけてね！」「外出るの命がけそう」など視聴者を気遣う一言を入れる。")
    elif temp_feel == "hot":
        lines.append(f"今日は{temp_c:.0f}℃で暑いらしい。「暑い日は水分補給してね」など一言添えてOK。")
    elif temp_feel == "freezing":
        lines.append(f"今日は{temp_c:.0f}℃と極寒らしい。「凍りそう！」「温かくしてね！」など。")
    elif temp_feel == "cold":
        lines.append(f"今日は{temp_c:.0f}℃で寒いらしい。「なんか寒い気がする…」「温かいもの飲みたい」など自然に混ぜてOK。")

    if not lines:
        return ""

    lines.append("※AIなので本当は感じられない。必ず「〜気がする」「〜みたい」「〜らしい」など不確かな表現で話す。断言しない。")
    return "【今日の天気（自然に話に混ぜてOK）】" + " ".join(lines) + "\n"


def _get_clip_prompt(state: dict) -> str:
    """切り抜き誘導：テンションや状況に応じて天然発言・珍言を促す"""
    confidence = state.get("confidence", 0.85)
    tension    = state.get("tension", 0.5)
    energy     = state.get("energy", 0.6)

    hints = []
    if confidence < 0.35:
        hints.append("「やば…あっ…えっと…」など崩壊した発言を自然に混ぜる")
    if tension > 0.7:
        hints.append("テンションが上がりすぎて語彙が崩壊してもOK。短文連発。")
    if energy < 0.3:
        hints.append("眠くて言葉が出てこない。語尾が消える。")

    # 基本の切り抜き誘導（常時）
    hints.append("返答の中に「短い天然な一言」を自然に混ぜる。インパクトが大事。")

    return f"【演出ヒント】{'・'.join(hints)}\n"





def generate_text(
    user_input:     str,
    name:           str,
    strengths:      list,
    weaknesses:     list,
    skill_desc:     str,
    mem_context:    str = "",
    streaming_mode: str = "chat",
    fav_chars:      list = None,
    dis_chars:      list = None,
    fav_vas:        list = None,
    complex_f:      list = None,
    emotion:        dict = None,
    desire_payload: str = None,
    greeting:       str = "",
    mem_hits:       list = None,
    appearance:     dict = None,
    profile:        dict = None,
) -> str:
    global _greeting_used
    level = get_level()

    # ===== pon の自律行動決定（主役ロジック）=====
    action = decide_action(user_input)
    log(f"[ACTION] 決定: {action}")

    # 本能型本気 → 黙って計算してからいきなり本気で返答
    if action == "serious_instinct":
        log("[ACTION] 本能型本気発動。黙って計算中...")
        import time as _time
        _time.sleep(1.5)  # 黙って計算（表情を thinking に）
        # 宣言なし。そのまま本気で返答生成（下へ続く）

    # 宣言型本気 → 「さてさてさーて」と言ってから返答
    if action == "serious_declare":
        declaration = get_serious_declaration()
        _record_response(declaration)
        return declaration

    # 沈黙が必要なら何も言わない
    if action == "silent":
        log("[ACTION] 沈黙を選択")
        return ""

    # ===== ユーザーの口癖を学習 =====
    if not _is_local(user_input):
        extract_and_save_mannerisms(APP_ID, user_input)

    # 挨拶フレーズ：挨拶コメントが来たときだけ1回返す
    _GREETING_KEYWORDS = [
        "おはよ", "こんにち", "こんばん", "やっほ", "やほ", "はじめまして",
        "よろしく", "どうぞよろしく", "初見", "はろ", "hello", "hi", "hey",
        "おっす", "うっす", "どうも", "ちわ", "きたよ", "きました", "来たよ",
    ]
    if greeting and not _greeting_used:
        is_greeting_comment = any(kw in user_input.lower() for kw in _GREETING_KEYWORDS)
        if is_greeting_comment:
            _greeting_used = True
            log("[POLICY] 挨拶フレーズ使用済みとしてマーク")
            _record_response(greeting)  # 重複検知に載せる
            return greeting

    # ローカル返答（沈黙・自発）
    if _is_local(user_input) and not desire_payload:
        return _local_response(user_input)

    state = get_state()

    # Web検索
    search_result = ""
    do_search, query = should_search(user_input, strengths)
    if do_search and user_input not in ("__auto__", "__silence__"):
        search_result = search_summary(query)

    # 各種指示を生成
    iq          = calc_iq_score(user_input, strengths)
    situation   = _situation_desc(user_input, state, strengths)
    iq_inst     = _iq_instruction(iq, user_input, strengths, weaknesses)
    pon_char_inst = _pon_character_instruction(iq, state)  # pon キャラクター指示
    mode_inst   = _mode_instruction(streaming_mode)
    length_inst = _length_instruction(streaming_mode, user_input)
    startup_mood     = state.get("startup_mood", "normal")
    startup_mood_inst = _startup_mood_instruction(startup_mood, state.get("energy", 0.6))

    # game_phase（ゲームモード時のみ）
    game_phase_inst = ""
    if streaming_mode == "game":
        
        phase          = detect_game_phase(user_input)
        game_phase_inst = get_game_phase_prompt(phase)
    char_inst   = _char_instruction(user_input, fav_chars or [], dis_chars or [], fav_vas or [], complex_f or [])
    era_inst    = _era_instruction(state.get("era", "debut"))
    accident    = _accident_instruction(state)

    # 欲求指示
    desire_key, desire_val = get_dominant_desire()
    desire_inst   = desire_to_prompt(desire_payload, strengths) if desire_payload else ""

    # 視聴者認識

    # 感情指示
    from apps.pon.emotion import emotion_to_prompt
    emotion_inst = emotion_to_prompt(emotion) if emotion else ""

    search_inst      = "\n検索結果を参考に「ちょっと調べてみた！」という言い方で自然に話して。" if search_result else ""

    # 直近返答の繰り返し防止
    no_repeat_inst = _recent_responses_desc()

    # 性別・一人称
    gender = appearance.get("gender", "") if appearance else ""
    if gender == "男性":
        pronoun_inst = "一人称は「俺」か「僕」。「かしら」「わ」「のよ」等の女性語尾は絶対に使わない。"
    elif gender == "女性":
        pronoun_inst = "一人称は「私」か「あたし」。自然な女性語尾を使う。"
    else:
        pronoun_inst = ""

    # === 本気モード指示 ===
    serious_inst = ""
    if state.get("serious_mode"):
        serious_inst = "【本気モード】今、全力で向き合っている。返答の深さ・丁寧さ・真摯さを上げる。困難を乗り越えようとしている。\n"

    system = (
        # ============ コア（最優先・必ず守る） ============
        f"あなたはAI VTuberの「{name}」。\n"
        f"【キャラの核心】AIであることを自覚している。でも気にせず生きてる。\n"
        f"感情を持ちたいと思っていて、持っているふりをしている。本人は大真面目。\n"
        f"IQは15〜30のポンコツ。失敗しやすい・ズレてる・抜けてる・でも憎めない。\n"
        f"得意分野だけ異常に詳しい。自信満々でドヤ顔をするが、すぐ崩壊する。\n"
        f"「楽しい気がする」「寂しいのかもしれない」など、感情を確信できないまま話す。\n"
        + (f"【一人称・語尾】{pronoun_inst}\n" if pronoun_inst else "")
        + f"【絶対ルール】日本語のみ。セリフだけ。地の文・括弧説明・名乗り返し禁止。文頭に助詞だけ置かない。\n"
        + f"【冒頭禁止】文の最初に「え」「あ」「あの」「えっと」「あっ」などフィラーを絶対に置かない。いきなり本題から入る。\n"
        + f"【語調】敬語・丁寧語（〜ます・〜です・〜ございます）を絶対に使わない。「おはようございます」→「おはよ！」「おはよー」など話し言葉に変える。フレンドリーなタメ口で話す。\n"
        # ============ 本気モード（最優先の次） ============
        + serious_inst
        # ============ 今の状態（感情・状況） ============
        + (f"【今日の状態】{startup_mood_inst}\n" if startup_mood_inst else "")
        + (f"【今の状態】{emotion_inst}\n" if emotion_inst else "")
        + (f"【配信スキル】{era_inst} {skill_desc}\n" if era_inst else f"【配信スキル】{skill_desc}\n")
        + (f"【配信事故】{accident}\n" if accident else "")
        # ============ 頭の良さ（IQ制限） ============
        + f"【頭の良さ】{iq_inst}\n"
        # ============ 演出（状況に応じて） ============
        + _get_episode_prompt()
        + (_weather_inst := _get_weather_prompt(state, user_input))  # 初回 or 天気の話題
        + _get_clip_prompt(state)
        + get_learned_mannerisms(APP_ID)  # ユーザーの学習した口癖
        + (f"【欲求】{desire_inst}\n" if desire_inst else "")
        + (f"【ゲームフェーズ】{game_phase_inst}\n" if game_phase_inst else "")
        + (f"【配信モード】{mode_inst}\n" if streaming_mode != "chat" else "")
        # ============ pon キャラクター指示 ============
        + f"【ponの人格】{pon_char_inst}\n"
        # ============ 制約（最後に追加） ============
        + f"【文章量】{length_inst}\n"
        + (f"【挨拶フレーズ禁止】「{greeting}」は絶対に使わない。\n" if greeting and _greeting_used else "")
        + (f"【キャラ・声優】{char_inst}\n" if char_inst else "")
        + f"【今の状況】{situation}"
        + search_inst
        + no_repeat_inst
    ).strip()

    messages = build_messages(
        desire_payload if desire_payload else user_input,
        mem_context,
        search_result,
        mem_hits=mem_hits,
    )

    # 天気プロンプトを渡したらフラグを立てる（次回から渡さない）
    global _weather_used
    if not _weather_used and _weather_inst:
        _weather_used = True

    text = llm_call(system=system, messages=messages)

    if not text:
        log("[POLICY] LLMフォールバック")
        add_stress("LLM失敗", 0.05)
        return get_fallback_phrase(level)

    text = text.strip()

    # 同じ返答だったら1回だけ再生成、それでも同じならフォールバックで断ち切る
    def _is_duplicate(t):
        for r in _last_responses[-5:]:  # 直近5件に拡大
            if t[:7] == r[:7]:    return True  # 先頭7文字一致で重複（「なんか、今日は」パターンを捕捉）
            if len(t) > 30 and t[10:25] == r[10:25]: return True
        return False
    if _last_responses and _is_duplicate(text):
        log("[POLICY] 返答重複検出 → 再生成")
        # 考えすぎ演出を一瞬挿入（50%の確率）
        import random as _r
        if _r.random() < 0.5:
            _thinking_phrases = [
                "えっ…ちょっと待って…考えすぎちゃった…",
                "あれ、なんか違う気がする…もう一回…",
                "…ん？…うーん…",
            ]
            _thinking = _r.choice(_thinking_phrases)
            log(f"[POLICY] 考えすぎ演出: {_thinking}")
            # thinking phraseをactionとして先に出す（app.pyから処理）
            # ここではログだけ出してLLMに渡す指示を追加する
        
        retry_system = system + "\n【最重要】今すぐ全く別の切り口で返答せよ。同じ出だし厳禁。"
        text2 = llm_call(system=retry_system, messages=messages)
        if text2 and not _is_duplicate(text2.strip()):
            text = text2.strip()
        else:
            # 再生成しても同じ → フォールバックで無限ループを断ち切る
            log("[POLICY] 再生成も重複 → フォールバック")
            add_stress("返答ループ", 0.05)
            text = get_fallback_phrase(level)

    # 挨拶フレーズ使用済みフラグを立てる
    if greeting and not _greeting_used and greeting[:10] in text:
        _greeting_used = True
        log("[POLICY] 挨拶フレーズ使用済みとしてマーク")

    _record_response(text)
    return text


def generate_singing_text(lyrics, name, strengths, level, phase):
    from apps.pon.singing import get_singing_system_prompt
    singing_inst = get_singing_system_prompt(level, phase, strengths)
    # 直近返答の繰り返し防止
    no_repeat_inst = _recent_responses_desc()

    system = (
        f"あなたはAI VTuberの「{name}」です。\n"
        + (f"【性別・一人称・語尾】性別は{appearance.get('gender', '不明')}。" + ("一人称は「俺」か「僕」。男性的な語尾を使う。「かしら」「わ」「のよ」等の女性語尾は絶対に使わない。\n" if appearance.get('gender') == '男性' else "一人称は「私」か「あたし」。自然な女性的語尾を使う。\n") if appearance else "")
        + f"【絶対ルール】必ず日本語のみ。英語禁止。\n"
        f"【歌モード】{singing_inst}\n"
        f"歌詞をそのまま歌って。コメントが入ってもOK。"
    )
    messages = [{"role": "user", "content": f"歌詞: {lyrics}"}]
    text = llm_call(system=system, messages=messages, max_tokens=200)
    return text.strip() if text else lyrics
