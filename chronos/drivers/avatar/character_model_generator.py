"""
複数 AI キャラクターの 3D モデル自動生成（汎用版）

identity.json から自動で 3D メッシュ生成
各キャラの appearance パラメータで見た目をカスタマイズ
"""

import json
import os
import numpy as np
import trimesh
from trimesh.creation import cylinder, icosphere, box


def load_identity(identity_path: str) -> dict:
    """identity.json を読み込み"""
    with open(identity_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_appearance_color(appearance: dict, color_type: str) -> tuple:
    """appearance から色情報を解析（RGB tuple）"""
    appearance_text = str(appearance).lower()

    # 髪色
    if color_type == "hair":
        if "黒" in appearance_text or "black" in appearance_text:
            return (0.1, 0.08, 0.09)  # 黒
        elif "茶" in appearance_text or "brown" in appearance_text:
            return (0.4, 0.25, 0.15)  # 茶髪
        elif "金" in appearance_text or "blonde" in appearance_text or "gold" in appearance_text:
            return (0.8, 0.7, 0.3)   # 金髪
        else:
            return (0.2, 0.15, 0.12)  # デフォルト（濃茶）

    # 目の色
    elif color_type == "eyes":
        if "紺" in appearance_text or "navy" in appearance_text:
            return (0.1, 0.1, 0.25)  # 紺色
        elif "青" in appearance_text or "blue" in appearance_text:
            return (0.2, 0.4, 0.6)   # 青
        elif "茶" in appearance_text or "brown" in appearance_text:
            return (0.4, 0.25, 0.1)  # 茶色
        elif "灰" in appearance_text or "gray" in appearance_text:
            return (0.3, 0.3, 0.3)   # 灰色
        else:
            return (0.15, 0.15, 0.3)  # デフォルト（紺）

    return (0.5, 0.5, 0.5)  # グレー


def create_character_mesh(identity: dict) -> trimesh.Trimesh:
    """
    キャラクターの 3D メッシュを生成（汎用）

    appearance から自動で形状・色をカスタマイズ
    """
    meshes = []
    name = identity.get('name', 'character')
    appearance = identity.get('appearance', {})

    # === 頭部 ===
    head = icosphere(subdivisions=4, radius=0.12)
    head.apply_translation([0, 0.43, 0])
    meshes.append(head)

    # === 髪 ===
    hair_back = icosphere(subdivisions=3, radius=0.14)
    hair_back.apply_translation([0, 0.42, -0.02])
    meshes.append(hair_back)

    hair_left = icosphere(subdivisions=2, radius=0.08)
    hair_left.apply_translation([-0.10, 0.40, 0])
    meshes.append(hair_left)

    hair_right = icosphere(subdivisions=2, radius=0.08)
    hair_right.apply_translation([0.10, 0.40, 0])
    meshes.append(hair_right)

    # === 目 ===
    left_eye = icosphere(subdivisions=2, radius=0.032)
    left_eye.apply_translation([-0.045, 0.455, 0.095])
    meshes.append(left_eye)

    right_eye = icosphere(subdivisions=2, radius=0.032)
    right_eye.apply_translation([0.045, 0.455, 0.095])
    meshes.append(right_eye)

    # 目の白い部分
    left_eye_white = icosphere(subdivisions=1, radius=0.010)
    left_eye_white.apply_translation([-0.035, 0.460, 0.112])
    meshes.append(left_eye_white)

    right_eye_white = icosphere(subdivisions=1, radius=0.010)
    right_eye_white.apply_translation([0.035, 0.460, 0.112])
    meshes.append(right_eye_white)

    # === 鼻 ===
    nose = icosphere(subdivisions=1, radius=0.015)
    nose.apply_translation([0, 0.42, 0.105])
    meshes.append(nose)

    # === 口 ===
    mouth = cylinder(radius=0.012, height=0.02)
    mouth.apply_translation([0, 0.39, 0.10])
    meshes.append(mouth)

    # === 体 ===
    body = box(extents=[0.20, 0.30, 0.13])
    body.apply_translation([0, 0.14, 0])
    meshes.append(body)

    left_shoulder = icosphere(subdivisions=2, radius=0.055)
    left_shoulder.apply_translation([-0.115, 0.28, 0])
    meshes.append(left_shoulder)

    right_shoulder = icosphere(subdivisions=2, radius=0.055)
    right_shoulder.apply_translation([0.115, 0.28, 0])
    meshes.append(right_shoulder)

    # === 腕 ===
    left_arm = cylinder(radius=0.032, height=0.30)
    left_arm.apply_translation([-0.135, 0.16, 0])
    meshes.append(left_arm)

    right_arm = cylinder(radius=0.032, height=0.30)
    right_arm.apply_translation([0.135, 0.16, 0])
    meshes.append(right_arm)

    # === 脚 ===
    left_leg = cylinder(radius=0.038, height=0.35)
    left_leg.apply_translation([-0.065, -0.10, 0])
    meshes.append(left_leg)

    right_leg = cylinder(radius=0.038, height=0.35)
    right_leg.apply_translation([0.065, -0.10, 0])
    meshes.append(right_leg)

    # === 特徴的なパーツ（appearance から判定） ===
    features_text = str(appearance.get('features', '')).lower()

    # 猫耳の有無
    if "猫" in features_text or "ear" in features_text:
        rotation_matrix = trimesh.transformations.rotation_matrix(0.25, [1, 0, 0])

        left_ear_main = cylinder(radius=0.028, height=0.13)
        left_ear_main.apply_translation([-0.075, 0.53, 0])
        left_ear_main.apply_transform(rotation_matrix)
        meshes.append(left_ear_main)

        left_ear_inner = cylinder(radius=0.015, height=0.10)
        left_ear_inner.apply_translation([-0.075, 0.52, 0.010])
        left_ear_inner.apply_transform(rotation_matrix)
        meshes.append(left_ear_inner)

        right_ear_main = cylinder(radius=0.028, height=0.13)
        right_ear_main.apply_translation([0.075, 0.53, 0])
        right_ear_main.apply_transform(rotation_matrix)
        meshes.append(right_ear_main)

        right_ear_inner = cylinder(radius=0.015, height=0.10)
        right_ear_inner.apply_translation([0.075, 0.52, 0.010])
        right_ear_inner.apply_transform(rotation_matrix)
        meshes.append(right_ear_inner)

    # 尻尾の有無
    if "尻尾" in features_text or "tail" in features_text:
        for i in range(5):
            seg = cylinder(radius=0.020, height=0.12)
            x_offset = 0.10 * np.sin(i * 0.4)
            y_offset = 0.15 - (i * 0.06)
            z_offset = -0.08 - (i * 0.10)
            seg.apply_translation([x_offset, y_offset, z_offset])

            tail_rot = trimesh.transformations.rotation_matrix(0.2 * i, [1, 0, 1])
            seg.apply_transform(tail_rot)
            meshes.append(seg)

    # === メッシュ結合 ===
    combined = trimesh.util.concatenate(meshes)

    return combined


def generate_character_model(character_name: str, identity_path: str, output_path: str) -> bool:
    """
    キャラクター 3D モデルを自動生成

    Args:
        character_name: キャラクター名（pon, mlm, doku など）
        identity_path: identity.json のパス
        output_path: 出力 VRM パス

    Returns:
        bool: 成功したか
    """
    try:
        print(f"[CHARGEN] {character_name} モデル生成開始...")

        # identity 読み込み
        identity = load_identity(identity_path)
        name = identity.get('name', character_name)

        print(f"[CHARGEN] キャラ: {name}")

        # メッシュ生成
        print(f"[CHARGEN] メッシュ生成中...")
        mesh = create_character_mesh(identity)

        # GLB で一時保存
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_glb = os.path.join(temp_dir, f"{character_name}_model.glb")
        mesh.export(temp_glb)

        print(f"[CHARGEN] 一時 GLB: {temp_glb}")

        # VRM として保存
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        with open(temp_glb, 'rb') as f:
            glb_data = f.read()

        with open(output_path, 'wb') as f:
            f.write(glb_data)

        print(f"[CHARGEN] {character_name} モデル生成完了: {output_path}")
        print(f"[CHARGEN] ファイルサイズ: {len(glb_data) / 1024:.1f} KB")

        return True

    except Exception as e:
        print(f"[CHARGEN] エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys

    # テスト：pon, mlm, doku を生成
    characters = [
        ("pon", "apps/pon/data/identity.json", "apps/pon/data/pon.vrm"),
        ("mlm", "apps/mlm/data/identity.json", "apps/mlm/data/mlm.vrm"),
        ("doku", "apps/doku/data/identity.json", "apps/doku/data/doku.vrm"),
    ]

    for char_name, identity_path, output_path in characters:
        if os.path.exists(identity_path):
            generate_character_model(char_name, identity_path, output_path)
        else:
            print(f"[CHARGEN] {char_name} の identity.json が見つかりません: {identity_path}")

    sys.exit(0)
