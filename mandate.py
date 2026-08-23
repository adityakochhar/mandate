import json, time, uuid
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError


def canonical(payload: dict) -> bytes:
    """One dict -> exactly one byte string. Order and spacing fixed."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def new_keypair():
    sk = SigningKey.generate()
    return sk, sk.verify_key


def create_mandate(issued_to, max_amount_paise, categories,
                   merchant_allowlist, ttl_seconds=86400, max_transactions=1):
    now = int(time.time())
    return {
        "mandate_id": "mnd_" + uuid.uuid4().hex[:12],
        "issued_to": issued_to,
        "scope": {
            "max_amount_paise": max_amount_paise,
            "currency": "INR",
            "categories": sorted(categories),
            "merchant_allowlist": sorted(merchant_allowlist),
            "max_transactions": max_transactions,
        },
        "not_before": now,
        "expires_at": now + ttl_seconds,
        "nonce": uuid.uuid4().hex,
    }


def sign_mandate(mandate: dict, signing_key: SigningKey) -> dict:
    sig = signing_key.sign(canonical(mandate)).signature
    return {**mandate, "signature": sig.hex()}


def verify_mandate(signed: dict, verify_key: VerifyKey) -> bool:
    if "signature" not in signed:
        return False
    body = {k: v for k, v in signed.items() if k != "signature"}
    try:
        verify_key.verify(canonical(body), bytes.fromhex(signed["signature"]))
        return True
    except (BadSignatureError, ValueError, TypeError):
        return False