from classifier import CategoryClassifier

c = CategoryClassifier().train()

for name in [
    "AA batteries 4-pack",
    "Arabica coffee beans 1kg",
    "Coffee grinder burr type",
    "Stainless steel cookware set",
]:
    label, confidence, top = c.predict(name)
    print(f"{name:32} -> {label:12} ({confidence:.2f}, leaning {top})")