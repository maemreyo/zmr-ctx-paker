# Output Schema Reference

ws-ctx-engine supports four output formats: **XML**, **JSON**, **YAML**, and **MD** (Markdown).

---

## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "WsCtxEngineOutput",
  "type": "object",
  "required": ["metadata", "files"],
  "properties": {
    "metadata": {
      "type": "object",
      "properties": {
        "repo_name":     { "type": "string" },
        "file_count":    { "type": "integer" },
        "total_tokens":  { "type": "integer" },
        "query":         { "type": ["string", "null"] },
        "generated_at":  { "type": "string", "format": "date-time" },
        "index_health":  { "type": "object" }
      }
    },
    "files": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["path", "score", "content"],
        "properties": {
          "path":             { "type": "string" },
          "score":            { "type": "number", "minimum": 0 },
          "domain":           { "type": "string" },
          "summary":          { "type": "string" },
          "content":          { "type": ["string", "null"] },
          "dependencies":     { "type": "array", "items": { "type": "string" } },
          "dependents":       { "type": "array", "items": { "type": "string" } },
          "secrets_detected": { "type": "array", "items": { "type": "string" } }
        }
      }
    }
  }
}
```

---

## YAML Format

The YAML output is structurally identical to JSON, wrapped under a `context` key:

```yaml
context:
  metadata:
    repo_name: my-repo
    file_count: 12
    total_tokens: 41200
    query: "auth flow"
    generated_at: "2026-03-26T10:00:00Z"
  files:
    - path: src/auth/handler.py
      score: 0.92
      domain: auth
      content: |
        def handle_login(request):
            ...
```

YAML output is typically 15–20% smaller than XML for the same content.

---

## XML Format (Repomix-compatible)

```xml
<?xml version='1.0' encoding='utf-8'?>
<repository>
  <metadata>
    <name>my-repo</name>
    <file_count>12</file_count>
    <total_tokens>41200</total_tokens>
    <query>auth flow</query>
  </metadata>
  <files>
    <file path="src/auth/handler.py" tokens="1234">
      <![CDATA[...file content...]]>
    </file>
  </files>
</repository>
```

---

## MCP Response Schema

When ws-ctx-engine is used as an MCP server, responses follow this schema:

```json
{
  "type": "status" | "result" | "error" | "meta",
  "command": "pack" | "query" | "index" | "search",
  "status": "success" | "error",
  "output_path": "/path/to/output.xml",
  "total_tokens": 41200,
  "generated_at": "2026-03-26T10:00:00Z"
}
```

---

## Pipe Examples

```bash
# Pack to stdout, pipe to clipboard (macOS)
wsctx pack . --format xml --stdout | pbcopy

# Pack to stdout, pipe to claude CLI
wsctx query "auth flow" --format xml --stdout | claude

# Validate XML output
wsctx pack . --format xml --stdout | xmllint --noout -

# Validate YAML output
wsctx pack . --format yaml --stdout | python -c "import yaml,sys; yaml.safe_load(sys.stdin)"

# Count tokens
wsctx pack . --format json --stdout | python -m json.tool | wc -c
```
