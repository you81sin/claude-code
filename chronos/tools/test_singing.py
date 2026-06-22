"""
tools/test_singing.py
----------------------
歌の底（楽譜フォーマット・MusicXML変換・エンジン選択）の検証。
音は鳴らさない。純Pythonで完結するロジックだけを確認する。

実行:
    python tools/test_singing.py
"""

import os
import sys
import xml.etree.ElementTree as ET

CHRONOS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CHRONOS_DIR)
os.chdir(CHRONOS_DIR)


def test_pitch():
    from libs.song import pitch_to_midi, midi_to_step_alter_octave
    assert pitch_to_midi("C4") == 60,  "C4 は MIDI 60"
    assert pitch_to_midi("A4") == 69,  "A4 は MIDI 69"
    assert pitch_to_midi("C#4") == 61, "C#4 は MIDI 61"
    assert pitch_to_midi("Db4") == 61, "Db4 も MIDI 61"
    assert pitch_to_midi(60) == 60,    "int はそのまま"
    assert midi_to_step_alter_octave(60) == ("C", 0, 4), "60→C4"
    assert midi_to_step_alter_octave(61) == ("C", 1, 4), "61→C#4"
    print("[OK] 音名⇄MIDI変換")


def test_load_and_validate():
    from libs.song import load_song, list_songs
    songs = list_songs("pon")
    assert "kaeru" in songs, f"kaeru が songs に無い: {songs}"
    song = load_song("kaeru")
    assert song.title == "かえるのうた"
    assert song.note_count == 29, f"音符数が想定外: {song.note_count}"
    assert song.lyrics_text.startswith("かえるのうたが"), song.lyrics_text
    print(f"[OK] 曲読み込み: 『{song.title}』 {song.note_count}音 / 歌詞={song.lyrics_text}")
    return song


def test_musicxml(song):
    xml = song.to_musicxml()
    # 整形式XMLとしてパースできるか（DOCTYPE行は外して検査）
    body = "\n".join(l for l in xml.splitlines() if not l.startswith("<!DOCTYPE"))
    root = ET.fromstring(body)
    assert root.tag == "score-partwise", root.tag
    notes = root.findall(".//note")
    assert len(notes) == len(song.notes), f"note数不一致 xml={len(notes)} song={len(song.notes)}"
    lyrics = root.findall(".//lyric/text")
    assert len(lyrics) == song.note_count, "lyric数が音符数と不一致"
    assert lyrics[0].text == "か", lyrics[0].text
    # テンポが入っているか
    assert root.find(".//sound[@tempo]") is not None, "tempo が無い"
    print(f"[OK] MusicXML出力: note={len(notes)} lyric={len(lyrics)} （NEUTRINOに渡せる形式）")


def test_engine_selection():
    import drivers.audio.singing_engine as se
    # SINGING_ENGINE を明示すればその通り選ぶ
    os.environ["SINGING_ENGINE"] = "sbv2"
    assert se.get_engine().name == "sbv2"
    os.environ["SINGING_ENGINE"] = "neutrino"
    assert se.get_engine().name == "neutrino"
    # auto かつ NEUTRINO 未設定 → sbv2 に落ちる
    os.environ["SINGING_ENGINE"] = "auto"
    os.environ.pop("NEUTRINO_DIR", None)
    os.environ.pop("NEUTRINO_RUN", None)
    assert se.get_engine().name == "sbv2", "auto時 NEUTRINO無→sbv2 のはず"
    print("[OK] エンジン選択（neutrino / sbv2 / auto フォールバック）")


def main():
    test_pitch()
    song = test_load_and_validate()
    test_musicxml(song)
    test_engine_selection()
    print("\n==============================")
    print(" SINGING TEST PASSED ✅")
    print("==============================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
