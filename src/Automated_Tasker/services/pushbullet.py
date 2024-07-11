from __future__ import annotations

from pushbullet import Pushbullet


class PushbulletNotifier:
    """A class for performing pushbullet operations.

    Requires the PushBullet API key under the vault entry tag 'pushbullet-key'"""

    def __init__(self, api_key):
        self.pb = Pushbullet(api_key)

    def send_notification(self, title, message):
        """Send a simple notification by pushing with pushbullet.

        Parameters:
            title(str): The title of the notification
            message(str): The content of the notification
        """
        self.pb.push_note(title, message)
