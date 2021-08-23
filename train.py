import atexit
from google.cloud import storage
from Calendar2Toggl import Calender2Toggl
from ProjectPredictor import ProjectPredictor
from DataStorer import DataStorer


def download_credentials():
    client = storage.Client(project="norbert-liki-sandbox")
    bucket = client.get_bucket("norbert-liki-aliz")
    blob = storage.Blob("token.pickle", bucket)
    blob.download_to_filename("token.pickle")


def kill_vm():
    """
    If we are running inside a GCE VM, kill it.
    """
    # based on https://stackoverflow.com/q/52748332/321772
    import json
    import logging
    import requests

    # get the token
    r = json.loads(
        requests.get("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                     headers={"Metadata-Flavor": "Google"})
            .text)

    token = r["access_token"]

    # get instance metadata
    # based on https://cloud.google.com/compute/docs/storing-retrieving-metadata
    project_id = requests.get("http://metadata.google.internal/computeMetadata/v1/project/project-id",
                              headers={"Metadata-Flavor": "Google"}).text

    name = requests.get("http://metadata.google.internal/computeMetadata/v1/instance/name",
                        headers={"Metadata-Flavor": "Google"}).text

    zone_long = requests.get("http://metadata.google.internal/computeMetadata/v1/instance/zone",
                             headers={"Metadata-Flavor": "Google"}).text
    zone = zone_long.split("/")[-1]

    # shut ourselves down
    logging.info("Calling API to delete this VM, {zone}/{name}".format(zone=zone, name=name))

    requests.delete("https://www.googleapis.com/compute/v1/projects/{project_id}/zones/{zone}/instances/{name}"
                    .format(project_id=project_id, zone=zone, name=name),
                    headers={"Authorization": "Bearer {token}".format(token=token)})


def train():
    ctt = Calender2Toggl(160 * 4)

    toggl_pjs = ctt._get_toggl_projects()
    te = ctt._query_existing_toggl_items()
    ce = ctt._get_calendar_events()
    print("Events are loaded.")

    pp = ProjectPredictor()
    train, test = pp.preprocess_data(ce, te, toggl_pjs)
    pp.fit(train, test, finetune=True)
    print("Training finished, starting saving.")

    ds = DataStorer()
    ds.store(pp)
    print("Model saved, shutting down.")

    atexit.register(kill_vm)


if __name__ == "__main__":
    try:
        download_credentials()
        train()
    except Exception as e:
        print(e)
        atexit.register(kill_vm)
