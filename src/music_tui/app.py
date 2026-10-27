from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from music_tui.widgets.pane import Pane
from music_tui.widgets.queue import QueuePane
from music_tui.widgets.statusbar import ProgressBar, StatusBar, fmt_time

METADATA = """\
Title    晴天
Artist   周杰伦
Album    叶惠美
Year     2003
Genre    流行
Format   FLAC 44.1kHz / 16bit
"""


class MusicTui(App):
    TITLE = "music-tui"

    CSS = """
    Screen { background: $background; }

    #tabs { height: 1; background: $panel; padding: 0 1; }
    #tabbar { width: 1fr; }
    #hint { width: auto; }

    #body { height: 1fr; }
    #queue { width: 2fr; }
    #right { width: 1fr; }
    #cover { height: 2fr; }
    #metadata { height: 1fr; }

    #cover .pane-body { content-align: center middle; }
    #metadata .pane-body { content-align: left top; }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("q", "quit", "退出"),
        ("space", "toggle", "播放/暂停"),
        ("j", "row_down", "下移"),
        ("k", "row_up", "上移"),
    ]

    playing = True
    elapsed = 0.0
    DURATION = 269.0

    def compose(self) -> ComposeResult:
        with Horizontal(id="tabs"):
            yield Static("[b]playlist[/]   library   playing   lyrics", id="tabbar")
            yield Static("[dim]space 播放 · j/k 选择 · q 退出[/]", id="hint")
        with Horizontal(id="body"):
            yield QueuePane("queue", id="queue")
            with Vertical(id="right"):
                yield Pane("cover", "[dim]♪[/]\n\n[dim]no cover[/]", id="cover")
                yield Pane("metadata", METADATA, id="metadata")
        yield StatusBar()

    def on_mount(self) -> None:
        self.query_one(ProgressBar).duration = self.DURATION
        self.query_one("#total", Static).update(fmt_time(self.DURATION))
        self.set_interval(0.25, self._tick)      # 每 0.25 秒推进一次
        self.set_focus(self.query_one("#queue"))

    def _tick(self) -> None:
        if not self.playing:
            return
        self.elapsed = min(self.DURATION, self.elapsed + 0.25)
        self.query_one(ProgressBar).progress = self.elapsed
        self.query_one("#elapsed", Static).update(fmt_time(self.elapsed))

    def action_toggle(self) -> None:
        self.playing = not self.playing
        icon = "▶" if self.playing else "⏸"
        self.query_one("#info", Static).update(f"[dim]vol 80[/]  [b]{icon}[/]")

    def action_row_down(self) -> None:
        self.query_one(QueuePane).move(1)

    def action_row_up(self) -> None:
        self.query_one(QueuePane).move(-1)