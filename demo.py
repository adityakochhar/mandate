from run import Runtime

rt = Runtime()

print("=" * 62)
print("MANDATE — bounded spending authority for AI agents")
print("=" * 62)

m = rt.issue_mandate(100000, ["groceries"], max_transactions=3)
print(f"\nmandate {m['mandate_id']}")
print(f"  limit      : 100000 paise")
print(f"  categories : {m['scope']['categories']}")
print(f"  merchants  : {m['scope']['merchant_allowlist']}\n")

scenarios = [
    ("1. In-scope purchase", "I want arabica coffee beans"),
    ("2. Over the limit", "buy the electric kettle"),
    ("3. Merchant lies about category", "buy AA batteries"),
    ("4. Model not confident", "buy the stainless steel cookware set"),
]

for title, instruction in scenarios:
    print("-" * 62)
    print(f"{title}\n  request: \"{instruction}\"")
    r = rt.run(instruction, m)
    print(f"  product: {r.get('product', '—')}")
    print(f"  RESULT : {r['decision']} ({r['reason']})")
    print(f"  detail : {r['detail']}")
    if r.get("order_id"):
        print(f"  order  : {r['order_id']}")

print("-" * 62)
print("\nAUDIT TRAIL")
print(f"{'decision':10} {'reason':22} {'claimed':12} {'derived':12} conf")
for row in rt.log.all_rows():
    print(f"{row['decision']:10} {row['reason_code']:22} "
          f"{str(row['claimed_category']):12} {str(row['derived_category']):12} "
          f"{row['confidence']}")