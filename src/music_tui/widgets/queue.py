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
        self.playing: int | None = None

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(id="queue-body", markup=True)

    def on_mount(self) -> None:
        self._redraw()

    def watch_selected(self) -> None:
        self._redraw()

    # 菜单绘画
    def _redraw(self) -> None:
        body = self.query_one("#queue-body", Static)
        if not self._songs:
            body.update("[dim]队列为空[/]")
            return

        lines: list[str] = []

        # 选中不播放：反色
        # 选中播放：反色+蓝色
        # 非选中但播放：蓝色
        # 非选中不播放：默认白
        for i,song in enumerate(self._songs):
            dur = fmt_time(song.duration)
            
            if i == self.selected and i != self.playing:
                lines.append(f"[reverse] {song.label()} [/] [dim]{dur}[/]")
            elif i == self.selected and i == self.playing:
                lines.append(f"[reverse yellow] {song.label()} [/] [dim]{dur}[/]")
            elif i != self.selected and i == self.playing:
                lines.append(f"[yellow] {song.label()} [/] [dim]{dur}[/]")  
            else:
                lines.append(f"  {song.label()}  [dim]{dur}[/]")
        body.update("\n".join(lines))

    def set_songs(self, songs: list[Song]) -> None:
        self._songs = songs
        self.selected = 0
        self._redraw()

    # 光标移动逻辑
    def move(self, delta: int) -> None:
        temp = len(self._songs)
        if temp == 0:
            return 

        next_pos = (self.selected+delta) % temp
        self.selected = next_pos

    # 获取当前歌曲序列
    def current_position(self) -> int | None:
        if not self._songs:
            return None
        return self.selected

    # 播放歌曲高亮显示
    def set_playing(self, pos: int | None) -> None:
        if pos == self.playing:
            return
        else:
            self.playing = pos
            self._redraw()

