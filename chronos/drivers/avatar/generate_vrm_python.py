# -*- coding: utf-8 -*-
"""
Python で GLB から VRM を直接生成
Blender 依存なし
"""

import json
import struct
import os
import gzip
import base64


def read_glb(glb_path: str) -> tuple:
    """GLB ファイルを読む -> (json_data, binary_data)"""
    with open(glb_path, 'rb') as f:
        data = f.read()

    # GLB header check
    magic = data[0:4]
    if magic != b'glTF':
        raise ValueError("Not a GLB file")

    version = struct.unpack('<I', data[4:8])[0]
    length = struct.unpack('<I', data[8:12])[0]

    print(f"[GLB] Version: {version}, Length: {length}")

    # JSON chunk
    json_len = struct.unpack('<I', data[12:16])[0]
    json_type = data[16:20]
    json_data = json.loads(data[20:20+json_len])

    # Binary chunk
    bin_offset = 20 + json_len
    bin_len = struct.unpack('<I', data[bin_offset:bin_offset+4])[0]
    bin_type = data[bin_offset+4:bin_offset+8]
    binary_data = data[bin_offset+8:bin_offset+8+bin_len]

    return json_data, binary_data


def add_vrm_extension(gltf_json: dict) -> dict:
    """glTF JSON に VRM extension を追加"""

    if 'extensions' not in gltf_json:
        gltf_json['extensions'] = {}

    # VRM metadata
    vrm_meta = {
        "exporterVersion": "v0.0.1",
        "specVersion": "0.0.1",
        "meta": {
            "title": "pon",
            "version": "1.0",
            "author": "CHRONOS",
            "contactInformation": "",
            "reference": "",
            "texture": None,
            "type": "Avatar",
            "allowedUserName": "Everyone",
            "violentUssageName": "Disallow",
            "sexualUssageName": "Disallow",
            "commercialUssageName": "Disallow",
            "otherPermissionUrl": "",
            "licenseName": "CC0",
            "otherLicenseUrl": ""
        },
        "humanoid": {
            "humanBones": []
        },
        "firstPerson": {
            "firstPersonBoneOffset": {"x": 0, "y": 0, "z": 0},
            "firstPersonMeshAnnotations": [],
            "lookAtTypeName": "Bone",
            "lookAtHorizontalInner": {"curve": [], "xRange": 90, "yRange": 10},
            "lookAtHorizontalOuter": {"curve": [], "xRange": 90, "yRange": 10},
            "lookAtVerticalDown": {"curve": [], "xRange": 90, "yRange": 10},
            "lookAtVerticalUp": {"curve": [], "xRange": 90, "yRange": 10}
        },
        "blendShapeMaster": {
            "blendShapeGroups": [
                {
                    "isBinary": False,
                    "materialValues": [],
                    "name": "expression_neutral",
                    "presetName": "neutral",
                    "binds": []
                },
                {
                    "isBinary": False,
                    "materialValues": [],
                    "name": "expression_happy",
                    "presetName": "happy",
                    "binds": []
                },
                {
                    "isBinary": False,
                    "materialValues": [],
                    "name": "expression_sad",
                    "presetName": "sad",
                    "binds": []
                },
                {
                    "isBinary": False,
                    "materialValues": [],
                    "name": "expression_angry",
                    "presetName": "angry",
                    "binds": []
                },
                {
                    "isBinary": False,
                    "materialValues": [],
                    "name": "expression_surprised",
                    "presetName": "surprised",
                    "binds": []
                },
            ]
        },
        "secondaryAnimation": {
            "boneGroups": [],
            "colliderGroups": []
        }
    }

    gltf_json['extensions']['VRM'] = vrm_meta

    # Add to extensionsUsed
    if 'extensionsUsed' not in gltf_json:
        gltf_json['extensionsUsed'] = []
    if 'VRM' not in gltf_json['extensionsUsed']:
        gltf_json['extensionsUsed'].append('VRM')

    return gltf_json


def write_glb(json_data: dict, binary_data: bytes, output_path: str):
    """VRM (GLB with VRM extension) を書き込み"""

    # JSON を再シリアライズ
    json_bytes = json.dumps(json_data, ensure_ascii=False).encode('utf-8')

    # 4バイト境界にパディング
    while len(json_bytes) % 4 != 0:
        json_bytes += b' '

    print(f"[VRM] JSON size: {len(json_bytes)}")
    print(f"[VRM] Binary size: {len(binary_data)}")

    # GLB ヘッダー
    magic = b'glTF'
    version = struct.pack('<I', 2)
    file_length = struct.pack('<I', 28 + len(json_bytes) + 8 + len(binary_data))

    # JSON chunk
    json_chunk_len = struct.pack('<I', len(json_bytes))
    json_chunk_type = b'JSON'

    # Binary chunk
    bin_chunk_len = struct.pack('<I', len(binary_data))
    bin_chunk_type = b'BIN\0'

    # 組み立て
    glb = magic + version + file_length
    glb += json_chunk_len + json_chunk_type + json_bytes
    glb += bin_chunk_len + bin_chunk_type + binary_data

    # 保存
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(glb)

    size_mb = len(glb) / (1024 * 1024)
    print(f"[VRM] Saved: {output_path} ({size_mb:.1f} MB)")


def glb_to_vrm(glb_path: str, vrm_output_path: str) -> bool:
    """GLB -> VRM 変換"""
    try:
        print("[VRM] Converting GLB to VRM...")
        print(f"[VRM] Input: {glb_path}")
        print(f"[VRM] Output: {vrm_output_path}")

        # GLB 読込
        json_data, binary_data = read_glb(glb_path)

        # VRM extension 追加
        json_data = add_vrm_extension(json_data)

        # VRM 書込
        write_glb(json_data, binary_data, vrm_output_path)

        print("[VRM] [OK] Conversion complete")
        return True

    except Exception as e:
        print(f"[VRM] [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    glb_path = r"C:\Users\you81\デスクトップ\Chronos\apps\pon\data\pon.glb"
    vrm_path = r"C:\Users\you81\デスクトップ\Chronos\apps\pon\data\pon.vrm"

    print("=" * 60)
    print("[GLB to VRM Converter (Pure Python)]")
    print("=" * 60)

    if not os.path.exists(glb_path):
        print(f"[ERROR] GLB not found: {glb_path}")
        return False

    success = glb_to_vrm(glb_path, vrm_path)

    if success:
        print("\n[SUCCESS] VRM ready for VSeeFace")
        print(f"Load: {vrm_path}")
        return True
    else:
        print("\n[FAILED]")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
