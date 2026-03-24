# Contributing to Context Packer

Thank you for your interest in contributing to Context Packer! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/zmr-ctx-paker.git
   cd zmr-ctx-paker
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/maemreyo/zmr-ctx-paker.git
   ```

## Development Setup

### Prerequisites

- Python 3.9 or higher
- pip or poetry for package management
- Git for version control

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[dev,all]"
   ```

3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=context_packer --cov-report=html

# Run specific test types
pytest -m property  # Property-based tests
pytest -m integration  # Integration tests
pytest -m benchmark  # Performance benchmarks
```

### Code Quality Checks

```bash
# Format code with black
black src/ tests/

# Lint with ruff
ruff check src/ tests/

# Type checking with mypy
mypy src/
```

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **Bug fixes**: Fix issues reported in the issue tracker
- **New features**: Implement features from the roadmap or propose new ones
- **Documentation**: Improve README, docstrings, or add examples
- **Tests**: Add or improve test coverage
- **Performance**: Optimize existing code
- **Refactoring**: Improve code quality without changing functionality

### Before You Start

1. **Check existing issues**: Look for existing issues or discussions related to your contribution
2. **Open an issue first**: For significant changes, open an issue to discuss your approach before implementing
3. **Get feedback**: Wait for maintainer feedback on your proposal before starting work

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for code formatting (line length: 100)
- Use [Ruff](https://github.com/astral-sh/ruff) for linting
- Use type hints for all function signatures
- Write docstrings for all public modules, classes, and functions

### Code Organization

```
src/context_packer/
├── __init__.py
├── cli.py              # CLI interface
├── chunker/            # AST parsing
├── index/              # Vector indexing
├── graph/              # Dependency graph
├── retrieval/          # Hybrid ranking
├── budget/             # Token budget management
├── packer/             # Output generation
└── utils/              # Shared utilities
```

### Documentation Style

- Use Google-style docstrings:
  ```python
  def function(arg1: str, arg2: int) -> bool:
      """Short description.
      
      Longer description if needed.
      
      Args:
          arg1: Description of arg1
          arg2: Description of arg2
          
      Returns:
          Description of return value
          
      Raises:
          ValueError: When invalid input is provided
      """
  ```

## Testing Guidelines

### Test Structure

- Place tests in `tests/` directory mirroring `src/` structure
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`
- Group related tests in classes

### Test Types

1. **Unit Tests**: Test individual functions/classes in isolation
   ```python
   def test_token_count_accuracy():
       """Test that token counting is within ±2% accuracy."""
       # Test implementation
   ```

2. **Property-Based Tests**: Test universal properties with Hypothesis
   ```python
   from hypothesis import given, strategies as st
   
   @given(st.text())
   def test_parse_never_crashes(source_code):
       """Property: Parser should never crash on any input."""
       # Test implementation
   ```

3. **Integration Tests**: Test component interactions
   ```python
   @pytest.mark.integration
   def test_full_workflow():
       """Test complete index → query → pack workflow."""
       # Test implementation
   ```

### Test Coverage

- Aim for >80% code coverage
- All new features must include tests
- Bug fixes should include regression tests

## Commit Message Guidelines

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(chunker): add support for TypeScript parsing

Implement TreeSitter-based parsing for TypeScript files with
support for interfaces, type aliases, and decorators.

Closes #123
```

```
fix(budget): correct token counting for multi-byte characters

Token counting was inaccurate for non-ASCII characters. Updated
to use tiktoken's proper encoding method.

Fixes #456
```

## Pull Request Process

### Before Submitting

1. **Update your branch**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all checks**:
   ```bash
   black src/ tests/
   ruff check src/ tests/
   mypy src/
   pytest
   ```

3. **Update documentation**: Update README, docstrings, and CHANGELOG.md

4. **Update CHANGELOG.md**: Add your changes under the "Unreleased" section

### Submitting the PR

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a Pull Request on GitHub with:
   - Clear title following commit message guidelines
   - Description of changes and motivation
   - Reference to related issues (e.g., "Closes #123")
   - Screenshots/examples if applicable

3. Fill out the PR template completely

### PR Review Process

- Maintainers will review your PR within 1-2 weeks
- Address review comments by pushing new commits
- Once approved, maintainers will merge your PR
- Your contribution will be included in the next release

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Commit messages follow guidelines
- [ ] No merge conflicts with main branch

## Reporting Bugs

### Before Reporting

1. Check if the bug has already been reported in [Issues](https://github.com/maemreyo/zmr-ctx-paker/issues)
2. Try to reproduce with the latest version
3. Gather relevant information (OS, Python version, error messages)

### Bug Report Template

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run command '...'
2. With config '...'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.11.5]
- Context Packer version: [e.g., 0.1.0]
- Installation method: [pip, source]

**Additional context**
- Error messages/stack traces
- Configuration file
- Sample repository (if applicable)
```

## Suggesting Enhancements

### Before Suggesting

1. Check if the enhancement has been suggested in [Issues](https://github.com/maemreyo/zmr-ctx-paker/issues)
2. Consider if it fits the project's scope and goals
3. Think about how it would benefit other users

### Enhancement Proposal Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Additional context**
- Use cases
- Examples from other projects
- Mockups or diagrams
```

## Development Tips

### Debugging

- Use `--verbose` flag for detailed logging
- Check logs in `.context-pack/logs/`
- Use Python debugger: `import pdb; pdb.set_trace()`

### Performance Profiling

```bash
# Profile with pytest-benchmark
pytest -m benchmark --benchmark-only

# Profile with cProfile
python -m cProfile -o profile.stats -m context_packer.cli pack /path/to/repo
```

### Working with Hypothesis

```bash
# Run with more examples
pytest --hypothesis-profile=ci

# Debug failing examples
pytest --hypothesis-verbosity=verbose
```

## Questions?

- Open a [Discussion](https://github.com/maemreyo/zmr-ctx-paker/discussions) for questions
- Join our community chat (if available)
- Email: zaob.ogn@gmail.com

## License

By contributing, you agree that your contributions will be licensed under the GPL-3.0-or-later license.

---

Thank you for contributing to Context Packer! 🎉
