from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

from music_tui.config import LRC_DIR

@dataclass(frozen=True)
class LyricLine:
    time_ms: int
    text: str

# 通过替换歌曲文件后缀为.lrc来查找对应的歌词文件
def lyrics_path(uri: str) -> Path:
    return LRC_DIR / Path(uri).with_suffix(".lrc")

# 解析函数
def parse_lrc(text: str) -> list[LyricLine]:
    offset = 0
    result = []

    for line in text.splitlines():
        # 判断空白行
        row = line.strip()
        if row == "":
            continue

        # 提取偏移时间
        m = re.match(r"\[offset:\s*([+-]?\d+)\s*\]",line)
        if m:
            offset = int(m.group(1))
            continue

        # 提取时间戳
        stamps = list(re.finditer(r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]",line))
        if not stamps:
            continue

        # 提取歌词,去空白
        text = line[stamps[-1].end():].strip()

        # 计算时间
        content = line[stamps[-1].end():].strip()
        for stamp in stamps:
            ms_str = stamp.group(3) or "0"
            ms = int(ms_str.ljust(3, "0"))
            minutes = int(stamp.group(1))
            seconds = int(stamp.group(2))           
            time_ms = minutes*60000 + seconds*1000 + ms - offset

            result.append(LyricLine(time_ms, content))

    # 排序
    result.sort(key=lambda item: item.time_ms)
    return result

# 根据时间找到当前行
def index_at(lines: list[LyricLine], position_ms: int) -> int:
    if not lines or position_ms < 0: return -1

    i = bisect_right(lines, position_ms, key=lambda l: l.time_ms) - 1
    if i < 0:return -1
    return i

# 解析lrc文件路径,判断并返回
def load_lyrics(uri: str) -> list[LyricLine] | None:
    lrc = lyrics_path(uri)
    if not lrc.exists(): return None

    try:
        content = lrc.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = lrc.read_text(encoding="gbk")
        except UnicodeDecodeError:
            content = lrc.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return parse_lrc(content)

