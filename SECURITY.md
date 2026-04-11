# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.4.x   | :white_check_mark: |
| < 0.4   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in vibescore, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email **security@vibescore.dev** or use [GitHub Security Advisories](https://github.com/stef41/vibescore/security/advisories/new).
3. Include steps to reproduce and impact assessment.

We will acknowledge receipt within 48 hours and provide a fix timeline within 7 days.

## Scope

vibescore scans project files locally for quality issues. It does not:
- Send data to external servers
- Require API keys or credentials
- Execute or modify your project's code

Security concerns are primarily around dependency supply chain and path traversal in file scanning.
