# ReadMe

Automatic loading of Google Calendar events to toggle using trigger events coming from Cloud Schedule via Pub/Sub to a Cloud Functions service.

## How to setup

1. Generate Calender API credentials using [generate_credentials.py](generate_credentials.py).
2. Add your toggle API token to [main.py](main.py).
3. Enable required Google APIs.
4. Create Pub/Sub topic.
5. Deploy Cloud Function.
6. Deploy a scheduled job in Cloud Scheduler.

### 3. Enable APIs

```
gcloud services enable pubsub.googleapis.com \
    cloudfunctions.googleapis.com \
    cloudscheduler.googleapis.com \
    calendar-json.googleapis.com
```

### 4. Create Pub/Sub topic

```
gcloud pubsub topics create calendar
```

## Deploy code to Cloud Functions

```
gcloud functions deploy calendar_to_toggle --runtime python37 --trigger-topic calendar --allow-unauthenticated --memory 128MB
```

## Create Cloud Scheduler

```
gcloud scheduler jobs create pubsub calendar_trigger --schedule "0 * * * 1,2,3,4,5" --topic=calendar --message-body "1"
```


### Generate requirements.txt from Pipfile

```
pipenv lock -r > requirements.txt
```