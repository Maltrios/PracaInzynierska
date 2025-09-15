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
        if any(col is None or str(col).strip() == "" or str(col).startswith("Unnamed") for col in data.columns):
            raise ValueError("The CSV file must contain valid column names in the first row.")

        if len(data.columns) != len(set(data.columns)):
            raise ValueError("CSV file contains duplicate column names.")

        if data.empty:
            raise ValueError("Uploaded dataset is empty.")

        if data.shape[1] < 2:
            raise ValueError("Dataset must have at least 2 columns.")

        if len(data) < 20:
            raise ValueError("Dataset must have at least 20 rows.")

        self.data, self.dropped_ids = detect_and_drop_id(data)

        categorical_columns = self.data.select_dtypes(include=["object", "category"]).columns.tolist()
        if len(categorical_columns) == 0:
            raise ValueError("No categorical columns in the data, at least one required")

        self.decision_column = None
        self.label_encoder = LabelEncoder()

    def validate_target_column(self, target: str, min_samples_per_class: int =2, max_classes: int = 20):
        if target not in self.data.columns:
            raise ValueError(f"Target column '{target}' not found in dataset.")

        y = self.data[target]
        class_counts = y.value_counts()

        if len(class_counts) < 2:
            raise ValueError("Target column must have at least 2 unique classes.")

        if (class_counts < min_samples_per_class).any():
            raise ValueError("Each class in target must have at least 2 samples.")

        if len(class_counts) > max_classes:
            raise ValueError(f"Too many unique classes in target column ({len(class_counts)}).")

    def prepare_data(self, decision_column):
        self.validate_target_column(decision_column)
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