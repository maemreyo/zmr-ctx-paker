# Server Commands

Server commands enable running ws-ctx-engine as a service for AI agent integration.

## Available Commands

| Command | Description | Use Case |
|---------|-------------|----------|
| [`mcp`](mcp.md) | Run MCP server | AI agent integration via Model Context Protocol |

## Overview

The server commands transform ws-ctx-engine from a CLI tool into a long-running service that AI agents can communicate with using standard protocols.

## Use Cases

### AI Agent Integration
- Claude Desktop integration
- Cursor IDE integration  
- Windsurf integration
- Custom agent implementations

### Automation Scenarios
- CI/CD automation servers
- Development tooling backends
- Team-wide code search services

## Related Documentation

- [`mcp`](mcp.md) - MCP server command details
- [MCP Integration Guide](../../integrations/mcp-server.md) - Setup instructions
- [Agent Workflows](../../integrations/agent-workflows.md) - Agent patterns
