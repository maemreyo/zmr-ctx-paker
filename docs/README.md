# Documentation

## Structure

```
docs/
├── guides/          User-facing how-to guides
├── reference/       Technical reference per component
├── integrations/    IDE and agent integration guides
├── development/     Internal: plans, research, audits
└── roadmap/         Release roadmap
```

---

## Guides

User-facing documentation for operating ws-ctx-engine.

| File | Description |
|------|-------------|
| [guides/compression.md](guides/compression.md) | Smart compression and context shuffling |
| [guides/logging.md](guides/logging.md) | Structured logging system |
| [guides/output-formats.md](guides/output-formats.md) | XML, JSON, YAML, MD output schemas |
| [guides/performance.md](guides/performance.md) | Performance tuning and Rust extension |

---

## Reference

Technical reference for each component in the pipeline.

| File | Description |
|------|-------------|
| [reference/architecture.md](reference/architecture.md) | System architecture overview |
| [reference/prd.md](reference/prd.md) | Product requirements document |
| [reference/design-ideas.md](reference/design-ideas.md) | Design philosophy and ideas |
| [reference/chunker.md](reference/chunker.md) | AST-based code chunker |
| [reference/vector-index.md](reference/vector-index.md) | Embedding + vector index (LEANN/FAISS) |
| [reference/graph.md](reference/graph.md) | Dependency graph and PageRank |
| [reference/retrieval.md](reference/retrieval.md) | Hybrid semantic + graph retrieval |
| [reference/ranking.md](reference/ranking.md) | Ranking and score merging |
| [reference/budget.md](reference/budget.md) | Token budget manager |
| [reference/packer.md](reference/packer.md) | XML and ZIP output packer |
| [reference/output-formatters.md](reference/output-formatters.md) | Output formatter modules |
| [reference/secret-scanner.md](reference/secret-scanner.md) | Secret detection before packing |
| [reference/workflow.md](reference/workflow.md) | Pipeline orchestration (indexer + query) |
| [reference/cli.md](reference/cli.md) | CLI commands reference |
| [reference/config.md](reference/config.md) | YAML configuration reference |
| [reference/supporting-modules.md](reference/supporting-modules.md) | Backend selector, logging, utilities |

---

## Integrations

Guides for connecting ws-ctx-engine to IDEs and AI agents.

| File | Description |
|------|-------------|
| [integrations/mcp-server.md](integrations/mcp-server.md) | MCP server reference |
| [integrations/agent-workflows.md](integrations/agent-workflows.md) | AI agent workflow integration |
| [integrations/claude-desktop.md](integrations/claude-desktop.md) | Claude Desktop setup |
| [integrations/cursor.md](integrations/cursor.md) | Cursor IDE setup |
| [integrations/windsurf.md](integrations/windsurf.md) | Windsurf IDE setup |

---

## Development

Internal documents: planning, research, and audit reports.

### Plans

| File | Description |
|------|-------------|
| [development/plans/agent-integration-proposal.md](development/plans/agent-integration-proposal.md) | Strategic proposal for agent-first architecture |
| [development/plans/agent-plan-v4.md](development/plans/agent-plan-v4.md) | Comprehensive agent implementation plan (v4) |
| [development/plans/cli-init-plan-v1.md](development/plans/cli-init-plan-v1.md) | `wsctx init` enhanced architecture plan (v1) |
| [development/plans/cli-init-plan-v2.md](development/plans/cli-init-plan-v2.md) | `wsctx init` enhancement plan (v2) |

### Research

| File | Description |
|------|-------------|
| [development/research/leann.md](development/research/leann.md) | LEANN vector index implementation research |

### Audits

| File | Description |
|------|-------------|
| [development/audits/agent-plan-v4-audit.md](development/audits/agent-plan-v4-audit.md) | Agent plan v4 implementation audit |
| [development/audits/chunker-issues.md](development/audits/chunker-issues.md) | Chunker issues and improvement report |
| [development/audits/mcp-security.md](development/audits/mcp-security.md) | MCP server security audit |
| [development/audits/repo-review.md](development/audits/repo-review.md) | Full repository review |
| [development/audits/review-prompts.md](development/audits/review-prompts.md) | Test query prompts for self-evaluation |

---

## Roadmap

| File | Description |
|------|-------------|
| [roadmap/ROADMAP.md](roadmap/ROADMAP.md) | Release roadmap and milestone tracker |
