# ReadMe

Automatic loading of Google Calendar events to Toggl using trigger events coming from Cloud Schedule via Pub/Sub to a Cloud Functions service.

## How to setup

1. Generate Calender API  and Toggl credentials using [generate_credentials.py](generate_credentials.py).
2. Enable required Google APIs.
3. Create Pub/Sub topic.
4. Deploy Cloud Function.
5. Deploy a scheduled job in Cloud Scheduler.

### 3. Enable APIs

```
gcloud services enable pubsub.googleapis.com \
    cloudfunctions.googleapis.com \
    cloudscheduler.googleapis.com \
    calendar-json.googleapis.com \
    servicemanagement.googleapis.com
```

### 4. Create Pub/Sub topic

```
gcloud pubsub topics create calendar
```

## Deploy code to Cloud Functions

```
gcloud functions deploy calendar_to_toggl \
    --runtime python37 \
    --trigger-topic calendar \
    --allow-unauthenticated \
    --memory 512MB
```

## Create Cloud Scheduler

```
gcloud scheduler jobs create pubsub calendar_trigger \
    --schedule "0 10-22/4 * * 1-5" \
    --topic=calendar \
    --message-body "4" \
    --time-zone "Europe/Budapest"
```

## Next steps
- [ ] Automate deployment
- [ ] Store Toggl project infos in Datastore since querying it requires admin rights
- [x] Avoid duplicate time entries. (Currently based on event summary)

## Additional how to-s
### Generate requirements.txt from Pipfile

```
pipenv lock -r > requirements.txt
```

### Store  API key in Secret Manager


First create the secret version
```
printf "YOUR SECRET" | gcloud secrets create toggl_key --data-file=-
```

Then add methods from [getSecret.py](getSecret.py) to [main.py](main.py).