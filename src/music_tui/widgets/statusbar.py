from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static


def fmt_time(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


class ProgressBar(Static):
    """自己画的进度条：用 ● 表示游标，左右两边填充。"""

    progress = reactive(0.0)
    duration = reactive(0.0)

    DEFAULT_CSS = """
    ProgressBar { width: 1fr; height: 1; }
    """

    def watch_progress(self) -> None:
        self.refresh()                   # 值变了就重画

    def watch_duration(self) -> None:
        self.refresh()

    def render(self) -> Text:
        width = max(3, self.size.width)
        ratio = 0.0 if self.duration <= 0 else min(1.0, self.progress / self.duration)
        head = int(ratio * (width - 1))
        text = Text()
        text.append("─" * head, style="cyan")
        text.append("●", style="bold cyan")
        text.append("─" * (width - 1 - head), style="grey37")
        return text


class StatusBar(Horizontal):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $panel;
        padding: 0 1;
    }
    #elapsed { width: 6; }
    #total   { width: 6; text-align: right; padding: 0 1 0 0; }
    #info    { width: auto; }
    """

    def compose(self) -> ComposeResult:
        yield Static("00:00", id="elapsed")
        yield ProgressBar()
        yield Static("00:00", id="total")
        yield Static("[dim]vol 80[/]  [b]⏸[/]", id="info")