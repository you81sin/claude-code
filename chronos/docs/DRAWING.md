# 絵を描く（お絵描き活動）

pon がAI画像生成で「絵を描く」活動。**追加インストール不要・無料で動く**
（既定で Pollinations.ai を使う。APIキー不要）。

## 使い方

```
python main.py pon
> /draw            ← pon が勝手にお題を決めて描く
> /draw ドラゴン    ← お題を指定して描く
```

コメントから拾うのも対応：「ねこ描いて」「ドラゴンの絵をかいて」等。

## 流れ（apps/pon/drawing.py）

```
お題を決める（指定 or ランダム）
   ↓
プロンプト生成（ポンコツらしい「クレヨン落書き風」に寄せる）
   ↓
画像生成  drivers/image/novelai.py（Pollinations 無料 → NovelAI → Segmind）
   ↓
保存  apps/pon/data/drawings/<時刻>.png
表示用  apps/pon/data/current_drawing.png  ← OBS はこの固定パスを表示すると常に最新
   ↓
感想を一言（LLMがあれば生成・無ければ定型）→ 既存の音声経路で喋る
```

## OBS で見せる

OBS に「画像ソース」を追加し、`apps/pon/data/current_drawing.png` を指定する。
`/draw` のたびにこのファイルが上書きされるので、配信画面に最新の絵が出る。

## 画質を上げたい場合（任意）

既定の無料エンジンで十分動くが、`.env` に以下があるとそちら優先：
- `NOVELAI_TOKEN`（NovelAI）
- `SEGMIND_API_KEY`（Segmind）

## メモ

- pon は IQ15〜30 のポンコツ設定なので、絵もわざと「下手かわいい落書き」方向にしている。
- 検証: `python tools/test_drawing.py`（画像生成はモック・ネット不要）
