"""
math_formulation.py – translates a research topic/hypothesis into
formal mathematical / optimization formulation using Gemini.
"""

import json
import re
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

_MODEL_NAME = "gemini-2.0-flash"


def generate_math_formulation(topic: str, reasoning_summary: str, critic_feedback: str = "", previous_output: dict = None) -> dict:
    """
    Generates a formal mathematical formulation for the research topic.
    Returns a dict matching the MathFormulation schema.
    """
    model = genai.GenerativeModel(_MODEL_NAME)

    feedback_block = f"""

⚠️ RETRY — PREVIOUS ATTEMPT REJECTED (score below 7.5/10)
Reviewer feedback: {critic_feedback}
Previous output: {json.dumps(previous_output) if previous_output else 'None'}
You MUST directly fix the above issue. Use domain-specific variable names, a topic-specific LaTeX equation (not a generic loss function), and real algorithm names. Do NOT repeat the previous response.""" if critic_feedback and critic_feedback not in ("Looks good", "Critic unavailable", "") else ""

    prompt = f"""You are an expert at translating research ideas into formal mathematical language.

Research Topic: "{topic}"
Context: {reasoning_summary}{feedback_block}

Formalize this research problem mathematically. Return a valid JSON object:
{{
  "problem_type": "Optimization | Classification | Regression | Generative | Graph | Reinforcement Learning | Statistical Modeling",
  "objective": "Plain English description only — NO LaTeX, NO backslashes, NO math symbols. E.g. 'Minimize the reconstruction error between the observed signal and the estimated components, with regularization penalties.'",
  "variables": [
    "x: plain English description of what this variable represents",
    "theta: plain English description",
    "y: plain English description"
  ],
  "constraints": [
    "Plain English constraint description only — no LaTeX",
    "Another plain English constraint"
  ],
  "algorithm_suggestion": "Plain English only — name the algorithm and explain why it fits in 2 sentences. No LaTeX.",
  "latex": "The core equation in LaTeX for KaTeX rendering only. Use double backslashes. E.g. \\\\min_{{\\\\theta}} \\\\sum_{{i=1}}^{{n}} \\\\mathcal{{L}}(f_\\\\theta(x_i), y_i) + \\\\lambda \\\\|\\\\theta\\\\|^2"
}}

CRITICAL RULES:
- objective, variables, constraints, algorithm_suggestion must be PLAIN ENGLISH ONLY — absolutely no LaTeX, no backslashes, no \\mathbf, no \\hat, no math notation
- Use words like "estimated matrix", "parameter vector", "input signal" instead of math symbols in text fields
- Only the "latex" field should contain LaTeX notation
- latex must be valid KaTeX (use double backslashes \\\\)
- Be specific to the topic, not generic
- variables list should have 3-5 items

Return ONLY the JSON object."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)
    except Exception as e:
        print(f"[Math] Error: {e}")
        return {
            "problem_type": "Optimization",
            "objective": f"Minimize the loss function L(θ) over the parameter space for {topic}",
            "variables": ["θ: model parameters", "X: input feature matrix", "y: target output"],
            "constraints": ["θ ∈ feasible parameter space", "Training data X must be normalized"],
            "algorithm_suggestion": "Stochastic Gradient Descent (SGD) is recommended due to its scalability with large datasets.",
            "latex": "\\min_{\\theta} \\frac{1}{n} \\sum_{i=1}^{n} \\mathcal{L}(f_{\\theta}(x_i), y_i) + \\lambda \\|\\theta\\|_2^2",
        }
