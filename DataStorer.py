from google.cloud import datastore
from datetime import datetime
from ProjectPredictor import ProjectPredictor
import dill


class DataStorer:
    def __init__(self) -> None:
        self.client = datastore.Client()

    def store(self, model: ProjectPredictor) -> None:
        """Stores an input pipeline object as byte string in Datastore.

        Args:
            model (ProjectPredictor): scikit-learn pipeline object.
        """

        with open("tmp.pkl", "wb") as f:
            dill.dump(model, f)

        with open("tmp.pkl", "rb") as f:
            pipe = f.read()

        entity = datastore.Entity(key=self.client.key("model"), exclude_from_indexes=["model"])
        entity.update({
            'model': pipe,
            'date': datetime.now()
        })
        self.client.put(entity)

    def fetch(self) -> ProjectPredictor:
        """Ready saved byte model string from Datastore.

        Returns:
            ProjectPredictor: Decoded pipeline object.
        """

        query = self.client.query(kind='model')
        query.order = ['-date']
        ds_model = list(query.fetch(limit=1))[0]
        return dill.loads(ds_model['model'])
