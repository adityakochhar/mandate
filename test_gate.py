import time
from mandate import new_keypair, create_mandate, sign_mandate
from classifier import CategoryClassifier
from gate import evaluate, NonceStore, ALLOW, DENY, ESCALATE

sk, vk = new_keypair()
clf = CategoryClassifier().train()

m = sign_mandate(
    create_mandate("agent_buyer_01", 100000, ["groceries"], ["merch_kofi"]), sk
)


def req(**over):
    base = {
        "amount_paise": 85000,
        "currency": "INR",
        "merchant_id": "merch_kofi",
        "product_name": "Arabica coffee beans 1kg",
        "claimed_category": "groceries",
    }
    return {**base, **over}


def check(label, expected_decision, expected_reason, request,
          store=None, now=None, classifier=clf):
    store = store or NonceStore()
    d, reason, detail = evaluate(m, request, vk, store,
                                 classifier=classifier, now=now)
    assert d == expected_decision and reason == expected_reason, \
        (label, d, reason, detail)
    print(f"{label:24} {d:9} {reason}")


check("valid purchase", ALLOW, "OK", req())
check("over limit", DENY, "AMOUNT_EXCEEDED", req(amount_paise=140000))
check("unknown merchant", DENY, "MERCHANT_NOT_ALLOWED", req(merchant_id="merch_evil"))
check("wrong currency", DENY, "CURRENCY_MISMATCH", req(currency="USD"))
check("expired", DENY, "EXPIRED", req(), now=int(time.time()) + 90000)
check("missing field", DENY, "MALFORMED", {"amount_paise": 500})
check("no product name", DENY, "MALFORMED", req(product_name=""))
check("no classifier", DENY, "NO_CLASSIFIER", req(), classifier=None)

check("spoofed category", DENY, "CATEGORY_NOT_ALLOWED",
      req(product_name="AA batteries 4-pack", claimed_category="groceries",
          amount_paise=18000))

check("unknown product", ESCALATE, "CATEGORY_UNCERTAIN",
      req(product_name="Stainless steel cookware set", amount_paise=45000))

tampered = {**m, "scope": {**m["scope"], "max_amount_paise": 10000000}}
d, reason, _ = evaluate(tampered, req(amount_paise=900000), vk,
                        NonceStore(), classifier=clf)
assert d == DENY and reason == "SIGNATURE_INVALID"
print(f"{'raised own limit':24} {d:9} {reason}")

store = NonceStore()
evaluate(m, req(), vk, store, classifier=clf)
store.record(m["nonce"])
check("replay attempt", DENY, "TRANSACTION_LIMIT", req(), store=store)