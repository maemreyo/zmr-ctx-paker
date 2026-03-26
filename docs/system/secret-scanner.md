# Secret Scanner Module

> **Module Path**: `src/ws_ctx_engine/secret_scanner.py`

## Purpose

The Secret Scanner detects credentials and sensitive data in source files before they are included in context packs. It prevents accidental leakage of API keys, database passwords, and private keys to LLMs or shared outputs.

The scanner uses a **two-layer approach**:
1. **Regex patterns** — fast, built-in, zero dependencies
2. **secretlint** — optional external tool for broader coverage

Results are cached by `mtime` + `inode` so unchanged files are not re-scanned.

## Architecture

```
secret_scanner.py
├── _SECRET_PATTERNS     # Built-in regex rules
├── SecretScanResult     # Dataclass: secrets_detected, secret_scan_skipped
└── SecretScanner        # Main class: scan(), caching, secretlint integration
```

## Built-in Regex Patterns

| Pattern Name | What It Detects |
| ------------ | --------------- |
| `aws_access_key` | AWS access key IDs (`AKIA...`) |
| `private_key` | PEM private key headers |
| `database_url_with_password` | DSNs with embedded passwords (postgres/mysql/mongodb) |
| `api_key_assignment` | Assignments like `api_key = "abc123"` |
| `env_secret` | Common env var secrets (`SECRET_KEY=`, `DATABASE_PASSWORD=`, etc.) |

## Key Classes

### SecretScanResult

```python
@dataclass
class SecretScanResult:
    secrets_detected: list[str]    # Names of matched patterns / secretlint rule IDs
    secret_scan_skipped: bool      # True if the file could not be read
```

### SecretScanner

```python
class SecretScanner:
    def __init__(
        self,
        repo_path: str,
        index_dir: str = ".ws-ctx-engine",
        use_secretlint: bool = True,
        secretlint_timeout_seconds: float = 5.0,
    ) -> None:
```

**Constructor Parameters:**

| Parameter | Default | Description |
| --------- | ------- | ----------- |
| `repo_path` | Required | Repository root path |
| `index_dir` | `.ws-ctx-engine` | Directory to store the scan cache |
| `use_secretlint` | `True` | Auto-detect and use `secretlint` if available |
| `secretlint_timeout_seconds` | `5.0` | Per-file timeout for the external tool |

## Scanning Pipeline

```python
result = scanner.scan("src/config.py")
```

1. **Stat check** — get `mtime` + `inode` for the file
2. **Cache lookup** — if cached entry matches `mtime`+`inode`, return cached result immediately
3. **Read content** — read file as UTF-8 (errors ignored)
4. **secretlint** — run external tool if available (with 5s timeout)
5. **Regex scan** — run built-in patterns against content
6. **Merge** — union of secretlint and regex findings, sorted
7. **Cache write** — persist result to `secret_scan_cache.json`

## Cache Format

```
.ws-ctx-engine/
└── secret_scan_cache.json
```

```json
{
  "src/config.py": {
    "mtime": 1705312200.0,
    "inode": 12345678,
    "secrets_found": ["aws_access_key"],
    "scanned_at": "2024-01-15T10:30:00Z"
  }
}
```

## secretlint Integration

The scanner auto-detects `secretlint` via `shutil.which("secretlint")`. It tries two command orderings to handle different secretlint versions:

```python
[secretlint, "--format", "json", file_path]
[secretlint, file_path, "--format", "json"]
```

secretlint output is parsed for `ruleId` or `message` fields from both array and nested object response formats.

If secretlint is unavailable or times out, the scanner falls back to regex-only scanning silently — it never raises.

## CLI Integration

Enable secret scanning via the `--secrets-scan` flag on `query` and `pack` commands:

```bash
# Scan for secrets and redact files that contain them
wsctx query "authentication logic" --secrets-scan

wsctx pack . -q "API layer" --secrets-scan
```

When secrets are detected, the file's content is **redacted** in the output and replaced with a warning message. The file is still listed in the pack's index with the detected secret pattern names.

In Markdown output (`--format md`), redacted files display:

```
**Secrets detected:** aws_access_key
**Content redacted for safety.**
```

## Code Example

```python
from ws_ctx_engine.secret_scanner import SecretScanner

scanner = SecretScanner(
    repo_path="/path/to/repo",
    use_secretlint=True,
)

result = scanner.scan("src/config.py")

if result.secrets_detected:
    print(f"REDACTED: {result.secrets_detected}")
else:
    print("Clean")
```

## Performance

- **Cache hit**: microseconds (dict lookup)
- **Regex scan only**: <1ms per file
- **With secretlint**: up to `secretlint_timeout_seconds` per uncached file

For large repos, the cache makes repeated scans fast. The cache is invalidated per-file by `mtime`+`inode`, so only modified files are re-scanned.

## Dependencies

| Dependency | Required | Purpose |
| ---------- | -------- | ------- |
| `re` | Yes (stdlib) | Built-in pattern matching |
| `json` | Yes (stdlib) | Cache persistence |
| `subprocess` | Yes (stdlib) | secretlint invocation |
| `secretlint` | No (external) | Broader secret detection |

## Related Modules

- [CLI](./cli.md) — Exposes `--secrets-scan` flag on `query` and `pack` commands
- [Output Formatters](./output-formatters.md) — Handles redacted content display
- [Workflow](./workflow.md) — Passes `secrets_scan=True` to the query pipeline
