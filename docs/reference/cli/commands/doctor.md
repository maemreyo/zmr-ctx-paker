# doctor Command

Check optional dependencies and recommend installation tier.

## Usage

```bash
ws-ctx-engine doctor
```

## Description

The `doctor` command validates your installation by checking for the presence of optional dependencies. It helps you understand which features are available and what additional packages you might want to install for full functionality.

## Output Example

```
Dependency Doctor
- faiss-cpu                 OK
- igraph                    OK
- leann                     MISSING
- networkx                  OK
- scikit-learn              OK
- sentence-transformers     OK
- tree-sitter               OK
- tree-sitter-javascript    OK
- tree-sitter-python        OK
- tree-sitter-rust          MISSING
- tree-sitter-typescript    OK

Some recommended dependencies are missing for full feature set.
Recommended install: pip install "ws-ctx-engine[all]"
Missing: leann, tree-sitter-rust
```

## When to Use

✅ **Run `doctor` when:**
- First installing ws-ctx-engine
- Troubleshooting missing functionality
- Verifying installation completeness
- Checking if optional features are available

❌ **Don't need to run:**
- Every time you use the CLI
- During normal development workflow

## Dependency Tiers

The tool checks for dependencies in different tiers:

### Core Dependencies (Required)
These are always installed with the base package.

### Recommended Dependencies
Enhance functionality but not strictly required:
- `faiss-cpu` - Vector search backend
- `igraph` - Fast graph operations
- `networkx` - Graph operations (fallback)
- `scikit-learn` - Machine learning utilities
- `sentence-transformers` - Embedding generation

### Optional Dependencies
Enable specific language support:
- `tree-sitter` - Base AST parsing
- `tree-sitter-python` - Python code parsing
- `tree-sitter-javascript` - JavaScript/TypeScript parsing
- `tree-sitter-typescript` - TypeScript-specific parsing
- `tree-sitter-rust` - Rust code parsing
- `leann` - Advanced vector index (optional, uses FAISS fallback)

## Installation Recommendations

Based on the output, you can install dependencies by tier:

```bash
# Install all recommended dependencies
pip install "ws-ctx-engine[all]"

# Or install specific missing ones
pip install leann tree-sitter-rust
```

## Related Commands

- [`init-config`](config/init-config.md) - Generate configuration after installation
- [`index`](index.md) - Build indexes once dependencies are verified

## Troubleshooting

**Q: Should I install all dependencies?**
A: For most users, yes. Install `ws-ctx-engine[all]` for complete functionality. Only skip if you have specific constraints.

**Q: Can I use ws-ctx-engine without some dependencies?**
A: Yes! The tool has fallback mechanisms. Missing `igraph`? It uses `networkx`. Missing `leann`? It uses `FAISS`.

**Q: Do I need all tree-sitter grammars?**
A: Only for languages you work with. If you don't write Rust, you don't need `tree-sitter-rust`.

## Related Documentation

- [Installation Guide](../../INSTALL.md) - Complete installation instructions
- [Configuration](../implementation/configuration.md) - Configuration after setup
- [Dependencies](../implementation/dependencies.md) - Dependency details
