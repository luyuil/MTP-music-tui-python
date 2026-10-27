from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from music_tui.services.mpd import ConnectionEvent, MpdService, QueueEvent, Status, StatusEvent
from music_tui.widgets.pane import Pane
from music_tui.widgets.queue import QueuePane
from music_tui.widgets.statusbar import ProgressBar, StatusBar, fmt_time


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

    #-----------生命周期-----------
    def compose(self) -> ComposeResult:
        pass
    def on_mount(self) -> None:
        pass
    def on_unmount(self) -> None:
        pass

    #-----------链接桥-------------
    def _pump(self) -> None:
        pass
    def _apply_status(self, status:Status) -> None:
        pass

    #-----------按键动作-----------
    def action_toggle(self) -> None:
        pass
    def action_row_down(self) -> None:
        pass
    def action_row_up(self) -> None:
        pass