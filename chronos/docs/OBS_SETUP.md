# OBS 設定手順（pon 配信用）

## 目標
OBS で pon 3D avatar を配信に表示する

## 方法 A: OBS ブラウザソース（推奨）

### 手順
1. **OBS を起動**
2. **シーン作成** → 新規シーン作成（例：「pon配信」）
3. **ソース追加** → 「ブラウザ」
4. **ブラウザ設定**:
   - URL: `http://localhost:8000/viewer.html`
   - 幅: 1280
   - 高さ: 720
   - 60 FPS
5. **OK** をクリック

### 確認
- pon の 3D avatar が OBS に表示される
- マウスで回転可能（ユーザー操作不要なら設定で無効化）

### 追加設定
- **背景削除**: VSeeFace とは異なり、Babylon.js はデフォルトで白背景
  - OBS で色度キー（Chroma Key）を使用して背景を削除
  - または Babylon.js viewer を修正して背景透明化

---

## 方法 B: VRM + VSeeFace（複雑）

### 前提条件
- Blender に VRM アドオンをインストール
- VSeeFace をインストール

### 手順
1. Blender VRM アドオンをインストール:
   https://github.com/saturday06/VRM-Addon-for-Blender/releases

2. Blender で pon.vrm を正規生成:
   ```bash
   python drivers/avatar/blender_vrm_generator.py
   ```

3. VSeeFace で pon.vrm を読み込む

4. OBS で VSeeFace をウィンドウキャプチャ

---

## Phase 2 推奨構成

| コンポーネント | 役割 |
|---|---|
| CHRONOS main.py | pon の自律応答エンジン（コンソール） |
| SBV2 Server | TTS 音声生成（port 5000） |
| Web Server | Babylon.js viewer（port 8000） |
| OBS | ブラウザソース で viewer.html をキャプチャ |
| Discord/YouTube | 配信先 |

---

## 完全な配信パイプライン

```
User Input (コンソール)
    ↓
CHRONOS (応答生成 + state更新)
    ↓
SBV2 (TTS 音声合成)
    ↓
viewer.html (OSC受信 → emotion反映)
    ↓
OBS ブラウザソース (表示)
    ↓
YouTube/Discord (配信)
```

---

## トラブルシューティング

### OBS でブラウザが真っ白
- ✓ localhost:8000 が実行中か確認
- ✓ ブラウザ幅・高さを調整
- ✓ キャッシュクリア: F5 リロード

### pon が表示されない
- ✓ `apps/pon/data/pon.glb` が存在するか確認
- ✓ Babylon.js エラーをコンソールで確認
- ✓ VRM ではなく GLB が読み込まれているか確認

### 音声が配信に乗らない
- ✓ SBV2 server が実行中か確認
- ✓ OBS 音声設定で SBV2 デバイスを選択
- ✓ または CABLE Virtual Audio を使用

---

## 開始

1. **CHRONOS を起動**:
   ```bash
   start_test_broadcast.bat
   ```

2. **OBS を起動** → ブラウザソース追加

3. **配信開始**
