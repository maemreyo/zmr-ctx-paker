"""
Phase 0 — CozoDB Fit Validation
================================
Go/No-go gate before investing in GraphStore (Phase 2).

Runs against this repo (ws-ctx-engine itself):
1. Chunks + extracts graph data with TreeSitterChunker
2. Inserts all nodes + edges into in-memory CozoDB
3. Runs 3 Datalog queries: contains_of, impact_of, find_path
4. Measures p50/p95/p99 latency per query type
5. Prints verdict: PASS / FAIL per target

Usage:
    python scripts/phase0_cozo_validation.py
    python scripts/phase0_cozo_validation.py --repo /path/to/other/repo
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

# Ensure src/ is importable when run from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ── Latency targets (from roadmap Appendix A) ────────────────────────────────
TARGETS = {
    "single_hop_p95_ms": 10.0,
    "multi_hop_p95_ms":  50.0,
}
FAIL_THRESHOLDS = {
    "single_hop_p95_ms": 25.0,
    "multi_hop_p95_ms":  100.0,
}
N_ITERATIONS = 100


# ── CozoDB schema ─────────────────────────────────────────────────────────────

SCHEMA_DDL = """
    :create nodes {
        id: String
        =>
        kind: String,
        name: String,
        file: String,
        language: String
    }
    :create edges {
        src: String, relation: String, dst: String
        =>
    }
"""


def init_db() -> "pycozo.Client":
    from pycozo.client import Client  # type: ignore[import-untyped]

    db = Client("mem", "", {})
    db.run(":create nodes { id: String => kind: String, name: String, file: String, language: String }")
    db.run(":create edges { src: String, relation: String, dst: String => }")
    return db


# ── Bulk insert ───────────────────────────────────────────────────────────────

def insert_nodes(db: "pycozo.Client", nodes: list) -> None:
    rows = [[n.id, n.kind, n.name, n.file, n.language] for n in nodes]
    db.run(
        "?[id, kind, name, file, language] <- $rows :put nodes { id => kind, name, file, language }",
        {"rows": rows},
    )


def insert_edges(db: "pycozo.Client", edges: list) -> None:
    rows = [[e.src, e.relation, e.dst] for e in edges]
    db.run(
        "?[src, relation, dst] <- $rows :put edges { src, relation, dst }",
        {"rows": rows},
    )


# ── Queries ───────────────────────────────────────────────────────────────────

def _rows(df) -> list:
    """Extract rows from a pycozo result (pandas DataFrame)."""
    return df.values.tolist() if len(df) > 0 else []


def query_contains_of(db: "pycozo.Client", file_id: str) -> list:
    """Single-hop: symbols contained in a file."""
    df = db.run(
        """
        ?[sym, kind] :=
            *edges{ src: $file, relation: "CONTAINS", dst: sym },
            *nodes{ id: sym, kind }
        """,
        {"file": file_id},
    )
    return _rows(df)


def query_impact_of(db: "pycozo.Client", file_id: str) -> list:
    """Single-hop: files that share the same language as the anchor (proxy for IMPORTS until Phase 2)."""
    df = db.run(
        """
        ?[other_file] :=
            *nodes{ id: $file, language: lang },
            *nodes{ id: other_file, kind: "file", language: lang },
            other_file != $file
        """,
        {"file": file_id},
    )
    return _rows(df)


def query_find_path(db: "pycozo.Client", src_file: str, dst_file: str) -> list:
    """Multi-hop (depth-2): files reachable via shared symbol names (CONTAINS proxy)."""
    df = db.run(
        """
        reachable[a, b] :=
            *edges{ src: a, relation: "CONTAINS", dst: sym },
            *edges{ src: b, relation: "CONTAINS", dst: sym },
            a != b

        ?[hop1, hop2] :=
            reachable[$src, hop1],
            reachable[hop1, hop2],
            hop2 != $src
        :limit 20
        """,
        {"src": src_file, "dst": dst_file},
    )
    return _rows(df)


# ── Benchmarking ──────────────────────────────────────────────────────────────

def bench(fn, *args, n: int = N_ITERATIONS) -> dict:
    latencies: list[float] = []
    result = None
    for _ in range(n):
        t0 = time.perf_counter()
        result = fn(*args)
        latencies.append((time.perf_counter() - t0) * 1000)
    latencies.sort()
    return {
        "result_count": len(result) if result is not None else 0,
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(latencies[int(n * 0.95)], 3),
        "p99_ms": round(latencies[int(n * 0.99)], 3),
        "min_ms": round(latencies[0], 3),
        "max_ms": round(latencies[-1], 3),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 0: CozoDB fit validation")
    parser.add_argument("--repo", default=str(Path(__file__).parent.parent), help="Repo path to index")
    args = parser.parse_args()

    repo_path = args.repo
    print(f"\n{'='*60}")
    print(f"Phase 0 — CozoDB Fit Validation")
    print(f"Repo: {repo_path}")
    print(f"{'='*60}\n")

    # ── Step 1: Chunk the repo ────────────────────────────────────────────────
    print("Step 1/4: Chunking repo with TreeSitterChunker...")
    t0 = time.perf_counter()
    from ws_ctx_engine.chunker.tree_sitter import TreeSitterChunker
    chunker = TreeSitterChunker()
    chunks = chunker.parse(repo_path)
    chunk_time = time.perf_counter() - t0
    print(f"  → {len(chunks)} chunks in {chunk_time:.2f}s")

    # ── Step 2: Build graph ───────────────────────────────────────────────────
    print("\nStep 2/4: Building graph (chunks_to_graph)...")
    t0 = time.perf_counter()
    from ws_ctx_engine.graph.builder import chunks_to_graph
    from ws_ctx_engine.graph.validation import validate_graph
    nodes, edges = chunks_to_graph(chunks)
    graph_time = time.perf_counter() - t0

    result = validate_graph(nodes, edges)
    print(f"  → {len(nodes)} nodes, {len(edges)} edges in {graph_time*1000:.1f}ms")
    print(f"  → Validation: {'✅ valid' if result.is_valid else '❌ INVALID'}")
    if result.errors:
        for e in result.errors:
            print(f"    ERROR: {e}")
    if result.warnings:
        print(f"  → {len(result.warnings)} warnings (orphan symbols)")

    file_nodes = [n for n in nodes if n.kind == "file"]
    sym_nodes  = [n for n in nodes if n.kind != "file"]
    print(f"  → File nodes: {len(file_nodes)}, Symbol nodes: {len(sym_nodes)}")

    # ── Step 3: Insert into CozoDB ────────────────────────────────────────────
    print("\nStep 3/4: Inserting into in-memory CozoDB...")
    t0 = time.perf_counter()
    db = init_db()
    insert_nodes(db, nodes)
    insert_edges(db, edges)
    insert_time = time.perf_counter() - t0
    print(f"  → Inserted in {insert_time*1000:.1f}ms")

    # Pick anchors: prefer files that actually have CONTAINS edges (non-trivial symbols)
    files_with_symbols: set[str] = {e.src for e in edges if e.relation == "CONTAINS"}
    py_rich = [n.id for n in file_nodes if n.language == "python" and n.id in files_with_symbols]
    # Sort by symbol count descending — richest file first
    sym_count = {e.src: 0 for e in edges}
    for e in edges:
        sym_count[e.src] = sym_count.get(e.src, 0) + 1
    py_rich.sort(key=lambda fid: sym_count.get(fid, 0), reverse=True)
    anchor  = py_rich[0] if py_rich else file_nodes[0].id
    anchor2 = py_rich[1] if len(py_rich) > 1 else anchor

    # ── Step 4: Benchmark queries ─────────────────────────────────────────────
    print(f"\nStep 4/4: Benchmarking queries (n={N_ITERATIONS} each)...")
    print(f"  Anchor file: {anchor}\n")

    results: dict[str, dict] = {}

    print("  [1/3] contains_of (single-hop: file → symbols)...")
    results["contains_of"] = bench(query_contains_of, db, anchor)
    r = results["contains_of"]
    print(f"        {r['result_count']} results | p50={r['p50_ms']}ms  p95={r['p95_ms']}ms  p99={r['p99_ms']}ms")

    print("  [2/3] impact_of (single-hop: co-language files)...")
    results["impact_of"] = bench(query_impact_of, db, anchor)
    r = results["impact_of"]
    print(f"        {r['result_count']} results | p50={r['p50_ms']}ms  p95={r['p95_ms']}ms  p99={r['p99_ms']}ms")

    print("  [3/3] find_path (multi-hop depth-2: shared-symbol reachability)...")
    results["find_path"] = bench(query_find_path, db, anchor, anchor2)
    r = results["find_path"]
    print(f"        {r['result_count']} results | p50={r['p50_ms']}ms  p95={r['p95_ms']}ms  p99={r['p99_ms']}ms")

    # ── Verdict ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("VERDICT")
    print(f"{'='*60}")

    all_pass = True

    single_hop_p95 = max(results["contains_of"]["p95_ms"], results["impact_of"]["p95_ms"])
    multi_hop_p95  = results["find_path"]["p95_ms"]

    def check(label: str, actual: float, target: float, fail: float) -> bool:
        if actual <= target:
            status = "✅ PASS"
        elif actual <= fail:
            status = "⚠️  WARN"
        else:
            status = "❌ FAIL"
            return False
        print(f"  {status}  {label}: {actual}ms  (target <{target}ms, fail >{fail}ms)")
        return actual <= fail

    ok1 = check("Single-hop p95", single_hop_p95, TARGETS["single_hop_p95_ms"], FAIL_THRESHOLDS["single_hop_p95_ms"])
    ok2 = check("Multi-hop  p95", multi_hop_p95,  TARGETS["multi_hop_p95_ms"],  FAIL_THRESHOLDS["multi_hop_p95_ms"])
    all_pass = ok1 and ok2

    print()
    if not result.is_valid:
        print("  ❌ FAIL  Graph validation errors — fix before Phase 2")
        all_pass = False

    print(f"\n{'='*60}")
    if all_pass:
        print("  🟢 GO — CozoDB fit confirmed. Ready for Phase 2 (GraphStore).")
    else:
        print("  🔴 NO-GO — Latency or validation issues. Investigate before Phase 2.")
    print(f"{'='*60}\n")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
