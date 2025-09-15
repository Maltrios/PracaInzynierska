from services.ParameterSearch import ParameterSearch
from sklearn.model_selection import GridSearchCV
from sklearn.tree import DecisionTreeClassifier

class GridSearch(ParameterSearch):

    def __init__(self, cv=5, scoring='accuracy'):
        super().__init__()
        self.param_grid = {
            'max_depth': [2, 3, 4, 5, None],
            'min_samples_leaf': [1, 5, 10],
            'ccp_alpha': [0.005, 0.01, 0.02, 0.05]
        }
        self.cv = cv
        self.scoring = scoring

    def fit(self, X,y):
        self.search = GridSearchCV(
            estimator=DecisionTreeClassifier(random_state=0),
            param_grid=self.param_grid,
            cv=self.cv,
            scoring=self.scoring,
            n_jobs=1
        )
        self.search.fit(X, y)
