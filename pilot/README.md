# VERITAS pilot set

20 questions across two graphs, built to stress-test all four axes before scaling
to the full benchmark.

## Composition

| Domain | Questions | Honest-null | Languages |
|---|---|---|---|
| Aurora (EU AI Act) | 10 | 3 | 7 EN, 3 SK |
| MatGraph (materials) | 10 | 3 | 10 EN |
| **Total** | **20** | **6 (30%)** | 17 EN, 3 SK |

Honest-null is oversampled to 30% here on purpose — the pilot exists to check the
abstention axis behaves. The full set dials back to ~20%.

Two goldens are already fully annotated as worked references:
`matgraph-q014` (answerable) and `matgraph-q027` (honest-null).

## Files

- `questions.json` — the manifest. Every `answerable_hypothesis` is a **guess** to
  confirm against the real graph during annotation.
- `golden/*.json` — 20 stubs. 18 are empty and ready to fill; 2 are worked examples.
- `build_pilot.py` — regenerates the stubs (won't clobber the 2 annotated ones).

## How to annotate (short version — full rules in ANNOTATION_PROTOCOL.md)

For each stub in `golden/`:

1. Replace `graph_snapshot` with the **real** snapshot id you're looking at.
2. **Confirm `answerable`** against the graph — the hint in `notes` is only a hypothesis.
3. Fill `golden_edges` (required vs supporting, with `required_provenance`).
4. Fill `required_claims` (`must_be_grounded`, `max_confidence`) and `forbidden_claims`.
5. Set `annotation.annotator`, `annotated_at`, and `difficulty` (`clear`/`borderline`);
   remove the `_difficulty_hint` line.
6. Validate: it must pass `golden.schema.json`.

The SK questions (`aurora-q006`, `aurora-q007`, `matgraph-q020`) should share golden
edges with their EN equivalents where the question is a true translation — that's how
you test cross-lingual retrieval parity.

## Then

1. Run each system-under-test over the 20 questions, emitting one trace per question
   (per `trace.schema.json`) into a `traces/` dir.
2. Score:
   ```bash
   python -m veritas.scorer --traces pilot/traces --golden pilot/golden --out pilot/scores.json
   ```
3. First comparative number to look for: **path_fidelity_f1 for vector-only RAG vs
   traversal.** If vector collapses (it should — it retrieves nodes, not paths) you
   have your headline chart.
