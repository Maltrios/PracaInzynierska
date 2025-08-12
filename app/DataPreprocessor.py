import pandas as pd
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from sklearn.preprocessing import LabelEncoder


def detect_and_drop_id(table):
    potential_ids = []

    for col in table.columns:
        name_match = "id" in col.lower() or "uuid" in col.lower()
        high_uniqueness = table[col].nunique() / len(table) > 0.8
        too_many_uniques = table[col].nunique() > 1000
        likely_id_type = table[col].dtype in ["int64", "object"]

        if (name_match or high_uniqueness or too_many_uniques) and likely_id_type:
            potential_ids.append(col)

    return table.drop(columns=potential_ids), potential_ids

class DataPreprocessor:

    def __init__(self, data: pd.DataFrame):
        self.data, self.dropped_ids = detect_and_drop_id(data)
        self.decision_column = None
        self.label_encoder = LabelEncoder()


    def prepare_data(self, decision_column):
        self.decision_column = decision_column
        self.data[self.decision_column] = self.label_encoder.fit_transform(self.data[self.decision_column])
        categorical_column = self.data.select_dtypes(include=["object", "category"]).columns.tolist()

        encoder = OneHotEncoder(drop=None, sparse_output=False)
        encoded_array = encoder.fit_transform(self.data[categorical_column])
        encoded_cols = encoder.get_feature_names_out(categorical_column)

        encoded_df = pd.DataFrame(encoded_array, columns=encoded_cols)
        final_data = pd.concat([self.data.drop(columns=categorical_column).reset_index(drop=True), encoded_df], axis=1)

        X = final_data.drop(columns=self.decision_column)
        y = final_data[self.decision_column]

        return X, y, final_data

    def show_file_columns(self):
        return list(self.data.columns)