import time
from music_tui.services.mpd import MpdService


class StubClient:
    _sock = None
    def __init__(self):        self.calls = []
    def connect(self, h, p):   pass
    def disconnect(self):      pass
    def status(self):          return {"state": "stop"}
    def play(self, *a):        self.calls.append(("play", a))


def test_every_queued_command_reaches_mpd(monkeypatch):
    """连发 3 条命令，MPD 必须收到 3 条（防止 _execute 被缩进进 if 里）"""
    stub = StubClient()
    svc = MpdService()
    monkeypatch.setattr(svc, "_connect", lambda *, for_idle: stub)
    monkeypatch.setattr(svc, "_idle_loop", lambda: None)   # 只测命令线程

    svc.start()
    try:
        svc.play(); svc.play(); svc.play()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and len(stub.calls) < 3:
            time.sleep(0.01)
        assert len(stub.calls) == 3
    finally:
        svc.stop()