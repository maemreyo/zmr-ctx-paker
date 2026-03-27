# Agent Integration Workflow

Integrate ws-ctx-engine with AI agents for enhanced development capabilities.

## Overview

ws-ctx-engine provides two primary integration methods for AI agents:

1. **MCP Server Mode**: Long-running server for IDE/agent integration
2. **Agent Mode CLI**: Direct command-line integration with session tracking

## MCP Server Integration

### Setup

#### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ws-ctx-engine": {
      "command": "ws-ctx-engine",
      "args": ["mcp", "-w", "/absolute/path/to/your/project"],
      "env": {}
    }
  }
}
```

**Restart Claude Desktop** - ws-ctx-engine tools will appear automatically.

#### Cursor IDE

Add to Cursor settings (`settings.json`):

```json
{
  "mcp": {
    "servers": {
      "ws-ctx-engine": {
        "command": "ws-ctx-engine",
        "args": ["mcp", "-w", "${workspaceFolder}"]
      }
    }
  }
}
```

#### Windsurf

Windsurf auto-detects ws-ctx-engine when installed in the project directory.

### Available MCP Tools

Once connected, agents can use:

**Search & Discovery:**
- `search_codebase` - Semantic code search
- `get_file_context` - Retrieve file with dependencies
- `get_symbol_info` - Symbol definitions and references

**Context Generation:**
- `pack_context` - Generate LLM-ready packages
- `get_domain_map` - Domain keyword mappings

**Graph Operations:**
- `trace_call_chain` - Trace execution paths
- `get_index_status` - Check index health

### Example Agent Conversations

#### Code Exploration

**User:** "Find the authentication middleware"

**Agent uses:** `search_codebase(query="authentication middleware")`

**Result:** Returns ranked file paths with scores

#### Context Package

**User:** "Show me how payment processing works"

**Agent uses:** `pack_context(query="payment processing workflow", format="xml")`

**Result:** Complete context package with relevant files

#### Deep Dive

**User:** "Trace how a request goes from route to database"

**Agent uses:** `trace_call_chain(from_fn="handle_request", to_fn="save_to_db")`

**Result:** Execution path through the codebase

## CLI Agent Mode

### Basic Usage

```bash
# Enable agent mode output
ws-ctx-engine query "implement feature X" --agent-mode

# With session tracking
ws-ctx-engine query "part 1" --session-id agent-123 --agent-mode
```

### Multi-Turn Workflows

#### Session-Based Deduplication

```bash
# Turn 1: Initial exploration
ws-ctx-engine query "explore auth system" \
  --session-id auth-review \
  --agent-mode

# Turn 2: Specific area (excludes turn 1 content)
ws-ctx-engine query "auth middleware details" \
  --session-id auth-review \
  --agent-mode

# Turn 3: Testing approach (excludes turns 1 & 2)
ws-ctx-engine query "how to test auth" \
  --session-id auth-review \
  --agent-mode

# Cleanup
ws-ctx-engine session clear --session-id auth-review
```

### Agent Mode Output Format

```json
{
  "type": "status",
  "command": "query",
  "status": "success",
  "output_path": "./output/repomix-output.xml",
  "total_tokens": 45678,
  "generated_at": "2024-01-15T10:30:00Z"
}
```

## Advanced Patterns

### Pattern 1: Automated Code Review Agent

```python
# Pseudo-code for custom agent
async def review_pr(agent, pr_number):
    # Get changed files
    changed = await get_changed_files(pr_number)
    
    # Ask agent to review
    context = await agent.query(
        "review these changes for issues",
        changed_files=changed,
        session_id=f"pr-{pr_number}-review"
    )
    
    # Post review comments
    await post_review(pr_number, context)
```

### Pattern 2: Feature Implementation Assistant

```python
async def implement_feature(agent, feature_desc):
    # Explore existing patterns
    existing = await agent.search("similar features")
    
    # Get implementation context
    context = await agent.pack(
        f"implement {feature_desc}",
        mode="edit",
        budget=75000
    )
    
    # Generate implementation plan
    plan = await agent.generate_plan(context)
    
    return plan
```

### Pattern 3: Bug Investigation Workflow

```python
async def investigate_bug(agent, bug_description):
    session = f"bug-{uuid.uuid4()}"
    
    # Find related code
    locations = await agent.search(bug_description, session_id=session)
    
    # Get detailed context
    context = await agent.pack(
        "investigate this bug",
        changed_files=locations,
        session_id=session
    )
    
    # Analyze root cause
    analysis = await agent.analyze(context)
    
    # Suggest fixes
    fixes = await agent.suggest_fixes(analysis)
    
    # Cleanup
    await agent.clear_session(session)
    
    return fixes
```

## Rate Limiting

### Configure Limits

```bash
# Set rate limits for MCP server
ws-ctx-engine mcp -w . \
  --rate-limit search_codebase=60 \
  --rate-limit pack_context=30 \
  --rate-limit get_symbol_info=200
```

### Default Limits

| Tool | Default Limit |
|------|---------------|
| `search_codebase` | 60/min |
| `pack_context` | 30/min |
| `get_file_context` | 120/min |
| `get_symbol_info` | 200/min |
| `trace_call_chain` | 100/min |

## Best Practices

### Session Management

**Do's ✅:**
- Use descriptive session IDs
- Clear sessions after completion
- Track session state in long conversations

**Don'ts ❌:**
- Reuse session IDs across unrelated tasks
- Leave sessions running indefinitely
- Forget to cleanup failed sessions

### Token Budget Strategy

```bash
# Quick lookup (10K tokens)
ws-ctx-engine query "quick check" --budget 10000

# Standard context (30K tokens)
ws-ctx-engine query "feature implementation" --budget 30000

# Comprehensive analysis (75K+ tokens)
ws-ctx-engine query "system architecture" --budget 75000
```

### Compression Guidelines

```bash
# Enable for large contexts
ws-ctx-engine pack . -q "full system" --compress

# Disable for small contexts
ws-ctx-engine query "small feature" --no-compress
```

## Troubleshooting

### "MCP server not connecting"

**Solutions:**
1. Verify workspace path is absolute
2. Check ws-ctx-engine is installed
3. Ensure indexes are built
4. Restart IDE/agent

### "Session deduplication not working"

**Check:**
```bash
# Verify session exists
ls -la .ws-ctx-engine/sessions/

# Check session ID matches
ws-ctx-engine query "test" --session-id my-session
```

### "Rate limit exceeded"

**Solutions:**
- Increase limits: `--rate-limit tool=120`
- Reduce request frequency
- Cache results locally

## Security Considerations

### Secret Scanning

```bash
# Always enable in shared environments
ws-ctx-engine query "code" --secrets-scan
```

### Access Control

**MCP Server:**
- Runs locally via stdio
- No network exposure
- File access limited to workspace

**CLI Mode:**
- User-controlled execution
- Explicit permissions
- Audit trail via shell history

## Related Workflows

- [Development Workflow](development.md) - Daily development patterns
- [CI/CD Integration](ci-cd.md) - Automation workflows
- [Initial Setup](initial-setup.md) - Getting started guide
