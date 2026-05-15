"""
reasoning_chain.py – uses Gemini to perform Chain-of-Thought decomposition
of a research topic into structured reasoning output.
"""

import json
import re
from agents.gemini_client import get_model, MODEL_NAME as _MODEL_NAME


def generate_reasoning(topic: str, critic_feedback: str = "") -> dict:
    model = get_model()

    feedback_block = f"\n\nA quality reviewer rejected the previous attempt. Fix this specific issue: {critic_feedback}" if critic_feedback and critic_feedback != "Looks good" else ""

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
