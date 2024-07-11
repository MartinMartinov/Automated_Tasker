from __future__ import annotations

import asyncio
import time
import hashlib
import hmac
import base64
import uuid

from aiohttp import ClientSession


class SwitchBotController:
    """A class for performing necessary switchbot operations.

    Requires the SwitchBot token and secret under the vault entry tag 'switchbot-token' and 'switchbot-secret'"""

    def __init__(self, token: str, secret: str):
        nonce = uuid.uuid4()
        t = int(round(time.time() * 1000))
        string_to_sign = "{}{}{}".format(token, t, nonce)

        string_to_sign = bytes(string_to_sign, "utf-8")
        secret = bytes(secret, "utf-8")

        sign = base64.b64encode(hmac.new(secret, msg=string_to_sign, digestmod=hashlib.sha256).digest())

        self.base_url = "https://api.switch-bot.com/"
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json; charset=utf8",
            "t": str(t),
            "sign": str(sign, "utf-8"),
            "nonce": str(nonce),
        }
        self.devices = []
        self.scenes = {}

    async def fetch_devices(self, session: ClientSession) -> None:
        """Fetch the list of devices and store them in the devices list.

        Parameters:
            session (ClientSession): An aiohttp session to be used for all the switchbot requests
        """
        url = f"{self.base_url}v1.1/devices"
        async with session.get(url, headers=self.headers) as response:
            resp_json = await response.json()
            self.devices = resp_json.get("body", {}).get("deviceList", [])

    async def fetch_scenes(self, session: ClientSession) -> None:
        """Fetch the list of scenes and store them in the scenes dict, mapping sceneName to sceneId.

        Parameters:
            session (ClientSession): An aiohttp session to be used for all the switchbot requests
        """
        url = f"{self.base_url}v1.1/scenes"
        async with session.get(url, headers=self.headers) as response:
            resp_json = await response.json()
            self.scenes = {scene["sceneName"]: scene["sceneId"] for scene in resp_json.get("body", [])}

    async def turn_on_light_bulbs(self, session: ClientSession) -> None:
        """Turn every lightbult listed in devices to maximum brightness yellow-white light.

        Parameters:
            session (ClientSession): An aiohttp session to be used for all the switchbot requests
        """
        tasks = []
        for device in self.devices:
            if device["deviceType"] == "Color Bulb":
                device_id = device["deviceId"]
                url = f"{self.base_url}v1.1/devices/{device_id}/commands"
                payload = {
                    "command": "setColor",
                    "parameter": "255:255:204",
                    "commandType": "command",
                }
                tasks.append(session.post(url, headers=self.headers, json=payload))
                payload = {
                    "command": "setBrightness",
                    "parameter": "100",
                    "commandType": "command",
                }
                tasks.append(session.post(url, headers=self.headers, json=payload))
                payload = {
                    "command": "turnOn",
                    "parameter": "default",
                    "commandType": "command",
                }
                tasks.append(session.post(url, headers=self.headers, json=payload))
        await asyncio.gather(*tasks)

    async def open_curtains(self, session: ClientSession) -> None:
        """Open every Curtain3 device.

        Parameters:
            session (ClientSession): An aiohttp session to be used for all the switchbot requests
        """
        tasks = []
        for device in self.devices:
            if device["deviceType"] == "Curtain3":
                device_id = device["deviceId"]
                url = f"{self.base_url}v1.1/devices/{device_id}/commands"
                payload = {
                    "command": "setPosition",
                    "parameter": "0",
                    "mode": "1",
                    "commandType": "command",
                }
                tasks.append(session.post(url, headers=self.headers, json=payload))
        await asyncio.gather(*tasks)

    async def activate_scene(self, session: ClientSession, sceneId: str) -> None:
        """Active the specific scene.

        Parameters:
            session (ClientSession): An aiohttp session to be used for all the switchbot requests
            sceneId (str): The sceneId pulled from the scenes dict to execute
        """
        url = f"{self.base_url}v1.1/scenes/{sceneId}/execute"
        async with session.get(url, headers=self.headers) as response:
            await response.json()
