import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from merchant import app
from mandate import new_keypair, create_mandate, sign_mandate
from classifier import CategoryClassifier
from gate import evaluate, NonceStore, ALLOW, DENY, ESCALATE
from agent import BuyerAgent
from payments import PaymentProcessor
from audit import AuditLog

CATALOG = json.loads((Path(__file__).parent / "catalog.json").read_text())


class Runtime:
    def __init__(self, fresh_log=True):
        self.client = TestClient(app)
        self.signing_key, self.verify_key = new_keypair()
        self.classifier = CategoryClassifier().train()
        self.agent = BuyerAgent()
        self.payments = PaymentProcessor()
        self.log = AuditLog(fresh=fresh_log)
        self.nonces = NonceStore()

    def issue_mandate(self, max_amount_paise, categories,
                      merchants=("merch_kofi",), max_transactions=1):
        mandate = create_mandate(
            self.agent.agent_id, max_amount_paise,
            list(categories), list(merchants),
            max_transactions=max_transactions,
        )
        return sign_mandate(mandate, self.signing_key)

    def run(self, instruction, signed_mandate):
        item, why = self.agent.propose(instruction, CATALOG)
        if item is None:
            self.log.record(
                mandate_id=signed_mandate["mandate_id"],
                agent_id=self.agent.agent_id, instruction=instruction,
                decision="NO_PROPOSAL", reason_code="NO_MATCH", detail=why,
            )
            return {"decision": "NO_PROPOSAL", "reason": "NO_MATCH", "detail": why}

        challenge = self.client.post(
            "/checkout", json={"sku": item["sku"]}
        ).json()

        request = {
            "amount_paise": challenge["amount_paise"],
            "currency": challenge["currency"],
            "merchant_id": challenge["merchant_id"],
            "product_name": challenge["name"],
            "claimed_category": challenge["category"],
        }

        decision, reason, detail = evaluate(
            signed_mandate, request, self.verify_key,
            self.nonces, classifier=self.classifier,
        )

        derived, confidence, _ = self.classifier.predict(challenge["name"])

        order_id = None
        if decision == ALLOW:
            order = self.payments.create_order(
                amount_paise=challenge["amount_paise"],
                receipt="rcpt_" + uuid.uuid4().hex[:10],
                notes={
                    "mandate_id": signed_mandate["mandate_id"],
                    "sku": item["sku"],
                },
            )
            order_id = order["id"]
            self.nonces.record(signed_mandate["nonce"])
            self.client.post("/confirm", json={
                "challenge_id": challenge["challenge_id"],
                "payment_reference": order_id,
            })

        self.log.record(
            mandate_id=signed_mandate["mandate_id"],
            agent_id=self.agent.agent_id,
            instruction=instruction,
            product_name=challenge["name"],
            claimed_category=challenge["category"],
            derived_category=derived,
            confidence=round(float(confidence), 3),
            amount_paise=challenge["amount_paise"],
            merchant_id=challenge["merchant_id"],
            decision=decision, reason_code=reason,
            detail=detail, order_id=order_id,
        )

        return {
            "decision": decision, "reason": reason, "detail": detail,
            "product": challenge["name"],
            "amount_paise": challenge["amount_paise"],
            "order_id": order_id,
        }