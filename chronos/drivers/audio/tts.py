"""
drivers/audio/tts.py
---------------------
Style-Bert-VITS2 APIサーバーへの接続。
通常モードと歌モードを切り替えられる。
"""

import urllib.request
import urllib.parse
from observation.logger import log

TTS_HOST    = "http://127.0.0.1:5000"
OUTPUT_PATH = "output_voice.wav"

# モデルID設定
# 0: amitaro（女性）, 3: jvnv-M1-jp（男性）, 4: jvnv-M2-jp（男性）
MODEL_ID_FEMALE = 0
MODEL_ID_MALE   = 3


def get_model_id(app_id: str = "pon") -> int:
    """identityの性別に応じてmodel_idを返す"""
    try:
        import os, json
        path = os.path.join("apps", app_id, "data", "identity.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                identity = json.load(f)
            gender = identity.get("appearance", {}).get("gender", "女性")
            return MODEL_ID_MALE if gender == "男性" else MODEL_ID_FEMALE
    except Exception:
        pass
    return MODEL_ID_FEMALE


def synthesize(
    text:       str,
    mode:       str = "normal",  # normal / humming / live
    model_name: str = "amitaro",
    speaker_id: int = 0,
    app_id:     str = "pon",
) -> bytes | None:
    """
    モードによってパラメータを変える。

    normal:  通常会話
    humming: 鼻歌・下手風（音程ズレ・揺らぎ大）
    live:    本気モード（LIVEイベント等）
    """

    params_map = {
        "normal": {
            "length":    1.0,
            "noise":     0.6,
            "noisew":    0.8,
            "sdp_ratio": 0.2,
        },
        "humming": {
            "length":    0.88,
            "noise":     0.95,
            "noisew":    1.3,
            "sdp_ratio": 0.5,
        },
        "live": {
            "length":    0.92,
            "noise":     0.5,
            "noisew":    0.6,
            "sdp_ratio": 0.3,
        },
    }

    p        = params_map.get(mode, params_map["normal"])
    model_id = get_model_id(app_id)

    try:
        params = urllib.parse.urlencode({
            "text":       text,
            "model_id":   model_id,
            "speaker_id": speaker_id,
            "length":     p["length"],
            "noise":      p["noise"],
            "noisew":     p["noisew"],
            "sdp_ratio":  p["sdp_ratio"],
            "language":   "JP",
        })
        url = f"{TTS_HOST}/voice?{params}"
        with urllib.request.urlopen(url, timeout=30) as res:
            audio = res.read()
        log(f"[TTS:{mode}] 音声生成成功 ({len(audio)} bytes) model_id={model_id}")
        return audio

    except Exception as e:
        log(f"[TTS ERROR] {e}")
        return None


def synthesize_to_file(text: str, path: str = OUTPUT_PATH, mode: str = "normal", app_id: str = "pon") -> bool:
    audio = synthesize(text, mode=mode, app_id=app_id)
    if audio is None:
        return False
    with open(path, "wb") as f:
        f.write(audio)
    return True
