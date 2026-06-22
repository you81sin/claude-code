"""
libs/song.py
-------------
pon が「歌う」ための曲データ（楽譜）の最小フォーマットと変換。

歌声合成エンジン（NEUTRINO 等）は MusicXML を入力に取ることが多いので、
人が書きやすい簡易JSONフォーマット → MusicXML へ変換できるようにする。

簡易フォーマット（apps/pon/songs/*.json）:
{
  "title": "かえるのうた",
  "tempo": 100,            # BPM
  "key": 0,                # 調号（#の数。フラットは負。0=ハ長調）
  "beats_per_measure": 4,  # 拍子の分子（4/4 なら 4）
  "notes": [
    {"lyric": "か", "pitch": "C4", "beats": 1},
    {"lyric": "え", "pitch": "D4", "beats": 1},
    {"rest": true, "beats": 1}          # 休符
  ]
}

- pitch: 科学的音名 "C4"/"C#4"/"Db4" もしくは MIDI番号(int, 60=中央C)
- beats: 4分音符を 1 とした長さ（0.5=8分, 2=2分, 4=全音符）
- 1音が小節線をまたがない前提（またぐ長さは音を分けて書く）

この層は外部ライブラリ不要（純Python）。
"""

import json
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom


# =========================================================
# 音名 ⇄ MIDI / MusicXML
# =========================================================

_STEP_TO_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_SEMITONE_TO_SHARP = {  # MIDI%12 → (step, alter)
    0: ("C", 0), 1: ("C", 1), 2: ("D", 0), 3: ("D", 1), 4: ("E", 0),
    5: ("F", 0), 6: ("F", 1), 7: ("G", 0), 8: ("G", 1), 9: ("A", 0),
    10: ("A", 1), 11: ("B", 0),
}


def pitch_to_midi(pitch) -> int:
    """音名 "C4"/"C#4"/"Db4" または int → MIDI番号(int)。中央C(C4)=60。"""
    if isinstance(pitch, (int, float)):
        return int(pitch)
    s = str(pitch).strip()
    if not s:
        raise ValueError("pitch が空")
    step = s[0].upper()
    if step not in _STEP_TO_SEMITONE:
        raise ValueError(f"不正な音名: {pitch}")
    semitone = _STEP_TO_SEMITONE[step]
    i = 1
    while i < len(s) and s[i] in "#♯b♭":
        if s[i] in "#♯":
            semitone += 1
        else:
            semitone -= 1
        i += 1
    octave_str = s[i:]
    if not octave_str.lstrip("-").isdigit():
        raise ValueError(f"オクターブが読めない: {pitch}")
    octave = int(octave_str)
    return (octave + 1) * 12 + semitone


def midi_to_step_alter_octave(midi: int):
    """MIDI番号 → (step, alter, octave)。MusicXML 用。"""
    octave = midi // 12 - 1
    step, alter = _SEMITONE_TO_SHARP[midi % 12]
    return step, alter, octave


# 4分音符=1拍 を基準にした音価 → MusicXML の type 名（best-effort）
_BEATS_TO_TYPE = {
    4.0: "whole", 2.0: "half", 1.0: "quarter",
    0.5: "eighth", 0.25: "16th", 0.125: "32nd",
    3.0: "half", 1.5: "quarter", 0.75: "eighth",  # 付点系は近い値で代用
}


def _beats_to_type(beats: float) -> str:
    return _BEATS_TO_TYPE.get(round(beats, 3), "quarter")


# =========================================================
# Song モデル
# =========================================================

class Song:
    def __init__(self, data: dict):
        self.title             = data.get("title", "無題")
        self.tempo             = int(data.get("tempo", 100))
        self.key               = int(data.get("key", 0))
        self.beats_per_measure = int(data.get("beats_per_measure", 4))
        self.notes             = list(data.get("notes", []))
        self.validate()

    def validate(self) -> None:
        if not self.notes:
            raise ValueError(f"曲『{self.title}』に音符が無い")
        for i, n in enumerate(self.notes):
            beats = n.get("beats")
            if not isinstance(beats, (int, float)) or beats <= 0:
                raise ValueError(f"音符{i}: beats が不正 ({beats})")
            if not n.get("rest"):
                if "pitch" not in n:
                    raise ValueError(f"音符{i}: pitch が無い（休符なら rest:true）")
                pitch_to_midi(n["pitch"])  # 読めなければ例外
                if not str(n.get("lyric", "")).strip():
                    raise ValueError(f"音符{i}: lyric（歌詞の音）が無い")

    @property
    def lyrics_text(self) -> str:
        """歌詞だけを連結（フォールバック＝喋り合成用）。"""
        return "".join(str(n.get("lyric", "")) for n in self.notes if not n.get("rest"))

    @property
    def note_count(self) -> int:
        return sum(1 for n in self.notes if not n.get("rest"))

    # -----------------------------------------------------
    # MusicXML 出力（NEUTRINO 等の歌声合成エンジン向け）
    # -----------------------------------------------------
    def to_musicxml(self) -> str:
        divisions = 4  # 4分音符 = 4（→16分音符=1）
        bpm       = self.beats_per_measure

        root = ET.Element("score-partwise", version="3.1")
        part_list = ET.SubElement(root, "part-list")
        score_part = ET.SubElement(part_list, "score-part", id="P1")
        ET.SubElement(score_part, "part-name").text = self.title
        part = ET.SubElement(root, "part", id="P1")

        measure_no = 1
        measure = self._new_measure(part, measure_no, divisions, first=True)
        beats_in_measure = 0.0

        for n in self.notes:
            beats = float(n["beats"])
            # 小節が一杯になったら次の小節へ
            if beats_in_measure >= bpm - 1e-6:
                measure_no += 1
                measure = self._new_measure(part, measure_no, divisions)
                beats_in_measure = 0.0

            note_el = ET.SubElement(measure, "note")
            if n.get("rest"):
                ET.SubElement(note_el, "rest")
            else:
                midi = pitch_to_midi(n["pitch"])
                step, alter, octave = midi_to_step_alter_octave(midi)
                pitch_el = ET.SubElement(note_el, "pitch")
                ET.SubElement(pitch_el, "step").text = step
                if alter:
                    ET.SubElement(pitch_el, "alter").text = str(alter)
                ET.SubElement(pitch_el, "octave").text = str(octave)

            ET.SubElement(note_el, "duration").text = str(int(round(beats * divisions)))
            ET.SubElement(note_el, "voice").text = "1"
            ET.SubElement(note_el, "type").text = _beats_to_type(beats)
            if not n.get("rest"):
                lyric_el = ET.SubElement(note_el, "lyric")
                ET.SubElement(lyric_el, "syllabic").text = "single"
                ET.SubElement(lyric_el, "text").text = str(n.get("lyric", ""))

            beats_in_measure += beats

        rough = ET.tostring(root, encoding="unicode")
        pretty = minidom.parseString(rough).toprettyxml(indent="  ")
        # DOCTYPE を足す（MusicXML として素直に読めるように）
        lines = pretty.split("\n", 1)
        doctype = ('<!DOCTYPE score-partwise PUBLIC '
                   '"-//Recordare//DTD MusicXML 3.1 Partwise//EN" '
                   '"http://www.musicxml.org/dtds/partwise.dtd">')
        return lines[0] + "\n" + doctype + "\n" + lines[1]

    def _new_measure(self, part, number, divisions, first=False):
        measure = ET.SubElement(part, "measure", number=str(number))
        if first:
            attr = ET.SubElement(measure, "attributes")
            ET.SubElement(attr, "divisions").text = str(divisions)
            key = ET.SubElement(attr, "key")
            ET.SubElement(key, "fifths").text = str(self.key)
            time = ET.SubElement(attr, "time")
            ET.SubElement(time, "beats").text = str(self.beats_per_measure)
            ET.SubElement(time, "beat-type").text = "4"
            clef = ET.SubElement(attr, "clef")
            ET.SubElement(clef, "sign").text = "G"
            ET.SubElement(clef, "line").text = "2"
            direction = ET.SubElement(measure, "direction", placement="above")
            dtype = ET.SubElement(direction, "direction-type")
            metro = ET.SubElement(dtype, "metronome")
            ET.SubElement(metro, "beat-unit").text = "quarter"
            ET.SubElement(metro, "per-minute").text = str(self.tempo)
            ET.SubElement(direction, "sound", tempo=str(self.tempo))
        return measure


# =========================================================
# 読み込み
# =========================================================

def _songs_dir(app_id: str = "pon") -> str:
    return os.path.join("apps", app_id, "songs")


def load_song(name: str, app_id: str = "pon") -> Song:
    """apps/<app_id>/songs/<name>.json を読んで Song を返す。"""
    name = name.strip()
    if not name.endswith(".json"):
        name += ".json"
    path = os.path.join(_songs_dir(app_id), name)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Song(data)


def list_songs(app_id: str = "pon") -> list:
    """登録済みの曲名一覧（拡張子なし）。"""
    d = _songs_dir(app_id)
    if not os.path.isdir(d):
        return []
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))
