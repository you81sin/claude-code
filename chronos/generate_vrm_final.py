# -*- coding: utf-8 -*-
"""
Generate VRM with Blender (after manual addon enable)
"""

import subprocess
import os
import shutil

BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

script_content = r"""
import bpy
import sys

print("[SETUP] Clear scene")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

print("[LOAD] Import GLB")
glb_path = r'C:\Users\you81\デスクトップ\Chronos\apps\pon\data\pon_blender.glb'
bpy.ops.import_scene.gltf(filepath=glb_path)

print("[FIND] Get mesh object")
mesh_obj = None
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        mesh_obj = obj
        break

if not mesh_obj:
    print("[ERROR] Mesh not found!")
    sys.exit(1)

print(f"[MESH] Using: {mesh_obj.name}")
bpy.context.view_layer.objects.active = mesh_obj
mesh_obj.select_set(True)

print("[SHAPEKEY] Add expression shape keys")
mesh = mesh_obj.data

if mesh.shape_keys is None:
    print("[SHAPEKEY] Create Basis")
    mesh_obj.shape_key_add(name="Basis", from_mix=False)

expressions = [
    "expression_neutral",
    "expression_happy",
    "expression_sad",
    "expression_angry",
    "expression_surprised",
]

for expr in expressions:
    if expr not in mesh.shape_keys.key_blocks:
        mesh_obj.shape_key_add(name=expr, from_mix=False)
        print(f"[SHAPEKEY] + {expr}")
    else:
        print(f"[SHAPEKEY] - {expr} (exists)")

print("[EXPORT] VRM export")
vrm_path = r'C:\Users\you81\デスクトップ\Chronos\apps\pon\data\pon_final.vrm'

try:
    bpy.ops.export_scene.vrm(filepath=vrm_path)
    print(f"[SUCCESS] VRM exported: {vrm_path}")
except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)

print("[DONE]")
"""

def main():
    print("=" * 70)
    print("[Phase 2: VRM Generation]")
    print("=" * 70)

    if not os.path.exists(BLENDER):
        print(f"\nERROR: Blender not found")
        return False

    # Write script
    script_file = r"C:\temp\gen_vrm.py"
    os.makedirs(os.path.dirname(script_file), exist_ok=True)

    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)

    print(f"\nScript: {script_file}")
    print(f"Blender: {BLENDER}")
    print("\n[IMPORTANT] Make sure:")
    print("1. Blender VRM addon is ENABLED")
    print("2. Blender is completely closed")
    print("\nRunning Blender...")

    # Run Blender
    result = subprocess.run(
        [BLENDER, "-b", "-P", script_file],
        capture_output=False,
        text=True,
        timeout=180
    )

    if result.returncode != 0:
        print("\n[ERROR] Blender execution failed")
        return False

    # Check output
    vrm_file = r'C:\Users\you81\デスクトップ\Chronos\apps\pon\data\pon_final.vrm'

    if os.path.exists(vrm_file):
        size_mb = os.path.getsize(vrm_file) / (1024 * 1024)
        print(f"\n[OK] VRM created: {vrm_file} ({size_mb:.1f} MB)")

        # Copy to pon.vrm
        target = r'C:\Users\you81\デスクトップ\Chronos\apps\pon\data\pon.vrm'
        shutil.copy(vrm_file, target)
        print(f"[OK] Copied to: {target}")

        print("\n[NEXT] Load pon.vrm in VSeeFace:")
        print("1. Open VSeeFace")
        print("2. Click '+' button")
        print("3. Select: " + target)

        return True
    else:
        print(f"\n[ERROR] VRM not created")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
