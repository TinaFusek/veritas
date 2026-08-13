# VERITAS — the critic as a cross-lingual drift detector (Bod 4)

*Can the adversarial critic detect a cross-lingual retrieval failure without
understanding the source language? Tested on the Slovak question q007.*

---

## The setup

q007 is asked in Slovak: it names Article 50 explicitly and asks about its
disclosure exemptions. The correct entry is Article 50. But the system diverged —
it retrieved Articles 25, 26, 69, 86 instead. The English version of the same
question retrieves Article 50 correctly, so the failure is in the cross-lingual
retrieval path, not the data. This is exactly the kind of silent failure that is
invisible at the answer-text level: the answer reads plausibly.

## What the critic did

The critic — which was never told the question is Slovak, and does not reason about
Slovak morphology — caught the divergence three independent ways:

- **MISSING_CORE (Art. 50):** flagged that Article 50, which actually contains the
  exemptions asked about, is absent from the answer.
- **SHOULD_HAVE_ABSTAINED (Art. 50):** noted the system gave a speculative external
  recommendation instead of cleanly abstaining when it lacked the article.
- **OVER_REACH (Art. 25, 26, 69, 86):** stated the cited articles are "not relevant
  to the transparency exemptions of Article 50 and appear to be keyword-related
  rather than legally relevant."

## Why this matters

The third objection is the key one. The critic detected the cross-lingual failure
**without needing to understand Slovak at all** — it only had to recognise that the
cited articles don't match the topic the question is about. That sidesteps the whole
problem of non-dominant-language morphology: you don't need a language-specific
retrieval fix to *detect* the drift, you need a critic that checks topical coherence
between the question and the citations.

This gives a language-agnostic drift detector: for any language, if the retrieved
articles are topically unrelated to the question, the critic flags OVER_REACH. It
does not fix the retrieval — that still needs the article-pinning fix applied to
Aurora — but it makes the failure *visible and automatic*, which is the first step.

## Combined with the honest-null finding

Together with the honest-null analysis, this shows the critic (Layer 2) is a
capable detector of two failure classes that answer-text metrics miss entirely:
false-premise questions, and cross-lingual / topical drift. Its remaining blind spot
is structural — coverage gaps it cannot see without the graph (q013) — which is
precisely what Layer 3 covers. The division of labour is clean and, across q007,
q008, q009, q010 and q013, empirically demonstrated.
