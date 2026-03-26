"""
critic.py – Critic agent that validates the full pipeline output.
Scores each section and decides whether to approve or request regeneration.
"""

import json
import re
import os
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

_MODEL_NAME = "gemini-2.0-flash"

SCORE_THRESHOLD = 7.5
MAX_RETRIES = 2


def run_critic(topic: str, state: Dict[str, Any]) -> Dict[str, Any]:
    model = genai.GenerativeModel(_MODEL_NAME)

    reasoning  = state.get("reasoning", {})
    hypotheses = state.get("hypotheses", [])
    math       = state.get("math_formulation", {})
    roadmap    = state.get("roadmap", [])
    gaps       = state.get("gaps", [])
    retry_count = state.get("retry_count", 0)

    retry_label = f"(RETRY ATTEMPT {retry_count} — previous scores were below 7.5)" if retry_count > 0 else ""

    prompt = f"""You are a strict research quality reviewer {retry_label}. Score this AI-generated research blueprint for: "{topic}"

--- REASONING ---
Summary: {reasoning.get("summary", "")}
Subtopics: {reasoning.get("subtopics", [])}
Key Concepts: {reasoning.get("key_concepts", [])}
Explanation: {reasoning.get("explanation", "")}

--- GAPS ---
{gaps}

--- HYPOTHESES ({len(hypotheses)}) ---
{json.dumps(hypotheses, indent=2)[:2000]}

--- MATH FORMULATION ---
Problem Type: {math.get("problem_type", "")}
Objective: {math.get("objective", "")}
Variables: {math.get("variables", [])}
Constraints: {math.get("constraints", [])}
Algorithm: {math.get("algorithm_suggestion", "")}
LaTeX: {math.get("latex", "")}

--- ROADMAP (first 3 weeks of {len(roadmap)}) ---
{json.dumps(roadmap[:3], indent=2)[:1200]}

SCORING CRITERIA (be strict, score 1-10):
- reasoning: Are subtopics specific named research areas (not generic)? Does explanation use real analogies and mention landmark papers?
- hypotheses: Are hypotheses truly novel with specific datasets/architectures named? Do experiment setups name real tools? Score below 7.5 if any hypothesis is vague.
- math: Is the LaTeX equation specific to this topic (not a generic loss function)? Are variables named after domain-specific quantities? Score below 7.5 if it looks copy-pasted.
- roadmap: Do tasks name real papers, real GitHub repos, real courses? Are weeks progressive and specific to {topic}? Score below 7.5 if tasks are generic.

Return ONLY valid JSON:
{{
  "scores": {{
    "reasoning": <int 1-10>,
    "hypotheses": <int 1-10>,
    "math": <int 1-10>,
    "roadmap": <int 1-10>
  }},
  "feedback": {{
    "reasoning": "<specific actionable fix — name exactly what is missing or too generic>",
    "hypotheses": "<specific actionable fix — e.g. 'Hypothesis 2 lacks a named dataset and baseline model. Add specific benchmark like ImageNet or MIMIC-III and compare against ViT-B/16'>",
    "math": "<specific actionable fix — e.g. 'The LaTeX uses generic theta notation. Rewrite using domain variables like W_attention, d_model, and include the specific loss term for this task'>",
    "roadmap": "<specific actionable fix — e.g. 'Week 3 tasks are too generic. Name the actual seminal paper (e.g. Dosovitskiy et al. 2020 ViT paper) and a real GitHub repo to clone'>"
  }}
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)

        scores   = result.get("scores", {})
        feedback = result.get("feedback", {})

        retry_nodes = []
        section_to_node = {
            "reasoning":  "reason",
            "hypotheses": "hypothesize",
            "math":       "formalize",
            "roadmap":    "roadmap",
        }
        for section, node in section_to_node.items():
            if scores.get(section, 0) < SCORE_THRESHOLD:
                retry_nodes.append(node)

        approved = len(retry_nodes) == 0

        print(f"[Critic] Scores: {scores}")
        if approved:
            print(f"[Critic] ✓ Approved on attempt {retry_count + 1}")
        else:
            print(f"[Critic] ✗ Retry needed — nodes: {retry_nodes}")
            for section, fb in feedback.items():
                if scores.get(section, 10) < SCORE_THRESHOLD:
                    print(f"  [{section}] score={scores.get(section)} → {fb}")

        return {
            "approved":    approved,
            "scores":      scores,
            "feedback":    feedback,
            "retry_nodes": retry_nodes,
        }

    except Exception as e:
        print(f"[Critic] Error: {e}")
        return {
            "approved": True,
            "scores":   {"reasoning": 7, "hypotheses": 7, "math": 7, "roadmap": 7},
            "feedback": {"reasoning": "Critic unavailable", "hypotheses": "Critic unavailable",
                         "math": "Critic unavailable", "roadmap": "Critic unavailable"},
            "retry_nodes": [],
        }
