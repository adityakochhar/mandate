from collections import Counter

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

from training_data import TRAINING_DATA, CATEGORIES
from classifier import CategoryClassifier, UNCERTAIN

SEED = 42

train_data, test_data = train_test_split(
    TRAINING_DATA,
    test_size=0.25,
    random_state=SEED,
    stratify=[label for _, label in TRAINING_DATA],
)

print(f"train: {len(train_data)}   held-out test: {len(test_data)}")
print(f"test class balance: {dict(Counter(l for _, l in test_data))}")
print()

test_texts = [t for t, _ in test_data]
test_labels = [l for _, l in test_data]


def evaluate(C_value):
    clf = CategoryClassifier(threshold=0.0)
    clf.pipeline.named_steps["logisticregression"].set_params(C=C_value)
    clf.train(train_data)
    predictions = [clf.predict(t)[2] for t in test_texts]
    correct = sum(p == a for p, a in zip(predictions, test_labels))
    confidences = [clf.scores(t)[clf.predict(t)[2]] for t in test_texts]
    return clf, predictions, correct / len(test_labels), sum(confidences) / len(confidences)


print("choosing C on held-out data")
print(f"{'C':>6} {'accuracy':>10} {'mean conf':>11}")
results = {}
for C_value in [1.0, 5.0, 10.0, 50.0, 200.0]:
    _, _, acc, conf = evaluate(C_value)
    results[C_value] = acc
    print(f"{C_value:>6} {acc:>10.2%} {conf:>11.2f}")
print()

best_C = max(results, key=results.get)
print(f"best C by held-out accuracy: {best_C}")
print()

clf, predictions, acc, _ = evaluate(best_C)

print("per-class performance (ignoring threshold)")
print(classification_report(test_labels, predictions, zero_division=0))

print("confusion matrix (rows = actual, cols = predicted)")
print(f"{'':>13}" + "".join(f"{c[:7]:>9}" for c in CATEGORIES))
matrix = confusion_matrix(test_labels, predictions, labels=CATEGORIES)
for name, row in zip(CATEGORIES, matrix):
    print(f"{name:>13}" + "".join(f"{v:>9}" for v in row))
print()

print("threshold trade-off on held-out data")
print(f"{'threshold':>10} {'auto-decided':>13} {'escalated':>10} {'wrong auto':>11}")
for threshold in [0.40, 0.50, 0.60, 0.70, 0.80, 0.90]:
    clf.threshold = threshold
    decided = wrong = escalated = 0
    for text, actual in zip(test_texts, test_labels):
        label, _, _ = clf.predict(text)
        if label == UNCERTAIN:
            escalated += 1
        else:
            decided += 1
            if label != actual:
                wrong += 1
    print(f"{threshold:>10.2f} {decided:>13} {escalated:>10} {wrong:>11}")