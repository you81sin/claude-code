"""
tools/draw_demo.py
-------------------
ネット・Pillow なしで「お絵描きの見た目（線の出方・タッチ・描く順）」を確認する。

AI画像の代わりに、手作りの線画ビットマップを本物のパイプライン
（libs.sketch.bitmap_to_strokes → humanize → 固定ペン）に通し、
  - 静止画 SVG（最終的なタッチが分かる）
  - 1本ずつ描くアニメ HTML（線を一本ずつ＝挙動が分かる）
を書き出す。

実行: python tools/draw_demo.py [出力ディレクトリ]
"""

import os
import sys
import json
import math

CHRONOS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CHRONOS_DIR)

from libs.sketch import bitmap_to_strokes, humanize, build_payload, DEFAULT_PEN


# ---------- 手作り線画ビットマップ（ねこ顔）----------
def make_cat_bitmap(size=120):
    bm = [[0] * size for _ in range(size)]

    def put(x, y):
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < size and 0 <= yi < size:
            bm[yi][xi] = 1

    def circle(cx, cy, r, a0=0, a1=360):
        steps = max(24, int(r * 6))
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            put(cx + r * math.cos(a), cy + r * math.sin(a))

    def line(x0, y0, x1, y1):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / n
            put(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)

    cx, cy, R = size * 0.5, size * 0.52, size * 0.34
    circle(cx, cy, R)                       # 顔の輪郭
    # 耳（三角）
    line(cx - R * 0.7, cy - R * 0.72, cx - R * 0.35, cy - R * 1.15)
    line(cx - R * 0.35, cy - R * 1.15, cx - R * 0.05, cy - R * 0.78)
    line(cx + R * 0.7, cy - R * 0.72, cx + R * 0.35, cy - R * 1.15)
    line(cx + R * 0.35, cy - R * 1.15, cx + R * 0.05, cy - R * 0.78)
    # 目
    circle(cx - R * 0.38, cy - R * 0.1, R * 0.10)
    circle(cx + R * 0.38, cy - R * 0.1, R * 0.10)
    # 鼻
    line(cx, cy + R * 0.05, cx, cy + R * 0.18)
    # 口（への字スマイル）
    circle(cx, cy + R * 0.12, R * 0.22, a0=20, a1=160)
    # ヒゲ
    for dy in (-0.04, 0.06):
        line(cx + R * 0.18, cy + R * (0.1 + dy), cx + R * 0.85, cy + R * (0.02 + dy))
        line(cx - R * 0.18, cy + R * (0.1 + dy), cx - R * 0.85, cy + R * (0.02 + dy))
    return bm


# ---------- 静止画 SVG（最終的なタッチ）----------
def to_svg(payload, size=600, pad=60):
    pen = payload["pen"]
    sx = lambda x: pad + x * (size - 2 * pad)
    sy = lambda y: pad + y * (size - 2 * pad)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">',
        f'<rect width="{size}" height="{size}" fill="#fffdf5"/>',
        f'<text x="16" y="30" font-family="sans-serif" font-size="20" '
        f'fill="#888">🖍 {payload.get("theme","")}</text>',
    ]
    for s in payload["strokes"]:
        pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in s)
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="{pen["color"]}" '
            f'stroke-width="{pen["width"]}" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


# ---------- アニメ HTML（線を一本ずつ）----------
def to_html(payload):
    data = json.dumps(payload, ensure_ascii=False)
    return """<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">
<title>pon お絵描きデモ</title>
<style>html,body{margin:0;height:100%;background:#fdfdf8;overflow:hidden}
#wrap{width:100vw;height:100vh;display:flex;align-items:center;justify-content:center}
canvas{background:#fffdf5;box-shadow:0 2px 16px rgba(0,0,0,.08)}
#t{position:fixed;left:16px;top:12px;font:600 20px sans-serif;color:#666}
button{position:fixed;right:16px;top:12px;font-size:16px;padding:6px 12px}</style></head>
<body><div id="t"></div><button onclick="run()">もう一回</button>
<div id="wrap"><canvas id="c" width="700" height="700"></canvas></div>
<script>
const PAYLOAD = __DATA__;
const cv=document.getElementById('c'),ctx=cv.getContext('2d');
document.getElementById('t').textContent='🖍 '+(PAYLOAD.theme||'');
let anim=null;
function run(){
 if(anim)cancelAnimationFrame(anim);
 ctx.fillStyle='#fffdf5';ctx.fillRect(0,0,cv.width,cv.height);
 const pen=PAYLOAD.pen||{},color=pen.color||'#2b2b2b',width=pen.width||2.6,
       wobble=pen.wobble||0.6,speed=pen.speed||220;
 ctx.lineCap='round';ctx.lineJoin='round';ctx.strokeStyle=color;
 const W=cv.width,H=cv.height,PAD=60,SX=x=>PAD+x*(W-2*PAD),SY=y=>PAD+y*(H-2*PAD);
 const S=PAYLOAD.strokes||[];let si=0,pi=0,pause=0,last=performance.now();
 function step(now){
  const dt=Math.min(.05,(now-last)/1000);last=now;
  if(now<pause){anim=requestAnimationFrame(step);return;}
  let b=Math.max(1,Math.round(speed*dt*(0.7+Math.random()*0.6)));
  while(b-->0){
   if(si>=S.length)return;const s=S[si];
   if(s.length<2){si++;pi=0;continue;}
   if(pi===0){ctx.beginPath();ctx.lineWidth=width*0.6;
    ctx.moveTo(SX(s[0][0])+(Math.random()-.5)*wobble,SY(s[0][1])+(Math.random()-.5)*wobble);pi=1;}
   else{const p=s[pi];ctx.lineWidth=width+(Math.random()-.5)*wobble*0.5;
    ctx.lineTo(SX(p[0])+(Math.random()-.5)*wobble,SY(p[1])+(Math.random()-.5)*wobble);ctx.stroke();pi++;
    if(pi>=s.length){si++;pi=0;pause=now+(60+Math.random()*120)+(Math.random()<.12?400:0);break;}}
  }
  anim=requestAnimationFrame(step);
 }
 anim=requestAnimationFrame(step);
}
run();
</script></body></html>""".replace("__DATA__", data)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out_dir, exist_ok=True)

    bm = make_cat_bitmap(120)
    strokes = bitmap_to_strokes(bm, min_len=3)
    strokes = humanize(strokes, jitter=0.004, seed=7777)
    payload = build_payload(strokes, theme="ねこ（デモ）")

    pts = sum(len(s) for s in strokes)
    print(f"[DEMO] ストローク数: {len(strokes)}本 / 総点数: {pts} / ペン: {DEFAULT_PEN}")

    svg_path  = os.path.join(out_dir, "draw_demo.svg")
    html_path = os.path.join(out_dir, "draw_demo.html")
    json_path = os.path.join(out_dir, "draw_demo.json")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(to_svg(payload))
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(to_html(payload))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"[DEMO] 静止画: {svg_path}")
    print(f"[DEMO] アニメ: {html_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
