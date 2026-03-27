# CI/CD Integration Workflow

Automate code analysis, review, and documentation generation in CI/CD pipelines.

## Overview

Integrate ws-ctx-engine into your CI/CD workflow to:
- Automatically analyze PR changes
- Generate context for code review
- Create documentation updates
- Run quality checks

## GitHub Actions

### Example 1: Automated PR Review

```yaml
name: PR Analysis

on:
  pull_request:
    branches: [main, develop]

jobs:
  analyze-pr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install ws-ctx-engine
        run: |
          pip install "ws-ctx-engine[all]"
      
      - name: Initialize configuration
        run: |
          ws-ctx-engine init-config .
      
      - name: Build indexes
        run: |
          ws-ctx-engine index .
      
      - name: Get changed files
        id: changed
        run: |
          git diff --name-only ${{ github.event.before }} > changed.txt
          echo "count=$(wc -l < changed.txt)" >> $GITHUB_OUTPUT
      
      - name: Generate PR context
        if: steps.changed.outputs.count > 0
        run: |
          ws-ctx-engine pack . \
            -q "review these code changes" \
            --changed-files changed.txt \
            --format xml \
            --agent-mode \
            --stdout > pr-context.json
      
      - name: Upload context artifact
        uses: actions/upload-artifact@v4
        with:
          name: pr-review-context
          path: pr-context.json
```

### Example 2: Documentation Generation

```yaml
name: Auto Documentation

on:
  push:
    branches: [main]

jobs:
  generate-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup ws-ctx-engine
        uses: ./.github/actions/setup-ws-ctx-engine
      
      - name: Generate API documentation
        run: |
          ws-ctx-engine query "public API endpoints" \
            --format markdown \
            --budget 50000 \
            --stdout > docs/api-overview.md
      
      - name: Commit documentation updates
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "docs: Auto-update API documentation"
          file_pattern: docs/*.md
```

### Example 3: Code Quality Check

```yaml
name: Code Quality

on:
  pull_request:
    branches: [main]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      
      - name: Setup ws-ctx-engine
        uses: ./.github/actions/setup-ws-ctx-engine
      
      - name: Analyze code changes
        run: |
          git diff --name-only HEAD~1 > changed.txt
          ws-ctx-engine pack . \
            -q "identify potential issues in these changes" \
            --changed-files changed.txt \
            --format json \
            --agent-mode \
            --stdout > quality-report.json
      
      - name: Upload quality report
        uses: actions/upload-artifact@v4
        with:
          name: quality-report
          path: quality-report.json
```

## GitLab CI

### Example Configuration

```yaml
stages:
  - analyze
  - review

analyze_pr:
  stage: analyze
  image: python:3.11
  script:
    - pip install "ws-ctx-engine[all]"
    - ws-ctx-engine init-config .
    - ws-ctx-engine index .
    - git diff --name-only > changed.txt
    - ws-ctx-engine pack . \
        -q "review changes" \
        --changed-files changed.txt \
        --format xml \
        --agent-mode \
        --stdout > pr-context.json
  artifacts:
    paths:
      - pr-context.json
    expire_in: 1 week
```

## CircleCI

### Example Configuration

```yaml
version: 2.1

jobs:
  pr-analysis:
    docker:
      - image: python:3.11
    steps:
      - checkout
      - run:
          name: Install ws-ctx-engine
          command: |
            pip install "ws-ctx-engine[all]"
      - run:
          name: Initialize and index
          command: |
            ws-ctx-engine init-config .
            ws-ctx-engine index .
      - run:
          name: Generate context
          command: |
            git diff --name-only HEAD~1 > changed.txt
            ws-ctx-engine pack . \
              -q "code review" \
              --changed-files changed.txt \
              --format json
      - store_artifacts:
          path: output/
```

## Azure DevOps

### Example Pipeline

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
- script: |
    pip install "ws-ctx-engine[all]"
    ws-ctx-engine init-config .
    ws-ctx-engine index .
  displayName: 'Setup ws-ctx-engine'

- script: |
    git diff --name-only HEAD~1 > changed.txt
    ws-ctx-engine pack . \
      -q "PR analysis" \
      --changed-files changed.txt \
      --format xml
  displayName: 'Generate PR Context'

- task: PublishPipelineArtifact@1
  inputs:
    targetPath: 'output/'
    artifact: 'pr-review-context'
```

## Common Patterns

### Pattern 1: Changed Files Detection

```yaml
# GitHub Actions
- name: Get changed files
  run: |
    git diff --name-only ${{ github.event.before }} > changed.txt

# GitLab CI (last commit)
- git diff --name-only HEAD~1 > changed.txt

# Generic (between tags)
- git diff --name-only v1.0.0 HEAD > changed.txt
```

### Pattern 2: Conditional Execution

```yaml
# Only for PRs with code changes
- name: Check if code changed
  id: check
  run: |
    count=$(git diff --name-only ${{ github.event.before }} | wc -l)
    echo "changed=$count" >> $GITHUB_OUTPUT

- name: Run analysis
  if: steps.check.outputs.changed > 0
  run: |
    # Your analysis here
```

### Pattern 3: Artifact Management

```yaml
# Upload for later use
- uses: actions/upload-artifact@v4
  with:
    name: analysis-results
    path: |
      output/*.xml
      output/*.json
      *.md

# Download in subsequent job
- uses: actions/download-artifact@v4
  with:
    name: analysis-results
```

## Best Practices

### Performance Optimization

**Cache Indexes:**
```yaml
- name: Cache ws-ctx-engine indexes
  uses: actions/cache@v4
  with:
    path: .ws-ctx-engine/
    key: ${{ runner.os }}-wsctx-${{ hashFiles('**/*.py') }}
    restore-keys: |
      ${{ runner.os }}-wsctx-
```

**Incremental Updates:**
```bash
# In CI, always start fresh
ws-ctx-engine index .

# But use incremental for multi-step workflows
ws-ctx-engine index . --incremental
```

### Security Considerations

**Secret Scanning:**
```bash
# Enable secret scanning in CI
ws-ctx-engine pack . \
  -q "review changes" \
  --secrets-scan \
  --agent-mode
```

**Access Control:**
```yaml
# Limit artifact access
permissions:
  contents: read
  pull-requests: write
```

### Cost Management

**Token Budget Control:**
```bash
# Limit token usage in CI
ws-ctx-engine query "review" --budget 30000
```

**Compression:**
```bash
# Reduce output size
ws-ctx-engine pack . -q "review" --compress
```

## Troubleshooting

### "Indexes not found in CI"

**Solution:**
```yaml
# Always build indexes in CI
- name: Build indexes
  run: ws-ctx-engine index .
```

### "No changed files detected"

**Check:**
```bash
# Verify git history
git log --oneline -5

# Check diff
git diff --name-only HEAD~1
```

### "Memory limit exceeded"

**Solutions:**
```bash
# Reduce token budget
ws-ctx-engine query "review" --budget 20000

# Use compression
ws-ctx-engine pack . -q "review" --compress
```

## Related Workflows

- [Development Workflow](development.md) - Local development patterns
- [Agent Integration](agent-integration.md) - AI agent automation
- [Initial Setup](initial-setup.md) - Getting started guide
