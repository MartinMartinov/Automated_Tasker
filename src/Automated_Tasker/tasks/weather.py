from __future__ import annotations

from Automated_Tasker.tasklist import Tasks, FIRST_THING_HOURS, FIRST_THING_MINUTES
from Automated_Tasker.utils.vault import Vault
from Automated_Tasker.services.pushbullet import PushbulletNotifier

from datetime import timedelta

from typing import List
from bs4 import BeautifulSoup
from aiohttp import ClientSession

import logging

logger = logging.getLogger(__name__)


@Tasks.register
class Weather:
    """A task for pushing the GoC weather report through PushBullet."""

    NAME: str = "Weather"
    TIME: timedelta = timedelta(hours=FIRST_THING_HOURS, minutes=FIRST_THING_MINUTES)
    DAYS: List[str] = []
    DAY: int = 0

    async def execute(self, vault: Vault | None = None):
        """Get the weather from weather.gc.ca and push it to pushbullet.

        Parameters:
            vault (Vault | None): The vault with the pushbullet token
        """
        notifier = PushbulletNotifier(vault.load_entries()["pushbullet-key"])
        url = "https://weather.gc.ca/en/location/index.html?coords=45.403,-75.687"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        async with ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html_content = await response.text()
                else:
                    logger.warning("Did not get a 200 response from weather.gc.ca.")
                    return

        report = "No special weather statement found for today."
        soup = BeautifulSoup(html_content, "html.parser")

        # Locate the table containing the weather forecast
        weather_table = soup.find("table", class_="table mrgn-bttm-md textforecast")

        # Find the specific row for tonight's weather
        rows = weather_table.find_all("tr")
        for row in rows:
            columns = row.find_all("td")
            if len(columns) > 0 and "tonight" in columns[0].get_text(strip=True).lower():
                report = columns[1].get_text(strip=True)
                break

        notifier.send_notification("Weather", report)
