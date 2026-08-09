# VERITAS — first results (Aurora Compliance pilot)

*Draft fragment for the JOSS paper / arXiv methods note. Numbers are from a run against
the live Aurora `/ask` endpoint over 8 hand-annotated questions (4 answerable, 4
out-of-scope or cross-lingual), graph snapshot `aurora-2026-07-12-sha1:e717347b`,
against a vector-only baseline. This is a pilot: n is small by design, to validate that
the metrics discriminate before scaling.*

## Statement of need

Retrieval-augmented generation over knowledge graphs (GraphRAG) is increasingly used in
high-stakes settings — legal compliance, safety-critical engineering — where a fluent
but wrongly-reasoned answer is worse than no answer. Existing RAG evaluations score the
correctness of the answer *text* (faithfulness, answer relevancy). They do not score
whether the system reached the answer by a defensible path, whether each claim is backed
by traversed evidence, or whether the system correctly declined when the graph could not
answer. VERITAS addresses this with path-level metrics computed by comparing a system's
execution *trace* against a human-annotated *golden* reasoning path. Crucially, the
golden encodes the legally-correct path, not the path the system happens to take — so a
divergence is a localisation of where retrieval departs from correct reasoning, not a
scoring artefact.

## What the pilot measures reliably

Three signals were stable and interpretable across the run:

**1. Retrieval breadth (over-retrieval).** The traversal system cites a mean of **4.0
articles per question**, including on questions whose correct answer rests on a single
article. Broad context is not free: it dilutes the reasoning path and raises the chance
of citing a tangential article. This is a concrete, quantitative property of the system
that answer-text correctness does not expose.

**2. Entry-point divergence.** Per-question inspection of which article each answer is
built on shows that the system frequently enters the graph through an article other than
the legally-correct one:

| Question | Correct entry | System entered | |
|----------|--------------:|---------------:|--|
| q011 — deployer obligations | Art. 26 | Art. 26 | ✓ |
| q003 — penalties for prohibited practices | Art. 5 | Art. 5 (+ Art. 99) | ~ |
| q002 — provider documentation | Art. 11 | Art. 82 | ✗ |
| q005 — GPAI transparency | Art. 53 | Art. 50 | ✗ |

The system reaches Article 26 correctly for the deployer-obligations question — notably
the article its own trace-analytics flags as the most-visited "hotspot", so the busiest
node is also correctly served. But for provider-documentation and GPAI-transparency it
enters through unrelated articles. A direct fulltext query for these topics ranks the
correct article highest (e.g. Art. 11 scores 7.80, Art. 53 scores 7.95); the divergence
is introduced by the router's query reformulation, which reorders relevance. This is
invisible to any answer-only metric.

**3. The honest-null gap.** Of three deliberately out-of-scope questions, only one (a
question about a future CJEU ruling) was correctly refused. The others — a non-existent
Article 141, and a programming-language requirement — were answered from incidentally
keyword-matched articles (Art. 37 via "requirements"; various via "AI system"). A
fulltext relevance floor removes the weakest matches but is defeated by the same router
reformulation that raises tangential articles above the floor. This localises a concrete
architectural need: lexical thresholding is insufficient for abstention; a semantic
"is this context actually on-topic?" check is required. We propose this as the primary
next iteration.

**4. Cross-lingual retrieval failure.** The Slovak question naming Article 50 explicitly
("výnimky ... podľa článku 50") does not reach Article 50 even through the system's
translate-for-retrieval step — it enters at Articles 25, 26, 69, 86. The same content in
English ranks Article 50 highest (fulltext 5.51). The failure is in the cross-lingual
retrieval path, not the index — directly relevant to under-served non-English compliance
settings.

## Baseline contrast

The vector-only baseline reconstructs **no** graph edges on any question (path fidelity
0.00), by construction: it retrieves text chunks, not paths. The traversal system does
reconstruct edges, so path-level auditing separates the two approaches even where
answer-text quality would not.

## Limitation and next step (calibration)

The **absolute** path-fidelity F1 in this run is low and should not yet be read as a
verdict on the system. Two things depress it mechanically: (a) edge reconstruction from a
cited article currently pulls *all* of that article's edge types, while the golden
annotates a representative subset — so even a correct entry (q011 → Art. 26) is penalised
on precision; and (b) the entry-point divergences above genuinely lower recall. Isolating
(a) — restricting reconstruction to the edge types the golden covers — is the immediate
next calibration step, expected to raise per-question fidelity on correctly-entered
questions substantially (a controlled simulation on q011 gives F1 ≈ 0.71 once (a) is
removed). Until that calibration lands, path fidelity is reported as a relative,
baseline-anchored signal, not an absolute score.

## Interpretation

A naive benchmark would tune thresholds until every score read 1.0, hiding the
behaviour. VERITAS instead surfaces specific, nameable defects — over-retrieval,
entry-point divergence, cross-lingual drift, keyword-bleed abstention failure — each
actionable and none visible to answer-text correctness. The honest-null signal in
particular doubles as a map of where the knowledge graph and its retrieval are
incomplete. Reporting these honestly, including the calibration limit on absolute path
fidelity, is itself the point: the tool is built to show where a system is weak, not to
flatter it.
