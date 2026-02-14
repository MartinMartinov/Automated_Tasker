from __future__ import annotations

from Automated_Tasker.subdaemon import Subdaemons
from Automated_Tasker.services.switchbot import SwitchBotController
from Automated_Tasker.services.pushbullet import PushbulletNotifier

from datetime import timedelta, datetime
from aiohttp import ClientSession

from typing import List
import asyncio

import logging

logger = logging.getLogger(__name__)

CHECK_PERIOD = timedelta(minutes=30)
ALERT_PERIOD = timedelta(hours=24)

@Subdaemons.register
class CheckLitterBox:
    """A deamon that checks the regular use of the litter box."""

    NAME: str = "LitterChecker"

    async def start(self, vault: Vault | None = None):
        """Check to see if the litterbox swaps between 

        Parameters:
            vault (Vault | None): The vault with the switchbot token and secret
        """
        tokens = vault.load_entries()
        last_status = "timeOutNotClose"
        last_time = datetime.now()
        while True:
            async with ClientSession() as session:
                controller = SwitchBotController(tokens["switchbot-token"], tokens["switchbot-secret"])
                await controller.refresh(session)
                try:
                    status = (await controller.status(session, "Litterbox Position"))["openState"]
                except ConnectionError:
                    asyncio.sleep(30)
                    continue
                    
            if status != last_status:
                last_time = datetime.now()
                last_status = status
            
            if (datetime.now()-last_time) >= ALERT_PERIOD:
                notifier = PushbulletNotifier(vault.load_entries()["pushbullet-key"])
                notifier.send_notification(
                    "Litterbox alert",
                    f"It has not self-cleaned in at least {(datetime.now()-last_time).total_seconds()//3600} hours"
                )
                last_time = datetime.now()
            await asyncio.sleep(CHECK_PERIOD.total_seconds())
