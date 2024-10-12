from __future__ import annotations

from Automated_Tasker.tasklist import Tasks, DAY_START
from Automated_Tasker.utils.vault import Vault
from Automated_Tasker.services.calendar import GoogleCalendarClient
from Automated_Tasker.services.pushbullet import PushbulletNotifier

from datetime import timedelta

from typing import List

import logging

logger = logging.getLogger(__name__)


@Tasks.register
class ToDoList:
    """A task for pushing today's calendar events and tasks through PushBullet."""

    NAME: str = "ToDoList"
    TIME: timedelta = timedelta(hours=DAY_START[0], minutes=DAY_START[1])
    DAYS: List[str] = []
    DAY: int = 0

    async def execute(self, vault: Vault | None = None):
        """Get all of today's events and tasks from Google Calendar and push it to pushbullet.

        Parameters:
            vault (Vault | None): The vault with the pushbullet token and Google Calendar creds
        """
        calendar = GoogleCalendarClient(vault)
        notifier = PushbulletNotifier(vault.load_entries()["pushbullet-key"])

        events = list(calendar.get_todays_events())
        if events:
            update = "Events - "
            for event in events:
                update = update + f"\n{event['start']['dateTime'][11:19]} - {event['summary']}"
            notifier.send_notification("Today's Events", update)
