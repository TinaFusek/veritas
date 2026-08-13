---
title: 'Beyond Answer Text: Auditing GraphRAG Reasoning Paths with Layered Adversarial Validation'
tags:
  - Python
  - GraphRAG
  - knowledge graphs
  - retrieval-augmented generation
  - evaluation
  - auditability
authors:
  - name: Martina Fusková
    affiliation: 1
affiliations:
  - name: Independent researcher, Bratislava, Slovakia
    index: 1
date: 13 August 2026
bibliography: paper.bib
---

# Summary

`VERITAS` evaluates retrieval-augmented generation over knowledge graphs (GraphRAG)
by auditing the *reasoning path* a system takes, rather than the text of its answer.
Given a system's execution **trace** — the nodes and edges its retrieval visited, and
the claims its answer made — and a human-annotated **golden** reasoning path, it
computes four deterministic metrics: path fidelity, provenance coverage, an honest-null
rate, and an overconfidence penalty. The golden encodes the correct path through the
graph, not the path the system happens to take, so a low score localises *where*
retrieval diverges from correct reasoning. Scoring is deterministic: it compares the
trace against the graph rather than asking a second language model whether an answer was
good, which would share the blind spots of the model under evaluation.

`VERITAS` extends this into a **layered audit**. Above the deterministic scorer sits an
optional adversarial critic — a language model prompted to attack an answer and propose
objections — whose output is treated as *hypotheses* that the deterministic layer then
verifies against the graph. Each layer catches a distinct class of error, and the paper
below reports experiments establishing that the layers cannot substitute for one another.

# Statement of need

GraphRAG is increasingly deployed where a fluent but wrongly-reasoned answer is worse
than no answer: legal compliance, clinical information, safety-critical engineering.
Established RAG evaluations score the correctness of the answer text — for example
faithfulness and answer relevancy [@ragas]. These are necessary but not sufficient in
high-stakes domains: they cannot see whether the system reached its answer by a
defensible path, whether each claim is backed by traversed evidence, or whether the
system correctly declined to answer when the graph contained no evidence. A system can
produce a fluent, plausible answer from the wrong part of the graph, and answer-level
metrics will not detect it.

`VERITAS` makes the reasoning path itself the unit of evaluation, for researchers and
engineers who need to know not just *whether* their system is right, but *why* — and who
need that judgement reproducible and independent of the model being judged.

# The layered design

**Layer 1 — the system generates a trace.** The GraphRAG system answers and emits a
trace: the nodes and edges its retrieval visited, and the claims it made.

**Layer 2 — an adversarial critic proposes objections.** A second model, prompted as
"the prosecution," attempts to break the answer: wrong entry article, missing core
obligation, unsupported claim, over-reach, or a case where the system should have
abstained. Its output is hypotheses, not verdicts; the critic is allowed to be aggressive
and occasionally wrong.

**Layer 3 — a deterministic scorer is the final arbiter.** The scorer verifies both the
trace and the critic's objections against the graph and the golden path, producing the
four metrics. Path fidelity precision is scoped to the edge types the golden annotates,
so a system that correctly enters a node is not penalised for also traversing that node's
other edge types; the unscoped figure is reported alongside, and the gap quantifies
over-retrieval.

# Experiments

Aurora, an assistant over the full text of the EU AI Act (Regulation 2024/1689), is the
validated pilot, with an annotated question set of 13 questions spanning obligations,
classification, transparency, authorities, sanctions, and both out-of-scope and
coverage-gap honest-null cases. MatGraph, over Materials Project semiconductor data, is a
second graph the framework is designed to transfer to; it shares the schema and scorer,
but its traces are not yet annotated, so the results below are reported on Aurora only.
The framework is graph-agnostic by construction; MatGraph transfer is ongoing work, not a
validated claim.

**Path-level scoring surfaces silent defects.** On the answerable Aurora questions,
calibrated path-fidelity F1 was high where the system entered through the legally-correct
article (e.g. 0.86 and 0.59 on two questions) and 0.00 where it entered through an
unrelated article — including a Slovak question that named its target article explicitly
yet failed to retrieve it. A vector-only baseline reconstructed no graph edges on any
question. Each low score names a specific, reproducible failure — entry-point divergence,
cross-lingual retrieval miss, over-retrieval — invisible to answer-text correctness.

**The critic is a capable but bounded detector.** Across 13 questions the critic's
objections agreed with the goldens 77% of the time initially; two targeted prompt
refinements raised this to 92%. A third refinement, attempting to make the critic detect
a *structural* coverage gap, regressed — establishing the boundary. On q007 (the Slovak
question) the critic flagged the cross-lingual drift without any knowledge of Slovak,
purely by detecting that the cited articles were topically unrelated to the question — a
language-agnostic drift signal. On the false-premise honest-null questions (a
non-existent article, an out-of-scope court ruling, an impossible requirement) it
correctly demanded abstention.

**The boundary case proves the architecture.** On q013 — a question whose answer exists
in the law but is not structured in the graph, present only as raw text — the critic,
despite 92% overall agreement, could not detect the gap, because it reads the answer and
citations, not the graph. Only Layer 3, which reads the graph, catches it. This single
case is the sharpest evidence that the deterministic layer is not replaceable by more
capable agents: the layers own distinct failure classes and cannot substitute for one
another. We measured this rather than assuming it.

# Reproducibility and deliverables

The repository includes the deterministic scorer and its four metrics, JSON schemas for
traces and goldens, an **annotation template** documenting how to build a golden path for
a new graph, **inter-annotator agreement tooling** (Cohen's kappa) for validating that a
golden is not one annotator's opinion, a test suite, and OpenTelemetry export. The design
is graph-agnostic; the annotation template and IAA tooling are the mechanism by which it
transfers to domains beyond the EU AI Act.

# Honest limitations

The pilots are small by design — one primary domain, one annotator — and the absolute
numbers need a larger dataset and a completed inter-annotator study (the tooling is
included) before they carry independent weight. The adversarial critic and the layered
audit above the scorer are validated at pilot scale. A planner layer that would choose
the reasoning path before traversal, and a critic referenced dynamically against
domain state-of-the-art rather than a fixed prompt, are designed but not yet validated;
they are stated as next steps rather than hidden — fitting, for a tool built to reward
honesty over fluency.

# Acknowledgements

The author thanks the engineering colleagues whose questions after a technical talk
sharpened the planner and critic-reference ideas noted as future work.

# References
