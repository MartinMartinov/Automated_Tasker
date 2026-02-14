from __future__ import annotations

from Automated_Tasker.tasklist import Tasks, DAY_START, DAY_END
from Automated_Tasker.utils.vault import Vault
from Automated_Tasker.services.pushbullet import PushbulletNotifier

import random
import nltk
from datetime import datetime, timedelta
from nltk.corpus import wordnet
from datetime import timedelta

from typing import List

import logging

logger = logging.getLogger(__name__)

# Download necessary datasets
nltk.download('wordnet', quiet=True)

def get_words(target_date: datetime = datetime.now(), count: int = 8, category='mixed', mode='random'):
    seed_value = int(target_date.strftime("%Y%m%d"))
    random.seed(seed_value)

    mapping = {
        'noun': wordnet.NOUN,
        'adj': wordnet.ADJ,
        'adv': wordnet.ADV,
        'verb': wordnet.VERB,
    }

    words_out = []

    if category in mapping:
        active_cats = [mapping[category]]
    elif mode == 'random':
        active_cats = [random.choice(list(mapping.values()))]
    elif mode == 'even':
        cat_list = list(mapping.values())
        active_cats = [cat_list[i % len(cat_list)] for i in range(count)]
    else:
        return words_out

    for cat_type in active_cats:
        needed = count if len(active_cats) == 1 else 1
        
        all_synsets = list(wordnet.all_synsets(cat_type))
        selected = random.sample(all_synsets, needed)
        
        for syn in selected:
            words_out.append(syn.lemmas()[0].name().replace('_', ' '))

    return words_out

@Tasks.register
class MorningWordGame:
    """A task for pushing today's calendar events and tasks through PushBullet."""

    NAME: str = "MorningWordGame"
    TIME: timedelta = timedelta(hours=DAY_START[0], minutes=DAY_START[1])
    DAYS: List[str] = []
    DAY: int = 0

    async def execute(self, vault: Vault | None = None):
        """Get all of today's events and tasks from Google Calendar and push it to pushbullet.

        Parameters:
            vault (Vault | None): The vault with the pushbullet token and Google Calendar creds
        """
        calendar = GoogleCalendarClient(vault)
        notifier = PushbulletNotifier(vault.load_entries()["pushbullet-key"])
        notifier.send_notification("Yesterday's Words", "\n".join(get_words(datetime.now()-timedelta(hours=24))))

@Tasks.register
class NightWordGame:
    """A task for pushing today's calendar events and tasks through PushBullet."""

    NAME: str = "NightWordGame"
    TIME: timedelta = timedelta(hours=DAY_END[0], minutes=DAY_END[1])
    DAYS: List[str] = []
    DAY: int = 0

    async def execute(self, vault: Vault | None = None):
        """Get all of today's events and tasks from Google Calendar and push it to pushbullet.

        Parameters:
            vault (Vault | None): The vault with the pushbullet token and Google Calendar creds
        """
        calendar = GoogleCalendarClient(vault)
        notifier = PushbulletNotifier(vault.load_entries()["pushbullet-key"])
        notifier.send_notification("Today's Words", "\n".join(get_words()))