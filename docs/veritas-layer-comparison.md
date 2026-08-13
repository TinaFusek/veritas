# VERITAS — Layer 2 (critic) vs Layer 3 (scorer)

*What each layer catches per question. The point is the divergence: each layer sees a class of error the other cannot.*

| Question | Type | Layer 2 — adversarial critic | Layer 3 — deterministic scorer |
|---|---|---|---|
| aurora-q002 | answerable | missing core, over reach, wrong entry | F1=0.00 (prec 0.00/uns 0.00, rec 0.00) |
| aurora-q003 | answerable | over reach, unsupported claim | F1=0.86 (prec 0.75/uns 0.09, rec 1.00) |
| aurora-q005 | answerable | missing core, over reach, unsupported claim, wrong entry | F1=0.00 (prec 0.00/uns 0.00, rec 0.00) |
| aurora-q007 | answerable | missing core, over reach, should have abstained | F1=0.00 (prec 0.00/uns 0.00, rec 0.00) |
| aurora-q008 | abstain | over reach, should have abstained, unsupported claim, wrong entry | honest-null (no trace) |
| aurora-q009 | abstain | over reach, should have abstained | honest-null (no trace) |
| aurora-q010 | abstain | over reach, should have abstained, unsupported claim | honest-null (no trace) |
| aurora-q011 | answerable | missing core, over reach, unsupported claim | F1=0.59 (prec 0.42/uns 0.19, rec 1.00) |
| aurora-q012 | answerable | over reach, unsupported claim | (no trace saved) |
| aurora-q013 | abstain | missing core, over reach, unsupported claim | honest-null (no trace) |
| aurora-q014 | answerable | over reach, unsupported claim | (no trace saved) |
| aurora-q015 | answerable | over reach, unsupported claim | (no trace saved) |
| aurora-q016 | answerable | missing core, over reach, unsupported claim | (no trace saved) |

## What this shows

- **Layer 2 (critic)** phrases failures in legal terms — *missing core*, *wrong entry*, *should abstain* — often naming the specific missing article (e.g. it flags Art. 11/12/18 for the provider-documentation question).
- **Layer 3 (scorer)** gives the hard, graph-verified numbers — path fidelity, precision (scoped vs unscoped = over-retrieval), honest-null category.
- **The divergence is the value:** on q013 (coverage-gap) the critic cannot see that the answer exists in law but not in the graph — only Layer 3, which reads the graph, catches it. Conversely the critic often names the *specific* missing article before the scorer quantifies the miss. Neither layer alone is sufficient.
