# Security Policy

This project has been audited against three OWASP security frameworks:

| Framework | Version | Coverage |
|-----------|---------|----------|
| OWASP Top 10 Web Application Security Risks | 2025 | Full |
| OWASP Top 10 for LLM Applications | 2025 | Full |
| OWASP Top 10 for Agentic Applications | 2026 | Full |

## Security Features

- **JWT Authentication** with RS256 (asymmetric keys only)
- **Per-tenant rate limiting** with sliding window
- **Token budget enforcement** to prevent cost explosion
- **Audit logging** for all security-relevant events
- **Input validation** with Pydantic strict mode
- **Output sanitization** for LLM responses
- **Human-in-the-loop gates** for consequential actions

## Running Your Own Audit

Use the included [OWASP Security Audit Prompt](OWASP_Security_Audit_Prompt.md) to run a comprehensive security audit on your own project.

## Reporting Vulnerabilities

If you discover a security vulnerability, please open a GitHub issue or contact the maintainer directly.

## References

- [OWASP Top 10 Web](https://owasp.org/Top10/)
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [OWASP Secure Agent Playbook](https://github.com/OWASP/secure-agent-playbook)
