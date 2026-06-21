# -*- coding: utf-8 -*-
"""
GLB -> VRM Proper Conversion
Add VRM metadata to GLB to make it VSeeFace compatible
"""

import json
import struct
import os


def create_vrm_metadata() -> dict:
    """Create VRM metadata JSON"""
    return {
        "exporterVersion": "0.0.1",
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
        "firstPerson": {},
        "blendShapeMaster": {
            "blendShapeGroups": [
                {
                    "name": "expression_neutral",
                    "presetName": "neutral",
                    "binds": [],
                    "materialValues": [],
                    "isBinary": False
                },
                {
                    "name": "expression_happy",
                    "presetName": "happy",
                    "binds": [],
                    "materialValues": [],
                    "isBinary": False
                },
                {
                    "name": "expression_sad",
                    "presetName": "sad",
                    "binds": [],
                    "materialValues": [],
                    "isBinary": False
                },
                {
                    "name": "expression_angry",
                    "presetName": "angry",
                    "binds": [],
                    "materialValues": [],
                    "isBinary": False
                },
                {
                    "name": "expression_surprised",
                    "presetName": "surprised",
                    "binds": [],
                    "materialValues": [],
                    "isBinary": False
                },
            ]
        },
        "secondaryAnimation": {}
    }


def glb_to_vrm_proper(glb_path: str, vrm_output_path: str) -> bool:
    """
    Convert GLB to VRM by adding metadata

    VRM = glTF2 + VRM extension metadata
    """
    try:
        print(f"[VRM] Loading GLB: {glb_path}")

        with open(glb_path, 'rb') as f:
            glb_data = f.read()

        if len(glb_data) < 20:
            print(f"[VRM] Invalid GLB file (too small)")
            return False

        # Verify GLB header (magic = "glTF")
        magic = glb_data[0:4].decode('ascii', errors='ignore')
        if magic != 'glTF':
            print(f"[VRM] Not a valid GLB file (magic={magic})")
            return False

        print(f"[VRM] GLB valid, size: {len(glb_data)} bytes")

        # Extract JSON chunk from GLB
        version = struct.unpack('<I', glb_data[4:8])[0]
        file_length = struct.unpack('<I', glb_data[8:12])[0]

        print(f"[VRM] GLB version: {version}, file_length: {file_length}")

        # Read first chunk (JSON)
        chunk_length = struct.unpack('<I', glb_data[12:16])[0]
        chunk_type = glb_data[16:20].decode('ascii')

        print(f"[VRM] First chunk: type={chunk_type}, length={chunk_length}")

        if chunk_type != 'JSON':
            print(f"[VRM] First chunk is not JSON")
            return False

        # Parse existing glTF JSON
        json_data_bytes = glb_data[20:20+chunk_length]
        gltf_json = json.loads(json_data_bytes.decode('utf-8'))

        print(f"[VRM] glTF JSON parsed")

        # Add VRM extension
        if 'extensions' not in gltf_json:
            gltf_json['extensions'] = {}

        vrm_metadata = create_vrm_metadata()
        gltf_json['extensions']['VRM'] = vrm_metadata

        if 'extensionsUsed' not in gltf_json:
            gltf_json['extensionsUsed'] = []
        if 'VRM' not in gltf_json['extensionsUsed']:
            gltf_json['extensionsUsed'].append('VRM')

        print(f"[VRM] VRM extension added to glTF")

        # Serialize back to JSON
        new_json_data = json.dumps(gltf_json, ensure_ascii=False).encode('utf-8')

        # Align to 4-byte boundary
        while len(new_json_data) % 4 != 0:
            new_json_data += b' '

        print(f"[VRM] New JSON size: {len(new_json_data)} bytes")

        # Reconstruct GLB
        # Header
        new_glb = b'glTF'  # magic
        new_glb += struct.pack('<I', version)  # version

        # Calculate new file length
        binary_chunk_offset = 20 + len(new_json_data) + 8  # JSON chunk header (8) + JSON data
        # Get binary chunk from original GLB
        binary_chunk_start = 20 + chunk_length + 8
        binary_chunk_data = glb_data[binary_chunk_start + 8:]  # Skip binary chunk header
        binary_chunk_length = len(binary_chunk_data) - 8 if binary_chunk_data else 0

        new_file_length = 12 + 8 + len(new_json_data) + 8 + len(binary_chunk_data)
        new_glb += struct.pack('<I', new_file_length)

        # JSON chunk
        new_glb += struct.pack('<I', len(new_json_data))
        new_glb += b'JSON'
        new_glb += new_json_data

        # Binary chunk
        if len(glb_data) > binary_chunk_start:
            binary_data = glb_data[binary_chunk_start:]
            new_glb += binary_data

        # Save VRM
        os.makedirs(os.path.dirname(vrm_output_path) or '.', exist_ok=True)
        with open(vrm_output_path, 'wb') as f:
            f.write(new_glb)

        size_mb = len(new_glb) / (1024 * 1024)
        print(f"[VRM] VRM saved: {vrm_output_path} ({size_mb:.1f} MB)")

        return True

    except Exception as e:
        print(f"[VRM] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Convert pon GLB to VRM"""

    glb_path = "apps/pon/data/pon_blender.glb"
    vrm_output = "apps/pon/data/pon.vrm"

    print("=" * 60)
    print("[GLB to VRM Converter]")
    print("=" * 60)

    if not os.path.exists(glb_path):
        print(f"\n[ERROR] GLB not found: {glb_path}")
        return False

    print(f"\nInput:  {glb_path}")
    print(f"Output: {vrm_output}")

    success = glb_to_vrm_proper(glb_path, vrm_output)

    if success:
        print("\n[OK] VRM conversion successful!")
        print(f"Load {vrm_output} in VSeeFace")
        return True
    else:
        print("\n[FAIL] VRM conversion failed")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
