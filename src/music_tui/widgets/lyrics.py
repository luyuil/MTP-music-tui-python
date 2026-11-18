from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from music_tui.core.lyrics import LyricLine, index_at
from music_tui.widgets.pane import Pane