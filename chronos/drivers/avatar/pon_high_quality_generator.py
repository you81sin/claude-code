# -*- coding: utf-8 -*-
"""
High Quality Procedural pon Generator
100% AI Auto-Generated, No Manual Assets
Anime Character Quality Level
"""

import numpy as np
import trimesh
from trimesh.creation import cylinder, icosphere, box
import os


def create_anime_eyes(position_x: float) -> trimesh.Trimesh:
    """Create large anime-style eyes"""
    # Outer eye white (large, oval)
    eye = icosphere(subdivisions=3, radius=0.05)
    eye.apply_scale([1.2, 1.4, 1.0])  # Make oval
    eye.apply_translation([position_x, 0.0, 0.12])

    return eye


def create_eye_iris(position_x: float) -> trimesh.Trimesh:
    """Create dark iris"""
    iris = icosphere(subdivisions=2, radius=0.028)
    iris.apply_translation([position_x, -0.008, 0.125])

    return iris


def create_eye_pupil(position_x: float) -> trimesh.Trimesh:
    """Create pupils with shine"""
    pupil = icosphere(subdivisions=2, radius=0.015)
    pupil.apply_translation([position_x, -0.01, 0.135])

    return pupil


def create_nose() -> trimesh.Trimesh:
    """Small anime nose"""
    nose = icosphere(subdivisions=1, radius=0.012)
    nose.apply_translation([0, -0.03, 0.11])

    return nose


def create_mouth() -> trimesh.Trimesh:
    """Mouth shape"""
    mouth = cylinder(radius=0.016, height=0.025)
    mouth.apply_translation([0, -0.08, 0.10])

    return mouth


def create_face(head_radius: float = 0.15) -> list:
    """Create detailed face"""
    meshes = []

    # Main head sphere
    head = icosphere(subdivisions=4, radius=head_radius)
    head.apply_translation([0, 0.42, 0])
    meshes.append(head)

    # Eyes
    meshes.append(create_anime_eyes(-0.055))
    meshes.append(create_anime_eyes(0.055))

    # Iris (dark navy/purple)
    meshes.append(create_eye_iris(-0.055))
    meshes.append(create_eye_iris(0.055))

    # Pupils
    meshes.append(create_eye_pupil(-0.055))
    meshes.append(create_eye_pupil(0.055))

    # Eyebrows
    eyebrow_l = cylinder(radius=0.008, height=0.045)
    eyebrow_l.apply_translation([-0.055, 0.08, 0.115])
    meshes.append(eyebrow_l)

    eyebrow_r = cylinder(radius=0.008, height=0.045)
    eyebrow_r.apply_translation([0.055, 0.08, 0.115])
    meshes.append(eyebrow_r)

    # Nose
    meshes.append(create_nose())

    # Mouth
    meshes.append(create_mouth())

    return meshes


def create_hair_bob() -> list:
    """Create shoulder-length black bob haircut"""
    meshes = []

    # Hair back (main volume)
    hair_back = icosphere(subdivisions=3, radius=0.165)
    hair_back.apply_translation([0, 0.40, -0.05])
    meshes.append(hair_back)

    # Hair sides (bob effect)
    hair_left = icosphere(subdivisions=3, radius=0.12)
    hair_left.apply_scale([0.8, 1.0, 1.0])
    hair_left.apply_translation([-0.15, 0.35, 0])
    meshes.append(hair_left)

    hair_right = icosphere(subdivisions=3, radius=0.12)
    hair_right.apply_scale([0.8, 1.0, 1.0])
    hair_right.apply_translation([0.15, 0.35, 0])
    meshes.append(hair_right)

    # Front hair bangs
    bang_left = icosphere(subdivisions=2, radius=0.08)
    bang_left.apply_translation([-0.08, 0.45, 0.05])
    meshes.append(bang_left)

    bang_right = icosphere(subdivisions=2, radius=0.08)
    bang_right.apply_translation([0.08, 0.45, 0.05])
    meshes.append(bang_right)

    return meshes


def create_cat_ears() -> list:
    """Create detailed cat ears"""
    meshes = []

    rotation_matrix = trimesh.transformations.rotation_matrix(0.3, [1, 0, 0])

    # Left ear outer
    ear_l_main = cylinder(radius=0.035, height=0.15)
    ear_l_main.apply_translation([-0.085, 0.545, 0])
    ear_l_main.apply_transform(rotation_matrix)
    meshes.append(ear_l_main)

    # Left ear inner (pink)
    ear_l_inner = cylinder(radius=0.018, height=0.12)
    ear_l_inner.apply_translation([-0.085, 0.535, 0.015])
    ear_l_inner.apply_transform(rotation_matrix)
    meshes.append(ear_l_inner)

    # Right ear outer
    ear_r_main = cylinder(radius=0.035, height=0.15)
    ear_r_main.apply_translation([0.085, 0.545, 0])
    ear_r_main.apply_transform(rotation_matrix)
    meshes.append(ear_r_main)

    # Right ear inner (pink)
    ear_r_inner = cylinder(radius=0.018, height=0.12)
    ear_r_inner.apply_translation([0.085, 0.535, 0.015])
    ear_r_inner.apply_transform(rotation_matrix)
    meshes.append(ear_r_inner)

    return meshes


def create_body() -> list:
    """Create torso with clothing layers"""
    meshes = []

    # Shirt layer (under hoodie)
    shirt = box(extents=[0.22, 0.32, 0.14])
    shirt.apply_translation([0, 0.12, 0])
    meshes.append(shirt)

    # Hoodie (outer layer, slightly larger)
    hoodie = box(extents=[0.24, 0.34, 0.15])
    hoodie.apply_translation([0, 0.13, -0.01])
    meshes.append(hoodie)

    # Shoulders (round out the top)
    shoulder_l = icosphere(subdivisions=2, radius=0.062)
    shoulder_l.apply_translation([-0.125, 0.30, 0])
    meshes.append(shoulder_l)

    shoulder_r = icosphere(subdivisions=2, radius=0.062)
    shoulder_r.apply_translation([0.125, 0.30, 0])
    meshes.append(shoulder_r)

    return meshes


def create_arms() -> list:
    """Create arms"""
    meshes = []

    # Left arm
    arm_l = cylinder(radius=0.036, height=0.32)
    arm_l.apply_translation([-0.145, 0.16, 0])
    meshes.append(arm_l)

    # Left hand
    hand_l = icosphere(subdivisions=2, radius=0.028)
    hand_l.apply_translation([-0.145, -0.02, 0])
    meshes.append(hand_l)

    # Right arm
    arm_r = cylinder(radius=0.036, height=0.32)
    arm_r.apply_translation([0.145, 0.16, 0])
    meshes.append(arm_r)

    # Right hand
    hand_r = icosphere(subdivisions=2, radius=0.028)
    hand_r.apply_translation([0.145, -0.02, 0])
    meshes.append(hand_r)

    return meshes


def create_legs() -> list:
    """Create legs with jeans (proportionally balanced)"""
    meshes = []

    # Left leg (thinner, shorter)
    leg_l = cylinder(radius=0.035, height=0.34)
    leg_l.apply_translation([-0.068, -0.08, 0])
    meshes.append(leg_l)

    # Left foot (smaller)
    foot_l = box(extents=[0.038, 0.05, 0.055])
    foot_l.apply_translation([-0.068, -0.28, 0])
    meshes.append(foot_l)

    # Right leg (thinner, shorter)
    leg_r = cylinder(radius=0.035, height=0.34)
    leg_r.apply_translation([0.068, -0.08, 0])
    meshes.append(leg_r)

    # Right foot (smaller)
    foot_r = box(extents=[0.038, 0.05, 0.055])
    foot_r.apply_translation([0.068, -0.28, 0])
    meshes.append(foot_r)

    return meshes


def create_tail() -> list:
    """Create cat tail (curved)"""
    meshes = []

    # Tail segments for curve effect
    for i in range(6):
        seg = cylinder(radius=0.025, height=0.13)

        # Position along curve
        x_offset = 0.12 * np.sin(i * 0.5)
        y_offset = 0.15 - (i * 0.065)
        z_offset = -0.12 - (i * 0.10)

        seg.apply_translation([x_offset, y_offset, z_offset])

        # Rotate for curve
        tail_rot = trimesh.transformations.rotation_matrix(0.25 * i, [1, 0, 1])
        seg.apply_transform(tail_rot)

        meshes.append(seg)

    return meshes


def apply_pon_materials(mesh: trimesh.Trimesh):
    """Apply colors to mesh based on size and position"""

    for i, face in enumerate(mesh.faces):
        # Get face center
        face_center = mesh.vertices[face].mean(axis=0)
        bounds = mesh.bounds
        face_size = np.linalg.norm(
            mesh.vertices[face[1]] - mesh.vertices[face[0]]
        )

        # Determine material by position and size
        material = trimesh.visual.ColorVisuals()

        # Eyes (navy-purple)
        if (abs(face_center[0]) > 0.04 and
            face_center[1] > 0.35 and
            face_size < 0.12):
            mesh.visual.vertex_colors[face] = [38, 38, 89, 255]  # Navy purple

        # Iris/pupils (dark)
        elif (abs(face_center[0]) > 0.04 and
              face_center[1] > 0.38 and
              face_size < 0.05):
            mesh.visual.vertex_colors[face] = [20, 20, 40, 255]  # Very dark

        # Hair (black)
        elif face_center[1] > 0.30:
            mesh.visual.vertex_colors[face] = [25, 25, 25, 255]  # Black

        # Skin (light peachy)
        elif (abs(face_center[0]) < 0.12 and
              face_center[1] > 0.25):
            mesh.visual.vertex_colors[face] = [230, 190, 170, 255]  # Skin tone

        # Clothing (hoodie - light gray)
        elif face_center[1] < 0.35 and face_center[1] > -0.05:
            mesh.visual.vertex_colors[face] = [110, 110, 120, 255]  # Gray

        # Jeans/pants (dark blue)
        elif face_center[1] < 0.05 and face_center[1] > -0.25:
            mesh.visual.vertex_colors[face] = [35, 45, 75, 255]  # Jeans blue

        # Feet/shoes (dark)
        elif face_center[1] < -0.25:
            mesh.visual.vertex_colors[face] = [40, 40, 40, 255]  # Dark gray

        # Default (light gray)
        else:
            mesh.visual.vertex_colors[face] = [180, 180, 180, 255]


def generate_high_quality_pon() -> trimesh.Trimesh:
    """Generate complete high-quality pon model (162cm scale)"""

    print("[PON] Creating face...")
    meshes = create_face()

    print("[PON] Creating hair...")
    meshes.extend(create_hair_bob())

    print("[PON] Creating cat ears...")
    meshes.extend(create_cat_ears())

    print("[PON] Creating body...")
    meshes.extend(create_body())

    print("[PON] Creating arms...")
    meshes.extend(create_arms())

    print("[PON] Creating legs...")
    meshes.extend(create_legs())

    print("[PON] Creating tail...")
    meshes.extend(create_tail())

    print("[PON] Combining meshes...")
    combined = trimesh.util.concatenate(meshes)

    print("[PON] Applying materials...")
    apply_pon_materials(combined)

    # Scale to 162cm height (identity.json specification)
    # Procedural model ~100cm → scale to 162cm
    scale_factor = 1.62
    print(f"[PON] Scaling to 162cm (factor: {scale_factor}x)...")
    combined.apply_scale(scale_factor)

    return combined


def main():
    print("=" * 60)
    print("[PON High Quality Procedural Generator]")
    print("=" * 60)

    print("\n[PON] Generating high-quality 3D model...")

    mesh = generate_high_quality_pon()

    output_path = "C:/Users/you81/デスクトップ/Chronos/apps/pon/data/pon.glb"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"\n[PON] Exporting to GLB...")
    mesh.export(output_path)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[PON] Saved: {output_path} ({size_mb:.1f} MB)")

    print("\n[SUCCESS] High-quality pon ready!")
    print("[NEXT] Open http://localhost:8000/viewer.html in OBS")

    return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
