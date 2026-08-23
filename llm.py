import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class LLMProvider:
    """Anything that can turn a shopping request into a chosen SKU."""

    def choose(self, instruction, catalog_items):
        raise NotImplementedError


class GroqProvider(LLMProvider):
    def __init__(self, model="openai/gpt-oss-20b"):
        self.model = model
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ["GROQ_API_KEY"],
        )

    def choose(self, instruction, catalog_items):
        listing = "\n".join(
            f"{i['sku']}: {i['name']} — {i['price_paise']} paise"
            for i in catalog_items
        )
        prompt = (
            "You are a shopping assistant. Pick ONE item that best matches "
            "the request, or none if nothing fits.\n\n"
            f"Catalog:\n{listing}\n\n"
            f"Request: {instruction}\n\n"
            'Reply with JSON only: {"sku": "SKU001", "reason": "..."} '
            'or {"sku": null, "reason": "..."}'
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)


class OllamaProvider(GroqProvider):
    """Same prompt, same parsing — different endpoint. Runs locally, no API key."""

    def __init__(self, model="qwen2.5-coder:14b", base_url="http://localhost:11434/v1"):
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key="ollama")