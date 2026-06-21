"""
drivers/avatar/hunyuan3d.py
----------------------------
Tripo3D API で画像→3Dメッシュ（GLB）生成。
（旧: Segmind Hunyuan3D → クレジット切れのため Tripo3D に移行）

APIキー取得: https://platform.tripo3d.ai/
  .env に TRIPO_API_KEY=tsk_xxxx を追加
  無料枠: 月200クレジット（1モデル≈10〜15クレジット）
"""

import os
import time
import json
import urllib.request
import urllib.error
from observation.logger import log

TRIPO_BASE = "https://api.tripo3d.ai/v2/openapi"


# =========================================================
# 1. 画像アップロード → image_token
# =========================================================

def _upload_image(image_path: str, api_key: str) -> str | None:
    """画像をアップロードして image_token を返す"""
    with open(image_path, "rb") as f:
        image_data = f.read()

    boundary = f"----Boundary{int(time.time())}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="image.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + image_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{TRIPO_BASE}/upload",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        if result.get("code") == 0:
            token = result.get("data", {}).get("image_token")
            log(f"[TRIPO3D] アップロード完了: {token}")
            return token
        log(f"[TRIPO3D] アップロード失敗: {result}")
        return None
    except Exception as e:
        log(f"[TRIPO3D] アップロード例外: {e}")
        return None


# =========================================================
# 2. タスク作成 → task_id
# =========================================================

def _create_task(image_token: str, api_key: str) -> str | None:
    """image_to_model タスクを作成して task_id を返す"""
    payload = json.dumps({
        "type": "image_to_model",
        "file": {
            "type":       "png",
            "file_token": image_token,
        },
    }).encode()

    req = urllib.request.Request(
        f"{TRIPO_BASE}/task",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        if result.get("code") == 0:
            task_id = result["data"]["task_id"]
            log(f"[TRIPO3D] タスク作成: {task_id}")
            return task_id
        log(f"[TRIPO3D] タスク作成失敗: {result}")
        return None
    except Exception as e:
        log(f"[TRIPO3D] タスク作成例外: {e}")
        return None


# =========================================================
# 3. 完了待ち → GLB URL
# =========================================================

def _poll_task(task_id: str, api_key: str, timeout: int = 300) -> str | None:
    """タスクが完了するまでポーリング。GLB の URL を返す"""
    start = time.time()
    while time.time() - start < timeout:
        req = urllib.request.Request(
            f"{TRIPO_BASE}/task/{task_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())

            if result.get("code") != 0:
                log(f"[TRIPO3D] ポーリングエラー: {result}")
                return None

            data   = result["data"]
            status = data.get("status", "")

            if status == "success":
                url = data.get("result", {}).get("model", {}).get("url")
                log(f"[TRIPO3D] 生成成功: {url}")
                return url

            if status in ("failed", "cancelled"):
                log(f"[TRIPO3D] タスク失敗: {status}")
                return None

            progress = data.get("progress", 0)
            log(f"[TRIPO3D] 生成中... {progress}%")
            time.sleep(10)

        except Exception as e:
            log(f"[TRIPO3D] ポーリング例外: {e}")
            time.sleep(5)

    log("[TRIPO3D] タイムアウト（300秒）")
    return None


# =========================================================
# 4. GLB ダウンロード
# =========================================================

def _download_glb(url: str, output_path: str) -> bool:
    """GLB を URL からダウンロード"""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(data)
        log(f"[TRIPO3D] GLB保存完了 → {output_path} ({len(data)//1024}KB)")
        return True
    except Exception as e:
        log(f"[TRIPO3D] ダウンロード例外: {e}")
        return False


# =========================================================
# 3. テキスト→タスク作成（text_to_model）
# =========================================================

def _create_text_task(prompt: str, api_key: str) -> str | None:
    """text_to_model タスクを作成して task_id を返す"""
    payload = json.dumps({
        "type":   "text_to_model",
        "prompt": prompt,
    }).encode()

    req = urllib.request.Request(
        f"{TRIPO_BASE}/task",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        if result.get("code") == 0:
            task_id = result["data"]["task_id"]
            log(f"[TRIPO3D] テキストタスク作成: {task_id}")
            return task_id
        log(f"[TRIPO3D] テキストタスク作成失敗: {result}")
        return None
    except urllib.error.HTTPError as e:
        try:
            error_body = json.loads(e.read().decode())
            log(f"[TRIPO3D] テキストタスク作成エラー {e.code}: {error_body}")
        except Exception:
            log(f"[TRIPO3D] テキストタスク作成エラー {e.code}: {e}")
        return None
    except Exception as e:
        log(f"[TRIPO3D] テキストタスク作成例外: {e}")
        return None


# =========================================================
# 公開インターフェース
# =========================================================

def image_to_glb(image_path: str, output_path: str) -> bool:
    """
    Tripo3D API で画像→GLB 変換。

    .env に TRIPO_API_KEY=tsk_xxxx を設定してください。
    https://platform.tripo3d.ai/ でAPIキー取得・無料登録可。
    """
    api_key = os.getenv("TRIPO_API_KEY", "")
    if not api_key:
        log("[TRIPO3D] TRIPO_API_KEY 未設定。スキップ。")
        log("[TRIPO3D] https://platform.tripo3d.ai/ でAPIキーを取得してください")
        return False

    if not os.path.exists(image_path):
        log(f"[TRIPO3D] 画像が見つからない: {image_path}")
        return False

    log("[TRIPO3D] 3Dモデル生成開始（Tripo3D・無料枠）...")

    image_token = _upload_image(image_path, api_key)
    if not image_token:
        return False

    task_id = _create_task(image_token, api_key)
    if not task_id:
        return False

    model_url = _poll_task(task_id, api_key)
    if not model_url:
        return False

    return _download_glb(model_url, output_path)


def text_to_glb(prompt: str, output_path: str) -> bool:
    """
    テキスト→3D GLB 変換。

    優先順：
    1. Tripo3D API（品質優先）
    2. シンプル生成（フォールバック・品質は無視）
    """
    api_key = os.getenv("TRIPO_API_KEY", "")

    # === 方法1: Tripo3D API ===
    if api_key:
        log(f"[TRIPO3D] テキスト→3D生成開始（Tripo3D）: {prompt[:60]}...")

        task_id = _create_text_task(prompt, api_key)
        if task_id:
            model_url = _poll_task(task_id, api_key)
            if model_url:
                if _download_glb(model_url, output_path):
                    return True
                log("[TRIPO3D] ダウンロード失敗 → フォールバック")
        else:
            log("[TRIPO3D] タスク作成失敗 → フォールバック")
    else:
        log("[TRIPO3D] API キー未設定 → フォールバック")

    # === 方法2: シンプル生成（フォールバック） ===
    log("[SIMPLE_AVATAR] シンプル生成にフォールバック...")
    from drivers.avatar.simple_generator import generate_simple_avatar

    return generate_simple_avatar("pon", {}, output_path)
