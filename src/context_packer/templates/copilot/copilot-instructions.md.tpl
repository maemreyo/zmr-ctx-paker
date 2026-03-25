# ctx-packer — Code Packaging for GitHub Copilot

## Overview

This project uses **ctx-packer** for intelligent code context packaging.

## Commands

```bash
${CTX_CMD_INDEX}           # Build index (run once)
${CTX_CMD_SEARCH} # Find relevant files
${CTX_CMD_FULL_ZIP}  # Full context bundle
```

## Use Cases

- Finding files related to a feature or bug
- Understanding code structure before changes
- Generating context for code review
- Investigating errors or issues

## Notes

- Index location: `.context-pack/`
- ZIP output for file upload
- XML output for pasting
- Default budget: 100k tokens
