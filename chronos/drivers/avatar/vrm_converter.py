"""
drivers/avatar/vrm_converter.py
--------------------------------
Blender ヘッドレスで GLB → VRM を全自動変換する。
VRM Addon for Blender が未インストールなら自動ダウンロード＆インストール。

パイプライン:
    model.glb
        ↓  Blender (headless) + VRM Addon
    pon.vrm  ← VSeeFace に読み込める形式
"""

import os
import glob
import subprocess
import tempfile
import json
from observation.logger import log

# CHRONOS が使う5表情（osc.py と一致させること）
EXPRESSIONS = [
    "expression_happy",
    "expression_sad",
    "expression_angry",
    "expression_surprised",
    "expression_neutral",
]

# VRM Addon for Blender の GitHub リリース URL
# https://github.com/saturday06/VRM-Addon-for-Blender
_VRM_ADDON_URL = (
    "https://github.com/saturday06/VRM-Addon-for-Blender"
    "/releases/latest/download/VRM_Addon_for_Blender-release.zip"
)
_VRM_ADDON_ZIP = os.path.join(tempfile.gettempdir(), "vrm_addon_for_blender.zip")


# =========================================================
# Blender 検索
# =========================================================

def find_blender() -> str | None:
    """Blender の実行ファイルパスを返す（見つからなければ None）"""
    # PATH から探す
    try:
        cmd = "where" if os.name == "nt" else "which"
        result = subprocess.run(
            [cmd, "blender"], capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip().splitlines()[0]
    except Exception:
        pass

    # Windows の標準インストール先
    for pattern in [
        r"C:\Program Files\Blender Foundation\Blender *\blender.exe",
        r"C:\Program Files (x86)\Blender Foundation\Blender *\blender.exe",
    ]:
        matches = glob.glob(pattern)
        if matches:
            return sorted(matches)[-1]   # 最新バージョンを優先

    return None


# =========================================================
# VRM Addon インストール
# =========================================================

def _download_vrm_addon() -> str:
    """VRM Addon ZIP をダウンロードしてパスを返す"""
    import urllib.request
    if not os.path.exists(_VRM_ADDON_ZIP):
        log("[VRM] VRM Addon をダウンロード中...")
        urllib.request.urlretrieve(_VRM_ADDON_URL, _VRM_ADDON_ZIP)
        log(f"[VRM] ダウンロード完了: {_VRM_ADDON_ZIP}")
    return _VRM_ADDON_ZIP


def _install_vrm_addon(blender_exe: str) -> bool:
    """Blender に VRM Addon をインストールする"""
    try:
        zip_path = _download_vrm_addon()
    except Exception as e:
        log(f"[VRM] Addon ダウンロード失敗: {e}")
        return False

    install_script = (
        "import bpy;"
        f"bpy.ops.preferences.addon_install(filepath=r'{zip_path}');"
        "bpy.ops.preferences.addon_enable(module='vrm');"
        "bpy.ops.wm.save_userpref();"
        "print('[VRM_INSTALL] 完了')"
    )
    result = subprocess.run(
        [blender_exe, "--background", "--python-expr", install_script],
        capture_output=True, text=True, timeout=120
    )
    if "[VRM_INSTALL] 完了" in result.stdout:
        log("[VRM] VRM Addon インストール完了")
        return True
    log(f"[VRM] Addon インストール失敗:\n{result.stdout[-500:]}")
    return False


# =========================================================
# メイン変換
# =========================================================

def glb_to_vrm(
    glb_path: str,
    vrm_path: str,
    expressions: list[str] | None = None,
) -> bool:
    """
    Blender ヘッドレスで GLB を VRM に変換する。

    - アーマチュアがなければ自動生成（標準ヒューマノイド骨格）
    - 表情シェイプキーを追加（expressions リスト）
    - VRM Addon がなければ自動インストール
    """
    if expressions is None:
        expressions = EXPRESSIONS

    blender_exe = find_blender()
    if not blender_exe:
        log("[VRM] Blender が見つかりません。インストールしてください。")
        log("[VRM] https://www.blender.org/download/")
        return False

    log(f"[VRM] Blender: {blender_exe}")

    # _blender_vrm.py のパス（このファイルと同じディレクトリ）
    script_path = os.path.join(os.path.dirname(__file__), "_blender_vrm.py")
    if not os.path.exists(script_path):
        log(f"[VRM] スクリプトが見つかりません: {script_path}")
        return False

    # 引数を JSON で渡す（パスにスペースや日本語があっても安全）
    args_json = json.dumps({
        "glb_path":    os.path.abspath(glb_path),
        "vrm_path":    os.path.abspath(vrm_path),
        "expressions": expressions,
    })

    cmd = [
        blender_exe,
        "--background",
        "--python", script_path,
        "--", args_json,
    ]

    log("[VRM] Blender で変換中...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if "[VRM_SUCCESS]" in result.stdout:
        log(f"[VRM] 変換完了 → {vrm_path}")
        return True

    # VRM Addon が未インストールの可能性
    if "addon" in result.stdout.lower() or "vrm" not in str(result.stdout).lower():
        log("[VRM] VRM Addon を自動インストールします...")
        if _install_vrm_addon(blender_exe):
            # 再実行
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if "[VRM_SUCCESS]" in result.stdout:
                log(f"[VRM] 変換完了 → {vrm_path}")
                return True

    log(f"[VRM] 変換失敗:\n{result.stdout[-800:]}")
    return False
