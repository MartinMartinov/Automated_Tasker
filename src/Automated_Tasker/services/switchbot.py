from __future__ import annotations

import asyncio
import time
import hashlib
import hmac
import base64
import uuid
import json

from aiohttp import ClientSession

NUM_RETRIES = 10
WAIT_RETRIES = 5  # Seconds

URL = "https://api.switch-bot.com/"

# You're gonna want these API docs:
# https://github.com/OpenWonderLabs/SwitchBotAPI


class SwitchBotController:
    """A class for performing necessary switchbot operations.

    Requires the SwitchBot token and secret under the vault entry tag 'switchbot-token' and 'switchbot-secret'
    """

    def __init__(self, token: str, secret: str):
        """Initiate the controller for an account (and fetch scenes/devices if given a session).

        Parameters:
            token: The token given for a SwitchBot account
            secret: The secret given for a SwitchBot account
        """
        nonce = uuid.uuid4()
        t = int(round(time.time() * 1000))
        string_to_sign = "{}{}{}".format(token, t, nonce)

        string_to_sign = bytes(string_to_sign, "utf-8")
        secret = bytes(secret, "utf-8")

        sign = base64.b64encode(hmac.new(secret, msg=string_to_sign, digestmod=hashlib.sha256).digest())

        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json; charset=utf8",
            "t": str(t),
            "sign": str(sign, "utf-8"),
            "nonce": str(nonce),
        }
        self.devices = {}
        self.scenes = {}

    async def refresh(self, session: ClientSession) -> None:
        """Fetch all lists to populate the class.

        Parameters:
            session: An aiohttp session to be used for all the switchbot requests

        Raises:
            ConnectionError: Raised if only bad responses are received after NUM_RETRIES attemps
        """
        await self.get_devices(session)
        await self.get_scenes(session)

    async def get_devices(self, session: ClientSession) -> None:
        """Fetch the list of devices and store them in the devices list.

        Parameters:
            session: An aiohttp session to be used for all the switchbot requests

        Raises:
            ConnectionError: Raised if only bad responses are received after NUM_RETRIES attemps
        """
        for _ in range(NUM_RETRIES):
            async with session.get(f"{URL}v1.1/devices", headers=self.headers) as response:
                if not response.ok:
                    await asyncio.sleep(WAIT_RETRIES)
                    continue
                listings = (await response.json())["body"]["deviceList"]
                self.devices = {device["deviceName"]: device["deviceId"] for device in listings}
                return
        raise ConnectionError("Could not get devices")

    async def get_scenes(self, session: ClientSession) -> None:
        """Fetch the list of scenes and store them in the scenes dict, mapping sceneName to sceneId.

        Parameters:
            session: An aiohttp session to be used for all the switchbot requests

        Raises:
            ConnectionError: Raised if only bad responses are received after NUM_RETRIES attemps
        """
        for _ in range(NUM_RETRIES):
            async with session.get(f"{URL}v1.1/scenes", headers=self.headers) as response:
                if not response.ok:
                    await asyncio.sleep(WAIT_RETRIES)
                    continue
                listings = (await response.json())
                self.scenes = {scene["sceneName"]: scene["sceneId"] for scene in listings["body"]}
                return
        raise ConnectionError("Could not get scenes")

    async def command(self, session: ClientSession, device: str, payload: str) -> None:
        """Post a command to a device.

        Parameters:
            session: An aiohttp session to be used for all the switchbot requests
            device: The name of the device to have the command pushed to it
            payload: The payload containing the command to be given

        Raises:
            ConnectionError: Raised if only bad responses are received after NUM_RETRIES attemps
        """
        for _ in range(NUM_RETRIES):
            async with session.post(
                f"{URL}v1.1/devices/{self.devices[device]}/commands", headers=self.headers, json=payload
            ) as response:
                if not response.ok:
                    await asyncio.sleep(WAIT_RETRIES)
                    continue
                return
        raise ConnectionError("Could not send command")

    async def status(self, session: ClientSession, device: str) -> Any:
        """Pull the status of a device.

        Parameters:
            session: An aiohttp session to be used for all the switchbot requests
            device: The name of the device to have the command pushed to it

        Raises:
            ConnectionError: Raised if only bad responses are received after NUM_RETRIES attemps
        """
        for _ in range(NUM_RETRIES):
            async with session.get(f"{URL}v1.1/devices/{self.devices[device]}/status", headers=self.headers) as response:
                if not response.ok:
                    await asyncio.sleep(WAIT_RETRIES)
                    continue
                return (await response.json())["body"]
        raise ConnectionError("Could not get status")

    async def execute(self, session: ClientSession, scene: str) -> None:
        """Active the specific scene.

        Parameters:
            session: An aiohttp session to be used for all the switchbot requests
            scene: The scene pulled from the scenes dict to execute
        """
        for _ in range(NUM_RETRIES):
            async with session.get(f"{URL}v1.1/scenes/{self.scenes[scene]}/execute", headers=self.headers) as response:
                if not response.ok:
                    await asyncio.sleep(WAIT_RETRIES)
                    continue
                return
        raise ConnectionError("Could not execute scene")
    
    async def light_bulb(
        self,
        session: ClientSession,
        device: str,
        brightness: int = 100,
        colour: str = "255:255:204",
    ) -> None:
        """Turn on a light bulb.

        Parameters:
            session: An aiohttp session to be used for all the switchbot requests
            device: The device ID
            brightness: A number between 1-100 (inclusive) to set the brightness
            colour: A colour defined by an 256 RGB string (i.e., R:G:B)
        """
        tasks = [
            ("power", "on", "turnOn", "default"), 
            ("brightness", brightness, "setBrightness", brightness), 
            ("color", colour, "setColor", colour),
         ]
        for _ in range(0, 10):
            status = await self.status(session, device)
            if all(status[key] == value for key, value, _, _ in tasks):
                return

            for key, value, cmd, param in tasks:
                if status[key] != value:
                    await self.command(session, device, {"command": cmd, "parameter": param, "commandType": "command"})

            await asyncio.sleep(5)

    async def activate_socket(
        self,
        session: ClientSession,
        device: str,
    ) -> None:
        """Turn on a socket.

        Parameters:
            session: An aiohttp session to be used for all the switchbot requests
            device: The device ID
        """
        for _ in range(0, 10):
            status = await self.status(session, device)
            if status["power"] == "on":
                return

            await self.command(session, device, {"command": "turnOn", "commandType": "command"})
            await asyncio.sleep(5)

    async def press_bot(
            controller: SwitchBotController,
            session: ClientSession,
            device: str
        ) -> None:
        """Press a bot.

        Parameters:
            session: An aiohttp session to be used for all the switchbot requests
            device: The device ID
        """
        await controller.command(session, device, {"command": "press", "commandType": "command"})
        await asyncio.sleep(5)

    async def open_curtain(
        self,
        session: ClientSession,
        device: str
    ) -> None:
        """Turn every a specefic lightbulb on (to brightness and colour).

        Parameters:
            session: An aiohttp session to be used for all the switchbot requests
            device: The device ID
        """
        for _ in range(0, 10):
            status = await self.status(session, device)
            if "moving" in status and status["moving"] != False:
                await asyncio.sleep(30)
                status = await self.status(session, device)

            if status["slidePosition"] < 10:
                return

            await self.command(session, device, {
                "command": "setPosition",
                "parameter": "0,1,0",
                "mode": "1",
                "commandType": "command",
            })
            await asyncio.sleep(5)
