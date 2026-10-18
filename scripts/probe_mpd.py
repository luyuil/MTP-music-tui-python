from mpd import MPDClient

c = MPDClient()
c.timeout = 5
c.connect("127.0.0.1", 6600)

st = c.status()
print("state: ", st.get("state"))
print("elapsed:", st.get("elapsed"), "/", st.get("duration"))
print("volume :", st.get("volume"))
print("queue  :", len(c.playlistinfo()), "首")

song = c.currentsong()
print("current:", song.get("artist"), "-", song.get("title"))

# 命令：成功返回 None/结果，失败抛异常
c.pause(1)
print("paused :", c.status().get("state"))
c.pause(0)
c.next()
c.setvol(40)
print("volume :", c.status().get("volume"))
c.seekcur(10)
print("elapsed:", c.status().get("elapsed"))

c.disconnect()