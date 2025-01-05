from __future__ import annotations

from Automated_Tasker.tasklist import Tasks
from Automated_Tasker.utils.vault import Vault
from Automated_Tasker.services.calendar import GoogleCalendarClient
from Automated_Tasker.services.switchbot import SwitchBotController

from datetime import timedelta
from aiohttp import ClientSession

from typing import List

import logging

logger = logging.getLogger(__name__)

@Tasks.register
class StartNightLight:
    """A task for turning on the night scene set in switchbot."""

    NAME: str = "NightLight"
    TIME: timedelta = timedelta(hours=23)
    DAYS: List[str] = []
    DAY: int = 0

    async def execute(self, vault: Vault | None = None):
        """Start all the SwitchBot alarm devices.

        Parameters:
            vault (Vault | None): The vault with the switchbot token and secret
        """
        tokens = vault.load_entries()
        controller = SwitchBotController(tokens["switchbot-token"], tokens["switchbot-secret"])
        async with ClientSession() as session:
            await controller.fetch_scenes(session)
            await controller.activate_scene(session, controller.lookup_scene("Night Light"))
