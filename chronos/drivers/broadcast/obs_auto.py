"""
OBS 自動制御（WebSocket）

obs-websocket プラグインが必要
https://github.com/obsproject/obs-websocket
"""

import json
import websocket
import time


class OBSController:
    def __init__(self, host='localhost', port=4455, password=''):
        self.ws_url = f"ws://{host}:{port}"
        self.password = password
        self.ws = None
        self.request_id = 0

    def connect(self):
        """OBS WebSocket に接続"""
        try:
            self.ws = websocket.create_connection(self.ws_url, timeout=5)
            print(f"[OBS] 接続成功: {self.ws_url}")
            return True
        except Exception as e:
            print(f"[OBS] 接続失敗: {e}")
            print("[OBS] OBS を起動して、obs-websocket を有効にしてください")
            return False

    def send_request(self, request_type: str, data: dict = None):
        """OBS にリクエストを送信"""
        self.request_id += 1
        payload = {
            'op': 6,
            'd': {
                'requestType': request_type,
                'requestId': str(self.request_id),
                'requestData': data or {}
            }
        }

        try:
            self.ws.send(json.dumps(payload))
            response = self.ws.recv()
            return json.loads(response)
        except Exception as e:
            print(f"[OBS] リクエストエラー: {e}")
            return None

    def get_scenes(self):
        """シーン一覧取得"""
        response = self.send_request('GetSceneList')
        if response:
            return response['d'].get('responseData', {}).get('scenes', [])
        return []

    def get_sources(self, scene_name: str):
        """シーンのソース一覧取得"""
        response = self.send_request('GetSceneItemList', {'sceneName': scene_name})
        if response:
            return response['d'].get('responseData', {}).get('sceneItems', [])
        return []

    def start_streaming(self, server: str, key: str):
        """配信開始"""
        response = self.send_request('SetStreamServiceSettings', {
            'streamServiceType': 'rtmp_custom',
            'streamServiceSettings': {
                'server': server,
                'key': key
            }
        })
        print(f"[OBS] ストリーム設定完了")

        response = self.send_request('StartStream')
        if response and response['d'].get('responseData', {}).get('outputActive'):
            print("[OBS] 配信開始")
            return True
        print("[OBS] 配信開始失敗")
        return False

    def stop_streaming(self):
        """配信停止"""
        response = self.send_request('StopStream')
        if response:
            print("[OBS] 配信停止")
            return True
        return False

    def close(self):
        """接続を閉じる"""
        if self.ws:
            self.ws.close()


def setup_obs_for_broadcast(stream_server: str, stream_key: str):
    """OBS を配信用に設定"""
    obs = OBSController()

    if not obs.connect():
        return False

    print("[OBS] シーン確認中...")
    scenes = obs.get_scenes()
    print(f"[OBS] シーン: {[s['sceneName'] for s in scenes]}")

    print(f"[OBS] ストリーム設定: {stream_server}")
    obs.start_streaming(stream_server, stream_key)

    time.sleep(2)
    obs.close()

    return True


if __name__ == "__main__":
    # テスト
    server = input("Stream server (e.g., rtmps://a.rtmp.youtube.com:443/live2): ")
    key = input("Stream key: ")

    setup_obs_for_broadcast(server, key)
