import time
from mandate import verify_mandate
from classifier import CategoryClassifier, UNCERTAIN

DENY = "DENY"
ALLOW = "ALLOW"
ESCALATE = "ESCALATE"


class NonceStore:
    """Remembers spent nonces so a mandate can't be replayed."""

    def __init__(self):
        self._seen = {}

    def count(self, nonce):
        return self._seen.get(nonce, 0)

    def record(self, nonce):
        self._seen[nonce] = self._seen.get(nonce, 0) + 1


def evaluate(signed_mandate, request, verify_key, nonce_store,
             classifier=None, now=None):
    """Returns (decision, reason_code, detail). Fails closed on anything odd."""
    now = int(time.time()) if now is None else now

    try:
        if not verify_mandate(signed_mandate, verify_key):
            return DENY, "SIGNATURE_INVALID", "mandate signature did not verify"

        scope = signed_mandate["scope"]

        if now < signed_mandate["not_before"]:
            return DENY, "NOT_YET_VALID", "mandate is not active yet"

        if now >= signed_mandate["expires_at"]:
            return DENY, "EXPIRED", "mandate has expired"

        used = nonce_store.count(signed_mandate["nonce"])
        if used >= scope["max_transactions"]:
            return DENY, "TRANSACTION_LIMIT", f"already used {used} time(s)"

        if request["currency"] != scope["currency"]:
            return DENY, "CURRENCY_MISMATCH", request["currency"]

        if request["amount_paise"] > scope["max_amount_paise"]:
            return DENY, "AMOUNT_EXCEEDED", (
                f"{request['amount_paise']} > {scope['max_amount_paise']}"
            )

        if request["merchant_id"] not in scope["merchant_allowlist"]:
            return DENY, "MERCHANT_NOT_ALLOWED", request["merchant_id"]

        # Category is NEVER taken from the merchant. It is derived independently
        # from the product name, because the merchant is the party being guarded
        # against and must not supply the data used to guard against it.
        if classifier is None:
            return DENY, "NO_CLASSIFIER", "category cannot be verified"

        product_name = request.get("product_name")
        if not product_name:
            return DENY, "MALFORMED", "product_name missing"

        label, confidence, leaning = classifier.predict(product_name)

        if label == UNCERTAIN:
            return ESCALATE, "CATEGORY_UNCERTAIN", (
                f"leaning {leaning} at {confidence:.2f}, "
                f"below threshold {classifier.threshold:.2f}"
            )

        if label not in scope["categories"]:
            return DENY, "CATEGORY_NOT_ALLOWED", (
                f"classified {label} at {confidence:.2f}; "
                f"merchant claimed {request.get('claimed_category')}"
            )

        return ALLOW, "OK", f"category {label} verified at {confidence:.2f}"

    except Exception as exc:
        return DENY, "MALFORMED", f"{type(exc).__name__}: {exc}"