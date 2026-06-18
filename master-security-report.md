# Master Security Report — Adaptive GenAI Learning Tutor

**Audit Date:** 2026-06-17
**Project:** Adaptive GenAI Learning Tutor
**Branch:** `security-audit-2026-06-17`
**Frameworks Applied:**
- OWASP Top 10:2025 (Web Application Security)
- OWASP Top 10 for LLM Applications 2025
- OWASP Top 10 for Agentic Applications 2026

---

## Executive Summary

This consolidated report merges findings from three OWASP framework audits. The Adaptive GenAI Learning Tutor is a multi-tenant, deep-agent tutoring system with FastAPI backend, React frontend, MCP tool exposure, and Qwen LLM integration.

### Overall Risk Assessment: **MEDIUM-HIGH**

| Framework | Critical | High | Medium | Low | Info | Total |
|-----------|----------|------|--------|-----|------|-------|
| Web (A01-A10) | 0 | 14 | 26 | 4 | 1 | 45 |
| LLM (LLM01-10) | 1 | 7 | 19 | 7 | 3 | 37 |
| Agentic (ASI01-10) | 0 | 7 | 17 | 8 | 2 | 34 |
| **Deduplicated Total** | **1** | **21** | **45** | **14** | **4** | **~85** |

### Top 10 Critical/High Findings (Prioritized)

| Rank | ID | Category | Severity | Description |
|------|-----|----------|----------|-------------|
| 1 | LLM-001 | Prompt Injection | **CRITICAL** | Direct prompt injection in orchestrator via unsanitized user input |
| 2 | WEB-005 | Auth Misconfiguration | HIGH | Default "local" auth accepts arbitrary headers |
| 3 | AGT-020 | Memory Poisoning | HIGH | Unrestricted memory writes allow cross-session poisoning |
| 4 | WEB-001 | Access Control | HIGH | Wildcard CORS in non-production environments |
| 5 | LLM-029 | Unbounded Consumption | HIGH | No per-user token limits; cost explosion risk |
| 6 | AGT-009 | Tool Misuse | HIGH | MCP `ask_tutor` provides full agent access without validation |
| 7 | WEB-023 | Auth Failures | HIGH | HS256 JWT algorithm allowed (weaker than RS256) |
| 8 | AGT-005 | Tool Misuse | HIGH | No runtime tool ACL enforcement across subagents |
| 9 | WEB-013 | Crypto Failures | HIGH | JWT secrets stored in plaintext environment variables |
| 10 | AGT-006 | HITL Bypass | HIGH | State write may execute before HITL approval check |

---

## Deduplicated Findings by Theme

### Theme 1: Input Validation & Prompt Injection
**Overlapping:** LLM-001, LLM-002, LLM-003, LLM-004, AGT-001, AGT-002, AGT-009, WEB-016

**Root Cause:** User input flows directly into LLM context without sanitization at any layer.

**Consolidated Remediation:**
1. Implement centralized input sanitization layer before orchestrator
2. Add prompt injection detection using pattern matching or ML classifier
3. Use structured message formats (not string concatenation)
4. Validate and sanitize all tool parameters before execution
5. Apply same validation to MCP tools as REST endpoints

**Files Requiring Changes:**
- `backend/agent_runtime.py:214` - Add input sanitization
- `backend/agent.py:138-177` - Harden orchestrator prompt
- `mcp_server/server.py:428-467` - Add content filtering
- NEW: `backend/input_filter.py` - Centralized filtering module

---

### Theme 2: Authentication & Authorization
**Overlapping:** WEB-005, WEB-002, AGT-010, AGT-011, WEB-023, WEB-024, WEB-025, WEB-026

**Root Cause:** Default auth mode trusts client-provided headers; MCP lacks server-side identity validation.

**Consolidated Remediation:**
1. Require JWT/OIDC in production (fail startup if `TUTOR_ENV=production` and `auth_mode=local`)
2. Remove HS256 from allowed JWT algorithms
3. Implement MCP authentication layer with API keys per role
4. Add account lockout after 5 failed auth attempts
5. Implement JWT revocation list for forced logout
6. Add MFA for admin role

**Files Requiring Changes:**
- `backend/settings.py` - Add production auth validation
- `backend/auth.py` - Remove HS256; add lockout logic
- `mcp_server/server.py` - Add authentication layer
- NEW: `backend/mcp_auth.py` - MCP-specific auth

---

### Theme 3: Memory & State Integrity
**Overlapping:** AGT-020, AGT-021, AGT-022, AGT-023, WEB-029, WEB-030, WEB-015

**Root Cause:** Agent memories, learner state, and checkpoints lack integrity protection; shared namespaces enable cross-session pollution.

**Consolidated Remediation:**
1. Isolate memory namespace by tenant_id and learner_id
2. Add HMAC signatures to all persisted state files
3. Implement content validation for memory writes
4. Enable SQLCipher encryption for checkpoint database
5. Add integrity verification on state load

**Files Requiring Changes:**
- `backend/agent.py:70` - Change namespace to include tenant/learner
- `backend/stores.py` - Add HMAC signing/verification
- `backend/checkpoints.py` - Enable encryption
- NEW: `backend/state_integrity.py` - Centralized integrity module

---

### Theme 4: Resource Consumption & Rate Limiting
**Overlapping:** LLM-029, LLM-030, LLM-031, LLM-032, WEB-019, AGT-008, AGT-025

**Root Cause:** No per-user token budgets; recursion limit too high (80); shared rate limits across tools.

**Consolidated Remediation:**
1. Implement per-user token budgets tracked in learner profile
2. Reduce recursion limit to 20-30
3. Implement per-tool rate limits (not shared)
4. Add server-side timeout for streaming (5-10 minutes)
5. Implement circuit breaker for external APIs
6. Add IP-based rate limiting as backup

**Files Requiring Changes:**
- `backend/agent_runtime.py:32` - Reduce recursion limit
- `backend/llm_provider.py` - Add circuit breaker
- `backend/rate_limit.py` - Per-tool limits
- `backend/settings.py` - Token budget settings
- `backend/stores.py` - Track token usage

---

### Theme 5: Secrets & Cryptography
**Overlapping:** WEB-012, WEB-013, LLM-005, WEB-014, WEB-015

**Root Cause:** API keys and JWT secrets stored in plaintext environment variables; no encryption at rest.

**Consolidated Remediation:**
1. Migrate to secrets management (Vault, AWS Secrets Manager)
2. Implement key rotation policy (30-90 days)
3. Encrypt sensitive localStorage data
4. Implement application-level encryption for JSON data files
5. Add pre-commit hook to prevent `.env` commits

**Files Requiring Changes:**
- `backend/settings.py` - Integrate secret manager
- `tutor-ui/src/context/SessionContext.jsx` - Encrypt localStorage
- `backend/stores.py` - Add encryption layer
- NEW: `.pre-commit-config.yaml` - Secret scanning

---

### Theme 6: Logging, Monitoring & Alerting
**Overlapping:** WEB-032, WEB-033, WEB-034, WEB-035, AGT-027, AGT-028

**Root Cause:** Security events logged but not monitored; no real-time alerting; centralized log management absent.

**Consolidated Remediation:**
1. Integrate with SIEM (ELK, Splunk, Datadog)
2. Implement real-time alerting via PagerDuty/Slack
3. Log all auth events (success and failure) with source IP
4. Add anomaly detection for unusual patterns
5. Implement dead letter queue for failed enterprise writes

**Files Requiring Changes:**
- `backend/audit.py` - Add security event logging
- `backend/auth.py` - Log auth attempts
- `backend/observability.py` - Add SIEM integration
- NEW: `backend/alerting.py` - Alert rules and triggers

---

### Theme 7: Supply Chain & Dependencies
**Overlapping:** WEB-009, WEB-010, LLM-009, LLM-011, AGT-014, AGT-015, AGT-017

**Root Cause:** No automated vulnerability scanning; dependencies not pinned; skills loaded without integrity verification.

**Consolidated Remediation:**
1. Add Dependabot configuration
2. Integrate pip-audit and npm audit in CI/CD
3. Pin exact versions for production
4. Generate and maintain SBOM (CycloneDX)
5. Sign and verify skill files
6. Implement multi-provider LLM fallback

**Files Requiring Changes:**
- NEW: `.github/dependabot.yml`
- `pyproject.toml` - Pin versions
- `backend/agent.py` - Add skill verification
- NEW: `sbom.json` - Software bill of materials

---

### Theme 8: Grounding & Citation Verification
**Overlapping:** LLM-026, LLM-027, LLM-028, AGT-003, AGT-029

**Root Cause:** Grounding rules enforced via prompt only; no technical verification that citations exist or match corpus.

**Consolidated Remediation:**
1. Implement post-generation citation validator
2. Check all cited sources exist in corpus
3. Add grounding compliance score to responses
4. Block responses with zero citations
5. Add "hallucination detection" layer

**Files Requiring Changes:**
- NEW: `backend/grounding_validator.py`
- `backend/agent_runtime.py` - Call validator before response
- `backend/tools.py` - Add citation verification

---

## Remediation Roadmap

### Phase 1: Critical & High (Week 1-2)
| ID | Fix | Effort | Risk if Unpatched |
|----|-----|--------|-------------------|
| LLM-001 | Input sanitization layer | 3 days | CRITICAL - Full system compromise |
| WEB-005 | Production auth enforcement | 1 day | HIGH - Full impersonation |
| AGT-020 | Memory namespace isolation | 1 day | HIGH - Cross-user attacks |
| WEB-001 | Specific CORS origins | 0.5 day | HIGH - CSRF attacks |
| LLM-029 | Token budgets | 2 days | HIGH - Cost explosion |
| AGT-009 | MCP content filtering | 1 day | HIGH - Prompt injection |
| WEB-023 | Remove HS256 | 0.5 day | HIGH - Token forgery |

### Phase 2: High Priority (Week 3-4)
| ID | Fix | Effort |
|----|-----|--------|
| WEB-013 | Secrets management integration | 3 days |
| AGT-005 | Tool ACL enforcement | 2 days |
| AGT-006 | HITL gate validation | 1 day |
| WEB-032 | Security event logging | 2 days |
| WEB-035 | Real-time alerting | 2 days |
| LLM-030 | Reduce recursion limit | 0.5 day |

### Phase 3: Medium Priority (Month 2)
- State integrity protection (HMAC signatures)
- Citation verification pipeline
- Circuit breakers for external APIs
- Per-tool rate limiting
- Dependency vulnerability scanning (CI/CD)
- SBOM generation

### Phase 4: Long-term (Month 3+)
- MFA implementation
- Account lockout mechanism
- Anomaly detection
- Comprehensive security documentation
- Penetration testing

---

## Regression Tests Required

### Security Test Suite (NEW)
```python
# tests/test_security.py

def test_prompt_injection_patterns_rejected():
    """Common injection patterns should be filtered."""

def test_cross_tenant_access_blocked():
    """Learners cannot access other tenants' data."""

def test_mcp_role_cannot_be_spoofed():
    """MCP tools verify role server-side."""

def test_hitl_gate_blocks_until_approval():
    """commit_progress requires explicit approval."""

def test_memory_namespace_isolated():
    """Learner A's memory not visible to learner B."""

def test_token_budget_enforced():
    """Users exceeding token budget receive error."""

def test_recursion_limit_graceful_degradation():
    """Hitting limit returns friendly message, not crash."""

def test_citation_verification():
    """All cited sources must exist in corpus."""

def test_hs256_jwt_rejected():
    """HS256 tokens rejected when removed from config."""

def test_production_requires_jwt_auth():
    """Startup fails if TUTOR_ENV=production and auth_mode=local."""
```

---

## Files Changed Summary

| File | Changes |
|------|---------|
| `backend/agent_runtime.py` | Input sanitization; reduce recursion limit |
| `backend/agent.py` | Memory namespace isolation; skill verification |
| `backend/settings.py` | Production auth validation; token budgets |
| `backend/auth.py` | Remove HS256; add lockout; log attempts |
| `backend/stores.py` | HMAC signing; token tracking |
| `backend/rate_limit.py` | Per-tool limits; IP-based limits |
| `backend/llm_provider.py` | Circuit breaker |
| `mcp_server/server.py` | Content filtering; auth layer |
| `tutor-ui/src/context/SessionContext.jsx` | Encrypt localStorage |
| NEW: `backend/input_filter.py` | Centralized input sanitization |
| NEW: `backend/grounding_validator.py` | Citation verification |
| NEW: `backend/state_integrity.py` | HMAC for state files |
| NEW: `backend/alerting.py` | Security alerting |
| NEW: `backend/mcp_auth.py` | MCP authentication |
| NEW: `.github/dependabot.yml` | Dependency scanning |
| NEW: `tests/test_security.py` | Security test suite |
| NEW: `SECURITY.md` | Vulnerability reporting process |

---

## Approval Gate

**This concludes the read-only audit. No code changes have been made.**

Do you want me to proceed with automated remediation?

Reply with one of:
- **REMEDIATE ALL** — Fix all findings
- **REMEDIATE CRITICAL-HIGH ONLY** — Fix only Critical and High severity findings
- **REMEDIATE [ID]** — Fix a specific finding (e.g., REMEDIATE LLM-001)
- **STOP** — Do not make any changes

---

*Report generated by OWASP Security Audit*
*Branch: `security-audit-2026-06-17`*
*Baseline: 39 pytest passed, 2 npm audit vulnerabilities (esbuild/vite)*
