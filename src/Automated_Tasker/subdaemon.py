from __future__ import annotations

from typing import Protocol, List, Final, Deque, TypeVar, Any
import importlib
import functools
import traceback
from datetime import timedelta, datetime
import collections
import pkgutil
import asyncio
from Automated_Tasker.utils.vault import vault
from Automated_Tasker.services.pushbullet import PushbulletNotifier
from pytz import timezone
from getpass import getpass

import logging

logger = logging.getLogger(__name__)


class _Subdaemon(Protocol):
    """The minimum template for all the subdaemons registered by the subdaemonlist."""

    NAME: str

    async def start(self, vault: Vault | None = None) -> None: ...
    
class SubdaemonRegistry:
    """
    The registry which loads all the subdaemons in the subdaemons folder as _Subdaemons 
    in the global_subdaemonlist.
    """

    _DaemonT = TypeVar("_DaemonT", bound=_Subdaemon)

    def __init__(self, package: str | None = None):
        self.loaded = False
        self._package_name = package
        self.global_subdaemonlist: list[Any] = []
        self.vault = vault
        self.subdaemons = {}

    def load(self) -> None:
        """Invoke the _load_package() function on _package_name (if initiliazed)."""
        if not self.loaded:
            if self._package_name:
                _load_package(self._package_name)
        self.loaded = True

    def register(self, subdaemon: type[_DaemonT]) -> type[_DaemonT]:
        """Decorator used to take a _Daemon class and add it to the global_subdaemonlist.

        Parameters:
            subdaemon (_DaemonT): The _Daemon class being defined

        Returns:
            _DaemonT: The unchanged but now registered _Daemon
        """
        self.global_subdaemonlist.append(subdaemon)
        logger.info(f"Registered {subdaemon.NAME} to global subdaemonlist.")
        return subdaemon
    
    def start(self) -> None:
        """Start all the subdaemons in the registry."""
        if self.subdaemons:
            for name, subdaemon in self.subdaemons.items():
                subdaemon.cancel()
        self.subdaemons = {}
        for subdaemon in self.global_subdaemonlist:
            self.subdaemons[subdaemon.NAME] = asyncio.create_task(subdaemon().start(self.vault))
        logger.info(f"Started {', '.join(self.subdaemons.keys())} subdaemons.")

    def restart_failed(self) -> None:
        """Restart all the subdaemons in the registry that are done."""
        for name, task in self.subdaemons.items():
            if task.done():
                for subdaemon in self.global_subdaemonlist:
                    if name == subdaemon.NAME:
                        self.subdaemons[name] = asyncio.create_task(subdaemon().start(self.vault))
                        logger.info(f"Restarted {name} subdaemon.")
                        break

@functools.cache
def _load_package(package: str) -> None:
    """Walk though the package directory and load each module found inside.

    Parameters:
        package (str): The package to load and do the walkthrough on
    """
    root = importlib.import_module(package)
    for _, module_name, is_pkg in pkgutil.walk_packages(root.__path__, prefix=f"{root.__name__}."):
        if not is_pkg:
            importlib.import_module(module_name)


Subdaemons = SubdaemonRegistry(package="Automated_Tasker.subdaemons")