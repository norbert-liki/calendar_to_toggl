import base64
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from toggl.api_client import TogglClientApi
from typing import Tuple


# MODFY THIS
TOGGLE_SETTINGS = {
    'token': "ADD YOUR TOKEN HERE",
    'user_agent': 'load_app',
    'workspace_id': 2049184  # Aliz workspace
}


def get_hours_param(event) -> int:
    """ Gets hour parameter from Pub/Sub trigger message"""
    if 'data' in event:
        return int(base64.b64decode(event['data']).decode('utf-8'))
    else:
        return 1


def calculate_from_to_timestamps(hours: int) -> Tuple[str, str]:
    """Calculates date ranges within calendar events will be querried.

    Args:
        hours (int): Number of hours to look back

    Returns:
      (time_from, time_to)  : Date ranges in format: 2021-02-13T08:27:13.772498Z
    """
    now = datetime.datetime.utcnow()
    time_to = now.isoformat() + 'Z'  # 'Z' indicates UTC time
    time_from = (now - datetime.timedelta(hours=hours)).isoformat() + \
        'Z'  # 'Z' indicates UTC time
    return (time_from, time_to)


def calendar_to_toggle(event, context) -> None:
    """Uploads events from the last hour to toggle.

    Args:
         event (dict):  The dictionary with data specific to this type of
         event. The `data` field contains the PubsubMessage message.
         context (google.cloud.functions.Context): The Cloud Functions event
         metadata. The `event_id` field contains the Pub/Sub message ID. The
         `timestamp` field contains the publish time.
    """

    # Load credentials
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    else:
        print("Credentials does not exist. Please genrate token.pickle first.")

    service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
    toggle_client = TogglClientApi(TOGGLE_SETTINGS)

    # Call the Calendar API
    time_from, time_to = calculate_from_to_timestamps(get_hours_param(event))

    events_result = service.events().list(calendarId='primary',
                                          timeMin=time_from, timeMax=time_to,
                                          maxResults=None, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print(f'No events found between {time_from} and {time_to}.')
    for event in events:
        if event['start'].get('dateTime'):  # Exclude all day events
            new_entry = {
                "time_entry": {
                    "description": event['summary'],
                    "tags": [],
                    "duration": None,
                    "start": event['start'].get('dateTime'),
                    "stop": event['end'].get('dateTime'),
                    "pid": None,
                    "created_with": "calendar2toggleapp"
                }
            }

            toggle_client.create_time_entry(new_entry)


if __name__ == '__main__':
    calendar_to_toggle()
