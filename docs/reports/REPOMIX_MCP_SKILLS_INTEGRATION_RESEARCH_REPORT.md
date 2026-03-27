# Repomix MCP & Skills Integration Research Report

**Date:** March 27, 2026  
**Author:** ws-ctx-engine Research Team  
**Scope:** MCP Server Architecture & Agent Skills System

---

## Executive Summary

Repomix v0.2.36+ đã tích hợp **hoàn chỉnh** cả MCP server và Agent Skills generation. Đây là đối thủ cạnh tranh trực tiếp cần được nghiên cứu kỹ.

---

## 1. MCP Server Implementation

### Architecture Overview

```
┌─────────────────────────────────────┐
│         Repomix MCP Server          │
├─────────────────────────────────────┤
│  Protocol Adapter Layer             │
│  - MCP standard request/response    │
│  - JSON-RPC 2.0 handling            │
├─────────────────────────────────────┤
│  Code Processing Engine             │
│  - File packing & compression       │
│  - Tree-sitter AST analysis         │
│  - Token optimization (~70% reduction)│
├─────────────────────────────────────┤
│  Git Integration Module             │
│  - Remote repo cloning              │
│  - Incremental updates              │
│  - GitHub/GitLab support            │
└─────────────────────────────────────┘
```

### Key Features

| Feature                 | Implementation                     | Notes                                 |
| ----------------------- | ---------------------------------- | ------------------------------------- |
| **Local Code Packing**  | Auto-scan & pack local directories | Similar to `wsctx pack`               |
| **Remote Repo Support** | Direct GitHub clone & pack         | Via `--remote` flag                   |
| **Compression**         | Tree-sitter based ~70% reduction   | Competes with our planned compression |
| **Security Scanning**   | Secretlint integration             | Detects sensitive files               |
| **MCP Tools**           | Limited to file operations         | No semantic search                    |

### Usage Example

```bash
# Run as MCP server
npx repomix --mcp

# Configure in Cline (VS Code)
{
  "mcpServers": {
    "repomix": {
      "command": "npx",
      "args": ["repomix", "--mcp"]
    }
  }
}
```

---

## 2. Agent Skills Generation System

### What is Agent Skills?

**Agent Skills** là định dạng output đặc biệt của Repomix, tạo ra structured directory làm reference cho AI assistants (Claude Code, Cursor, etc.).

### Generated Structure

```
.claude/skills/<skill-name>/
├── SKILL.md                    # Main metadata & documentation
└── references/
    ├── summary.md              # Purpose, format, statistics
    ├── project-structure.md    # Directory tree with line counts
    ├── files.md                # All file contents (grep-friendly)
    └── tech-stack.md           # Languages, frameworks, dependencies
```

### File Descriptions

#### SKILL.md

- Skills name, description, project info
- File count, line count, token count
- Usage guidelines
- Common use cases

#### references/summary.md

- Purpose explanation
- File structure breakdown
- Usage guidelines
- Statistics by language/file type

#### references/project-structure.md

```
src/
  index.ts (42 lines)
  utils/
    helpers.ts (128 lines)
    math.ts (87 lines)
```

#### references/files.md

````markdown
## File: src/index.ts

```typescript
import { sum } from "./utils/helpers";

export function main() {
  console.log(sum(1, 2));
}
```
````

````

#### references/tech-stack.md
Auto-detected from:
- package.json, requirements.txt, Cargo.toml, go.mod
- .nvmrc, pyproject.toml
- Dependencies (direct & dev)

### Usage Examples

```bash
# Generate from local directory
repomix --skill-generate

# Generate with custom name
repomix --skill-generate my-project-reference

# Generate from remote repo
repomix --remote https://github.com/user/repo --skill-generate

# Non-interactive (CI/CD)
repomix --skill-generate --skill-output ./output --force
````

### Integration Locations

1. **Personal Skills**: `~/.claude/skills/` - Available across all projects
2. **Project Skills**: `.claude/skills/` - Shared via git

---

## 3. Competitive Analysis

### Feature Comparison Matrix

| Capability            | Repomix  | ws-ctx-engine    | aider   |
| --------------------- | -------- | ---------------- | ------- |
| **MCP Server**        | ✅       | ❌ (planned)     | ❌      |
| **Agent Skills**      | ✅       | ❌               | ❌      |
| **Semantic Search**   | ❌       | ✅ (LEANN/FAISS) | ❌      |
| **Dependency Graph**  | ❌       | ✅ (PageRank)    | partial |
| **Domain Mapping**    | ❌       | ✅               | ❌      |
| **Token Compression** | ✅ (70%) | ❌ (planned)     | ❌      |
| **Secret Scanning**   | ✅       | ❌ (planned)     | ❌      |

### Strategic Positioning

**Repomix Strengths:**

- ✅ Mature MCP implementation (production-ready)
- ✅ Agent Skills format for Claude
- ✅ Tree-sitter compression
- ✅ Simple, works out of the box

**Repomix Weaknesses:**

- ❌ No semantic search (only file listing)
- ❌ No dependency analysis
- ❌ No intelligent ranking
- ❌ Concatenation-based approach

**ws-ctx-engine Differentiation:**

- ✅ **Intelligent Discovery**: Semantic vector search + PageRank-weighted results
- ✅ **Dependency Context**: Agents get ranked results with dependency graph
- ✅ **Domain Intelligence**: Keyword-based architectural mapping
- ✅ **Retrieval Moat**: No competitor has this combination

---

## 4. Technical Insights

### MCP Architecture Patterns

**Repomix Approach:**

```typescript
// Simplified flow
1. CLI entry point → --mcp flag
2. Initialize MCP server (stdio transport)
3. Register tools:
   - pack_local(path, options)
   - pack_remote(repo_url, options)
4. Handle JSON-RPC requests
5. Return packed output
```

**Key Design Decisions:**

- Stdio transport only (no HTTP/SSE)
- Stateless design (each request independent)
- File-based output (not streaming)
- Rate limiting via external config

### Skills Generation Strategy

**Why Skills Work:**

1. **Structured Format**: Multiple focused files vs single monolithic file
2. **Grep-Friendly**: Easy to search across references
3. **AI-Optimized**: Syntax highlighting headers, clear delimiters
4. **Metadata-Rich**: Tech stack, statistics, structure info

**Format Choices:**

- Markdown over XML (better for Claude)
- Kebab-case naming convention
- Max 64 char skill names
- Path traversal protection

---

## 5. Lessons Learned for ws-ctx-engine

### What to Adopt

1. **Skills-like Output Format**
   - Consider adding `--skill-generate` equivalent
   - Create structured `.qoder/skills/` directory
   - Focus on AI comprehension optimization

2. **MCP Tool Design**
   - Keep tools simple and focused
   - Use stdio transport initially
   - Add remote repo support via `--remote`

3. **Non-Interactive Mode**
   - Essential for CI/CD integration
   - `--skill-output` + `--force` pattern

### What to Improve Upon

1. **Add Semantic Layer**
   - Repomix only does file listing
   - We should offer conceptual search

2. **Dependency Intelligence**
   - PageRank-weighted results
   - Call hierarchy visualization

3. **Domain Mapping**
   - Architectural domain clustering
   - Keyword-based navigation

### What to Avoid

1. **Don't replicate their weaknesses**
   - No mindless concatenation
   - Maintain retrieval intelligence

2. **Keep differentiation clear**
   - Market as "intelligent MCP" not just "another MCP"
   - Emphasize semantic search + dependency graph

---

## 6. Recommendations

### Immediate Actions (Phase 3)

1. **Expose Retrieval Engine via MCP**

   ```python
   tools = [
       "search_codebase(query, limit, domain_filter)",
       "get_file_context(path, include_deps)",
       "get_domain_map()",
       "get_index_status()"
   ]
   ```

2. **Add Qoder Skills Generation**

   ```bash
   wsctx --skill-generate [--output ~/.qoder/skills/]
   ```

3. **Implement Remote Repo Support**
   ```bash
   wsctx mcp --workspace . --remote github:user/repo
   ```

### Medium-term (Q2 2026)

1. **Tree-sitter Compression**
   - Partner with Chonkie or Code-Chunk libraries
   - Target 60-70% token reduction

2. **Enhanced Security**
   - Integrate Secretlint or similar
   - Add path traversal guards

3. **Multi-IDE Support**
   - Qoder (primary)
   - Windsurf (existing)
   - Cursor (growing adoption)
   - VS Code (via MCP marketplace)

### Long-term Vision

**Position ws-ctx-engine as:**

> "The intelligent retrieval layer for AI-powered development"

Not: "Another code packing tool"

---

## 7. Conclusion

Repomix đã validation thị trường cho:

- ✅ MCP servers cho codebase interaction
- ✅ Agent Skills format cho AI assistants
- ✅ Automated code packing & compression

**Tuy nhiên**, họ chỉ làm được surface-level features (file listing, concatenation).

**Cơ hội của ws-ctx-engine:**

- Deep semantic search (vector + graph)
- Intelligent ranking (PageRank + RRF)
- Domain intelligence (keyword mapping)
- Dependency-aware context packaging

**Chiến lược:** Không chạy đua tính năng (feature checkbox war). Tập trung vào retrieval engine superiority - đây là moat thực sự.

---

## References

- [Repomix Official Docs](https://repomix.com/guide/agent-skills-generation)
- [Repomix v0.2.36 Release](https://blog.gitcode.com/ec0388e4258baba7c753e7b6b8e0f124.html)
- [GitHub: yamadashy/repomix](https://github.com/yamadashy/repomix)
- [Internal: agent-plan-v4.md](docs/development/plans/agent-plan-v4.md)
- [Internal: agent-integration-proposal.md](docs/development/plans/agent-integration-proposal.md)

---

**Report Length:** ~1,200 words  
**Research Time:** 30 minutes  
**Confidence Level:** High (validated against multiple sources)
