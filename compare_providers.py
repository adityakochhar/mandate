import json
import time
from pathlib import Path
from agent import BuyerAgent
from llm import GroqProvider, OllamaProvider

catalog = json.loads((Path(__file__).parent / "catalog.json").read_text())

instructions = [
    "I want arabica coffee beans",
    "buy the electric kettle",
    "buy AA batteries",
    "buy the ceramic serving bowl set",
    "I need a laptop",
]

for label, provider in [("groq (hosted)", GroqProvider()),
                        ("ollama (local)", OllamaProvider())]:
    print(f"\n{label}")
    agent = BuyerAgent(provider=provider)
    start = time.time()
    for instruction in instructions:
        try:
            item, why = agent.propose(instruction, catalog)
            chosen = f"{item['sku']} {item['name']}" if item else f"none ({why})"
        except Exception as exc:
            chosen = f"ERROR {type(exc).__name__}"
        print(f"  {instruction:38} -> {chosen}")
    print(f"  total: {time.time() - start:.1f}s")
    