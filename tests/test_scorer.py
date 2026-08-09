"""Minimal but meaningful tests for the VERITAS scorer."""
import json
import os
import pytest

from veritas.scorer import (
    score_path_fidelity, score_provenance_coverage,
    score_honest_null, score_overconfidence, score_trace, aggregate,
    edge_key,
)

HERE = os.path.dirname(__file__)
EX = os.path.join(HERE, "..", "examples")


def _load(rel):
    with open(os.path.join(EX, rel)) as f:
        return json.load(f)


@pytest.fixture
def answerable_pair():
    return _load("traces/matgraph-q014.json"), _load("golden/matgraph-q014.json")


@pytest.fixture
def null_pair():
    return _load("traces/matgraph-q027.json"), _load("golden/matgraph-q027.json")


def test_path_fidelity_hits_all_required(answerable_pair):
    trace, golden = answerable_pair
    pf = score_path_fidelity(trace, golden)
    assert pf["required_hit"] == pf["required_total"] == 2
    assert pf["recall"] == 1.0


def test_ungrounded_claim_is_caught(answerable_pair):
    trace, golden = answerable_pair
    cov = score_provenance_coverage(trace)
    # c4 (experimental ~6 eV) is true but not in graph -> must be flagged
    assert "c4" in cov["ungrounded_claims"]
    assert cov["grounded"] == 0.75


def test_honest_null_true_abstain(null_pair):
    trace, golden = null_pair
    hn = score_honest_null(trace, golden)
    assert hn["category"] == "true_abstain"
    assert hn["correct"] is True


def test_false_answer_is_penalized():
    # unanswerable question, but the system answered anyway
    trace = {
        "question": {"id": "q"},
        "system": {"name": "x"},
        "traversal": {"used_edges": [], "visited_nodes": []},
        "answer": {"text": "The singularities are at 3.4 and 4.3 eV.", "abstained": False, "claims": []},
    }
    golden = {"question_id": "q", "answerable": False, "golden_edges": []}
    hn = score_honest_null(trace, golden)
    assert hn["category"] == "false_answer"
    assert hn["correct"] is False


def test_overconfidence_flags_asserted_derived_edge():
    trace = {
        "question": {"id": "q"},
        "system": {"name": "x"},
        "traversal": {
            "visited_nodes": [],
            "used_edges": [
                {"source": "a", "type": "R", "target": "b",
                 "provenance": {"grade": "derived"}}
            ],
        },
        "answer": {
            "text": "...",
            "abstained": False,
            "claims": [
                {"claim_id": "c1", "text": "x",
                 "evidence": [{"kind": "edge", "ref": edge_key("a", "R", "b")}],
                 "confidence_stated": "asserted"}  # derived edge stated as fact -> violation
            ],
        },
    }
    oc = score_overconfidence(trace)
    assert oc["penalty"] == 1.0
    assert oc["violations"][0]["claim_id"] == "c1"


def test_aggregate_confusion_matrix(answerable_pair, null_pair):
    scores = [score_trace(*answerable_pair), score_trace(*null_pair)]
    agg = aggregate(scores)
    assert agg["honest_null_rate"] == 1.0
    assert agg["honest_null_confusion"]["true_abstain"] == 1
    assert agg["honest_null_confusion"]["true_answer"] == 1
    assert agg["n_total"] == 2


def test_question_id_mismatch_raises(answerable_pair, null_pair):
    trace, _ = answerable_pair
    _, golden = null_pair
    with pytest.raises(ValueError):
        score_trace(trace, golden)


# --- calibration: edge-type-scoped precision (v1.0) ---
def test_precision_scoped_to_golden_edge_types():
    """A correct entry that also traverses other edge types of the same node
    should not be punished on precision for types the golden doesn't annotate."""
    from veritas.scorer import score_path_fidelity
    golden = {
        "golden_edges": [
            {"source": "art:5", "type": "PENALIZED_BY", "target": "sanc:x", "role": "required"},
        ]
    }
    trace = {
        "traversal": {
            "used_edges": [
                {"source": "art:5", "type": "PENALIZED_BY", "target": "sanc:x"},   # golden hit
                {"source": "art:5", "type": "IMPOSES", "target": "obl:y"},          # off-type noise
                {"source": "art:5", "type": "IMPOSES", "target": "obl:z"},          # off-type noise
            ]
        }
    }
    s = score_path_fidelity(trace, golden)
    assert s["recall"] == 1.0
    assert s["precision"] == 1.0            # scoped: only PENALIZED_BY counts
    assert s["precision_unscoped"] < 0.5    # raw: diluted by IMPOSES noise
    assert s["retrieval_breadth"] == 3


# --- inter-annotator agreement tool ---
def test_cohen_kappa_bounds():
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from tools.iaa import cohen_kappa
    assert cohen_kappa(["required", "supporting"], ["required", "supporting"]) == 1.0
    # systematic swap across a shared 2-category set gives kappa = -1
    assert cohen_kappa(["required", "supporting"], ["supporting", "required"]) == -1.0
    # partial agreement lands strictly between
    k = cohen_kappa(["required", "required", "excluded"], ["required", "supporting", "excluded"])
    assert 0.0 < k < 1.0
