# ReadMe

Automatic loading of Google Calendar events to toggle using trigger events coming from Cloud Schedule via Pub/Sub to a Cloud Functions service.

## How to setup

1. Generate Calender API  and Toggle credentials using [generate_credentials.py](generate_credentials.py).
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
gcloud functions deploy calendar_to_toggle \
    --runtime python37 \
    --trigger-topic calendar \
    --allow-unauthenticated \
    --memory 128MB
```

## Create Cloud Scheduler

```
gcloud scheduler jobs create pubsub calendar_trigger \
    --schedule "0 5-22 * * 1-5" \
    --topic=calendar \
    --message-body "1" \
    --time-zone "Europe/Budapest"
```

## Next steps
- [ ] Automate deployment
- [ ] Store toggle project infos in Datastore since querying it requires admin rights


## Additional how to-s
### Generate requirements.txt from Pipfile

```
pipenv lock -r > requirements.txt
```

### Store Toggle API key in Secret Manager


First create the secret version
```
printf "YOUR SECRET" | gcloud secrets create toggle_key --data-file=-
```

Then add methods from [getSecret.py](getSecret.py) to [main.py](main.py).