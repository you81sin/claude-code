# drivers/avatar/ — アバター生成

このフォルダには見た目（3Dモデル）生成の試行錯誤が大量に残っている。
**実際に「核」から呼ばれているのは下の3本だけ**。残りは実験の記録（参考用・未使用）。

## ✅ 現役パイプライン（main.py / memory/identity.py が使う）

```
identity.json の appearance
   ↓  drivers/image/novelai.py        : テキスト → 参考イラスト(png)
   ↓  drivers/avatar/hunyuan3d.py     : 画像 or テキスト → 3Dモデル(glb)
   ↓  drivers/avatar/glb_vrm_simple.py: glb → vrm（VSeeFace で読める形式）
   → apps/pon/data/pon.vrm
```

- `hunyuan3d.py` … 画像→GLB / テキスト→GLB（Segmind API）
- `glb_vrm_simple.py` … GLB→VRM 変換
- （画像生成は1つ上の階層 `drivers/image/novelai.py`）

## 🧪 実験（現在は未使用・消さずに残してある）

`ai_image_generator` / `character_model_generator` / `comfyui_pon_generator` /
`desktpomate_generator` / `generate_vrm_python` / `glb_to_vrm_converter` /
`glb_to_vrm_proper` / `glb_vrm_proper` / `neural4d_pon_generator` /
`pon_high_quality_generator` / `pon_model_generator` / `simple_generator` /
`tripo_3d_generator` / `tripo_sr_pon_generator` / `vrm_converter` / `vrm_generator`

> これらは過去に試した別ルート（TripoSR / Neural4D / ComfyUI / Blender bpy 等）。
> Windows 絶対パス（`C:\...`）が埋まっているものもあり、そのままでは動かない。
> 「どれが正解か分からない」状態を避けるため、**現役は上の3本** と明記しておく。
> 将来 `_experiments/` へ物理的に隔離する案あり（要・本人確認）。
