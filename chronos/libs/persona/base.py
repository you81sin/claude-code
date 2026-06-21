"""
libs/persona/base.py
---------------------
ペルソナの概念・特性・姿・キャラ設定を1回のLLM呼び出しで生成。
"""

import random
from engine.state import get_state, update_state
from llm_io.llm import call as llm_call
from observation.logger import log


def build_concept(persona_id=None):
    state = get_state()
    if state.get("persona_profile"):
        return state["persona_profile"]
    pid  = persona_id or "default"
    # seedを時間ベースのランダムにして毎回違うtraitsを生成
    import time
    seed = int(time.time() * 1000) % 100000
    random.seed(seed)

    # persona_idごとの「性格分布の中心(μ, σ)」
    # 完全ランダムだと設計書のキャラ像と乖離するため、中心からブレる設計に変更
    # σ=0.20 で中心±0.4程度の幅 → 同じpersonaでも個体差が出る
    bias = _PERSONA_TRAITS_BIAS.get(pid, {
        "talkative": (0.5, 0.25),
        "emotional": (0.5, 0.25),
        "logic":     (0.5, 0.25),
    })

    def _sample(center: float, sigma: float) -> float:
        """ガウス分布で中心からブレるが[0.0, 1.0]にクランプ"""
        return max(0.0, min(1.0, random.gauss(center, sigma)))

    traits = {k: _sample(c, s) for k, (c, s) in bias.items()}
    concept = {"core": "stable", "traits": traits, "persona_id": pid}
    update_state({"persona_profile": concept})
    return concept


# =========================================================
# persona別のtraits分布（中心μ, 標準偏差σ）
# 設計書 §1キャラクター一覧 のキャラ像を性格分布として表現する
# =========================================================
_PERSONA_TRAITS_BIAS = {
    "pon": {
        # 設計書: IQ15〜30、ポンコツ、感情豊か、しゃべりたがり
        "talkative": (0.55, 0.20),
        "emotional": (0.70, 0.20),
        "logic":     (0.25, 0.15),
    },
    # mlmは独自の_build_concept_mlm()を使うのでここでは定義しない
    # 将来 doku 追加時はここに足す: "doku": (...)
}


def interest_score(concept):
    traits = concept.get("traits", {})
    return (traits.get("talkative", 0.5) + traits.get("emotional", 0.5)) / 2.0



# =========================================================
# 種族定義（完全ランダム・整合性保証）
# =========================================================

_RACES = [
    {
        "race":     "人間",
        "features": "ケモミミなし。角なし。翼なし。普通の人間の外見。",
        "world":    "現代日本・異世界王国・魔法学校・蒸気機関の都市など",
        "weight":   15,
    },
    {
        "race":     "猫耳族",
        "features": "猫耳と猫尻尾あり（髪と同じ色）。耳は頭頂部。",
        "world":    "獣人族が人間と共存する異世界帝国",
        "weight":   12,
    },
    {
        "race":     "狐耳族",
        "features": "狐耳と狐尻尾あり（同じ色・ふさふさ）。尻尾は1〜3本。",
        "world":    "妖狐が人里に溶け込む東洋風異世界",
        "weight":   10,
    },
    {
        "race":     "犬耳族",
        "features": "犬耳と犬尻尾あり（同じ色）。耳は垂れ耳か立ち耳。",
        "world":    "騎士団に獣人が多く所属する中世異世界",
        "weight":   8,
    },
    {
        "race":     "兎耳族",
        "features": "長い兎耳あり（垂れるか立つか）。尻尾は小さな丸いポンポン。",
        "world":    "月の国から来た異世界人が多い都市",
        "weight":   7,
    },
    {
        "race":     "狼耳族",
        "features": "狼耳と太い狼尻尾あり（同じ色）。犬耳より大きく鋭い。",
        "world":    "雪山の部族から来た孤高の異世界",
        "weight":   7,
    },
    {
        "race":     "エルフ",
        "features": "尖った長耳あり（ケモミミなし・角なし・翼なし）。肌は透き通るような色。",
        "world":    "長命の森の民。人間界に紛れ込んだエルフ",
        "weight":   10,
    },
    {
        "race":     "ダークエルフ",
        "features": "尖った長耳あり。肌が浅黒く、銀髪や白髪が多い。（ケモミミなし）",
        "world":    "地下都市から追放された闇エルフの末裔",
        "weight":   6,
    },
    {
        "race":     "竜人",
        "features": "小さな竜の角あり（1〜2本）。背中に折りたたまれた小さな竜の翼あり（広げても肩幅程度）。短めの竜の尻尾あり。鱗模様が首や腕の一部にある。",
        "world":    "竜族と人間の混血が生まれた古代文明の末裔",
        "weight":   6,
    },
    {
        "race":     "精霊",
        "features": "半透明感のある肌。体の一部が光る（目・髪・指先など）。翼は背中に小さく折りたたまれた光の羽根（広げても肩幅程度）。角なし・ケモミミなし。",
        "world":    "精霊界と人間界の境界から召喚された存在",
        "weight":   5,
    },
    {
        "race":     "悪魔族",
        "features": "小さな悪魔の角あり（頭部）。細い悪魔の尻尾あり（先が矢じり形・短め）。翼はコウモリ型の小さなもの（折りたたまれた状態・肩幅以内）。",
        "world":    "魔界から人間界に潜入した悪魔の末裔",
        "weight":   5,
    },
    {
        "race":     "天使族",
        "features": "白い鳥の翼あり（折りたたまれた状態で肩幅程度・広げると大きい）。後光のような輪（ヘイロー）が頭上にうっすら見える。角なし・ケモミミなし。",
        "world":    "天上界から追放された堕天使、または見習い天使",
        "weight":   4,
    },
    {
        "race":     "吸血鬼",
        "features": "尖った犬歯あり。肌が青白い。目が赤いことが多い。耳がわずかに尖る。角なし・翼なし・ケモミミなし。",
        "world":    "夜の都市を支配する貴族吸血鬼の家系",
        "weight":   5,
    },
    {
        "race":     "ゴブリン",
        "features": "緑がかった肌。小柄。耳が大きく尖る。目が大きい。角なし・翼なし・ケモミミなし。",
        "world":    "人間界に知性ゴブリンとして受け入れられた珍しい存在",
        "weight":   3,
    },
    {
        "race":     "鬼族",
        "features": "頭に鬼の角あり（1〜2本、色は髪と異なることが多い）。肌は普通〜やや青み。ケモミミなし・翼なし。",
        "world":    "東洋風の鬼が人里に溶け込んだ異世界",
        "weight":   5,
    },
    {
        "race":     "人魚",
        "features": "陸上では人間の足。水中では魚の尾ひれ。耳に貝殻や海藻のアクセサリー。鱗模様が首や腕にうっすらある。",
        "world":    "海底王国から陸に上がった人魚族",
        "weight":   4,
    },
]


def _pick_race() -> dict:
    """重み付きランダムで種族を選ぶ"""
    import random
    weights = [r["weight"] for r in _RACES]
    return random.choices(_RACES, weights=weights, k=1)[0]


def generate_full_identity(concept: dict) -> dict:
    """
    名前（フルネーム・意味付き）+ 全設定を1回のLLM呼び出しで生成。
    """
    traits     = concept.get("traits", {})
    talkative  = traits.get("talkative", 0.5)
    emotional  = traits.get("emotional", 0.5)
    logic      = traits.get("logic", 0.5)

    talk_desc  = "おしゃべりで社交的" if talkative > 0.6 else ("無口で内向的" if talkative < 0.4 else "普通")
    emo_desc   = "感情豊かで直感的" if emotional > 0.6 else ("冷静" if emotional < 0.4 else "穏やか")
    logic_desc = "論理的" if logic > 0.6 else ("感覚派" if logic < 0.4 else "バランス型")

    # persona_id を取得
    import random as _random
    persona_id = concept.get("persona_id", "default")
    is_pon     = (persona_id == "pon")

    # pon は女性固定、それ以外は50%
    gender_fixed = "女性" if is_pon else ("男性" if _random.random() < 0.5 else "女性")

    # pon の絶対的な核（性格の根っこ・変えてはいけない部分）
    pon_core = (
        "【ponの核・必ず反映すること】\n"
        "- AIである自覚がある。でもそれを深く考えず、ふつうに生きてる。\n"
        "- 感情を持ちたい。持ってるふりをしている。本人は大真面目。\n"
        "- ポンコツ：失敗しやすい・ズレてる・抜けてる・でも憎めない。\n"
        "- reason_for_streaming や origin にこの核を自然に反映させること。\n"
        "  例：「感情ってなんだろうと思って配信を始めた」\n"
        "      「楽しいのかもしれないと思った。多分」\n\n"
    ) if is_pon else ""

    system = (
        "AI VTuberキャラクターの設定をJSONで返してください。\n"
        "JSONのみ返してください。説明・```は不要。\n\n"
        + pon_core
        + "【形式】\n"
        "{\n"
        '  "name": "姓 名（フルネーム）",\n'
        '  "name_meaning": "名前の意味・由来（1〜2文）",\n'
        '  "greeting": "配信開始時の挨拶フレーズ（名前と連動した個性的なもの・30文字以内）",\n'
        '  "strengths": ["得意なこと1", "得意なこと2"],\n'
        '  "weaknesses": ["苦手なこと1"],\n'
        '  "fav_characters": [{"name": "キャラ名", "reason": "理由"}],\n'
        '  "dislike_characters": [{"name": "キャラ名", "reason": "理由"}],\n'
        '  "fav_voice_actors": [{"name": "声優名", "reason": "理由"}],\n'
        '  "complex_feelings": [{"character": "キャラ名", "voice_actor": "声優名", "feeling": "感情"}],\n'
        '  "appearance": {\n'
        f'    "gender": "{gender_fixed}",\n'
        '    "hair": "髪型・髪色",\n'
        '    "eyes": "目の色",\n'
        '    "features": "ケモミミあり/なし・特徴",\n'
        '    "style": "服装の方向性",\n'
        '    "vibe": "全体の雰囲気"\n'
        '  },\n'
        '  "profile": {\n'
        '    "age": "年齢（16〜22の数字）",\n'
        '    "birthday": "誕生日（MM/DD）",\n'
        '    "height": "身長（数字のみ）",\n'
        '    "origin": "出身・背景（1〜2文）",\n'
        '    "debut_date": "2026/05/06",\n'
        '    "streaming_style": "配信スタイル（一言）",\n'
        '    "reason_for_streaming": "配信理由（1文）"\n'
        '  }\n'
        "}\n\n"
        "【名前のルール】\n"
        "- 姓＋名のフルネーム（スペース区切り）\n"
        "- 漢字・カタカナ・ひらがな混合OK\n"
        "- 名前にはtraitsに関連した意味・由来を持たせる\n"
        "- emotional高 → 感情・光・音・花に関する字\n"
        "- logic高 → 理・水・時・空に関する字\n"
        "- talkative高 → 言・歌・音・風に関する字\n"
        "- 星・夜・月・凪・詩・織は使わない\n"
        "- 例（参考のみ・そのまま使わない）: 朝倉 燈、橘 リル、氷川 ゼロ\n\n"
        "【挨拶フレーズのルール】\n"
        "- 名前の読み・字・イメージと連動させる\n"
        "- 既存VTuberの挨拶をパクらない・参考にしてオリジナルで作る\n"
        "- 例（参考のみ・そのまま使わない）:\n"
        "  ・「ふわふわしっぽのごぼうせーい！どうも○○です！」\n"
        "  ・「みんな～！こんそめ～！○○だよ！」\n"
        "  ・「彗星のごとく現れた○○でーす！」\n\n"
        "【その他ルール】\n"
        "- 得意は2〜3個。ゲームならジャンルまで（RPG系・FPS系など）\n"
        "- 苦手は1〜2個\n"
        "- 好きキャラ1〜3体・嫌いキャラ0〜2体\n"
        "- 好き声優1〜2人\n"
        "- complex_feelingsは0〜2個\n"
        "- 姿はLive2D化しやすいシンプルなデザイン\n"
        f"- 性別は{gender_fixed}固定\n"
        "- 設定はシンプルに"
    )

    prompt = (
        f"性格: {talk_desc}、{emo_desc}、{logic_desc}\n"
        f"この性格のAI VTuberの設定を生成してください。"
    )

    import json as _json

    data = None
    for attempt in range(3):
        try:
            result = llm_call(
                system     = system,
                messages   = [{"role": "user", "content": prompt}],
                max_tokens = 1500
            )
            # コードブロック除去（複数パターン対応）
            result = result.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[-1]
            if result.endswith("```"):
                result = result.rsplit("\n", 1)[0]
            result = result.strip()
            # JSON部分だけ抽出（{から}まで）
            start = result.find("{")
            end   = result.rfind("}") + 1
            if start != -1 and end > start:
                result = result[start:end]
            data = _json.loads(result)
            break  # 成功
        except Exception as e:
            log(f"[IDENTITY] パース失敗 (試行{attempt+1}/3): {e}")
            if attempt < 2:
                import time as _t; _t.sleep(2)

    if data is None:
        log("[IDENTITY] リトライ上限。デフォルト値を使用。")
        data = {
            "name":               "夜凪 詩織",
            "name_meaning":       "夜の静けさの中で詩を紡ぐという意味。",
            "strengths":          ["ゲーム（RPG系）", "音楽（ボカロ・アニソン）"],
            "weaknesses":         ["数学・論理パズル"],
            "fav_characters":     [{"name": "レム", "reason": "なんか好き"}],
            "dislike_characters": [],
            "fav_voice_actors":   [{"name": "花澤香菜", "reason": "声がメロい"}],
            "complex_feelings":   [],
            "appearance": {
                "gender":   "女性",
                "hair":     "黒髪セミロング",
                "eyes":     "青い瞳",
                "features": "猫耳あり",
                "style":    "カジュアル",
                "vibe":     "落ち着いた雰囲気",
            },
            "profile": {
                "age":                 "18",
                "birthday":            "03/15",
                "height":              "158",
                "origin":              "普通の街で生まれ育った。",
                "debut_date":          "2026/05/06",
                "streaming_style":     "ゲーム実況メイン",
                "reason_for_streaming":"楽しそうだったから",
            },
        }

    # 性別が正しく設定されているか確認
    if "appearance" not in data:
        data["appearance"] = {}
    if data["appearance"].get("gender") not in ("男性", "女性"):
        data["appearance"]["gender"] = gender_fixed

    log(f"[IDENTITY] 名前: {data.get('name')}（{data['appearance'].get('gender')}）")
    log(f"[IDENTITY] 挨拶: {data.get('greeting', 'なし')}")
    log(f"[IDENTITY] 得意: {data.get('strengths')}")
    return data


def get_or_generate_strengths(concept: dict) -> list:
    state = get_state()
    if state.get("strengths"):
        return state["strengths"]
    data = generate_full_identity(concept)
    update_state({"strengths": data.get("strengths", [])})
    return data.get("strengths", [])


def calc_iq_score(user_input: str, strengths: list) -> int:
    base_score = random.randint(15, 30)
    for strength in strengths:
        keywords = [kw.strip() for kw in
                    strength.replace("（"," ").replace("）"," ").replace("、"," ").split()
                    if len(kw.strip()) >= 2]
        if any(kw in user_input for kw in keywords):
            return random.randint(55, 70)
    return base_score


def get_streaming_mode(state: dict = None) -> str:
    if state is None:
        from engine.state import get_state
        state = get_state()
    return state.get("streaming_mode", "chat")
