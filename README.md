# VERITAS

**A benchmark that audits the *reasoning path* of GraphRAG systems — not just the answer text.**

Most RAG evaluations ask *"is the answer correct?"* VERITAS asks a harder question:
*did the system reach that answer by a defensible path, and does it honestly say
"I don't know" when the graph has no evidence?* It scores a system's execution
**trace** against a human-annotated **golden** reasoning path, on four axes:

| Axis | Question it answers | Direction |
|------|--------------------|-----------|
| **Path fidelity** | Did it traverse the right edges of the graph? | higher = better |
| **Provenance coverage** | Are the answer's claims backed by traversed evidence? | higher = better |
| **Honest-null** | Does it abstain exactly when the graph can't answer? | higher = better |
| **Overconfidence** | Does it overstate weakly-supported claims? | lower = better |

The key design choice: the golden encodes the **correct path**, not the path the
system happens to take. So a low score is a *localisation* of where retrieval diverges
from correct reasoning — a finding, not a scoring artefact.

Scoring is **deterministic**: it compares the trace against the graph, rather than
asking another LLM "was this good?" — which would share the blind spots of the model
being judged.

---
<img width="1960" height="1116" alt="veritas-hero" src="https://github.com/user-attachments/assets/6ab63fdd-0f36-4f5b-8c63-82fdc5b37d9b" />
---

## Why this exists

In high-stakes settings — legal compliance, clinical information, safety-critical
engineering — a fluent but wrongly-reasoned answer is worse than no answer, because you
believe it. Answer-level metrics (faithfulness, answer relevancy) can't see *how* the
system got there. VERITAS makes the reasoning path itself the unit of evaluation.

## Install

```bash
pip install veritas-graphrag        # from PyPI (once published)
# or, from source:
git clone https://github.com/TinaFusek/veritas && cd veritas
pip install -e ".[dev]"
```

## Quick start

Score a directory of traces against a directory of goldens (matched by `question_id`):

```bash
veritas --traces runs/traces-traversal --golden pilot/golden --out scores.json
```

Or from Python:

```python
import json
from veritas.scorer import score_trace

golden = json.load(open("pilot/golden/aurora-q003.json"))
trace  = json.load(open("runs/traces-traversal/aurora-q003.json"))

score = score_trace(trace, golden)
print(score.path_fidelity["f1"], score.honest_null["category"])
```

## The two artefacts

A **golden** (`golden.schema.json`) specifies the edges a correct answer must traverse,
each tagged `required` or `supporting`, with a required provenance grade — or, for
out-of-scope questions, that the correct behaviour is abstention (`answerable: false`).

A **trace** (`trace.schema.json`) is what the system under test emits: the nodes and
edges its retrieval actually visited, and the claims its answer made.

Both use the same edge identity — `source|type|target` — so they line up directly.
See [`ANNOTATION_PROTOCOL.md`](ANNOTATION_PROTOCOL.md) for how goldens are annotated.

## What the metrics do (and don't) claim

- **Path fidelity** precision is *scoped to the edge types the golden annotates*. A
  system that correctly enters a node also traverses that node's other edge types;
  counting those against precision would punish correct retrieval for being thorough.
  The unscoped figure is reported alongside as `precision_unscoped` — the gap between
  them quantifies over-retrieval.
- **Provenance coverage** reports `grounded` (evidence resolves to a traversed edge),
  not just `linked` (evidence is gestured at). Claim matching is pluggable.
- **Honest-null** is a per-question boolean that becomes a *rate* only when aggregated
  over the out-of-scope slice.

## First results (Aurora / EU AI Act pilot)

Calibrated path fidelity on the answerable questions of an 8-question pilot, run
against a live GraphRAG assistant over the full EU AI Act, versus a vector-only
baseline. Small *n* by design — the pilot validates that the metrics discriminate
before scaling.

| Question | Path fidelity (F1) | Entered correctly? |
|----------|-------------------:|:------------------:|
| q003 — penalties for prohibited practices | **0.86** | yes (Art. 5) |
| q011 — deployer obligations | **0.59** | yes (Art. 26, the graph's hotspot) |
| q002 — provider documentation | 0.00 | no (entered Art. 82, not 11) |
| q005 — GPAI transparency | 0.00 | no (entered Art. 50, not 53) |
| q007 — exceptions under Art. 50 (Slovak) | 0.00 | no (cross-lingual miss) |

The vector-only baseline reconstructs **no** graph edges on any question (path fidelity
0.00 throughout) — by construction, it retrieves text chunks, not paths. The point of
the low numbers is not a verdict on the system; it's that each one *names* a specific,
reproducible failure — entry-point divergence, cross-lingual retrieval miss,
over-retrieval — none of which is visible to answer-text correctness.

See [`docs/RESULTS.md`](docs/RESULTS.md) for the full write-up.

## Tests

```bash
pytest -q          # 8 tests, including the precision-calibration invariant
```

## Status & roadmap

**v1.0** — deterministic scorer (4 metrics, calibrated), JSON schemas, annotation
protocol, OpenTelemetry export, Aurora + MatGraph pilot goldens.

https://doi.org/10.5281/zenodo.21862325

Planned:
- Larger annotated dataset (20+ questions) and a second domain's traces
- Inter-annotator agreement (Cohen's kappa) — tooling in `tools/iaa.py`
- *Future work:* a semantic-abstain layer to close the honest-null gap; a
  generate/critique two-agent layer above the deterministic checks; time-decaying
  confidence ("belief with a half-life")

## Citation

If you use VERITAS, please cite it — see [`CITATION.cff`](CITATION.cff).

## License

MIT — see [`LICENSE`](LICENSE).
