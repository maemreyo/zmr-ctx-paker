"""
Phase 2 — GraphStore Benchmark
================================
Validates Phase 2 implementation against roadmap latency targets.

Runs against this repo (ws-ctx-engine itself):
1. Chunks + builds full graph (CALLS + IMPORTS) with chunks_to_full_graph
2. Inserts into RocksDB-backed GraphStore (temp dir)
3. Measures latency for: contains_of, callers_of, impact_of
4. Reports node/edge counts with CALLS/IMPORTS breakdown
5. Checks against roadmap targets
6. Prints GO / NO-GO

Usage:
    python scripts/phase2_graphstore_benchmark.py
    python scripts/phase2_graphstore_benchmark.py --repo /path/to/other/repo
    python scripts/phase2_graphstore_benchmark.py --mem   # use in-memory store
"""

from __future__ import annotations

import argparse
import statistics
import sys
import tempfile
import time
from pathlib import Path

# Ensure src/ is importable when run from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ── Latency targets (from roadmap Appendix A) ─────────────────────────────
TARGETS = {
    "single_hop_p95_ms": 10.0,
    "multi_hop_p95_ms": 50.0,
}
FAIL_THRESHOLDS = {
    "single_hop_p95_ms": 25.0,
    "multi_hop_p95_ms": 100.0,
}
N_ITERATIONS = 100


# ── Benchmarking utility ───────────────────────────────────────────────────


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


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2: GraphStore benchmark")
    parser.add_argument(
        "--repo",
        default=str(Path(__file__).parent.parent),
        help="Repo path to index",
    )
    parser.add_argument(
        "--mem",
        action="store_true",
        help="Use in-memory store instead of RocksDB",
    )
    args = parser.parse_args()

    repo_path = args.repo
    print(f"\n{'='*60}")
    print("Phase 2 — GraphStore Benchmark")
    print(f"Repo: {repo_path}")
    print(f"{'='*60}\n")

    # ── Step 1: Chunk the repo ────────────────────────────────────────────
    print("Step 1/4: Chunking repo with TreeSitterChunker...")
    t0 = time.perf_counter()
    from ws_ctx_engine.chunker.tree_sitter import TreeSitterChunker

    chunker = TreeSitterChunker()
    chunks = chunker.parse(repo_path)
    chunk_time = time.perf_counter() - t0
    print(f"  -> {len(chunks)} chunks in {chunk_time:.2f}s")

    # ── Step 2: Build full graph (CALLS + IMPORTS) ────────────────────────
    print("\nStep 2/4: Building full graph (chunks_to_full_graph)...")
    t0 = time.perf_counter()
    from ws_ctx_engine.graph.builder import chunks_to_full_graph
    from ws_ctx_engine.graph.validation import validate_graph

    nodes, edges = chunks_to_full_graph(chunks)
    graph_time = time.perf_counter() - t0

    g_result = validate_graph(nodes, edges)
    contains_edges = [e for e in edges if e.relation == "CONTAINS"]
    calls_edges = [e for e in edges if e.relation == "CALLS"]
    imports_edges = [e for e in edges if e.relation == "IMPORTS"]

    print(f"  -> {len(nodes)} nodes, {len(edges)} total edges in {graph_time*1000:.1f}ms")
    print(f"     CONTAINS={len(contains_edges)}, CALLS={len(calls_edges)}, IMPORTS={len(imports_edges)}")
    print(
        f"  -> Validation: {'PASS (valid)' if g_result.is_valid else 'FAIL (INVALID)'}"
    )
    if g_result.errors:
        for e in g_result.errors:
            print(f"     ERROR: {e}")
    if g_result.warnings:
        print(f"  -> {len(g_result.warnings)} validation warnings")

    file_nodes = [n for n in nodes if n.kind == "file"]
    sym_nodes = [n for n in nodes if n.kind != "file"]
    print(f"  -> File nodes: {len(file_nodes)}, Symbol nodes: {len(sym_nodes)}")

    # ── Step 3: Insert into GraphStore ───────────────────────────────────
    print("\nStep 3/4: Inserting into GraphStore...")
    from ws_ctx_engine.graph.cozo_store import GraphStore

    tmp_dir = None
    if args.mem:
        storage_str = "mem"
        print("  Using in-memory store")
    else:
        tmp_dir = tempfile.mkdtemp(prefix="wsctx_bench_")
        storage_str = f"rocksdb:{tmp_dir}/graph.db"
        print(f"  Using RocksDB: {tmp_dir}/graph.db")

    t0 = time.perf_counter()
    store = GraphStore(storage_str)
    if not store.is_healthy:
        print("  ERROR: GraphStore is not healthy — aborting benchmark")
        return 1

    store.bulk_upsert(nodes, edges)
    insert_time = time.perf_counter() - t0
    print(f"  -> Inserted in {insert_time*1000:.1f}ms")

    # Pick anchor files for benchmarking
    files_with_symbols: set[str] = {e.src for e in edges if e.relation == "CONTAINS"}
    py_files = [n.id for n in file_nodes if n.language == "python" and n.id in files_with_symbols]
    sym_count_map: dict[str, int] = {}
    for e in edges:
        if e.relation == "CONTAINS":
            sym_count_map[e.src] = sym_count_map.get(e.src, 0) + 1
    py_files.sort(key=lambda fid: sym_count_map.get(fid, 0), reverse=True)

    anchor_file = py_files[0] if py_files else (file_nodes[0].id if file_nodes else "")
    # Pick a symbol name for callers_of
    anchor_syms = store.contains_of(anchor_file)
    anchor_sym_name = anchor_syms[0].get("sym", "").split("#")[-1] if anchor_syms else ""

    # ── Step 4: Benchmark queries ─────────────────────────────────────────
    print(f"\nStep 4/4: Benchmarking queries (n={N_ITERATIONS} each)...")
    print(f"  Anchor file:   {anchor_file}")
    print(f"  Anchor symbol: {anchor_sym_name}\n")

    results: dict[str, dict] = {}

    print("  [1/3] contains_of (single-hop: file -> symbols)...")
    results["contains_of"] = bench(store.contains_of, anchor_file)
    r = results["contains_of"]
    print(
        f"        {r['result_count']} results | "
        f"p50={r['p50_ms']}ms  p95={r['p95_ms']}ms  p99={r['p99_ms']}ms"
    )

    print("  [2/3] callers_of (single-hop: who calls function?)...")
    results["callers_of"] = bench(store.callers_of, anchor_sym_name or "nonexistent")
    r = results["callers_of"]
    print(
        f"        {r['result_count']} results | "
        f"p50={r['p50_ms']}ms  p95={r['p95_ms']}ms  p99={r['p99_ms']}ms"
    )

    print("  [3/3] impact_of (single-hop: who imports this file?)...")
    results["impact_of"] = bench(store.impact_of, anchor_file)
    r = results["impact_of"]
    print(
        f"        {r['result_count']} results | "
        f"p50={r['p50_ms']}ms  p95={r['p95_ms']}ms  p99={r['p99_ms']}ms"
    )

    # ── Verdict ───────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("VERDICT")
    print(f"{'='*60}")

    all_pass = True

    single_hop_p95 = max(
        results["contains_of"]["p95_ms"],
        results["callers_of"]["p95_ms"],
        results["impact_of"]["p95_ms"],
    )

    def check(label: str, actual: float, target: float, fail: float) -> bool:
        if actual <= target:
            status = "PASS"
        elif actual <= fail:
            status = "WARN"
        else:
            status = "FAIL"
            return False
        print(f"  [{status}]  {label}: {actual}ms  (target <{target}ms, fail >{fail}ms)")
        return actual <= fail

    ok1 = check(
        "Single-hop p95",
        single_hop_p95,
        TARGETS["single_hop_p95_ms"],
        FAIL_THRESHOLDS["single_hop_p95_ms"],
    )
    all_pass = ok1

    print()
    if not g_result.is_valid:
        print("  [FAIL]  Graph validation errors — check resolver output")
        all_pass = False

    print(f"\nEdge summary:")
    print(f"  CONTAINS : {len(contains_edges)}")
    print(f"  CALLS    : {len(calls_edges)}")
    print(f"  IMPORTS  : {len(imports_edges)}")

    print(f"\n{'='*60}")
    if all_pass:
        print("  GO — GraphStore Phase 2 targets met.")
    else:
        print("  NO-GO — Latency or validation issues. Investigate.")
    print(f"{'='*60}\n")

    # Cleanup temp dir
    if tmp_dir:
        import shutil

        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
