# Examples Directory

This directory contains example usage of ws-ctx-engine.

## 📁 Structure

```
examples/
├── README.md                # This file
├── .gitignore              # Git ignore rules
└── mcp/                    # MCP tool examples
    ├── README.md          # Detailed tool documentation
    ├── QUICKSTART.md      # Quick start guide
    ├── tool_demo.py       # Full MCP server demo
    ├── json_examples.py   # JSON-RPC format examples
    ├── practical_demo.py  # Real tool execution demo
    ├── debug_logger.py    # Debug logging tool
    └── error_handler.py   # Graceful error handling
```

## 🎯 Quick Start

### MCP Tool Examples (Recommended)

```bash
# 1. View tool documentation
cat examples/mcp/README.md

# 2. Run quick demo
uv run python examples/mcp/tool_demo.py

# 3. See JSON formats
uv run python examples/mcp/json_examples.py

# 4. Run practical demo with real results
uv run python examples/mcp/practical_demo.py

# 5. Debug tool calls with detailed logging
uv run python examples/mcp/debug_logger.py
```

## 📚 Example Descriptions

### MCP Examples (`mcp/`)

## 🔧 Usage Patterns

### Pattern 1: Learning the Tools

```bash
# Start with documentation
cat examples/mcp/README.md

# Run the full demo
uv run python examples/mcp/tool_demo.py
```

### Pattern 2: Understanding JSON Format

```bash
# See exact JSON structures
uv run python examples/mcp/json_examples.py
```

### Pattern 3: Testing Your Workspace

```bash
# Run practical demo on current directory
cd /path/to/your/project
uv run python ../ws-ctx-paker/examples/mcp/practical_demo.py
```

### Pattern 4: Debugging Issues

```bash
# Get detailed logs of each tool call
uv run python examples/mcp/debug_logger.py

# Check generated log file
cat mcp_tool_calls_*.log
```

### Pattern 5: Handling Errors

```bash
# Learn how to handle missing dependencies gracefully
uv run python examples/mcp/error_handler.py --demo
```

## 🚀 Common Workflows

### Workflow 1: First Time Setup

```bash
# 1. Install dependencies
uv add ws-ctx-engine[all]

# 2. Build index
uv run ws-ctx-engine index .

# 3. Run examples
uv run python examples/mcp/practical_demo.py
```

### Workflow 2: Troubleshooting

```bash
# 1. Check what's wrong
uv run python scripts/dependency_doctor.py

# 2. Debug tool calls
uv run python examples/mcp/debug_logger.py

# 3. Learn how to fix
cat docs/HOW_TO_FIX_MISSING_DEPS.md
```

### Workflow 3: Development

```bash
# 1. Understand JSON format
uv run python examples/mcp/json_examples.py

# 2. Modify for your use case
cp examples/mcp/tool_demo.py my_custom_script.py

# 3. Test your modifications
uv run python my_custom_script.py
```

## 📖 Related Documentation

- [MCP Server Guide](docs/integrations/mcp-server.md)
- [Missing Dependencies Fix](docs/HOW_TO_FIX_MISSING_DEPS.md)
- [Installation Guide](INSTALL.md)
- [Main README](README.md)

## 💡 Tips

1. **Start Simple**: Begin with `tool_demo.py` to understand the basics
2. **Use Debug Logger**: When something fails, run `debug_logger.py` to see details
3. **Check Logs**: Log files in `mcp_tool_calls_*.log` contain full I/O
4. **Handle Errors Gracefully**: Use patterns from `error_handler.py` in production

## ⚠️ Notes

- **Python Version**: Examples tested with Python 3.13.5
- **Dependencies**: Some examples require `ws-ctx-engine[all]` tier
- **Index Required**: Most examples need indexes built first: `ws-ctx-engine index .`

---

**Last Updated:** 2026-03-27  
**Maintainer:** ws-ctx-engine team
