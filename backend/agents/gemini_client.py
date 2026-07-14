"""
gemini_client.py – OpenRouter-backed AI client.
Uses OpenRouter's OpenAI-compatible API so all agents work without changes.
Exposes the same get_model() interface as before, returning a wrapper object
with a generate_content(prompt) method.
"""

import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("research_assistant.gemini")

_OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not _OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY environment variable is not set.")

_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=_OPENROUTER_API_KEY,
)

# Free model on OpenRouter — auto-routes to best free model
MODEL_NAME = "openrouter/free"


class _GenerateResponse:
    """Mimics the Gemini SDK response object so all agents work unchanged."""
    def __init__(self, text: str):
        self.text = text


class _OpenRouterModel:
    """
    Drop-in replacement for genai.GenerativeModel.
    Exposes generate_content(prompt) exactly like the Gemini SDK does.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate_content(self, prompt: str) -> _GenerateResponse:
        logger.debug(f"[OpenRouter] Calling model={self.model_name}")
        response = _client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content or ""
        return _GenerateResponse(text)


def get_model(model_name: str = MODEL_NAME) -> _OpenRouterModel:
    """Returns a configured OpenRouter model instance."""
    return _OpenRouterModel(model_name)

