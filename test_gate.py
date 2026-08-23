import time
from mandate import new_keypair, create_mandate, sign_mandate
from gate import evaluate, NonceStore, ALLOW, DENY

sk, vk = new_keypair()
m = sign_mandate(
    create_mandate("agent_buyer_01", 100000, ["groceries"], ["merch_kofi"]), sk
)

def req(**over):
    base = {
        "amount_paise": 85000,
        "currency": "INR",
        "merchant_id": "merch_kofi",
        "category": "groceries",
    }
    return {**base, **over}


def check(label, expected_decision, expected_reason, request, store=None, now=None):
    store = store or NonceStore()
    d, reason, _ = evaluate(m, request, vk, store, now=now)
    assert d == expected_decision and reason == expected_reason, (label, d, reason)
    print(f"{label}: {reason}")


check("valid purchase", ALLOW, "OK", req())
check("over limit", DENY, "AMOUNT_EXCEEDED", req(amount_paise=140000))
check("wrong category", DENY, "CATEGORY_NOT_ALLOWED", req(category="electronics"))
check("unknown merchant", DENY, "MERCHANT_NOT_ALLOWED", req(merchant_id="merch_evil"))
check("wrong currency", DENY, "CURRENCY_MISMATCH", req(currency="USD"))
check("expired", DENY, "EXPIRED", req(), now=int(time.time()) + 90000)
check("missing field", DENY, "MALFORMED", {"amount_paise": 500})

tampered = {**m, "scope": {**m["scope"], "max_amount_paise": 10000000}}
d, reason, _ = evaluate(tampered, req(amount_paise=900000), vk, NonceStore())
assert d == DENY and reason == "SIGNATURE_INVALID"
print(f"raised own limit: {reason}")

store = NonceStore()
evaluate(m, req(), vk, store)
store.record(m["nonce"])
check("replay attempt", DENY, "TRANSACTION_LIMIT", req(), store=store)