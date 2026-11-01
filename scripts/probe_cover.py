"""阶段 1 验收：从 MPD 读封面。用法：python scripts/probe_cover.py"""
import threading
import time

from music_tui.services.mpd import CoverEvent, MpdService

SONGS = [
    "松下優也 - Mr.“Broken Heart” (Instrumental).mp3",
    "Ba+-+Duvet.flac",
]


def main() -> None:
    svc = MpdService()
    svc.start()
    try:
        time.sleep(0.5)                    # 等 idle 线程连上 MPD
        for uri in SONGS:
            svc.load_cover(uri)

        seen: dict[str, CoverEvent] = {}
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and len(seen) < len(SONGS):
            for ev in svc.drain():
                if isinstance(ev, CoverEvent):
                    seen[ev.uri] = ev
            time.sleep(0.05)

        for uri in SONGS:
            ev = seen.get(uri)
            if ev is None:
                print(f"✗ 没收到事件: {uri}")
            else:
                size = len(ev.data) if ev.data else 0
                print(f"✓ {uri}  mime={ev.mime!r}  {size} 字节")

        names = [t.name for t in threading.enumerate() if t.name.startswith("mpd")]
        print("线程:", names)
        assert "mpd-cmd" in names, "命令线程死了！"
    finally:
        svc.stop()


if __name__ == "__main__":
    main()