"""
drivers/avatar/simple_generator.py
-----------------------------------
シンプルな3Dアバター自動生成（品質は無視）。
pymeshio + trimesh で GLB を自動生成。

品質は後で手動作成した VRM で置き換え可能。
"""

import os
from observation.logger import log


def generate_simple_avatar(name: str, appearance: dict, output_path: str) -> bool:
    """
    シンプルな3Dアバター自動生成。
    球体（顔）+ 立方体（体）+ 球体（目）で最小限のモデル化。

    appearance: キャラクター情報（使用しない、互換性のため）
    output_path: GLB 保存先
    戻り値: 成功時 True
    """
    try:
        import trimesh
        import numpy as np
    except ImportError:
        log("[SIMPLE_AVATAR] trimesh がインストールされていません")
        log("[SIMPLE_AVATAR] pip install trimesh を実行してください")
        return False

    try:
        log(f"[SIMPLE_AVATAR] シンプルアバター生成開始: {name}")

        # === 顔（球体） ===
        face = trimesh.creation.icosphere(subdivisions=2, radius=0.3)
        face.visual.vertex_colors = [200, 180, 160, 255]  # 肌色

        # === 体（立方体） ===
        body = trimesh.creation.box(extents=[0.2, 0.4, 0.1])
        body.apply_translation([0, -0.3, 0])
        body.visual.vertex_colors = [100, 100, 150, 255]  # 服色

        # === 左目（小さい球体） ===
        left_eye = trimesh.creation.icosphere(subdivisions=1, radius=0.05)
        left_eye.apply_translation([-0.1, 0.1, 0.28])
        left_eye.visual.vertex_colors = [50, 50, 50, 255]  # 黒

        # === 右目（小さい球体） ===
        right_eye = trimesh.creation.icosphere(subdivisions=1, radius=0.05)
        right_eye.apply_translation([0.1, 0.1, 0.28])
        right_eye.visual.vertex_colors = [50, 50, 50, 255]  # 黒

        # === 結合 ===
        mesh = trimesh.util.concatenate([face, body, left_eye, right_eye])

        # === GLB 保存 ===
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        mesh.export(output_path)

        log(f"[SIMPLE_AVATAR] GLB 生成完了 → {output_path}")
        return True

    except Exception as e:
        log(f"[SIMPLE_AVATAR] エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
