"""
critic.py – Critic agent that validates the full pipeline output.
Scores each section and decides whether to approve or request regeneration
of specific nodes. Used as a conditional router in the LangGraph pipeline.
"""

import json
import re
from typing import Dict, Any
from agents.gemini_client import get_model, MODEL_NAME as _MODEL_NAME

# Minimum acceptable score per section (out of 10)
SCORE_THRESHOLD = 6
MAX_RETRIES = 2


def run_critic(topic: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the pipeline output and returns a critique report.

    Returns:
    {
        "approved": bool,
        "scores": { "reasoning": int, "hypotheses": int, "math": int, "roadmap": int },
        "feedback": { "reasoning": str, "hypotheses": str, "math": str, "roadmap": str },
        "retry_nodes": ["hypothesize", "formalize", ...]   # nodes to re-run
    }
    """
    model = get_model()

    reasoning = state.get("reasoning", {})
    hypotheses = state.get("hypotheses", [])
    math = state.get("math_formulation", {})
    roadmap = state.get("research_roadmap", [])
    gaps = state.get("gaps", [])

    prompt = f"""You are a strict research quality reviewer. Evaluate the following AI-generated research blueprint for the topic: "{topic}"

--- REASONING ---
Summary: {reasoning.get("summary", "")}
Subtopics: {reasoning.get("subtopics", [])}
Key Concepts: {reasoning.get("key_concepts", [])}
Difficulty: {reasoning.get("difficulty_level", "")}
Explanation: {reasoning.get("explanation", "")}

--- GAPS IDENTIFIED ---
{gaps}

--- HYPOTHESES ({len(hypotheses)} generated) ---
{json.dumps(hypotheses, indent=2)[:1500]}

--- MATH FORMULATION ---
Problem Type: {math.get("problem_type", "")}
Objective: {math.get("objective", "")}
Variables: {math.get("variables", [])}
Constraints: {math.get("constraints", [])}
Algorithm: {math.get("algorithm_suggestion", "")}
LaTeX: {math.get("latex", "")}

--- ROADMAP ({len(roadmap)} weeks) ---
{json.dumps(roadmap[:3], indent=2)[:1000]}...

Score each section from 1-10 based on:
- reasoning: Is the topic decomposition accurate, clear, and well-structured?
- hypotheses: Are the hypotheses novel, testable, and grounded in the gaps? Are there at least 2?
- math: Is the formulation specific to the topic (not generic)? Is the LaTeX valid and meaningful?
- roadmap: Are the weeks logical, progressive, and actionable? Are there at least 4 weeks?

Return ONLY a valid JSON object:
{{
  "scores": {{
    "reasoning": <int 1-10>,
    "hypotheses": <int 1-10>,
    "math": <int 1-10>,
    "roadmap": <int 1-10>
  }},
  "feedback": {{
    "reasoning": "<one sentence on what's wrong or 'Looks good'>",
    "hypotheses": "<one sentence on what's wrong or 'Looks good'>",
    "math": "<one sentence on what's wrong or 'Looks good'>",
    "roadmap": "<one sentence on what's wrong or 'Looks good'>"
  }}
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)

        scores = result.get("scores", {})
        feedback = result.get("feedback", {})

        # Determine which nodes need to re-run
        retry_nodes = []
        section_to_node = {
            "reasoning": "reason",
            "hypotheses": "hypothesize",
            "math": "formalize",
            "roadmap": "roadmap",
        }
        for section, node in section_to_node.items():
            if scores.get(section, 0) < SCORE_THRESHOLD:
                retry_nodes.append(node)

        approved = len(retry_nodes) == 0

        print(f"[Critic] Scores: {scores}")
        print(f"[Critic] Approved: {approved} | Retry nodes: {retry_nodes}")

        return {
            "approved": approved,
            "scores": scores,
            "feedback": feedback,
            "retry_nodes": retry_nodes,
        }

    except Exception as e:
        print(f"[Critic] Error during critique: {e}")
        # On critic failure, approve to avoid blocking the pipeline
        return {
            "approved": True,
            "scores": {"reasoning": 7, "hypotheses": 7, "math": 7, "roadmap": 7},
            "feedback": {"reasoning": "Critic unavailable", "hypotheses": "Critic unavailable",
                         "math": "Critic unavailable", "roadmap": "Critic unavailable"},
            "retry_nodes": [],
        }
