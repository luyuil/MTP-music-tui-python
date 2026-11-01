from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from music_tui.services.mpd import (
    ConnectionEvent,
    CoverEvent,
    MpdService,
    QueueEvent,
    Status,
    StatusEvent,
)
from music_tui.widgets.cover import CoverPane
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
            #queue { width: 1fr; 
                     border: round hotpink;
                   }
            #right { width: 1fr; }
            #cover { height: 2fr;
                     border: round hotpink; 
                   }
            #musializer { height: 1fr; 
                          border: round hotpink; 
                   }

            #cover .pane-body { content-align: center middle; }
            #musializer .pane-body { content-align: left top; }
          """
    BINDINGS: ClassVar[list[BindingType]] = [
        ("q", "quit", "退出"),
        ("space", "play_pause", "暂停"),
        ("down", "row_down", "下移"),
        ("up", "row_up", "上移"),
        ("enter", "play_selected", "播放选中"),
    ]

    #-----------生命周期-----------
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.svc: MpdService | None = None
        self._last: Status | None = None
        self._cover_uri: str | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="tabs"):
            yield Static("[b]playlist[/]   library   playing   lyrics", id="tabbar")
            yield Static("[dim]space 暂停 · ↑/↓ 选择 · enter 播放 · q 退出[/]", id="hint")
        with Horizontal(id="body"):
            yield QueuePane("queue", id="queue")
            with Vertical(id="right"):
                yield CoverPane("cover", id="cover")
                yield Pane("musializer", "[dim]—[/]", id="musializer")
        yield StatusBar()

    def on_mount(self) -> None:
        self.svc = MpdService()
        self.svc.start()
        self.set_focus(self.query_one("#queue"))
        self.set_interval(0.1, self._pump)
        
    def on_unmount(self) -> None:
        if self.svc is not None:
            self.svc.stop()

    #-----------链接桥-------------
    def _pump(self) -> None:
        if self.svc is None:
            return
        
        for ev in self.svc.drain():
            if isinstance(ev, StatusEvent):
                self._last = ev.status
                self._apply_status(ev.status)
                self._maybe_load_cover()
            elif isinstance(ev, QueueEvent):
                self.query_one(QueuePane).set_songs(ev.songs)
                self._maybe_load_cover()
            elif isinstance(ev, ConnectionEvent):
                pass
            elif isinstance(ev, CoverEvent):
                if ev.uri == self._cover_uri:
                    self.query_one(CoverPane).set_cover(ev.data)

        if self._last is not None:
            pos = self._last.position()
            self.query_one(ProgressBar).progress = pos
            self.query_one("#elapsed", Static).update(fmt_time(pos))

    def _apply_status(self, status:Status) -> None:
        bar = self.query_one(ProgressBar)
        bar.duration = status.duration
        self.query_one("#total", Static).update(fmt_time(status.duration))
        self.query_one("#elapsed", Static).update(fmt_time(status.position()))
        icon = "▶" if status.state == "play" else "⏸"
        self.query_one("#info", Static).update(f"vol {status.volume or 0}  [b]{icon}[/]")
        self.query_one(QueuePane).set_playing(status.song)

    def _maybe_load_cover(self) -> None:
        if self.svc is None or self._last is None:
            return
        
        uri = self.query_one(QueuePane).uri_at(self._last.song)

        if uri is None:
            if self._cover_uri is not None:
                self._cover_uri = None
                self.query_one(CoverPane).set_cover(None)
            return

        if uri == self._cover_uri:
            return

        self._cover_uri = uri
        self.svc.load_cover(uri)

    #-----------按键动作-----------
    # 空格暂停
    def action_play_pause(self) -> None:
        if self.svc is not None:
            self.svc.toggle()

    # 上下键选择
    def action_row_down(self) -> None:
        self.query_one(QueuePane).move(1)
           
    def action_row_up(self) -> None:
        self.query_one(QueuePane).move(-1)

    # Enter键播放
    def action_play_selected(self) -> None:
        if self.svc is None:
            return

        pane = self.query_one(QueuePane)
        pos = pane.current_position()
        if pos is None:
            return 
        self.svc.play(pos)