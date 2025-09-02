import pandas as pd
import sklearn
from .GridSearch import GridSearch
from .RandomSearch import RandomSearch
from sklearn.feature_selection import SequentialFeatureSelector
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


class ModelTrainer:
    def __init__(self, X , y,checked = True):
        self.X = X
        self.y = y
        self.X_train, self.X_test, self.y_train, self.y_test = sklearn.model_selection.train_test_split(self.X, self.y, test_size=0.3,                                                                   stratify=self.y)
        self.checked = checked
        self.model = None
        self.search = None
        self.used_features = None

    def train_model(self, best_columns = None):

        if self.checked:
            self.search = GridSearch()
        else:
            self.search = RandomSearch()

        if best_columns is not None and len(best_columns) > 0:
            X_train = self.X_train[best_columns]
            X_test = self.X_test[best_columns]
        else:
            X_train = self.X_train
            X_test = self.X_test

        self.used_features = X_train.columns

        self.search.fit(X_train, self.y_train)
        self.model = self.search.get_best_model()
        y_predict = self.model.predict(X_test)

        if len(self.y.unique()) == 2:
            average = 'binary'
        else:
            average = 'weighted'

        return {
            "accuracy": accuracy_score(self.y_test, y_predict),
            "precision": precision_score(self.y_test, y_predict, average=average, zero_division=0),
            "recall": recall_score(self.y_test, y_predict, average=average, zero_division=0),
            "f1": f1_score(self.y_test, y_predict, average=average, zero_division=0),
        }


    def find_best_attributes(self):
        sfs = SequentialFeatureSelector(
            self.model,
            direction="backward",
            n_features_to_select="auto",
            scoring="accuracy",
            cv=5,
            n_jobs=1
        )
        sfs.fit(self.X_train,self.y_train)
        selected_columns = self.X.columns[sfs.get_support()]

        return selected_columns

    def sort_best_column(self):
        features = pd.DataFrame(self.model.feature_importances_, index=self.used_features)
        return list(features.head(15).index)