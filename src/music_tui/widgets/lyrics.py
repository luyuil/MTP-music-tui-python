from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from music_tui.core.lyrics import LyricLine, index_at
from music_tui.widgets.pane import Pane


class LyricsPane(Pane):
    # 初始化
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._lines: list[LyricLine] = []
        self._rows: list[Static] = []
        self._current: int = -1
        self._pending_scroll: bool = False

    # 定义挂载界面的组件
    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="lyrics-scroll")

    # 接收新数据，清空旧画面，渲染新画面
    def set_lines(self, lines: list[LyricLine]) -> None:
        scroll = self.query_one("#lyrics-scroll", VerticalScroll)
        scroll.remove_children()

        self._lines = lines
        self._rows = []
        self._current = -1
        self._pending_scroll = False

        if not lines:
            scroll.mount(Static("暂无歌词", classes="lyric"))
            return

        rows = [
            Static(line.text or "♪", classes="lyric", markup=False)
            for line in lines
        ]
        scroll.mount_all(rows)
        self._rows = rows

    # 计算目标行位置，并高亮
    def set_position(self, position_ms: int) -> None:
        idx = index_at(self._lines, position_ms)

        if idx != self._current:
            if 0 <= self._current < len(self._rows):
                self._rows[self._current].set_class(False, "current")

            self._current = idx

            if idx >= 0:
                self._rows[idx].set_class(True, "current")

            self._pending_scroll = idx >= 0

        if self._pending_scroll:
            self._try_scroll()

    # 布局完成后滚动到当前行
    def _try_scroll(self) -> None:
        if not (0 <= self._current < len(self._rows)):
            self._pending_scroll = False
            return

        scroll = self.query_one("#lyrics-scroll", VerticalScroll)

        # 布局还没算完：内容比视口高，但暂时不能滚
        if scroll.max_scroll_y <= 0:
            if len(self._rows) <= scroll.size.height:
                self._pending_scroll = False
            return

        # 用控件定位，自动处理长歌词换行后的真实高度
        scroll.scroll_to_widget(
            self._rows[self._current],
            animate=False,
            center=True,
        )
        self._pending_scroll = False

    # 窗口尺寸变化后重新滚动到当前行
    def on_resize(self) -> None:
        self._pending_scroll = True
        self._try_scroll()