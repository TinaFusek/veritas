"""
Aurora Compliance — stamp provenance onto the graph.

Adds the two things belief-half-life and VERITAS need:

  1. graph_snapshot  — a content-derived ID for THIS version of the graph,
                       stored on a (:GraphMeta {name:'aurora'}) node and on every edge.
  2. recorded_at + provenance grade on every relationship:

       measured : none in Aurora yet — statutory text lives on nodes, so Article/Annex
                  NODES get provenance='measured' (source: fetched official text)
       derived  : every LLM-extracted edge (IMPOSES, APPLIES_TO, CONDITIONAL_ON,
                  HAS_EXCEPTION, REFERS_TO, PENALIZED_BY) — Claude produced these
       weak     : CHUNK_OF — retrieval infrastructure, not legal structure

Idempotent: recorded_at is only set where missing (coalesce), so re-running after
adding new data stamps only the new edges — which is exactly what half-life needs.

Run after ingest + add_sanctions:
    python add_provenance.py
"""

import hashlib
import os
from datetime import date

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

DERIVED_RELS = ["IMPOSES", "APPLIES_TO", "CONDITIONAL_ON",
                "HAS_EXCEPTION", "REFERS_TO", "PENALIZED_BY"]
WEAK_RELS = ["CHUNK_OF"]


def compute_snapshot(session) -> str:
    """Content-derived snapshot: hash of every article's number+text hash.
    Same content -> same snapshot, any edit -> new snapshot."""
    rows = session.run(
        "MATCH (a:Article) RETURN a.number AS n, a.text AS t ORDER BY n"
    )
    h = hashlib.sha1()
    for r in rows:
        h.update(str(r["n"]).encode())
        h.update(hashlib.sha1((r["t"] or "").encode()).digest())
    return f"aurora-{date.today().isoformat()}-sha1:{h.hexdigest()[:8]}"


STAMP_META = """
MERGE (g:GraphMeta {name:'aurora'})
SET g.snapshot = $snap, g.stamped_at = datetime()
"""

# node-level: the statutory text itself is the 'measured' layer
STAMP_NODES = """
MATCH (a) WHERE a:Article OR a:Annex
SET a.provenance = 'measured',
    a.recorded_at = coalesce(a.recorded_at, datetime())
"""

# edge-level template — provenance grade + timestamp + snapshot
STAMP_RELS = """
MATCH ()-[r:%s]->()
SET r.provenance   = $grade,
    r.source       = $source,
    r.recorded_at  = coalesce(r.recorded_at, datetime()),
    r.graph_snapshot = $snap
RETURN count(r) AS n
"""


def main() -> None:
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    with driver.session() as s:
        snap = compute_snapshot(s)
        s.run(STAMP_META, snap=snap)
        s.run(STAMP_NODES)
        print(f"snapshot: {snap}")
        print("nodes   : Article/Annex -> provenance='measured'")

        for rel in DERIVED_RELS:
            n = s.run(STAMP_RELS % rel, grade="derived",
                      source="LLM extraction (claude-sonnet-4-6)", snap=snap).single()["n"]
            print(f"edges   : {rel:<15} -> derived   ({n})")
        for rel in WEAK_RELS:
            n = s.run(STAMP_RELS % rel, grade="weak",
                      source="chunking/embedding infrastructure", snap=snap).single()["n"]
            print(f"edges   : {rel:<15} -> weak      ({n})")

    driver.close()
    print("\nProvenance stamped \u2726")
    print("Read it back:  MATCH (g:GraphMeta {name:'aurora'}) RETURN g.snapshot;")


if __name__ == "__main__":
    main()
