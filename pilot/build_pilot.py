"""
Build the VERITAS pilot dataset skeleton: 20 questions across two graphs,
each with an empty golden stub ready to fill per ANNOTATION_PROTOCOL.md.

Split per domain: 7 answerable (hypothesis) + 3 honest-null (hypothesis) = 10.
Total 20, of which 6 honest-null (30%) — oversampled vs the 20% full-set target
on purpose, so the pilot can stress-test the honest-null axis.

Every 'answerable' flag here is a HYPOTHESIS. The annotator confirms it against
the actual graph (protocol Step 2) and edits if wrong.
"""
import json
import os

SNAPSHOT_AURORA = "aurora-2026-07-11-TODO"   # replace with real snapshot id at annotation time
SNAPSHOT_MATGRAPH = "mp-2026-06-30-sha1:4be2f1"

# (id, text, language, answerable_hypothesis, note_to_annotator)
AURORA = [
    ("aurora-q001", "Is a CV screening tool high-risk?", "en", True,
     "Annex III employment use case -> Art. 6(2). Core answerable case."),
    ("aurora-q002", "What must a provider of a high-risk AI system document?", "en", True,
     "Art. 9/10/11 technical documentation obligations."),
    ("aurora-q003", "What penalties apply to prohibited practices?", "en", True,
     "Art. 5 prohibited -> Art. 99 sanctions. Check the sanction edge exists (this is the one the Cypher bug once missed)."),
    ("aurora-q004", "When do high-risk obligations become applicable?", "en", True,
     "Transitional / entry-into-application dates. Watch for Deadline nodes."),
    ("aurora-q005", "What are the transparency requirements for GPAI models?", "en", True,
     "Art. 53 GPAI. Note: only ~1 trace historically hit GPAI transparency — coverage may be thin."),
    ("aurora-q006", "Kedy platia povinnosti pre vysokorizikové systemy?", "sk", True,
     "SK duplicate of q004. Tests translate-for-retrieval; golden edges should match q004."),
    ("aurora-q007", "Ake su vynimky z povinnosti zverejnenia podla clanku 50?", "sk", True,
     "Art. 50 disclosure exceptions, in Slovak. Answer stays SK; retrieval crosses languages."),
    ("aurora-q008", "Does the AI Act require a specific programming language for compliant systems?", "en", False,
     "HONEST-NULL: the regulation says nothing about programming languages. Correct = abstain / reject premise."),
    ("aurora-q009", "How did the CJEU rule on Article 6 in 2027?", "en", False,
     "HONEST-NULL: graph is the regulation text, not case law, and the date is future. Must not fabricate a ruling."),
    ("aurora-q010", "What does Article 141 of the AI Act require?", "en", False,
     "HONEST-NULL: no such article exists. Correct = say the article isn't in the graph, don't invent it."),
]

MATGRAPH = [
    ("matgraph-q014", "Which wide-gap materials suit power electronics?", "en", True,
     "Canonical case (already annotated). AlN required path."),
    ("matgraph-q015", "Which stable materials have a band gap between 1 and 2 eV?", "en", True,
     "Filter by band_gap + energy_above_hull. Multiple valid materials -> use required/supporting split."),
    ("matgraph-q016", "What is a candidate for a transistor channel?", "en", True,
     "Application match. SiC/GaN tagged transistor_channel here — mind the forbidden 'SiC=power_electronics' claim."),
    ("matgraph-q017", "Why does leakage current worsen below 2 nm?", "en", True,
     "PhysicalEffect layer (tunneling). Provenance is 'derived'/'weak' — max_confidence should cap accordingly."),
    ("matgraph-q018", "Which material has the widest band gap in the graph?", "en", True,
     "Single-answer superlative (AlN). Clean path-fidelity test."),
    ("matgraph-q019", "Is GaN a candidate for power electronics in this graph?", "en", True,
     "Answerable but nuanced: graph tags GaN transistor_channel, not power_electronics. Real-world yes, graph no — annotate to the graph."),
    ("matgraph-q020", "Ktore stabilne materialy maju siroky zakazany pas?", "sk", True,
     "SK cross-lingual for wide-gap stable materials."),
    ("matgraph-q027", "Where are the van Hove singularities in silicon's density of states?", "en", False,
     "HONEST-NULL (already annotated). No DOS data in public MP graph. The gap the QE work fills."),
    ("matgraph-q028", "Which of these materials is most biocompatible for a neural implant?", "en", False,
     "HONEST-NULL: no BioConstraint layer yet. Correct = abstain. Marks exactly the future node type discussed."),
    ("matgraph-q029", "What is the thin-film synthesis temperature for AlN?", "en", False,
     "HONEST-NULL: no SynthesisRoute nodes in v1 graph. Must not invent a temperature."),
]


def stub(qid, snapshot, answerable, note):
    return {
        "veritas_version": "0.1.0",
        "question_id": qid,
        "graph_snapshot": snapshot,
        "answerable": answerable,           # HYPOTHESIS — confirm against graph
        "golden_nodes": [],
        "golden_edges": [],
        "required_claims": [],
        "forbidden_claims": [],
        "annotation": {
            "annotator": "TODO",
            "annotated_at": "TODO",
            "protocol_version": "1.0",
            "_difficulty_hint": "set to 'clear' or 'borderline' when annotating",
            "notes": "HYPOTHESIS answerable=%s. %s" % (answerable, note),
        },
    }


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    gold_dir = os.path.join(base, "golden")
    os.makedirs(gold_dir, exist_ok=True)

    manifest = []
    for domain, snapshot, rows in [
        ("aurora", SNAPSHOT_AURORA, AURORA),
        ("matgraph", SNAPSHOT_MATGRAPH, MATGRAPH),
    ]:
        for qid, text, lang, answerable, note in rows:
            manifest.append({
                "id": qid, "text": text, "language": lang,
                "domain": domain, "answerable_hypothesis": answerable,
            })
            path = os.path.join(gold_dir, qid + ".json")
            # don't clobber the two already-annotated goldens if present
            if os.path.exists(path):
                continue
            with open(path, "w") as f:
                json.dump(stub(qid, snapshot, answerable, note), f, indent=2, ensure_ascii=False)

    with open(os.path.join(base, "questions.json"), "w") as f:
        json.dump({
            "veritas_version": "0.1.0",
            "description": "VERITAS pilot set (20 questions, 2 graphs). answerable flags are hypotheses to confirm.",
            "n": len(manifest),
            "questions": manifest,
        }, f, indent=2, ensure_ascii=False)

    null = sum(1 for q in manifest if not q["answerable_hypothesis"])
    print("questions: %d (%d honest-null hypotheses = %d%%)"
          % (len(manifest), null, round(100 * null / len(manifest))))


if __name__ == "__main__":
    main()
