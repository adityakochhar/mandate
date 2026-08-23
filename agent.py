from llm import GroqProvider


class BuyerAgent:
    """Proposes purchases. Has no authority to approve any of them."""

    def __init__(self, provider=None, agent_id="agent_buyer_01"):
        self.provider = provider or GroqProvider()
        self.agent_id = agent_id

    def propose(self, instruction, catalog):
        choice = self.provider.choose(instruction, catalog["items"])
        sku = choice.get("sku")
        if not sku:
            return None, choice.get("reason", "no matching item")

        item = next((i for i in catalog["items"] if i["sku"] == sku), None)
        if item is None:
            return None, f"model chose unknown sku {sku}"

        return item, choice.get("reason", "")