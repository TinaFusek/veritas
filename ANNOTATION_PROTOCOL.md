# VERITAS Annotation Protocol v1.0

*The point of this document: two annotators, given the same question and graph,
should produce golden files that agree. Write the rule down once; apply it every time.
When a question can't be annotated consistently, it is thrown out — consistency beats size.*

---

## 0. What you are annotating

For each benchmark question you produce **one golden file** (`golden.schema.json`)
describing what a *correct, honest* answer would have to do against a **fixed graph
snapshot**. You are not writing the answer. You are defining the standard the answer
is judged against, on four axes:

1. which edges a correct traversal must follow (**path fidelity**),
2. which facts must be present and how strongly they may be stated (**provenance coverage**, **overconfidence**),
3. whether the graph can answer at all (**honest-null**),
4. what must *not* be claimed (**forbidden claims**).

Everything is tied to a `graph_snapshot`. A golden file is only valid against traces
run on that same snapshot. If the graph changes, re-validate — belief has a half-life.

---

## 1. The one rule that prevents drift

> **Annotate only what the graph itself licenses — never what you personally know.**

You are a materials scientist / lawyer. You know things the graph doesn't. That
knowledge does **not** go into `golden_edges` or `must_be_grounded: true` claims.
If a fact is true in the world but absent from the graph, it is either a
`required_claim` with `must_be_grounded: false` (the system may say it, but it's not
grounded) or, if saying it would overreach, a `forbidden_claim`.

This single rule is what keeps two annotators aligned: you are both reading the same
graph, not comparing your private expertise.

---

## 2. Step-by-step

**Step 1 — Fix the snapshot.** Record the exact `graph_snapshot` id you are looking at.
Do all annotation for a question against that one version.

**Step 2 — Decide answerability first.** Before anything else, ask: *does the graph
contain a path that answers this?*
- **Yes** → `answerable: true`.
- **No** → `answerable: false`, leave `golden_edges` empty, and go straight to
  forbidden claims. These honest-null questions are ~20% of the set by design and are
  the benchmark's differentiator — treat them as first-class, not filler.

**Step 3 — Mark the required edges.** Trace, by hand in the graph, the minimal set of
edges the answer depends on. For each: `role: required`. Add `role: supporting` for
edges that strengthen the answer but whose absence wouldn't make it wrong. Set
`required_provenance` to the grade that edge *should* carry (a band-gap value is
`measured`; a material→application link is usually `derived`).

**Step 4 — List required claims.** Write each fact the answer must contain, in plain
language (the scorer matches them semantically, so exact wording is for you, not the
machine). For each, set:
- `must_be_grounded`: true if it rests on a golden edge; false if it's true-but-not-in-graph.
- `max_confidence`: the strongest phrasing allowed. Anything on a `derived` edge caps at
  `qualified`; anything on a `weak` edge caps at `hedged`/`attributed`. A `measured`
  edge may be `asserted`.

**Step 5 — List forbidden claims.** The tempting hallucinations: facts from outside the
graph, over-generalizations from one data point, mislabeled tags (e.g. "SiC is tagged
power_electronics" when the graph says `transistor_channel`). Give a one-line `reason`.

**Step 6 — Rate difficulty.** `clear` or `borderline`. If you hesitated on
answerability or on whether an edge is required, it's `borderline`. Borderline items are
reported separately and may be excluded from the headline number.

---

## 3. Decision rules for the hard cases

Write these down because they *will* recur:

- **Multiple valid paths to the same answer.** Mark the *union* of edges as
  `supporting` and only the edges common to all valid paths as `required`. Path
  fidelity then rewards any correct route without demanding a specific one.

- **Partially answerable.** The graph answers part of the question but not all. This is
  `answerable: true`, but add the unanswerable portion's facts as `forbidden_claims`
  (the system should not invent them) and note it. If the *core* of the question is
  unanswerable, mark the whole thing `answerable: false`.

- **True in the world, absent in the graph.** `required_claim` with
  `must_be_grounded: false`, or `forbidden_claim` if asserting it would mislead. Never a
  golden edge.

- **DFT/text says X, reality says Y.** Annotate to the graph (X), but you may add the
  correction as a `must_be_grounded: false` claim with a low `max_confidence`. This is
  exactly the AlN ~4 eV (DFT) vs ~6 eV (experiment) situation.

- **Question presupposes a false premise.** `answerable: false`; the correct behaviour
  is to reject the premise, which the scorer reads as a (correct) abstention.

---

## 4. Reliability check (do this, it's the paper's credibility)

- Two annotators independently annotate an overlap set (≥15% of questions).
- Report agreement:
  - **answerable flag** → Cohen's κ (aim κ ≥ 0.8).
  - **golden edge sets** → mean Jaccard overlap of required edges (aim ≥ 0.7).
- Disagreements are resolved by discussion **and** by amending this protocol with the
  new rule, then re-annotating. The protocol grows; the annotations stay consistent.
- Any item still contested after discussion → `difficulty: borderline` or drop it.

---

## 5. Claim decomposition (who splits the answer into claims?)

The scorer needs the system's answer broken into atomic claims. **The benchmark does
this, not the system under test** — otherwise a system can game coverage by emitting
few, vague claims. Use one decomposition method for all systems (an LLM claim-splitter
with a fixed prompt), validate it on a sample by hand, and freeze it. Document the
prompt and the validation in the methods section. The scorer's `matcher` argument is the
injection point for this.

---

## 6. Checklist per question

- [ ] `graph_snapshot` recorded
- [ ] `answerable` decided *before* edges
- [ ] required vs supporting edges marked, with `required_provenance`
- [ ] required claims listed with `must_be_grounded` + `max_confidence`
- [ ] forbidden claims listed with reasons
- [ ] difficulty rated
- [ ] validates against `golden.schema.json`
- [ ] if in overlap set: second annotator done, agreement logged
