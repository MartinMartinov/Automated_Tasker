from __future__ import annotations

from Automated_Tasker.tasklist import Tasks
from Automated_Tasker.utils.vault import Vault
from Automated_Tasker.services.calendar import GoogleCalendarClient
from Automated_Tasker.services.switchbot import SwitchBotController

from datetime import timedelta
from aiohttp import ClientSession

import asyncio
from typing import List
from datetime import datetime

import logging

logger = logging.getLogger(__name__)

@Tasks.register
class SetAlarm:
    """A task for creating an Alarm task based on Google Calendar entries for the day."""

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
