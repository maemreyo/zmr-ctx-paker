# Enhancing ctx-packer for AI Agents: A Strategic Proposal

## 1. The Current Landscape & Problems

**ctx-packer** was originally designed as a *Human-to-AI* bridge. A human developer runs the CLI, generates a ZIP or XML file, and uploads/pastes it into an LLM context window (like Claude.ai, Cursor, or Windsurf). 

However, with the rise of autonomous coding agents (Claude Code, TRAE, AutoGPT, SWE-agent), the paradigm is shifting toward *AI-to-Codebase* interactions.

### The Problems
1. **Opaque Output Formats:** Currently, `ctx-packer` exports context as either `.zip` (files + metadata) or `.xml`. 
   - A CLI-based AI agent cannot easily "read" a `.zip` file without unzipping it first, which creates friction.
   - An `.xml` dump of 100k tokens printed to standard output (`stdout`) will overwhelm the agent's immediate context window, causing truncation or context-loss errors.
2. **Lack of Incremental Discovery:** Agents don't need the entire context dumped at once. They need to *search*, look at a list of relevant files, read summaries, and then decide which specific files to deep-dive into. `ctx-packer` currently lacks an interactive "search-only" or "summary" mode.
3. **No Native MCP (Model Context Protocol) Support:** The industry standard for exposing tools to AI agents is the Model Context Protocol. `ctx-packer` is purely a CLI tool, meaning agents have to use shell commands to interact with it, parsing unstructured text output.

## 2. Motivations

Why should we optimize `ctx-packer` for AI agents?

- **Empower Autonomous Agents:** Codebases are too large for an agent to simply `grep` or `find`. By exposing `ctx-packer`'s semantic search and PageRank graph to agents, we give them a "smart map" of the codebase.
- **Reduce Token Waste:** Instead of an agent reading 50 irrelevant files to find a bug, it can query `ctx-packer` to get the top 5 most semantically relevant files, saving tokens and time.
- **Stay Ahead of the Curve:** Tools like `repomix` and `aider` are building deep integrations with AI agents. `ctx-packer` has superior retrieval (vector + graph + domain), but needs the right interface to shine in an agentic workflow.

## 3. Potential Solutions & Implementation Plan

To make `ctx-packer` the ultimate tool for AI agents, we need to implement features across three tiers: CLI Enhancements, Output Formats, and Protocol Integrations.

### Solution 1: Agent-Friendly Output Formats (JSON / Markdown)
Agents are best at parsing structured data (JSON) or highly readable text (Markdown). 
- **Action:** Add `--format json` and `--format md`.
- **JSON Output:** Instead of zipping files, output a JSON array of matched files, their relevance scores, and their contents. This allows agents to parse the output programmatically using `jq` or Python scripts.
- **Markdown Output:** Generate a clean Markdown file with collapsible sections (or just clear headers) that an agent can read using standard file-reading tools.

### Solution 2: "Search-Only" & "Dry-Run" CLI Commands
Agents need to know *what* exists before they decide to read it.
- **Action:** Add a `ctx-packer search "<query>"` command (distinct from `pack`).
- **Behavior:** This command would return *only* a list of file paths and their relevance scores, without the actual file contents.
- **Example Output:**
  ```text
  1. src/auth/login.py (Score: 0.92) - Domain: authentication
  2. src/models/user.py (Score: 0.85) - Domain: database
  3. tests/test_auth.py (Score: 0.78)
  ```
- **Agent Workflow:** The agent runs the search, sees the top 3 files, and then uses its native `cat` or `read_file` tool to examine only the files it deems necessary.

### Solution 3: Native MCP (Model Context Protocol) Server
This is the ultimate solution. Instead of forcing agents to use the shell, `ctx-packer` should act as an MCP server.
- **Action:** Create a new entry point: `ctx-packer mcp`.
- **Behavior:** Exposes `ctx-packer`'s capabilities as formal tools to any MCP-compatible client (Claude Desktop, Cursor, Windsurf).
- **Proposed MCP Tools:**
  1. `search_codebase(query: str, limit: int)`: Returns top N relevant file paths.
  2. `get_file_context(path: str)`: Returns the file content along with its graph dependencies (who calls it, what it calls).
  3. `get_domain_map()`: Returns the high-level architecture/domain clusters of the repository.

### Solution 4: Agent-Specific Prompts & Instructions
When `ctx-packer-init` is run, it currently creates instructions. We should enhance these instructions to teach the agent *how* to use the new features.
- **Action:** Update the `.claude/skills/ctx-packer/SKILL.md` and `.cursorrules` to instruct the agent: 
  > *"Do not use `ctx-packer pack` directly. Instead, use `ctx-packer search "<query>"` to find relevant files, then read those files individually."*

## 4. Proposed Roadmap

**Phase 1: Quick Wins (CLI & Formats)**
- Implement `ctx-packer search` (returns list of files + scores only).
- Implement `--format json` for the `pack` command.
- Update `ctx-packer-init` templates to teach agents to use the `search` command.

**Phase 2: Advanced Agent CLI**
- Implement an `--agent-mode` flag that suppresses all progress bars, rich formatting, and emojis, outputting pure parseable text.

**Phase 3: The MCP Server**
- Build `context_packer/mcp_server.py`.
- Define the standard tools (`search_codebase`, `get_dependencies`).
- Document how to attach the `ctx-packer` MCP server to Claude Desktop and Cursor.