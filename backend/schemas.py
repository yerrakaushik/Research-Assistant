from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


# ── Research Pipeline ─────────────────────────────────────────────────────────
class ResearchRequest(BaseModel):
    topic: str


class Paper(BaseModel):
    title: str
    authors: List[str]
    abstract: str
    url: str
    published: str
    relevance_score: Optional[float] = None


class Hypothesis(BaseModel):
    title: str
    rationale: str
    experiment_setup: str
    expected_outcome: str
    novelty_score: int  # 1–10


class RoadmapWeek(BaseModel):
    week: int
    goal: str
    topics: List[str]
    tasks: List[str]
    resources: List[str]


class MathFormulation(BaseModel):
    problem_type: str
    objective: str
    variables: List[str]
    constraints: List[str]
    algorithm_suggestion: str
    latex: str


class Reasoning(BaseModel):
    summary: str
    subtopics: List[str]
    key_concepts: List[str]
    difficulty_level: str
    explanation: str


class ResearchBlueprint(BaseModel):
    topic: str
    reasoning: Reasoning
    papers: List[Paper]
    gaps: List[str]
    hypotheses: List[Hypothesis]
    math_formulation: MathFormulation
    roadmap: List[RoadmapWeek]
    critic_scores: Optional[Any] = None


class SessionSummary(BaseModel):
    id: int
    topic: str
    created_at: datetime

    class Config:
        from_attributes = True
