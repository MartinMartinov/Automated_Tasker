from __future__ import annotations

from Automated_Tasker.utils.vault import Vault

from tempfile import TemporaryDirectory
from pathlib import Path
from pytz import timezone
from collections.abc import Iterator
from typing import Any

from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request


class GoogleCalendarClient:
    """A class for accessing Google Calendar using the oauth2 API and Google Cloud Projects.

    Requires the Google Cloud Project secret token for the account under the vault entry tag 'google-secrets'.
    This will create and use the google-creds entry for your temporary access and refresh tokens."""

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self, vault: Vault):
        self.service = None
        self.vault = vault
        self.authenticate()

    def authenticate(self) -> None:
        """Use the default Google OAuth flow using a tempdir (as its all file based :/)."""
        with TemporaryDirectory() as secrets_exchange:
            temp_dir = Path(secrets_exchange)
            cred_filename = temp_dir / "credentials.json"
            secret_filename = temp_dir / "client_secret_google_calendar.json"

            creds = self.vault.load_entries().get("google-creds")
            if creds:
                open(cred_filename, "wt").write(creds)
                creds = Credentials.from_authorized_user_file(cred_filename, scopes=self.SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    open(secret_filename, "wt").write(self.vault.load_entries().get("google-secrets"))
                    flow = InstalledAppFlow.from_client_secrets_file(secret_filename, scopes=self.SCOPES)
                    creds = flow.run_local_server(port=0)
                self.vault.store_entry("google-creds", creds.to_json())

            self.service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    def get_today_startstop(self) -> tuple[datetime, datetime]:
        """Get today's start and stop (in EST timezone), to query Google Calendar with.

        Returns:
            datetime: Today (EST) start time
            datetime: Today (EST) stop time
        """
        now = datetime.now()
        diff = timezone("UTC").localize(now) - timezone("EST").localize(now).astimezone(timezone("UTC"))
        start = (
            now
            - timedelta(
                hours=now.hour,
                minutes=now.minute,
                seconds=now.second,  # Catch all-day events and tasks
                milliseconds=now.microsecond / 1000,
            )
            - diff
        ).isoformat() + ".000Z"
        stop = (datetime(now.year, now.month, now.day, 23, 59, 59) - diff).isoformat() + ".000Z"
        return start, stop

    def get_todays_events(self) -> Iterator[dict[Any]]:
        """Get today's Google Calendar events.

        Yields:
            Iterator[str]: The events returned by Google Calendar in chronological sequence
        """
        start, stop = self.get_today_startstop()
        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=start,
                    timeMax=stop,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
        except HttpError:
            return None

        events = events_result.get("items", [])

        for event in events:
            if "dateTime" in event["start"]:
                yield event
