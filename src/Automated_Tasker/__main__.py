from __future__ import annotations

from Automated_Tasker.daemon import Daemon
import asyncio


def main():
    app = Daemon()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.main_loop())


if __name__ == "__main__":
    main()
