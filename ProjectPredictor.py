from typing import Dict, List, Tuple
import pandas as pd
import sys
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.pipeline import Pipeline
from pycaret.classification import setup, predict_model, save_model, create_model, finalize_model, tune_model
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import make_column_transformer
from sklearn.compose import make_column_selector


class ProjectPredictor:
    def __init__(self) -> None:
        pass

    @staticmethod
    def attendee_count_(row):
        if isinstance(row, list):
            return len(row)
        else:
            return 0

    @staticmethod
    def attendee_list_(row):
        if isinstance(row, list):
            return ", ".join(user.get("email") for user in row)
        else:
            return ""

    @staticmethod
    def attendee_n_(row, n):
        if isinstance(row, list) and len(row) > n:
            return row[n].get("email")
        else:
            return ""

    @staticmethod
    def get_my_response(row):
        try:
            return [i.get("responseStatus") for i in row if i.get("self")][0]
        except TypeError:
            return "accepted"

    def convert_toggl_entries(self, toggl_entries: List[Dict]) -> pd.DataFrame:
        """Preprocesses input toggle entries to a DataFrame.

        Args:
            toggl_entries (List[Dict]): list of toggl entries

        Returns:
            pd.DataFrame: Parsed entries as a DataFrame
        """
        if not toggl_entries:
            return (pd.DataFrame({'start_tm': "2021-03-15T11:00:00+01:00", "description": "na", "duration": "-1", "pid": -1},
                                 index=[0])
                    .assign(start_tm=lambda x: pd.to_datetime(x.start_tm)))

        toggl_df = (pd.DataFrame(toggl_entries)
                    .assign(start_tm=lambda x: pd.to_datetime(x.start),
                            end_tm=lambda x: pd.to_datetime(x.stop),
                            )
                    .filter(["start_tm", "description", "duration", "pid"])
                    )
        if "pid" not in toggl_df.columns:
            toggl_df['pid'] = -1
        return toggl_df

    def preprocess_data(self, calendar_events: List[Dict], toggl_entries: List[Dict], toggl_projects: List[Dict]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Preprocesses and joins input sources, splits them to train and test sets.

        Args:
            calendar_events (List[Dict]): Google Calendar Events
            toggl_entries (List[Dict]): Existing toggle project entries
            toggl_projects (List[Dict]): All toggle projects

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: train / test DataFrames
        """

        self.toggl_pjs = pd.DataFrame(toggl_projects).filter(["id", "name"])

        te_df = self.convert_toggl_entries(toggl_entries)

        ce_df = pd.DataFrame(calendar_events)

        train_df = (
            ce_df.filter(["start", "end", "attendees", "creator", "summary", "eventType", "colorId", "description"])
            .fillna({"colorId": '99'})
            .assign(start_tm=pd.to_datetime(ce_df.start.apply(lambda x: x.get("dateTime"))),
                    end_tm=pd.to_datetime(ce_df.end.apply(lambda x: x.get("dateTime"))),
                    first_attendee=ce_df.attendees.apply(self.attendee_n_, n=0),
                    second_attendee=ce_df.attendees.apply(self.attendee_n_, n=1),
                    third_attendee=ce_df.attendees.apply(self.attendee_n_, n=2),
                    fourth_attendee=ce_df.attendees.apply(self.attendee_n_, n=3),
                    fifth_attendee=ce_df.attendees.apply(self.attendee_n_, n=4),
                    attendee_list=ce_df.attendees.apply(self.attendee_list_),
                    attendee_cnt=ce_df.attendees.apply(self.attendee_count_),
                    creator=ce_df.creator.apply(lambda x: x.get("email")),
                    start_hour=(lambda x: x.start_tm.dt.hour),
                    text=lambda x: x.summary + " " + x.description.fillna(""),
                    description=(lambda x: x.summary),
                    response=lambda x: x.attendees.apply(self.get_my_response)
                    )
            .query("(eventType != 'outOfOffice') & (start_tm.notna()) & (response == 'accepted')", engine="python")
            .drop(columns=["start", "end", "attendees", "response"])
            .merge(te_df, how="inner", on=["start_tm", "description"])
            .dropna()
            .assign(pid=lambda x: x.pid.astype("int"))
            .merge(self.toggl_pjs, how="inner", left_on="pid", right_on="id")
            .drop(columns=["id", "pid"])
            .sort_values("start_tm", ascending=False)
        )

        project_overwrites = {'PMO': "Resourcing"}
        train_df['name'] = train_df['name'].map(project_overwrites).fillna(train_df['name'])

        train_df["event_order"] = train_df.filter(["name"]).groupby("name").cumcount()
        train_df["event_count"] = train_df.filter(["name", "event_order"]).groupby("name").transform(max)
        train_df["split"] = train_df.apply(lambda x: "test" if x.event_count
                                           > 1 and x.event_order == 0 else "train", axis=1)

        train_df.drop(columns=["start_tm", "end_tm", "event_order", "event_count"], inplace=True)
        train = train_df.query("split == 'train'").drop(columns="split")
        test = train_df.query("split == 'test'").drop(columns="split")
        return (train, test)

    def preprocess_for_pred(self, calendar_events: List[Dict], toggl_entries: List[Dict]) -> pd.DataFrame:
        """Preprocess input Lists to a prediction DataFrame.

        Args:
            calendar_events (List[Dict]): Google Calendar Events
            toggl_entries (List[Dict]): Existing toggle project entries

        Returns:
            pd.DataFrame: Prediction DataFrame
        """

        te_df = self.convert_toggl_entries(toggl_entries)
        ce_df = (pd.DataFrame(calendar_events)
                 .assign(start_tm=lambda x: x.start.apply((lambda x: x.get("dateTime"))),
                         response=lambda x: x.attendees.apply(self.get_my_response))
                 .query("(eventType != 'outOfOffice') & (start_tm.notna()) & (response == 'accepted')", engine="python")
                 )
        if "colorId" not in ce_df:
            ce_df["colorId"] = "99"

        return (
            ce_df.filter(["start", "end", "attendees", "creator", "summary", "eventType", "colorId", "description"])
            .fillna({"colorId": '99'})
            .assign(start_tm=pd.to_datetime(ce_df.start.apply(lambda x: x.get("dateTime"))),
                    end_tm=pd.to_datetime(ce_df.end.apply(lambda x: x.get("dateTime"))),
                    first_attendee=ce_df.attendees.apply(ProjectPredictor.attendee_n_, n=0),
                    second_attendee=ce_df.attendees.apply(ProjectPredictor.attendee_n_, n=1),
                    third_attendee=ce_df.attendees.apply(ProjectPredictor.attendee_n_, n=2),
                    fourth_attendee=ce_df.attendees.apply(ProjectPredictor.attendee_n_, n=3),
                    fifth_attendee=ce_df.attendees.apply(ProjectPredictor.attendee_n_, n=4),
                    attendee_list=ce_df.attendees.apply(ProjectPredictor.attendee_list_),
                    attendee_cnt=ce_df.attendees.apply(ProjectPredictor.attendee_count_),
                    creator=ce_df.creator.apply(lambda x: x.get("email")),
                    start_hour=(lambda x: x.start_tm.dt.hour),
                    text=lambda x: x.summary + " " + x.description.fillna(""),
                    description=(lambda x: x.summary),
                    )
            .drop(columns=["start", "end", "attendees"])
            .merge(te_df, how="left", on=["start_tm", "description"])
            .query("pid.isna() & duration.isna()", engine="python")
        )

    def fit(self, train: pd.DataFrame, test: pd.DataFrame, target: str = "name", finetune: bool = False, text_feature: str = "text", **kwargs) -> Pipeline:
        """Trains and finetunes model for project prediction.

        Args:
            train (pd.DataFrame): training data
            test (pd.DataFrame): test dataset
            finetune (bool, optional): Performs model finetuning if selected. Defaults to False.

        Returns:
            Pipeline: trained sklearn pipeline
        """

        text_pipeline = Pipeline([
            ('vect', CountVectorizer(lowercase=True)),
            ('tfidf', TfidfTransformer()),
        ])
        custom_transformer = make_column_transformer(
            (text_pipeline,
             text_feature),
            (OneHotEncoder(handle_unknown="ignore"),
             make_column_selector(dtype_include=object)))

        self.clf = setup(train, target=target, test_data=test,
                         session_id=123, custom_pipeline=custom_transformer, preprocess=False,
                         numeric_features=["duration", "attendee_cnt"],
                         silent=True, **kwargs)

        model = create_model('svm')
        if finetune:
            model = tune_model(model, search_library="optuna", search_algorithm="tpe", n_iter=200)

        final_model = finalize_model(model)

        self.pipeline, self.filename = save_model(final_model, "trained_model")
        return self.pipeline

    def predict(self, data: pd.DataFrame) -> pd.DataFrame:
        """Makes prediction for unseen data.

        Args:
            data (pd.DataFrame): unseen data

        Returns:
            pd.DataFrame: input data extended with predictions
        """

        if data.shape[0] == 0:
            sys.exit("There is nothing to load.")

        return (predict_model(self.pipeline, data, raw_score=True)
                .merge(self.toggl_pjs, left_on="Label", right_on="name", suffixes=["", "Label"])
                )
