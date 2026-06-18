# OWASP Top 10:2025 Web Application Security Audit Report

**Project:** Adaptive GenAI Learning Tutor
**Audit Date:** 2026-06-17
**Scope:** Backend (FastAPI), Frontend (React/tutor-ui), MCP Server

---

## Executive Summary

This audit evaluated the Adaptive GenAI Learning Tutor application against the OWASP Top 10:2025 Web Application Security Risks. The system is a FastAPI backend with React frontend, multi-tenant architecture, and enterprise features including Supabase persistence, LangSmith tracing, and MCP tool exposure.

**Overall Risk Level:** MEDIUM-HIGH

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 14 |
| Medium | 26 |
| Low | 4 |
| Info | 1 |
| **TOTAL** | **45** |

---

## A01: Broken Access Control

### WEB-001: Wildcard CORS in Non-Production Environments
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/main.py:79-84`, `backend/settings.py:90,176`, `.env.example:8`
- **Evidence:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
# settings.py:176
default_cors = ["*"] if os.getenv("TUTOR_ENV", "local").lower() not in {"prod", "production"} else []
```
- **Impact:** Allows any origin to make cross-origin requests in non-production environments, enabling CSRF attacks.
- **Remediation:** Use specific allowed origins even in development.
- **CWE:** CWE-942 (Permissive Cross-domain Policy)

### WEB-002: Insufficient Access Control for MCP Tools
- **Severity:** MEDIUM
- **Confidence:** MEDIUM
- **Files:** `mcp_server/server.py:35-62`
- **Evidence:** MCP tools rely on client-provided role parameter without backend verification.
- **Impact:** Malicious MCP client could escalate privileges by supplying `role="admin"`.
- **Remediation:** Implement server-side role validation using JWT/OIDC mechanisms.
- **CWE:** CWE-285 (Improper Authorization)

### WEB-003: Missing Horizontal Access Control Audit for Progress Export
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/main.py:278-282`
- **Evidence:** `require_learner_access` checks authorization but doesn't audit who accessed whose data.
- **Impact:** No audit trail for educator/admin data exports.
- **Remediation:** Add audit events specifically for data exports.
- **CWE:** CWE-778 (Insufficient Logging)

### WEB-004: Silent Cross-Tenant Access Failures
- **Severity:** HIGH
- **Confidence:** MEDIUM
- **Files:** `backend/stores.py:101-116,241-249`, `backend/repositories/supabase.py:80-93`
- **Evidence:** Cross-tenant access attempts return None silently without logging.
- **Impact:** Attacker could enumerate exercise IDs to map tenant boundaries without detection.
- **Remediation:** Log cross-tenant access attempts; use RLS in Supabase.
- **CWE:** CWE-200 (Information Exposure)

---

## A02: Security Misconfiguration

### WEB-005: Permissive Default Authentication Mode
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/settings.py:92,189`, `backend/auth.py:197-218`
- **Evidence:**
```python
auth_mode: Literal["local", "disabled", "jwt", "oidc"] = "local"
# Local mode accepts headers without cryptographic verification
```
- **Impact:** If deployed to production, any client can impersonate any user/tenant/role.
- **Remediation:** Enforce production auth mode validation; fail if production + weak auth.
- **CWE:** CWE-287 (Improper Authentication)

### WEB-006: Missing Security Headers
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/main.py`
- **Evidence:** No X-Content-Type-Options, X-Frame-Options, CSP, HSTS headers configured.
- **Impact:** Browser-based attacks (clickjacking, MIME sniffing) not mitigated.
- **Remediation:** Add security headers middleware.
- **CWE:** CWE-1021 (Improper Restriction of Rendered UI Layers)

### WEB-007: Verbose Error Messages
- **Severity:** LOW
- **Confidence:** MEDIUM
- **Files:** `backend/llm_provider.py:68-70`, `backend/auth.py:98-106`
- **Evidence:** Error messages may leak internal implementation details.
- **Impact:** Aids attackers in reconnaissance.
- **Remediation:** Implement error sanitization; log full errors, return generic messages.
- **CWE:** CWE-209 (Information Exposure Through Error Message)

### WEB-008: Insecure Default Request Body Limit
- **Severity:** LOW
- **Confidence:** HIGH
- **Files:** `backend/settings.py:91,188`
- **Evidence:** 64KB limit checked in middleware but Uvicorn may parse larger bodies.
- **Impact:** Large payload DoS attacks could bypass this check.
- **Remediation:** Configure Uvicorn's `--limit-max-body`; use reverse proxy limits.
- **CWE:** CWE-770 (Allocation of Resources Without Limits)

---

## A03: Software Supply Chain Failures

### WEB-009: No Dependency Vulnerability Scanning
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `pyproject.toml`, `tutor-ui/package.json`
- **Evidence:** No Dependabot, pip-audit, or automated CVE scanning configured.
- **Impact:** 15+ Python packages and 20+ npm packages without vulnerability monitoring.
- **Remediation:** Add Dependabot; integrate pip-audit and npm audit in CI/CD.
- **CWE:** CWE-1104 (Use of Unmaintained Third Party Components)

### WEB-010: Missing Software Bill of Materials (SBOM)
- **Severity:** LOW
- **Confidence:** HIGH
- **Files:** No SBOM file found
- **Evidence:** Project lacks SBOM in SPDX or CycloneDX format.
- **Impact:** Cannot quickly identify affected components during supply chain incidents.
- **Remediation:** Generate SBOM using cyclonedx-py and npm sbom.
- **CWE:** CWE-1059 (Insufficient Documentation of Error Handling)

### WEB-011: SRI Not Required (Not Using CDN)
- **Severity:** INFO
- **Confidence:** HIGH
- **Files:** `tutor-ui/index.html`
- **Evidence:** Application bundles all assets; no external CDN dependencies.
- **Impact:** LOW - Not applicable as no external scripts loaded.
- **Status:** NOT APPLICABLE

---

## A04: Cryptographic Failures

### WEB-012: API Keys in Environment Variables Without Encryption
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `.env.example:38,62-63,68-69`, `backend/settings.py:127,142-143,227`
- **Evidence:** `QWEN_API_KEY`, `LANGSMITH_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY` in plaintext.
- **Impact:** If .env committed or server compromised, keys immediately exposed.
- **Remediation:** Use secret management service (Vault, AWS Secrets Manager).
- **CWE:** CWE-312 (Cleartext Storage of Sensitive Information)

### WEB-013: JWT Secrets in Plain Configuration
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/settings.py:97-98,194-195`, `backend/auth.py:144-150`
- **Evidence:** JWT signing secrets stored in environment variables without protection.
- **Impact:** Compromise allows attacker to forge authentication tokens.
- **Remediation:** Enforce RS256 over HS256; store keys in secret manager.
- **CWE:** CWE-321 (Use of Hard-coded Cryptographic Key)

### WEB-014: Insecure Local Storage of Session Data
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `tutor-ui/src/context/SessionContext.jsx:6,10-17`
- **Evidence:** User session data (learner_id, tenant_id, role) stored in localStorage.
- **Impact:** Data persists and is accessible to XSS attacks.
- **Remediation:** Use sessionStorage; encrypt localStorage data.
- **CWE:** CWE-922 (Insecure Storage of Sensitive Information)

### WEB-015: Missing Encryption for Data at Rest
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/stores.py:31-40`, `backend/audit.py:93-95`
- **Evidence:** Learner progress, exercises, and audit logs stored in plaintext JSON.
- **Impact:** Filesystem compromise exposes all learner data.
- **Remediation:** Implement application-level encryption or filesystem encryption.
- **CWE:** CWE-311 (Missing Encryption of Sensitive Data)

---

## A05: Injection

### WEB-016: Potential SQL Injection via Supabase Filters
- **Severity:** HIGH
- **Confidence:** MEDIUM
- **Files:** `backend/repositories/supabase.py:82-89`, `backend/pgvector_store.py:182-191`
- **Evidence:**
```python
rows = self.client.get("learner_profiles", {"tenant_id": f"eq.{tenant}"})
```
- **Impact:** While PostgREST uses parameterized queries, filter values use string interpolation.
- **Remediation:** Validate/sanitize inputs; use UUID regex for IDs.
- **CWE:** CWE-89 (SQL Injection)

### WEB-017: Future Command Injection Risk
- **Severity:** LOW
- **Confidence:** LOW
- **Files:** `backend/stores.py:31-40`, `backend/agent.py:56-64`
- **Evidence:** File path operations don't currently use user-controlled paths.
- **Impact:** Potential future risk if user-controlled paths are added.
- **Remediation:** Never allow user-controlled paths; use Path().resolve() with validation.
- **CWE:** CWE-78 (OS Command Injection)

### WEB-018: NoSQL Injection
- **Severity:** N/A
- **Status:** NOT APPLICABLE
- **Justification:** Application uses PostgreSQL and local JSON, not NoSQL databases.

---

## A06: Insecure Design

### WEB-019: Rate Limiting Bypass via Header Manipulation
- **Severity:** MEDIUM
- **Confidence:** MEDIUM
- **Files:** `backend/rate_limit.py:100-125`
- **Evidence:** Rate limits scoped per `tenant_id:user_id`; in local auth, headers can be changed.
- **Impact:** Attackers can bypass rate limits by changing identity headers.
- **Remediation:** Implement IP-based rate limiting; add anomaly detection.
- **CWE:** CWE-799 (Improper Control of Interaction Frequency)

### WEB-020: Insufficient Monitoring and Alerting Design
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/audit.py:68-98`, `backend/observability.py:24-78`
- **Evidence:** Security events logged but not monitored or alerted.
- **Impact:** Attacks could go undetected for extended periods.
- **Remediation:** Integrate with SIEM; implement real-time alerting.
- **CWE:** CWE-778 (Insufficient Logging)

### WEB-021: Missing Security Documentation
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** Repository structure
- **Evidence:** No SECURITY.md, threat model, or security architecture diagrams.
- **Impact:** Security vulnerabilities introduced due to lack of design artifacts.
- **Remediation:** Create SECURITY.md; document threat model.
- **CWE:** CWE-1059 (Insufficient Documentation)

### WEB-022: Absence of Security Testing in CI/CD
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `pyproject.toml`, `tests/`
- **Evidence:** No SAST (bandit), DAST (ZAP), or secret scanning configured.
- **Impact:** No automated security testing in development workflow.
- **Remediation:** Add bandit, detect-secrets, eslint-plugin-security.
- **CWE:** CWE-1068 (Inconsistency Between Implementation and Design)

---

## A07: Authentication Failures

### WEB-023: Weak JWT Algorithm Configuration
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/settings.py:96,193`, `backend/auth.py:134-135`
- **Evidence:**
```python
auth_jwt_algorithms: list[str] = Field(default_factory=lambda: ["RS256", "HS256"])
```
- **Impact:** HS256 tokens can be forged if secret is compromised; algorithm downgrade possible.
- **Remediation:** Remove HS256; enforce RS256 or ES256 only.
- **CWE:** CWE-327 (Use of a Broken or Risky Cryptographic Algorithm)

### WEB-024: Missing Multi-Factor Authentication
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/auth.py`
- **Evidence:** No MFA implementation found.
- **Impact:** Compromised credentials grant full access with no second factor.
- **Remediation:** Implement TOTP-based MFA; support WebAuthn/FIDO2.
- **CWE:** CWE-308 (Use of Single-factor Authentication)

### WEB-025: No Account Lockout Mechanism
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/auth.py`, `backend/rate_limit.py`
- **Evidence:** No failed login attempt tracking or account lockout.
- **Impact:** Brute force attacks can continue indefinitely.
- **Remediation:** Implement lockout after 5 failed attempts; add CAPTCHA.
- **CWE:** CWE-307 (Improper Restriction of Excessive Authentication Attempts)

### WEB-026: Insufficient Session Management
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/auth.py`
- **Evidence:** Stateless JWTs with no revocation list or session tracking.
- **Impact:** Cannot revoke JWTs before expiration; no forced logout capability.
- **Remediation:** Implement JWT revocation list; add session tracking.
- **CWE:** CWE-613 (Insufficient Session Expiration)

### WEB-027: Password Complexity (Future Risk)
- **Severity:** MEDIUM
- **Status:** NOT APPLICABLE (Currently)
- **Justification:** App uses JWT/OIDC without local password management.

---

## A08: Software or Data Integrity Failures

### WEB-028: No Code Signing or Artifact Verification
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** Build/deployment configuration
- **Evidence:** No GPG signatures, Docker image signing, or npm provenance.
- **Impact:** Cannot verify authenticity of deployed artifacts.
- **Remediation:** Implement Sigstore cosign; sign Python wheels.
- **CWE:** CWE-494 (Download of Code Without Integrity Check)

### WEB-029: Insecure Deserialization in Agent Checkpoints
- **Severity:** HIGH
- **Confidence:** MEDIUM
- **Files:** `backend/checkpoints.py`, `backend/agent.py:191`
- **Evidence:** LangGraph checkpointers serialize/deserialize graph state.
- **Impact:** Checkpoint tampering could execute code when agent resumes.
- **Remediation:** Use JSON-only serialization; HMAC signatures on checkpoint data.
- **CWE:** CWE-502 (Deserialization of Untrusted Data)

### WEB-030: Missing Audit Trail Integrity Protection
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/audit.py:93-95`
- **Evidence:** Audit logs are JSONL without integrity protection.
- **Impact:** Attacker with filesystem access can modify/delete audit entries.
- **Remediation:** Implement HMAC signatures; use append-only filesystem features.
- **CWE:** CWE-117 (Improper Output Neutralization for Logs)

### WEB-031: Lack of Update Integrity Verification
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** Deployment process
- **Evidence:** No automated deployment checksums or integrity verification.
- **Impact:** Compromised code could be deployed without detection.
- **Remediation:** Sign Git commits; implement deployment verification tests.
- **CWE:** CWE-354 (Improper Validation of Integrity Check Value)

---

## A09: Security Logging and Alerting Failures

### WEB-032: Insufficient Security Event Logging
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/auth.py`, `backend/audit.py`
- **Evidence:** Missing logs for failed auth, authorization failures, suspicious patterns.
- **Impact:** Insufficient logging prevents detection and investigation.
- **Remediation:** Log all auth events; audit all authorization decisions.
- **CWE:** CWE-778 (Insufficient Logging)

### WEB-033: No Centralized Log Management
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/observability.py:58-73`, `backend/audit.py`
- **Evidence:** Logs to stdout and local files only; no aggregation.
- **Impact:** Correlation and analysis difficult; log rotation may delete evidence.
- **Remediation:** Integrate with ELK, Splunk, or CloudWatch.
- **CWE:** CWE-778 (Insufficient Logging)

### WEB-034: Missing Anomaly Detection
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** Entire codebase
- **Evidence:** No behavioral analytics, velocity checks, or geographic anomaly detection.
- **Impact:** Advanced attacks staying under rate limits go undetected.
- **Remediation:** Implement behavioral analytics; detect impossible travel.
- **CWE:** CWE-693 (Protection Mechanism Failure)

### WEB-035: No Real-Time Security Alerting
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/audit.py`
- **Evidence:** Security events logged but no alerting mechanism.
- **Impact:** Critical events discovered hours or days after occurrence.
- **Remediation:** Implement real-time alerting via PagerDuty, Slack, or email.
- **CWE:** CWE-778 (Insufficient Logging)

### WEB-036: Sensitive Data in Application Logs
- **Severity:** MEDIUM
- **Confidence:** MEDIUM
- **Files:** `backend/llm_provider.py:68-70`
- **Evidence:** Logs may contain PII or API response content.
- **Impact:** Log access becomes a data breach vector.
- **Remediation:** Implement log sanitization; redact sensitive data.
- **CWE:** CWE-532 (Information Exposure Through Log Files)

---

## A10: Mishandling of Exceptional Conditions

### WEB-037: Generic Exception Handling Masks Security Issues
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/auth.py:99-104`, `backend/llm_provider.py:64-67`, `mcp_server/server.py:452-453`
- **Evidence:** Broad exception handlers catch security-relevant errors.
- **Impact:** Security teams cannot differentiate between benign errors and attacks.
- **Remediation:** Implement specific exception classes; log before converting.
- **CWE:** CWE-755 (Improper Handling of Exceptional Conditions)

### WEB-038: Error Handling Bypass in Rate Limiting
- **Severity:** MEDIUM
- **Confidence:** MEDIUM
- **Files:** `backend/rate_limit.py:137-155`, `mcp_server/server.py:49-53`
- **Evidence:** Unexpected exceptions in rate limiter could bypass protection.
- **Impact:** Error conditions could disable protection mechanisms.
- **Remediation:** Implement fail-secure defaults; deny on rate limiter error.
- **CWE:** CWE-754 (Improper Check for Unusual or Exceptional Conditions)

### WEB-039: Detailed Validation Error Responses
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/main.py:103-115`
- **Evidence:** Validation errors expose internal model structure via `exc.errors()`.
- **Impact:** Attackers can map API schema via malformed requests.
- **Remediation:** Sanitize validation error details for production.
- **CWE:** CWE-209 (Information Exposure Through Error Message)

### WEB-040: Insufficient Error Recovery in Agent System
- **Severity:** MEDIUM
- **Confidence:** MEDIUM
- **Files:** `backend/agent_runtime.py`, `backend/main.py:193-204`
- **Evidence:** Generic error recovery may hide security-relevant failures.
- **Impact:** Users not informed why request failed; security issues hidden.
- **Remediation:** Categorize errors; implement graceful degradation with clear communication.
- **CWE:** CWE-755 (Improper Handling of Exceptional Conditions)

---

## Summary by Category

| Category | Critical | High | Medium | Low | Info |
|----------|----------|------|--------|-----|------|
| A01: Broken Access Control | 0 | 2 | 2 | 0 | 0 |
| A02: Security Misconfiguration | 0 | 1 | 2 | 2 | 0 |
| A03: Supply Chain Failures | 0 | 0 | 1 | 1 | 1 |
| A04: Cryptographic Failures | 0 | 1 | 4 | 0 | 0 |
| A05: Injection | 0 | 1 | 0 | 1 | 0 |
| A06: Insecure Design | 0 | 0 | 5 | 0 | 0 |
| A07: Authentication Failures | 0 | 4 | 2 | 0 | 0 |
| A08: Data Integrity Failures | 0 | 2 | 2 | 0 | 0 |
| A09: Logging Failures | 0 | 3 | 3 | 0 | 0 |
| A10: Exception Handling | 0 | 0 | 5 | 0 | 0 |
| **TOTAL** | **0** | **14** | **26** | **4** | **1** |

---

## Regression Tests Required

1. **Auth boundary tests:** Verify learners cannot access other tenants' data
2. **CORS validation tests:** Ensure specific origins enforced in production
3. **Rate limit tests:** Verify IP-based limits work with header manipulation
4. **JWT validation tests:** Confirm HS256 is rejected when removed from allowed list
5. **Audit log tests:** Verify critical events are logged with required fields

---

**End of Report**
