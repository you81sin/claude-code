# 歌の底 — セットアップ

pon に「本物の歌声」で歌わせるための手順。
**コード側（楽譜 → 歌声エンジン → 再生 の指揮系統）はもう入っている。**
あとは歌声合成エンジンを君のPCに入れて、場所を教えるだけ。

エンジンが無くても `/sing` は動く（喋り合成で「歌うように喋る」フォールバックになる）。

---

## いまの仕組み

```
apps/pon/songs/<曲>.json        ← 楽譜（メロディ＋歌詞・人が書ける簡易形式）
        │  libs/song.py
        ▼
  MusicXML へ変換
        │  drivers/audio/singing_engine.py
        ▼
  歌声エンジン（NEUTRINO 等） → output_song.wav
        │  drivers/audio/player.py
        ▼
       再生
```

確認:
```bash
python tools/test_singing.py     # 楽譜→MusicXML→エンジン選択 の検証（音は鳴らさない）
python main.py pon               # 起動後に  /songs  → /sing kaeru
```

---

## おすすめ：NEUTRINO（無料・日本語・Windows）

[NEUTRINO](https://n3utrino.work/) はAI歌声合成。楽譜(MusicXML)を渡すと歌ってくれる。

1. NEUTRINO 本体をダウンロードして解凍（例: `C:\NEUTRINO`）。
2. 同梱の歌声ライブラリ（例: `KIRITAN` など）を確認。
3. `.env` に設定:
   ```
   SINGING_ENGINE=neutrino
   NEUTRINO_DIR=C:\NEUTRINO
   NEUTRINO_MODEL=KIRITAN        # 使うライブラリ名
   ```
4. `python main.py pon` → `/sing kaeru`

> NEUTRINO はバージョンによって起動方法（`Run.bat` の引数）が違うことがある。
> うまく動かない場合は、自前の起動スクリプトを作って `NEUTRINO_RUN` に指定する手もある：
> ```
> NEUTRINO_RUN=C:\NEUTRINO\sing.bat     # 引数: <musicxml> <out_wav> <model> を受ける
> ```
> `sing.bat` の中で NEUTRINO のパイプライン（musicXMLtoLabel → NEUTRINO → NSF/WORLD）を
> 呼んで、最後に `<out_wav>` を書き出すようにする。

---

## 曲の作り方（楽譜フォーマット）

`apps/pon/songs/<名前>.json` を作るだけ。`apps/pon/songs/kaeru.json` が見本。

```json
{
  "title": "曲名",
  "tempo": 108,             // BPM
  "key": 0,                 // 調号（#の数。フラットは負。0=ハ長調）
  "beats_per_measure": 4,   // 拍子の分子
  "notes": [
    {"lyric": "か", "pitch": "C4", "beats": 1},   // 4分音符
    {"lyric": "え", "pitch": "D4", "beats": 0.5}, // 8分音符
    {"rest": true, "beats": 1}                     // 休符
  ]
}
```

- `pitch`: 音名 `C4` / `C#4` / `Db4`、または MIDI番号(数字, 60=中央C)
- `beats`: 4分音符=1。0.5=8分、2=2分、4=全音符
- `lyric`: その音で歌う「1音（ひらがな/カタカナ1文字が無難）」
- 1音が小節線をまたがないように分けて書く

将来：LLM に歌詞→簡易メロディを生成させて、この形式で吐かせることもできる
（pon が「オリジナル曲」を作って歌う、への入口）。
