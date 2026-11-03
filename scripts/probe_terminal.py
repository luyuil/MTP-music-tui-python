"""检测当前终端支持哪种图片协议。

用法：在你打算运行 TUI 的那个终端里执行

    .venv/bin/python scripts/probe_terminal.py

它会向终端发送查询序列，读回终端的能力响应。
"""

import os
import sys

from textual_image._terminal import TerminalError, probe_terminal


def main() -> None:
    print("TERM             =", os.environ.get("TERM"))
    print("COLORTERM        =", os.environ.get("COLORTERM"))
    print("TERM_PROGRAM     =", os.environ.get("TERM_PROGRAM"))
    print("KITTY_WINDOW_ID  =", os.environ.get("KITTY_WINDOW_ID"))
    print("stdout 是终端吗  =", sys.stdout.isatty())
    print()

    try:
        caps = probe_terminal()
    except TerminalError as exc:
        print("探测失败：", exc)
        return

    print("单元格像素尺寸   =", caps.cell_size)
    print("Sixel 支持       =", caps.sixel)
    print("Kitty TGP 支持   =", caps.tgp)
    print()
    if caps.tgp:
        print("=> 推荐协议：Kitty TGP（最好）")
    elif caps.sixel:
        print("=> 推荐协议：Sixel")
    else:
        print("=> 没有图形协议，只能字符渲染（半块 / 盲文）")


if __name__ == "__main__":
    main()
