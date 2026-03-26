"""
agent_graph.py – LangGraph-based orchestration pipeline with step callbacks.
Pipeline: reason → search → rag → hypothesize → formalize → roadmap → critic
Critic validates quality and loops back to failing nodes (max 2 retries).
"""

from typing import TypedDict, List, Dict, Any, Optional, Callable
from langgraph.graph import StateGraph, END
from agents.reasoning_chain import generate_reasoning
from agents.arxiv_search import search_arxiv
from agents.rag_engine import query_rag
from agents.hypothesis_gen import generate_hypotheses
from agents.math_formulation import generate_math_formulation
from agents.roadmap_gen import generate_roadmap
from agents.critic import run_critic, MAX_RETRIES
from agents.evaluator import evaluate_and_print, compute_rus
import time

_CALL_DELAY = 4  # seconds between Gemini calls to respect RPM limits


# ── State ─────────────────────────────────────────────────────────────────────
class ResearchState(TypedDict):
    topic: str
    reasoning: Dict[str, Any]
    papers: List[Dict[str, Any]]
    rag_context: str
    gaps: List[str]
    hypotheses: List[Dict[str, Any]]
    math_formulation: Dict[str, Any]
    roadmap: List[Dict[str, Any]]
    retry_count: int
    critic_feedback: Optional[Dict[str, Any]]
    critic_scores: Optional[Dict[str, int]]
    _on_step: Optional[Any]
    _pre_retry_snapshot: Optional[Dict[str, Any]]  # state before first retry


# ── Nodes ─────────────────────────────────────────────────────────────────────
def reason_node(state: ResearchState) -> ResearchState:
    _emit(state, 1, "Structured Reasoning")
    feedback = _get_feedback(state, "reasoning")
    reasoning = generate_reasoning(state["topic"], critic_feedback=feedback, previous_output=state.get("reasoning"))
    time.sleep(_CALL_DELAY)
    return {**state, "reasoning": reasoning}


def search_node(state: ResearchState) -> ResearchState:
    _emit(state, 2, "ArXiv Paper Search")
    papers = search_arxiv(state["topic"], max_results=15)
    return {**state, "papers": papers}


def rag_node(state: ResearchState) -> ResearchState:
    _emit(state, 3, "RAG Gap Analysis")
    context = query_rag(
        f"What are the key limitations, open problems, and research gaps in {state['topic']}?",
        state["papers"],
        top_k=5,
    )
    return {**state, "rag_context": context}


def hypothesize_node(state: ResearchState) -> ResearchState:
    _emit(state, 4, "Hypothesis Generation")
    feedback = _get_feedback(state, "hypotheses")
    result = generate_hypotheses(state["topic"], state["rag_context"], state["papers"], critic_feedback=feedback, previous_output=state.get("hypotheses"))
    time.sleep(_CALL_DELAY)
    return {**state, "gaps": result.get("gaps", []), "hypotheses": result.get("hypotheses", [])}


def formalize_node(state: ResearchState) -> ResearchState:
    _emit(state, 5, "Math Formulation")
    feedback = _get_feedback(state, "math")
    summary = state["reasoning"].get("summary", state["topic"])
    math = generate_math_formulation(state["topic"], summary, critic_feedback=feedback, previous_output=state.get("math_formulation"))
    time.sleep(_CALL_DELAY)
    return {**state, "math_formulation": math}


def roadmap_node(state: ResearchState) -> ResearchState:
    _emit(state, 6, "Roadmap Generation")
    feedback = _get_feedback(state, "roadmap")
    subtopics = state["reasoning"].get("subtopics", [])
    difficulty = state["reasoning"].get("difficulty_level", "Intermediate")
    roadmap = generate_roadmap(state["topic"], subtopics, difficulty, critic_feedback=feedback, previous_output=state.get("roadmap"))
    time.sleep(_CALL_DELAY)
    return {**state, "roadmap": roadmap}


def critic_node(state: ResearchState) -> ResearchState:
    retry_count = state.get("retry_count", 0)
    _emit(state, 7, f"Critic Validation (attempt {retry_count + 1})")
    critique = run_critic(state["topic"], state)
    time.sleep(_CALL_DELAY)

    retry_nodes = critique.get("retry_nodes", [])
    approved    = critique.get("approved", True)

    # Snapshot the current output before the first retry so we can measure improvement
    pre_retry_snapshot = state.get("_pre_retry_snapshot")
    if not approved and retry_nodes and retry_count == 0 and pre_retry_snapshot is None:
        pre_retry_snapshot = {
            "topic":            state["topic"],
            "reasoning":        state["reasoning"],
            "hypotheses":       state["hypotheses"],
            "math_formulation": state["math_formulation"],
            "roadmap":          state["roadmap"],
            "gaps":             state["gaps"],
            "papers":           state["papers"],
            "retry_nodes":      retry_nodes,
            "critic_scores":    critique.get("scores", {}),  # scores BEFORE retry
        }
        print(f"[Critic] 📸 Snapshot taken before retry — nodes: {retry_nodes}")

    return {
        **state,
        "retry_count":        retry_count + 1,
        "critic_feedback":    critique.get("feedback", {}),
        "critic_scores":      critique.get("scores", {}),
        "_retry_nodes":       retry_nodes,
        "_approved":          approved,
        "_pre_retry_snapshot": pre_retry_snapshot,
    }


# ── Router ────────────────────────────────────────────────────────────────────
def critic_router(state: ResearchState) -> str:
    approved    = state.get("_approved", True)
    retry_count = state.get("retry_count", 0)
    retry_nodes = state.get("_retry_nodes", [])

    if approved:
        print(f"[Critic] ✓ All scores above threshold. Final scores: {state.get('critic_scores')}")
        return "end"

    if retry_count > MAX_RETRIES:
        print(f"[Critic] Max retries ({MAX_RETRIES}) reached — accepting output as-is. "
              f"Final scores: {state.get('critic_scores')}")
        return "end"

    if not retry_nodes:
        return "end"

    node_order = ["reason", "hypothesize", "formalize", "roadmap"]
    for node in node_order:
        if node in retry_nodes:
            print(f"[Critic] → Retrying '{node}' (attempt {retry_count + 1}/{MAX_RETRIES})...")
            return node

    return "end"


# ── Helpers ───────────────────────────────────────────────────────────────────
def _get_feedback(state: ResearchState, section: str) -> str:
    feedback = state.get("critic_feedback") or {}
    return feedback.get(section, "")


def _emit(state: ResearchState, step: int, label: str):
    cb = state.get("_on_step")
    if callable(cb):
        cb(step, label)
    print(f"[Pipeline] Step {step} — {label}")


# ── Build ─────────────────────────────────────────────────────────────────────
def build_pipeline() -> StateGraph:
    graph = StateGraph(ResearchState)
    graph.add_node("reason", reason_node)
    graph.add_node("search", search_node)
    graph.add_node("rag", rag_node)
    graph.add_node("hypothesize", hypothesize_node)
    graph.add_node("formalize", formalize_node)
    graph.add_node("roadmap", roadmap_node)
    graph.add_node("critic", critic_node)

    graph.set_entry_point("reason")
    graph.add_edge("reason", "search")
    graph.add_edge("search", "rag")
    graph.add_edge("rag", "hypothesize")
    graph.add_edge("hypothesize", "formalize")
    graph.add_edge("formalize", "roadmap")
    graph.add_edge("roadmap", "critic")
    graph.add_conditional_edges("critic", critic_router, {
        "end": END,
        "reason": "reason",
        "hypothesize": "hypothesize",
        "formalize": "formalize",
        "roadmap": "roadmap",
    })
    return graph.compile()


_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


def run_pipeline(topic: str, on_step: Optional[Callable] = None) -> dict:
    pipeline = get_pipeline()
    initial_state: ResearchState = {
        "topic": topic,
        "reasoning": {},
        "papers": [],
        "rag_context": "",
        "gaps": [],
        "hypotheses": [],
        "math_formulation": {},
        "roadmap": [],
        "retry_count": 0,
        "critic_feedback": None,
        "critic_scores": None,
        "_on_step": on_step,
        "_pre_retry_snapshot": None,
    }
    final_state = pipeline.invoke(initial_state)
    result = {
        "topic": final_state["topic"],
        "reasoning": final_state["reasoning"],
        "papers": final_state["papers"],
        "gaps": final_state["gaps"],
        "hypotheses": final_state["hypotheses"],
        "math_formulation": final_state["math_formulation"],
        "roadmap": final_state["roadmap"],
        "critic_scores": final_state.get("critic_scores"),
    }
    try:
        evaluate_and_print(result, pre_retry_snapshot=final_state.get("_pre_retry_snapshot"))
    except Exception as e:
        import traceback
        print(f"\n[Evaluator] ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
    return result
