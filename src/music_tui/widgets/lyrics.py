from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from music_tui.core.lyrics import LyricLine, index_at
from music_tui.widgets.pane import Pane

class LyricsPane(Pane):
    def __init__(self, title, body = "", **kwargs):
        self._lines: list[LyricLine] = []
        self._rows: list[Static] = []
        self._current: int = -1

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="lyrics-scroll")

    def set_lines(self, lines: list[LyricLine]) -> None:
        scroll = self.query_one("#lyrics-scroll", VerticalScroll)
        if not lines:
            scroll.mount(Static("[dim]暂无歌词[/]"))

    def set_position(self, position_ms: int) -> None:
        pass

    def on_resize(self) -> None:
        pass