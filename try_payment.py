from payments import PaymentProcessor

p = PaymentProcessor()
order = p.create_order(
    amount_paise=85000,
    receipt="rcpt_test_001",
    notes={"mandate_id": "mnd_demo", "sku": "SKU001"},
)

print(f"order id:  {order['id']}")
print(f"amount:    {order['amount']} paise")
print(f"status:    {order['status']}")
print(f"receipt:   {order['receipt']}")
print(f"notes:     {order['notes']}")