# CLI Module

> **Module Path**: `src/ws_ctx_engine/cli/`

The CLI module provides the user-facing command-line interface for ws-ctx-engine, built with Typer and Rich for an excellent developer experience.

## Purpose

The CLI module serves as the primary user interface for ws-ctx-engine:

1. **Repository Indexing**: Build and maintain semantic indexes
2. **Codebase Search**: Query indexed repositories
3. **Context Packing**: Generate LLM-ready output
4. **Index Management**: Status, cleanup, and maintenance

## Entry Points

The package provides multiple entry points for convenience:

| Entry Point          | Description           |
| -------------------- | --------------------- |
| `ws-ctx-engine`      | Primary CLI command   |
| `wsctx`              | Short alias           |
| `ws-ctx-engine-init` | Config initialization |
| `wsctx-init`         | Short alias for init  |

## Documentation Structure

This documentation is organized into the following sections:

### 📐 Architecture & Design
- **[Architecture](architecture.md)** - System architecture and component relationships
- **[Global Options](global-options.md)** - Global CLI options and output modes

### 🔧 Command Reference
- **[Commands Overview](commands/README.md)** - Complete command reference
  - Core Commands: `doctor`, `index`, `search`, `query`, `pack`, `status`
  - Maintenance: `vacuum`, `reindex-domain`
  - Configuration: `init-config`
  - Server: `mcp`
  - Session: `session clear`

### 🔄 Workflows
- **[Workflows Overview](workflows/README.md)** - Common usage patterns
  - [Initial Setup](workflows/initial-setup.md) - Getting started
  - [Development](workflows/development.md) - Daily development workflow
  - [CI/CD Integration](workflows/ci-cd.md) - Automation workflows
  - [Agent Integration](workflows/agent-integration.md) - AI agent workflows

### ⚙️ Implementation Details
- **[Implementation Overview](implementation/README.md)** - Technical implementation
  - [Framework](implementation/framework.md) - Typer and Rich framework
  - [Dependencies](implementation/dependencies.md) - Module dependencies
  - [Configuration](implementation/configuration.md) - Configuration loading
  - [Error Handling](implementation/error-handling.md) - Error patterns

### 🔗 Related Modules
- **[Related Modules](related-modules.md)** - Cross-references to other documentation

## Quick Start

```bash
# 1. Initialize configuration
ws-ctx-engine init-config /path/to/repo

# 2. Check dependencies
ws-ctx-engine doctor

# 3. Build initial index
ws-ctx-engine index /path/to/repo

# 4. Search and pack
ws-ctx-engine query "your query" --format xml
```

## Navigation

For a complete list of commands, see the [Commands Overview](commands/README.md).

For common usage patterns, see [Workflows](workflows/README.md).

For technical implementation details, see [Implementation](implementation/README.md).
