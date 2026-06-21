"""
GLB → VRM: 正しいバイナリ変換（メタデータ追加）
"""

import json
import struct
import os


def log(msg: str):
    print(msg)


def glb_to_vrm_proper(glb_path: str, vrm_path: str) -> bool:
    """
    GLB → VRM: VRM メタデータを正しく追加。
    GLB バイナリ構造を保ったまま拡張する。
    """
    if not os.path.exists(glb_path):
        log(f"[VRM] GLB が見つかりません: {glb_path}")
        return False

    try:
        with open(glb_path, 'rb') as f:
            glb_data = f.read()

        # === GLB ヘッダ解析 ===
        if len(glb_data) < 20 or glb_data[:4] != b'glTF':
            log("[VRM] 無効な GLB ファイル")
            return False

        version = struct.unpack('<I', glb_data[4:8])[0]
        total_length = struct.unpack('<I', glb_data[8:12])[0]

        if version != 2:
            log(f"[VRM] GLB バージョン {version} は非対応")
            return False

        # === JSON チャンク解析 ===
        chunk_length = struct.unpack('<I', glb_data[12:16])[0]
        chunk_type = glb_data[16:20]

        if chunk_type != b'JSON':
            log("[VRM] JSON チャンクが見つかりません")
            return False

        json_start = 20
        json_end = json_start + chunk_length

        # JSON データの実際の長さ（パディング前）
        json_raw = glb_data[json_start:json_end].rstrip(b' \x00')

        try:
            gltf = json.loads(json_raw)
        except Exception as e:
            log(f"[VRM] JSON パースエラー: {e}")
            return False

        # === VRM メタデータ追加 ===
        if 'extensions' not in gltf:
            gltf['extensions'] = {}

        gltf['extensions']['VRM'] = {
            "exporterVersion": "0.0.1",
            "specVersion": "0.0.3",
            "meta": {
                "title": "pon",
                "version": "1.0.0",
                "author": "CHRONOS",
                "contactInformation": "",
                "reference": "",
                "texture": -1,
                "allowedUserName": "Everyone",
                "violentUssageName": "Everyone",
                "sexualUssageName": "Everyone",
                "commercialUssageName": "Everyone",
                "otherPermissionUrl": "",
                "licenseName": "CC0",
                "otherLicenseUrl": ""
            },
            "humanoid": {
                "humanBones": []
            },
            "firstPerson": {
                "firstPersonBone": -1,
                "firstPersonBoneOffset": {"x": 0.0, "y": 0.0, "z": 0.0},
                "meshAnnotations": [],
                "lookAtTypeName": "Bone"
            },
            "blendShapeMaster": {
                "blendShapeGroups": []
            },
            "secondaryAnimation": {
                "boneGroups": [],
                "colliderGroups": []
            }
        }

        if 'extensionsUsed' not in gltf:
            gltf['extensionsUsed'] = []
        if 'VRM' not in gltf['extensionsUsed']:
            gltf['extensionsUsed'].append('VRM')

        # === 新しい JSON を生成 ===
        new_json = json.dumps(gltf, separators=(',', ':')).encode('utf-8')

        # パディング（4バイト境界）
        padding_size = (4 - (len(new_json) % 4)) % 4
        new_json_padded = new_json + b' ' * padding_size

        # === バイナリデータ（第2チャンク）を取得 ===
        bin_chunk_start = json_end
        bin_chunk_data = glb_data[bin_chunk_start:]

        # === 新しい GLB を構築 ===
        # ヘッダ
        new_glb = bytearray()
        new_glb.extend(b'glTF')
        new_glb.extend(struct.pack('<I', 2))  # version

        # JSON チャンク長（新）
        new_json_chunk_length = len(new_json_padded)

        # 総サイズ計算（ヘッダ + JSONチャンクヘッダ + JSONデータ + バイナリ）
        new_total_length = 12 + 8 + new_json_chunk_length + len(bin_chunk_data)
        new_glb.extend(struct.pack('<I', new_total_length))

        # JSON チャンク
        new_glb.extend(struct.pack('<I', new_json_chunk_length))
        new_glb.extend(b'JSON')
        new_glb.extend(new_json_padded)

        # バイナリデータ
        new_glb.extend(bin_chunk_data)

        # === VRM 保存 ===
        os.makedirs(os.path.dirname(vrm_path) or '.', exist_ok=True)
        with open(vrm_path, 'wb') as f:
            f.write(new_glb)

        log(f"[VRM] VRM 生成完了 → {vrm_path}")
        log(f"[VRM] サイズ: {len(new_glb)} bytes")
        return True

    except Exception as e:
        log(f"[VRM] エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    glb_path = "apps/pon/data/model.glb"
    vrm_path = "apps/pon/data/pon.vrm"
    ok = glb_to_vrm_proper(glb_path, vrm_path)
    sys.exit(0 if ok else 1)
