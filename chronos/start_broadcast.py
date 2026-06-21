#!/usr/bin/env python3
"""
配信自動開始スクリプト

YouTube Live 作成 → OBS 設定 → 配信開始 → CHRONOS チャット監視
"""

import sys
import os
import subprocess
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from drivers.broadcast.youtube_auto import setup_youtube
from drivers.broadcast.obs_auto import setup_obs_for_broadcast


def check_requirements():
    """必要な環境チェック"""
    print("=" * 60)
    print("配信準備チェック")
    print("=" * 60)
    print()

    # OBS チェック
    print("✓ OBS をインストール済みか？")
    print("  https://obsproject.com/download")
    print()

    print("✓ OBS に obs-websocket をインストール済みか？")
    print("  OBS 内: ツール → スクリプト → Python インストール")
    print("  または: https://github.com/obsproject/obs-websocket")
    print()

    print("✓ Google Cloud Console でプロジェクト作成済みか？")
    print("  YouTube Data API を有効化")
    print("  OAuth 2.0 認証情報（Desktop アプリ）を作成")
    print("  youtube_credentials.json を プロジェクトフォルダに配置")
    print()

    print("=" * 60)
    print()

    response = input("上記すべて準備完了ですか？(y/n): ").strip().lower()
    return response == 'y'


def main():
    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "CHRONOS 配信自動開始" + " " * 23 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    if not check_requirements():
        print("[ERROR] 準備が完了していません")
        return False

    print("[配信] ステップ 1/3: YouTube Live 作成")
    print()

    broadcast_info = setup_youtube()
    if not broadcast_info:
        print("[ERROR] YouTube Live 作成失敗")
        return False

    print()
    print("[配信] ステップ 2/3: OBS 設定")
    print()

    ok = setup_obs_for_broadcast(
        broadcast_info['server'],
        broadcast_info['stream_key']
    )

    if not ok:
        print("[警告] OBS 設定失敗（手動で設定してください）")
        print(f"  サーバー: {broadcast_info['server']}")
        print(f"  キー: {broadcast_info['stream_key']}")

    print()
    print("[配信] ステップ 3/3: CHRONOS チャット監視開始")
    print()

    # CHRONOS を起動
    chronos_script = os.path.join(os.path.dirname(__file__), "main.py")
    print(f"[配信] CHRONOS 起動: {chronos_script}")
    print(f"[配信] チャット監視開始")
    print(f"[配信] 配信URL: {broadcast_info['url']}")
    print()

    # YouTube Live チャット監視を開始
    from drivers.youtube.chat import start_youtube_chat
    try:
        start_youtube_chat(
            video_id=broadcast_info['broadcast_id'],
            channel='pon'
        )
    except Exception as e:
        print(f"[ERROR] チャット監視開始失敗: {e}")
        return False

    print()
    print("=" * 60)
    print("✅ 配信中")
    print("=" * 60)
    print(f"配信URL: {broadcast_info['url']}")
    print("ponが自動で返答中...")
    print()

    # ずっと実行
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print()
        print("[配信] 停止します...")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
