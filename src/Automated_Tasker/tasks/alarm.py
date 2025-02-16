from __future__ import annotations

from Automated_Tasker.tasklist import Tasks, SET_ALARM
from Automated_Tasker.utils.vault import Vault
from Automated_Tasker.services.calendar import GoogleCalendarClient
from Automated_Tasker.services.switchbot import SwitchBotController

from datetime import timedelta
from aiohttp import ClientSession

from typing import List
from datetime import datetime

import logging

logger = logging.getLogger(__name__)

@Tasks.register
class SetAlarm:
    """A task for checking traffic."""

    NAME: str = "SetAlarm"
    TIME: timedelta = timedelta(hours=SET_ALARM[0], minutes=SET_ALARM[1])
    DAYS: List[str] = []
    DAY: int = 0

    async def execute(self, vault: Vault | None = None):
        """Get the first event and create an alarm for it.

        Parameters:
            vault (Vault | None): The vault with the Google Calendar creds
        """
        calendar = GoogleCalendarClient(vault)
        for event in calendar.get_todays_events():
            if not event['summary'].startswith('-w'):
                continue

            alarm_time = timedelta(minutes=30)
            if "overrides" in event["reminders"]:
                offset = timedelta(minutes=event["reminders"]["overrides"][0]["minutes"])
                etime = datetime.strptime(event["start"]["dateTime"][:19], "%Y-%m-%dT%H:%M:%S") - offset
                alarm_time = timedelta(hours=etime.hour, minutes=etime.minute, seconds=etime.second)

            class Alarm:
                """An etheral task created for setting off an alarm at a variable time."""

                NAME: str = "Alarm"
                TIME: timedelta = alarm_time
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
                        await controller.activate_scene(session, controller.lookup_scene("Alarm Start"))

            Tasks.add_daily_tasklist(Alarm())
            logger.info(f"Added Alarm ({alarm_time}) to daily tasklist.")
