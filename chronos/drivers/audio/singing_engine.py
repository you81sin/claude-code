"""
drivers/audio/singing_engine.py
--------------------------------
「歌う声」の底。歌声合成エンジンを差し替えられるようにする層。

設計:
  - 楽譜(libs.song.Song) を受け取り、wav を書き出す。
  - エンジンは環境変数 SINGING_ENGINE で選ぶ（neutrino / sbv2 / auto）。
  - 本物のエンジン（NEUTRINO）が無くても、喋り合成(SBV2)で「歌詞を歌うように喋る」
    フォールバックに落ちる＝ここが無くてもアプリは死なない。

エンジン:
  NeutrinoEngine … 本物の歌声合成。楽譜→MusicXML→NEUTRINO→wav。
                   要 NEUTRINO_DIR（君のPCにインストールしたNEUTRINOの場所）。
  Sbv2Engine     … フォールバック。歌詞を Style-Bert-VITS2 で「歌うっぽく喋る」。
                   メロディは乗らない（あくまで繋ぎ）。
"""

import os
import subprocess
from observation.logger import log


class SingingEngine:
    name = "base"

    def available(self) -> bool:
        raise NotImplementedError

    def synthesize(self, song, out_path: str, app_id: str = "pon") -> bool:
        """song を歌って out_path(wav) に書き出す。成功で True。"""
        raise NotImplementedError


# =========================================================
# NEUTRINO（本物の歌声合成・無料/日本語/Windows）
# =========================================================

class NeutrinoEngine(SingingEngine):
    """
    NEUTRINO 本体は別途インストールが必要（docs/SINGING_SETUP.md 参照）。
    NEUTRINO_DIR にインストール先、NEUTRINO_MODEL に声モデル名を設定する。

    パイプライン（NEUTRINOの標準構成・バージョン差は SINGING_SETUP.md で吸収）:
        MusicXML → musicXMLtoLabel → NEUTRINO → NSF/WORLD → wav
    実際の起動は環境依存が大きいので、ユーザの run ラッパー(NEUTRINO_RUN)を呼ぶ方式も用意。
    """
    name = "neutrino"

    def __init__(self):
        self.dir   = os.environ.get("NEUTRINO_DIR", "").strip()
        self.model = os.environ.get("NEUTRINO_MODEL", "").strip()
        self.run   = os.environ.get("NEUTRINO_RUN", "").strip()  # 任意: 自前ラッパー

    def available(self) -> bool:
        if self.run:
            return os.path.exists(self.run)
        return bool(self.dir) and os.path.isdir(self.dir)

    def synthesize(self, song, out_path: str, app_id: str = "pon") -> bool:
        if not self.available():
            log("[SING:neutrino] NEUTRINO_DIR 未設定 or 見つからない → フォールバックへ")
            return False

        # 1) 楽譜を MusicXML に書き出す
        work_dir = os.path.join("apps", app_id, "songs", ".work")
        os.makedirs(work_dir, exist_ok=True)
        xml_path = os.path.join(work_dir, "score.musicxml")
        try:
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(song.to_musicxml())
            log(f"[SING:neutrino] MusicXML 出力: {xml_path}")
        except Exception as e:
            log(f"[SING:neutrino] MusicXML 出力失敗: {e}")
            return False

        # 2) NEUTRINO 実行
        try:
            if self.run:
                # 自前ラッパー: 引数は (musicxml, out_wav, model)
                cmd = [self.run, xml_path, out_path, self.model or "default"]
            else:
                # NEUTRINO同梱の Run スクリプトを叩く想定（OS差を吸収）
                runner = "Run.bat" if os.name == "nt" else "Run.sh"
                cmd = [os.path.join(self.dir, runner), xml_path, out_path,
                       self.model or "default"]
            log(f"[SING:neutrino] 実行: {' '.join(cmd)}")
            res = subprocess.run(cmd, cwd=self.dir or None,
                                 capture_output=True, text=True, timeout=600)
            if res.returncode != 0:
                log(f"[SING:neutrino] 失敗(rc={res.returncode}): {res.stderr[:200]}")
                return False
            if not os.path.exists(out_path):
                log("[SING:neutrino] wav が生成されなかった")
                return False
            log(f"[SING:neutrino] 歌声生成 成功 → {out_path}")
            return True
        except FileNotFoundError as e:
            log(f"[SING:neutrino] 実行ファイルが見つからない: {e} → SINGING_SETUP.md を確認")
            return False
        except subprocess.TimeoutExpired:
            log("[SING:neutrino] タイムアウト（曲が長い/マシンが遅い）")
            return False
        except Exception as e:
            log(f"[SING:neutrino] 例外: {e}")
            return False


# =========================================================
# SBV2 フォールバック（歌詞を歌うっぽく喋る・繋ぎ）
# =========================================================

class Sbv2Engine(SingingEngine):
    name = "sbv2"

    def available(self) -> bool:
        return True  # サーバが無くても synthesize 内で graceful に失敗する

    def synthesize(self, song, out_path: str, app_id: str = "pon") -> bool:
        from drivers.audio.tts import synthesize_to_file
        lyrics = song.lyrics_text
        if not lyrics:
            return False
        log(f"[SING:sbv2] メロディ無し・歌詞を歌うように喋る（繋ぎ）: {lyrics[:20]}…")
        # humming モード（音程ゆらぎ大）で「歌ってる風」に喋らせる
        return synthesize_to_file(lyrics, out_path, mode="humming", app_id=app_id)


# =========================================================
# 選択・ディスパッチ
# =========================================================

_ENGINES = {
    "neutrino": NeutrinoEngine,
    "sbv2":     Sbv2Engine,
}


def get_engine() -> SingingEngine:
    """
    環境変数 SINGING_ENGINE で選ぶ。
      neutrino … 本物の歌声合成
      sbv2     … 喋り合成フォールバック
      auto(既定) … NEUTRINO が使えれば neutrino、ダメなら sbv2
    """
    choice = os.environ.get("SINGING_ENGINE", "auto").strip().lower()

    if choice in _ENGINES:
        return _ENGINES[choice]()

    # auto
    neu = NeutrinoEngine()
    if neu.available():
        log("[SING] エンジン自動選択: neutrino")
        return neu
    log("[SING] エンジン自動選択: sbv2（NEUTRINO未設定のため繋ぎ）")
    return Sbv2Engine()


def synthesize_song(song, out_path: str = "output_song.wav", app_id: str = "pon") -> tuple:
    """
    曲を歌って wav を書き出す。
    戻り値: (成功か, 使ったエンジン名)
    """
    engine = get_engine()
    ok = engine.synthesize(song, out_path, app_id=app_id)
    if not ok and engine.name != "sbv2":
        # 本物が失敗したら繋ぎに落とす
        log("[SING] 本物エンジン失敗 → sbv2 フォールバック")
        fb = Sbv2Engine()
        ok = fb.synthesize(song, out_path, app_id=app_id)
        return ok, fb.name
    return ok, engine.name
