from __future__ import annotations

from Automated_Tasker.tasklist import Tasks, SET_ALARM
from Automated_Tasker.utils.vault import Vault
from Automated_Tasker.services.maps import GoogleMapsClient
from Automated_Tasker.services.calendar import GoogleCalendarClient
from Automated_Tasker.services.pushbullet import PushbulletNotifier

from datetime import timedelta
import asyncio
from urllib import parse

from typing import List, Any
from datetime import datetime
from pytimeparse.timeparse import timeparse

import logging

logger = logging.getLogger(__name__)


def convert_timedelta(date: datetime) -> timedelta:
    """Convert a datetime into a timedelta showing time into today instead

    Args:
        date: The original datetime object

    Returns:
        The converted timedelta
    """
    return timedelta(
        hours=date.hour,
        minutes=date.minute,
        seconds=date.second,
    )


def directions_url(origin, destination, travel_mode="driving"):
    base_url = "https://www.google.com/maps/dir/?api=1"
    params = {"origin": origin, "destination": destination, "travelmode": travel_mode}
    return f"{base_url}&{parse.urlencode(params)}"


@Tasks.register
class SetTrafficAlerts:
    """A task for creating an Alarm task based on Google Calendar entries for the day."""

    NAME: str = "SetTrafficAlerts"
    TIME: timedelta = timedelta(hours=SET_ALARM[0], minutes=SET_ALARM[1])
    DAYS: List[str] = []
    DAY: int = 0

    async def execute(self, vault: Vault | None = None):
        """Get all of today's events from Google Calendar to warn of changes to travel time.

        Parameters:
            vault: The vault with the pushbullet token and Google Calendar creds
        """
        calendar = GoogleCalendarClient(vault)
        maps = GoogleMapsClient(vault)
        home_address = vault.load_entries()["home-address"]
        notifier = PushbulletNotifier(vault.load_entries()["pushbullet-key"])

        for event in calendar.get_todays_events():
            if "location" not in event:
                continue

            arrival_time = datetime.strptime(event["start"]["dateTime"][:19], "%Y-%m-%dT%H:%M:%S")
            arrival_time -= timedelta(minutes=5)
            api_dict = dict(
                origin=home_address,
                destination=event["location"],
                arrival_time=arrival_time.timestamp(),
            )

            for _ in range(5):
                try:  # Try five times while catching exceptions
                    seconds = timeparse((await maps.get_distance(**api_dict))["duration"])
                    break
                except:
                    await asyncio.sleep(60)  # In no rush to schedule this
                seconds = timeparse((await maps.get_distance(**api_dict))["duration"])

            name = event["summary"]

            fallback_time = convert_timedelta(arrival_time - (timedelta(seconds=seconds)))
            recheck_time = convert_timedelta(arrival_time - (2 * timedelta(seconds=seconds)))

            class TrafficAlert:
                """An ethereal task created for checking travel time before going somewhere."""

                NAME: str = "TrafficAlert"
                TIME: timedelta = recheck_time
                DAYS: List[str] = []
                DAY: int = 0

                def __init__(
                    self,
                    name: str,
                    *,
                    api_dict: dict[str, Any],
                    fallback_time: datetime,
                    arrival_time: datetime,
                    vault: Vault,
                ):
                    self.name = name
                    self.api_dict = api_dict
                    self.vault = vault
                    self.fallback_time = fallback_time
                    self.arrival_time = arrival_time

                async def execute(self, _: Vault | None = None):
                    """Start all the SwitchBot alarm devices."""
                    seconds = None
                    for _ in range(5):  # Try five times while catching exceptions
                        try:
                            maps = GoogleMapsClient(self.vault)
                            seconds = timeparse((await maps.get_distance(**self.api_dict))["duration"])
                            break
                        except:
                            await asyncio.sleep(60)

                    if seconds:
                        departure_time = convert_timedelta(self.arrival_time - timedelta(seconds=seconds))
                        notifier.send_notification(
                            f"ETA for {self.name}",
                            f"Leave at {departure_time} to get there for {self.arrival_time}",
                            directions_url(api_dict["origin"], api_dict["destination"]),
                        )
                        return
                    notifier.send_notification(
                        f"Fallback ETA for {self.name}",
                        f"Leave at {self.fallback_time} to get there for {self.arrival_time}",
                        directions_url(api_dict["origin"], api_dict["destination"]),
                    )

            Tasks.add_daily_tasklist(
                TrafficAlert(
                    name,
                    api_dict=api_dict,
                    fallback_time=fallback_time,
                    arrival_time=arrival_time,
                    vault=vault,
                )
            )
            logger.info(f"Added TrafficAlert at ({recheck_time}) to daily tasklist.")
