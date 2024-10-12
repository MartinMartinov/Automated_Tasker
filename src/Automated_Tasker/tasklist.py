from __future__ import annotations

from typing import Protocol, List, Final, Deque, TypeVar, Any
import importlib
import functools
from datetime import timedelta, datetime
import collections
import pkgutil
from Automated_Tasker.utils.vault import Vault
from Automated_Tasker.services.pushbullet import PushbulletNotifier
from pytz import timezone
from getpass import getpass

import logging

logger = logging.getLogger(__name__)

SET_ALARM = (4, 30) # Hours, Minutes to set Alarm to
DAY_START = (6, 30) # Hours, Minutes to notify in the morning

class _Task(Protocol):
    """The minimum tempalte for all the tasks registered by the tasklist."""

    NAME: str
    TIME: timedelta
    DAYS: List[str]
    DAY: int

    async def execute(self, vault: Vault | None = None, tasklist: collections.deque | None = None) -> None: ...


class TaskRegistry:
    """The registry which loads all the tasks in the tasks folder as _Tasks in the global_tasklist.

    Also creates a daily tasklist to execute throughout the day."""

    _TaskT = TypeVar("_TaskT", bound=_Task)
    WEEKDAYS: Final = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def __init__(self, package: str | None = None):
        self.loaded = False
        self._package_name = package
        self.global_tasklist: Deque[Any] = collections.deque()
        self.current_tasklist: Deque[Any] = collections.deque()
        self.vault = Vault(getpass("Vault password: "))

    def load(self) -> None:
        """Invoke the _load_package() function on _package_name (if initiliazed)."""
        if not self.loaded:
            if self._package_name:
                _load_package(self._package_name)
        self.loaded = True

    def register(self, task: type[_TaskT]) -> type[_TaskT]:
        """Decorator used to take a _Task class and add it to the global_tasklist.

        Parameters:
            task (_TaskT): The _Task class being defined

        Returns:
            _TaskT: The unchanged but now registered _Task
        """
        i = 0
        for i, set_task in enumerate(self.global_tasklist):
            if task.TIME < set_task.TIME:
                break
        self.global_tasklist.insert(i, task)
        logger.info(f"Registered {task.NAME} ({task.TIME}) to global tasklist.")
        return task

    def create_daily_tasklist(self) -> None:
        """Decorator used to take a _Task class and add it to the global_tasklist.

        Parameters:
            task (_TaskT): The _Task class being defined
        """
        self.current_tasklist = collections.deque()
        today = datetime.today().astimezone(timezone("EST"))
        weekday = TaskRegistry.WEEKDAYS[today.weekday()]
        tasks = []
        for task in self.global_tasklist:
            if task.DAY != 0 and task.DAY is not today.day:
                continue
            if task.DAYS and weekday not in task.DAYS:
                continue
            self.add_daily_tasklist(task())
            tasks.append(task.NAME)
        logger.info(f"Added {', '.join(tasks)} to daily tasklist.")

    def add_daily_tasklist(self, task: type[_TaskT]) -> None:
        """Insert a daily task into the current tasklist.

        Parameters:
            task (_TaskT): The task to add to the list
        """
        i = 0
        for i, set_task in enumerate(self.current_tasklist):
            if task.TIME < set_task.TIME:
                break
        self.current_tasklist.insert(i, task)

    async def execute_daily_tasks(self) -> None:
        """Check if it is time to execute a task, and then execute."""
        now = datetime.now()
        current_time = timedelta(
            hours=now.hour,
            minutes=now.minute,
            seconds=now.second,
        )
        if self.current_tasklist:
            if self.current_tasklist[0].TIME < current_time:
                task = self.current_tasklist.popleft()
                logger.info(f"Executing {task.NAME}.")
                try:
                    await task.execute(self.vault)
                    logger.info(f"{task.NAME} executed.")
                except Exception as e:
                    notifier = PushbulletNotifier(self.vault.load_entries()["pushbullet-key"])
                    notifier.send_notification(f"Task {task.NAME} failed to execute.", repr(e))
                    logger.info(f"{task.NAME} failed to execute, notified.")

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


Tasks = TaskRegistry(package="Automated_Tasker.tasks")
