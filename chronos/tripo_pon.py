#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TripoSR 3D Generation for pon
Direct implementation (no argparse interference)
"""

import sys
import os
import logging
import time
import shutil

# Set up paths
sys.path.insert(0, "C:/TripoSR")
os.makedirs("C:/Users/you81/デスクトップ/Chronos/apps/pon/data", exist_ok=True)

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Imports
import numpy as np
import rembg
import torch
from PIL import Image
from tsr.system import TSR
from tsr.utils import remove_background, resize_foreground

print("[INIT] TripoSR pon 3D generation")

# Config
image_path = "C:/Users/you81/デスクトップ/Chronos/apps/pon/data/pon_illustration.png"
device = "cuda:0" if torch.cuda.is_available() else "cpu"
output_dir = "C:/Users/you81/デスクトップ/Chronos/apps/pon/data"

print(f"[1] Loading image: {image_path}")
image = Image.open(image_path).convert("RGB")
print(f"    Size: {image.size}")

print("[2] Removing background...")
rembg_session = rembg.new_session()
image_rgba = remove_background(image, rembg_session)
image_rgba = resize_foreground(image_rgba, 0.85)

# Debug: Save background removed image
debug_path = os.path.join(output_dir, "debug_bg_removed.png")
image_rgba.save(debug_path)
print(f"    Saved debug image: {debug_path}")

# Convert RGBA to RGB with white background composite
image_np = np.array(image_rgba).astype(np.float32) / 255.0
image_rgb = image_np[:, :, :3] * image_np[:, :, 3:4] + (1 - image_np[:, :, 3:4]) * 1.0
image_final = Image.fromarray((image_rgb * 255.0).astype(np.uint8))

# Debug: Save final preprocessed image
final_debug_path = os.path.join(output_dir, "debug_final_input.png")
image_final.save(final_debug_path)
print(f"    Saved final input: {final_debug_path}")

print("[3] Loading TripoSR model...")
try:
    model = TSR.from_pretrained(
        "stabilityai/TripoSR",
        config_name="config.yaml",
        weight_name="model.ckpt",
    )
    print(f"    Model loaded, device: {device}")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

model.renderer.set_chunk_size(16384)  # chunk_size UP for better quality
model.to(device)

print("[4] Running 3D inference (2-5 min on CPU)...")
with torch.no_grad():
    scene_codes = model([image_final], device=device)

print("[5] Extracting mesh (resolution=1024, MAXIMUM quality)...")
# resolution 512 → 1024: 4倍の頂点数 = より詳細なメッシュ
meshes = model.extract_mesh(scene_codes, has_vertex_color=True, resolution=1024)

print("[6] Exporting GLB...")
glb_path = os.path.join(output_dir, "pon.glb")
meshes[0].export(glb_path)
glb_size = os.path.getsize(glb_path) / (1024 * 1024)
print(f"    OK {glb_path} ({glb_size:.1f} MB)")

print("[7] Copying to VRM...")
vrm_path = os.path.join(output_dir, "pon.vrm")
shutil.copy(glb_path, vrm_path)
print(f"    OK {vrm_path}")

print("\n" + "="*60)
print("[SUCCESS] pon 高品質 3D avatar 生成完了！")
print("="*60)
print(f"\nFiles created:")
print(f"  GLB: {glb_path}")
print(f"  VRM: {vrm_path}")
print(f"\nBroadcast: python main.py pon")
