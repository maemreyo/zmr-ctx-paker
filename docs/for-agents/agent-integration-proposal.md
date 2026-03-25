# Enhancing ws-ctx-engine for AI Agents: A Strategic Proposal

## 1. The Current Landscape & Problems

**ws-ctx-engine** was originally designed as a *Human-to-AI* bridge. A human developer runs the CLI, generates a ZIP or XML file, and uploads/pastes it into an LLM context window (like Claude.ai, Cursor, or Windsurf).

However, with the rise of autonomous coding agents (Claude Code, TRAE, AutoGPT, SWE-agent), the paradigm is shifting toward *AI-to-Codebase* interactions.

### The Problems
1. **Opaque Output Formats:** Currently, `ws-ctx-engine` exports context as either `.zip` (files + metadata) or `.xml`.
   - A CLI-based AI agent cannot easily "read" a `.zip` file without unzipping it first, which creates friction.
   - An `.xml` dump of 100k tokens printed to standard output (`stdout`) will overwhelm the agent's immediate context window, causing truncation or context-loss errors.
2. **Lack of Incremental Discovery:** Agents don't need the entire context dumped at once. They need to *search*, look at a list of relevant files, read summaries, and then decide which specific files to deep-dive into. `ws-ctx-engine` currently lacks an interactive "search-only" or "summary" mode.
3. **No Native MCP (Model Context Protocol) Support:** The industry standard for exposing tools to AI agents is the Model Context Protocol. `ws-ctx-engine` is purely a CLI tool, meaning agents have to use shell commands to interact with it, parsing unstructured text output.

### Competitive Landscape
The competitive framing "stay ahead of the curve" is **incorrect** and must be reframed. Tools like Repomix already have:
- `--mcp` flag to run as an MCP server
- `--compress` using Tree-sitter for ~70% token reduction
- `--skill-generate` for Claude Agent Skills format
- Built-in security validation for sensitive file detection

**The true differentiation of ws-ctx-engine is not "having MCP" — it is the superior retrieval engine.** ws-ctx-engine has Semantic Vector Search (LEANN/FAISS), Dependency Graph Analysis (PageRank), and Domain Keyword Mapping. No competitor has this combination. The goal of Phase 3 is therefore: *"Expose our superior retrieval engine via MCP"*, not *"add MCP as a checkbox feature."*

## 2. Motivations & Existing Strengths

Why should we optimize `ws-ctx-engine` for AI agents?

- **Leverage Existing Power:** `ws-ctx-engine` *already has* an incredibly powerful core engine: **Semantic Vector Search** (via LEANN/FAISS), **Dependency Graph Analysis** (PageRank), and **Domain Keyword Mapping**. Exposing this existing engine to agents turns them from blind file-readers into context-aware architects.
- **Empower Autonomous Agents:** Codebases are too large for an agent to simply `grep` or `find`. By exposing our semantic search and PageRank graph to agents, we give them a "smart map" of the codebase.
- **Reduce Token Waste:** Instead of an agent reading 50 irrelevant files to find a bug, it can query `ws-ctx-engine` to get the top 5 most semantically relevant files, saving tokens and time.
- **Differentiation:** Unlike Repomix (which focuses on compression and file packing), ws-ctx-engine's retrieval engine enables *intelligent discovery* — agents can ask conceptual questions and get ranked results, not just list all files.

## 3. Potential Solutions & Implementation Plan

To make `ws-ctx-engine` the ultimate tool for AI agents, we need to implement features across three tiers: CLI Discovery, Output Formats, and Protocol Integrations.

### Solution 1: "Search-Only" & "Dry-Run" CLI Commands (Highest ROI)
Agents need to know *what* exists before they decide to read it. This is the fastest quick-win to change agent behavior immediately.

- **Action:** Add a `ws-ctx-engine search "<query>"` command (distinct from `pack`).
- **Behavior:** This command returns *only* a list of file paths, their relevance scores, and short summaries—without dumping the actual file contents.
- **Output Format:** `--agent-mode` outputs **newline-delimited JSON (NDJSON)** for machine parsing:
  ```json
  {"path": "src/auth/login.py", "score": 0.92, "domain": "authentication", "summary": "User authentication via JWT tokens"}
  {"path": "src/models/user.py", "score": 0.85, "domain": "database", "summary": "User ORM model with role field"}
  {"path": "tests/test_auth.py", "score": 0.78, "domain": "tests", "summary": "Integration tests for auth flow"}
  ```
- **Without `--agent-mode`:** Outputs human-readable plain text (scores + summaries).
- **Agent Workflow:** The agent runs the search, sees the top 3 files, and then uses its native `cat` or `read_file` tool to examine only the files it deems necessary.

### Solution 2: Agent-Friendly Output Formats (JSON / Markdown)
For when agents *do* need full context bundles, they need formats they natively understand.

- **Action:** Add `--format json` and `--format md` to the `pack` and `query` commands.
- **JSON Output:** Instead of zipping files, output a JSON array of matched files, their relevance scores, and their contents. This allows agents to parse the output programmatically using `jq` or Python scripts.
- **Markdown Output:** Generate a clean Markdown file with collapsible sections (or just clear headers) that an agent can read using standard file-reading tools.

### Solution 3: Native MCP (Model Context Protocol) Server
This is the ultimate solution. Instead of forcing agents to use the shell, `ws-ctx-engine` should act as an MCP server.

- **Action:** Create a new entry point: `ws-ctx-engine mcp`.
- **Behavior:** Exposes `ws-ctx-engine`'s existing semantic search and graph capabilities as formal tools to any MCP-compatible client (Claude Desktop, Cursor, Windsurf).
- **Proposed MCP Tools:**

  ```json
  // Tool: search_codebase
  {
    "name": "search_codebase",
    "description": "Search the indexed codebase using semantic vector similarity",
    "inputSchema": {
      "type": "object",
      "properties": {
        "query": { "type": "string", "description": "Natural language query" },
        "limit": { "type": "integer", "default": 10, "description": "Max results to return" }
      },
      "required": ["query"]
    }
  }
  // Response:
  {
    "results": [
      { "path": "src/auth/login.py", "score": 0.92, "domain": "authentication" }
    ],
    "index_built_at": "2026-03-25T10:30:00Z",
    "files_indexed": 147,
    "dirty": false  // true if uncommitted changes since last index
  }
  ```

  ```json
  // Tool: get_file_context
  {
    "name": "get_file_context",
    "description": "Get file content with dependency graph context",
    "inputSchema": {
      "type": "object",
      "properties": {
        "path": { "type": "string", "description": "Absolute or relative file path" },
        "include_dependencies": { "type": "boolean", "default": false }
      },
      "required": ["path"]
    }
  }
  // Response:
  {
    "content": "DELIMITER:file_content_start:src/auth/login.py:DELIMITER\n...file content...\nDELIMITER:file_content_end:DELIMITER",
    "dependencies": ["src/models/user.py", "src/utils/jwt.py"],
    "dependents": ["src/middleware/auth.py"],
    "sanitized": true  // confirms content wrapped in delimiters
  }
  ```

  ```json
  // Tool: get_domain_map
  {
    "name": "get_domain_map",
    "description": "Get high-level architecture clusters of the repository",
    "inputSchema": { "type": "object", "properties": {} }
  }
  // Response:
  {
    "domains": [
      { "name": "authentication", "files": 12, "keywords": ["jwt", "oauth", "login"] },
      { "name": "database", "files": 8, "keywords": ["orm", "query", "migration"] }
    ],
    "graph_stats": { "nodes": 147, "edges": 29119 }
  }
  ```

  ```json
  // Tool: get_index_status
  {
    "name": "get_index_status",
    "description": "Check if the index is current or stale",
    "inputSchema": { "type": "object", "properties": {} }
  }
  // Response:
  {
    "index_built_at": "2026-03-25T10:30:00Z",
    "files_indexed": 147,
    "dirty": true,  // uncommitted changes detected
    "recommendation": "Rebuild index with: ws-ctx-engine index ."
  }
  ```

- **Security & Scope Isolation:**

  | Threat | Mitigation |
  |--------|------------|
  | Path Traversal | Reject paths outside initialized workspace; resolve symlinks |
  | Secret / Credential Leakage | Scan files for hardcoded API keys, tokens, passwords before returning; use Secretlint integration |
  | RADE (Prompt Injection via Content) | Wrap all file content in `DELIMITER:file_content_start:FILENAME:DELIMITER` / `DELIMITER:file_content_end:DELIMITER` to ensure agent treats it as data, not instructions |
  | Scope Isolation | MCP server bound to specific `.ws-ctx-engine` directory; no cross-repository queries |
  | Rate Limiting | Implement request throttling (e.g., max 60 searches/minute per client) to prevent CPU abuse |

- **Content Sanitization (RADE Mitigation):** All content returned by `get_file_context` **must** be wrapped in clear delimiters:
  ```
  DELIMITER:file_content_start:src/auth/login.py:DELIMITER
  [actual file content here]
  DELIMITER:file_content_end:DELIMITER
  ```
  This ensures the agent's parser can distinguish between *data* and *instructions*, preventing malicious instructions embedded in source files from being executed.

- **Secret Scanning:** Before returning file content via `get_file_context` or `search`, run a lightweight secret scan (e.g., using `gitsecret`, `trufflehog`, or `secretlint`) to detect:
  - Hardcoded API keys (`sk-`, `api_key`, `SECRET`)
  - AWS credentials
  - Private keys (`-----BEGIN RSA PRIVATE KEY-----`)
  - Database connection strings with passwords

  Files flagged as containing secrets should be excluded from results, with a `secrets_detected: ["aws_key", "private_key"]` field in the response.

## 4. Proposed Roadmap

**Phase 1: Quick Wins (CLI & Agent Prompts)**
- Implement `ws-ctx-engine search --agent-mode` (outputs NDJSON for machine parsing).
- Implement an `--agent-mode` flag for all commands that suppresses progress bars, rich formatting, and emojis, outputting pure parseable text.
- Update `wsctx-init` templates (`SKILL.md`, `.cursorrules`, etc.) to teach agents to use the new `search` command instead of full `pack` dumps.

**Phase 2: Agent-Native Formats**
- Implement `--format json` and `--format md` for the `pack` command.
- Add `--secrets-scan` flag to detect and exclude sensitive files from output.

**Phase 3: The MCP Server**
- Build `ws_ctx_engine/mcp_server.py` with:
  - All four tools: `search_codebase`, `get_file_context`, `get_domain_map`, `get_index_status`
  - Full output schemas as defined above
  - Content sanitization (delimiter wrapping)
  - Secretlint integration
  - Path traversal protection
  - Rate limiting (60 req/min per client)
- Document how to attach the `ws-ctx-engine` MCP server to Claude Desktop and Cursor.

## 5. Summary: Open Questions for Stakeholders

1. Should `get_file_context` return raw content or a structured object with metadata (line counts, language, AST summary)?
2. Should secret scanning be opt-in (`--secrets-scan`) or always-on?
3. Should the MCP server support authentication (e.g., API key for remote usage), or is local-only acceptable for v1?
4. What is the acceptable latency for `search_codebase`? Should we cache embeddings for frequently-used queries?