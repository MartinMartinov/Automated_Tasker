from __future__ import annotations

from Automated_Tasker.tasklist import Tasks, SET_ALARM
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

TIME_GRADIENT = 60*10 # seconds

@Tasks.register
class SetAlarm:
    """A task for checking traffic."""

    NAME: str = "SetAlarm"
    TIME: timedelta = timedelta(hours=SET_ALARM[0], minutes=SET_ALARM[1])
    DAYS: List[str] = []
    DAY: int = 0

    async def execute(self, vault: Vault):
        """Get the first event and create an alarm for it.

        Parameters:
            vault: The vault with the Google Calendar creds
        """
        calendar = GoogleCalendarClient(vault)
        for event in calendar.get_todays_events():
            if not event["summary"].startswith("-w"):
                continue

            alarm_time = timedelta(minutes=30)
            now = datetime.now()
            now_time = timedelta(hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)

            tokens = vault.load_entries()

            if "overrides" in event["reminders"]:
                offset = timedelta(minutes=event["reminders"]["overrides"][0]["minutes"])
                etime = datetime.strptime(event["start"]["dateTime"][:19], "%Y-%m-%dT%H:%M:%S") - offset
                alarm_time = timedelta(hours=etime.hour, minutes=etime.minute, seconds=etime.second)
                alarm_time -= timedelta(seconds=60*10) # 10 minutes earlier to start coffee brewing

            if alarm_time < now_time:
                return

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
                        await controller.refresh(session)
                        try:
                            await controller.press_bot(session, "Nespresso")
                            await asyncio.sleep(30)
                            await controller.press_bot(session, "Nespresso")
                        except ConnectionError:
                            pass
                        await asyncio.sleep(60*10)
                        await controller.refresh(session)
                        await asyncio.gather(
                            controller.open_curtain(session, "Curtain"),
                            controller.light_bulb(session, "Left Bulb"),
                            controller.light_bulb(session, "Right Bulb"),
                            return_exceptions=True,
                        )
                        await asyncio.sleep(60*5)
                        try:
                            await controller.activate_socket(session, "Alarm Light")
                        except ConnectionError:
                            pass

            Tasks.add_daily_tasklist(Alarm())
            logger.info(f"Added Alarm ({alarm_time}) to daily tasklist.")
