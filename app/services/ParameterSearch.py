class ParameterSearch:
    def __init__(self):
        self.search = None

    def fit(self, X, y):
        raise NotImplementedError

    def get_best_model(self):
        if self.search is None:
            raise ValueError("The model has not been trained. First, call .fit(X, y).")
        return self.search.best_estimator_

    def get_best_params(self):
        if self.search is None:
            raise ValueError("The model has not been trained")
        return self.search.best_params_

    def get_validation_score(self):
        if self.search is None:
            raise ValueError("Model nie został wytrenowany.")
        return self.search.best_score_