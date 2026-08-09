---
title: 'VERITAS: auditing the reasoning path of GraphRAG systems'
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
date: 15 July 2026
bibliography: paper.bib
---

# Summary

`VERITAS` is a benchmark that evaluates retrieval-augmented generation over knowledge
graphs (GraphRAG) by auditing the *reasoning path* a system takes, rather than the text
of its answer. Given a system's execution **trace** — the nodes and edges its retrieval
visited, and the claims its answer made — and a human-annotated **golden** reasoning
path, `VERITAS` computes four deterministic metrics: path fidelity, provenance coverage,
an honest-null rate, and an overconfidence penalty. The golden encodes the correct path
through the graph, not the path the system happens to take, so a low score localises
*where* retrieval diverges from correct reasoning. Scoring is deterministic — it
compares the trace against the graph, rather than asking a second language model whether
an answer was good, which would share the blind spots of the model under evaluation.

# Statement of need

GraphRAG is increasingly deployed in settings where a fluent but wrongly-reasoned
answer is worse than no answer: legal compliance, clinical information, safety-critical
engineering. Established RAG evaluations score the correctness of the answer text — for
example faithfulness and answer relevancy [@ragas]. These are necessary but not
sufficient in high-stakes domains: they cannot see whether the system reached its answer
by a defensible path, whether each claim is backed by evidence the system actually
traversed, or whether the system correctly declined to answer when the graph contained
no evidence. A system can produce a fluent, plausible-sounding answer from the wrong part
of the graph, and answer-level metrics will not detect it.

`VERITAS` addresses this gap by making the reasoning path itself the unit of evaluation.
It is aimed at researchers and engineers building GraphRAG systems who need to know not
just *whether* their system is right, but *why* — and who need that judgement to be
reproducible and independent of the model being judged.

# Design

**Artefacts.** A golden (`golden.schema.json`) lists the edges a correct answer must
traverse, each labelled `required` or `supporting`, with a required provenance grade;
or, for out-of-scope questions, it records that the correct behaviour is abstention. A
trace (`trace.schema.json`) records the nodes and edges a system visited and the claims
it made. Both share the edge identity `source|type|target`, so they align directly.

**Metrics.** *Path fidelity* is an F1 over graph edges: recall counts required golden
edges; precision is scoped to the edge *types* the golden annotates, so that a system
which correctly enters a node is not penalised for also traversing that node's other
edge types (the unscoped precision is reported alongside, and the gap quantifies
over-retrieval). *Provenance coverage* reports the share of answer claims whose evidence
resolves to a traversed edge. *Honest-null* is a per-question judgement of whether the
system abstained exactly when it should, aggregated into a rate over the out-of-scope
slice. *Overconfidence* penalises assertive claims backed only by weak-provenance edges.

**Determinism.** Because the golden is a fixed artefact and the metrics are computed by
set operations over edges, two runs of the scorer on the same inputs produce identical
output. Claim-to-requirement matching is the one pluggable component; the default is
lexical, and an LLM matcher can be injected without affecting the path-level metrics.

# Pilot results

We validated that the metrics discriminate on an 8-question pilot against a live
GraphRAG assistant over the full text of the EU AI Act (Regulation 2024/1689),
decomposed into a knowledge graph of articles, obligations, roles, risk categories,
exceptions and sanctions, compared against a vector-only baseline. On the answerable
questions, calibrated path-fidelity F1 was 0.86 and 0.59 on the two questions where the
system entered the graph through the legally-correct article, and 0.00 on three where it
entered through an unrelated article — including one Slovak-language question that named
its target article explicitly yet failed to retrieve it. The vector-only baseline
reconstructed no graph edges on any question. The low scores are not a verdict on the
system; each names a specific, reproducible failure — entry-point divergence,
cross-lingual retrieval miss, over-retrieval — that answer-text correctness does not
expose. The pilot is deliberately small; its purpose is to show the metrics separate
correct from incorrect reasoning before the dataset is scaled.

# Acknowledgements

The author thanks Ramesh Raskar for early mentorship in agentic systems.

# References
