import json, uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Kofi General Store")
CATALOG = json.loads((Path(__file__).parent / "catalog.json").read_text())
ITEMS = {i["sku"]: i for i in CATALOG["items"]}
CHALLENGES = {}
ORDERS = {}


class CheckoutRequest(BaseModel):
    sku: str
    quantity: int = 1


class ConfirmRequest(BaseModel):
    challenge_id: str
    payment_reference: str


@app.get("/catalog")
def get_catalog():
    return CATALOG


@app.post("/checkout")
def checkout(body: CheckoutRequest):
    item = ITEMS.get(body.sku)
    if item is None:
        raise HTTPException(404, "unknown sku")
    if item["in_stock"] < body.quantity:
        raise HTTPException(409, "insufficient stock")

    challenge_id = "chl_" + uuid.uuid4().hex[:12]
    challenge = {
        "challenge_id": challenge_id,
        "merchant_id": CATALOG["merchant_id"],
        "sku": item["sku"],
        "name": item["name"],
        "category": item["category"],
        "quantity": body.quantity,
        "amount_paise": item["price_paise"] * body.quantity,
        "currency": "INR",
    }
    CHALLENGES[challenge_id] = challenge
    return JSONResponse(status_code=402, content=challenge)


@app.post("/confirm")
def confirm(body: ConfirmRequest):
    challenge = CHALLENGES.get(body.challenge_id)
    if challenge is None:
        raise HTTPException(404, "unknown challenge")
    if body.challenge_id in ORDERS:
        return ORDERS[body.challenge_id]

    item = ITEMS[challenge["sku"]]
    if item["in_stock"] < challenge["quantity"]:
        raise HTTPException(409, "insufficient stock")
    item["in_stock"] -= challenge["quantity"]

    order = {
        "order_id": "ord_" + uuid.uuid4().hex[:12],
        "challenge_id": body.challenge_id,
        "sku": challenge["sku"],
        "amount_paise": challenge["amount_paise"],
        "payment_reference": body.payment_reference,
        "status": "confirmed",
    }
    ORDERS[body.challenge_id] = order
    return order