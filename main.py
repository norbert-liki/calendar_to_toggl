import base64
import datetime
import pickle
import re
from googleapiclient.discovery import build
from toggl.api_client import TogglClientApi
from typing import List


class Calender2Toggle():
    def __init__(self) -> None:
        self.look_back_hours: int = 1
        self.time_from: str = None  # Format 2021-02-13T08:27:13.772498Z
        self.time_to: str = None

    def set_hours_param(self, event=None) -> int:
        """ Sets look_back_hours parameter from Pub/Sub trigger message"""
        try:
            if 'data' in event:
                self.look_back_hours = int(
                    base64.b64decode(event['data']).decode('utf-8'))
        except:
            pass

    def calculate_from_to_timestamps(self) -> None:
        """Calculates date ranges within calendar events will be querried."""
        now = datetime.datetime.utcnow()
        time_to = now.isoformat() + 'Z'  # 'Z' indicates UTC time
        time_from = (now - datetime.timedelta(hours=self.look_back_hours)).isoformat() + \
            'Z'  # 'Z' indicates UTC time
        self.time_from, self.time_to = time_from, time_to

    def search_project_code(self, event: dict, projects: List[dict]) -> int:
        """1. Looks for project codes in calendar events
        2. Looks up found project codes to get toggle project_id

        Args:
            event (dict): single calendar event
            projects List[dict]: Toggle projects in a list

        Returns:
            project_id (int): matched toggle project_id
        """
        event_desc = event.get('description')

        if event_desc:
            PROJECT_PATTERN = r'\(\w+-\d+\)|([eE]ngineering)|(HR)|(PMO)'
            try:
                found_project_name = re.search(
                    PROJECT_PATTERN, event_desc).group()
                return next((p['id'] for p in projects if found_project_name in p['name']))
            except AttributeError:
                pass

    def __call__(self, event=None, context=None) -> None:
        """Uploads calendar events to toggle within x last hours where x comes
        from either Pub/Sub message or default 1.

        Args:
            event (dict):  The dictionary with data specific to this type of
                event. The `data` field contains the PubsubMessage message.
            context (google.cloud.functions.Context): The Cloud Functions event
                metadata.
        """

        # Setting lookback timeframe
        self.set_hours_param(event)
        self.calculate_from_to_timestamps()

        # Load credentials
        try:
            with open('token.pickle', 'rb') as token:
                creds, toogle_settings = pickle.load(token)
        except FileNotFoundError:
            print("Credentials does not exist. Please genrate token.pickle first.")

        service = build('calendar', 'v3', credentials=creds,
                        cache_discovery=False)
        toggle_client = TogglClientApi(toogle_settings)
        projects = toggle_client.get_projects().json()

        # Call the Calendar API
        events_result = service.events().list(calendarId='primary',
                                              timeMin=self.time_from, timeMax=self.time_to,
                                              maxResults=None, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        # Load events to toogle
        if not events:
            print(
                f'No events found between {self.time_from} and {self.time_to}.')
        for event in events:
            if event['start'].get('dateTime'):  # Exclude all day events
                new_entry = {
                    "time_entry": {
                        "description": event['summary'],
                        "tags": [],
                        "duration": None,
                        "start": event['start'].get('dateTime'),
                        "stop": event['end'].get('dateTime'),
                        "pid": self.search_project_code(event, projects),
                        "created_with": "calendar2toggle_app"
                    }
                }
                toggle_client.create_time_entry(new_entry)


def calendar_to_toggle(event=None, context=None):
    Calender2Toggle()(event, context)


if __name__ == '__main__':
    calendar_to_toggle()
