"""
pon（響 凪）の 3D モデルを自動生成

identity.json から キャラ情報を取得して、
Python で人型メッシュ + 猫耳 + 尻尾を生成
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


def create_pon_mesh(identity: dict) -> trimesh.Trimesh:
    """
    pon（響 凪）のメッシュを生成 - 人間らしい形状

    仕様：
    - 女性、黒髪ボブ、紫がかった紺色の目
    - 黒猫のような垂れた耳と尻尾
    - オーバーサイズパーカー + ジーンズ
    - 物静かで儚げな雰囲気

    部品：
    - 頭（顔 + 髪で人間らしく）
    - 顔パーツ（目・鼻・口）
    - 体（肩・腰で人間的比率）
    - 腕・脚（より自然な比率）
    - 猫耳・尻尾
    """
    meshes = []

    # === 頭部 ===
    # 顔のベース（球を少し潰した形）
    head = icosphere(subdivisions=4, radius=0.12)
    head.apply_translation([0, 0.43, 0])
    meshes.append(head)

    # === 髪（ボブ髪を表現） ===
    # 髪は頭より大きな球で覆う
    hair_back = icosphere(subdivisions=3, radius=0.14)
    hair_back.apply_translation([0, 0.42, -0.02])
    meshes.append(hair_back)

    # 髪の左サイド
    hair_left = icosphere(subdivisions=2, radius=0.08)
    hair_left.apply_translation([-0.10, 0.40, 0])
    meshes.append(hair_left)

    # 髪の右サイド
    hair_right = icosphere(subdivisions=2, radius=0.08)
    hair_right.apply_translation([0.10, 0.40, 0])
    meshes.append(hair_right)

    # === 目 === （紫がかった紺色）
    left_eye = icosphere(subdivisions=2, radius=0.032)
    left_eye.apply_translation([-0.045, 0.455, 0.095])
    meshes.append(left_eye)

    right_eye = icosphere(subdivisions=2, radius=0.032)
    right_eye.apply_translation([0.045, 0.455, 0.095])
    meshes.append(right_eye)

    # === 目の白い部分（瞳のハイライト） ===
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

    # === 体 === （オーバーサイズパーカー）
    # 肩を広めに
    body = box(extents=[0.20, 0.30, 0.13])
    body.apply_translation([0, 0.14, 0])
    meshes.append(body)

    # 肩パッド（ゆったり感）
    left_shoulder = icosphere(subdivisions=2, radius=0.055)
    left_shoulder.apply_translation([-0.115, 0.28, 0])
    meshes.append(left_shoulder)

    right_shoulder = icosphere(subdivisions=2, radius=0.055)
    right_shoulder.apply_translation([0.115, 0.28, 0])
    meshes.append(right_shoulder)

    # === 腕（左） === （より人間的）
    left_arm = cylinder(radius=0.032, height=0.30)
    left_arm.apply_translation([-0.135, 0.16, 0])
    meshes.append(left_arm)

    # === 腕（右） === （より人間的）
    right_arm = cylinder(radius=0.032, height=0.30)
    right_arm.apply_translation([0.135, 0.16, 0])
    meshes.append(right_arm)

    # === 脚（左） ===
    left_leg = cylinder(radius=0.038, height=0.35)
    left_leg.apply_translation([-0.065, -0.10, 0])
    meshes.append(left_leg)

    # === 脚（右） ===
    right_leg = cylinder(radius=0.038, height=0.35)
    right_leg.apply_translation([0.065, -0.10, 0])
    meshes.append(right_leg)

    # === 猫耳（左） === （垂れた形）
    left_ear_main = cylinder(radius=0.028, height=0.13)
    left_ear_main.apply_translation([-0.075, 0.53, 0])
    # X軸で回転（垂れた感じ）
    rotation_matrix = trimesh.transformations.rotation_matrix(
        0.25, [1, 0, 0]
    )
    left_ear_main.apply_transform(rotation_matrix)
    meshes.append(left_ear_main)

    # 耳の内側（ピンク色に見えるように）
    left_ear_inner = cylinder(radius=0.015, height=0.10)
    left_ear_inner.apply_translation([-0.075, 0.52, 0.010])
    left_ear_inner.apply_transform(rotation_matrix)
    meshes.append(left_ear_inner)

    # === 猫耳（右） ===
    right_ear_main = cylinder(radius=0.028, height=0.13)
    right_ear_main.apply_translation([0.075, 0.53, 0])
    right_ear_main.apply_transform(rotation_matrix)
    meshes.append(right_ear_main)

    right_ear_inner = cylinder(radius=0.015, height=0.10)
    right_ear_inner.apply_translation([0.075, 0.52, 0.010])
    right_ear_inner.apply_transform(rotation_matrix)
    meshes.append(right_ear_inner)

    # === 尻尾（曲線状） ===
    tail_segments = []
    for i in range(5):
        seg = cylinder(radius=0.020, height=0.12)
        x_offset = 0.10 * np.sin(i * 0.4)
        y_offset = 0.15 - (i * 0.06)
        z_offset = -0.08 - (i * 0.10)
        seg.apply_translation([x_offset, y_offset, z_offset])

        # 回転（尻尾が曲がるように）
        tail_rot = trimesh.transformations.rotation_matrix(
            0.2 * i, [1, 0, 1]
        )
        seg.apply_transform(tail_rot)
        tail_segments.append(seg)

    meshes.extend(tail_segments)

    # === すべてのメッシュを結合 ===
    combined = trimesh.util.concatenate(meshes)

    return combined


def generate_pon_vrm(identity_path: str, output_path: str) -> bool:
    """
    pon の VRM を自動生成

    identity.json → 3D メッシュ → VRM
    """
    try:
        print("[PON_GEN] pon モデル生成開始...")

        # identity 読み込み
        identity = load_identity(identity_path)
        name = identity.get('name', 'pon')
        appearance = identity.get('appearance', {})

        print(f"[PON_GEN] キャラ: {name}")
        print(f"[PON_GEN] 見た目: {appearance}")

        # メッシュ生成
        print("[PON_GEN] メッシュ生成中...")
        mesh = create_pon_mesh(identity)

        # GLB で一時保存
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_glb = os.path.join(temp_dir, "pon_model.glb")
        mesh.export(temp_glb)

        print(f"[PON_GEN] 一時 GLB: {temp_glb}")

        # GLB → VRM に変換
        # （簡略版: GLB をそのまま VRM として保存）
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        with open(temp_glb, 'rb') as f:
            glb_data = f.read()

        with open(output_path, 'wb') as f:
            f.write(glb_data)

        print(f"[PON_GEN] VRM 生成完了: {output_path}")
        print(f"[PON_GEN] ファイルサイズ: {len(glb_data) / 1024:.1f} KB")

        return True

    except Exception as e:
        print(f"[PON_GEN] エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    identity_path = "apps/pon/data/identity.json"
    output_path = "apps/pon/data/pon.vrm"

    ok = generate_pon_vrm(identity_path, output_path)
    sys.exit(0 if ok else 1)
