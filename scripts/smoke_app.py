import asyncio

from music_tui.app import MusicTui

async def main() -> None:
    app = MusicTui()
    async with app.run_test() as pilot:
        await pilot.pause()
        if app._exception is not None:
            raise SystemExit(f"启动失败:{app._exception!r}")
        print("挂载正常，控件：", [type(w).__name__ for w in app.query("*")])

asyncio.run(main())        
