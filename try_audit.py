from audit import AuditLog

log = AuditLog(fresh=True)
log.record(mandate_id="mnd_demo", product_name="AA batteries 4-pack",
           claimed_category="groceries", derived_category="electronics",
           confidence=0.79, amount_paise=18000, merchant_id="merch_kofi",
           decision="DENY", reason_code="CATEGORY_NOT_ALLOWED",
           detail="merchant claim contradicted")
log.record(mandate_id="mnd_demo", product_name="Arabica coffee beans 1kg",
           claimed_category="groceries", derived_category="groceries",
           confidence=0.82, amount_paise=85000, merchant_id="merch_kofi",
           decision="ALLOW", reason_code="OK", order_id="order_TTFpBFf1e5pKKO")

for row in log.all_rows():
    print(f"{row['decision']:9} {row['reason_code']:22} {row['product_name']}")
print()
print("summary:", log.summary())