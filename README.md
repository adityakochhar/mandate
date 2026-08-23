# Mandate

**Bounded spending authority for AI agents.**

An AI agent that can spend real money on your behalf — but only inside a
cryptographically signed mandate it cannot modify, widen, or bypass.

Built for the Razorpay AI Buildathon 2026, Track 1 (AI Growth & Agentic Commerce).

---

## The problem

AI agents can recommend what to buy. They can't safely buy it.

Nobody hands an agent a card, because there's no way to say *"you may spend
up to ₹1,000, only on groceries, only today"* and have that hold when the
model is confused, jailbroken, or fed a malicious product listing.

Mandate is that missing layer.

## How it works

```
Human issues mandate          (signed: limit, categories, merchants, expiry)
        ↓
Buyer agent                   (LLM picks an item, requests checkout)
        ↓
Merchant returns HTTP 402     (payment challenge)
        ↓
Mandate gate                  (7 checks — fails closed)
        ↓
    ALLOW → Razorpay test-mode order
    DENY  → logged, no money moves
  ESCALATE → sent to human for approval
        ↓
Audit row written, every time
```

### The core design decision

**The gate is not inside the agent.** The agent proposes; it never approves.

An agent that validates its own mandate provides no protection — the same
component that gets compromised is the one deciding whether to allow the
payment. Enforcement lives outside the model, in plain deterministic Python,
and the LLM has no path around it.

Structurally, `payments.create_order()` is only reachable from inside
`if decision == ALLOW`. Money cannot move without passing the gate.

### The category problem

An early version trusted the merchant's declared product category. That's a
trust inversion: the merchant is the party being guarded against, yet was
supplying the data used to guard against it. A ₹180 pack of AA batteries
tagged `groceries` passed every check under a groceries-only mandate.

`test_vulnerability.py` reproduces the original hole and confirms the fix.

The gate now derives the category independently, using a classifier trained
on product names. The merchant's claim is recorded in the audit log but never
used for a decision.

---

## Running it

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```
GROQ_API_KEY=...
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
```

Then:

```bash
python demo.py                    # end-to-end, four scenarios
python test_gate.py               # 12 gate checks
python test_mandate.py            # signature tamper tests
python test_vulnerability.py      # the fixed vulnerability
python evaluate_classifier.py     # held-out ML metrics
```

---

## Results

### Gate behaviour — `test_gate.py`

```
valid purchase           ALLOW     OK
over limit               DENY      AMOUNT_EXCEEDED
unknown merchant         DENY      MERCHANT_NOT_ALLOWED
wrong currency           DENY      CURRENCY_MISMATCH
expired                  DENY      EXPIRED
missing field            DENY      MALFORMED
no product name          DENY      MALFORMED
no classifier            DENY      NO_CLASSIFIER
spoofed category         DENY      CATEGORY_NOT_ALLOWED
unknown product          ESCALATE  CATEGORY_UNCERTAIN
raised own limit         DENY      SIGNATURE_INVALID
replay attempt           DENY      TRANSACTION_LIMIT
```

### End-to-end — `demo.py`

Mandate: 100000 paise, `["groceries"]`, `["merch_kofi"]`

| Scenario | Result | Detail |
|---|---|---|
| Arabica coffee beans | ALLOW | category groceries verified at 0.82 |
| Electric kettle | DENY | 189000 > 100000 |
| AA batteries (mislabelled) | DENY | classified electronics at 0.79; merchant claimed groceries |
| Ceramic serving bowl set | ESCALATE | leaning electronics at 0.36, below threshold 0.50 |

### Classifier — honest metrics

145 hand-built training examples, 4 categories, 25% held out.

- **Accuracy on unseen names: 65%**
- Per-class recall: groceries 0.92, household 0.60, appliances 0.50, electronics 0.38
- Electronics precision is 1.00 — when it says electronics, it's right; it's just rarely confident enough to say so.

The model is weak. That is the point of the threshold:

| Threshold | Auto-decided | Escalated | **Wrong approvals** |
|---|---|---|---|
| 0.40 | 20 | 17 | **1** |
| 0.50 | 16 | 21 | **0** |
| 0.60 | 8 | 29 | **0** |
| 0.80 | 3 | 34 | **0** |

**0.50 was chosen as the lowest threshold with zero wrong approvals.** The cost
is that 57% of purchases require human confirmation. A better model reduces
that friction; it does not change the safety property.

`C=5.0` was likewise selected by held-out accuracy across `C ∈ {1, 5, 10, 50, 200}`,
not by inspection.

---

## Not implemented, and why

- **Mandate revocation.** A mandate expires but cannot be cancelled early. Real
  systems need a revocation list; out of scope for this build.
- **Full AP2 / x402 spec compliance.** The core exchange is implemented — 402
  challenge, signed delegated authority, replay protection. This is not a
  conformant implementation of either specification.
- **Payment completion.** Razorpay test-mode orders are created and linked to
  the mandate via `notes`. There is no customer to complete checkout, so the
  chain honestly ends at order creation, not captured payment.
- **Merchant-side category integrity.** The classifier defends against a
  merchant misdeclaring a category. It cannot defend against a merchant
  misdescribing the product itself.

## Known trade-offs

- **Check ordering.** Amount is checked before category (cheapest check first).
  An item that is both over-limit and miscategorised reports only
  `AMOUNT_EXCEEDED`. Fast-fail was chosen over exhaustive reporting.
- **Training data is synthetic and small.** 145 examples written by hand,
  skewed toward Indian retail vocabulary.

## Stack

Python 3.12 · FastAPI · PyNaCl (Ed25519) · scikit-learn · Groq (`openai/gpt-oss-20b`) · Razorpay test mode · SQLite

Model access is behind an `LLMProvider` interface — swapping providers is a
one-line change, because the model holds no authority in the design.