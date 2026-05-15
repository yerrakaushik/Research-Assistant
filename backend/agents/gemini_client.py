"""
gemini_client.py – Centralized Gemini API client initialization.
All agents import from here instead of each calling genai.configure() separately.
"""

import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("research_assistant.gemini")

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not _GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

genai.configure(api_key=_GEMINI_API_KEY)

MODEL_NAME = "gemini-2.0-flash"


def get_model(model_name: str = MODEL_NAME) -> genai.GenerativeModel:
    """Returns a configured GenerativeModel instance."""
    return genai.GenerativeModel(model_name)
