from __future__ import annotations

from Automated_Tasker.subdaemon import Subdaemons
from Automated_Tasker.services.switchbot import SwitchBotController
from Automated_Tasker.services.pushbullet import PushbulletNotifier

from datetime import timedelta
from aiohttp import ClientSession

from typing import List
import asyncio

import logging

logger = logging.getLogger(__name__)

CHECK_PERIOD = 30*60 # 30 minutes
ALERT_PERIOD = 18*60*60 # 12 hours


@Subdaemons.register
class CheckLitterBox:
    """A deamon that checks the regular use of the litter box."""

    NAME: str = "LitterChecker"

    def __init__(self) -> None:
        self.time_since_use = 0
        self.tokens = None

    async def start(self, vault: Vault | None = None):
        """Check to see if the litterbox swaps between 

        Parameters:
            vault (Vault | None): The vault with the switchbot token and secret
        """
        if not self.tokens:
            self.tokens = vault.load_entries()
        controller = SwitchBotController(self.tokens["switchbot-token"], self.tokens["switchbot-secret"])
        async with ClientSession() as session:
            await controller.refresh(session)
        last_status = "timeOutNotClose"
        check_time = 0
        while True:
            async with ClientSession() as session:
                status = (await controller.status(session, "Litterbox Position"))["openState"]
                    
                if status == last_status:
                    check_time += CHECK_PERIOD
                else:
                    last_status = status
                    check_time = 0
                
                if check_time >= ALERT_PERIOD:
                    notifier = PushbulletNotifier(vault.load_entries()["pushbullet-key"])
                    notifier.send_notification(
                        "Litterbox alert",
                        f"It has not self-cleaned in at least {check_time//60//60:02d} hours"
                    )
            await asyncio.sleep(CHECK_PERIOD)
