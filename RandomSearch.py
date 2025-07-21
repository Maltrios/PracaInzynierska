from ParameterSearch import ParameterSearch
from sklearn.model_selection import RandomizedSearchCV
from sklearn.tree import DecisionTreeClassifier
from scipy.stats import randint, uniform

class RandomSearch(ParameterSearch):

    def __init__(self, n_iter = 20, cv=5, scoring='accuracy'):
        super().__init__()
        self.param_distributions = {
            'max_depth': randint(2, 10),
            'min_samples_leaf': randint(1, 20),
            'ccp_alpha': uniform(0.0, 0.05)  # rozkład ciągły
        }

        self.n_inter = n_iter
        self.cv = cv
        self.scoring = scoring


    def fit(self, X, y):
        self.search = RandomizedSearchCV(
            estimator=DecisionTreeClassifier(random_state=0),
            param_distributions=self.param_distributions,
            n_iter=self.n_inter,  # liczba losowań (im więcej, tym lepiej)
            cv=self.cv,
            scoring=self.scoring,
            random_state=1,
            n_jobs=-1
        )
        self.search.fit(X, y)


