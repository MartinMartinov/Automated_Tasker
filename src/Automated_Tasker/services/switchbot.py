from __future__ import annotations

import asyncio
import time
import hashlib
import hmac
import base64
import uuid
import json

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
    
    def lookup_scene(self, name: str) -> str:
        """Get scene ID from scene name

        Parameters:
            name (str): The name of the scene

        Returns:
            str: The ID corresponding to the name
        """
        if name in self.scenes:
            return self.scenes[name]
        return "N/A"

    async def turn_on_light_bulb(
        self, session: ClientSession, devid: str, brightness: int = 100, colour: str = "255:255:204"
    ) -> None:
        """Turn every a specefic lightbult on (to brightness and colour).

        Parameters:
            session (ClientSession): An aiohttp session to be used for all the switchbot requests
            devid (str): The device ID
            brightness (int): A number between 1-100 (inclusive) to set the brightness
            colour (str): A colour defined by an 256 RGB string (i.e., R:G:B)
        """
        complete = False
        post_url = f"{self.base_url}v1.1/devices/{devid}/commands"
        get_url = f"{self.base_url}v1.1/devices/{devid}/status"
        commands = [
            ("turnOn", "default"),
            ("setBrightness", str(brightness)),
            ("setColor", colour),
        ]
        while not complete:
            tasks = []
            for command, parameter in commands:
                payload = {
                    "command": command,
                    "parameter": parameter,
                    "commandType": "command",
                }
                tasks.append(session.post(post_url, headers=self.headers, json=payload))
            await asyncio.gather(*tasks)
            await asyncio.sleep(5)  # Rough timeout guess
            async with session.get(get_url, headers=self.headers, json=payload) as resp:
                if not resp.ok:
                    continue
                status = await resp.text()
                status = json.loads(status)["body"]
            complete = True
            commands = []
            if status["power"] != "on":
                complete = False
                commands.append(("turnOn", "default"))
            if status["brightness"] != 100:
                complete = False
                commands.append(("setBrightness", str(brightness)))
            if status["color"] != "255:255:204":
                complete = False
                commands.append(("setColor", colour))

    async def turn_on_light_bulbs(
        self, session: ClientSession, brightness: int = 100, colour: str = "255:255:204"
    ) -> None:
        """Turn every lightbult listed on (to brightness and colour) asynchronously.

        Parameters:
            session (ClientSession): An aiohttp session to be used for all the switchbot requests
            brightness (int): A number between 1-100 (inclusive) to set the brightness
            colour (str): A colour defined by an 256 RGB string (i.e., R:G:B)
        """
        tasks = []
        for device in self.devices:
            if device["deviceType"] == "Color Bulb":
                tasks.append(self.turn_on_light_bulb(session, device["deviceId"], brightness, colour))
        await asyncio.gather(*tasks)

    async def open_curtain(self, session: ClientSession, devid: str) -> None:
        """Open a specific Curtain3 device.

        Parameters:
            session (ClientSession): An aiohttp session to be used for all the switchbot requests
            devid (str): The device ID
        """
        post_url = f"{self.base_url}v1.1/devices/{devid}/commands"
        get_url = f"{self.base_url}v1.1/devices/{devid}/status"
        while True:
            payload = {
                "command": "setPosition",
                "parameter": "0,1,0",
                "mode": "1",
                "commandType": "command",
            }
            resp = await asyncio.gather(session.post(post_url, headers=self.headers, json=payload))
            await asyncio.sleep(5)  # Rough timeout guess
            moving = True
            while moving:
                await asyncio.sleep(30)  # Curtain moves real slow
                async with session.get(get_url, headers=self.headers, json=payload) as resp:
                    status = await resp.text()
                    status = json.loads(status)["body"]
                if status["moving"] != 100: # I think 0 is fastest and 100 is slowest, API says this should be a bool
                    moving = False

            if int(status["slidePosition"]) < 20:
                break

    async def open_curtains(self, session: ClientSession) -> None:
        """Open every Curtain3 device in devices asynchronously.

        Parameters:
            session (ClientSession): An aiohttp session to be used for all the switchbot requests
        """
        tasks = []
        for device in self.devices:
            if device["deviceType"] == "Curtain3":
                tasks.append(self.open_curtain(session, device["deviceId"]))
        await asyncio.gather(*tasks)

    async def turn_on_plug_alarm(self, session: ClientSession, devid: str) -> None:
        """Turn on a specific alarm Plug Mini.

        Parameters:
            session (ClientSession): An aiohttp session to be used for all the switchbot requests
            devid (str): The device ID
        """
        post_url = f"{self.base_url}v1.1/devices/{devid}/commands"
        get_url = f"{self.base_url}v1.1/devices/{devid}/status"
        while True:
            payload = {
                "command": "turnOn",
                "commandType": "command",
            }
            resp = await asyncio.gather(session.post(post_url, headers=self.headers, json=payload))
            await asyncio.sleep(5)  # Rough timeout guess
            async with session.get(get_url, headers=self.headers, json=payload) as resp:
                status = await resp.text()
                status = json.loads(status)["body"]
                if status["power"] == "on":
                    break

    async def turn_on_plug_alarms(self, session: ClientSession) -> None:
        """Turn on every Plug Mini whose name starts with Alarm in devices asynchronously.

        Parameters:
            session (ClientSession): An aiohttp session to be used for all the switchbot requests
        """
        tasks = []
        for device in self.devices:
            if device["deviceName"].startswith("Alarm") and device["deviceType"] == "Plug Mini (US)":
                tasks.append(self.turn_on_plug_alarm(session, device["deviceId"]))
        await asyncio.gather(*tasks)

    async def activate_scene(self, session: ClientSession, sceneId: str) -> None:
        """Active the specific scene.

        Parameters:
            session (ClientSession): An aiohttp session to be used for all the switchbot requests
            sceneId (str): The sceneId pulled from the scenes dict to execute
        """
        url = f"{self.base_url}v1.1/scenes/{sceneId}/execute"
        while True:
            async with session.post(url, headers=self.headers) as response:
                resp = await response.json()
            if 'message' not in resp or resp['message'] != 'success':
                continue
            break