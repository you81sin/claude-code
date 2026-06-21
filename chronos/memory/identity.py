"""
memory/identity.py
-------------------
キャラクターの同一性を永続化する。
初回起動時に生成してJSONに保存。
2回目以降は読み込むだけ。

保存内容:
  name      名前（LLMが生成）
  traits    性格パラメータ
  strengths 得意分野
  created   生成日時
"""

import os
import json
import time


def _identity_path(app_id: str) -> str:
    return os.path.join("apps", app_id, "data", "identity.json")


def load_identity(app_id: str) -> dict | None:
    path = _identity_path(app_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_identity(app_id: str, identity: dict) -> None:
    path = _identity_path(app_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(identity, f, ensure_ascii=False, indent=2)


def _log_appearance(identity: dict) -> None:
    """姿をログに出力する"""
    import sys
    ap = identity.get("appearance", {})
    if not ap:
        return
    name   = identity.get("name", "？")
    gender = ap.get("gender", "不明")
    hair   = ap.get("hair", "不明")
    eyes   = ap.get("eyes", "不明")
    feat   = ap.get("features", "")
    style  = ap.get("style", "")
    vibe   = ap.get("vibe", "")
    pr     = identity.get("profile", {})
    age    = pr.get("age", "？")
    height = pr.get("height", "？")
    print(f"[IDENTITY] 姿: {name} / {gender} / {age}歳 / {height}cm", file=sys.stderr)
    print(f"[IDENTITY]     髪: {hair} / 目: {eyes}", file=sys.stderr)
    if feat:  print(f"[IDENTITY]     特徴: {feat}", file=sys.stderr)
    if style: print(f"[IDENTITY]     服装: {style}", file=sys.stderr)
    if vibe:  print(f"[IDENTITY]     雰囲気: {vibe}", file=sys.stderr)


def _gen_novelai_prompt(identity: dict) -> str:
    """NovelAI向け画像生成プロンプトを自動生成する"""
    ap = identity.get("appearance", {})
    if not ap:
        return ""

    gender  = ap.get("gender", "女性")
    hair    = ap.get("hair", "")
    eyes    = ap.get("eyes", "")
    feat    = ap.get("features", "")
    style   = ap.get("style", "")
    vibe    = ap.get("vibe", "")

    # 性別タグ
    gender_tag = "1girl" if gender == "女性" else "1boy"

    # 髪色・髪型の簡易変換
    hair_tags = []
    hair_colors = {"黒": "black hair", "白": "white hair", "金": "blonde hair", "銀": "silver hair",
                   "赤": "red hair", "青": "blue hair", "緑": "green hair", "紫": "purple hair",
                   "茶": "brown hair", "ピンク": "pink hair", "水色": "light blue hair",
                   "グレー": "grey hair", "オレンジ": "orange hair"}
    for jp, en in hair_colors.items():
        if jp in hair:
            hair_tags.append(en)
    if "ロング" in hair or "長" in hair:    hair_tags.append("long hair")
    if "ショート" in hair or "短" in hair:  hair_tags.append("short hair")
    if "ミディアム" in hair or "セミ" in hair: hair_tags.append("medium hair")
    if "ツイン" in hair:  hair_tags.append("twintails")
    if "ポニー" in hair:  hair_tags.append("ponytail")
    if "三つ編" in hair:  hair_tags.append("braid")
    if "ウェーブ" in hair or "癖" in hair:  hair_tags.append("wavy hair")

    # 目の色
    eye_tags = []
    eye_colors = {"青": "blue eyes", "赤": "red eyes", "緑": "green eyes", "金": "golden eyes",
                  "紫": "purple eyes", "茶": "brown eyes", "黒": "black eyes", "銀": "silver eyes",
                  "水色": "light blue eyes", "ピンク": "pink eyes", "ヘテロ": "heterochromia"}
    for jp, en in eye_colors.items():
        if jp in eyes:
            eye_tags.append(en)

    # 特徴（ケモミミ等）
    feat_tags = []
    if "猫耳" in feat:   feat_tags.append("cat ears, cat tail")
    if "狐耳" in feat:   feat_tags.append("fox ears, fox tail")
    if "犬耳" in feat:   feat_tags.append("dog ears")
    if "兎耳" in feat:   feat_tags.append("rabbit ears")
    if "竜" in feat:     feat_tags.append("dragon horns, dragon tail")
    if "角" in feat:     feat_tags.append("horns")
    if "翼" in feat:     feat_tags.append("wings")

    # 服装
    style_tags = []
    if "制服" in style or "セーラー" in style: style_tags.append("school uniform")
    if "和服" in style or "着物" in style:     style_tags.append("kimono")
    if "ゴシック" in style:                    style_tags.append("gothic lolita")
    if "カジュアル" in style:                  style_tags.append("casual clothes")
    if "スポーツ" in style:                    style_tags.append("sportswear")
    if "アイドル" in style:                    style_tags.append("idol costume")
    if "ファンタジー" in style:                style_tags.append("fantasy outfit")

    # 雰囲気→品質タグ
    vibe_tags = []
    if "元気" in vibe or "明るい" in vibe:     vibe_tags.append("smile, energetic")
    if "クール" in vibe or "冷静" in vibe:     vibe_tags.append("cool, stoic")
    if "ミステリアス" in vibe or "神秘" in vibe: vibe_tags.append("mysterious")
    if "おとなしい" in vibe or "静か" in vibe: vibe_tags.append("quiet, gentle")
    if "かわいい" in vibe or "可愛" in vibe:   vibe_tags.append("cute")

    # 品質タグ
    quality = "masterpiece, best quality, ultra-detailed, anime style, vibrant colors"

    parts = [quality, gender_tag]
    parts += hair_tags
    parts += eye_tags
    parts += feat_tags
    parts += style_tags
    parts += vibe_tags
    parts.append("upper body, looking at viewer")

    prompt = ", ".join(p for p in parts if p)
    return prompt


_identity_locks: dict = {}
_identity_lock_mutex = __import__('threading').Lock()
_identity_cache: dict = {}  # メモリキャッシュ（ファイル読み込みを減らす）

def _get_lock(app_id: str):
    with _identity_lock_mutex:
        if app_id not in _identity_locks:
            import threading
            _identity_locks[app_id] = threading.Lock()
        return _identity_locks[app_id]


def get_or_create_identity(app_id: str, generate_fn) -> dict:
    """
    identityが存在すれば読み込む。
    なければgenerate_fn()で生成して保存する。

    generate_fn: () -> {"name": str, "traits": dict, "strengths": list}
    """
    import sys
    # メモリキャッシュがあればそれを返す
    if app_id in _identity_cache:
        return _identity_cache[app_id]

    lock = _get_lock(app_id)
    with lock:
        # ロック取得後も再チェック
        if app_id in _identity_cache:
            return _identity_cache[app_id]

        identity = load_identity(app_id)
        if identity:
            print(f"[IDENTITY] 読み込み成功: {identity.get('name')}", file=sys.stderr)
            _identity_cache[app_id] = identity
            return identity

        print(f"[IDENTITY] 新規生成開始: {app_id}", file=sys.stderr)
        identity = generate_fn()
        identity["created"] = time.time()
        save_identity(app_id, identity)
        _identity_cache[app_id] = identity
        print(f"[IDENTITY] 保存完了: {_identity_path(app_id)}", file=sys.stderr)
        _log_appearance(identity)

    # NovelAIプロンプトを出力 + 画像生成
    novelai = _gen_novelai_prompt(identity)
    if novelai:
        print(f"[IDENTITY] 🎨 NovelAIプロンプト:", file=sys.stderr)
        print(f"[IDENTITY]   {novelai}", file=sys.stderr)

        # 画像生成（NOVELAI_TOKENがあれば自動生成）→ GLB生成
        import threading
        output_path = os.path.join("apps", app_id, "data", "appearance.png")
        glb_path    = os.path.join("apps", app_id, "data", "avatar.glb")

        def _gen_image():
            try:
                from drivers.image.novelai import generate_appearance
                ok = generate_appearance(novelai, output_path)
                if ok:
                    print(f"[NOVELAI] 画像保存: {output_path}", file=sys.stderr)
                    # GLB生成（SEGMIND_API_KEYがあれば）
                    try:
                        from drivers.avatar.hunyuan3d import image_to_glb
                        image_to_glb(output_path, glb_path)
                    except Exception as e:
                        print(f"[HUNYUAN3D] スキップ: {e}", file=sys.stderr)
            except Exception as e:
                print(f"[NOVELAI] スキップ: {e}", file=sys.stderr)
        threading.Thread(target=_gen_image, daemon=True).start()

    return identity
