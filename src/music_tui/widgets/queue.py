from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from music_tui.core.models import Song
from music_tui.widgets.pane import Pane
from music_tui.widgets.statusbar import fmt_time


class QueuePane(Pane):
    selected = reactive(0)               # 假焦点行

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._songs: list[Song] = []

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(id="queue-body", markup=True)

    def on_mount(self) -> None:
        self._redraw()

    def watch_selected(self) -> None:
        self._redraw()

    def _redraw(self) -> None:
        body = self.query_one("#queue-body", Static)
        if not self._songs:
            body.update("[dim]队列为空[/]")
            return

        lines: list[str] = []
        for i,song in enumerate(self._songs):
            dur = fmt_time(song.duration)
            if i == self.selected:
                lines.append(f"[reverse] {song.label()} [/reverse] [dim]{dur}[/]")
            else:
                lines.append(f"  {song.label()}  [dim]{dur}[/]")
        body.update("\n".join(lines))

    def set_songs(self, songs: list[Song]) -> None:
        self._songs = songs
        self.selected = 0
        self._redraw()

    def move(self, delta: int) -> None:
        self.selected = max(0, min(len(self._songs)-1, self.selected + delta))