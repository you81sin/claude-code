"""
drivers/image/novelai.py
-------------------------
AI 画像生成クライアント。

優先順位:
  1. Pollinations.ai  ― 無料・APIキー不要
  2. NovelAI         ― NOVELAI_TOKEN があり有効なら使用
  3. Segmind         ― SEGMIND_API_KEY があれば使用
"""

import os
import io
import urllib.request
import urllib.parse
import urllib.error
from observation.logger import log


# =========================================================
# 1. Pollinations.ai（無料・キー不要）
# =========================================================

def _generate_pollinations(prompt: str, output_path: str) -> bool:
    """
    https://pollinations.ai  — 完全無料、APIキー不要。
    GET リクエスト1本で PNG が返ってくる。
    """
    log("[IMAGE] 画像生成開始（Pollinations.ai・無料）...")

    safe_prompt = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{safe_prompt}"
        f"?width=832&height=1216&model=flux&seed=42&nologo=true"
    )

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()

        if len(data) < 1000:
            log(f"[IMAGE] レスポンスが小さすぎます ({len(data)} bytes)")
            return False

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(data)

        log(f"[IMAGE] 生成完了 → {output_path} ({len(data)//1024}KB)")
        return True

    except Exception as e:
        log(f"[IMAGE] Pollinations 失敗: {e}")
        return False


# =========================================================
# 2. NovelAI（有料プランがあれば）
# =========================================================

def _generate_novelai(prompt: str, output_path: str) -> bool:
    import json, zipfile

    token = os.getenv("NOVELAI_TOKEN", "")
    if not token:
        return False

    # サブスクリプション確認
    try:
        req = urllib.request.Request(
            "https://api.novelai.net/user/subscription",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            sub = json.loads(r.read())
        if not sub.get("active"):
            log("[IMAGE] NovelAI サブスク未有効 → スキップ")
            return False
        if not sub.get("perks", {}).get("imageGeneration"):
            log("[IMAGE] NovelAI imageGeneration 権限なし → スキップ")
            return False
    except Exception as e:
        log(f"[IMAGE] NovelAI サブスク確認失敗: {e} → スキップ")
        return False

    log("[IMAGE] 画像生成開始（NovelAI）...")

    payload = json.dumps({
        "input":  prompt,
        "model":  "nai-diffusion-4-full",
        "action": "generate",
        "parameters": {
            "width": 832, "height": 1216,
            "scale": 6.0, "sampler": "k_euler_ancestral",
            "steps": 28,  "seed": 42, "n_samples": 1,
            "qualityToggle": True,
            "negative_prompt": (
                "lowres, bad anatomy, bad hands, text, error, "
                "cropped, worst quality, low quality, blurry"
            ),
        },
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            "https://image.novelai.net/ai/generate-image",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
                "Accept":        "*/*",
                "User-Agent":    "Mozilla/5.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()

        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".png")]
            if not names:
                return False
            img_bytes = zf.read(names[0])

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(img_bytes)

        log(f"[IMAGE] 生成完了 → {output_path}")
        return True

    except Exception as e:
        log(f"[IMAGE] NovelAI 失敗: {e}")
        return False


# =========================================================
# 3. Segmind（クレジットがあれば）
# =========================================================

def _generate_segmind(prompt: str, output_path: str) -> bool:
    import json, requests as _req

    api_key = os.getenv("SEGMIND_API_KEY", "")
    if not api_key:
        return False

    log("[IMAGE] 画像生成開始（Segmind）...")
    try:
        resp = _req.post(
            "https://api.segmind.com/v1/sdxl1.0-txt2img",
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            json={
                "prompt": prompt,
                "negative_prompt": "lowres, bad anatomy, blurry",
                "samples": 1, "num_inference_steps": 25,
                "guidance_scale": 7.5, "seed": 42,
                "img_width": 832, "img_height": 1216,
            },
            timeout=120,
        )
        if resp.status_code != 200:
            log(f"[IMAGE] Segmind エラー {resp.status_code}")
            return False
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(resp.content)
        log(f"[IMAGE] 生成完了 → {output_path}")
        return True
    except Exception as e:
        log(f"[IMAGE] Segmind 失敗: {e}")
        return False


# =========================================================
# 公開インターフェース
# =========================================================

def generate_appearance(prompt: str, output_path: str) -> bool:
    """
    利用可能なサービスを順番に試して画像を生成する。
    Pollinations（無料）→ NovelAI → Segmind の順。
    """
    for fn in [_generate_pollinations, _generate_novelai, _generate_segmind]:
        if fn(prompt, output_path):
            return True
    log("[IMAGE] すべての画像生成サービスが失敗しました")
    return False
