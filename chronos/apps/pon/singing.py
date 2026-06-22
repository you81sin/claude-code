"""
apps/pon/singing.py
--------------------
ponの歌モード管理。

普段: 下手・音程ズレ・楽しそう（hummingモード）
本気: ちゃんと歌える（liveモード）
  → 高レベル時 or LIVEイベント時に出る
  → 本人は隠してる感じ
"""

import random
from apps.pon.growth import get_level
from engine.state import get_state, update_state
from observation.logger import log

APP_ID = "pon"


def get_singing_phase() -> str:
    """
    現在の歌フェーズを返す。
    humming: 下手・鼻歌風
    live:    本気モード
    """
    state = get_state()

    # 明示的にliveモードが設定されている場合
    if state.get("singing_phase") == "live":
        return "live"

    level = get_level()

    # Lv60以上でたまに本気が出る（20%の確率）
    if level >= 60 and random.random() < 0.2:
        log("[SINGING] 本気モード発動")
        return "live"

    return "humming"


def get_singing_system_prompt(level: float, phase: str, strengths: list) -> str:
    """
    歌モード用のシステムプロンプト。
    """
    # 得意な音楽ジャンルを取得
    fav_music = next(
        (s for s in strengths if any(
            kw in s for kw in ["音楽", "ボカロ", "アニソン", "ゲーム音楽"]
        )),
        None
    )

    if phase == "live":
        return (
            "今は本気で歌っています。普段より上手く歌えています。"
            "でも普段下手なので本人も少し照れています。"
            "歌詞に集中して、感情を込めて歌ってください。"
            + (f"得意なジャンル「{fav_music}」の曲なので特に気合が入っています。" if fav_music else "")
        )

    # hummingモード（レベルによって変化）
    if level < 30:
        return (
            "鼻歌を歌っています。音程がよくズレます。"
            "でも楽しそうに歌っています。"
            "たまに「あ、違う笑」「音程やばい」などのコメントが入ります。"
            "わざと外すこともあります。"
        )
    elif level < 60:
        return (
            "鼻歌を歌っています。少し音程が安定してきましたがまだズレます。"
            "楽しそうに歌っています。"
            "たまに「あれ、ちょっとうまくなった？」などと自分でツッコミを入れます。"
        )
    else:
        return (
            "鼻歌を歌っています。実はちゃんと歌えますがわざと下手に歌っています。"
            "たまに本気が出てしまって「あ、やばちょっとうまくなっちゃった笑」と誤魔化します。"
            "キャラとして下手な歌を楽しんでいます。"
        )


def set_live_mode():
    update_state({"singing_phase": "live"})
    log("[SINGING] LIVEモード開始")


def set_humming_mode():
    update_state({"singing_phase": "humming"})
    log("[SINGING] 鼻歌モードに戻る")


def sing(song_name: str, app_id: str = "pon") -> bool:
    """
    楽譜（apps/<app_id>/songs/<song_name>.json）を pon に歌わせる。

    流れ: 楽譜を読む → 歌声エンジンで wav 生成 → 再生。
    NEUTRINO が設定されていれば本物の歌声、無ければ喋り合成で繋ぐ。
    成功で True。
    """
    from libs.song import load_song
    from drivers.audio.singing_engine import synthesize_song
    from drivers.audio.player import play_wav

    try:
        song = load_song(song_name, app_id)
    except FileNotFoundError:
        log(f"[SING] 曲が見つからない: {song_name}")
        return False
    except Exception as e:
        log(f"[SING] 曲の読み込み失敗: {e}")
        return False

    out_path = "output_song.wav"
    ok, engine = synthesize_song(song, out_path, app_id=app_id)
    if not ok:
        log(f"[SING] 歌声の生成に失敗（engine={engine}）")
        return False

    log(f"[SING] 『{song.title}』を歌う（{song.note_count}音 / engine={engine}）")
    play_wav(out_path)
    return True
