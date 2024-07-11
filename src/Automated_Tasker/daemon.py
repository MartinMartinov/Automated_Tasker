from __future__ import annotations

from Automated_Tasker.tasklist import Tasks
from datetime import datetime
import asyncio

import logging

logger = logging.getLogger(__name__)

LOOP_WAIT = 15


class Daemon:
    """The simple daemon invoking the different tasklist functions."""

    def __init__(self):
        self.day = ""
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler()]
        )
        logger.info("Daemon initiated.")
        Tasks.load()

    def new_day(self) -> None:
        """Generate a new list based on the global registry."""
        Tasks.create_daily_tasklist()

    async def main_loop(self) -> None:
        """The main loop doing regular checks on daily tasks every LOOP_WAIT seconds."""
        logger.info("Entering main loop.")
        while True:
            current = datetime.now().day
            if self.day != current:
                self.new_day()
                self.day = current
            await Tasks.execute_daily_tasks()
            await asyncio.sleep(LOOP_WAIT)
