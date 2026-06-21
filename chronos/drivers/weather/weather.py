"""
drivers/weather/weather.py
---------------------------
天気情報取得（wttr.in・APIキー不要）

.env に CITY=Tokyo を設定。都市名は英語推奨。
例: CITY=Tokyo / CITY=Osaka / CITY=Sapporo
"""

import os
import json
import time
import urllib.request
import urllib.parse
from observation.logger import log

# wttr.in 天気コード → 空の状態
_SKY_CODES = {
    113: "sunny",
    116: "partly_cloudy",
    119: "cloudy",   122: "cloudy",
    143: "foggy",    248: "foggy",    260: "foggy",
    176: "rainy",    293: "rainy",    296: "rainy",
    299: "rainy",    302: "rainy",    305: "rainy",    308: "rainy",
    200: "stormy",   386: "stormy",   389: "stormy",   392: "stormy",   395: "stormy",
    227: "snowy",    230: "snowy",    323: "snowy",    326: "snowy",
    329: "snowy",    332: "snowy",    335: "snowy",    338: "snowy",
    350: "snowy",    362: "snowy",    365: "snowy",    371: "snowy",
    374: "snowy",    377: "snowy",
}


def _classify_wind(kph: float) -> str:
    if kph >= 50: return "stormy_wind"   # 嵐レベル
    if kph >= 30: return "windy"          # 髪が乱れる
    if kph >= 12: return "breezy"         # 気持ちいい風
    return "calm"


def _classify_temp(c: float) -> str:
    if c >= 35: return "scorching"   # 猛暑・熱中症注意
    if c >= 28: return "hot"         # 暑い
    if c >= 20: return "warm"        # 暖かい
    if c >= 10: return "cool"        # 涼しい
    if c >= 0:  return "cold"        # 寒い
    return "freezing"                # 極寒


def fetch_weather() -> dict | None:
    """
    wttr.in から現在の天気を取得して返す。
    CITY 未設定または失敗時は None。

    戻り値例:
      {
        "sky":       "rainy",        # sunny/partly_cloudy/cloudy/foggy/rainy/stormy/snowy
        "wind":      "windy",        # calm/breezy/windy/stormy_wind
        "temp_feel": "hot",          # freezing/cold/cool/warm/hot/scorching
        "temp_c":    28.0,
        "wind_kph":  32.0,
        "humidity":  75,
        "city":      "Tokyo",
      }
    """
    city = os.getenv("CITY", "").strip()
    if not city:
        return None

    url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        cur       = data["current_condition"][0]
        temp_c    = float(cur["temp_C"])
        wind_kph  = float(cur["windspeedKmph"])
        code      = int(cur["weatherCode"])
        humidity  = int(cur["humidity"])

        sky       = _SKY_CODES.get(code, "cloudy")
        wind      = _classify_wind(wind_kph)
        temp_feel = _classify_temp(temp_c)

        result = {
            "sky":       sky,
            "wind":      wind,
            "temp_feel": temp_feel,
            "temp_c":    temp_c,
            "wind_kph":  wind_kph,
            "humidity":  humidity,
            "city":      city,
            "fetched_at": time.time(),
        }
        log(f"[WEATHER] {city}: {sky} {temp_c}°C 風{wind_kph}km/h → {temp_feel} {wind}")
        return result

    except Exception as e:
        log(f"[WEATHER] 取得失敗 ({city}): {e}")
        return None
