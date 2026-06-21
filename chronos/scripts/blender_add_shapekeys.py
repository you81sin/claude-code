"""
Blender Python Script
Mesh にシェイプキーを追加（expression_neutral/happy/sad/angry/surprised）

使用方法：
1. Blender で pon.vrm を開く
2. Scripting ワークスペースで本スクリプトを実行
3. シェイプキーが自動追加される
4. VRM として Export
"""

import bpy

def add_shape_keys():
    """メッシュにシェイプキーを追加"""

    # アクティブなメッシュオブジェクトを取得
    obj = bpy.context.active_object

    if obj is None or obj.type != 'MESH':
        print("[SHAPE_KEY] メッシュオブジェクトが選択されていません")
        return False

    mesh = obj.data

    print(f"[SHAPE_KEY] {obj.name} にシェイプキーを追加...")

    # Basis シェイプキーを作成
    if mesh.shape_keys is None:
        basis = obj.shape_key_add(name="Basis", from_mix=False)
        print("[SHAPE_KEY] Basis シェイプキーを作成")

    # 5 つの表情シェイプキーを追加
    expressions = [
        ("expression_neutral", "Neutral / Normal face"),
        ("expression_happy", "Happy / Smiling face"),
        ("expression_sad", "Sad / Sad face"),
        ("expression_angry", "Angry / Angry face"),
        ("expression_surprised", "Surprised / Surprised face"),
    ]

    for name, desc in expressions:
        try:
            # シェイプキーが既に存在するか確認
            if name not in mesh.shape_keys.key_blocks:
                sk = obj.shape_key_add(name=name, from_mix=False)
                sk.vertex_group = ""
                print(f"[SHAPE_KEY] ✓ {name} を追加")
            else:
                print(f"[SHAPE_KEY] ! {name} は既に存在")
        except Exception as e:
            print(f"[SHAPE_KEY] × {name} 追加失敗: {e}")

    print(f"[SHAPE_KEY] シェイプキー追加完了")
    print(f"[SHAPE_KEY] 次のステップ: File → Export as → VRM形式 で保存")

    return True


if __name__ == "__main__":
    add_shape_keys()
