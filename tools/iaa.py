"""
Inter-annotator agreement (IAA) for VERITAS goldens.

Why this matters
----------------
A golden is a human judgement about which edges the correct reasoning path must
traverse. A benchmark built on one annotator's judgement is vulnerable to the
charge that the "correct path" is just that person's opinion. IAA answers it with
a number: have two annotators, independently, marked the same edges required /
supporting / excluded — and how much of their agreement is beyond chance?

We report **Cohen's kappa** over the edge-labelling decision.

The decision being measured
---------------------------
For each question we take the *union* of edges either annotator touched (from the
candidate edge set of that question's entered node(s)), and for each edge each
annotator assigned one of three labels:

    required  |  supporting  |  excluded (not in their golden)

Cohen's kappa is computed over this 3-way labelling, per question and pooled.

Usage
-----
    python -m tools.iaa --a annotatorA/ --b annotatorB/ [--candidates candidates.json]

  --a, --b     directories of golden JSON files from two annotators (matched by
               question_id). Only questions present in BOTH are scored.
  --candidates optional JSON mapping question_id -> [edge_key, ...], the full
               candidate edge set per question. If omitted, the candidate set is
               taken as the union of edges either annotator labelled (a slightly
               optimistic kappa, since jointly-excluded edges aren't counted).

Kappa interpretation (Landis & Koch, rough): <0 poor, 0-.2 slight, .2-.4 fair,
.4-.6 moderate, .6-.8 substantial, .8-1 almost perfect.

No third-party dependencies.
"""
from __future__ import annotations
import argparse, glob, json, os
from collections import defaultdict


def edge_key(e: dict) -> str:
    return f"{e['source']}|{e['type']}|{e['target']}"


def labels_for(golden: dict) -> dict:
    """edge_key -> 'required' | 'supporting' for one annotator's golden."""
    out = {}
    for e in golden.get("golden_edges", []):
        out[edge_key(e)] = e.get("role", "required")
    return out


def cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    """Cohen's kappa for two equal-length label sequences over a shared item set."""
    assert len(labels_a) == len(labels_b)
    n = len(labels_a)
    if n == 0:
        return float("nan")
    cats = sorted(set(labels_a) | set(labels_b))
    # observed agreement
    po = sum(1 for x, y in zip(labels_a, labels_b) if x == y) / n
    # expected agreement by chance
    pa = {c: labels_a.count(c) / n for c in cats}
    pb = {c: labels_b.count(c) / n for c in cats}
    pe = sum(pa[c] * pb[c] for c in cats)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def score_pair(golden_a: dict, golden_b: dict, candidates: list[str] | None):
    la, lb = labels_for(golden_a), labels_for(golden_b)
    if candidates is None:
        universe = sorted(set(la) | set(lb))
    else:
        universe = sorted(set(candidates) | set(la) | set(lb))
    seq_a = [la.get(k, "excluded") for k in universe]
    seq_b = [lb.get(k, "excluded") for k in universe]
    return cohen_kappa(seq_a, seq_b), len(universe)


def main(argv=None):
    p = argparse.ArgumentParser(description="VERITAS inter-annotator agreement (Cohen's kappa)")
    p.add_argument("--a", required=True, help="dir of annotator A goldens")
    p.add_argument("--b", required=True, help="dir of annotator B goldens")
    p.add_argument("--candidates", default=None,
                   help="optional JSON: question_id -> [edge_key,...] candidate set")
    args = p.parse_args(argv)

    def load_dir(d):
        out = {}
        for f in glob.glob(os.path.join(d, "*.json")):
            g = json.load(open(f))
            out[g["question_id"]] = g
        return out

    A, B = load_dir(args.a), load_dir(args.b)
    cand = json.load(open(args.candidates)) if args.candidates else {}
    shared = sorted(set(A) & set(B))
    if not shared:
        print("No questions present in both annotator sets.")
        return

    # per-question kappa + a pooled sequence
    pooled_a, pooled_b = [], []
    print(f"{'question':16s} {'kappa':>7s} {'items':>6s}")
    print("-" * 32)
    for qid in shared:
        la, lb = labels_for(A[qid]), labels_for(B[qid])
        universe = sorted(set(cand.get(qid, [])) | set(la) | set(lb))
        seq_a = [la.get(k, "excluded") for k in universe]
        seq_b = [lb.get(k, "excluded") for k in universe]
        k = cohen_kappa(seq_a, seq_b)
        pooled_a += seq_a
        pooled_b += seq_b
        print(f"{qid:16s} {k:7.3f} {len(universe):6d}")
    print("-" * 32)
    print(f"{'POOLED':16s} {cohen_kappa(pooled_a, pooled_b):7.3f} {len(pooled_a):6d}")


if __name__ == "__main__":
    main()
