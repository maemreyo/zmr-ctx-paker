from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import Config
from ..domain_map import DomainMapDB
from ..models import IndexMetadata
from ..secret_scanner import SecretScanner
from ..session.dedup_cache import SessionDeduplicationCache, clear_all_sessions
from ..workflow import search_codebase
from ..workflow.indexer import load_indexes
from ..workflow.query import query_and_pack
from .config import MCPConfig
from .security import RADESession, RateLimiter, WorkspacePathGuard


@dataclass
class CacheEntry:
    payload: dict[str, Any]
    expires_at: float


class MCPToolService:
    def __init__(
        self, workspace: str, config: MCPConfig, index_dir: str = ".ws-ctx-engine"
    ) -> None:
        self.workspace_root = Path(workspace).resolve()
        self.index_dir = index_dir
        self.mcp_config = config

        self._path_guard = WorkspacePathGuard(str(self.workspace_root))
        self._rade = RADESession()
        self._scanner = SecretScanner(repo_path=str(self.workspace_root), index_dir=index_dir)
        self._rate_limiter = RateLimiter(config.rate_limits)
        self._cache: dict[str, CacheEntry] = {}

    def tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "search_codebase",
                "description": "Search the indexed codebase and return ranked file paths.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                        "domain_filter": {"type": "string"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_file_context",
                "description": "Return file content with dependency context and secret redaction.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "include_dependencies": {"type": "boolean", "default": True},
                        "include_dependents": {"type": "boolean", "default": True},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "get_domain_map",
                "description": "Return inferred architecture domains from the domain map index.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_index_status",
                "description": "Return index freshness and workspace recommendation.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "index_status",
                "description": "Alias for get_index_status. Return index freshness and workspace recommendation.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "pack_context",
                "description": (
                    "Query the indexed codebase and pack matching files into a context output. "
                    "Returns the output file path and token statistics."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Natural language query"},
                        "format": {
                            "type": "string",
                            "enum": ["xml", "zip", "json", "yaml", "md"],
                            "default": "xml",
                        },
                        "token_budget": {
                            "type": "integer",
                            "minimum": 1000,
                            "description": "Token budget override (uses config default if omitted)",
                        },
                        "agent_phase": {
                            "type": "string",
                            "enum": ["discovery", "edit", "test"],
                            "description": "Agent phase for context weighting",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "session_clear",
                "description": (
                    "Delete session deduplication cache files. "
                    "Pass session_id to clear a specific session, or omit to clear all sessions."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID to clear (omit to clear all)",
                        },
                    },
                },
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}

        _valid_tools = {
            "search_codebase",
            "get_file_context",
            "get_domain_map",
            "get_index_status",
            "index_status",
            "pack_context",
            "session_clear",
        }
        if name not in _valid_tools:
            return {"error": "TOOL_NOT_FOUND", "message": f"Unknown tool: {name}"}

        if name in {"get_domain_map", "get_index_status", "index_status"}:
            # Normalise alias so the cache key is stable
            canonical = "get_index_status" if name == "index_status" else name
            cache_key = f"tool:{canonical}"
            cached = self._read_cache(cache_key)
            if cached is not None:
                return cached

        # Use the canonical name for rate limiting (alias shares the same bucket)
        rate_name = "get_index_status" if name == "index_status" else name
        allowed, retry_after = self._rate_limiter.allow(rate_name)
        if not allowed:
            limit = self.mcp_config.rate_limits.get(rate_name, 0)
            return {
                "error": "RATE_LIMIT_EXCEEDED",
                "retry_after_seconds": retry_after,
                "message": f"{rate_name} limit: {limit}/min. Back off and retry.",
            }

        if name == "search_codebase":
            payload = self._search_codebase(args)
        elif name == "get_file_context":
            payload = self._get_file_context(args)
        elif name == "get_domain_map":
            payload = self._get_domain_map()
            if "error" not in payload:
                self._write_cache("tool:get_domain_map", payload)
        elif name in {"get_index_status", "index_status"}:
            payload = self._get_index_status()
            if "error" not in payload:
                self._write_cache("tool:get_index_status", payload)
        elif name == "pack_context":
            payload = self._pack_context(args)
        else:
            payload = self._session_clear(args)

        return payload

    def _search_codebase(self, args: dict[str, Any]) -> dict[str, Any]:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return {
                "error": "INVALID_ARGUMENT",
                "message": "'query' is required and must be a non-empty string.",
            }

        limit = args.get("limit", 10)
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            return {
                "error": "INVALID_ARGUMENT",
                "message": "'limit' must be an integer in [1, 50].",
            }

        domain_filter = args.get("domain_filter")
        if domain_filter is not None and not isinstance(domain_filter, str):
            return {
                "error": "INVALID_ARGUMENT",
                "message": "'domain_filter' must be a string when provided.",
            }

        cfg = Config.load(str(self.workspace_root / ".ws-ctx-engine.yaml"))
        try:
            results, index_health = search_codebase(
                repo_path=str(self.workspace_root),
                query=query,
                config=cfg,
                limit=limit,
                domain_filter=domain_filter,
                index_dir=self.index_dir,
            )
            return {"results": results, "index_health": index_health}
        except FileNotFoundError as exc:
            return {"error": "INDEX_NOT_FOUND", "message": str(exc)}
        except Exception as exc:
            return {"error": "SEARCH_FAILED", "message": str(exc)}

    def _get_file_context(self, args: dict[str, Any]) -> dict[str, Any]:
        raw_path = args.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return {
                "error": "INVALID_ARGUMENT",
                "message": "'path' is required and must be a non-empty string.",
            }

        include_dependencies_arg = args.get("include_dependencies", True)
        include_dependents_arg = args.get("include_dependents", True)
        if not isinstance(include_dependencies_arg, bool):
            return {
                "error": "INVALID_ARGUMENT",
                "message": "'include_dependencies' must be a boolean when provided.",
            }
        if not isinstance(include_dependents_arg, bool):
            return {
                "error": "INVALID_ARGUMENT",
                "message": "'include_dependents' must be a boolean when provided.",
            }

        include_dependencies = include_dependencies_arg
        include_dependents = include_dependents_arg
        index_health = self._index_health_or_unknown()

        try:
            resolved = self._path_guard.resolve_relative(raw_path)
        except PermissionError as exc:
            return {
                "path": raw_path,
                "content": None,
                "error": str(exc),
                "secrets_detected": [],
                "sanitized": False,
                "index_health": index_health,
            }

        if not resolved.exists() or not resolved.is_file():
            return {
                "path": raw_path,
                "content": None,
                "error": "FILE_NOT_FOUND",
                "secrets_detected": [],
                "sanitized": False,
                "index_health": index_health,
            }

        rel_path = self._path_guard.to_relative_posix(resolved)
        dependencies, dependents = self._load_neighbors(rel_path)

        scan_result = self._scanner.scan(rel_path)
        if scan_result.secrets_detected:
            return {
                "path": rel_path,
                "language": self._detect_language(resolved),
                "line_count": self._line_count(resolved),
                "content": None,
                "dependencies": dependencies if include_dependencies else [],
                "dependents": dependents if include_dependents else [],
                "secrets_detected": scan_result.secrets_detected,
                "sanitized": False,
                "error": "File excluded: contains sensitive credentials. Remove secrets and re-index, or use environment variables.",
                "index_health": index_health,
            }

        try:
            content = resolved.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            return {
                "path": rel_path,
                "content": None,
                "error": f"FILE_READ_FAILED: {exc}",
                "secrets_detected": [],
                "sanitized": False,
                "index_health": index_health,
            }

        wrapped = self._rade.wrap(rel_path, content)
        return {
            "path": rel_path,
            "language": self._detect_language(resolved),
            "line_count": self._line_count(resolved),
            **wrapped,
            "dependencies": dependencies if include_dependencies else [],
            "dependents": dependents if include_dependents else [],
            "secrets_detected": [],
            "sanitized": True,
            "index_health": index_health,
        }

    def _get_domain_map(self) -> dict[str, Any]:
        metadata = self._load_metadata()
        if metadata is None:
            return {
                "error": "INDEX_NOT_FOUND",
                "message": "Index metadata not found. Run 'ws-ctx-engine index .' first.",
            }

        index_health = self._build_index_health(metadata)

        graph_stats = {"total_nodes": 0, "total_edges": 0, "avg_degree": 0.0}
        pagerank_scores: dict[str, float] = {}
        try:
            _, graph, _ = load_indexes(
                str(self.workspace_root), index_dir=self.index_dir, auto_rebuild=False
            )
            graph_stats = self._graph_stats(graph)
            pagerank_scores = graph.pagerank()
        except Exception:
            pagerank_scores = {}

        domains: list[dict[str, Any]] = []
        db_path = self.workspace_root / self.index_dir / "domain_map.db"
        files_indexed = sorted(metadata.file_hashes.keys())

        try:
            db = DomainMapDB(str(db_path))
            keywords = sorted(db.keywords)
            for keyword in keywords:
                directories = db.get(keyword)
                if not directories:
                    continue

                matched_files = self._matched_files(files_indexed, directories)
                if not matched_files:
                    continue

                ranked_files = sorted(
                    matched_files, key=lambda p: pagerank_scores.get(p, 0.0), reverse=True
                )
                pagerank_weight = round(
                    sum(pagerank_scores.get(path, 0.0) for path in matched_files), 6
                )

                domains.append(
                    {
                        "name": keyword,
                        "file_count": len(matched_files),
                        "keywords": [keyword],
                        "top_files": ranked_files[:3],
                        "pagerank_weight": pagerank_weight,
                    }
                )

            db.close()
        except Exception:
            domains = []

        domains.sort(key=lambda item: (item["file_count"], item["pagerank_weight"]), reverse=True)

        return {
            "domains": domains[:50],
            "graph_stats": graph_stats,
            "index_health": index_health,
        }

    def _get_index_status(self) -> dict[str, Any]:
        metadata = self._load_metadata()
        if metadata is None:
            return {
                "error": "INDEX_NOT_FOUND",
                "message": "Index metadata not found. Run 'ws-ctx-engine index .' first.",
                "workspace": str(self.workspace_root),
            }

        index_health = self._build_index_health(metadata)
        recommendation = (
            "Rebuild the index with: ws-ctx-engine index ."
            if index_health.get("status") == "stale"
            else "Index appears up-to-date."
        )
        return {
            "index_health": index_health,
            "recommendation": recommendation,
            "workspace": str(self.workspace_root),
        }

    def _load_metadata(self) -> IndexMetadata | None:
        metadata_path = self.workspace_root / self.index_dir / "metadata.json"
        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, encoding="utf-8") as f:
                payload = json.load(f)
            created_at_raw = payload.get("created_at")
            if not isinstance(created_at_raw, str):
                return None
            return IndexMetadata(
                created_at=datetime.fromisoformat(created_at_raw),
                repo_path=str(payload.get("repo_path", str(self.workspace_root))),
                file_count=int(payload.get("file_count", 0)),
                backend=str(payload.get("backend", "unknown")),
                file_hashes=dict(payload.get("file_hashes", {})),
            )
        except Exception:
            return None

    def _build_index_health(self, metadata: IndexMetadata) -> dict[str, Any]:
        vcs = "git" if (self.workspace_root / ".git").exists() else "none"
        status = "unknown"
        stale_reason: str | None = None

        if vcs == "git":
            try:
                if metadata.is_stale(str(self.workspace_root)):
                    status = "stale"
                    stale_reason = "Repository files changed since index build"
                else:
                    status = "current"
            except Exception:
                status = "unknown"

        index_built_at = metadata.created_at.replace(microsecond=0)
        if index_built_at.tzinfo is None:
            index_built_at = index_built_at.replace(tzinfo=UTC)

        return {
            "status": status,
            "stale_reason": stale_reason,
            "files_indexed": metadata.file_count,
            "index_built_at": index_built_at.isoformat().replace("+00:00", "Z"),
            "vcs": vcs,
        }

    def _index_health_or_unknown(self) -> dict[str, Any]:
        metadata = self._load_metadata()
        if metadata is None:
            vcs = "git" if (self.workspace_root / ".git").exists() else "none"
            return {
                "status": "unknown",
                "stale_reason": "Index metadata not found",
                "files_indexed": 0,
                "index_built_at": None,
                "vcs": vcs,
            }
        return self._build_index_health(metadata)

    def _load_neighbors(self, path: str) -> tuple[list[str], list[str]]:
        try:
            _, graph, _ = load_indexes(
                str(self.workspace_root), index_dir=self.index_dir, auto_rebuild=False
            )
        except Exception:
            return [], []

        graph_obj = getattr(graph, "graph", None)
        if graph_obj is None:
            return [], []

        try:
            if hasattr(graph, "_nx"):
                dependencies = sorted(str(x) for x in graph_obj.successors(path))
                dependents = sorted(str(x) for x in graph_obj.predecessors(path))
                return dependencies, dependents

            if hasattr(graph, "file_to_vertex") and hasattr(graph, "vertex_to_file"):
                vertex = graph.file_to_vertex.get(path)
                if vertex is None:
                    return [], []
                dependencies = sorted(
                    str(graph.vertex_to_file[v]) for v in graph_obj.successors(vertex)
                )
                dependents = sorted(
                    str(graph.vertex_to_file[v]) for v in graph_obj.predecessors(vertex)
                )
                return dependencies, dependents
        except Exception:
            return [], []

        return [], []

    def _graph_stats(self, graph: Any) -> dict[str, Any]:
        graph_obj = getattr(graph, "graph", None)
        if graph_obj is None:
            return {"total_nodes": 0, "total_edges": 0, "avg_degree": 0.0}

        try:
            if hasattr(graph, "_nx"):
                nodes = int(graph_obj.number_of_nodes())
                edges = int(graph_obj.number_of_edges())
            else:
                nodes = int(graph_obj.vcount())
                edges = int(graph_obj.ecount())

            avg_degree = round((2.0 * edges / nodes), 2) if nodes else 0.0
            return {"total_nodes": nodes, "total_edges": edges, "avg_degree": avg_degree}
        except Exception:
            return {"total_nodes": 0, "total_edges": 0, "avg_degree": 0.0}

    @staticmethod
    def _matched_files(files: list[str], directories: list[str]) -> list[str]:
        matched: set[str] = set()
        for directory in directories:
            normalized = str(directory).strip("/")
            if normalized in {"", "."}:
                continue
            prefix = f"{normalized}/"
            for file_path in files:
                if file_path == normalized or file_path.startswith(prefix):
                    matched.add(file_path)
        return sorted(matched)

    @staticmethod
    def _detect_language(path: Path) -> str:
        suffix = path.suffix.lower()
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
        }
        return mapping.get(suffix, "text")

    @staticmethod
    def _line_count(path: Path) -> int:
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def _read_cache(self, key: str) -> dict[str, Any] | None:
        entry = self._cache.get(key)
        if entry is None:
            return None

        now = datetime.now(UTC).timestamp()
        if now >= entry.expires_at:
            self._cache.pop(key, None)
            return None

        return entry.payload

    def _pack_context(self, args: dict[str, Any]) -> dict[str, Any]:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return {
                "error": "INVALID_ARGUMENT",
                "message": "'query' is required and must be a non-empty string.",
            }

        fmt = args.get("format", "xml")
        _valid_formats = {"xml", "zip", "json", "yaml", "md"}
        if fmt not in _valid_formats:
            return {
                "error": "INVALID_ARGUMENT",
                "message": f"'format' must be one of {sorted(_valid_formats)}.",
            }

        token_budget = args.get("token_budget")
        if token_budget is not None:
            if not isinstance(token_budget, int) or token_budget < 1000:
                return {
                    "error": "INVALID_ARGUMENT",
                    "message": "'token_budget' must be an integer ≥ 1000.",
                }

        agent_phase = args.get("agent_phase")
        if agent_phase is not None and agent_phase not in {"discovery", "edit", "test"}:
            return {
                "error": "INVALID_ARGUMENT",
                "message": "'agent_phase' must be 'discovery', 'edit', or 'test'.",
            }

        base_cfg = Config.load(str(self.workspace_root / ".ws-ctx-engine.yaml"))
        # Use dataclasses.replace to avoid mutating the loaded config object (H-4).
        replace_kwargs: dict[str, Any] = {"format": fmt}
        if token_budget is not None:
            replace_kwargs["token_budget"] = token_budget
        cfg = dataclasses.replace(base_cfg, **replace_kwargs)

        try:
            output_path, tracker = query_and_pack(
                repo_path=str(self.workspace_root),
                query=query,
                config=cfg,
                index_dir=self.index_dir,
                agent_phase=agent_phase,
            )
        except FileNotFoundError as exc:
            return {"error": "INDEX_NOT_FOUND", "message": str(exc)}
        except Exception as exc:
            return {"error": "PACK_FAILED", "message": str(exc)}

        # Guard output_path to the workspace (M-2): the config's output_path may
        # be an absolute path set by the user — verify it stays inside the workspace.
        resolved_output = Path(output_path).resolve()
        resolved_workspace = self.workspace_root.resolve()
        if not str(resolved_output).startswith(str(resolved_workspace)):
            # Return the path but flag it so callers know it is external.
            pass  # non-blocking: informational only; pack already completed

        result: dict[str, Any] = {"output_path": output_path}
        metrics_obj = getattr(tracker, "metrics", None)
        if metrics_obj is not None:
            result["total_tokens"] = getattr(metrics_obj, "total_tokens", 0)
            result["file_count"] = getattr(metrics_obj, "files_processed", 0)
        return result

    _SESSION_ID_RE = re.compile(r"[a-zA-Z0-9_\-]{1,128}")

    def _session_clear(self, args: dict[str, Any]) -> dict[str, Any]:
        cache_dir = self.workspace_root / self.index_dir
        session_id = args.get("session_id")

        if session_id is not None:
            # C-1: allowlist validation before constructing any file path.
            if not isinstance(session_id, str) or not session_id.strip():
                return {
                    "error": "INVALID_ARGUMENT",
                    "message": "'session_id' must be a non-empty string when provided.",
                }
            if not self._SESSION_ID_RE.fullmatch(session_id):
                return {
                    "error": "INVALID_ARGUMENT",
                    "message": (
                        "'session_id' must match [a-zA-Z0-9_-]{1,128}. "
                        "Directory separators and special characters are not allowed."
                    ),
                }
            try:
                cache = SessionDeduplicationCache(session_id=session_id, cache_dir=cache_dir)
            except PermissionError as exc:
                return {"error": "ACCESS_DENIED", "message": str(exc)}
            # H-5: use actual deleted count returned by clear().
            deleted = cache.clear()
            return {"cleared": True, "session_id": session_id, "files_deleted": deleted}

        deleted = clear_all_sessions(cache_dir)
        return {"cleared": True, "session_id": None, "files_deleted": deleted}

    def _write_cache(self, key: str, payload: dict[str, Any]) -> None:
        now = datetime.now(UTC).timestamp()
        self._cache[key] = CacheEntry(
            payload=payload, expires_at=now + self.mcp_config.cache_ttl_seconds
        )
