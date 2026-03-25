"""Secret scanning with mtime+inode cache for CLI and MCP outputs."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "database_url_with_password": re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb)://[^\s:@]+:[^\s@]+@[^\s]+"),
    "api_key_assignment": re.compile(r"\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*[\"'][^\"'\n]{8,}[\"']", re.IGNORECASE),
    "env_secret": re.compile(r"\b(?:SECRET_KEY|DATABASE_PASSWORD|AWS_SECRET_ACCESS_KEY)\s*=\s*[^\n]+", re.IGNORECASE),
}


@dataclass
class SecretScanResult:
    secrets_detected: list[str]
    secret_scan_skipped: bool


class SecretScanner:
    def __init__(
        self,
        repo_path: str,
        index_dir: str = ".ws-ctx-engine",
        use_secretlint: bool = True,
        secretlint_timeout_seconds: float = 5.0,
    ) -> None:
        self.repo_path = Path(repo_path)
        self.cache_path = self.repo_path / index_dir / "secret_scan_cache.json"
        self._cache: dict[str, dict[str, Any]] = self._load_cache()
        self._secretlint_timeout_seconds = secretlint_timeout_seconds
        self._secretlint_cmd = self._detect_secretlint() if use_secretlint else None

    def scan(self, relative_path: str) -> SecretScanResult:
        full_path = self.repo_path / relative_path
        try:
            stat = full_path.stat()
        except OSError:
            return SecretScanResult(secrets_detected=[], secret_scan_skipped=False)

        cached = self._cache.get(relative_path)
        if (
            cached
            and cached.get("mtime") == stat.st_mtime
            and cached.get("inode") == stat.st_ino
            and isinstance(cached.get("secrets_found"), list)
        ):
            return SecretScanResult(
                secrets_detected=[str(x) for x in cached.get("secrets_found", [])],
                secret_scan_skipped=False,
            )

        content = self._read_text(full_path)
        if content is None:
            return SecretScanResult(secrets_detected=[], secret_scan_skipped=False)

        found_from_secretlint = self._scan_with_secretlint(full_path)
        found_from_regex = self._scan_with_regex(content)
        if found_from_secretlint is None:
            found = found_from_regex
        else:
            found = sorted({*found_from_secretlint, *found_from_regex})

        self._cache[relative_path] = {
            "mtime": stat.st_mtime,
            "inode": stat.st_ino,
            "secrets_found": found,
            "scanned_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
        self._save_cache()
        return SecretScanResult(secrets_detected=found, secret_scan_skipped=False)

    def _detect_secretlint(self) -> str | None:
        return shutil.which("secretlint")

    def _scan_with_secretlint(self, full_path: Path) -> list[str] | None:
        if self._secretlint_cmd is None:
            return None

        command_variants = [
            [self._secretlint_cmd, "--format", "json", str(full_path)],
            [self._secretlint_cmd, str(full_path), "--format", "json"],
        ]

        for command in command_variants:
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self._secretlint_timeout_seconds,
                    check=False,
                )
            except Exception:
                continue

            parsed = self._parse_secretlint_json(completed.stdout)
            if parsed is not None:
                if parsed:
                    return parsed
                if completed.returncode == 0:
                    return []

        return None

    def _parse_secretlint_json(self, stdout: str) -> list[str] | None:
        raw = stdout.strip()
        if not raw:
            return []

        try:
            payload = json.loads(raw)
        except Exception:
            return None

        findings: set[str] = set()

        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                rule_id = item.get("ruleId") or item.get("ruleName")
                message = item.get("message")
                if isinstance(rule_id, str) and rule_id.strip():
                    findings.add(rule_id.strip())
                elif isinstance(message, str) and message.strip():
                    findings.add(message.strip().split("\n", 1)[0])

        elif isinstance(payload, dict):
            messages = payload.get("messages")
            if isinstance(messages, list):
                for item in messages:
                    if not isinstance(item, dict):
                        continue
                    rule_id = item.get("ruleId") or item.get("ruleName")
                    message = item.get("message")
                    if isinstance(rule_id, str) and rule_id.strip():
                        findings.add(rule_id.strip())
                    elif isinstance(message, str) and message.strip():
                        findings.add(message.strip().split("\n", 1)[0])

            results = payload.get("results")
            if isinstance(results, list):
                for result in results:
                    if not isinstance(result, dict):
                        continue
                    result_messages = result.get("messages")
                    if not isinstance(result_messages, list):
                        continue
                    for item in result_messages:
                        if not isinstance(item, dict):
                            continue
                        rule_id = item.get("ruleId") or item.get("ruleName")
                        message = item.get("message")
                        if isinstance(rule_id, str) and rule_id.strip():
                            findings.add(rule_id.strip())
                        elif isinstance(message, str) and message.strip():
                            findings.add(message.strip().split("\n", 1)[0])

        return sorted(findings)

    def _scan_with_regex(self, content: str) -> list[str]:
        return [name for name, pattern in _SECRET_PATTERNS.items() if pattern.search(content)]

    def _load_cache(self) -> dict[str, dict[str, Any]]:
        if not self.cache_path.exists():
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
                return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _read_text(path: Path) -> str | None:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return None
