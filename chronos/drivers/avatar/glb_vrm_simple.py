"""
GLB → VRM: GLB をそのまま VRM にコピー。
VSeeFace 1.13+ はネイティブ GLB サポート。
"""

import shutil
import os


def log(msg: str):
    """簡易ロガー"""
    print(msg)


def glb_to_vrm_simple(glb_path: str, vrm_path: str) -> bool:
    """
    GLB → VRM: ファイルをコピーするだけ。
    VSeeFace はGLBもVRMも同じ形式でサポート。
    """
    if not os.path.exists(glb_path):
        log(f"[GLB_VRM] GLB ファイルが見つかりません: {glb_path}")
        return False

    try:
        os.makedirs(os.path.dirname(vrm_path) or '.', exist_ok=True)
        shutil.copy2(glb_path, vrm_path)
        log(f"[GLB_VRM] VRM コピー完了 → {vrm_path}")
        return True
    except Exception as e:
        log(f"[GLB_VRM] エラー: {e}")
        return False


if __name__ == "__main__":
    import sys
    glb_path = "apps/pon/data/model.glb"
    vrm_path = "apps/pon/data/pon.vrm"
    ok = glb_to_vrm_simple(glb_path, vrm_path)
    sys.exit(0 if ok else 1)
