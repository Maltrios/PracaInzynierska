import GridSearch
import graphviz
import pandas
import sklearn.model_selection

from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from sklearn import tree
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from sklearn.feature_selection import SequentialFeatureSelector

########################### FUNKCJE #######################################


def detect_and_drop_id(table):
    potential_ids = []

    for col in table.columns:
        name_match = "id" in col.lower() or "uuid" in col.lower()
        high_uniqueness = table[col].nunique() / len(table) > 0.95
        likely_id_type = table[col].dtype in ["int64", "object"]

        if (name_match or high_uniqueness) and likely_id_type:
            potential_ids.append(col)

    return table.drop(columns=potential_ids), potential_ids

def tree_to_dot_with_mapping(clf, feature_names, class_names,all_feature_names=None):
    if all_feature_names is None:
        all_feature_names = feature_names

    dot_str = 'digraph Tree {\n'
    dot_str += 'node [shape=box, style="rounded, filled", color="lightblue", fontname="helvetica"];\n'

    def split_feature(feature_name):
        if "_" in feature_name:
            return feature_name.split("_", 1)
        return feature_name, None

    # przygotuj mapę wszystkich kategorii dla bazowych cech one-hot
    base_categories = {}
    for feat in all_feature_names:
        base, cat = split_feature(feat)
        if cat is not None:
            base_categories.setdefault(base, set()).add(cat)

    def recurse(node, parent=None, parent_label=None, allowed_categories_map=None):
        nonlocal dot_str
        if allowed_categories_map is None:
            allowed_categories_map = {b: cats.copy() for b, cats in base_categories.items()}

        if clf.tree_.feature[node] != -2:
            feat = feature_names[clf.tree_.feature[node]]
            base, category = split_feature(feat)
            threshold = clf.tree_.threshold[node]
            left = clf.tree_.children_left[node]
            right = clf.tree_.children_right[node]

            dot_str += f'"{node}" [label="{base}\n≤ {threshold:.2f}"];\n'
            if parent is not None:
                dot_str += f'"{parent}" -> "{node}" [label="{parent_label}"];\n'

            if category and abs(threshold - 0.5) < 1e-5:
                # aktualizuj allowed_categories_map dla dzieci
                allowed_left = {k: v.copy() for k, v in allowed_categories_map.items()}
                allowed_right = {k: v.copy() for k, v in allowed_categories_map.items()}

                # lewa gałąź: kategorie bez 'category'
                allowed_left[base].discard(category)
                # prawa gałąź: tylko 'category'
                allowed_right[base] = {category}

                # etykiety
                cats = sorted(allowed_left[base])
                if len(cats) == 0:
                    left_label = f"{base} ≠ {category}"
                elif len(cats) == 1:
                    left_label = f"{cats[0]}"
                else:
                    left_label = f"{base} in {{{', '.join(cats)}}}"
                right_label = f"{category}"

                recurse(left, node, left_label, allowed_left)
                recurse(right, node, right_label, allowed_right)
            else:
                left_label = f"≤ {threshold:.2f}"
                right_label = f"> {threshold:.2f}"

                recurse(left, node, left_label, allowed_categories_map)
                recurse(right, node, right_label, allowed_categories_map)

        else:
            value = clf.tree_.value[node]
            class_index = int(value.argmax())
            label = class_names[class_index]
            dot_str += f'"{node}" [label="{label}", style=filled, fillcolor="lightgreen"];\n'
            if parent is not None:
                dot_str += f'"{parent}" -> "{node}" [label="{parent_label}"];\n'

    recurse(0)
    dot_str += '}'
    return dot_str


########################### LOGIKA APLIKACJI  ############################


#TODO 1: pliki csv należy zakodować na liczby
data = pandas.read_csv("drug200.csv")

#wybranie kolumn decyzyjnych
print(data.columns.tolist())
decision_column = input("Wybierz kolumnę decyzyjną")

data, dropped_ids = detect_and_drop_id(data)
print("Usunięto kolumny identyfikatorów:", dropped_ids)

label_encoder = LabelEncoder()
data[decision_column] = label_encoder.fit_transform(data[decision_column])

categorical_column = data.select_dtypes(include=["object", "category"]).columns.tolist()
# print(categorical_column)


encoder = OneHotEncoder(drop=None,sparse_output=False)
encoded_array = encoder.fit_transform(data[categorical_column])
encoded_cols = encoder.get_feature_names_out(categorical_column)

encoded_df = pandas.DataFrame(encoded_array, columns=encoded_cols)
final_data = pandas.concat([data.drop(columns=categorical_column).reset_index(drop=True), encoded_df], axis=1)

#TODO 2: analiza plików

X = final_data.drop(columns=decision_column)
y = final_data[decision_column]

#podział na dane testowe i treningowe
X_train, X_test, y_train, y_test = sklearn.model_selection.train_test_split(X,y,  test_size=0.3, stratify=y)

# Zbuduj drzewo
dtc = tree.DecisionTreeClassifier(random_state=17)
dtc = dtc.fit(X_train,y_train)

# Predykcja na danych testowych
y_pred = dtc.predict(X_test)

# print(confusion_matrix(y_test, y_pred))
# print(classification_report(y_test, y_pred))
#
# print(dtc.feature_importances_)

# Ocena modelu
accuracy = accuracy_score(y_test, y_pred)
print("Test set accuracy: {:.2f}".format(accuracy))

features = pandas.DataFrame(dtc.feature_importances_, index=X.columns)
print(features.head(15))

print("--------------------------------")
sfs = SequentialFeatureSelector(
    dtc,
    direction="backward",
    n_features_to_select="auto",
    scoring="accuracy",
    cv=5,
    n_jobs=-1
)
sfs.fit(X_train,y_train)

selected_columns = X.columns[sfs.get_support()]
print("Wybrane cechy:", list(selected_columns))

print("--------------------------------")

# --- Nowe dane zredukowane ---
X_train_best = X_train[selected_columns]
X_test_best = X_test[selected_columns]

# --- GridSearch tylko na zbiorze treningowym ---
search = GridSearch.GridSearch()
search.fit(X_train_best,y_train)
print("Najlepsze parametry:", search.get_best_params())

# --- Finalny model i ocena ---
dtc_best = search.get_best_model()
dtc_best.fit(X_train_best, y_train)
y_pred_best = dtc_best.predict(X_test_best)

best_accuracy = accuracy_score(y_test, y_pred_best)
print(f"Accuracy (wszystkie cechy): {accuracy:.2f}")
print(f"Accuracy (wybrane cechy): {best_accuracy:.2f}")


#TODO 3: narysowanie drzewa decyzyjnego na podstawie danych

dot_data = tree_to_dot_with_mapping(
    dtc_best,
    feature_names=X_train_best.columns,
    class_names=label_encoder.inverse_transform(range(len(label_encoder.classes_))),
    all_feature_names=final_data.drop(columns=decision_column).columns
)

graph = graphviz.Source(dot_data)
graph.render("final_tree_best1", format="png", view=True)
