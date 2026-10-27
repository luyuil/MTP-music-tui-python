from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class Pane(Widget):
    can_focus = True                     # 让 Tab 能在面板间切焦点

    DEFAULT_CSS = """
    Pane {
        border: round $border;
        padding: 0 1;
    }
    Pane:focus { border: round $accent; }
    Pane > .pane-body {
        height: 1fr;
        width: 1fr;
    }
    """

    def __init__(self, title: str, body: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = title        # 边框左上角
        self._body = body

    def compose(self) -> ComposeResult:
        yield Static(self._body, classes="pane-body", markup=True)