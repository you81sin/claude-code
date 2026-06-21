"""
AI 画像生成エンジン（SEGMIND API）

identity.json の appearance から AI に画像を生成させる
Stable Diffusion で pon の 2D キャラ画像を自動生成
"""

import json
import requests
import base64
import os
from pathlib import Path


def load_env():
    """手動で .env ファイルを読み込む"""
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


def appearance_to_prompt(identity: dict) -> str:
    """appearance から AI プロンプトを生成"""
    app = identity.get('appearance', {})
    name = identity.get('name', 'character')

    # プロンプトの構築
    prompt_parts = [
        f"a beautiful anime girl named {name}",
    ]

    # 髪
    hair = app.get('hair', '').lower()
    if '黒' in hair or 'black' in hair:
        prompt_parts.append("with black bob haircut")
    elif '茶' in hair or 'brown' in hair:
        prompt_parts.append("with brown bob haircut")

    # 目
    eyes = app.get('eyes', '').lower()
    if '紺' in eyes or 'navy' in eyes:
        prompt_parts.append("with purple-tinted navy blue eyes")

    # 特徴
    features = app.get('features', '').lower()
    if '猫' in features or 'cat' in features:
        prompt_parts.append("with cat ears")
        prompt_parts.append("with cat tail")

    # 衣装
    style = app.get('style', '').lower()
    if 'パーカー' in style or 'hoodie' in style:
        prompt_parts.append("wearing a hoodie")
    if 'ジーンズ' in style or 'jeans' in style:
        prompt_parts.append("wearing jeans")

    # クオリティ指定
    prompt_parts.extend([
        "high quality illustration",
        "anime art style",
        "detailed character design",
        "professional digital art",
    ])

    return ", ".join(prompt_parts)


def generate_image_segmind(prompt: str, api_key: str) -> str:
    """
    SEGMIND API で Stable Diffusion を実行

    Args:
        prompt: AI プロンプト
        api_key: SEGMIND API キー

    Returns:
        生成された画像パス
    """

    url = "https://api.segmind.com/v1/sd1.5"

    payload = {
        "prompt": prompt,
        "negative_prompt": "low quality, blurry, distorted",
        "height": 512,
        "width": 512,
        "scheduler": "normal",
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
        "seed": 0,
        "samples": 1,
    }

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        print(f"[AI_GEN] API リクエスト送信...")
        print(f"[AI_GEN] プロンプト: {prompt[:80]}...")

        response = requests.post(url, json=payload, headers=headers, timeout=60)

        if response.status_code != 200:
            print(f"[AI_GEN] API エラー: {response.status_code}")
            print(f"[AI_GEN] 応答: {response.text}")
            return None

        # 画像データを Base64 デコード
        result = response.json()
        if 'image' not in result:
            print(f"[AI_GEN] 応答に 'image' キーがない")
            return None

        image_base64 = result['image']
        image_data = base64.b64decode(image_base64)

        return image_data

    except Exception as e:
        print(f"[AI_GEN] エラー: {e}")
        return None


def save_image(image_data: bytes, output_path: str) -> bool:
    """画像を PNG として保存"""
    try:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        with open(output_path, 'wb') as f:
            f.write(image_data)

        size_kb = len(image_data) / 1024
        print(f"[AI_GEN] 画像保存: {output_path} ({size_kb:.1f} KB)")
        return True

    except Exception as e:
        print(f"[AI_GEN] 保存エラー: {e}")
        return False


def generate_character_image(char_name: str, identity_path: str, output_path: str) -> bool:
    """
    キャラクターの AI 画像を自動生成

    Args:
        char_name: キャラクター名
        identity_path: identity.json パス
        output_path: 出力画像パス

    Returns:
        成功したか
    """

    print(f"[AI_GEN] {char_name} の AI 画像生成開始...")

    # identity 読み込み
    try:
        identity = load_identity(identity_path)
    except Exception as e:
        print(f"[AI_GEN] identity 読み込みエラー: {e}")
        return False

    # プロンプト生成
    prompt = appearance_to_prompt(identity)
    print(f"[AI_GEN] プロンプト: {prompt}")

    # API キーを環境から取得
    api_key = os.getenv("SEGMIND_API_KEY")
    if not api_key:
        print(f"[AI_GEN] エラー: SEGMIND_API_KEY が設定されていません")
        return False

    # 画像生成
    image_data = generate_image_segmind(prompt, api_key)
    if not image_data:
        print(f"[AI_GEN] 画像生成失敗")
        return False

    # 保存
    if save_image(image_data, output_path):
        print(f"[AI_GEN] {char_name} AI 画像生成完了")
        return True
    else:
        return False


if __name__ == "__main__":
    import sys

    # pon の AI 画像を生成
    ok = generate_character_image(
        "pon",
        "apps/pon/data/identity.json",
        "apps/pon/data/pon_generated.png"
    )

    sys.exit(0 if ok else 1)
