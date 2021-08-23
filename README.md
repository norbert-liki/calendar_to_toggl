# ReadMe

Automatic loading of Google Calendar events to Toggl using trigger events coming from Cloud Scheduler via Pub/Sub to a Cloud Functions service.
The solution has 2 main parts:

1. Function that loads calendar events and predicts the project for each event
2. Function that retrains prediction model periodically


## 1. Setting up loading function 

1. Generate Calender API  and Toggl credentials using [generate_credentials.py](generate_credentials.py).
2. Enable required Google APIs.
3. Create Pub/Sub topic.
4. Deploy Cloud Function.
5. Deploy a scheduled job in Cloud Scheduler.

### Enable APIs

```
gcloud services enable pubsub.googleapis.com \
    cloudfunctions.googleapis.com \
    cloudscheduler.googleapis.com \
    calendar-json.googleapis.com \
    servicemanagement.googleapis.com
```

### Create Pub/Sub topic

```
gcloud pubsub topics create calendar
```

### Deploy code to Cloud Functions

```
gcloud functions deploy calendar_to_toggl \
    --runtime python38 \
    --trigger-topic calendar \
    --memory 512MB
```

### Create Cloud Scheduler

```
gcloud scheduler jobs create pubsub calendar_trigger \
    --schedule "0 10-22/4 * * 1-5" \
    --topic=calendar \
    --message-body "4" \
    --time-zone "Europe/Budapest"
```

## 2. Setting up retraining pipeline


**From the retrainer_cf folder issue the following commands:**


### Copy the pickled credentials to a cloud storage bucket and add it to the [retrainer_cf/main.py](./retrainer_cf/main.py)


### Create Pub/Sub topic

```
gcloud pubsub topics create calendar_retrain
```

### Deploy code to Cloud Functions

```
gcloud functions deploy calendar_retrain \
    --runtime python38 \
    --trigger-topic calendar_retrain \
    --memory 128MB
```

### Create Cloud Scheduler

```
gcloud scheduler jobs create pubsub calendar_retraining_trigger \
    --schedule "0 22 * * 1-5" \
    --topic=calendar_retrain \
    --message-body "0" \
    --time-zone "Europe/Budapest"
```





## Next steps
- [ ] Automate deployment
- [ ] Store Toggl project infos in Datastore since querying it requires admin rights

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


### Run retraining job

From the retrainer_cf folder issue:

```
gcloud compute instances create calendar-retrainer \
    --image-family=cos-89-lts \
    --image-project=cos-cloud \
    --machine-type=e2-medium-2 \
    --scopes cloud-platform \
    --container-image=gcr.io/norbert-liki-sandbox/calendar-trainer:latest \
    --zone us-central1-a \
    --preemptible
```

## Building and testing docker container for retraining
```sh
gcloud builds submit . -t gcr.io/norbert-liki-sandbox/calendar-trainer:latest --timeout=9999
```

Run the container locally to test it

```sh
docker run --rm -v ~/.config/gcloud:/.config/gcloud -e GOOGLE_APPLICATION_CREDENTIALS=/.config/gcloud/application_default_credentials.json gcr.io/norbert-liki-sandbox/calendar-trainer:latest
```