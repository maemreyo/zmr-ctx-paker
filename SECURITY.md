# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take the security of ws-ctx-engine seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Please Do Not

- **Do not** open a public GitHub issue for security vulnerabilities
- **Do not** disclose the vulnerability publicly until it has been addressed

### How to Report

**Email**: Send details to **zaob.ogn@gmail.com** with the subject line "SECURITY: [Brief Description]"

**Include**:
1. Description of the vulnerability
2. Steps to reproduce the issue
3. Potential impact
4. Suggested fix (if any)
5. Your contact information

### What to Expect

1. **Acknowledgment**: We will acknowledge receipt of your report within 48 hours
2. **Assessment**: We will assess the vulnerability and determine its severity within 5 business days
3. **Updates**: We will keep you informed of our progress
4. **Resolution**: We will work on a fix and coordinate disclosure timing with you
5. **Credit**: We will credit you in the security advisory (unless you prefer to remain anonymous)

## Security Best Practices

When using ws-ctx-engine, follow these security best practices:

### API Keys and Secrets

- **Never commit API keys** to the repository
- Store API keys in environment variables:
  ```bash
  export OPENAI_API_KEY="your-key-here"
  ```
- Use `.env` files (excluded from git) for local development
- Rotate API keys regularly

### Configuration Files

- Review `.ws-ctx-engine.yaml` before committing
- Exclude sensitive paths in `exclude_patterns`
- Be cautious with `include_patterns` to avoid exposing sensitive files

### Input Validation

- Validate repository paths before indexing
- Be cautious when indexing untrusted repositories
- Review generated output before sharing

### Dependencies

- Keep dependencies up to date:
  ```bash
  pip install --upgrade ws-ctx-engine
  ```
- Review security advisories for dependencies
- Use virtual environments to isolate dependencies

### Network Security

- When using OpenAI API fallback, ensure HTTPS connections
- Review network logs in `.ws-ctx-engine/logs/` for suspicious activity
- Use firewall rules to restrict outbound connections if needed

## Known Security Considerations

### Code Execution

ws-ctx-engine parses source code but **does not execute it**. However:
- AST parsing may trigger parser bugs in Tree-sitter
- Malformed source files could cause parser crashes (handled by fallback)

### Data Privacy

- Indexed code is stored locally in `.ws-ctx-engine/`
- When using OpenAI API fallback, code snippets are sent to OpenAI
- Review OpenAI's data usage policy: https://openai.com/policies/api-data-usage-policies

### File System Access

- ws-ctx-engine reads files from the specified repository path
- It writes to `.ws-ctx-engine/` and the configured output directory
- Ensure proper file permissions on sensitive repositories

## Security Updates

Security updates will be released as patch versions (e.g., 0.1.1) and announced via:
- GitHub Security Advisories
- Release notes in CHANGELOG.md
- Email to reporters (if applicable)

## Vulnerability Disclosure Policy

We follow a **coordinated disclosure** approach:

1. **Private disclosure**: Report sent to maintainers
2. **Assessment**: 5 business days to assess severity
3. **Fix development**: Time varies based on complexity
4. **Coordinated release**: Fix released with security advisory
5. **Public disclosure**: 90 days after fix release (or earlier if agreed)

## Security Hall of Fame

We recognize security researchers who responsibly disclose vulnerabilities:

<!-- List will be populated as vulnerabilities are reported and fixed -->

*No vulnerabilities reported yet.*

## Contact

For security concerns, contact:
- **Email**: zaob.ogn@gmail.com
- **PGP Key**: (To be added if needed)

For general questions, use [GitHub Discussions](https://github.com/maemreyo/zmr-ctx-paker/discussions).

---

Thank you for helping keep ws-ctx-engine and its users safe!
