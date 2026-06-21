"""
apps/pon/test_action.py
-----------------------
pon の行動判定システムのテスト。

実行: python -m pytest apps/pon/test_action.py
または: python apps/pon/test_action.py
"""

import sys
import os
import time

# モジュールパスを追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engine.state import get_state, update_state
from apps.pon.action import (
    decide_action,
    evaluate_difficulty,
    should_enter_serious_mode_declared,
    should_enter_serious_mode_instinct,
)


def test_serious_declare():
    """宣言型本気のテスト（難度0.85）"""
    print("\n" + "=" * 60)
    print("TEST: 宣言型本気（serious_declare）")
    print("=" * 60)

    # 状態をリセット
    update_state({
        "DEBUG_MODE": True,
        "DEBUG_difficulty": 0.85,
        "serious_mode_declared": False,
        "serious_cooldown_declared": 0.0,
        "last_serious_declared_time": 0.0,
    })

    # アクション決定（この中で本気判定も行われる）
    action = decide_action("テスト入力")
    print(f"[TEST] アクション決定: {action}")
    assert action == "serious_declare", f"serious_declare が返るべき、実際: {action}"

    print("[PASS] 宣言型本気テスト")


def test_serious_instinct():
    """本能型本気のテスト（難度0.99）"""
    print("\n" + "=" * 60)
    print("TEST: 本能型本気（serious_instinct）")
    print("=" * 60)

    # 状態をリセット
    update_state({
        "DEBUG_MODE": True,
        "DEBUG_difficulty": 0.99,
        "serious_mode_instinct": False,
        "serious_cooldown_instinct": 0.0,
        "last_serious_instinct_time": 0.0,
    })

    # アクション決定（この中で本気判定も行われる）
    action = decide_action("テスト入力")
    print(f"[TEST] アクション決定: {action}")
    assert action == "serious_instinct", f"serious_instinct が返るべき、実際: {action}"

    print("[PASS] 本能型本気テスト")


def test_silent():
    """沈黙のテスト（エネルギー枯渇）"""
    print("\n" + "=" * 60)
    print("TEST: 沈黙（silent）")
    print("=" * 60)

    # デバッグモード OFF + エネルギー枯渇
    update_state({"DEBUG_MODE": False, "energy": 0.05})

    # アクション決定
    action = decide_action("テスト入力")
    print(f"[TEST] アクション決定: {action}")
    assert action == "silent", f"silent が返るべき、実際: {action}"

    print("[PASS] 沈黙テスト")


def test_normal_respond():
    """通常返答のテスト"""
    print("\n" + "=" * 60)
    print("TEST: 通常返答（respond）")
    print("=" * 60)

    # デバッグモード OFF + 通常状態
    update_state({
        "DEBUG_MODE": False,
        "energy": 0.6,
        "mood": 0.2,
        "desire": {"feeling_lonely": 0.5},
    })

    # アクション決定
    action = decide_action("テスト入力")
    print(f"[TEST] アクション決定: {action}")
    assert action == "respond", f"respond が返るべき、実際: {action}"

    print("[PASS] 通常返答テスト")


def test_debug_mode():
    """デバッグモードのテスト"""
    print("\n" + "=" * 60)
    print("TEST: デバッグモード")
    print("=" * 60)

    # デバッグモード ON + 任意の困難度
    update_state({"DEBUG_MODE": True, "DEBUG_difficulty": 0.5})

    difficulty = evaluate_difficulty()
    print(f"[TEST] デバッグ困難度: {difficulty:.2f}")
    assert difficulty == 0.5, f"デバッグ困難度が適用されていない"

    print("[PASS] デバッグモードテスト")


def run_all_tests():
    """全テスト実行"""
    print("\n")
    print("=" * 60)
    print("pon 行動判定テスト実行".center(60))
    print("=" * 60)

    try:
        test_serious_declare()
        test_serious_instinct()
        test_silent()
        test_normal_respond()
        test_debug_mode()

        print("\n" + "=" * 60)
        print("[OK] すべてのテストに合格しました！")
        print("=" * 60 + "\n")
        return True

    except AssertionError as e:
        print(f"\n[FAIL] テスト失敗: {e}\n")
        return False

    except Exception as e:
        print(f"\n[ERROR] エラー: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
