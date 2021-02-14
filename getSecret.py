import subprocess
import shlex
import json
from google.cloud import secretmanager
import google.auth
from typing import Dict, Union


class getSecret():
    """Class gets secret from Secret Manager.
    # TODO too slow, therefore secrets are saved within a pickle file in the application.
    """

    def __init__(self) -> None:
        self.project_number: int = None

    def get_project_number(self) -> int:
        """Determines current project number"""

        # Load current project_id
        credentials, project_id = google.auth.default()

        project_number_command = f"""gcloud projects describe {project_id} \
                                        --format='value(projectNumber)'"""
        project_output = subprocess.check_output(
            shlex.split(project_number_command))

        self.project_number = json.loads(project_output)

    def get_secret(self, secret_name: str) -> Union[int, str]:
        """Loads secret with a given name from Secret Manager"""

        client = secretmanager.SecretManagerServiceClient()
        # Access the secret version.
        response = client.access_secret_version(
            request={"name": f"projects/{self.project_number}/secrets/{secret_name}/versions/1"})
        return response.payload.data.decode("UTF-8")

    def __call__(self, secret_name: str = "toggle_key") -> Dict:
        self.get_project_number()
        return {
            'token': self.get_secret(secret_name),
            'user_agent': 'load_app',
            'workspace_id': 2049184  # Aliz workspace
        }
