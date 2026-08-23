from fastapi.testclient import TestClient
from merchant import app

client = TestClient(app)

r = client.get("/catalog")
assert r.status_code == 200 and len(r.json()["items"]) == 10
print(f"catalog: {len(r.json()['items'])} items")

r = client.post("/checkout", json={"sku": "SKU001"})
assert r.status_code == 402, r.status_code
challenge = r.json()
print(f"checkout returned 402: {challenge['amount_paise']} paise for {challenge['name']}")

r = client.post("/confirm", json={
    "challenge_id": challenge["challenge_id"], "payment_reference": "pay_fake_001"
})
order = r.json()
assert order["status"] == "confirmed"
print(f"order confirmed: {order['order_id']}")

r2 = client.post("/confirm", json={
    "challenge_id": challenge["challenge_id"], "payment_reference": "pay_fake_001"
})
assert r2.json()["order_id"] == order["order_id"]
print("duplicate confirm returned same order (idempotent)")

r = client.post("/checkout", json={"sku": "SKU999"})
assert r.status_code == 404
print("unknown sku rejected")

grinder = next(i for i in client.get("/catalog").json()["items"] if i["sku"] == "SKU009")
print(f"mislabelled: '{grinder['name']}' claims category '{grinder['category']}'")