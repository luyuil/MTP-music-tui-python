import time

from mpd import MPDClient

c = MPDClient()
c.timeout = 120
c.connect("127.0.0.1", 6600)

print("监听中... 另开一个终端跑 mpc pause / mpc play / mpc volume 30 / mpc next")
deadline = time.time() + 120
while time.time() < deadline:
    changed = c.idle("player", "mixer", "playlist", "options")
    st = c.status()
    print(f"[{time.strftime('%H:%M:%S')}] 变了: {changed} "
          f"→ state={st.get('state')} song={st.get('song')} vol={st.get('volume')}")