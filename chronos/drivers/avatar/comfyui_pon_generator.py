# -*- coding: utf-8 -*-
"""
ComfyUI + FLUX Integration for CHRONOS
Automatic Image Generation for pon
"""

import json
import requests
import time
import os
from pathlib import Path


def load_identity(char_name: str = "pon") -> dict:
    """Load character identity"""
    identity_path = Path(f"apps/{char_name}/data/identity.json")
    with open(identity_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_pon_flux_prompt(identity: dict) -> str:
    """Create FLUX-optimized prompt for pon"""

    # ポンの詳細プロンプト
    prompt = """
    A beautiful anime girl named pon, age 18, standing pose.
    Black bob haircut with bangs, shoulder-length, shiny black hair.
    Large, expressive navy blue eyes with purple tint, very detailed eyes.
    Small black cat ears on top of head, small black cat tail.
    Fair, pale skin, soft gentle expression, neutral mood.
    Wearing gray hoodie, blue jeans, comfortable casual style.
    Full body view, professional anime illustration, high quality digital art.
    Studio lighting, clean white background, character focus, VTuber style art.
    Beautiful proportions, anatomically correct, anime aesthetics, high detail.
    """

    return prompt.strip()


def generate_via_comfyui_api(prompt: str, output_path: str, comfyui_url: str = "http://127.0.0.1:8188") -> bool:
    """
    Call ComfyUI API with FLUX model
    Requires: ComfyUI running locally with FLUX model
    """

    print(f"[COMFYUI] Generating image with FLUX...")
    print(f"[COMFYUI] Endpoint: {comfyui_url}")

    # Simplified FLUX workflow
    workflow = {
        "1": {
            "inputs": {
                "ckpt_name": "flux1-dev.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "2": {
            "inputs": {
                "text": prompt,
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "3": {
            "inputs": {
                "text": "ugly, distorted, blurry",
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "4": {
            "inputs": {
                "width": 512,
                "height": 512,
                "length": 1,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "5": {
            "inputs": {
                "seed": 42,
                "steps": 20,
                "cfg": 7.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0]
            },
            "class_type": "KSampler"
        },
        "6": {
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2]
            },
            "class_type": "VAEDecode"
        },
        "7": {
            "inputs": {
                "filename_prefix": "pon_flux",
                "images": ["6", 0]
            },
            "class_type": "SaveImage"
        }
    }

    try:
        # Check ComfyUI availability
        print("[COMFYUI] Checking ComfyUI availability...")
        try:
            response = requests.get(f"{comfyui_url}/system_stats", timeout=5)
            if response.status_code != 200:
                print(f"[COMFYUI] ComfyUI not responding (status {response.status_code})")
                return False
        except requests.exceptions.ConnectionError:
            print(f"[COMFYUI] Cannot connect to {comfyui_url}")
            return False

        print("[COMFYUI] Connected! Submitting generation request...")

        # Submit workflow
        response = requests.post(
            f"{comfyui_url}/prompt",
            json={"prompt": workflow},
            timeout=10
        )

        if response.status_code != 200:
            print(f"[COMFYUI] Failed to submit workflow: {response.status_code}")
            return False

        result = response.json()
        prompt_id = result.get("prompt_id")

        if not prompt_id:
            print(f"[COMFYUI] No prompt_id in response: {result}")
            return False

        print(f"[COMFYUI] Workflow submitted (ID: {prompt_id})")
        print(f"[COMFYUI] Generating image... (may take 30-60 seconds)")

        # Poll for completion
        start_time = time.time()
        max_wait = 300  # 5 minutes

        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{comfyui_url}/history/{prompt_id}", timeout=5)

                if response.status_code == 200:
                    history = response.json()

                    if prompt_id in history:
                        job = history[prompt_id]

                        # Check if outputs exist
                        if job.get("outputs"):
                            print(f"[COMFYUI] Generation complete!")

                            # Try to find and copy the generated image
                            output_dir = Path("C:/ComfyUI/output") if os.path.exists("C:/ComfyUI/output") else Path("ComfyUI/output")

                            if output_dir.exists():
                                # Find latest PNG
                                pngs = sorted(output_dir.glob("pon_flux_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
                                if pngs:
                                    src = pngs[0]
                                    os.makedirs(os.path.dirname(output_path), exist_ok=True)

                                    # Copy to target location
                                    import shutil
                                    shutil.copy(str(src), output_path)

                                    size_kb = os.path.getsize(output_path) / 1024
                                    print(f"[COMFYUI] Image saved: {output_path} ({size_kb:.1f} KB)")
                                    return True

                        # Check for errors
                        if job.get("status", {}).get("status") == "error":
                            print(f"[COMFYUI] Generation error: {job.get('status')}")
                            return False

                time.sleep(2)

            except Exception as e:
                print(f"[COMFYUI] Poll error: {e}")
                time.sleep(2)

        print(f"[COMFYUI] Timeout after {max_wait}s")
        return False

    except Exception as e:
        print(f"[COMFYUI] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_via_huggingface_spaces(prompt: str, output_path: str) -> bool:
    """
    Generate image using Hugging Face FLUX Spaces
    Requires: Manual generation via web UI
    """

    print("[FLUX] Cannot generate via Spaces API (endpoint unavailable)")
    print()
    print("[MANUAL GENERATION REQUIRED]")
    print("1. Open browser: https://huggingface.co/spaces/black-forest-labs/FLUX.1-dev")
    print("2. Paste prompt:")
    print(f"   {prompt[:80]}...")
    print("3. Click Generate")
    print("4. Download image")
    print(f"5. Save to: {output_path}")
    print()

    return False


def check_comfyui_available() -> bool:
    """Check if ComfyUI is running locally"""
    try:
        response = requests.get("http://127.0.0.1:8188/system_stats", timeout=2)
        return response.status_code == 200
    except:
        return False


def generate_fallback_placeholder(output_path: str) -> bool:
    """Create placeholder PNG for testing"""
    print("[PLACEHOLDER] Creating test image placeholder...")

    try:
        from PIL import Image, ImageDraw
        import os

        # Create simple anime-style placeholder
        width, height = 512, 512
        img = Image.new('RGB', (width, height), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)

        # Draw simple face
        # Head circle
        draw.ellipse([150, 100, 350, 300], fill=(220, 200, 180), outline=(0, 0, 0), width=2)

        # Eyes
        draw.ellipse([180, 150, 220, 190], fill=(20, 20, 100), outline=(0, 0, 0))
        draw.ellipse([260, 150, 300, 190], fill=(20, 20, 100), outline=(0, 0, 0))

        # Hair outline
        draw.rectangle([130, 80, 370, 140], fill=(10, 10, 20), outline=(0, 0, 0))

        # Body
        draw.rectangle([200, 300, 300, 450], fill=(120, 120, 130), outline=(0, 0, 0), width=2)

        # Add text
        draw.text((150, 470), "pon - Test Image", fill=(0, 0, 0))

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path)

        print(f"[PLACEHOLDER] Created: {output_path}")
        return True

    except Exception as e:
        print(f"[PLACEHOLDER] Failed: {e}")
        return False


def main():
    print("=" * 60)
    print("[CHRONOS] pon Image Generation (FLUX)")
    print("=" * 60)

    # Load identity
    print("\n[LOAD] Loading pon identity...")
    identity = load_identity("pon")
    print(f"[LOAD] Character: {identity.get('name', 'pon')}")

    # Create prompt
    print("[PROMPT] Creating FLUX prompt...")
    prompt = create_pon_flux_prompt(identity)
    print(f"[PROMPT] {prompt[:100]}...")

    output_path = "apps/pon/data/pon_illustration.png"

    # Try ComfyUI first (faster), then Hugging Face Spaces
    if check_comfyui_available():
        print("\n[INFO] ComfyUI detected locally")
        if generate_via_comfyui_api(prompt, output_path):
            print(f"\n[SUCCESS] Image generated: {output_path}")
            return True
        else:
            print("[INFO] ComfyUI generation failed, trying Hugging Face...")

    # Fallback to Hugging Face Spaces
    if generate_via_huggingface_spaces(prompt, output_path):
        print(f"\n[SUCCESS] Image generated: {output_path}")
        return True

    # Fallback: create placeholder for testing
    print("\n[FALLBACK] All generation methods unavailable")
    print("[INFO] Creating placeholder image for testing...")

    if generate_fallback_placeholder(output_path):
        print(f"\n[SUCCESS] Placeholder image created: {output_path}")
        print("[INFO] For production, generate real image via FLUX:")
        print("       https://huggingface.co/spaces/black-forest-labs/FLUX.1-dev")
        return True

    else:
        print("\n[ERROR] Image generation failed")
        print("[INFO] Manual option: Generate image at https://huggingface.co/spaces/black-forest-labs/FLUX.1-dev")
        print(f"[INFO] Save as: {output_path}")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
