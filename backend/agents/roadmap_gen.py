"""
roadmap_gen.py – generates a beginner-friendly week-by-week learning
and research roadmap tailored to the topic and difficulty level.
"""

import json
import re
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

_MODEL_NAME = "gemini-2.0-flash"


def generate_roadmap(topic: str, subtopics: list, difficulty_level: str, critic_feedback: str = "", previous_output: list = None) -> list:
    model = genai.GenerativeModel(_MODEL_NAME)
    subtopics_str = ", ".join(subtopics[:5]) if subtopics else topic
    num_weeks = {"Beginner": 10, "Intermediate": 12, "Advanced": 14}.get(difficulty_level, 10)
    feedback_block = f"""

⚠️ RETRY — PREVIOUS ATTEMPT REJECTED (score below 7.5/10)
Reviewer feedback: {critic_feedback}
Previous output: {json.dumps(previous_output) if previous_output else 'None'}
You MUST directly fix the above issue. Name real papers with authors and years, real GitHub repos, real courses (Coursera, fast.ai, etc.). Do NOT repeat the previous response.""" if critic_feedback and critic_feedback not in ("Looks good", "Critic unavailable", "") else ""

    prompt = f"""You are a research mentor who has guided 50+ students from zero to publishing their first paper.

Research Topic: "{topic}"
Key Subtopics: {subtopics_str}
Student Level: {difficulty_level}
Duration: {num_weeks} weeks{feedback_block}

Return a JSON array with EXACTLY {num_weeks} week objects. Each week:
{{
  "week": <number>,
  "goal": "One specific measurable goal",
  "topics": ["Specific topic 1", "Specific topic 2", "Specific topic 3"],
  "tasks": ["Task 1 naming real tools/papers/datasets", "Task 2", "Task 3", "Task 4"],
  "resources": ["Real named resource (type)", "Real named resource 2 (type)", "Real named resource 3 (type)"]
}}

Week structure:
- Weeks 1-2: Math + Python/PyTorch setup
- Weeks 3-4: Core concepts + seminal papers in {topic}
- Weeks 5-6: Reproduce a paper result from {topic}
- Weeks 7-8: Implement a baseline system
- Weeks 9+: Novel experiments, ablation studies, writeup

Name real papers, datasets, GitHub repos, courses. Be extremely specific to {topic}.
Return ONLY the JSON array, no extra text."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        roadmap = json.loads(text)
        if isinstance(roadmap, list):
            print(f"[Roadmap] OK — {len(roadmap)} weeks generated")
            return roadmap
        return roadmap.get("roadmap", roadmap.get("weeks", []))
    except Exception as e:
        print(f"[Roadmap] FAILED: {type(e).__name__}: {e}")
        raise
