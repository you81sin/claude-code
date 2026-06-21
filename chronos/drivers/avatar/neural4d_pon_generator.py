# -*- coding: utf-8 -*-
"""
Neural4D AnimeArt API Integration
100% AI-Generated VRM for pon
No human-created assets needed
"""

import os
import json
import requests
import time
from pathlib import Path


def load_env():
    """Load environment variables from .env"""
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


load_env()


def load_identity(char_name: str = "pon") -> dict:
    """Load character identity from JSON"""
    identity_path = Path(f"apps/{char_name}/data/identity.json")
    with open(identity_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_neural4d_prompt(identity: dict) -> str:
    """Create optimized prompt for Neural4D AnimeArt"""

    app = identity.get('appearance', {})
    profile = identity.get('profile', {})

    prompt = f"""
    An anime girl character named {identity.get('name', 'pon')}, age {profile.get('age', 18)}.

    Physical description:
    - Hair: {app.get('hair', 'black bob hair')}
    - Eyes: {app.get('eyes', 'navy blue with purple tint')}
    - Distinctive features: {app.get('features', 'cat ears and tail')}
    - Clothing: {app.get('style', 'gray hoodie and jeans')}
    - Height: {profile.get('height', 162)}cm
    - Skin tone: Fair, pale

    Expression and mood:
    - {app.get('vibe', 'Quiet, ethereal, slightly mysterious but gentle')}
    - Neutral to slightly melancholic expression

    Art style:
    - High-quality anime character illustration
    - Professional digital art
    - Studio quality 3D anime character
    - Full body, standing pose
    - Clean background
    - Ready for VTuber streaming
    """

    return prompt.strip()


def call_neural4d_api(prompt: str, api_key: str, output_path: str) -> bool:
    """Call Neural4D AnimeArt API to generate VRM"""

    print(f"[NEURAL4D] Submitting prompt to AnimeArt API...")
    print(f"[NEURAL4D] Prompt: {prompt[:100]}...")

    # Neural4D API endpoint
    url = "https://api.neural4d.com/v1/generate"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "mode": "text",
        "prompt": prompt,
        "model": "animeart-v1",
        "quality": "high",
        "format": "vrm",  # Direct VRM output
        "style": "anime",
        "expression": "neutral",
    }

    try:
        print("[NEURAL4D] Sending API request...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            print(f"[NEURAL4D] Task created: {task_id}")
            print(f"[NEURAL4D] Waiting for generation (typically 60-90 seconds)...")

            return poll_neural4d_status(task_id, api_key, output_path)

        else:
            print(f"[NEURAL4D] Error: {response.status_code}")
            print(f"[NEURAL4D] Response: {response.text}")
            return False

    except Exception as e:
        print(f"[NEURAL4D] Request failed: {e}")
        return False


def poll_neural4d_status(task_id: str, api_key: str, output_path: str, max_wait: int = 300) -> bool:
    """Poll Neural4D for generation status"""

    url = f"https://api.neural4d.com/v1/tasks/{task_id}"

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                result = response.json()
                status = result.get('status')
                progress = result.get('progress', 0)

                print(f"[NEURAL4D] Status: {status} ({progress}%)")

                if status == 'completed':
                    # Download VRM
                    vrm_url = result.get('download_url')
                    if vrm_url:
                        return download_vrm(vrm_url, output_path)
                    else:
                        print(f"[NEURAL4D] No download URL in response")
                        return False

                elif status == 'failed':
                    print(f"[NEURAL4D] Generation failed")
                    return False

            time.sleep(5)  # Poll every 5 seconds

        except Exception as e:
            print(f"[NEURAL4D] Polling error: {e}")
            time.sleep(5)

    print(f"[NEURAL4D] Timeout after {max_wait} seconds")
    return False


def download_vrm(vrm_url: str, output_path: str) -> bool:
    """Download generated VRM file"""

    print(f"[NEURAL4D] Downloading VRM from {vrm_url}...")

    try:
        response = requests.get(vrm_url, timeout=60)

        if response.status_code == 200:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'wb') as f:
                f.write(response.content)

            size_mb = len(response.content) / (1024 * 1024)
            print(f"[NEURAL4D] VRM saved: {output_path} ({size_mb:.1f} MB)")

            return True

        else:
            print(f"[NEURAL4D] Download error: {response.status_code}")
            return False

    except Exception as e:
        print(f"[NEURAL4D] Download failed: {e}")
        return False


def main():
    print("=" * 60)
    print("[PON Auto-Generation - Neural4D AnimeArt API]")
    print("=" * 60)

    # Load API key
    api_key = os.getenv("NEURAL4D_API_KEY")
    if not api_key:
        print("[ERROR] NEURAL4D_API_KEY not found in .env")
        return False

    print(f"\n[AUTH] API Key loaded: {api_key[:20]}...")

    # Load character identity
    print("[LOAD] Loading pon identity...")
    identity = load_identity("pon")
    print(f"[LOAD] Character: {identity.get('name', 'pon')}")

    # Create prompt
    print("[PROMPT] Generating Neural4D prompt...")
    prompt = create_neural4d_prompt(identity)

    # Call API
    output_path = "apps/pon/data/pon.vrm"

    print(f"\n[GENERATE] Starting pon VRM generation...")
    print(f"[GENERATE] Output: {output_path}")

    success = call_neural4d_api(prompt, api_key, output_path)

    if success:
        print("\n" + "=" * 60)
        print("[SUCCESS] pon VRM generated!")
        print(f"[READY] Load in VSeeFace: {output_path}")
        print("[NEXT] Open OBS → Add Browser Source → http://localhost:8001/viewer.html")
        print("=" * 60)
        return True

    else:
        print("\n[FAIL] VRM generation failed")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
