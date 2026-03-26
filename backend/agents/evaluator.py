"""
evaluator.py – Multi-dimensional evaluation of the research pipeline output.
Prints a structured metrics report to the terminal after each generation.

Dimensions:
  1. Reasoning Quality       – coherence, step validity, dependency accuracy
  2. Formalization Accuracy  – objective correctness, symbol consistency, constraint validity
  3. Hypothesis Quality      – novelty (embedding similarity), feasibility, relevance
  4. Generation Quality      – BLEU, ROUGE-L, BERTScore (hypothesis text)
  5. Interpretability        – clarity of reasoning traces
  6. End-to-End Utility      – composite Research Utility Score (RUS)
  7. Ablation Summary        – per-module contribution estimate
"""

import re
import math
import time
from typing import Dict, Any

# ── Optional heavy deps (graceful fallback if unavailable) ────────────────────
try:
    from rouge_score import rouge_scorer as _rouge_scorer
    _ROUGE_OK = True
except ImportError:
    _ROUGE_OK = False

try:
    import nltk
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    _BLEU_OK = True
except ImportError:
    _BLEU_OK = False

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    _ST_MODEL = None
    _ST_OK = True
except ImportError:
    _ST_OK = False


def _get_st_model():
    global _ST_MODEL
    if _ST_MODEL is None and _ST_OK:
        _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _ST_MODEL


# ── Individual metric functions ───────────────────────────────────────────────

def _reasoning_quality(reasoning: Dict) -> Dict[str, float]:
    """Heuristic scoring of reasoning output."""
    summary = reasoning.get("summary", "")
    subtopics = reasoning.get("subtopics", [])
    key_concepts = reasoning.get("key_concepts", [])
    explanation = reasoning.get("explanation", "")

    # Logical coherence: length + sentence count of summary/explanation
    total_words = len(summary.split()) + len(explanation.split())
    coherence = min(1.0, total_words / 120)

    # Step validity: subtopics are specific (not generic fallback)
    generic = {"foundations", "current methods", "open problems"}
    specific = [s for s in subtopics if s.lower() not in generic]
    step_validity = len(specific) / max(len(subtopics), 1)

    # Dependency accuracy: key concepts present and non-trivial
    dep_accuracy = min(1.0, len(key_concepts) / 5)

    return {
        "logical_coherence":   round(coherence, 3),
        "step_validity":       round(step_validity, 3),
        "dependency_accuracy": round(dep_accuracy, 3),
    }


def _formalization_accuracy(math_form: Dict) -> Dict[str, float]:
    """Score the math formulation section."""
    latex = math_form.get("latex", "")
    variables = math_form.get("variables", [])
    constraints = math_form.get("constraints", [])
    objective = math_form.get("objective", "")

    # Objective correctness: non-empty, specific (not generic)
    obj_score = 0.0
    if objective and len(objective.split()) > 8:
        obj_score = 1.0 if "minimize" in objective.lower() or "maximize" in objective.lower() or "estimate" in objective.lower() else 0.7

    # Symbol consistency: LaTeX has real math symbols
    latex_symbols = len(re.findall(r'\\[a-zA-Z]+', latex))
    sym_score = min(1.0, latex_symbols / 5)

    # Constraint validity: at least 2 meaningful constraints
    valid_constraints = [c for c in constraints if len(c.split()) > 3]
    con_score = min(1.0, len(valid_constraints) / 2)

    return {
        "objective_correctness": round(obj_score, 3),
        "symbol_consistency":    round(sym_score, 3),
        "constraint_validity":   round(con_score, 3),
    }


def _hypothesis_quality(hypotheses: list, topic: str) -> Dict[str, float]:
    """Score hypotheses on novelty, feasibility, relevance."""
    if not hypotheses:
        return {"novelty": 0.0, "feasibility": 0.0, "relevance": 0.0}

    novelty_scores, feasibility_scores, relevance_scores = [], [], []

    model = _get_st_model() if _ST_OK else None

    for h in hypotheses:
        title = h.get("title", "")
        rationale = h.get("rationale", "")
        setup = h.get("experiment_setup", "")
        raw_novelty = h.get("novelty_score", 5)

        # Novelty: use LLM-assigned score + embedding distance from topic
        base_novelty = raw_novelty / 10.0
        if model and title:
            emb_topic = model.encode([topic], normalize_embeddings=True)
            emb_hyp   = model.encode([title], normalize_embeddings=True)
            similarity = float(np.dot(emb_topic[0], emb_hyp[0]))
            # Lower similarity = more novel
            embedding_novelty = 1.0 - max(0.0, similarity)
            novelty = (base_novelty * 0.6 + embedding_novelty * 0.4)
        else:
            novelty = base_novelty
        novelty_scores.append(novelty)

        # Feasibility: experiment_setup mentions concrete methods/datasets
        concrete_keywords = ["dataset", "model", "baseline", "train", "evaluate",
                             "benchmark", "accuracy", "f1", "precision", "recall",
                             "implement", "experiment", "compare"]
        hits = sum(1 for kw in concrete_keywords if kw in setup.lower())
        feasibility_scores.append(min(1.0, hits / 4))

        # Relevance: rationale references the topic words
        topic_words = set(topic.lower().split())
        rationale_words = set(rationale.lower().split())
        overlap = len(topic_words & rationale_words) / max(len(topic_words), 1)
        relevance_scores.append(min(1.0, overlap * 3))

    return {
        "novelty":      round(sum(novelty_scores) / len(novelty_scores), 3),
        "feasibility":  round(sum(feasibility_scores) / len(feasibility_scores), 3),
        "relevance":    round(sum(relevance_scores) / len(relevance_scores), 3),
    }


def _generation_quality(hypotheses: list, reasoning: Dict) -> Dict[str, float]:
    """BLEU, ROUGE-L on hypothesis text vs reasoning summary as reference."""
    if not hypotheses:
        return {"bleu": 0.0, "rouge_l": 0.0, "bertscore_approx": 0.0}

    reference = reasoning.get("summary", "") + " " + reasoning.get("explanation", "")
    if not reference.strip():
        return {"bleu": 0.0, "rouge_l": 0.0, "bertscore_approx": 0.0}

    hypothesis_text = " ".join(
        h.get("rationale", "") + " " + h.get("experiment_setup", "")
        for h in hypotheses
    )

    # BLEU
    bleu = 0.0
    if _BLEU_OK and hypothesis_text.strip():
        try:
            ref_tokens = reference.lower().split()
            hyp_tokens = hypothesis_text.lower().split()
            sf = SmoothingFunction().method1
            bleu = sentence_bleu([ref_tokens], hyp_tokens, smoothing_function=sf)
        except Exception:
            bleu = 0.0

    # ROUGE-L
    rouge_l = 0.0
    if _ROUGE_OK and hypothesis_text.strip():
        try:
            scorer = _rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
            scores = scorer.score(reference, hypothesis_text)
            rouge_l = scores["rougeL"].fmeasure
        except Exception:
            rouge_l = 0.0

    # BERTScore approximation via sentence-transformer cosine similarity
    bertscore = 0.0
    model = _get_st_model() if _ST_OK else None
    if model and hypothesis_text.strip():
        try:
            import numpy as np
            e_ref = model.encode([reference[:512]], normalize_embeddings=True)
            e_hyp = model.encode([hypothesis_text[:512]], normalize_embeddings=True)
            bertscore = float(np.dot(e_ref[0], e_hyp[0]))
        except Exception:
            bertscore = 0.0

    return {
        "bleu":              round(bleu, 4),
        "rouge_l":           round(rouge_l, 4),
        "bertscore_approx":  round(max(0.0, bertscore), 4),
    }


def _interpretability(reasoning: Dict, gaps: list) -> Dict[str, float]:
    """Clarity of reasoning traces and gap articulation."""
    explanation = reasoning.get("explanation", "")
    summary = reasoning.get("summary", "")

    # Clarity: avg sentence length (shorter = clearer, up to a point)
    sentences = [s.strip() for s in re.split(r'[.!?]', explanation) if s.strip()]
    if sentences:
        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        clarity = 1.0 - min(1.0, max(0.0, (avg_len - 15) / 25))
    else:
        clarity = 0.0

    # Human eval proxy: summary completeness
    summary_score = min(1.0, len(summary.split()) / 40)

    # Gap articulation: gaps are specific (long sentences)
    specific_gaps = [g for g in gaps if len(g.split()) > 10]
    gap_clarity = min(1.0, len(specific_gaps) / max(len(gaps), 1))

    return {
        "reasoning_clarity":  round(clarity, 3),
        "summary_completeness": round(summary_score, 3),
        "gap_articulation":   round(gap_clarity, 3),
    }


def _research_utility_score(all_scores: Dict) -> float:
    """Composite RUS: weighted average across all dimensions."""
    weights = {
        "reasoning":       0.20,
        "formalization":   0.15,
        "hypothesis":      0.25,
        "generation":      0.15,
        "interpretability": 0.15,
        "roadmap":         0.10,
    }

    def avg(d): return sum(d.values()) / len(d) if d else 0.0

    weighted = (
        weights["reasoning"]       * avg(all_scores.get("reasoning_quality", {})) +
        weights["formalization"]   * avg(all_scores.get("formalization_accuracy", {})) +
        weights["hypothesis"]      * avg(all_scores.get("hypothesis_quality", {})) +
        weights["generation"]      * avg(all_scores.get("generation_quality", {})) +
        weights["interpretability"]* avg(all_scores.get("interpretability", {})) +
        weights["roadmap"]         * all_scores.get("roadmap_coverage", 0.0)
    )
    return round(weighted, 4)


def _roadmap_coverage(roadmap: list) -> float:
    """Score roadmap completeness."""
    if not roadmap:
        return 0.0
    weeks_with_tasks = sum(1 for w in roadmap if len(w.get("tasks", [])) >= 3)
    weeks_with_resources = sum(1 for w in roadmap if len(w.get("resources", [])) >= 2)
    coverage = (weeks_with_tasks + weeks_with_resources) / (2 * len(roadmap))
    return round(coverage, 3)


# ── Main entry point ──────────────────────────────────────────────────────────

def evaluate_and_print(pipeline_output: Dict[str, Any], pre_retry_snapshot: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Runs all evaluation metrics on the pipeline output and prints a
    formatted report to the terminal. Returns the metrics dict.
    """
    topic       = pipeline_output.get("topic", "")
    reasoning   = pipeline_output.get("reasoning", {})
    hypotheses  = pipeline_output.get("hypotheses", [])
    math_form   = pipeline_output.get("math_formulation", {})
    gaps        = pipeline_output.get("gaps", [])
    roadmap     = pipeline_output.get("roadmap", [])
    papers      = pipeline_output.get("papers", [])

    print("\n[Evaluator] Starting evaluation...")
    t0 = time.time()

    try:
        rq = _reasoning_quality(reasoning)
    except Exception as e:
        print(f"[Evaluator] reasoning_quality failed: {e}"); rq = {}
    try:
        fa = _formalization_accuracy(math_form)
    except Exception as e:
        print(f"[Evaluator] formalization_accuracy failed: {e}"); fa = {}
    try:
        hq = _hypothesis_quality(hypotheses, topic)
    except Exception as e:
        print(f"[Evaluator] hypothesis_quality failed: {e}"); hq = {}
    try:
        gq = _generation_quality(hypotheses, reasoning)
    except Exception as e:
        print(f"[Evaluator] generation_quality failed: {e}"); gq = {}
    try:
        interp = _interpretability(reasoning, gaps)
    except Exception as e:
        print(f"[Evaluator] interpretability failed: {e}"); interp = {}
    try:
        rc = _roadmap_coverage(roadmap)
    except Exception as e:
        print(f"[Evaluator] roadmap_coverage failed: {e}"); rc = 0.0

    all_scores = {
        "reasoning_quality":      rq,
        "formalization_accuracy": fa,
        "hypothesis_quality":     hq,
        "generation_quality":     gq,
        "interpretability":       interp,
        "roadmap_coverage":       rc,
    }

    rus = _research_utility_score(all_scores)
    elapsed = round(time.time() - t0, 2)

    # ── Ablation: per-module contribution to RUS ──────────────────────────────
    def avg(d): return round(sum(d.values()) / len(d), 3) if d else 0.0
    ablation = {
        "Reasoning Module":       avg(rq),
        "Formalization Module":   avg(fa),
        "Hypothesis Module":      avg(hq),
        "Generation Quality":     avg(gq),
        "Interpretability Module":avg(interp),
        "Roadmap Module":         rc,
    }

    # ── Terminal print ────────────────────────────────────────────────────────
    W = 62
    def bar(score, width=20):
        filled = int(score * width)
        return "█" * filled + "░" * (width - filled)

    def row(label, score):
        pct = f"{score*100:5.1f}%"
        return f"  {label:<30} {bar(score)} {pct}"

    print("\n" + "═" * W)
    print(f"  📊  EVALUATION METRICS  —  {topic[:35]}")
    print("═" * W)

    print("\n  ① REASONING QUALITY")
    for k, v in rq.items():
        print(row(k.replace("_", " ").title(), v))

    print("\n  ② FORMALIZATION ACCURACY")
    for k, v in fa.items():
        print(row(k.replace("_", " ").title(), v))

    print("\n  ③ HYPOTHESIS QUALITY")
    for k, v in hq.items():
        print(row(k.replace("_", " ").title(), v))

    print("\n  ④ GENERATION QUALITY  (BLEU / ROUGE-L / BERTScore)")
    for k, v in gq.items():
        print(row(k.replace("_", " ").title(), v))

    print("\n  ⑤ INTERPRETABILITY")
    for k, v in interp.items():
        print(row(k.replace("_", " ").title(), v))

    print("\n  ⑥ ROADMAP COVERAGE")
    print(row("Week Completeness", rc))

    print("\n" + "─" * W)
    print(f"\n  ⑦ ABLATION ANALYSIS  (per-module avg contribution)")
    for mod, score in ablation.items():
        print(row(mod, score))

    print("\n" + "─" * W)
    rus_bar = bar(rus, 30)
    print(f"\n  🏆  RESEARCH UTILITY SCORE (RUS)")
    print(f"      {rus_bar}  {rus*100:.1f} / 100")

    # ── Critic Scores ─────────────────────────────────────────────────────────
    post_scores = pipeline_output.get("critic_scores") or {}
    if post_scores:
        print(f"\n  🔁  CRITIC SCORES")
        print(f"  {'─'*30}")
        for sec in ["reasoning", "hypotheses", "math", "roadmap"]:
            if sec in post_scores:
                print(f"  {sec.capitalize():<18} {post_scores[sec]:>6}/10")
        print(f"  {'─'*30}")

    print(f"\n  Papers found: {len(papers)}   Hypotheses: {len(hypotheses)}   "
          f"Roadmap weeks: {len(roadmap)}   Eval time: {elapsed}s")
    print("\n" + "═" * W + "\n")

    return {**all_scores, "rus": rus, "ablation": ablation}


def compute_rus(pipeline_output: Dict[str, Any]) -> float:
    """Compute RUS for a pipeline output dict without printing anything."""
    topic      = pipeline_output.get("topic", "")
    reasoning  = pipeline_output.get("reasoning", {})
    hypotheses = pipeline_output.get("hypotheses", [])
    math_form  = pipeline_output.get("math_formulation", {})
    gaps       = pipeline_output.get("gaps", [])
    roadmap    = pipeline_output.get("roadmap", [])

    try: rq = _reasoning_quality(reasoning)
    except: rq = {}
    try: fa = _formalization_accuracy(math_form)
    except: fa = {}
    try: hq = _hypothesis_quality(hypotheses, topic)
    except: hq = {}
    try: gq = _generation_quality(hypotheses, reasoning)
    except: gq = {}
    try: interp = _interpretability(reasoning, gaps)
    except: interp = {}
    try: rc = _roadmap_coverage(roadmap)
    except: rc = 0.0

    return _research_utility_score({
        "reasoning_quality":      rq,
        "formalization_accuracy": fa,
        "hypothesis_quality":     hq,
        "generation_quality":     gq,
        "interpretability":       interp,
        "roadmap_coverage":       rc,
    })
