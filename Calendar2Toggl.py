import pandas as pd
import base64
import datetime
import pickle
from googleapiclient.discovery import build
from toggl.api_client import TogglClientApi
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlencode
from typing import Dict, List
from pytz import timezone


class Calender2Toggl():
    def __init__(self, look_back_hours: int = 8, event=None) -> None:
        self.look_back_hours = look_back_hours
        self.time_from: str = None  # Format 2021-02-13T08:27:13.772498Z
        self.time_to: str = None
        self.timezone: timezone = timezone("Europe/Budapest")

        # Load credentials
        try:
            with open('token.pickle', 'rb') as token:
                self.creds, self.toogle_settings = pickle.load(token)
                self.toggl_client = TogglClientApi(self.toogle_settings)
        except FileNotFoundError:
            print("Credentials does not exist. Please genrate token.pickle first.")

        # Setting lookback timeframe
        self._set_hours_param(event)
        self._calculate_from_to_timestamps()

    def _set_hours_param(self, event=None):
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

    def _get_toggl_projects(self):
        return self.toggl_client.get_projects().json()

    def _get_calendar_events(self) -> List[Dict]:
        """Querries events from Google Calendar

        Returns:
            event [List[Dict]]: Google Calendar events as list of dicts.
        """

        service = build('calendar', 'v3', credentials=self.creds,
                        cache_discovery=False)

        cal_events_result = service.events().list(calendarId='primary',
                                                  timeMin=self.time_from, timeMax=self.time_to,
                                                  maxResults=None, singleEvents=True,
                                                  orderBy='startTime').execute()
        return cal_events_result.get('items', [])

    def _query_existing_toggl_items(self) -> List[Dict]:
        """Query existing time entries in toggl to avoid duplicates"""

        auth = HTTPBasicAuth(self.toogle_settings['token'], 'api_token')
        end_tm = datetime.datetime.now().astimezone(self.timezone).replace(microsecond=0)
        start_tm = end_tm - datetime.timedelta(hours=self.look_back_hours + 3)

        url_schema = {"start_date": start_tm.isoformat(), "end_date": end_tm.isoformat()}
        url = "https://api.track.toggl.com/api/v8/time_entries?" + urlencode(url_schema)

        return requests.get(url, auth=auth).json()

    @staticmethod
    def load_event(row, toggl_client):
        """Parses and loads events to toggl in the right format.
        """
        try:
            new_entry = {
                "time_entry": {
                    "description": row['description'],
                    "tags": [],
                    "duration": (row['end_tm'] - row['start_tm']).seconds,
                    "start": row['start_tm'].isoformat(),
                    "stop": row['end_tm'].isoformat(),
                    "pid": row['id'],
                    "created_with": "calendar2toggl_app"
                }
            }

            toggl_client.create_time_entry(new_entry)
            print(f"Event loaded: {row['summary']}")
            return 'uploaded'
        except Exception as e:
            print(f"Failed to load: {row}")
            print(e)
            return 'failed to upload'

    def load_to_toggl(self, calendar_events: pd.DataFrame) -> None:
        """Uploads calendar events to toggl

        Args:
            calendar_events (pd.DataFrame): dataframe containing events to be uploaded
        """

        # Load events to toogle
        if calendar_events.shape[0] > 0:
            calendar_events.apply(self.load_event, axis=1, args=[self.toggl_client])
        else:
            print(
                f'No events found between {self.time_from} and {self.time_to}.')
