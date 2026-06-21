"""
drivers/audio/player.py
"""

import threading
import os
import re
from observation.logger import log
from engine.state import get_state

_playing = False
_lock    = threading.Lock()


def _remove_name_prefix(text: str) -> str:
    """
    「星河 響（ほしかわ ひびき）：」「星河 響：」「名前：」を除去する。
    """
    # 読み仮名あり: 名前（よみ）：
    clean = re.sub(r'^.+?[（(][^）)]*[）)]\s*[：:]\s*', '', text)
    if clean != text:
        return clean
    # スペース含む名前: 星河 響：
    clean = re.sub(r'^[　-鿿\w\s　]+[：:]\s*', '', text)
    return clean


def _remove_ruby(text: str) -> str:
    """
    本文中の読み仮名括弧を除去する。
    例: 星河響（ほしかわ ひびき） → 星河響
    ひらがな・カタカナ・スペースのみの括弧を対象にする。
    """
    return re.sub(r'[（(][ぁ-んァ-ヶー\s　]+[）)]', '', text)


def play_voice(text: str, voice_type: str = None) -> None:
    print(f"[VOICE:{voice_type}] {text}")
    clean = _remove_name_prefix(text)
    clean = _remove_ruby(clean)
    log(f"[PLAYER] TTS送信: {clean[:30]}")
    threading.Thread(target=_play, args=(clean,), daemon=True).start()


def _play(text: str) -> None:
    global _playing
    with _lock:
        if _playing:
            log("[PLAYER] 再生中のためスキップ")
            return
        _playing = True

    try:
        from drivers.audio.tts import synthesize_to_file
        import subprocess

        state          = get_state()
        streaming_mode = state.get("streaming_mode", "chat")
        singing_phase  = state.get("singing_phase", "humming")

        tts_mode = singing_phase if streaming_mode == "singing" else "normal"

        path = "output_voice.wav"
        # チャンネル名からapp_idを取得（pon/mlm対応）
        app_id = state.get("channel", "pon")
        ok   = synthesize_to_file(text, path, mode=tts_mode, app_id=app_id)
        if not ok:
            return

        try:
            import sounddevice as sd
            import soundfile as sf

            data, samplerate = sf.read(path, dtype="float32")
            # モノラルを2次元に統一
            if len(data.shape) == 1:
                data = data.reshape(-1, 1)
            channels = data.shape[1]

            def _play_on(device_idx):
                """指定デバイスに同期再生"""
                try:
                    with sd.OutputStream(
                        device=device_idx,
                        samplerate=samplerate,
                        channels=channels,
                        dtype="float32",
                    ) as s:
                        CHUNK = 2048
                        for i in range(0, len(data), CHUNK):
                            s.write(data[i : i + CHUNK])
                except Exception as ex:
                    log(f"[PLAYER] デバイス {device_idx} 再生失敗: {ex}")

            # CABLE Input (VB-Audio) を探して lip sync 用に同時再生
            cable_idx = next(
                (
                    i for i, d in enumerate(sd.query_devices())
                    if "CABLE Input" in d.get("name", "")
                    and d.get("max_output_channels", 0) > 0
                ),
                None,
            )
            if cable_idx is not None:
                threading.Thread(
                    target=_play_on, args=(cable_idx,), daemon=True
                ).start()
                log(f"[PLAYER] VB-Audio (device={cable_idx}) へ送信")

            # デフォルトデバイス（スピーカー）に同期再生
            _play_on(None)

        except Exception as e_sd:
            log(f"[PLAYER] sounddevice失敗、フォールバック: {e_sd}")
            if os.name == "nt":
                subprocess.call(
                    ["powershell", "-c", f"(New-Object Media.SoundPlayer '{path}').PlaySync()"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                subprocess.call(["aplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    except Exception as e:
        log(f"[PLAYER ERROR] {e}")
    finally:
        _playing = False
