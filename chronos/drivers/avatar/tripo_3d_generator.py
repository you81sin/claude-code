"""
Tripo 3D API を使った高品質 3D 自動生成

テキスト/画像 → Tripo 3D API → 3D メッシュ → VRM
"""

import requests
import json
import os
import time
import base64
from pathlib import Path


def load_env():
    """環境変数を読み込み"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


load_env()


def load_identity(path: str) -> dict:
    """identity.json を読み込み"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_character_prompt(identity: dict) -> str:
    """identity.json から Tripo 用プロンプトを生成"""
    app = identity.get('appearance', {})
    name = identity.get('name', 'character')

    prompt = f"""
    Create a 3D model of {name}, an anime character with:
    - Hair: {app.get('hair', 'black bob hair')}
    - Eyes: {app.get('eyes', 'purple-tinted navy blue')}
    - Features: {app.get('features', 'cat ears and tail')}
    - Clothing: {app.get('style', 'hoodie and jeans')}
    - Style: {app.get('vibe', 'quiet and ethereal')}
    - High quality anime character 3D model
    - Full body visible
    - Standing pose
    - Professional 3D game asset quality
    """
    return prompt.strip()


def call_tripo_api(image_url: str, api_key: str) -> dict:
    """
    Tripo 3D API を呼び出し（Image to 3D）

    Args:
        image_url: キャラクター画像 URL
        api_key: Tripo API キー

    Returns:
        API レスポンス（task_id など）
    """

    url = "https://api.tripo3d.ai/v2/openapi/task"

    # 画像を URL からダウンロードして base64 に変換
    try:
        print(f"[TRIPO] 画像ダウンロード: {image_url}")
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()
        image_data_b64 = base64.b64encode(img_response.content).decode('utf-8')
        print(f"[TRIPO] 画像サイズ: {len(img_response.content)} bytes")
    except Exception as e:
        print(f"[TRIPO] 画像ダウンロードエラー: {e}")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "type": "image_to_model",
        "file": {
            "type": "png",
            "data": image_data_b64
        }
    }

    try:
        print(f"[TRIPO] API リクエスト送信...")
        print(f"[TRIPO] URL: {url}")
        print(f"[TRIPO] メソッド: POST")
        print(f"[TRIPO] ヘッダー: Authorization: Bearer {api_key[:20]}...")

        response = requests.post(url, json=payload, headers=headers, timeout=60)

        if response.status_code != 200:
            print(f"[TRIPO] API エラー: {response.status_code}")
            print(f"[TRIPO] 応答: {response.text}")
            return None

        result = response.json()
        task_id = result.get('data', {}).get('task_id')
        print(f"[TRIPO] Task ID: {task_id}")

        return {'task_id': task_id}

    except Exception as e:
        print(f"[TRIPO] 通信エラー: {e}")
        return None


def poll_tripo_status(task_id: str, api_key: str, max_wait: int = 300) -> dict:
    """
    Tripo 3D 生成の完了を待機

    Args:
        task_id: Tripo Task ID
        api_key: Tripo API キー
        max_wait: 最大待機秒数

    Returns:
        完成した 3D データ（GLB URL など）
    """

    url = f"https://api.tripo3d.ai/v2/openapi/task/{task_id}"

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            print(f"[TRIPO] ステータス確認... ({int(time.time() - start_time)}秒経過)")

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                print(f"[TRIPO] ステータス取得エラー: {response.status_code}")
                time.sleep(5)
                continue

            result = response.json()
            data = result.get('data', {})
            status = data.get('status')
            progress = data.get('progress', 0)

            print(f"[TRIPO] ステータス: {status} (進捗: {progress}%)")

            if status == 'success':
                print(f"[TRIPO] 3D 生成完了")
                return data

            elif status in ('failed', 'cancelled'):
                print(f"[TRIPO] 生成失敗: {status}")
                return None

            time.sleep(2)  # 2秒待って再確認

        except Exception as e:
            print(f"[TRIPO] ポーリングエラー: {e}")
            time.sleep(5)

    print(f"[TRIPO] タイムアウト（{max_wait}秒）")
    return None


def download_glb(glb_url: str, output_path: str) -> bool:
    """
    GLB ファイルをダウンロード

    Args:
        glb_url: GLB ファイル URL
        output_path: 保存先パス

    Returns:
        成功したか
    """

    try:
        print(f"[TRIPO] GLB ダウンロード: {glb_url}")

        response = requests.get(glb_url, timeout=60)

        if response.status_code != 200:
            print(f"[TRIPO] ダウンロードエラー: {response.status_code}")
            return False

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        with open(output_path, 'wb') as f:
            f.write(response.content)

        size_mb = len(response.content) / (1024 * 1024)
        print(f"[TRIPO] GLB 保存: {output_path} ({size_mb:.1f} MB)")

        return True

    except Exception as e:
        print(f"[TRIPO] ダウンロード失敗: {e}")
        return False


def generate_3d_with_tripo(char_name: str, identity_path: str, image_url: str, output_path: str) -> bool:
    """
    Tripo 3D API で高品質 3D を生成

    Args:
        char_name: キャラクター名
        identity_path: identity.json パス
        image_url: キャラクター画像 URL
        output_path: 出力 GLB パス

    Returns:
        成功したか
    """

    print(f"[TRIPO] {char_name} の 3D 生成開始...")

    # API キー取得
    api_key = os.getenv("TRIPO_API_KEY")
    if not api_key:
        print(f"[TRIPO] エラー: TRIPO_API_KEY が設定されていません")
        return False

    # Tripo API を呼び出し
    result = call_tripo_api(image_url, api_key)
    if not result or 'task_id' not in result:
        print(f"[TRIPO] API 呼び出し失敗")
        return False

    task_id = result['task_id']

    # 完成を待機
    final_result = poll_tripo_status(task_id, api_key, max_wait=600)
    if not final_result:
        print(f"[TRIPO] 3D 生成失敗")
        return False

    # GLB URL を取得
    glb_url = final_result.get('output', {}).get('model')
    if not glb_url:
        print(f"[TRIPO] GLB URL が見つかりません")
        print(f"[TRIPO] 結果: {final_result}")
        return False

    # GLB をダウンロード
    if download_glb(glb_url, output_path):
        print(f"[TRIPO] {char_name} 3D 生成完了: {output_path}")
        return True
    else:
        return False


if __name__ == "__main__":
    import sys

    # テスト: Tripo サンプル画像で 3D 生成
    # （実際の pon 画像は AI 生成パイプラインから取得）

    # Tripo ドキュメントのサンプル画像 URL
    sample_image_url = "https://cdn.openai.com/API/docs/images/guides/image_generation_landscape.webp"

    print(f"[TRIPO] テスト実行: サンプル画像で 3D 生成")
    print(f"[TRIPO] 画像: {sample_image_url}")

    ok = generate_3d_with_tripo(
        "pon",
        "apps/pon/data/identity.json",
        sample_image_url,
        "apps/pon/data/pon_tripo.glb"
    )

    if ok:
        print(f"[TRIPO] テスト成功。pon_tripo.glb を生成")
    else:
        print(f"[TRIPO] テスト失敗")

    sys.exit(0 if ok else 1)
