# 纯数据模型

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Song:
    uri: str
    title: str = "" 
    artist: str = ""
    album: str = ""
    duration: float = 0.0
    pos: int = -1
    songid: int | None = None

    @classmethod
    def from_mpd(cls, d:dict) -> Song:
        name = d.get("file", "")
        return cls(
            uri=name,
            title=d.get("title")or name.rsplit("/",1)[-1],
            artist=d.get("artist",""),
            album=d.get("album",""),
            duration=float(d.get("duration") or 0),
            pos=int(d["pos"]) if "pos" in d else -1,
            songid=int(d["id"]) if "id" in d else None,
        )

    def label(self) -> str:
        return f"{self.artist} - {self.title}" if self.artist else self.title
    