"""
reasoning_chain.py – uses Gemini to perform Chain-of-Thought decomposition
of a research topic into structured reasoning output.
"""

import json
import re
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

_MODEL_NAME = "gemini-2.0-flash"


def generate_reasoning(topic: str, critic_feedback: str = "", previous_output: dict = None) -> dict:
    model = genai.GenerativeModel(_MODEL_NAME)

    feedback_block = f"""

⚠️ RETRY — PREVIOUS ATTEMPT REJECTED (score below 7.5/10)
Reviewer feedback: {critic_feedback}
Previous output: {json.dumps(previous_output) if previous_output else 'None'}
You MUST directly fix the above issue. Do NOT repeat the previous response. Be more specific, name real papers/datasets/tools.""" if critic_feedback and critic_feedback not in ("Looks good", "Critic unavailable", "") else ""

    prompt = f"""You are a world-class research advisor with deep expertise across computer science, biology, physics, and engineering. A student has asked you to explain a research topic in depth.

Topic: "{topic}"{feedback_block}

Perform a thorough Chain-of-Thought analysis. Return a valid JSON object:
{{
  "summary": "A rich 3-4 sentence overview covering what the field is, why it exists, and what problems it solves. Be specific to the topic.",
  "subtopics": [
    "Specific subtopic 1 (e.g. 'Convolutional Neural Networks for feature extraction')",
    "Specific subtopic 2 (e.g. 'Transfer learning and domain adaptation')",
    "Specific subtopic 3 (e.g. 'Attention mechanisms and Vision Transformers')",
    "Specific subtopic 4 (e.g. 'Semi-supervised and self-supervised learning')",
    "Specific subtopic 5 (e.g. 'Evaluation metrics: Dice score, IoU, Hausdorff distance')"
  ],
  "key_concepts": [
    "Specific concept 1 with brief definition",
    "Specific concept 2 with brief definition",
    "Specific concept 3 with brief definition",
    "Specific concept 4 with brief definition",
    "Specific concept 5 with brief definition",
    "Specific concept 6 with brief definition"
  ],
  "difficulty_level": "Beginner | Intermediate | Advanced",
  "explanation": "A detailed 6-8 sentence explanation. Start with a real-world analogy. Explain the core technical challenge. Describe why existing approaches fall short. Explain what makes this topic exciting for research. Mention 1-2 real landmark papers or breakthroughs. End with what a beginner should focus on first."
}}

CRITICAL: Be highly specific to '{topic}'. Do NOT give generic answers like 'Foundations', 'Current Methods', 'Open Problems'. Give real, named subtopics and concepts specific to this field.

Return ONLY the JSON object."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)
        print(f"[Reasoning] OK — difficulty: {result.get('difficulty_level')}, subtopics: {len(result.get('subtopics', []))}")
        return result
    except Exception as e:
        print(f"[Reasoning] FAILED: {type(e).__name__}: {e}")
        raise
