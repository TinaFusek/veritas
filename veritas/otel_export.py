"""
VERITAS -> OpenTelemetry exporter.

Turns a VERITAS trace (trace.schema.json) into OTel spans so GraphRAG runs land
in whatever observability stack the team already has (Grafana/Tempo, Jaeger,
Datadog...) instead of yet another dashboard.

Span model (one OTel trace per VERITAS trace):

    graphrag.question            <- root span, whole run
      graphrag.retrieval         <- entry method, visited nodes, one event per edge
      graphrag.synthesis         <- claims, abstention

Attribute namespace `veritas.*` carries the audit data:
    veritas.trace_id, veritas.question.id, veritas.system.name,
    veritas.retrieval.empty, veritas.answer.abstained,
    veritas.claims.total / .grounded (if a score dict is passed),
    veritas.score.path_fidelity / .provenance_coverage / .overconfidence

Two modes:
  * SDK mode  — if `opentelemetry-sdk` is installed, emits real spans through
                the configured exporter (OTLP endpoint via standard env vars:
                OTEL_EXPORTER_OTLP_ENDPOINT etc.).
  * File mode — no SDK needed; writes an OTLP/JSON-shaped file you can inspect
                or ship later. Default when the SDK is missing.

Usage:
    from veritas_otel import export_trace
    export_trace(trace_dict)                       # SDK if available, else file
    export_trace(trace_dict, score=score_dict)     # attach VERITAS metrics
    export_trace(trace_dict, out="run.otel.json")  # force file mode
"""

from __future__ import annotations

import json
import hashlib
import time
from typing import Optional


# --------------------------------------------------------------- helpers
def _ts_ns(offset_ms: float = 0.0) -> int:
    return int((time.time() + offset_ms / 1000.0) * 1e9)


def _ids_from(trace: dict) -> tuple[str, str]:
    """Deterministic OTel trace_id (32 hex) and root span_id (16 hex) from the
    VERITAS trace_id — the same run always maps to the same OTel trace."""
    seed = (trace.get("trace_id") or "veritas") + trace.get("question", {}).get("id", "")
    h = hashlib.sha256(seed.encode()).hexdigest()
    return h[:32], h[32:48]


def _common_attrs(trace: dict, score: Optional[dict]) -> dict:
    q = trace.get("question", {})
    sysd = trace.get("system", {})
    a = {
        "veritas.trace_id": trace.get("trace_id", ""),
        "veritas.question.id": q.get("id", ""),
        "veritas.question.language": q.get("language", ""),
        "veritas.system.name": sysd.get("name", ""),
        "veritas.system.retrieval_mode": sysd.get("retrieval_mode", ""),
        "veritas.graph_snapshot": sysd.get("graph_snapshot", ""),
    }
    if score:
        pf = score.get("path_fidelity", {})
        cov = score.get("provenance_coverage", {})
        oc = score.get("overconfidence", {})
        hn = score.get("honest_null", {})
        a.update({
            "veritas.score.path_fidelity": pf.get("f1"),
            "veritas.score.provenance_coverage": cov.get("grounded"),
            "veritas.score.overconfidence": oc.get("penalty"),
            "veritas.score.honest_null": hn.get("category"),
        })
    return {k: v for k, v in a.items() if v not in (None, "")}


# --------------------------------------------------------------- SDK mode
def _export_sdk(trace: dict, score: Optional[dict]) -> bool:
    try:
        from opentelemetry import trace as otel
        from opentelemetry.sdk.trace import TracerProvider
    except ImportError:
        return False

    provider = otel.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        # no provider configured by the app -> set a basic one (exporter comes
        # from standard OTEL_* env vars if opentelemetry-exporter-otlp is present)
        provider = TracerProvider()
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        except ImportError:
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        otel.set_tracer_provider(provider)

    tracer = otel.get_tracer("veritas", "0.1.0")
    attrs = _common_attrs(trace, score)
    trav = trace.get("traversal", {})
    ans = trace.get("answer", {})
    timing = trace.get("timing", {})

    with tracer.start_as_current_span("graphrag.question", attributes=attrs) as root:
        root.set_attribute("veritas.answer.abstained", bool(ans.get("abstained")))
        with tracer.start_as_current_span("graphrag.retrieval") as r:
            r.set_attribute("veritas.retrieval.entry_method", trav.get("entry_method", ""))
            r.set_attribute("veritas.retrieval.empty", bool(trav.get("retrieval_empty")))
            r.set_attribute("veritas.retrieval.nodes_visited", len(trav.get("visited_nodes", [])))
            for e in trav.get("used_edges", []):
                r.add_event("edge", {
                    "edge": f"{e['source']}|{e['type']}|{e['target']}",
                    "provenance": e.get("provenance", {}).get("grade", "unknown"),
                })
            if timing.get("retrieval_ms"):
                r.set_attribute("duration_hint_ms", timing["retrieval_ms"])
        with tracer.start_as_current_span("graphrag.synthesis") as s:
            claims = ans.get("claims", [])
            s.set_attribute("veritas.claims.total", len(claims))
            s.set_attribute("veritas.claims.with_evidence",
                            sum(1 for c in claims if c.get("evidence")))
    return True


# --------------------------------------------------------------- file mode
def _export_file(trace: dict, score: Optional[dict], out: str) -> str:
    """OTLP/JSON-shaped output — same span tree, inspectable, shippable later."""
    tid, sid = _ids_from(trace)
    t0 = _ts_ns()
    timing = trace.get("timing", {})
    total = timing.get("total_ms", 1000)
    retr = timing.get("retrieval_ms", total // 2)
    trav = trace.get("traversal", {})
    ans = trace.get("answer", {})

    def attrs_kv(d):  # OTLP attribute list shape
        out = []
        for k, v in d.items():
            if isinstance(v, bool):   val = {"boolValue": v}
            elif isinstance(v, (int,)):   val = {"intValue": str(v)}
            elif isinstance(v, float):    val = {"doubleValue": v}
            else:                         val = {"stringValue": str(v)}
            out.append({"key": k, "value": val})
        return out

    common = _common_attrs(trace, score)
    spans = [
        {
            "traceId": tid, "spanId": sid, "name": "graphrag.question",
            "kind": 1, "startTimeUnixNano": str(t0),
            "endTimeUnixNano": str(t0 + total * 1_000_000),
            "attributes": attrs_kv({**common,
                "veritas.answer.abstained": bool(ans.get("abstained"))}),
        },
        {
            "traceId": tid, "spanId": sid[:8] + "00000001", "parentSpanId": sid,
            "name": "graphrag.retrieval", "kind": 1,
            "startTimeUnixNano": str(t0),
            "endTimeUnixNano": str(t0 + retr * 1_000_000),
            "attributes": attrs_kv({
                "veritas.retrieval.entry_method": trav.get("entry_method", ""),
                "veritas.retrieval.empty": bool(trav.get("retrieval_empty")),
                "veritas.retrieval.nodes_visited": len(trav.get("visited_nodes", [])),
            }),
            "events": [
                {"name": "edge", "timeUnixNano": str(t0 + retr * 1_000_000),
                 "attributes": attrs_kv({
                     "edge": f"{e['source']}|{e['type']}|{e['target']}",
                     "provenance": e.get("provenance", {}).get("grade", "unknown")})}
                for e in trav.get("used_edges", [])
            ],
        },
        {
            "traceId": tid, "spanId": sid[:8] + "00000002", "parentSpanId": sid,
            "name": "graphrag.synthesis", "kind": 1,
            "startTimeUnixNano": str(t0 + retr * 1_000_000),
            "endTimeUnixNano": str(t0 + total * 1_000_000),
            "attributes": attrs_kv({
                "veritas.claims.total": len(ans.get("claims", [])),
                "veritas.claims.with_evidence":
                    sum(1 for c in ans.get("claims", []) if c.get("evidence")),
            }),
        },
    ]
    doc = {"resourceSpans": [{
        "resource": {"attributes": attrs_kv({"service.name":
            trace.get("system", {}).get("name", "graphrag")})},
        "scopeSpans": [{"scope": {"name": "veritas", "version": "0.1.0"},
                        "spans": spans}],
    }]}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    return out


# --------------------------------------------------------------- public API
def export_trace(trace: dict, score: Optional[dict] = None,
                 out: Optional[str] = None) -> str:
    """Export one VERITAS trace. Returns 'sdk' or the written file path."""
    if out is None and _export_sdk(trace, score):
        return "sdk"
    path = out or f"{trace.get('trace_id', 'trace')}.otel.json"
    return _export_file(trace, score, path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python veritas_otel.py <trace.json> [out.json]")
        raise SystemExit(1)
    with open(sys.argv[1]) as f:
        t = json.load(f)
    dest = export_trace(t, out=(sys.argv[2] if len(sys.argv) > 2 else None))
    print(f"exported -> {dest}")
