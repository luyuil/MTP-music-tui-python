from __future__ import annotations

from io import BytesIO

import PIL
from PIL import Image, ImageOps
from textual.widgets import Static

from music_tui.widgets.pane import Pane

BRAILLE_BITS = (
    (0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08),
    (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80),
)

# 计算灰度封面的平均阈值
def otsu_threshold(gray: Image.Image) -> int: 
    hist = gray.histogram()
    total = sum(hist)
    w_b = 0
    sum_b = 0

    max_v = 0
    max_t = 127

    if total == 0:
        return 128
    
    sum_all = sum(i*h for i, h in enumerate(hist))

    for t in range(256):
        w_b += hist[t]
        sum_b += t * hist[t]

        if w_b == 0:
            continue
        if w_b == total:
            break

        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / (total - w_b)
        v = w_b * (total - w_b) * (m_b - m_f)**2
        
        if v > max_v:
            max_v = v
            max_t = t

    return max_t+1

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

        # 获取正方形尺寸
        rows = min(height, width // 2)
        cols = rows * 2
        if rows == 0:
            return

        dots = rows * 4          # 点阵边长：宽高都是它

        gray = self.cover.convert("L")
        gray = ImageOps.autocontrast(gray)
        
        hist = gray.histogram()
        total = gray.width * gray.height
        mean = sum(i * n for i, n in enumerate(hist)) / total
        if mean < 128:
            gray = ImageOps.invert(gray)
            
        img = ImageOps.fit(gray, (dots, dots), method=Image.Resampling.LANCZOS)
        threshold = otsu_threshold(img)
        
        lines = []
        for y in range(rows):
            row = []
            for x in range(cols):
                code = 0
                for (dx, dy, bit) in BRAILLE_BITS:
                    if img.getpixel((x*2+dx, y*4+dy)) < threshold:
                        code |= bit
                row.append(chr(0x2800 + code))
            lines.append("".join(row))
        body.update("\n".join(lines))

    def on_resize(self) -> None:
        self._redraw()
            