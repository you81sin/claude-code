# -*- coding: utf-8 -*-
"""
desktpomate 3D Avatar Generator
Gold × Purple twintails, sailor uniform
High-quality procedural 3D model
"""

import numpy as np
import trimesh
from trimesh.creation import cylinder, icosphere, box
import os


def create_twintails_gold() -> list:
    """Create gold twintails"""
    meshes = []

    # Left twintail
    for i in range(4):
        seg = cylinder(radius=0.025, height=0.15)
        x = -0.12
        y = 0.48 - (i * 0.08)
        z = 0.08
        seg.apply_translation([x, y, z])

        # Curve rotation
        rot = trimesh.transformations.rotation_matrix(0.2 * i, [1, 0, 1])
        seg.apply_transform(rot)
        meshes.append(seg)

    # Right twintail
    for i in range(4):
        seg = cylinder(radius=0.025, height=0.15)
        x = 0.12
        y = 0.48 - (i * 0.08)
        z = 0.08
        seg.apply_translation([x, y, z])

        rot = trimesh.transformations.rotation_matrix(0.2 * i, [1, 0, 1])
        seg.apply_transform(rot)
        meshes.append(seg)

    return meshes


def create_twintails_purple() -> list:
    """Create purple twintail tips"""
    meshes = []

    # Purple tips (small spheres at end of twintails)
    left_tip = icosphere(subdivisions=2, radius=0.035)
    left_tip.apply_translation([-0.12, 0.16, 0.08])
    meshes.append(left_tip)

    right_tip = icosphere(subdivisions=2, radius=0.035)
    right_tip.apply_translation([0.12, 0.16, 0.08])
    meshes.append(right_tip)

    return meshes


def create_face_desktpomate() -> list:
    """Create detailed anime face"""
    meshes = []

    # Head
    head = icosphere(subdivisions=4, radius=0.16)
    head.apply_translation([0, 0.43, 0])
    meshes.append(head)

    # Large violet eyes
    eye_left = icosphere(subdivisions=3, radius=0.052)
    eye_left.apply_scale([1.3, 1.5, 1.0])
    eye_left.apply_translation([-0.058, 0.04, 0.135])
    meshes.append(eye_left)

    eye_right = icosphere(subdivisions=3, radius=0.052)
    eye_right.apply_scale([1.3, 1.5, 1.0])
    eye_right.apply_translation([0.058, 0.04, 0.135])
    meshes.append(eye_right)

    # Dark iris (violet)
    iris_left = icosphere(subdivisions=2, radius=0.032)
    iris_left.apply_translation([-0.058, 0.02, 0.142])
    meshes.append(iris_left)

    iris_right = icosphere(subdivisions=2, radius=0.032)
    iris_right.apply_translation([0.058, 0.02, 0.142])
    meshes.append(iris_right)

    # Pupils with shine
    pupil_left = icosphere(subdivisions=2, radius=0.018)
    pupil_left.apply_translation([-0.058, 0.015, 0.152])
    meshes.append(pupil_left)

    pupil_right = icosphere(subdivisions=2, radius=0.018)
    pupil_right.apply_translation([0.058, 0.015, 0.152])
    meshes.append(pupil_right)

    # Eyebrows
    brow_left = cylinder(radius=0.009, height=0.048)
    brow_left.apply_translation([-0.058, 0.12, 0.125])
    meshes.append(brow_left)

    brow_right = cylinder(radius=0.009, height=0.048)
    brow_right.apply_translation([0.058, 0.12, 0.125])
    meshes.append(brow_right)

    # Cute nose
    nose = icosphere(subdivisions=1, radius=0.014)
    nose.apply_translation([0, -0.02, 0.115])
    meshes.append(nose)

    # Smile
    mouth = cylinder(radius=0.018, height=0.028)
    mouth.apply_translation([0, -0.085, 0.105])
    meshes.append(mouth)

    return meshes


def create_sailor_uniform() -> list:
    """Create sailor school uniform"""
    meshes = []

    # Sailor jacket top (navy blue)
    jacket = box(extents=[0.26, 0.36, 0.16])
    jacket.apply_translation([0, 0.12, -0.01])
    meshes.append(jacket)

    # Collar (white)
    collar = box(extents=[0.28, 0.06, 0.18])
    collar.apply_translation([0, 0.32, -0.02])
    meshes.append(collar)

    # Red ribbon
    ribbon = box(extents=[0.08, 0.14, 0.22])
    ribbon.apply_translation([0, 0.18, 0.095])
    meshes.append(ribbon)

    # Skirt (navy)
    skirt = cylinder(radius=0.18, height=0.28)
    skirt.apply_translation([0, -0.08, 0])
    meshes.append(skirt)

    # White sailor accents on skirt
    accent_front = box(extents=[0.16, 0.08, 0.05])
    accent_front.apply_translation([0, -0.15, 0.095])
    meshes.append(accent_front)

    return meshes


def create_arms_desktpomate() -> list:
    """Create arms with hands"""
    meshes = []

    # Left arm
    arm_left = cylinder(radius=0.038, height=0.34)
    arm_left.apply_translation([-0.16, 0.16, 0])
    meshes.append(arm_left)

    # Left hand
    hand_left = icosphere(subdivisions=2, radius=0.032)
    hand_left.apply_translation([-0.16, -0.03, 0])
    meshes.append(hand_left)

    # Right arm
    arm_right = cylinder(radius=0.038, height=0.34)
    arm_right.apply_translation([0.16, 0.16, 0])
    meshes.append(arm_right)

    # Right hand
    hand_right = icosphere(subdivisions=2, radius=0.032)
    hand_right.apply_translation([0.16, -0.03, 0])
    meshes.append(hand_right)

    return meshes


def create_legs_desktpomate() -> list:
    """Create legs with socks and shoes"""
    meshes = []

    # Left leg
    leg_left = cylinder(radius=0.045, height=0.40)
    leg_left.apply_translation([-0.08, -0.15, 0])
    meshes.append(leg_left)

    # Navy-orange socks (left)
    sock_left_navy = cylinder(radius=0.048, height=0.12)
    sock_left_navy.apply_translation([-0.08, -0.35, 0])
    meshes.append(sock_left_navy)

    sock_left_orange = cylinder(radius=0.048, height=0.10)
    sock_left_orange.apply_translation([-0.08, -0.50, 0])
    meshes.append(sock_left_orange)

    # Left shoe
    shoe_left = box(extents=[0.052, 0.095, 0.075])
    shoe_left.apply_translation([-0.08, -0.62, 0])
    meshes.append(shoe_left)

    # Right leg
    leg_right = cylinder(radius=0.045, height=0.40)
    leg_right.apply_translation([0.08, -0.15, 0])
    meshes.append(leg_right)

    # Navy-orange socks (right)
    sock_right_navy = cylinder(radius=0.048, height=0.12)
    sock_right_navy.apply_translation([0.08, -0.35, 0])
    meshes.append(sock_right_navy)

    sock_right_orange = cylinder(radius=0.048, height=0.10)
    sock_right_orange.apply_translation([0.08, -0.50, 0])
    meshes.append(sock_right_orange)

    # Right shoe
    shoe_right = box(extents=[0.052, 0.095, 0.075])
    shoe_right.apply_translation([0.08, -0.62, 0])
    meshes.append(shoe_right)

    return meshes


def apply_desktpomate_materials(mesh: trimesh.Trimesh):
    """Apply colors matching desktpomate appearance"""

    for i, face in enumerate(mesh.faces):
        face_center = mesh.vertices[face].mean(axis=0)
        bounds = mesh.bounds
        face_size = np.linalg.norm(
            mesh.vertices[face[1]] - mesh.vertices[face[0]]
        )

        # Gold hair (twintails left/right high)
        if (abs(face_center[0]) > 0.08 and
            face_center[1] > 0.35 and
            face_center[2] > 0.05):
            mesh.visual.vertex_colors[face] = [255, 215, 0, 255]  # Gold

        # Purple hair tips
        elif (abs(face_center[0]) > 0.08 and
              face_center[1] < 0.25 and
              face_center[2] > 0.05):
            mesh.visual.vertex_colors[face] = [153, 50, 204, 255]  # Purple

        # Violet eyes
        elif (abs(face_center[0]) > 0.04 and
              face_center[1] > 0.35 and
              face_size < 0.12):
            mesh.visual.vertex_colors[face] = [138, 43, 226, 255]  # Violet

        # Dark iris/pupils
        elif (abs(face_center[0]) > 0.04 and
              face_center[1] > 0.38 and
              face_size < 0.05):
            mesh.visual.vertex_colors[face] = [50, 20, 100, 255]  # Dark purple

        # Skin tone
        elif (abs(face_center[0]) < 0.12 and
              face_center[1] > 0.25):
            mesh.visual.vertex_colors[face] = [245, 200, 180, 255]  # Fair skin

        # Navy blue (jacket, upper skirt)
        elif (face_center[1] > 0.05 and
              face_center[1] < 0.35):
            mesh.visual.vertex_colors[face] = [25, 25, 112, 255]  # Navy

        # White (collar, accents)
        elif (face_center[1] > 0.28 and
              face_center[1] < 0.38):
            mesh.visual.vertex_colors[face] = [245, 245, 245, 255]  # White

        # Red (ribbon)
        elif (abs(face_center[0]) < 0.08 and
              face_center[1] > 0.12 and
              face_center[1] < 0.28):
            mesh.visual.vertex_colors[face] = [220, 20, 60, 255]  # Crimson

        # Navy socks
        elif (face_center[1] < -0.30 and
              face_center[1] > -0.50):
            mesh.visual.vertex_colors[face] = [25, 25, 112, 255]  # Navy

        # Orange socks
        elif (face_center[1] < -0.45 and
              face_center[1] > -0.60):
            mesh.visual.vertex_colors[face] = [255, 140, 0, 255]  # Orange

        # Shoes
        elif face_center[1] < -0.55:
            mesh.visual.vertex_colors[face] = [40, 40, 40, 255]  # Dark gray

        # Default skin
        else:
            mesh.visual.vertex_colors[face] = [230, 190, 160, 255]


def generate_desktpomate() -> trimesh.Trimesh:
    """Generate complete desktpomate 3D model"""

    print("[DESKTPOMATE] Creating face...")
    meshes = create_face_desktpomate()

    print("[DESKTPOMATE] Creating gold twintails...")
    meshes.extend(create_twintails_gold())

    print("[DESKTPOMATE] Creating purple twintail tips...")
    meshes.extend(create_twintails_purple())

    print("[DESKTPOMATE] Creating sailor uniform...")
    meshes.extend(create_sailor_uniform())

    print("[DESKTPOMATE] Creating arms...")
    meshes.extend(create_arms_desktpomate())

    print("[DESKTPOMATE] Creating legs and shoes...")
    meshes.extend(create_legs_desktpomate())

    print("[DESKTPOMATE] Combining meshes...")
    combined = trimesh.util.concatenate(meshes)

    print("[DESKTPOMATE] Applying materials...")
    apply_desktpomate_materials(combined)

    return combined


def main():
    print("=" * 60)
    print("[DESKTPOMATE 3D Avatar Generator]")
    print("=" * 60)

    print("\n[DESKTPOMATE] Generating high-quality 3D model...")

    mesh = generate_desktpomate()

    output_path = "apps/desktpomate/data/desktpomate.glb"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"\n[DESKTPOMATE] Exporting to GLB...")
    mesh.export(output_path)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[DESKTPOMATE] Saved: {output_path} ({size_mb:.1f} MB)")

    print("\n[SUCCESS] desktpomate 3D avatar ready!")
    print("[NEXT] Run CHRONOS with: python main.py desktpomate")

    return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
