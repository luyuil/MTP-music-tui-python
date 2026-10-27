# MPD 服务层：两条连接，线程跑，UI只通过事件队列读状态。
from __future__ import annotations

import logging
import queue
import socket
import threading
import time
from dataclasses import dataclass, field

from mpd import CommandError, MPDClient, MPDError

from music_tui.core.models import Song

log = logging.getLogger(__name__)

IDLE_SUBSYSTEMS = ("player", "mixer", "playlist", "options")

'''
@1.初始化state数据,储存MPD数据
@2.解析MPD字符信息(获取数据信息)
@3.计算播放进度
'''
@dataclass(frozen=True, slots=True)
class Status:
    state: str = "stop"
    elapsed: float = 0.0
    duration: float = 0.0
    volume: int | None = None
    song: int | None = None
    repeat: bool = False
    random: bool = False
    single: bool = False
    consume: bool = False
    playlist_version: int = -1
    sampled_at: float = field(default_factory=time.monotonic)

    @classmethod
    def from_dict(cls, d:dict) -> Status:
        def num(key: str, cast, default=None):
            try:
                return cast(d[key])
            except (KeyError, TypeError, ValueError):
                return default

        v = num("playlist", int, None)
        return cls(
            state=d.get("state", "stop"),
            elapsed=num("elapsed",float,0.0) or 0.0,
            duration=num("duration",float,0.0) or 0.0,
            volume=num("volume", int),
            song=num("song", int),
            repeat=d.get("repeat") == "1",
            random=d.get("random") == "1",
            single=d.get("single") in ("1", "oneshot"),
            consume=d.get("consume") in ("1", "oneshot"),
            playlist_version=-1 if v is None else v
        )

    def position(self) -> float:
        # 本地插值。进度条靠这个才平滑，不要每秒去问MPD
        if self.state != "play":
            return self.elapsed
        drift = time.monotonic() - self.sampled_at
        end = self.duration if self.duration > 0 else float("inf")
        return min(end, self.elapsed + drift)

# 更新MPD的state信息
@dataclass(frozen=True, slots=True)
class StatusEvent:
    status: Status

# 更新MPD的播放队列
@dataclass(frozen=True, slots=True)
class QueueEvent:
    songs: list[Song]

# 检查与MPD的连接状态
@dataclass(frozen=True, slots=True)
class ConnectionEvent:
    connected: bool
    detail: str = ""

# 连接MPD服务端+事件更新
class MpdService:
    def __init__(self, host: str = "127.0.0.1", port: int = 6600) -> None:
        self._host = host
        self._port = port
        self._events: queue.Queue = queue.Queue(maxsize = 1000)
        self._cmd_q: queue.Queue = queue.Queue()
        self._stopping = threading.Event()
        self._playlist_version = -1
        self._idle_client:MPDClient | None = None
        self._threads: list[threading.Thread] = []

    #----------开始与停止---------
    def start(self) -> None:
        for target, name in ((self._cmd_loop, "mpd-cmd"),(self._idle_loop, "mpd-idle")):
            t = threading.Thread(target=target, name=name, daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        self._stopping.set()
        self._cmd_q.put(None)
        client, self._idle_client = self._idle_client, None
        self._close(client)

    #---------UI-----------
    def play(self, pos: int | None = None) -> None:
        self.send("play") if pos is None else self.send("play",pos)

    def toggle(self) -> None:
        self.send("pause")

    def next(self) -> None:
            self.send("next")

    def previous(self) -> None:
            self.send("previous")

    def stop_playback(self) -> None:
            self.send("stop")

    def seek(self, seconds:float) -> None:
            self.send("seekcur", max(0.0, seconds))

    def setvol(self, volume: int) -> None:
            self.send("setvol", max(0, min(100, volume)))

    def set_mode(self, mode: str, enabled: bool) -> None:
        self.send(mode, 1 if enabled else 0)   # 播放模式: repeat/random/single/consume

    def add(self, uri: str) -> None:
        self.send("add", uri)

    def clear(self) -> None:
        self.send("clear")

    def refresh(self) -> None:
        self.send("__status__")    # 见_execute 里的特殊处理

    def send(self, command: str, *args: object) -> None:
        # 所有 UI 命令都走这里，由 _cmd_loop 线程统一执行
        self._cmd_q.put((command, args))

    def drain(self) -> list[object]:
        # 非阻塞取走积压的事件；UI 定时调用，一次性消费
        events: list[object] = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                return events

    #----------内部------------
    def _connect(self, *, for_idle: bool) -> MPDClient:
         client = MPDClient()
         client.timeout = None if for_idle else 10  # idle 要长阻塞
         client.connect(self._host, self._port)
         return client

    @staticmethod
    def _close(client: MPDClient | None) -> None:
        if client is None:
            return
        try:
            # 先 shutdown 唤醒阻塞在 idle() 的读线程：直接 close 会被它持有的
            # 文件锁挡住，而挂起的 recv 又不会被 close 中断 → 死锁。
            sock = client._sock
            if sock is not None:
                sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            client.disconnect()
        except OSError:
            log.debug("断开时关闭连接失败", exc_info=True)

    def _push(self, event: object) -> None:
         try:
              self._events.put_nowait(event)
         except queue.Full:
             try:
                self._events.get_nowait()
             except queue.Empty:
                  pass
             self._events.put_nowait(event)

    def _push_status(self, client:MPDClient) -> None:
         self._push(StatusEvent(Status.from_dict(client.status())))

    def _execute(self, client:MPDClient, command: str, args: tuple) -> None:
        if command == "__status__":
              self._push_status(client)
        else:
            getattr(client, command)(*args)

    def _cmd_loop(self) -> None:
         client: MPDClient | None = None
         backoff = 0.5
         while not self._stopping.is_set():
              item = self._cmd_q.get()
              if item is None:
                   break
              command, args = item
              try:
                   if client is None:
                        client = self._connect(for_idle=False)
                   self._execute(client, command, args)
                   backoff = 0.5
              except CommandError as exc:
                # 「stop 状态下按 next」这类，MPD 会拒绝。吞掉，UI 不崩。
                log.debug("命令 %s 被拒绝：%s", command, exc)
              except (MPDError, OSError) as exc:
                log.warning("命令 %s 失败，重连：%s", command, exc)
                self._close(client)
                client = None
                self._push(ConnectionEvent(False, str(exc)))
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)      # 0.5 → 1 → 2 … 封顶 30s
              finally:
                if client is not None:
                    try:
                        self._push_status(client)
                    except (MPDError, OSError):
                        self._close(client)
                        client = None

    def _idle_loop(self) -> None:
        backoff = 0.5
        while not self._stopping.is_set():
            client: MPDClient | None = None
            try:
                client = self._connect(for_idle=True)
                self._idle_client = client
                self._push(ConnectionEvent(True))
                backoff = 0.5
                self._sync(client, ["player", "playlist"])   # 连上先推一次全量

                while not self._stopping.is_set():
                    changed = client.idle(*IDLE_SUBSYSTEMS)
                    self._sync(client, changed)
            except (MPDError, OSError) as exc:              # 断线、被 stop() 关闭…
                if self._stopping.is_set():
                    break
                log.warning("事件连接断开：%s", exc)
                self._push(ConnectionEvent(False, str(exc)))
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
            finally:
                self._idle_client = None
                self._close(client)

    def _sync(self, client: MPDClient, changed: list[str] | list) -> None:
        status = Status.from_dict(client.status())
        self._push(StatusEvent(status))
        if "playlist" in changed or status.playlist_version != self._playlist_version:
            self._playlist_version = status.playlist_version
            self._push(QueueEvent([Song.from_mpd(d) for d in client.playlistinfo()]))
                    