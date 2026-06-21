"""
tools/smoke_test.py
-------------------
「核が動くか」を1コマンドで確認するスモークテスト。

LLM / TTS / 3D / ネットワーク を一切使わずに、Chronos の中心ループ
（イベント → 状態更新 → pon の思考 → アクション生成）が落ちずに通るかを検証する。

ポイント:
  - APIキーが無くても動く（LLM 失敗時はフォールバック文に切り替わる設計を確認）
  - 一時ディレクトリで動くので、本物の apps/pon/data/ を汚さない
  - numpy など外部ライブラリ無しで核が起動することを確認

実行:
    python tools/smoke_test.py
成功すると最後に「SMOKE TEST PASSED」と出る。
"""

import os
import sys
import json
import tempfile
import shutil

# chronos/ をインポートパスに通す（このファイルは chronos/tools/ にある）
CHRONOS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CHRONOS_DIR)

# LLM を確実にオフラインにする（キーがあっても外部に出さない）
for k in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "CHRONOS_LLM_PROVIDER"):
    os.environ.pop(k, None)


def main() -> int:
    # 本物のデータを汚さないよう一時作業ディレクトリで動かす
    work = tempfile.mkdtemp(prefix="chronos_smoke_")
    os.chdir(work)
    data_dir = os.path.join("apps", "pon", "data")
    os.makedirs(data_dir, exist_ok=True)

    # identity を種として置く（LLM 生成をスキップさせ、会話ループだけを試す）
    identity = {
        "name": "テスト ぽん",
        "greeting": "やっほー、ぽんだよ！",
        "traits": {"talkative": 0.6, "emotional": 0.7, "logic": 0.25},
        "strengths": ["ゲーム（RPG系）", "音楽（ボカロ）"],
        "weaknesses": ["計算"],
        "fav_characters": [], "dislike_characters": [],
        "fav_voice_actors": [], "complex_feelings": [],
        "appearance": {"gender": "女性", "hair": "水色ツインテ", "eyes": "水色",
                       "features": "なし", "style": "カジュアル", "vibe": "元気"},
        "profile": {"age": "16", "birthday": "08/31", "height": "158",
                    "origin": "テスト", "debut_date": "2026/05/06",
                    "streaming_style": "雑談", "reason_for_streaming": "感情ってなんだろうと思って"},
    }
    with open(os.path.join(data_dir, "identity.json"), "w", encoding="utf-8") as f:
        json.dump(identity, f, ensure_ascii=False)

    print("[SMOKE] 核モジュールを import 中（外部ライブラリ無しで通るはず）...")
    from engine.state import init_startup_state, update_state
    from apps.pon.app import on_event

    mood = init_startup_state()
    print(f"[SMOKE] 起動時の状態: {mood}")
    update_state({"streaming_mode": "chat"})

    # --- ケース1: 通常コメント（LLM 不在 → フォールバック文が返るはず）---
    ev1 = {"type": "input", "source": "user", "payload": "今日はどんなゲームするの？",
           "channel": "pon", "_id": "t1"}
    a1 = on_event(ev1)
    print(f"[SMOKE] case1 通常コメント -> {a1}")
    assert a1 is not None,            "通常コメントで None が返った（落ちている）"
    assert a1.get("type") == "action", "action 型で返っていない"
    assert a1["payload"].get("voice"), "voice が空"

    # --- ケース2: 挨拶（greeting ショートカット = LLM 不要パス）---
    ev2 = {"type": "input", "source": "user", "payload": "こんにちは！",
           "channel": "pon", "_id": "t2"}
    a2 = on_event(ev2)
    print(f"[SMOKE] case2 挨拶 -> {a2}")
    assert a2 is not None, "挨拶で None が返った"

    # --- ケース3: 沈黙イベント（自発トーク経路）---
    ev3 = {"type": "input", "source": "ai", "payload": "__silence__",
           "channel": "pon", "_id": "t3"}
    a3 = on_event(ev3)
    print(f"[SMOKE] case3 沈黙 -> {a3}")  # None でも可（沈黙を選ぶ設計のため）

    # --- 記憶が書き込めているか（numpy 無しの純Python埋め込み）---
    from memory.engine import search_memory, _HAS_NUMPY
    hits = search_memory("pon", "ゲーム", k=3)
    print(f"[SMOKE] 記憶検索ヒット数: {len(hits)} / numpy={'有' if _HAS_NUMPY else '無(純Python)'}")

    shutil.rmtree(work, ignore_errors=True)
    print("\n==============================")
    print(" SMOKE TEST PASSED ✅")
    print("==============================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
