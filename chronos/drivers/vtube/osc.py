"""
drivers/vtube/osc.py
---------------------
VSeeFace OSC通信クライアント。
WebSocketではなくOSCでVSeeFaceに表情・パラメータを送る。

VSeeFace側の設定：
設定 → OSC → 有効にする → ON
デフォルトポート: 9000

送信できるパラメータ:
/avatar/parameters/[パラメータ名] [値]

使用するパラメータ（VRoidでシェイプキーとして設定が必要）:
- expression_happy    : 0.0〜1.0
- expression_sad      : 0.0〜1.0
- expression_angry    : 0.0〜1.0
- expression_surprised: 0.0〜1.0
- expression_neutral  : 0.0〜1.0
"""

import socket
import struct
import threading
from observation.logger import log

VSF_HOST = "127.0.0.1"
VSF_PORT = 9000


def _osc_string(s: str) -> bytes:
    """OSC文字列エンコード（4バイトアライン・null終端）"""
    s = s.encode("utf-8") + b"\x00"
    pad = (4 - len(s) % 4) % 4
    return s + b"\x00" * pad


def _osc_float(f: float) -> bytes:
    return struct.pack(">f", f)


def _build_osc_message(address: str, value: float) -> bytes:
    addr  = _osc_string(address)
    types = _osc_string(",f")
    val   = _osc_float(value)
    return addr + types + val


def send_osc(address: str, value: float):
    """OSCメッセージを送信する"""
    try:
        msg = _build_osc_message(address, value)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(msg, (VSF_HOST, VSF_PORT))
        sock.close()
    except Exception as e:
        log(f"[OSC] 送信失敗: {e}")


def _emotion_to_params(emotion_state: dict) -> dict:
    """
    emotion_stateからVSeeFaceのOSCパラメータを決定する。
    返り値: {パラメータ名: 値}
    """
    mood       = emotion_state.get("mood", 0.0)
    energy     = emotion_state.get("energy", 0.6)
    tension    = emotion_state.get("tension", 0.5)
    sulky      = emotion_state.get("sulky", 0.0)
    confidence = emotion_state.get("confidence", 0.85)
    streaming  = emotion_state.get("streaming_mode", "chat")

    # 全パラメータをリセット
    params = {
        "expression_happy":     0.0,
        "expression_sad":       0.0,
        "expression_angry":     0.0,
        "expression_surprised": 0.0,
        "expression_neutral":   0.0,
    }

    if streaming == "singing":
        params["expression_happy"] = 0.8
    elif tension > 0.7 and mood > 0.3:
        params["expression_surprised"] = 0.7
        params["expression_happy"]     = 0.3
    elif confidence > 0.8:
        params["expression_happy"] = 0.6
    elif mood > 0.4:
        params["expression_happy"] = 0.8
    elif mood < -0.3:
        params["expression_sad"] = 0.7
    elif sulky > 0.5:
        params["expression_angry"] = 0.5
    elif energy < 0.3:
        params["expression_sad"] = 0.3
        params["expression_neutral"] = 0.4
    else:
        params["expression_neutral"] = 0.6

    return params


def send_expression(emotion_state: dict):
    """emotion_stateからVSeeFaceに表情OSCを送る（非同期）"""
    def _send():
        params = _emotion_to_params(emotion_state)
        for name, value in params.items():
            send_osc(f"/avatar/parameters/{name}", value)

    threading.Thread(target=_send, daemon=True).start()
