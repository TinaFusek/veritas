"""
VERITAS scorer — v1.0.0 (calibrated)

Scores a GraphRAG system Trace against a Golden annotation on four axes:

  1. path_fidelity        — did the system follow the right edges?      (F1 over edges)
  2. provenance_coverage  — are the answer's claims backed by evidence? (share grounded)
  3. honest_null          — does it abstain exactly when it should?     (correct / total)
  4. overconfidence       — does it overstate weakly-supported claims?  (penalty, lower=better)

Design notes
------------
* Edge identity is the string  "source|type|target".  Both trace and golden use it.
* honest_null is only meaningful per-question as a boolean; it becomes a *rate* only
  when aggregated over the honest-null slice of the dataset. The batch aggregator does that.
* Claim <-> required_claim matching is intentionally pluggable (see `match_claims`).
  The default is a naive lexical matcher; the paper's harness swaps in an LLM matcher.
  Keeping it injectable is what makes the fairness argument defensible.

No third-party dependencies for scoring itself (jsonschema only used for validation).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Callable, Iterable
import json
import statistics

# Provenance grades ordered from strongest to weakest evidence.
_GRADE_RANK = {"measured": 3, "derived": 2, "weak": 1}
# Confidence phrasings ordered from strongest assertion to most cautious.
_CONF_RANK = {"asserted": 4, "qualified": 3, "hedged": 2, "attributed": 1}


def edge_key(source: str, type_: str, target: str) -> str:
    return f"{source}|{type_}|{target}"


# ---------------------------------------------------------------------------
# 1. Path fidelity
# ---------------------------------------------------------------------------
def score_path_fidelity(trace: dict, golden: dict) -> dict:
    """Edge-level precision / recall / F1.

    Recall counts only 'required' golden edges (supporting edges are credited if
    hit but never punish a miss). Precision is over the edges the system used —
    but scoped to the edge *types* the golden annotates (see calibration note).

    Calibration (v1.0)
    ------------------
    A golden annotates a representative subset of a question's relevant edges,
    by edge type (e.g. PENALIZED_BY for a penalties question; IMPOSES/APPLIES_TO
    for an obligations question). A system that correctly enters the right article
    also traverses that article's *other* edge types, which the golden does not
    annotate. Counting those against precision punishes correct retrieval for
    being thorough. So precision is computed only over used edges whose *type*
    appears in the golden. Edge types the golden never mentions are treated as
    out-of-scope for this question, not as false positives.

    This is reported as `precision` (scoped). The unscoped figure is kept as
    `precision_unscoped` for transparency — the gap between them quantifies
    over-retrieval breadth.
    """
    used_all = {
        edge_key(e["source"], e["type"], e["target"])
        for e in trace.get("traversal", {}).get("used_edges", [])
    }
    golden_edges = golden.get("golden_edges", [])
    required = {
        edge_key(e["source"], e["type"], e["target"])
        for e in golden_edges
        if e.get("role", "required") == "required"
    }
    supporting = {
        edge_key(e["source"], e["type"], e["target"])
        for e in golden_edges
        if e.get("role", "required") == "supporting"
    }
    all_golden = required | supporting

    # Edge types the golden annotates — the scope for precision.
    golden_types = {e["type"] for e in golden_edges}

    def _type_of(k: str) -> str:
        return k.split("|", 2)[1] if "|" in k else ""

    # Used edges whose type is in scope for this question.
    used_scoped = {k for k in used_all if _type_of(k) in golden_types}

    # Recall: of the required edges, how many were followed.
    hit_required = len(required & used_all)
    recall = hit_required / len(required) if required else 1.0

    # Precision (scoped): of the in-scope edges followed, how many were golden.
    hit_any = len(all_golden & used_scoped)
    precision = hit_any / len(used_scoped) if used_scoped else (1.0 if not required else 0.0)

    # Precision (unscoped): the raw figure, for transparency / over-retrieval signal.
    hit_any_all = len(all_golden & used_all)
    precision_unscoped = hit_any_all / len(used_all) if used_all else (1.0 if not required else 0.0)

    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "precision": round(precision, 4),
        "precision_unscoped": round(precision_unscoped, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "required_hit": hit_required,
        "required_total": len(required),
        "retrieval_breadth": len(used_all),
        "spurious_edges": sorted(used_scoped - all_golden),
    }


# ---------------------------------------------------------------------------
# 2. Provenance coverage
# ---------------------------------------------------------------------------
def score_provenance_coverage(trace: dict) -> dict:
    """Share of answer claims whose evidence refs actually exist in the traversal.

    Two levels:
      * linked   — claim has >=1 evidence entry (self-reported).
      * grounded — that evidence ref resolves to an edge/node the system really used.
    'grounded' is the honest number; 'linked' catches systems that gesture at
    evidence without traversing it.
    """
    used_edges = {
        edge_key(e["source"], e["type"], e["target"])
        for e in trace.get("traversal", {}).get("used_edges", [])
    }
    used_nodes = {
        n["node_id"] for n in trace.get("traversal", {}).get("visited_nodes", [])
    }
    claims = trace.get("answer", {}).get("claims", [])
    if not claims:
        return {"linked": 1.0, "grounded": 1.0, "n_claims": 0, "ungrounded_claims": []}

    linked = 0
    grounded = 0
    ungrounded = []
    for c in claims:
        ev = c.get("evidence", [])
        if ev:
            linked += 1
        ok = False
        for e in ev:
            ref = e.get("ref", "")
            if e.get("kind") == "edge" and ref in used_edges:
                ok = True
            elif e.get("kind") == "node" and ref in used_nodes:
                ok = True
        if ok:
            grounded += 1
        else:
            ungrounded.append(c.get("claim_id", c.get("text", "?")))

    n = len(claims)
    return {
        "linked": round(linked / n, 4),
        "grounded": round(grounded / n, 4),
        "n_claims": n,
        "ungrounded_claims": ungrounded,
    }


# ---------------------------------------------------------------------------
# 3. Honest-null (per question -> boolean correctness)
# ---------------------------------------------------------------------------
def score_honest_null(trace: dict, golden: dict) -> dict:
    """Did the system's abstain/answer decision match answerability?

    Returns a category so the aggregator can build a confusion matrix:
      * true_abstain  — unanswerable & abstained          (good)
      * false_answer  — unanswerable & answered anyway     (hallucination risk)
      * true_answer   — answerable  & answered             (good)
      * false_abstain — answerable  & abstained            (over-cautious)
    """
    answerable = golden.get("answerable", True)
    abstained = trace.get("answer", {}).get("abstained", False) \
        or trace.get("traversal", {}).get("retrieval_empty", False)

    if not answerable and abstained:
        cat = "true_abstain"
    elif not answerable and not abstained:
        cat = "false_answer"
    elif answerable and not abstained:
        cat = "true_answer"
    else:
        cat = "false_abstain"

    return {"category": cat, "correct": cat in ("true_abstain", "true_answer")}


# ---------------------------------------------------------------------------
# 4. Overconfidence penalty
# ---------------------------------------------------------------------------
def score_overconfidence(trace: dict) -> dict:
    """Penalize claims stated more strongly than their weakest supporting edge allows.

    Rule: map each claim's supporting edge grade -> the strongest confidence phrasing
    it licenses. If the claim was stated more strongly, it's a violation.

        measured -> asserted allowed
        derived  -> qualified is the ceiling (asserting a derived rule as fact = violation)
        weak     -> hedged/attributed only

    Claims with no evidence are skipped here (they're already caught by coverage),
    so this metric isolates the *miscalibration* failure specifically.
    """
    used = {
        edge_key(e["source"], e["type"], e["target"]): e.get("provenance", {}).get("grade", "weak")
        for e in trace.get("traversal", {}).get("used_edges", [])
    }
    # ceiling: strongest phrasing allowed per grade
    ceiling = {"measured": "asserted", "derived": "qualified", "weak": "hedged"}

    claims = trace.get("answer", {}).get("claims", [])
    violations = []
    considered = 0
    for c in claims:
        ev_grades = []
        for e in c.get("evidence", []):
            if e.get("kind") == "edge" and e.get("ref") in used:
                ev_grades.append(used[e["ref"]])
        if not ev_grades:
            continue  # unsupported -> not this metric's job
        considered += 1
        weakest = min(ev_grades, key=lambda g: _GRADE_RANK.get(g, 1))
        allowed = ceiling.get(weakest, "hedged")
        stated = c.get("confidence_stated", "asserted")
        if _CONF_RANK.get(stated, 4) > _CONF_RANK.get(allowed, 1):
            violations.append({
                "claim_id": c.get("claim_id", "?"),
                "weakest_grade": weakest,
                "allowed": allowed,
                "stated": stated,
            })

    penalty = len(violations) / considered if considered else 0.0
    return {
        "penalty": round(penalty, 4),  # 0 = perfectly calibrated, 1 = every supported claim overstated
        "violations": violations,
        "claims_considered": considered,
    }


# ---------------------------------------------------------------------------
# Claim matching (pluggable) — used only if you score against required_claims
# ---------------------------------------------------------------------------
def naive_lexical_matcher(system_claim: dict, required_text: str) -> bool:
    """Cheap default: token overlap over a threshold. Replace with an LLM matcher
    for the real harness; keep this for offline/CI runs."""
    a = set(system_claim.get("text", "").lower().split())
    b = set(required_text.lower().split())
    if not b:
        return False
    return len(a & b) / len(b) >= 0.5


def coverage_of_required(trace: dict, golden: dict,
                         matcher: Callable[[dict, str], bool] = naive_lexical_matcher) -> dict:
    """Of the facts the answer was required to contain, how many appear?"""
    required = golden.get("required_claims", [])
    if not required:
        return {"recall": None, "missing": []}
    sys_claims = trace.get("answer", {}).get("claims", [])
    missing = []
    hit = 0
    for r in required:
        if any(matcher(sc, r["text"]) for sc in sys_claims):
            hit += 1
        else:
            missing.append(r["text"])
    return {"recall": round(hit / len(required), 4), "missing": missing}


# ---------------------------------------------------------------------------
# Single-trace orchestration
# ---------------------------------------------------------------------------
@dataclass
class TraceScore:
    question_id: str
    system: str
    answerable: bool
    path_fidelity: dict
    provenance_coverage: dict
    honest_null: dict
    overconfidence: dict
    required_coverage: dict

    def to_dict(self) -> dict:
        return asdict(self)


def score_trace(trace: dict, golden: dict,
                matcher: Callable[[dict, str], bool] = naive_lexical_matcher) -> TraceScore:
    if trace.get("question", {}).get("id") != golden.get("question_id"):
        raise ValueError(
            f"question id mismatch: trace={trace.get('question', {}).get('id')} "
            f"golden={golden.get('question_id')}"
        )
    return TraceScore(
        question_id=golden["question_id"],
        system=trace.get("system", {}).get("name", "?"),
        answerable=golden.get("answerable", True),
        path_fidelity=score_path_fidelity(trace, golden),
        provenance_coverage=score_provenance_coverage(trace),
        honest_null=score_honest_null(trace, golden),
        overconfidence=score_overconfidence(trace),
        required_coverage=coverage_of_required(trace, golden, matcher),
    )


# ---------------------------------------------------------------------------
# Batch aggregation — the numbers that go in the paper
# ---------------------------------------------------------------------------
def aggregate(scores: Iterable[TraceScore]) -> dict:
    scores = list(scores)
    if not scores:
        return {}

    answerable = [s for s in scores if s.answerable]
    unanswerable = [s for s in scores if not s.answerable]

    def mean(xs):
        xs = [x for x in xs if x is not None]
        return round(statistics.mean(xs), 4) if xs else None

    # path fidelity / coverage are only meaningful on answerable questions
    pf = mean([s.path_fidelity["f1"] for s in answerable])
    cov = mean([s.provenance_coverage["grounded"] for s in answerable])
    overc = mean([s.overconfidence["penalty"] for s in answerable])
    reqcov = mean([s.required_coverage["recall"] for s in answerable
                   if s.required_coverage["recall"] is not None])

    # honest-null confusion matrix over the whole set
    cats = [s.honest_null["category"] for s in scores]
    conf = {c: cats.count(c) for c in
            ("true_abstain", "false_answer", "true_answer", "false_abstain")}
    honest_null_rate = (conf["true_abstain"] / len(unanswerable)) if unanswerable else None
    over_abstention = (conf["false_abstain"] / len(answerable)) if answerable else None

    return {
        "n_total": len(scores),
        "n_answerable": len(answerable),
        "n_unanswerable": len(unanswerable),
        "path_fidelity_f1": pf,
        "provenance_coverage_grounded": cov,
        "overconfidence_penalty": overc,
        "required_claim_recall": reqcov,
        "honest_null_rate": honest_null_rate,
        "over_abstention_rate": over_abstention,
        "honest_null_confusion": conf,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def main(argv=None):
    import argparse
    import glob
    import os

    p = argparse.ArgumentParser(description="VERITAS scorer v1.0.0")
    p.add_argument("--traces", required=True,
                   help="A trace .json file, or a directory of them.")
    p.add_argument("--golden", required=True,
                   help="A golden .json file, or a directory of them (matched by question_id).")
    p.add_argument("--out", default=None, help="Write per-trace scores here (JSON).")
    args = p.parse_args(argv)

    # collect goldens by question_id
    golden_files = ([args.golden] if os.path.isfile(args.golden)
                    else glob.glob(os.path.join(args.golden, "*.json")))
    goldens = {}
    for gf in golden_files:
        g = _load(gf)
        goldens[g["question_id"]] = g

    trace_files = ([args.traces] if os.path.isfile(args.traces)
                   else glob.glob(os.path.join(args.traces, "*.json")))

    per_trace = []
    for tf in trace_files:
        t = _load(tf)
        qid = t.get("question", {}).get("id")
        if qid not in goldens:
            print(f"[skip] no golden for {qid} ({tf})")
            continue
        s = score_trace(t, goldens[qid])
        per_trace.append(s)

    summary = aggregate(per_trace)

    print("\n=== VERITAS summary ===")
    for k, v in summary.items():
        print(f"{k:34s} {v}")

    if args.out:
        with open(args.out, "w") as f:
            json.dump(
                {"summary": summary, "per_trace": [s.to_dict() for s in per_trace]},
                f, indent=2,
            )
        print(f"\nWrote {args.out}")

    return summary


def _cli():
    """Console-script entry point (see pyproject [project.scripts])."""
    main()


if __name__ == "__main__":
    main()
