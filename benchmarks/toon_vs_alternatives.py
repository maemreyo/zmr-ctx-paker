#!/usr/bin/env python3
"""
TOON vs alternative format token benchmark.

Compares token counts for TOON, XML, JSON, YAML, and Markdown formatters
using tiktoken (cl100k_base) on synthetic payloads of increasing size.

Usage:
    python benchmarks/toon_vs_alternatives.py

Decision rule applied after results:
    savings vs XML < 10%  → TOON marked deprecated
    savings vs XML ≥ 15%  → TOON promoted to stable
    10% ≤ savings < 15%   → keep experimental, annotate with measured value
"""

from __future__ import annotations

import sys
import tempfile
import textwrap
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure project src is on path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import tiktoken

from ws_ctx_engine.output.json_formatter import JSONFormatter
from ws_ctx_engine.output.md_formatter import MarkdownFormatter
from ws_ctx_engine.output.toon_formatter import TOONFormatter
from ws_ctx_engine.output.yaml_formatter import YAMLFormatter
from ws_ctx_engine.packer.xml_packer import XMLPacker


# ---------------------------------------------------------------------------
# Payload generation
# ---------------------------------------------------------------------------

_PYTHON_TEMPLATE = textwrap.dedent(
    """\
    \"\"\"Module {idx}: Provides utilities for subsystem {idx}.\"\"\"
    from __future__ import annotations
    import logging
    from pathlib import Path
    from typing import Any

    logger = logging.getLogger(__name__)


    class Manager{idx}:
        \"\"\"Manages resources for subsystem {idx}.\"\"\"

        def __init__(self, config: dict[str, Any]) -> None:
            self.config = config
            self._cache: dict[str, Any] = {{}}

        def process(self, data: list[str]) -> list[str]:
            \"\"\"Process data items and return transformed results.\"\"\"
            results = []
            for item in data:
                transformed = self._transform(item)
                if transformed:
                    results.append(transformed)
                    logger.debug("Processed item: %s", item)
            return results

        def _transform(self, item: str) -> str | None:
            if item in self._cache:
                return self._cache[item]
            result = item.strip().lower().replace("-", "_")
            self._cache[item] = result
            return result

        def shutdown(self) -> None:
            \"\"\"Release all held resources.\"\"\"
            self._cache.clear()
            logger.info("Manager{idx} shut down cleanly")


    def create_manager(config: dict[str, Any] | None = None) -> Manager{idx}:
        \"\"\"Factory: create a Manager{idx} with optional config override.\"\"\"
        return Manager{idx}(config or {{}})
"""
)


def _make_metadata(n_files: int) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "repo_name": "benchmark-repo",
        "total_tokens": n_files * 320,
        "file_count": n_files,
        "query": "authentication and session management",
        "generated_at": now.isoformat(),
        "index_health": {
            "status": "current",
            "files_indexed": n_files * 10,
            "index_built_at": now.replace(minute=0, second=0, microsecond=0).isoformat(),
        },
    }


def _make_files(n: int) -> list[dict[str, Any]]:
    files = []
    for i in range(n):
        files.append(
            {
                "path": f"src/subsystem_{i}/manager.py",
                "content": _PYTHON_TEMPLATE.format(idx=i),
                "score": round(0.95 - i * 0.01, 4),
                "domain": f"subsystem_{i % 5}",
                "dependencies": [f"src/subsystem_{(i+1) % n}/manager.py"],
                "dependents": [f"src/subsystem_{(i-1) % n}/manager.py"],
                "secrets_detected": [],
            }
        )
    return files


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


def count_tokens(text: str, enc: tiktoken.Encoding) -> int:
    return len(enc.encode(text))


def measure_all(n_files: int, enc: tiktoken.Encoding) -> dict[str, int]:
    metadata = _make_metadata(n_files)
    files = _make_files(n_files)

    results: dict[str, int] = {}

    # XML (via XMLPacker) — requires real files on disk; write to a temp dir.
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            for f in files:
                file_path = tmp_root / f["path"]
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(f["content"])
            packer = XMLPacker()
            xml_out = packer.pack(
                selected_files=[f["path"] for f in files],
                repo_path=tmpdir,
                metadata=metadata,
            )
        results["xml"] = count_tokens(xml_out, enc)
    except Exception as exc:
        results["xml"] = -1
        print(f"  [xml error] {exc}")

    for name, cls in [
        ("json", JSONFormatter),
        ("yaml", YAMLFormatter),
        ("md", MarkdownFormatter),
        ("toon", TOONFormatter),
    ]:
        try:
            formatter = cls()
            out = formatter.render(metadata, files)
            results[name] = count_tokens(out, enc)
        except Exception as exc:
            results[name] = -1
            print(f"  [{name} error] {exc}")

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _savings_pct(baseline: int, value: int) -> str:
    if baseline <= 0 or value < 0:
        return "  N/A"
    pct = (baseline - value) / baseline * 100
    sign = "+" if pct < 0 else "-"
    return f"{sign}{abs(pct):.1f}%"


def print_table(results_by_size: dict[int, dict[str, int]]) -> None:
    formats = ["xml", "json", "yaml", "md", "toon"]
    sizes = sorted(results_by_size.keys())

    # Header
    col_w = 12
    header = f"{'Format':<8}" + "".join(f"{f'n={n}':>{col_w}}" for n in sizes)
    print(header)
    print("-" * len(header))

    for fmt in formats:
        row = f"{fmt:<8}"
        for n in sizes:
            tokens = results_by_size[n].get(fmt, -1)
            xml_tokens = results_by_size[n].get("xml", 0)
            if fmt == "xml":
                row += f"{tokens:>{col_w},}"
            else:
                savings = _savings_pct(xml_tokens, tokens)
                row += f"{tokens:>{col_w - 6},} ({savings})"
        print(row)


def toon_decision(results_by_size: dict[int, dict[str, int]]) -> str:
    """Apply the decision rule based on average savings vs XML across all sizes."""
    savings_list = []
    for n, results in results_by_size.items():
        xml = results.get("xml", 0)
        toon = results.get("toon", 0)
        if xml > 0 and toon > 0:
            savings_list.append((xml - toon) / xml * 100)

    if not savings_list:
        return "UNKNOWN — TOON benchmark failed to produce results"

    avg = sum(savings_list) / len(savings_list)

    if avg < 10:
        return (
            f"DEPRECATE — average savings {avg:.1f}% < 10% threshold. "
            "TOON adds complexity without meaningful benefit over YAML."
        )
    elif avg >= 15:
        return (
            f"PROMOTE — average savings {avg:.1f}% ≥ 15% threshold. "
            "Remove 'experimental' label and document in README."
        )
    else:
        return (
            f"KEEP EXPERIMENTAL — average savings {avg:.1f}% (10–15% range). "
            "Annotate docstring with measured value but do not promote yet."
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("TOON vs Alternative Formats — Token Benchmark")
    print("=" * 60)
    print("Encoding: cl100k_base (tiktoken)")
    print()

    enc = tiktoken.get_encoding("cl100k_base")
    sizes = [10, 50, 100]

    results_by_size: dict[int, dict[str, int]] = {}
    for n in sizes:
        print(f"Measuring n={n} files...", end=" ", flush=True)
        results_by_size[n] = measure_all(n, enc)
        print("done")

    print()
    print("Token Counts (savings = % reduction vs XML baseline)")
    print("-" * 60)
    print_table(results_by_size)

    print()
    print("Decision:")
    print(toon_decision(results_by_size))


if __name__ == "__main__":
    main()
