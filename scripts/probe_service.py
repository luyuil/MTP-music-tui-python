import time

from music_tui.services.mpd import (
    ConnectionEvent,
    MpdService,
    QueueEvent,
    StatusEvent,
)

svc = MpdService()
svc.start()

print("观察 20 秒；期间自动播放一次。Ctrl+C 提前退出")
start = time.time()
played = False
try:
    while time.time() - start < 20:
        for ev in svc.drain():
            if isinstance(ev, StatusEvent):
                s = ev.status
                print(f"[status] {s.state:5} {s.position():6.2f}/{s.duration:6.2f}s "
                      f"vol={s.volume} rnd={s.random}")
            elif isinstance(ev, QueueEvent):
                head = ev.songs[0].label() if ev.songs else "-"
                print(f"[queue ] {len(ev.songs)} 首，第一首：{head}")
            elif isinstance(ev, ConnectionEvent):
                print(f"[conn  ] connected={ev.connected} {ev.detail}")
        if not played and time.time() - start > 2:
            svc.play()
            played = True
        time.sleep(0.1)
finally:
    svc.stop()