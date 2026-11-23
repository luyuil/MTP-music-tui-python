from __future__ import annotations

from pathlib import Path

from music_tui.config import LRC_DIR
from music_tui.core.lyrics import (
    LyricLine,
    index_at,
    load_lyrics,
    lyrics_path,
    parse_lrc,
)


def test_parse_single_line() -> None:
    lines = parse_lrc("[00:01.00]hello")
    assert len(lines) == 1
    assert lines[0].time_ms == 1000
    assert lines[0].text == "hello"


def test_parse_multi_stamp() -> None:
    lines = parse_lrc("[00:01.00][00:05.00]副歌")
    assert [(l.time_ms, l.text) for l in lines] == [
        (1000, "副歌"),
        (5000, "副歌"),
    ]


def test_parse_ignores_metadata() -> None:
    text = "[ti:歌名]\n[ar:歌手]\n[al:专辑]\n[00:02.00]正文"
    assert len(parse_lrc(text)) == 1


def test_parse_ignores_blank_lines() -> None:
    text = "\n\n[00:01.00]a\n   \n[00:02.00]b\n"
    assert [l.text for l in parse_lrc(text)] == ["a", "b"]


def test_parse_ms_padding() -> None:
    text = "[00:01.5]a\n[00:02.50]b\n[00:03.500]c\n[00:04]d"
    assert [l.time_ms for l in parse_lrc(text)] == [1500, 2500, 3500, 4000]


def test_parse_cross_minute() -> None:
    assert parse_lrc("[01:05.25]x")[0].time_ms == 65250


def test_parse_sorts_output() -> None:
    text = "[00:05.00]b\n[00:01.00]a"
    assert [l.time_ms for l in parse_lrc(text)] == [1000, 5000]


def test_parse_empty_text() -> None:
    assert parse_lrc("") == []


def test_parse_skips_bad_lines() -> None:
    text = "随便一行\n[00:xx]坏行\n[00:01.00]好行"
    lines = parse_lrc(text)
    assert len(lines) == 1
    assert lines[0].text == "好行"


def test_parse_offset_positive() -> None:
    assert parse_lrc("[offset:+500]\n[00:10.00]x")[0].time_ms == 9500


def test_parse_offset_negative() -> None:
    assert parse_lrc("[offset:-500]\n[00:10.00]x")[0].time_ms == 10500


# ---------- index_at ----------

def test_index_at_boundaries() -> None:
    lines = [
        LyricLine(1000, "a"),
        LyricLine(3000, "b"),
        LyricLine(5000, "c"),
    ]
    assert index_at([], 1000) == -1
    assert index_at(lines, -1) == -1
    assert index_at(lines, 500) == -1
    assert index_at(lines, 1000) == 0
    assert index_at(lines, 2999) == 0
    assert index_at(lines, 3000) == 1
    assert index_at(lines, 9999) == 2


# ---------- lyrics_path ----------

def test_lyrics_path_flat() -> None:
    assert lyrics_path("a.mp3") == LRC_DIR / "a.lrc"


def test_lyrics_path_subdir() -> None:
    assert lyrics_path("专辑A/01.flac") == LRC_DIR / "专辑A" / "01.lrc"


# ---------- load_lyrics ----------

def test_load_lyrics_existing(tmp_path: Path, monkeypatch) -> None:
    lrc = tmp_path / "a.lrc"
    lrc.write_text("[00:01.00]你好\n", encoding="utf-8")
    monkeypatch.setattr("music_tui.core.lyrics.LRC_DIR", tmp_path)

    lines = load_lyrics("a.mp3")

    assert lines is not None
    assert lines[0].time_ms == 1000
    assert lines[0].text == "你好"


def test_load_lyrics_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("music_tui.core.lyrics.LRC_DIR", tmp_path)
    assert load_lyrics("nope.mp3") is None


def test_load_lyrics_gbk(tmp_path: Path, monkeypatch) -> None:
    lrc = tmp_path / "b.lrc"
    lrc.write_bytes("[00:01.00]你好\n".encode("gbk"))
    monkeypatch.setattr("music_tui.core.lyrics.LRC_DIR", tmp_path)

    lines = load_lyrics("b.mp3")

    assert lines is not None
    assert lines[0].text == "你好"