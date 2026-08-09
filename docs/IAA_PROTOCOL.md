# Inter-annotator agreement (IAA) — how to run the study

A second annotator makes the "correct path is not just one person's opinion"
claim measurable. You need this before the dataset is publication-strong.

## Steps

1. **Pick a subset.** 5-8 questions is enough for a pilot kappa. Include a mix of
   answerable and honest-null.

2. **Brief the second annotator** with `ANNOTATION_PROTOCOL.md` only — not with your
   own goldens. They must annotate independently, or the agreement is meaningless.

3. **Both annotate the same questions** into separate folders:
   `annotatorA/aurora-q003.json`, `annotatorB/aurora-q003.json`, ...

4. **Run the tool:**
   ```bash
   python -m tools.iaa --a annotatorA/ --b annotatorB/
   ```
   Optionally pass `--candidates candidates.json` (question_id -> [edge_key,...])
   so jointly-excluded edges are counted too — this gives a stricter, fairer kappa.

5. **Report the pooled kappa** in the paper. Landis & Koch: >.6 substantial,
   >.8 almost perfect. If it's low, that's itself a finding — it means the questions
   or the protocol need sharpening, not that you hide it.

## What disagreement usually reveals

- Ambiguity in required vs. supporting -> tighten the protocol's rule.
- A question with two genuinely valid paths -> either split it, or annotate both
  paths and mark the shared core as required.
