"""
hypothesis_gen.py – generate novel, literature-grounded research hypotheses
and identify gaps in existing work using Gemini + RAG context.
"""

import json
import re
import google.generativeai as genai
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

_MODEL_NAME = "gemini-2.0-flash"


def generate_hypotheses(topic: str, rag_context: str, papers: List[Dict], critic_feedback: str = "", previous_output: list = None) -> dict:
    model = genai.GenerativeModel(_MODEL_NAME)

    paper_titles = "\n".join(f"- {p['title']} ({p['published']})" for p in papers[:10])

    feedback_block = f"""

⚠️ RETRY — PREVIOUS ATTEMPT REJECTED (score below 7.5/10)
Reviewer feedback: {critic_feedback}
Previous output: {json.dumps(previous_output) if previous_output else 'None'}
You MUST directly fix the above issue. Name specific datasets (e.g. MIMIC-III, ImageNet, ChEMBL), real model architectures, and concrete baselines. Do NOT repeat the previous response.""" if critic_feedback and critic_feedback not in ("Looks good", "Critic unavailable", "") else ""

    prompt = f"""You are a senior research scientist with 20 years of experience in {topic}. A PhD student needs your help identifying research opportunities.

Topic: "{topic}"{feedback_block}

Recent papers found in literature:
{paper_titles}

Relevant context extracted from papers:
{rag_context[:3000]}

Your task — be thorough and specific:
1. Identify 4-5 concrete GAPS or LIMITATIONS in the existing work, grounded in the actual papers above
2. Generate 3 NOVEL, TESTABLE HYPOTHESES — each must be a real research contribution, not obvious

Return a valid JSON object:
{{
  "gaps": [
    "Gap 1: [specific limitation with context from the papers, 2-3 sentences]",
    "Gap 2: [specific limitation with context from the papers, 2-3 sentences]",
    "Gap 3: [specific limitation with context from the papers, 2-3 sentences]",
    "Gap 4: [specific limitation with context from the papers, 2-3 sentences]"
  ],
  "hypotheses": [
    {{
      "title": "Memorable, specific hypothesis title (not generic)",
      "rationale": "3-4 sentences: what gap this addresses, why it hasn't been solved, what insight makes this approach promising. Reference specific papers if relevant.",
      "experiment_setup": "3-4 sentences: exact dataset(s) to use, model architecture or method, baseline comparisons, evaluation protocol.",
      "expected_outcome": "2-3 sentences: specific quantitative targets (e.g. '5% improvement in Dice score over baseline X'), how you would know if the hypothesis is confirmed or rejected.",
      "novelty_score": 8
    }},
    {{
      "title": "Second hypothesis title",
      "rationale": "3-4 sentences of rationale",
      "experiment_setup": "3-4 sentences of experiment setup",
      "expected_outcome": "2-3 sentences of expected outcome",
      "novelty_score": 7
    }},
    {{
      "title": "Third hypothesis title",
      "rationale": "3-4 sentences of rationale",
      "experiment_setup": "3-4 sentences of experiment setup",
      "expected_outcome": "2-3 sentences of expected outcome",
      "novelty_score": 9
    }}
  ]
}}

CRITICAL: Be highly specific. Name real datasets, real architectures, real metrics. novelty_score 1-10 (10 = Nature/Science paper level). Do NOT be generic.

Return ONLY the JSON object."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)
        print(f"[Hypothesis] OK — gaps: {len(result.get('gaps', []))}, hypotheses: {len(result.get('hypotheses', []))}")
        return result
    except Exception as e:
        print(f"[Hypothesis] FAILED: {type(e).__name__}: {e}")
        raise
