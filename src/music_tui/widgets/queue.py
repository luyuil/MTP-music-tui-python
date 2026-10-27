from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from music_tui.widgets.pane import Pane

DEMO_ROWS = [
    ("晴天", "周杰伦", "4:29"),
    ("以父之名", "周杰伦", "5:42"),
    ("七里香", "周杰伦", "4:59"),
    ("Creep", "Radiohead", "3:58"),
    ("Karma Police", "Radiohead", "4:21"),
    ("夜曲", "周杰伦", "3:46"),
    ("Bohemian Rhapsody", "Queen", "5:55"),
    ("海阔天空", "Beyond", "5:26"),
]


class QueuePane(Pane):
    selected = reactive(0)               # 假焦点行

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(id="queue-body", markup=True)

    def on_mount(self) -> None:
        self._redraw()

    def watch_selected(self) -> None:
        self._redraw()

    def move(self, delta: int) -> None:
        self.selected = max(0, min(len(DEMO_ROWS) - 1, self.selected + delta))

    def _redraw(self) -> None:
        lines: list[str] = []
        for i, (title, artist, dur) in enumerate(DEMO_ROWS):
            if i == self.selected:
                lines.append(f"[reverse] {title} — {artist} [/reverse] [dim]{dur}[/]")
            elif i == 0:
                lines.append(f"[b]▶ {title}[/] [dim]— {artist}[/]  [dim]{dur}[/]")
            else:
                lines.append(f"  {title} [dim]— {artist}[/]  [dim]{dur}[/]")
        self.query_one("#queue-body", Static).update("\n".join(lines))