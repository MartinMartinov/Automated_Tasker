from __future__ import annotations

from Automated_Tasker.tasklist import Tasks
from Automated_Tasker.utils.vault import Vault
from Automated_Tasker.utils.ottawa_swimschedule import get_lane_swims
from Automated_Tasker.services.discord import DiscordBot

from time import strptime
from datetime import timedelta
from typing import List
import hashlib

import logging

logger = logging.getLogger(__name__)

@Tasks.register
class GetSwimSchedule:
    """A task for getting City of Ottawa pool schedules."""

    NAME: str = "SwimSchedulePoster"
    TIME: timedelta = timedelta(hours=16)
    DAYS: List[str] = ['Tuesday','Friday']
    DAY: int = 0

    async def execute(self, vault: Vault | None = None):
        """Start all the SwitchBot alarm devices.

        Parameters:
            vault (Vault | None): The vault with the discord bot token
        """
        # Get schedule
        messages = []
        async for table in get_lane_swims(
            'Saturday',
            "1980 Ogilvie Rd, Ottawa, ON",
            strptime("8:00", "%H:%M"),
            strptime("14:00", "%H:%M")
        ):
            message = "```"
            message += table
            message += "```"
            messages.append(message)

        # If schedule is new, post it
        hash = "HMAC: "+hashlib.md5(''.join(messages).encode()).hexdigest()
        async with DiscordBot(vault.load_entries()['discord-token-1322957423941648544']) as bot:
            old_hash = await bot.get_most_recent_message("Factorio & Swim Club", "swim-schedule")

            if hash != old_hash:
                await bot.post_message("Factorio & Swim Club", "general", "New schedule alert!!!")
                for message in messages:
                    await bot.post_message("Factorio & Swim Club", "swim-schedule", message)
                await bot.post_message("Factorio & Swim Club", "swim-schedule", hash)
