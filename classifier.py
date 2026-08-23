from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from training_data import TRAINING_DATA, CATEGORIES

UNCERTAIN = "UNCERTAIN"
DEFAULT_THRESHOLD = 0.50


class CategoryClassifier:
    def __init__(self, threshold=DEFAULT_THRESHOLD):
        self.threshold = threshold
        self.pipeline = make_pipeline(
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                sublinear_tf=True,
                min_df=1,
            ),
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                C=5.0,
            ),
        )
        self._trained = False

    def train(self, data=None):
        data = TRAINING_DATA if data is None else data
        texts = [t for t, _ in data]
        labels = [l for _, l in data]
        self.pipeline.fit(texts, labels)
        self._trained = True
        return self

    def scores(self, product_name):
        """Full probability distribution — useful for inspection and debugging."""
        if not self._trained:
            raise RuntimeError("classifier not trained")
        probs = self.pipeline.predict_proba([product_name])[0]
        classes = self.pipeline.classes_
        return dict(sorted(zip(classes, probs), key=lambda kv: -kv[1]))

    def predict(self, product_name):
        """Returns (category_or_UNCERTAIN, confidence, top_category)."""
        ranked = self.scores(product_name)
        top_category, confidence = next(iter(ranked.items()))
        if confidence < self.threshold:
            return UNCERTAIN, confidence, top_category
        return top_category, confidence, top_category