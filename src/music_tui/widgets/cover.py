from __future__ import annotations

from io import BytesIO

import PIL
from PIL import Image, ImageOps
from rich.style import Style
from rich.text import Text
from textual.widgets import Static

from music_tui.widgets.pane import Pane


class CoverPane(Pane):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cover: PIL.Image.Image | None = None  

    def set_cover(self, data: bytes | None) -> None:
        if data is None:
            self.cover = None
        else:
            self.cover = Image.open(BytesIO(data)).convert("RGB")
        self._redraw()

    def _redraw(self) -> None:
        body = self.query_one(".pane-body", Static)

        if self.cover is None:
            body.update("[dim]♪[/]\n\n[dim]no cover[/]")
            return

        width = self.size.width
        height = self.size.height

        if width == 0 or height == 0:
            return
        
        # ① 保持比例，缩到能放下的最大尺寸
        img = ImageOps.contain(self.cover, (width, height * 2), method=Image.Resampling.LANCZOS)

        # ② 造一块和显示区域一样大的黑底画布
        canvas = Image.new("RGB", (width, height * 2), (0, 0, 0))

        # ③ 把图贴到正中间
        canvas.paste(img, ((width - img.width) // 2, (height * 2 - img.height) // 2))
        
        text = Text()
        for y in range(height):
            for x in range(width):
                top = canvas.getpixel((x, y * 2))
                bottom = canvas.getpixel((x, y * 2 + 1))
                assert isinstance(top, tuple) and isinstance(bottom, tuple)
                text.append("▀",style=Style(
                    color=f"rgb({top[0]},{top[1]},{top[2]})",
                    bgcolor=f"rgb({bottom[0]},{bottom[1]},{bottom[2]})",),
                    )
            if y < height - 1:
                text.append("\n")

        body.update(text)

    def on_resize(self) -> None:
        self._redraw()
            