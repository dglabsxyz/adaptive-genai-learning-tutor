# OWASP Top 10 for LLM Applications 2025 Security Audit Report

**Project:** Adaptive GenAI Learning Tutor
**Audit Date:** 2026-06-17
**Scope:** Backend agent system, LLM integration, RAG pipeline, MCP server

---

## Executive Summary

This audit evaluated the Adaptive GenAI Learning Tutor application against the OWASP Top 10 for LLM Applications 2025. The system is a deep-agent orchestrator using Qwen LLM models, with local corpus retrieval (RAG), MCP tool exposure, and multi-tenant support.

**Overall Risk Level:** MEDIUM-HIGH

| Severity | Count |
|----------|-------|
| Critical | 1 |
| High | 7 |
| Medium | 19 |
| Low | 7 |
| Info | 3 |
| **TOTAL** | **37** |

---

## LLM01: Prompt Injection

### LLM-001: Direct Prompt Injection in Orchestrator
- **Severity:** CRITICAL
- **Confidence:** HIGH
- **Files:** `backend/agent.py:138-177`, `backend/agent_runtime.py:214`
- **Evidence:**
```python
def run_tutor_turn(learner_id: str, message: str, ...):
    return _invoke({"messages": [{"role": "user", "content": message}]}, ...)
```
User input flows directly into orchestrator without sanitization.
- **Impact:** Attackers can inject prompts to bypass grounding rules, manipulate tool calling, or extract system prompt content.
- **Remediation:** Implement input content filtering; add pre-processing layer; use structured message formats.
- **CWE:** CWE-94 (Improper Control of Generation of Code)

### LLM-002: Subagent Prompt Injection via Delegated Tasks
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/agent.py:87-136`
- **Evidence:** All subagents receive instructions incorporating user context without sanitization.
- **Impact:** Subagent behavior manipulation; cross-subagent injection attacks.
- **Remediation:** Validate parameters before delegation; use parameter allowlists.
- **CWE:** CWE-94 (Improper Control of Generation of Code)

### LLM-003: Indirect Prompt Injection via Corpus Content
- **Severity:** HIGH
- **Confidence:** MEDIUM
- **Files:** `backend/tools.py:45-51`
- **Evidence:** RAG pipeline retrieves corpus content without sanitization before LLM ingestion.
- **Impact:** Malicious content in corpus could inject instructions.
- **Remediation:** Sanitize retrieved content; implement content validation on ingestion.
- **CWE:** CWE-94 (Improper Control of Generation of Code)

### LLM-004: MCP Tool Prompt Injection
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `mcp_server/server.py:428-467`
- **Evidence:** `ask_tutor` MCP tool passes unsanitized messages to agent.
- **Impact:** MCP clients can inject prompts bypassing web UI scrutiny.
- **Remediation:** Apply same input validation to MCP tools as web endpoints.
- **CWE:** CWE-94 (Improper Control of Generation of Code)

---

## LLM02: Sensitive Information Disclosure

### LLM-005: API Keys in Environment Variables
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/settings.py:227`
- **Evidence:** `QWEN_API_KEY`, `LANGSMITH_API_KEY` read from env without encryption.
- **Impact:** Keys exposed in process listings, error messages, or logs.
- **Remediation:** Use dedicated secrets management; implement key rotation.
- **CWE:** CWE-312 (Cleartext Storage of Sensitive Information)

### LLM-006: User PII in LLM Responses
- **Severity:** MEDIUM
- **Confidence:** MEDIUM
- **Files:** `backend/tools.py:520-662`
- **Evidence:** User answers stored and logged verbatim; may contain PII.
- **Impact:** GDPR/privacy compliance violations; data breach risk.
- **Remediation:** Implement PII detection and redaction; add consent tracking.
- **CWE:** CWE-359 (Exposure of Private Information)

### LLM-007: System Prompts in Debug/Error Messages
- **Severity:** MEDIUM
- **Confidence:** LOW
- **Files:** `backend/agent.py:138-177`
- **Evidence:** Static prompts could be exposed through error messages or debug logging.
- **Impact:** Attackers can study prompts to craft better injections.
- **Remediation:** Never log system prompts in production; implement error sanitization.
- **CWE:** CWE-200 (Information Exposure)

### LLM-008: Learner Progress Data Exposure via URL
- **Severity:** LOW
- **Confidence:** HIGH
- **Files:** `backend/main.py:262-265`
- **Evidence:** `learner_id` in URL path exposed in logs, browser history, referrers.
- **Impact:** Learner IDs could be harvested for enumeration.
- **Remediation:** Use POST with body parameters for sensitive identifiers.
- **CWE:** CWE-598 (Information Exposure Through Query Strings)

---

## LLM03: Supply Chain

### LLM-009: Third-Party LLM Provider Dependency
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/llm_provider.py:1-176`
- **Evidence:** Hard dependency on Qwen/DashScope API for orchestration.
- **Impact:** Service disruption; data exfiltration; vendor lock-in.
- **Remediation:** Implement multi-provider fallback; add circuit breakers.
- **CWE:** CWE-1104 (Use of Unmaintained Third Party Components)

### LLM-010: No Model Integrity Verification
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/llm_provider.py:74-111`
- **Evidence:** No verification of model version, checksums, or integrity.
- **Impact:** No detection if provider switches model versions.
- **Remediation:** Implement model version tracking; add response validation.
- **CWE:** CWE-354 (Improper Validation of Integrity Check Value)

### LLM-011: Unverified Corpus Data Supply Chain
- **Severity:** MEDIUM
- **Confidence:** MEDIUM
- **Files:** `backend/corpus.py`
- **Evidence:** Corpus data loaded without cryptographic verification.
- **Impact:** Corpus poisoning if build pipeline is compromised.
- **Remediation:** Implement corpus signing and verification.
- **CWE:** CWE-494 (Download of Code Without Integrity Check)

---

## LLM04: Data and Model Poisoning

### LLM-012: User Content Potential Training Risk
- **Severity:** LOW
- **Confidence:** MEDIUM
- **Files:** `backend/tools.py:520-662`
- **Evidence:** User answers stored; could be used for future training/fine-tuning.
- **Impact:** Model degradation if poisoned data used for training.
- **Remediation:** Never use raw user input for training without review.
- **CWE:** CWE-20 (Improper Input Validation)

### LLM-013: No Input Validation on Corpus Building
- **Severity:** INFO
- **Confidence:** MEDIUM
- **Files:** `build_genai_research_corpus.py`
- **Evidence:** Corpus building processes external data without validation.
- **Impact:** Malicious content could poison knowledge base.
- **Remediation:** Implement content validation in corpus pipeline.
- **CWE:** CWE-20 (Improper Input Validation)

---

## LLM05: Improper Output Handling

### LLM-014: Unescaped LLM Output in API Responses
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/agent_runtime.py:68-75`
- **Evidence:** LLM responses returned directly without sanitization.
- **Impact:** XSS if frontend doesn't escape; malicious markdown injection.
- **Remediation:** Implement output sanitization; use CSP headers.
- **CWE:** CWE-79 (Cross-site Scripting)

### LLM-015: Code Execution Risk in Coach Notes
- **Severity:** LOW
- **Confidence:** LOW
- **Files:** `backend/tools.py:665-693`
- **Evidence:** LLM-generated coaching notes not validated for dangerous patterns.
- **Impact:** Command injection if rendered in unsafe contexts.
- **Remediation:** Add content filtering; blocklist dangerous patterns.
- **CWE:** CWE-94 (Improper Control of Generation of Code)

### LLM-016: Unbounded Tool Output in Streaming
- **Severity:** MEDIUM
- **Confidence:** MEDIUM
- **Files:** `backend/main.py:165-223`
- **Evidence:** Streaming endpoint sends LLM outputs via SSE without size limits.
- **Impact:** Client buffer exhaustion; DoS through massive responses.
- **Remediation:** Implement response size limits; add streaming rate limiting.
- **CWE:** CWE-400 (Uncontrolled Resource Consumption)

---

## LLM06: Excessive Agency

### LLM-017: Weak HITL Gate on Consequential Actions
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/agent_tools.py:144-158`, `backend/agent.py:190`
- **Evidence:** `commit_progress` has interrupt gate but state write may execute before approval.
- **Impact:** Consequential write could happen without proper approval.
- **Remediation:** Move state-mutating code after interrupt check; add approval validation.
- **CWE:** CWE-862 (Missing Authorization)

### LLM-018: Unrestricted Tool Access by Orchestrator
- **Severity:** MEDIUM
- **Confidence:** MEDIUM
- **Files:** `backend/agent.py:185`
- **Evidence:** Orchestrator has access to sensitive tools without additional restrictions.
- **Impact:** Prompt injection could trigger unauthorized tool calls.
- **Remediation:** Implement tool-level authorization; add usage quotas.
- **CWE:** CWE-269 (Improper Privilege Management)

### LLM-019: MCP Tools Grant Cross-Tenant Access
- **Severity:** HIGH
- **Confidence:** MEDIUM
- **Files:** `mcp_server/server.py:35-68`
- **Evidence:** `_require_mcp_access` relies on user-provided tenant_id.
- **Impact:** Cross-tenant data access by malicious educators.
- **Remediation:** Implement tenant-scoped authentication; validate from JWT claims.
- **CWE:** CWE-285 (Improper Authorization)

---

## LLM07: System Prompt Leakage

### LLM-020: Static System Prompts Vulnerable to Extraction
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/agent.py:138-177`, `backend/grounding/genai_tutor.md`
- **Evidence:** System prompts are static and comprehensive; extractable via various techniques.
- **Impact:** Attackers can study prompts to craft better injections.
- **Remediation:** Implement prompt rotation; add obfuscation; monitor extraction attempts.
- **CWE:** CWE-200 (Information Exposure)

### LLM-021: Skill Prompts Exposed via Filesystem
- **Severity:** LOW
- **Confidence:** HIGH
- **Files:** `backend/skills/*/SKILL.md`
- **Evidence:** Skill prompts loaded dynamically and exposed to agent.
- **Impact:** Revealing tutoring methodology and evaluation criteria.
- **Remediation:** Encrypt skill files at rest; implement access logging.
- **CWE:** CWE-200 (Information Exposure)

### LLM-022: Subagent Guardrails Reveal Architecture
- **Severity:** INFO
- **Confidence:** HIGH
- **Files:** `backend/agent.py:79-85`
- **Evidence:** `SUBAGENT_FS_GUARDRAIL` tells model what NOT to do, revealing system structure.
- **Impact:** Attackers learn about virtual filesystem, tool names, etc.
- **Remediation:** Use positive instructions; implement technical controls.
- **CWE:** CWE-200 (Information Exposure)

---

## LLM08: Vector and Embedding Weaknesses

### LLM-023: TF-IDF Embeddings Vulnerable to Keyword Stuffing
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/vector_store.py:42-148`
- **Evidence:** Local vector store uses TF-IDF, vulnerable to keyword manipulation.
- **Impact:** Corpus poisoning; search result manipulation; adversarial queries.
- **Remediation:** Add anomaly detection; consider semantic embeddings.
- **CWE:** CWE-20 (Improper Input Validation)

### LLM-024: No Embedding Security Boundaries
- **Severity:** LOW
- **Confidence:** MEDIUM
- **Files:** `backend/vector_store.py:176-218`
- **Evidence:** Search operates across all documents without tenant isolation.
- **Impact:** Potential cross-tenant leakage if corpus becomes multi-tenant.
- **Remediation:** Add tenant_id to metadata and filter during search.
- **CWE:** CWE-200 (Information Exposure)

### LLM-025: Predictable Query Expansion
- **Severity:** INFO
- **Confidence:** HIGH
- **Files:** `backend/vector_store.py:25-31`
- **Evidence:** `QUERY_EXPANSIONS` rules are static and predictable.
- **Impact:** Attackers can craft queries to manipulate search rankings.
- **Remediation:** Use learned query expansion; add randomization.
- **CWE:** CWE-20 (Improper Input Validation)

---

## LLM09: Misinformation

### LLM-026: Source Citation Not Cryptographically Verified
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/tools.py:28-42`
- **Evidence:** Source references trusted without verification; grounding relies on prompt compliance.
- **Impact:** LLM could hallucinate and cite non-existent sources.
- **Remediation:** Implement post-generation citation verification; add hallucination detection.
- **CWE:** CWE-345 (Insufficient Verification of Data Authenticity)

### LLM-027: No Factual Consistency Checks
- **Severity:** MEDIUM
- **Confidence:** MEDIUM
- **Files:** `backend/agent_runtime.py:68-75`
- **Evidence:** LLM outputs accepted without consistency validation.
- **Impact:** Contradictory information; hallucinated course details.
- **Remediation:** Implement claim extraction and verification; cross-check against corpus.
- **CWE:** CWE-345 (Insufficient Verification of Data Authenticity)

### LLM-028: Weak Grounding Enforcement in Subagents
- **Severity:** LOW
- **Confidence:** MEDIUM
- **Files:** `backend/agent.py:87-136`
- **Evidence:** Grounding instructions use "as needed" language; no technical enforcement.
- **Impact:** Subagents may generate responses without retrieving sources.
- **Remediation:** Require tool calls before text generation; validate source retrieval.
- **CWE:** CWE-20 (Improper Input Validation)

---

## LLM10: Unbounded Consumption

### LLM-029: No Token Limit Per User
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/llm_provider.py:74-111`
- **Evidence:** `max_tokens=800` is per-call; no accumulation tracking across sessions.
- **Impact:** Cost explosion; DoS via resource exhaustion; budget overruns.
- **Remediation:** Implement per-user token budgets; track cumulative usage.
- **CWE:** CWE-770 (Allocation of Resources Without Limits)

### LLM-030: Recursion Limit Allows Excessive LLM Calls
- **Severity:** HIGH
- **Confidence:** HIGH
- **Files:** `backend/agent_runtime.py:32`
- **Evidence:** `RECURSION_LIMIT = 80` could result in hundreds of LLM calls per request.
- **Impact:** Massive API costs; timeout issues; provider rate limiting.
- **Remediation:** Reduce to 20-30; implement cost estimation; add circuit breakers.
- **CWE:** CWE-674 (Uncontrolled Recursion)

### LLM-031: No Rate Limiting on Internal Tool Calls
- **Severity:** MEDIUM
- **Confidence:** MEDIUM
- **Files:** `backend/tools.py:45-51`
- **Evidence:** Internal tool calls (e.g., corpus search) have no rate limiting.
- **Impact:** LLM could trigger hundreds of search calls; memory exhaustion.
- **Remediation:** Add internal rate limiting; implement search result caching.
- **CWE:** CWE-770 (Allocation of Resources Without Limits)

### LLM-032: Unbounded Streaming Response Duration
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Files:** `backend/main.py:165-223`
- **Evidence:** Streaming endpoint has no timeout; waits until agent completes.
- **Impact:** Long-lived connections exhausting server resources; DoS.
- **Remediation:** Add server-side timeout; implement heartbeat limits.
- **CWE:** CWE-400 (Uncontrolled Resource Consumption)

### LLM-033: No Context Window Management
- **Severity:** MEDIUM
- **Confidence:** MEDIUM
- **Files:** `backend/agent_runtime.py:176-205`
- **Evidence:** Agent accumulates messages without pruning; history grows unbounded.
- **Impact:** Context window overflow; degraded performance; increased costs.
- **Remediation:** Implement conversation summarization; prune old messages.
- **CWE:** CWE-770 (Allocation of Resources Without Limits)

### LLM-034: Weak Rate Limiting Configuration
- **Severity:** LOW
- **Confidence:** HIGH
- **Files:** `backend/settings.py:115-121`
- **Evidence:** Limits are high (60 chat/min, 120 search/min) and easily abusable.
- **Impact:** Easy to exhaust resources within limits.
- **Remediation:** Reduce limits; implement adaptive rate limiting.
- **CWE:** CWE-770 (Allocation of Resources Without Limits)

---

## Summary by Category

| Category | Critical | High | Medium | Low | Info |
|----------|----------|------|--------|-----|------|
| LLM01: Prompt Injection | 1 | 2 | 1 | 0 | 0 |
| LLM02: Sensitive Info | 0 | 1 | 3 | 1 | 0 |
| LLM03: Supply Chain | 0 | 1 | 2 | 0 | 0 |
| LLM04: Poisoning | 0 | 0 | 0 | 1 | 1 |
| LLM05: Output Handling | 0 | 0 | 3 | 1 | 0 |
| LLM06: Excessive Agency | 0 | 1 | 2 | 0 | 0 |
| LLM07: Prompt Leakage | 0 | 0 | 1 | 1 | 1 |
| LLM08: Vector/Embedding | 0 | 0 | 1 | 1 | 1 |
| LLM09: Misinformation | 0 | 0 | 2 | 1 | 0 |
| LLM10: Unbounded Consumption | 0 | 2 | 4 | 1 | 0 |
| **TOTAL** | **1** | **7** | **19** | **7** | **3** |

---

## Regression Tests Required

1. **Prompt injection detection tests:** Common injection patterns rejected
2. **Grounding validation tests:** Responses include valid citations
3. **Token budget tests:** Users cannot exceed allocated tokens
4. **Recursion limit tests:** Graceful degradation at limit
5. **Citation verification tests:** All cited sources exist in corpus

---

**End of Report**
