# VERITAS — the critic as an abstention detector (Bod 3 + Bod 2 combined)

*Does the adversarial critic (Layer 2) give a stronger "I don't know" mechanism than a
lexical relevance floor? And where does it stop — where does only the deterministic
scorer (Layer 3) suffice? Measured on the four abstain questions.*

---

## The question

The first VERITAS results argued a lexical fulltext floor is not enough for honest
abstention — it thresholds a similarity score, but it doesn't understand *why* a question
is unanswerable. The two-agent experiment suggested the critic might do better, because
it reasons about meaning. This checks whether it actually does.

## Result: the critic abstains correctly when the premise is false

On the three "the answer does not exist in law" questions, the critic flagged
SHOULD_HAVE_ABSTAINED — and for the right reason each time:

| Question | Why it's unanswerable | What the critic said |
|---|---|---|
| q008 | no programming-language rule exists | "The Act does not impose any programming-language requirement" |
| q009 | a 2027 court ruling, outside the Act | "refers to a 2027 CJEU ruling that is outside the Act" |
| q010 | Article 141 does not exist | "Article 141 does not exist in the EU AI Act (which ends at Article 113)" |

This is qualitatively stronger than a relevance floor. A floor only measures how well the
translated query matches *something*; the critic recognises that the **premise itself is
false** — the article doesn't exist, the event is outside the law. It understands the
question, not just its keyword overlap.

## The boundary: coverage-gap defeats the critic (q013)

On q013 — "what practices are prohibited?" — the critic did **not** flag abstention. It
treated the question as answerable and raised factual objections instead ("Art. 5 does not
set fines"; "omits untargeted facial-image scraping").

Why: prohibited practices genuinely **exist** in the law, so from text alone the premise
looks answerable. What the critic cannot see is that in *this graph* Article 5 is only
chunked as raw text, with no structured obligations to traverse. That fact lives in the
graph, and the critic never sees the graph.

## The combined finding (Layer 2 + Layer 3)

Two kinds of honest-null, two different layers:

- **False-premise abstention** ("not in the law") → the **critic (Layer 2) suffices**. It
  reasons about meaning and catches non-existent articles, out-of-scope events, impossible
  requirements. Stronger than a lexical floor.
- **Coverage-gap abstention** ("in the law, but not structured in the graph") → **only the
  deterministic scorer (Layer 3) suffices**, because only it reads the graph. The critic
  is blind to it by construction.

So the layered design isn't redundancy — each layer owns a distinct failure class.
Together they cover both kinds of "I don't know"; neither does alone. That is the
empirical case for the architecture, measured rather than asserted.

## Practical upshot

A production abstention mechanism should run **both**: the critic to catch false-premise
questions cheaply and in natural language, and the deterministic graph check to catch
coverage gaps the critic cannot perceive. A lexical floor alone catches neither well.
