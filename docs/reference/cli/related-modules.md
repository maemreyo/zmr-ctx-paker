# Related Modules

Cross-references to other ws-ctx-engine documentation and modules.

## Core Documentation

### Reference Documentation

| Module | Description |
|--------|-------------|
| **[Workflow](workflow.md)** | Core workflow implementation called by CLI commands |
| **[Configuration](config.md)** | Configuration management and schema |
| **[Retrieval](retrieval.md)** | Search and retrieval system |
| **[Vector Index](vector-index.md)** | Vector indexing backend (FAISS/LEANN) |
| **[Graph](graph.md)** | Graph index and PageRank implementation |
| **[Chunker](chunker.md)** | Code chunking and AST parsing |
| **[Ranking](ranking.md)** | Result ranking and scoring |
| **[Budget](budget.md)** | Token budget management |

### Integration Guides

| Guide | Description |
|-------|-------------|
| **[MCP Server](../integrations/mcp-server.md)** | Model Context Protocol setup |
| **[Claude Desktop](../integrations/claude-desktop.md)** | Claude Desktop integration |
| **[Cursor](../integrations/cursor.md)** | Cursor IDE integration |
| **[Windsurf](../integrations/windsurf.md)** | Windsurf integration |
| **[Agent Workflows](../integrations/agent-workflows.md)** | AI agent patterns |

### Output Formats

| Format | Description |
|--------|-------------|
| **[Output Formatters](output-formatters.md)** | All output format options |
| **[Compression Guide](../guides/compression.md)** | Smart compression strategies |
| **[Performance Guide](../guides/performance.md)** | Performance optimization |

## Module Dependencies

### CLI Depends On

```
CLI Module
    ↓
Workflow Module (index_repository, query_and_pack, search_codebase)
    ↓
Core Engine
    ├── Retrieval System
    ├── Vector Index (FAISS/LEANN)
    ├── Graph Engine (NetworkX/igraph)
    ├── Chunker (AST parsing)
    └── Packer (Output formatting)
```

### Other Modules Depend On CLI For

- **User Interface**: Primary way users interact with system
- **Automation**: CI/CD integration point
- **Agent Integration**: MCP server entry point
- **Configuration**: Config file generation and loading

## Cross-References by Feature

### Search & Retrieval

**CLI Commands:**
- [`search`](commands/search.md) - Semantic search
- [`query`](commands/query.md) - Query and pack

**Implementation:**
- [Retrieval System](retrieval.md) - Search logic
- [Ranking](ranking.md) - Result scoring

### Indexing

**CLI Commands:**
- [`index`](commands/index.md) - Build indexes
- [`status`](commands/status.md) - Check status
- [`vacuum`](commands/maintenance/vacuum.md) - Optimize

**Implementation:**
- [Vector Index](vector-index.md) - Embedding storage
- [Graph](graph.md) - Dependency graph
- [Workflow](workflow.md) - Indexing pipeline

### Configuration

**CLI Commands:**
- [`init-config`](commands/config/init-config.md) - Generate config
- All commands accept `--config` flag

**Implementation:**
- [Configuration](config.md) - Config schema and loading

### Agent Integration

**CLI Commands:**
- [`mcp`](commands/server/mcp.md) - MCP server
- `query --agent-mode` - Agent mode output

**Guides:**
- [MCP Server](../integrations/mcp-server.md) - Setup guide
- [Agent Workflows](../integrations/agent-workflows.md) - Usage patterns

### Output Management

**CLI Options:**
- `--format` - Output format selection
- `--budget` - Token budget control
- `--compress` - Compression enablement

**Guides:**
- [Output Formatters](output-formatters.md) - Format details
- [Compression](../guides/compression.md) - Size optimization
- [Token Budget](budget.md) - Budget strategies

## Security Features

### Secret Scanning

**CLI Command:**
- `query --secrets-scan`
- `pack --secrets-scan`

**Implementation:**
- [Secret Scanner](secret-scanner.md) - Detection and redaction

## Performance Features

### Optimization Commands

**CLI Commands:**
- [`vacuum`](commands/maintenance/vacuum.md) - Database optimization
- [`reindex-domain`](commands/maintenance/reindex-domain.md) - Fast domain rebuild

**Guides:**
- [Performance Guide](../guides/performance.md) - Optimization strategies
- [Backend Selection](backend-selection.md) - Backend performance

## Architecture Overview

```
┌─────────────────────────────────────┐
│         User / Agent                │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│      CLI Module (This Docs)         │
│  - Typer/Rich Interface             │
│  - Command Handlers                 │
│  - Error Handling                   │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│      Workflow Module                │
│  - index_repository()               │
│  - query_and_pack()                 │
│  - search_codebase()                │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│      Core Engine                    │
│  - Retrieval                        │
│  - Vector Index                     │
│  - Graph                            │
│  - Chunker                          │
│  - Packer                           │
└─────────────────────────────────────┘
```

## Navigation Tips

### Finding Information

**For command usage:**
→ Start with [Commands Overview](commands/README.md)

**For implementation details:**
→ See [Implementation](implementation/README.md)

**For workflows:**
→ Check [Workflows](workflows/README.md)

**For integration:**
→ Go to [Integrations](../../integrations/README.md)

### Common Paths Through Documentation

**New user learning CLI:**
1. [CLI README](README.md) - Overview
2. [Initial Setup](workflows/initial-setup.md) - Getting started
3. [Commands Overview](commands/README.md) - Learn commands
4. [Development Workflow](workflows/development.md) - Daily usage

**Setting up agent integration:**
1. [MCP Command](commands/server/mcp.md) - Server setup
2. [Agent Workflows](workflows/agent-integration.md) - Usage patterns
3. [Claude Desktop](../integrations/claude-desktop.md) - Specific integration

**Troubleshooting issues:**
1. [Error Handling](implementation/error-handling.md) - Error messages
2. [Commands](commands/README.md) - Verify usage
3. [Related Modules](related-modules.md) - Find implementation docs

## Related Documentation Sets

### Within This Project
- [Architecture Overview](architecture.md)
- [Getting Started](../../README.md#getting-started)
- [Examples](../../examples/README.md)

### External Resources
- [Typer Documentation](https://typer.tiangolo.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [MCP Specification](https://modelcontextprotocol.io/)
