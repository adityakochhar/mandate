import json
from pathlib import Path
from agent import BuyerAgent

catalog = json.loads((Path(__file__).parent / "catalog.json").read_text())
agent = BuyerAgent()

for instruction in [
    "I want coffee beans, keep it under 900 rupees",
    "buy me bananas",
    "I need a laptop",
]:
    item, reason = agent.propose(instruction, catalog)
    if item:
        print(f"'{instruction}'\n  -> {item['sku']} {item['name']} ({item['price_paise']} paise)")
    else:
        print(f"'{instruction}'\n  -> no item chosen: {reason}")
    print()