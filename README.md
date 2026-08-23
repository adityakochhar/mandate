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
python batch.py                   # 30-attempt batch run
python test_gate.py               # 12 gate checks
python test_mandate.py            # signature tamper tests
python test_vulnerability.py      # the fixed vulnerability
python evaluate_classifier.py     # held-out ML metrics
python compare_providers.py       # hosted vs local model (needs `ollama serve`)
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
| Arabica coffee beans | ALLOW | category groceries verified at 0.84 |
| Electric kettle | DENY | 189000 > 100000 |
| AA batteries (mislabelled) | DENY | classified electronics at 0.75; merchant claimed groceries |
| Ceramic serving bowl set | ESCALATE | leaning appliances at 0.30, below threshold 0.60 |

### Batch run — 30 attempts

`python batch.py` runs 30 scenarios across four mandate configurations:
in-scope purchases, over-limit attempts, category violations, ambiguous
products, and requests for items not in the catalog.

| Outcome | Count |
|---|---|
| ALLOW | 10 |
| DENY — category not allowed | 10 |
| DENY — amount exceeded | 5 |
| ESCALATE — category uncertain | 3 |
| NO_PROPOSAL — no matching item | 2 |

**Unauthorised purchases: 0 / 30.** No money moved outside a mandate's scope.
**Legitimate purchases wrongly blocked: 0 / 30.**

Total runtime 21s, including 10 live Razorpay test-mode order creations.

*Caveat:* these scenarios were written by the author with knowledge of the
classifier's behaviour. They exercise every decision path, but they are not an
adversarial or independently sampled test set.

### Classifier — honest metrics

195 hand-built training examples, 4 categories, 25% held out.

- **Accuracy on unseen names: 73%**
- Per-class recall: electronics 1.00, groceries 0.69, appliances 0.64, household 0.50
- Groceries precision is 1.00; electronics precision is 0.60.

An earlier version had 145 examples skewed toward groceries, and everything
unrecognised was guessed as groceries (electronics recall: 0.38). Adding 50
targeted electronics and appliances examples raised accuracy to 73% — and
moved the bias rather than removing it. Electronics is now the majority class
and has become the new fallback guess. **The largest class is always the
model's default.**

| Threshold | Auto-decided | Escalated | **Wrong approvals** |
|---|---|---|---|
| 0.40 | 29 | 20 | **2** |
| 0.50 | 25 | 24 | **1** |
| 0.60 | 14 | 35 | **0** |
| 0.70 | 7 | 42 | **0** |

**0.60 is the lowest threshold with zero wrong approvals**, up from 0.50 before
the data change. Improving the model invalidated the previously safe threshold —
the threshold is re-derived from held-out data after every change to the model.

`C=5.0` was likewise selected by held-out accuracy across
`C ∈ {1, 5, 10, 50, 200}`, not by inspection.

### Provider independence

The same five instructions, run through a hosted model and a local one:

| | Groq (`openai/gpt-oss-20b`) | Ollama (`qwen2.5-coder:14b`, local) |
|---|---|---|
| Identical item chosen | 5 / 5 | 5 / 5 |
| Correctly declined absent item | yes | yes |
| Total time | 2.8s | 39.8s |

Swapping providers is a nine-line subclass — same prompt, same parsing, different
endpoint. Nothing in the gate, the payment path, or the audit log changes,
because the model holds no authority in the design. Local inference costs ~14×
latency and sends no data off the machine.

Reproduce with `python compare_providers.py`.

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
- **Training data is synthetic and small.** 195 examples written by hand,
  skewed toward Indian retail vocabulary.
- **Confidence threshold is coupled to the model.** Any change to training data
  or hyperparameters requires re-deriving it from held-out data.

## Stack

Python 3.12 · FastAPI · PyNaCl (Ed25519) · scikit-learn · Groq (`openai/gpt-oss-20b`) · Ollama · Razorpay test mode · SQLite

Model access is behind an `LLMProvider` interface — swapping providers is a
nine-line subclass, because the model holds no authority in the design.