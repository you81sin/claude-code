"""
YouTube Live 自動化

Google OAuth で認証 → ライブストリーム作成 → 配信開始
"""

import os
import json
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta


SCOPES = ['https://www.googleapis.com/auth/youtube']
CREDENTIALS_FILE = 'youtube_credentials.json'
TOKEN_FILE = 'youtube_token.pickle'


def get_authenticated_service():
    """Google OAuth で認証してサービスを取得"""
    creds = None

    # 保存済みトークンを使用
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # トークンが無効なら再認証
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # OAuth フロー開始
            if not os.path.exists(CREDENTIALS_FILE):
                print("[YOUTUBE] credentials.json が見つかりません")
                print("[YOUTUBE] Google Cloud Console から取得してください")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # トークン保存
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)


def create_live_broadcast(youtube, title: str, description: str = ""):
    """ライブ配信を作成"""
    try:
        # ブロードキャスト作成
        broadcast_body = {
            'snippet': {
                'title': title,
                'description': description,
                'scheduledStartTime': (
                    datetime.utcnow() + timedelta(minutes=1)
                ).isoformat() + 'Z'
            },
            'status': {
                'privacyStatus': 'public'
            }
        }

        broadcast_response = youtube.liveBroadcasts().insert(
            part='snippet,status',
            body=broadcast_body
        ).execute()

        broadcast_id = broadcast_response['id']
        print(f"[YOUTUBE] ブロードキャスト作成: {broadcast_id}")

        # ストリーム作成
        stream_body = {
            'snippet': {
                'title': f"{title} - Stream",
                'description': description
            },
            'cdn': {
                'ingestionType': 'rtmp',
                'resolution': '1080p',
                'frameRate': '30fps'
            }
        }

        stream_response = youtube.liveStreams().insert(
            part='snippet,cdn',
            body=stream_body
        ).execute()

        stream_id = stream_response['id']
        print(f"[YOUTUBE] ストリーム作成: {stream_id}")

        # ブロードキャストとストリームをバインド
        bind_body = {
            'streamId': stream_id
        }

        youtube.liveBroadcasts().bind(
            id=broadcast_id,
            part='id',
            body=bind_body
        ).execute()

        print(f"[YOUTUBE] バインド完了")

        # ストリームキーを取得
        stream_detail = youtube.liveStreams().list(
            part='cdn',
            id=stream_id
        ).execute()

        stream_key = stream_detail['items'][0]['cdn']['ingestionInfo']['streamName']
        server = 'rtmps://a.rtmp.youtube.com:443/live2'

        return {
            'broadcast_id': broadcast_id,
            'stream_id': stream_id,
            'stream_key': stream_key,
            'server': server,
            'url': f"https://www.youtube.com/watch?v={broadcast_id}"
        }

    except Exception as e:
        print(f"[YOUTUBE] エラー: {e}")
        return None


def start_live_broadcast(youtube, broadcast_id: str):
    """配信を開始"""
    try:
        transition_body = {
            'status': {
                'lifeCycleStatus': 'live'
            }
        }

        youtube.liveBroadcasts().transition(
            broadcastStatus='live',
            id=broadcast_id,
            part='status',
            body=transition_body
        ).execute()

        print(f"[YOUTUBE] 配信開始: {broadcast_id}")
        return True

    except Exception as e:
        print(f"[YOUTUBE] 開始エラー: {e}")
        return False


def setup_youtube():
    """YouTube Live セットアップメイン"""
    print("[YOUTUBE] セットアップ開始")

    youtube = get_authenticated_service()
    if not youtube:
        print("[YOUTUBE] 認証失敗")
        return None

    # ライブ配信作成
    broadcast_info = create_live_broadcast(
        youtube,
        title="pon - CHRONOS AI VTuber",
        description="AI VTuber pon が自動で配信中。チャットで話しかけてください！"
    )

    if not broadcast_info:
        print("[YOUTUBE] ライブ配信作成失敗")
        return None

    print()
    print("=" * 60)
    print("[YOUTUBE] ライブ配信準備完了")
    print(f"配信URL: {broadcast_info['url']}")
    print(f"ストリームキー: {broadcast_info['stream_key']}")
    print(f"サーバー: {broadcast_info['server']}")
    print("=" * 60)
    print()

    return broadcast_info


if __name__ == "__main__":
    setup_youtube()
