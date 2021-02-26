import base64
import datetime
import pickle
import re
from googleapiclient.discovery import build
from toggl.api_client import TogglClientApi
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlencode
from typing import Dict, List
from pytz import timezone


class Calender2Toggl():
    def __init__(self) -> None:
        self.look_back_hours: int = 1
        self.time_from: str = None  # Format 2021-02-13T08:27:13.772498Z
        self.time_to: str = None
        self.timezone: timezone = timezone("Europe/Budapest")

        # Load credentials
        try:
            with open('token.pickle', 'rb') as token:
                self.creds, self.toogle_settings = pickle.load(token)
        except FileNotFoundError:
            print("Credentials does not exist. Please genrate token.pickle first.")

    def _set_hours_param(self, event=None) -> int:
        """ Sets look_back_hours parameter from Pub/Sub trigger message"""
        try:
            if 'data' in event:
                self.look_back_hours = int(
                    base64.b64decode(event['data']).decode('utf-8'))
        except Exception:
            pass

    def _calculate_from_to_timestamps(self) -> None:
        """Calculates date ranges within calendar events will be querried."""
        now = datetime.datetime.utcnow()
        time_to = now.isoformat() + 'Z'  # 'Z' indicates UTC time
        time_from = (now - datetime.timedelta(hours=self.look_back_hours)).isoformat() + \
            'Z'  # 'Z' indicates UTC time
        self.time_from, self.time_to = time_from, time_to

    def _search_project_code(self, cal_event: dict, projects: List[dict]) -> int:
        """1. Looks for project codes in calendar events
        2. Looks up found project codes to get toggl project_id

        Args:
            event (dict): single calendar event
            projects List[dict]: Toggl projects in a list

        Returns:
            project_id (int): matched toggl project_id
        """
        cal_event_desc = cal_event.get('description')

        if cal_event_desc:
            PROJECT_PATTERN = r'\(\w+-\d+\)|([eE]ngineering)|(HR)|(PMO)'
            try:
                found_project_name = re.search(
                    PROJECT_PATTERN, cal_event_desc).group()
                return next((p['id'] for p in projects if found_project_name in p['name']))
            except AttributeError:
                pass

    def _query_existing_toggl_items(self):
        """Query existing time entries in toggl to avoid duplicates"""

        auth = HTTPBasicAuth(self.toogle_settings['token'], 'api_token')
        end_tm = datetime.datetime.now().astimezone(self.timezone).replace(microsecond=0)
        start_tm = end_tm - datetime.timedelta(hours=self.look_back_hours + 1)

        url_schema = {"start_date": start_tm.isoformat(), "end_date": end_tm.isoformat()}
        url = "https://api.track.toggl.com/api/v8/time_entries?" + urlencode(url_schema)

        return requests.get(url, auth=auth).json()

    def _check_event_load_status(self, cal_event: Dict, toggl_items: Dict) -> bool:
        """Checks whether an event is an all day event and it is already loaded to toggl
        or if it contains a description that should not be loaded."""

        all_day_flag = cal_event['start'].get('dateTime') is not None
        loaded_flag = len([time_entry for time_entry in toggl_items if cal_event.get(
            "summary") == time_entry.get("description")]) == 0

        ouf_of_office = cal_event.get("eventType") != "outOfOffice" or False

        DESC_FILTER_PAT = r'([oO]ut of office)|(ooo)'

        try:
            found_project_name = re.search(
                DESC_FILTER_PAT, cal_event.get("summary")).group()
            filter_desc = len(found_project_name) == 0
        except AttributeError:
            filter_desc = True

        return (all_day_flag and loaded_flag and filter_desc and ouf_of_office)

    def __call__(self, event=None, context=None) -> None:
        """Uploads calendar events to toggl within x last hours where x comes
        from either Pub/Sub message or default 1.

        Args:
            event (dict):  The dictionary with data specific to this type of
                event. The `data` field contains the PubsubMessage message.
            context (google.cloud.functions.Context): The Cloud Functions event
                metadata.
        """

        # Setting lookback timeframe
        self._set_hours_param(event)
        self._calculate_from_to_timestamps()

        service = build('calendar', 'v3', credentials=self.creds,
                        cache_discovery=False)
        toggl_client = TogglClientApi(self.toogle_settings)
        projects = toggl_client.get_projects().json()
        recorded_time_entries = self._query_existing_toggl_items()

        # Call the Calendar API
        cal_events_result = service.events().list(calendarId='primary',
                                                  timeMin=self.time_from, timeMax=self.time_to,
                                                  maxResults=None, singleEvents=True,
                                                  orderBy='startTime').execute()
        cal_events = cal_events_result.get('items', [])

        # Load events to toogle
        if not cal_events:
            print(
                f'No events found between {self.time_from} and {self.time_to}.')
        for cal_event in cal_events:
            if self._check_event_load_status(cal_event, recorded_time_entries):
                cal_event_start = datetime.datetime.fromisoformat(cal_event['start'].get('dateTime'))
                cal_event_end = datetime.datetime.fromisoformat(cal_event['end'].get('dateTime'))

                new_entry = {
                    "time_entry": {
                        "description": cal_event['summary'],
                        "tags": [],
                        "duration": (cal_event_end - cal_event_start).seconds,
                        "start": cal_event['start'].get('dateTime'),
                        "stop": cal_event['end'].get('dateTime'),
                        "pid": self._search_project_code(cal_event, projects),
                        "created_with": "calendar2toggl_app"
                    }
                }
                toggl_client.create_time_entry(new_entry)


def calendar_to_toggl(event=None, context=None):
    Calender2Toggl()(event, context)


if __name__ == '__main__':
    calendar_to_toggl()
