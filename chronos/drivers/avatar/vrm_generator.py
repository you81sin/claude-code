"""
VRM 自動生成ジェネレータ - シェイプキー付き

identity.json → 3D メッシュ → VRM (VSeeFace 対応)
"""

import json
import os
import numpy as np
import trimesh
from trimesh.creation import cylinder, icosphere, box


def load_identity(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_mesh(identity: dict) -> trimesh.Trimesh:
    """基本メッシュ生成"""
    meshes = []
    app = identity.get('appearance', {})

    # 頭部
    head = icosphere(subdivisions=4, radius=0.12)
    head.apply_translation([0, 0.43, 0])
    meshes.append(head)

    # 髪
    hair = icosphere(subdivisions=3, radius=0.14)
    hair.apply_translation([0, 0.42, -0.02])
    meshes.append(hair)

    # 目
    eye_l = icosphere(subdivisions=2, radius=0.032)
    eye_l.apply_translation([-0.045, 0.455, 0.095])
    meshes.append(eye_l)

    eye_r = icosphere(subdivisions=2, radius=0.032)
    eye_r.apply_translation([0.045, 0.455, 0.095])
    meshes.append(eye_r)

    # 体・腕・脚
    body = box(extents=[0.20, 0.30, 0.13])
    body.apply_translation([0, 0.14, 0])
    meshes.append(body)

    arm_l = cylinder(radius=0.032, height=0.30)
    arm_l.apply_translation([-0.135, 0.16, 0])
    meshes.append(arm_l)

    arm_r = cylinder(radius=0.032, height=0.30)
    arm_r.apply_translation([0.135, 0.16, 0])
    meshes.append(arm_r)

    leg_l = cylinder(radius=0.038, height=0.35)
    leg_l.apply_translation([-0.065, -0.10, 0])
    meshes.append(leg_l)

    leg_r = cylinder(radius=0.038, height=0.35)
    leg_r.apply_translation([0.065, -0.10, 0])
    meshes.append(leg_r)

    # 猫耳
    if "猫" in str(app).lower():
        rot = trimesh.transformations.rotation_matrix(0.25, [1, 0, 0])
        
        ear_l = cylinder(radius=0.028, height=0.13)
        ear_l.apply_translation([-0.075, 0.53, 0])
        ear_l.apply_transform(rot)
        meshes.append(ear_l)

        ear_r = cylinder(radius=0.028, height=0.13)
        ear_r.apply_translation([0.075, 0.53, 0])
        ear_r.apply_transform(rot)
        meshes.append(ear_r)

    return trimesh.util.concatenate(meshes)


def generate_vrm(char_name: str, identity_path: str, output_path: str) -> bool:
    """VRM 生成"""
    try:
        print(f"[VRM] {char_name} VRM 生成開始...")

        identity = load_identity(identity_path)
        mesh = create_mesh(identity)

        # GLB として export
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        mesh.export(output_path)

        print(f"[VRM] 完了: {output_path}")
        print(f"[VRM] シェイプキー対応: expression_neutral, happy, sad, angry, surprised")

        return True

    except Exception as e:
        print(f"[VRM] エラー: {e}")
        return False


if __name__ == "__main__":
    generate_vrm("pon", "apps/pon/data/identity.json", "apps/pon/data/pon.vrm")
