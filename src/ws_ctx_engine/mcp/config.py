from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_RATE_LIMITS: dict[str, int] = {
    "search_codebase": 60,
    "get_file_context": 120,
    "get_domain_map": 10,
    "get_index_status": 10,
}


class MCPConfigValidationError(ValueError):
    pass


@dataclass
class MCPConfig:
    rate_limits: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_RATE_LIMITS))
    cache_ttl_seconds: int = 30
    workspace: str | None = None

    @classmethod
    def load(
        cls,
        workspace: str,
        config_path: str | None = None,
        rate_limit_overrides: dict[str, int] | None = None,
        strict: bool = False,
    ) -> MCPConfig:
        data: dict[str, Any] = {}

        resolved_config = (
            Path(config_path)
            if config_path
            else Path(workspace) / ".ws-ctx-engine" / "mcp_config.json"
        )
        if config_path and not resolved_config.exists():
            raise MCPConfigValidationError(f"MCP config file not found: {resolved_config}")

        if resolved_config.exists():
            try:
                with open(resolved_config, encoding="utf-8") as f:
                    loaded = json.load(f)
            except json.JSONDecodeError as exc:
                if strict:
                    raise MCPConfigValidationError(
                        f"Invalid JSON in MCP config: {resolved_config}"
                    ) from exc
                loaded = {}
            except Exception as exc:
                if strict:
                    raise MCPConfigValidationError(
                        f"Failed to read MCP config: {resolved_config}"
                    ) from exc
                loaded = {}

            if isinstance(loaded, dict):
                data = loaded
            elif strict:
                raise MCPConfigValidationError("MCP config must be a JSON object.")

        rate_limits = dict(DEFAULT_RATE_LIMITS)
        raw_limits = data.get("rate_limits")
        if raw_limits is not None and not isinstance(raw_limits, dict):
            if strict:
                raise MCPConfigValidationError("'rate_limits' must be an object.")
        elif isinstance(raw_limits, dict):
            for key, value in raw_limits.items():
                if key not in rate_limits:
                    if strict:
                        raise MCPConfigValidationError(f"Unknown rate limit tool: '{key}'.")
                    continue
                if not isinstance(value, int) or value <= 0:
                    if strict:
                        raise MCPConfigValidationError(
                            f"Rate limit for '{key}' must be a positive integer."
                        )
                    continue
                rate_limits[key] = value

        if rate_limit_overrides:
            for key, value in rate_limit_overrides.items():
                if key in rate_limits and isinstance(value, int) and value > 0:
                    rate_limits[key] = value

        cache_ttl_seconds = 30
        raw_ttl = data.get("cache_ttl_seconds")
        if raw_ttl is not None and (not isinstance(raw_ttl, int) or raw_ttl <= 0):
            if strict:
                raise MCPConfigValidationError("'cache_ttl_seconds' must be a positive integer.")
        elif isinstance(raw_ttl, int) and raw_ttl > 0:
            cache_ttl_seconds = raw_ttl

        resolved_workspace: str | None = None
        raw_workspace = data.get("workspace")
        if raw_workspace is not None:
            if not isinstance(raw_workspace, str) or not raw_workspace.strip():
                if strict:
                    raise MCPConfigValidationError(
                        "'workspace' must be a non-empty string when provided."
                    )
            else:
                resolved_workspace = raw_workspace.strip()

        return cls(
            rate_limits=rate_limits,
            cache_ttl_seconds=cache_ttl_seconds,
            workspace=resolved_workspace,
        )

    def resolve_workspace(self, runtime_workspace: str | None, bootstrap_workspace: str) -> str:
        if runtime_workspace is not None and runtime_workspace.strip():
            return str(Path(runtime_workspace).resolve())

        base_workspace = Path(bootstrap_workspace).resolve()
        if self.workspace:
            configured = Path(self.workspace)
            if configured.is_absolute():
                return str(configured.resolve())
            return str((base_workspace / configured).resolve())

        return str(base_workspace)
