# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in the Adaptive GenAI Learning Tutor, please report it responsibly:

1. **Do NOT** create a public GitHub issue for security vulnerabilities
2. Email security concerns to the project maintainers
3. Include a detailed description of the vulnerability
4. Include steps to reproduce if possible
5. Allow up to 48 hours for an initial response

## Security Measures Implemented

This project implements security controls based on three OWASP frameworks:

### Authentication & Authorization
- JWT/OIDC authentication required in production
- HS256 algorithm blocked (only RS256, ES256, etc. allowed)
- Role-based access control (learner, educator, admin)
- Production mode blocks local/disabled auth modes

### Input Validation
- Prompt injection detection with 30+ patterns
- Input sanitization before LLM processing
- Message length limits (10,000 characters)
- MCP tool parameter validation

### Rate Limiting & Resource Control
- Per-user rate limits by action type
- Daily token budgets to prevent cost explosion
- Recursion limit set to 25 steps
- Per-tool rate limiting

### Data Protection
- HMAC-SHA256 signatures on persisted state files
- Memory namespace isolation per tenant/learner
- CORS restricted to specific origins in production
- Security headers on all responses

### Logging & Monitoring
- Security event logging with client IP tracking
- Audit trail for all sensitive operations
- Event flagging for SIEM integration

## Security Configuration

### Required Environment Variables (Production)

```bash
# Authentication (REQUIRED in production)
TUTOR_AUTH_MODE=oidc  # or 'jwt'
TUTOR_OIDC_JWKS_URL=https://your-idp/.well-known/jwks.json
TUTOR_AUTH_ISSUER=https://your-idp
TUTOR_AUTH_AUDIENCE=your-audience

# State Integrity (RECOMMENDED)
TUTOR_STATE_HMAC_KEY=your-secure-random-key

# CORS (REQUIRED in production)
TUTOR_CORS_ORIGINS=https://your-frontend.com,https://app.your-domain.com

# Token Budgets (OPTIONAL)
TUTOR_TOKEN_BUDGET_ENABLED=true
TUTOR_TOKEN_BUDGET_DAILY_LIMIT=100000
```

### Security Checks at Startup

The application performs these checks at startup:
1. Validates auth_mode is not 'local' or 'disabled' in production
2. Validates JWT algorithms are secure (no HS256)
3. Validates CORS origins do not include wildcards in production

## Security Audit Reports

Security audits are performed against:
- OWASP Top 10:2025 (Web Application Security)
- OWASP Top 10 for LLM Applications 2025
- OWASP Top 10 for Agentic Applications 2026

Audit reports are available in:
- `owasp-web-audit-report.md`
- `owasp-llm-audit-report.md`
- `owasp-agentic-audit-report.md`
- `master-security-report.md` (consolidated)
