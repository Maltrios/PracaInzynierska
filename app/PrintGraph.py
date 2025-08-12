from graphviz import Source


class PrintGraph:
    def __init__(self, clf, feature_names, class_names, all_feature_names=None):
        self.clf = clf
        self.feature_names = feature_names
        self.class_names = class_names
        self.all_feature_names = all_feature_names if all_feature_names is not None else list(feature_names)
        self.dot_str = ''
        self.base_categories = self._prepare_base_categories()


    def _split_feature(self, feature_name):
        return feature_name.split("_", 1) if "_" in feature_name else (feature_name, None)

    def _prepare_base_categories(self):
        categories = {}
        for feat in self.all_feature_names:
            base, cat = self._split_feature(feat)
            if cat is not None:
                categories.setdefault(base, set()).add(cat)
        return categories

    def _recurse(self, node, parent=None, parent_label=None, allowed_categories_map=None):
        if allowed_categories_map is None:
            allowed_categories_map = {b: cats.copy() for b, cats in self.base_categories.items()}

        if self.clf.tree_.feature[node] != -2:
            feat = self.feature_names[self.clf.tree_.feature[node]]
            base, category = self._split_feature(feat)
            threshold = self.clf.tree_.threshold[node]
            left = self.clf.tree_.children_left[node]
            right = self.clf.tree_.children_right[node]

            self.dot_str += f'"{node}" [label="{base}\n≤ {threshold:.2f}"];\n'
            if parent is not None:
                self.dot_str += f'"{parent}" -> "{node}" [label="{parent_label}"];\n'

            if category and abs(threshold - 0.5) < 1e-5:
                allowed_left = {k: v.copy() for k, v in allowed_categories_map.items()}
                allowed_right = {k: v.copy() for k, v in allowed_categories_map.items()}

                allowed_left[base].discard(category)
                allowed_right[base] = {category}

                cats = sorted(allowed_left[base])
                if len(cats) == 0:
                    left_label = f"{base} ≠ {category}"
                elif len(cats) == 1:
                    left_label = f"{cats[0]}"
                else:
                    left_label = f"{base} in {{{', '.join(cats)}}}"
                right_label = f"{category}"

                self._recurse(left, node, left_label, allowed_left)
                self._recurse(right, node, right_label, allowed_right)
            else:
                left_label = f"≤ {threshold:.2f}"
                right_label = f"> {threshold:.2f}"
                self._recurse(left, node, left_label, allowed_categories_map)
                self._recurse(right, node, right_label, allowed_categories_map)
        else:
            value = self.clf.tree_.value[node]
            class_index = int(value.argmax())
            label = self.class_names[class_index]
            self.dot_str += f'"{node}" [label="{label}", style=filled, fillcolor="lightgreen"];\n'
            if parent is not None:
                self.dot_str += f'"{parent}" -> "{node}" [label="{parent_label}"];\n'

    def to_dot(self):
        self.dot_str = 'digraph Tree {\n'
        self.dot_str += 'node [shape=box, style="rounded, filled", color="lightblue", fontname="helvetica"];\n'
        self._recurse(0)
        self.dot_str += '}'
        return self.dot_str

    def save(self, filename="tree", format_file="png"):
        """Zapisz graf do pliku."""
        dot = self.to_dot()
        return Source(dot).render(filename=filename, format=format_file, cleanup=True)

    def view(self, filename="tree", format_file="png"):
        """Zapisz i otwórz graf w domyślnej przeglądarce."""
        dot = self.to_dot()
        return Source(dot).render(filename=filename, format=format_file, view=True, cleanup=True)