import os
import sys

CONFIG = {
    "DECAY_ATTENTION": 0.99,
    "DECAY_ENTROPY": 0.98,
    "CLAMP_MIN": 0.0,
    "CLAMP_MAX": 1.0,
    "MAX_HISTORY": 5000,
    "SNAPSHOT_EPS": 1e-9,
    "LOOP_INTERVAL": 0.05,
    "MAX_EVENT_QUEUE": 1000,
    "DEBUG": True,

    # "anthropic" or "gemini"
    "LLM_PROVIDER": "gemini",
}

import uuid

# .envを自動で読み込む
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

from engine.worker import start_worker
from engine.state import update_state, init_startup_state, _STARTUP_MODE_JP
from runtime.silence import push_event

VALID_MODES = ["game", "marshmallow", "chat", "comment", "singing"]

def _preload_pon_identity():
    """起動時にponのidentityを先に生成しておく"""
    try:
        from memory.identity import get_or_create_identity
        from apps.pon.app import _generate_identity
        identity = get_or_create_identity("pon", _generate_identity)
        print(f"[CHRONOS] pon identity 準備完了: {identity.get('name', '?')}")
    except Exception as e:
        print(f"[CHRONOS] pon identity 生成失敗: {e}")


def _preload_pon_avatar():
    """
    起動時にponのアバター素材を自動生成する（なければ作る・あればスキップ）。

    パイプライン:
      identity.json の appearance
          ↓ Segmind 画像生成（novelai.py）
      apps/pon/data/appearance.png
          ↓ Hunyuan3D で GLB 生成（hunyuan3d.py）
      apps/pon/data/model.glb
          ↓ 手動: VRoid Studio または Blender で VRM 化
      apps/pon/data/pon.vrm  ← あればVSeeFaceに読み込める
    """
    import json

    # --- identity から appearance 情報を取得 ---
    identity_path = os.path.join("apps", "pon", "data", "identity.json")
    if not os.path.exists(identity_path):
        print("[AVATAR] identity.json が未生成のためスキップ")
        return
    with open(identity_path, "r", encoding="utf-8") as f:
        identity = json.load(f)

    name       = identity.get("name", "pon")
    appearance = identity.get("appearance", {})
    gender     = appearance.get("gender", "不明")
    hair       = appearance.get("hair", "")
    eyes       = appearance.get("eyes", "")
    features   = appearance.get("features", "")
    style      = appearance.get("style", "")
    vibe       = appearance.get("vibe", "")

    data_dir    = os.path.join("apps", "pon", "data")
    image_path  = os.path.join(data_dir, "appearance.png")
    glb_path    = os.path.join(data_dir, "model.glb")
    vrm_path    = os.path.join(data_dir, "pon.vrm")

    # --- VRM があれば全スキップ ---
    if os.path.exists(vrm_path):
        print(f"[AVATAR] pon.vrm 確認済み → スキップ ({vrm_path})")
        return

    # --- STEP 1: 参考画像生成（なければ） ---
    if os.path.exists(image_path):
        print(f"[AVATAR] appearance.png 確認済み → 画像生成スキップ")
    else:
        print(f"[AVATAR] appearance.png を生成中...")
        # pon はポンコツキャラ（IQ15〜30）なので見た目にも抜けた感じを出す
        prompt = (
            f"anime style, full body, solo, {gender}, "
            f"hair: {hair} with ahoge, eyes: {eyes} vacant dazed expression, "
            f"{features}, "
            f"outfit: {style}, "
            "slightly open mouth, confused look, goofy clumsy vibe, "
            "not cool, lovable idiot energy, "
            "white background, character sheet, high quality"
        )
        try:
            from drivers.image.novelai import generate_appearance
            ok = generate_appearance(prompt, image_path)
            if ok:
                print(f"[AVATAR] 参考画像 生成完了 → {image_path}")
            else:
                print(f"[AVATAR] 参考画像 生成失敗 → text_to_glb で GLB を直接生成します")
        except Exception as e:
            print(f"[AVATAR] 参考画像 生成エラー: {e} → text_to_glb で GLB を直接生成します")

    # --- STEP 2: 3D モデル（GLB）生成（なければ） ---
    if os.path.exists(glb_path):
        print(f"[AVATAR] model.glb 確認済み → 3D生成スキップ")
    else:
        try:
            from drivers.avatar.hunyuan3d import image_to_glb, text_to_glb
            ok = False
            if os.path.exists(image_path):
                print(f"[AVATAR] model.glb を生成中（画像→3D）...")
                ok = image_to_glb(image_path, glb_path)
            if not ok:
                # 画像がない or 失敗 → テキストから直接3D生成
                print(f"[AVATAR] model.glb を生成中（テキスト→3D）...")
                text_prompt = (
                    f"anime style female character, {hair}, {eyes} eyes, "
                    f"{features}, {style}, {vibe}, full body, T-pose"
                )
                ok = text_to_glb(text_prompt, glb_path)
            if ok:
                print(f"[AVATAR] 3Dモデル 生成完了 → {glb_path}")
            else:
                print(f"[AVATAR] 3Dモデル 生成失敗")
                return
        except Exception as e:
            print(f"[AVATAR] 3Dモデル 生成エラー: {e}")
            return

    # --- STEP 3: GLB → VRM 変換（VSeeFace 対応） ---
    if os.path.exists(vrm_path):
        print(f"[AVATAR] pon.vrm 確認済み → スキップ ({vrm_path})")
    else:
        print(f"[AVATAR] pon.vrm を生成中（GLB → VRM）...")
        try:
            from drivers.avatar.glb_vrm_simple import glb_to_vrm_simple
            ok = glb_to_vrm_simple(glb_path, vrm_path)
            if ok:
                print()
                print("=" * 50)
                print("[AVATAR] フェーズ2 完成：VRM アバター生成完了！")
                print(f"  VRM パス: {os.path.abspath(vrm_path)}")
                print()
                print("VSeeFace で読み込んでください:")
                print(f"  モデルを読み込む → {vrm_path}")
                print("=" * 50)
                print()
            else:
                print(f"[AVATAR] VRM 変換失敗")
        except Exception as e:
            print(f"[AVATAR] VRM 変換エラー: {e}")


def _reset_avatar(channel: str, full: bool = False):
    """
    アバター関連ファイルを削除して再生成する。

    full=False: appearance.png / model.glb / pon.vrm のみ削除（キャラは維持）
    full=True : 上記 + identity.json も削除（キャラごと作り直し）
    """
    data_dir = os.path.join("apps", channel, "data")
    targets  = [
        os.path.join(data_dir, "appearance.png"),
        os.path.join(data_dir, "model.glb"),
        os.path.join(data_dir, f"{channel}.vrm"),
    ]
    if full:
        targets += [
            os.path.join(data_dir, "identity.json"),
            os.path.join(data_dir, "emotion.json"),
            os.path.join(data_dir, "growth.json"),
        ]

    deleted = []
    for path in targets:
        if os.path.exists(path):
            os.remove(path)
            deleted.append(os.path.basename(path))

    if deleted:
        print(f"[AVATAR] 削除: {', '.join(deleted)}")
    else:
        print(f"[AVATAR] 削除するファイルがありませんでした")

    if full and channel == "pon":
        print("[AVATAR] キャラを再生成中...")
        _preload_pon_identity()

    print("[AVATAR] アバターを再生成中...")
    _preload_pon_avatar()


def _check_lock():
    """2重起動防止"""
    import os, sys
    lock_path = "chronos.lock"
    if os.path.exists(lock_path):
        try:
            with open(lock_path, "r") as f:
                pid = int(f.read().strip())
            try:
                import psutil
                if psutil.pid_exists(pid):
                    print(f"[CHRONOS] すでに起動しています (PID: {pid})")
                    sys.exit(1)
            except ImportError:
                # psutilがなければPIDシグナルで確認
                import signal
                try:
                    os.kill(pid, 0)
                    print(f"[CHRONOS] すでに起動しています (PID: {pid})")
                    sys.exit(1)
                except OSError:
                    pass
        except Exception:
            pass
    with open(lock_path, "w") as f:
        f.write(str(os.getpid()))
    import atexit
    def _remove_lock():
        try: os.remove(lock_path)
        except: pass
    atexit.register(_remove_lock)


def _start_weather_loop():
    """天気を起動時取得 + 30分ごとに更新するバックグラウンドスレッド"""
    import os, threading, time as _time
    city = os.getenv("CITY", "").strip()
    if not city:
        return  # CITY未設定ならスキップ

    from drivers.weather.weather import fetch_weather
    from engine.state import update_state as _us

    def _loop():
        while True:
            weather = fetch_weather()
            _us({"weather": weather})
            _time.sleep(1800)  # 30分ごとに更新

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def main():
    _check_lock()
    print("=== CHRONOS ===")
    print()

    # コマンドライン引数でキャラを指定（bat自動実行用）
    if len(sys.argv) > 1:
        channel = sys.argv[1].strip().lower()
        if channel not in ("pon", "mlm"):
            print("不明なキャラ:", channel)
            channel = "pon"
    else:
        # 対話的キャラ選択
        print("起動するキャラを選んでください:")
        print("  1. pon")
        print("  2. mlm")
        print()
        while True:
            choice = input("選択 (1/2): ").strip()
            if choice in ("1", "pon"):
                channel = "pon"
                break
            elif choice in ("2", "mlm"):
                channel = "mlm"
                break
            print("1 か 2 を入力してください")

    print(f"\n[CHRONOS] {channel} で起動します")
    print("mode: /mode game|marshmallow|chat|comment|singing")
    print("singing: /live | /humming | /sing <曲名> | /songs")
    print("avatar: /avatar regen (画像再生成) | /avatar reset (キャラごとリセット)")

    if channel == "pon":
        _preload_pon_identity()
        _preload_pon_avatar()  # 起動時に自動でアバター生成（なければ作る・あればスキップ）

    mood = init_startup_state()
    print(f"[CHRONOS] 今日の状態: {_STARTUP_MODE_JP.get(mood, mood)}")

    # 天気取得（CITY 設定済みなら）
    _start_weather_loop()

    start_worker(channel=channel)
    # YouTube Liveチャット自動起動（YOUTUBE_VIDEO_IDが設定されていれば）
    from drivers.youtube.chat import start_from_env
    start_from_env(channel=channel)

    while True:
        # input() 待ち中は False にしておく（silence ループが正しく動くように）
        # is_typing=True はメッセージ処理中のみ使う
        update_state({"is_typing": False})
        raw = input("> ").strip().lstrip(">").strip()  # 誤って > を含めた場合も除去
        update_state({"is_typing": True})
        # YouTubeチャット開始コマンド
        if raw.startswith("/screen"):
            from drivers.screen.capture import start_screen_loop, stop_screen_loop
            if raw == "/screen stop":
                stop_screen_loop()
            else:
                parts = raw.split()
                interval = int(parts[1]) if len(parts) > 1 else 30
                start_screen_loop(channel="pon", mode="obs", interval=interval)
            continue

        if raw.startswith("/youtube "):
            video_id = raw.split(" ", 1)[1].strip()
            from drivers.youtube.chat import start_youtube_chat
            start_youtube_chat(video_id, channel="pon")
            continue
        if raw == "/youtube stop":
            from drivers.youtube.chat import stop_youtube_chat
            stop_youtube_chat()
            continue

        # === デバッグコマンド ===
        if raw.startswith("/debug"):
            parts = raw.split()
            if len(parts) < 2:
                print("[DEBUG] 使用方法:")
                print("  /debug on                    → デバッグモード ON")
                print("  /debug off                   → デバッグモード OFF")
                print("  /debug difficulty <0.0-1.0> → 困難度強制設定")
                print("  /debug serious_declare       → 宣言型本気テスト（難度0.85）")
                print("  /debug serious_instinct      → 本能型本気テスト（難度0.99）")
                continue

            cmd = parts[1]
            if cmd == "on":
                update_state({"DEBUG_MODE": True})
                print("[DEBUG] モード ON")
            elif cmd == "off":
                update_state({"DEBUG_MODE": False})
                print("[DEBUG] モード OFF")
            elif cmd == "difficulty" and len(parts) >= 3:
                try:
                    difficulty = float(parts[2])
                    update_state({"DEBUG_difficulty": difficulty})
                    print(f"[DEBUG] 困難度を {difficulty} に設定")
                except ValueError:
                    print("[DEBUG] 困難度は 0.0-1.0 の値を指定")
            elif cmd == "serious_declare":
                update_state({"DEBUG_MODE": True, "DEBUG_difficulty": 0.85})
                print("[DEBUG] 宣言型本気テスト: 難度 0.85 に設定")
            elif cmd == "serious_instinct":
                update_state({"DEBUG_MODE": True, "DEBUG_difficulty": 0.99})
                print("[DEBUG] 本能型本気テスト: 難度 0.99 に設定")
            continue

        update_state({"is_typing": False})

        if raw.startswith("/mode "):
            mode = raw.replace("/mode ", "").strip()
            if mode in VALID_MODES:
                update_state({"streaming_mode": mode})
                print(f"[MODE] {mode}")
            else:
                print(f"[MODE] {VALID_MODES}")
            continue

        if raw == "/live":
            from apps.pon.singing import set_live_mode
            set_live_mode()
            update_state({"streaming_mode": "singing"})
            continue

        if raw == "/humming":
            from apps.pon.singing import set_humming_mode
            set_humming_mode()
            update_state({"streaming_mode": "singing"})
            continue

        # 楽譜を歌わせる: /sing <曲名>  /  登録曲一覧: /songs
        if raw == "/songs":
            from libs.song import list_songs
            songs = list_songs(channel)
            print("[SING] 登録曲:", ", ".join(songs) if songs else "(なし)")
            continue
        if raw.startswith("/sing"):
            from libs.song import list_songs
            parts = raw.split(maxsplit=1)
            if len(parts) < 2:
                print("[SING] 使い方: /sing <曲名>")
                print("[SING] 登録曲:", ", ".join(list_songs(channel)) or "(なし)")
            else:
                from apps.pon.singing import sing
                update_state({"streaming_mode": "singing"})
                if not sing(parts[1].strip(), app_id=channel):
                    print("[SING] 歌えなかった（曲名 or 歌声エンジン設定を確認）")
            continue

        if raw == "/avatar regen":
            # 画像・3D・VRMだけ削除して再生成（identityは維持）
            _reset_avatar(channel=channel, full=False)
            continue

        if raw == "/avatar reset":
            # identity含めてすべて削除してキャラごと作り直し
            _reset_avatar(channel=channel, full=True)
            continue

        if ":" in raw:
            channel, _, text = raw.partition(":")
            channel = channel.strip().lower()
            text    = text.strip()
        else:
            channel = "pon"
            text    = raw.strip()

        if channel not in ("pon", "mlm"):
            print(f"[ERROR] pon or mlm")
            continue

        # 空文字は無視
        if not text.strip():
            continue

        push_event({
            "_id":     str(uuid.uuid4()),  # 重複防止用ユニークID
            "type":    "input",
            "source":  "user",
            "payload": text,
            "channel": channel,
            "intensity": len(text) / 100
        }, channel)

if __name__ == "__main__":
    main()
