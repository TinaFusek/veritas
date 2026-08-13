# VERITAS: trace-level auditing with adversarial validation

*One system, layered. Each layer catches a different kind of error — and we have
empirical evidence for why every layer is needed.*

---

## The problem

Retrieval-augmented generation over knowledge graphs (GraphRAG) is moving into
high-stakes settings — legal compliance, clinical information, safety-critical
engineering — where a fluent but wrongly-reasoned answer is worse than no answer,
because you believe it. Existing evaluations score the *answer text*: is it faithful,
is it relevant? They cannot see whether the system reached the answer by a defensible
path, whether each claim is backed by traversed evidence, or whether the system should
have declined to answer at all.

VERITAS makes the **reasoning path itself** the unit of evaluation.

## The contribution

The contribution is not a single metric. It is a **layered audit**, where each layer
catches a class of error the others cannot — and the layering is empirically justified,
not assumed.

**Layer 1 — the system generates a trace.** The GraphRAG system (in our pilot, Aurora,
an assistant over the full EU AI Act) answers a question and emits a *trace*: the nodes
and edges its retrieval actually visited, and the claims its answer made. This is what
really happened, not what should have happened.

**Layer 2 — an adversarial critic proposes objections.** A second agent, prompted as
"the prosecution," tries to *break* the answer: wrong entry article, missing core
obligation, unsupported claim, over-reach, or a case where the system should have
abstained. Crucially, its output is a set of *hypotheses*, not verdicts — the critic is
allowed to be aggressive and occasionally wrong.

**Layer 3 — a deterministic scorer is the final arbiter.** The scorer verifies both the
trace *and* the critic's objections against the graph and a human-annotated golden path,
producing four metrics: path fidelity, provenance coverage, honest-null, and
overconfidence. It asks no LLM whether an answer was "good" — it compares against the
graph, which has no shared blind spot with the model under test.

## Why three layers — proven, not asserted

Two pilots produced the evidence.

The **scoring pilot** (8 questions, EU AI Act) showed the deterministic layer surfaces
concrete, reproducible defects invisible to answer-text metrics: entry-point divergence
(a question about provider documentation answered from the wrong article), a
cross-lingual retrieval miss (a Slovak question naming an article explicitly, yet not
retrieving it), and systematic over-retrieval.

The **two-agent experiment** (13 questions, three tuning rounds) showed exactly where
the critic helps and where it cannot. Round 1 reached 77% agreement with the goldens;
targeted prompt fixes lifted it to 92%. But a third round, attempting to make the critic
detect a *structural* gap — where an answer exists in law but is not structured in the
graph — failed, and even regressed. That failure is the finding: **the critic catches
factual errors, but only the deterministic layer, which can see the graph, catches
structural gaps.** The layers cannot substitute for each other. We measured this; we did
not assume it.

## What this is for

VERITAS is an **audit tool** for teams who need to trust a GraphRAG system in a
regulated domain — not a leaderboard metric for ML researchers. The deliverable is the
method and the annotation template ("how to build a golden path for your own graph"),
not a single score. Because the scorer is graph-agnostic and the critic can be pointed
at the state-of-the-art for any domain rather than a hardcoded checklist, the approach
is designed to transfer beyond the EU AI Act to any knowledge graph.

## Honest limitations

The pilots are small by design — 21 questions total, one domain, one annotator. Absolute
numbers need a larger dataset and a second annotator (inter-annotator agreement tooling
is included) before they carry independent weight. The planner layer (choosing the
reasoning path before traversal) and the SOTA-referenced critic are designed but not yet
validated. These are stated as next steps, not hidden — which is, after all, the whole
point of a tool built to reward honesty over fluency.
