from Calendar2Toggl import Calender2Toggl
from ProjectPredictor import ProjectPredictor
from DataStorer import DataStorer


def calendar_to_toggl(event=None, context=None):
    """Function that executes the loading process to toggl.

    Args:
        event ([type], optional): Pub/Sub trigger message. Defaults to None.
        context ([type], optional): Cloud Functions context. Defaults to None.
    """
    c2t = Calender2Toggl(event=event)
    te = c2t._query_existing_toggl_items()
    ce = c2t._get_calendar_events()
    to_pred = ProjectPredictor().preprocess_for_pred(ce, te)

    if to_pred.shape[0] > 0:
        ds = DataStorer()
        model = ds.fetch()
        preds = model.predict(to_pred)

        c2t.load_to_toggl(preds)


if __name__ == '__main__':
    calendar_to_toggl()
