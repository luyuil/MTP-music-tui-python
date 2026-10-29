# music-tui 代码导读

面向：刚学完 Python 语法、想读懂并改造这个项目的人。
读法：**不要从第 1 行读到最后一行**。先看第 0 节的三个模型，再按第 2 节的顺序读。

---

## 0. 先建立三个心智模型

### 模型 1：是框架调用你，不是你调用框架

`app.py` 里有一半方法，**你从来没有调用过**：

| 方法 | 什么时候被调用 | 谁调用 |
|---|---|---|
| `compose()` | 界面要挂载时 | Textual |
| `on_mount()` | 控件全部挂载完成 | Textual |
| `on_unmount()` | App 退出时 | Textual |
| `_pump()` | 每 0.1 秒 | Textual 的定时器（由 `set_interval` 注册） |
| `action_play_pause()` | 按下空格 | Textual（按 `BINDINGS` 查表） |
| `watch_selected()` | `selected` 的值变化时 | Textual 的 reactive 机制 |

这叫**回调（callback / hook）**。读 GUI 代码时不要问"哪里调用了 `on_mount`"，要问：

> **"谁会在什么时机调用它？"**

`__main__.py` 里只有一句 `MusicTui().run()`，剩下的全是 Textual 在合适的时机回调你的方法。

### 模型 2：跨文件调用 = 拿名字 → 拿对象 → 调方法

`app.py` 想用 `queue.py` 里的东西，要经过三步：

```
① 拿名字：  from music_tui.widgets.queue import QueuePane     ← 只是让 QueuePane 这个名字可用
② 拿对象：  yield QueuePane("queue", id="queue")              ← 执行 __init__，造出一个对象，挂到界面上
③ 调方法：  self.query_one(QueuePane).set_songs(ev.songs)      ← 把那个对象找回来，调它的方法
```

关键：**`QueuePane` 是"类"，不是"对象"**。类只是图纸，`yield` 那一步才造出房子。
第 ③ 步之所以能拿到"同一个对象"，是因为 Textual 帮你保存了控件树，`query_one` 是去树上找。

### 模型 3：数据是"事件"推过来的，不是"查询"来的

`_pump()` 每 0.1 秒做两件事：

1. `drain()` 把积压的事件取空，按类型更新界面；
2. 没有新事件时，用最后一份快照 `_last` 自己插值算进度。

所以界面上的数字**不是实时问 MPD 得到的**，而是"事件 + 本地推算"的组合。

---

## 1. 全局调用图

```
__main__.py
  └─ MusicTui().run()                         ← Textual 引擎接管
       ├─ __init__()                           → self.svc = None, self._last = None
       ├─ compose()                            → 造控件树（Pane / QueuePane / StatusBar）
       ├─ on_mount()                           → svc.start()；set_interval(0.1, _pump)
       │    └─ MpdService.start()              → 起两个后台线程（cmd / idle）
       │
       ├─ _pump()  每 0.1s  ──────────────┐
       │    ├─ svc.drain()  ← 取事件       │
       │    ├─ StatusEvent → _apply_status() → 改 4 个控件
       │    ├─ QueueEvent  → QueuePane.set_songs() → _redraw()
       │    └─ 无事件 → 用 _last.position() 推进度条
       │                                  │
       ├─ action_play_pause()  ← 空格按键  │
       │    └─ svc.toggle() → _cmd_q       │
       │                                   │
       └─ on_unmount() → svc.stop()        │
                                           ▼
                                    MPD (127.0.0.1:6600)
```

**两条独立的通道**：

- **命令出去**：`action_*` → `svc.toggle()` → 队列 → cmd 线程 → MPD
- **事件回来**：MPD → idle 线程 → 队列 → `_pump` → 界面

两条通道互不等待，所以 UI 永远不会被网络卡住。

---

## 2. app.py 逐段精讲

### 2.1 文件头（第 1–19 行）

```python
from __future__ import annotations
```

让类型注解"延迟求值"。有这个之后，`MpdService | None` 在 Python 3.9 也能写。
**必须在文件最前面**，否则 `SyntaxError`。

```python
from typing import ClassVar
from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
```

`import` 分三段（标准库 / 第三方 / 本项目），是 PEP 8 的顺序，也是 ruff 的 `I001` 在检查的东西。

```python
from music_tui.services.mpd import (
    ConnectionEvent, MpdService, QueueEvent, Status, StatusEvent,
)
```

这一行给了你 5 个**名字**：

| 名字 | 是什么 | 用来干嘛 |
|---|---|---|
| `MpdService` | 类 | `MpdService()` 造服务对象 |
| `Status` | 数据类 | 类型注解 `Status \| None` |
| `StatusEvent` | 数据类 | `isinstance` 判断 |
| `QueueEvent` | 数据类 | `isinstance` 判断 |
| `ConnectionEvent` | 数据类 | `isinstance` 判断 |

### 2.2 类属性（第 22–46 行）

```python
class MusicTui(App):
    TITLE = "music-tui"
    CSS = """..."""
    BINDINGS: ClassVar[list[BindingType]] = [...]
```

这三个是**类属性**（写在类里、方法外），Textual 在启动时会读取它们：

- `TITLE`：窗口标题；
- `CSS`：全局样式表，`#tabs` / `#queue` 这些就是后面控件的 `id`；
- `BINDINGS`：按键映射，每个元素是 `(按键, 动作名, 说明)`。

```python
("space", "play_pause", "播放/暂停"),
```

这句的意思是：**按下空格 → 去找 `action_play_pause` 方法并调用**。
规则固定：动作名 `xxx` → 方法名 `action_xxx`。`q` 对应的是 Textual 自带的 `action_quit`，所以你没写它也能退出。

### 2.3 `__init__`（第 49–52 行）

```python
def __init__(self, **kwargs) -> None:
    super().__init__(**kwargs)
    self.svc: MpdService | None = None
    self._last: Status | None = None
```

- `**kwargs`：把 Textual 传进来的参数（`id`、`classes` 等）原样收集成字典；
- `super().__init__(**kwargs)`：把字典**拆开**再传回父类 `App`。不写这句，Textual 的内部初始化就没了；
- `self.xxx`：**实例属性**，每个 App 对象自己有一份；
- `X | None`：表示"可能是 X，也可能是 None"。所以后面用之前要判断。

为什么 `svc` 先设成 `None`？因为 `__init__` 时还没开始连接 MPD，用一个明确的值表示"还没启动"。

### 2.4 `compose`（第 54–63 行）

```python
def compose(self) -> ComposeResult:
    with Horizontal(id="tabs"):
        yield Static("...", id="tabbar")
        yield Static("...", id="hint")
    with Horizontal(id="body"):
        yield QueuePane("queue", id="queue")
        with Vertical(id="right"):
            yield Pane("cover", "...", id="cover")
            yield Pane("musializer", "[dim]—[/]", id="musializer")
    yield StatusBar()
```

三个语法点：

1. **`yield`**：有 `yield` 的函数是**生成器**。`compose` 不是"返回控件"，而是"一个一个吐控件"，Textual 边收边挂载。
2. **`with`**：这里不是"打开文件"，而是 Textual 提供的**父子关系语法**。`with Horizontal(...)` 里面的 `yield`，都会成为这个 `Horizontal` 的子控件。
3. **`id=`**：给控件起 CSS id，全局唯一。`query_one("#tabs")` 就是按它找。

`QueuePane("queue", ...)` 的第一个参数 `"queue"` 是 `Pane` 的 `title`（边框左上角的文字），`id="queue"` 是 CSS 标识——**两者不是一回事**，一个给人看，一个给代码找。

### 2.5 `on_mount` / `on_unmount`（第 65–73 行）

```python
def on_mount(self) -> None:
    self.svc = MpdService()
    self.svc.start()
    self.set_focus(self.query_one("#queue"))
    self.set_interval(0.1, self._pump)
```

- `MpdService()`：只是造对象，**不连网络**；
- `.start()`：起两个后台线程，之后它自己连 MPD；
- `query_one("#queue")`：按 id 找控件；
- `set_focus(...)`：把键盘焦点给它；
- `set_interval(0.1, self._pump)`：注册定时器，每 0.1 秒调用一次 `_pump`。**注意传的是方法本身，不带括号**——带括号就变成"立刻调用一次，把返回值传进去"了。

```python
def on_unmount(self) -> None:
    if self.svc is not None:
        self.svc.stop()
```

退出时收尾：停线程、断连接。`if ... is not None` 是给类型的交代（也防启动失败时退出报错）。

### 2.6 `_pump`（第 76–92 行）—— 全文件的桥

```python
def _pump(self) -> None:
    if self.svc is None:
        return

    for ev in self.svc.drain():
```

`drain()` **非阻塞**：有事件就全部取走，没有就返回空列表。所以这里 `for` 就够了，不需要 `while`。

```python
        if isinstance(ev, StatusEvent):
            self._last = ev.status
            self._apply_status(ev.status)
```

`isinstance(x, T)` = "x 是不是 T 类型（或它的子类）"。
`ev.status` 是访问 dataclass 的**字段**，不是方法。

```python
        elif isinstance(ev, QueueEvent):
            self.query_one(QueuePane).set_songs(ev.songs)
```

这一行就是"跨文件调用"的典型：找到 `QueuePane` 对象 → 调它的 `set_songs`。

```python
    if self._last is not None:
        pos = self._last.position()
        self.query_one(ProgressBar).progress = pos
        self.query_one("#elapsed", Static).update(fmt_time(pos))
```

**在 `for` 外面**：无论这一轮有没有事件，每个 tick 都要推进进度条。
`position()` 是本地插值，不是问 MPD。

### 2.7 `_apply_status`（第 94–100 行）

纯翻译：一份 `Status` → 四个控件。

```python
bar.duration = status.duration          # 赋值给 reactive 属性 → 自动触发重画
self.query_one("#total", Static).update(fmt_time(status.duration))
```

- `bar.duration = ...`：`duration` 是 `reactive`，赋值会触发 `watch_duration` → `refresh()`；
- `.update(...)`：`Static` 的方法，改显示内容，支持 Rich 标记（`[b]`、`[dim]`）；
- `f"vol {status.volume or 0}"`：f-string 插值；`volume or 0` 表示"None 或 0 都显示 0"。

### 2.8 `action_*`（第 103–109 行）

```python
def action_play_pause(self) -> None:
    if self.svc is not None:
        self.svc.toggle()

def action_row_down(self) -> None:
    self.query_one(QueuePane).move(1)
```

按键 → 调 service 或调 widget。**它们都很短，因为真正的工作在别处**。这是好设计：App 只做"转发"。

---

## 3. queue.py 逐段

### 3.1 `selected = reactive(0)`（第 14 行）

```python
selected = reactive(0)
```

类属性，但它是**响应式**的：任何 `self.selected = 新值` 都会触发 `watch_selected()`。
命名规则固定：属性 `xxx` → 监听方法 `watch_xxx`。

这就是为什么 `move()` 只改 `self.selected`，界面就自动重画了。

### 3.2 `__init__`（第 16–18 行）

```python
def __init__(self, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    self._songs: list[Song] = []
```

- `*args`：收集所有位置参数成元组；
- `**kwargs`：收集所有关键字参数成字典；
- 原样转发给 `Pane.__init__(title, body="", **kwargs)`，这样 `QueuePane("queue", id="queue")` 才能工作。

`self._songs` 前的下划线表示"内部使用"，外部不要直接碰，用 `set_songs()`。

### 3.3 `compose` + 三级嵌套（第 20–22 行）

```python
def compose(self) -> ComposeResult:
    with VerticalScroll():
        yield Static(id="queue-body", markup=True)
```

`QueuePane` 本身是个 `Pane`（有边框），里面套一个滚动容器，容器里放一块文本。
所以控件树是：`QueuePane > VerticalScroll > Static#queue-body`。

`markup=True` 表示允许 `[b]`、`[reverse]` 这类 Rich 标记。

### 3.4 `_redraw`（第 30–43 行）

```python
body = self.query_one("#queue-body", Static)
if not self._songs:
    body.update("[dim]队列为空[/]")
    return
```

`query_one(选择器, 类型)` 的第二个参数是**类型提示**，帮编辑器和类型检查器知道返回的是 `Static`。

空列表要提前 `return`，否则会画出一片空白，看不出是"没数据"还是"坏了"。

```python
for i, song in enumerate(self._songs):
```

`enumerate` 同时给"下标"和"元素"，等价于：

```python
for i in range(len(self._songs)):
    song = self._songs[i]
```

```python
dur = fmt_time(song.duration)
```

**这是跨文件调函数**（不是方法）：`fmt_time` 定义在 `statusbar.py`，是模块级函数，`import` 之后直接 `fmt_time(x)` 就能调，不需要先造对象。

```python
lines.append(f"[reverse] {song.label()} [/reverse] [dim]{dur}[/]")
```

`song.label()` 是 `Song` 类的方法，返回 `"歌手 - 歌名"`。

### 3.5 `set_songs` 和 `move`（第 45–51 行）

```python
def set_songs(self, songs: list[Song]) -> None:
    self._songs = songs
    self.selected = 0
    self._redraw()
```

为什么先 `selected = 0` 再 `_redraw()`？队列换了，旧下标可能越界。
如果 `selected` 本来就是 0，赋值**不会**触发 `watch_selected`，所以还要显式调一次 `_redraw()`。

```python
self.selected = max(0, min(len(self._songs) - 1, self.selected + delta))
```

三层夹逼：先 `min` 封顶，再 `max` 兜底，保证下标永远落在 `[0, len-1]`。

---

## 4. statusbar.py / pane.py 速览

### `fmt_time`（statusbar.py:10–12）

```python
def fmt_time(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"
```

- `int()` 截断小数；
- `//` 整除得分钟，`%` 取余得秒；
- `:02d` = 至少两位、不足补 0。

### `ProgressBar`（statusbar.py:15–39）

```python
progress = reactive(0.0)
duration = reactive(0.0)

def watch_progress(self) -> None:
    self.refresh()
```

两个 reactive + 两个 watch，值一变就重画。`render()` 返回一个 Rich `Text` 对象。

### `StatusBar`（statusbar.py:42–58）

`Horizontal` 容器，里面四个控件：`#elapsed` / `ProgressBar` / `#total` / `#info`。
`app.py` 里 `query_one("#elapsed")` 能找到它，是因为 **id 在整个 App 范围内唯一**，不管它嵌套多深。

### `Pane`（pane.py:8–29）

通用面板：`__init__` 存标题和正文，`compose` 吐一个 `Static`。
`DEFAULT_CSS` 是**类级默认样式**，`Pane:focus` 表示获得焦点时换边框颜色。

---

## 5. 跨文件调用，到底怎么发生的

以 `QueueEvent` → 界面更新为例，完整链路：

```
mpd.py 的 idle 线程
  └─ _sync() 里 self._push(QueueEvent(songs))
        └─ 放进 self._events（queue.Queue）

app.py 的 UI 线程（每 0.1s）
  └─ _pump()
       └─ for ev in self.svc.drain():        ← 从队列取出 QueueEvent 对象
            └─ isinstance(ev, QueueEvent)
                 └─ self.query_one(QueuePane) ← 从控件树找回 QueuePane 对象
                      └─ .set_songs(ev.songs) ← 调用它的方法
                           └─ self._songs = songs
                           └─ self._redraw()  → body.update(...)  → 屏幕变了
```

**三个"对象"要分清**：

| 对象 | 在哪创建 | 怎么拿到 |
|---|---|---|
| `MpdService` 实例 | `app.py` 的 `on_mount` | `self.svc` |
| `QueuePane` 实例 | `app.py` 的 `compose`（`yield` 时） | `self.query_one(QueuePane)` |
| `QueueEvent` 实例 | `mpd.py` 的 idle 线程 | `drain()` 的返回值 |

### 亲手验证一次

在 `queue.py` 的 `set_songs` 里临时加一行：

```python
def set_songs(self, songs: list[Song]) -> None:
    print(f"[QueuePane] 收到 {len(songs)} 首")   # ← 临时
    ...
```

在真实终端里跑 `python -m music_tui`（不是 `run_test`），然后另开终端执行 `mpc clear`、`mpc add ...`。
你会看到每次队列变化都打印一次——**这就是跨文件调用真实发生的证据**。验证完删掉这行。

---

## 6. 语法速查表

| 写法 | 人话 |
|---|---|
| `from __future__ import annotations` | 类型注解延迟求值，必须放第一行 |
| `X \| None` | 可能是 X，也可能是 None |
| `list[Song]` | 元素是 Song 的列表 |
| `**kwargs` | 收集所有关键字参数；`f(**kwargs)` 是拆开传回去 |
| `*args` | 收集所有位置参数 |
| `@dataclass(frozen=True, slots=True)` | 自动生成 `__init__`；`frozen` 不可改；`slots` 省内存 |
| `@classmethod` / `cls` | 类方法，第一个参数是类本身（如 `Status.from_dict`） |
| `@staticmethod` | 静态方法，没有 self/cls |
| `yield` | 生成器：一个函数可以分多次"吐出"值 |
| `with ...:` | 上下文管理器；在 Textual 里表示父子关系 |
| `isinstance(x, T)` | x 是不是 T 类型 |
| `enumerate(x)` | 同时拿到下标和元素 |
| `a if cond else b` | 三元表达式，等价于 if/else 赋值 |
| `x or 0` | x 为假值（None/0/""）时取 0 |
| `f"{x:02d}"` | 至少两位、补零 |
| `f"{x:6.2f}"` | 宽 6、保留 2 位小数 |
| `reactive(0)` + `watch_xxx` | 属性变化自动触发回调 |
| `ClassVar[list[...]]` | 声明"这是类属性，不是实例属性" |
| `# type: ignore` | 让类型检查器闭嘴（尽量别用） |

---

## 7. 调用清单：你看到的每个调用是谁定义的

| 调用 | 定义在 | 作用 |
|---|---|---|
| `super().__init__(**kwargs)` | Textual `App` | 初始化框架内部状态 |
| `self.query_one(...)` | Textual `DOMNode` | 按 id 或类型在控件树里找控件 |
| `self.set_focus(...)` | Textual | 设置键盘焦点 |
| `self.set_interval(0.1, fn)` | Textual | 每 0.1 秒调用 fn |
| `self.svc.start()` | `mpd.py` | 起两个后台线程 |
| `self.svc.stop()` | `mpd.py` | 停线程、断连接 |
| `self.svc.drain()` | `mpd.py` | 非阻塞取空事件队列 |
| `self.svc.toggle()` | `mpd.py` | 往命令队列塞一条 pause |
| `status.position()` | `mpd.py`（`Status`） | 本地插值算当前秒数 |
| `Status.from_dict(...)` | `mpd.py` | 把 MPD 的字符串字典转成对象 |
| `fmt_time(x)` | `statusbar.py` | 秒 → `"mm:ss"` |
| `QueuePane(...)` | `queue.py` | 造队列面板 |
| `.set_songs(...)` | `queue.py` | 换数据 + 重画 |
| `.move(±1)` | `queue.py` | 移动选中行 |
| `Static.update(...)` | Textual | 改文本内容 |
| `ProgressBar.progress = x` | `statusbar.py` | 赋值触发重画 |
| `Song.from_mpd(d)` | `core/models.py` | MPD 字典 → Song 对象 |
| `song.label()` | `core/models.py` | `"歌手 - 歌名"` |

---

## 8. 照葫芦画瓢：四个改造模板

### 模板 A：加一个按键（例：`n` = 下一首）

1. `BINDINGS` 加一行：`("n", "next_track", "下一首")`
2. 类里加方法：

```python
def action_next_track(self) -> None:
    if self.svc is not None:
        self.svc.next()
```

就这两处。因为 `next()` 在 `mpd.py` 里已经有了。

### 模板 B：给 service 加一条命令

`mpd.py` 的"UI"区（`play`/`toggle` 那一堆）加：

```python
def previous(self) -> None:
    self.send("previous")
```

规则：**方法名不必等于 MPD 命令名，但 `send()` 的第一个参数必须是 MPD 认识的真命令**。
如果命令执行后需要刷新状态，`_cmd_loop` 的 `finally` 已经帮你推了。

### 模板 C：处理一种新事件

1. 在 `mpd.py` 定义事件类：

```python
@dataclass(frozen=True, slots=True)
class ErrorEvent:
    message: str
```

2. 在需要的地方 `self._push(ErrorEvent("..."))`
3. 在 `_pump` 加一个分支：

```python
elif isinstance(ev, ErrorEvent):
    self.query_one("#hint", Static).update(f"[red]{ev.message}[/]")
```

### 模板 D：加一个面板

1. 新文件 `widgets/xxx.py`，继承 `Pane`：

```python
class LyricsPane(Pane):
    def set_lyrics(self, text: str) -> None:
        self.query_one(".pane-body", Static).update(text)
```

注意 `Pane` 的 `.pane-body` 是 class，不是 id，所以用 `.pane-body`。

2. `app.py` 的 `compose` 里 `yield LyricsPane("lyrics", id="lyrics")`
3. 需要更新时：`self.query_one(LyricsPane).set_lyrics(...)`

---

## 9. 自测题（能答上来就算读懂了）

1. 按下空格，从按键到 MPD 收到命令，中间经过哪几个对象？
2. `set_songs` 里为什么要把 `self.selected` 重置成 0？
3. `_pump` 末尾那段为什么必须写在 `for` 循环外面？
4. 如果删掉 `watch_selected`，按 ↑/↓ 会怎样？
5. `query_one("#elapsed")` 找的是哪个类里的控件？为什么在 `app.py` 里能直接找到？
6. `QueuePane.__init__` 为什么需要 `*args, **kwargs`？
7. `self.set_interval(0.1, self._pump)` 如果把 `self._pump` 写成 `self._pump()` 会怎样？
8. `MpdService()` 和 `MpdService().start()` 分别发生了什么？

答案都能在上面的章节里找到。答不出来的，回到对应小节再读一遍。
