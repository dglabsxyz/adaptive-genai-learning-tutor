# Improved OWASP Security Audit Prompt

You are my authorized security testing and remediation assistant. Work only on the local project I provide and only in non-production environments. Do not test, scan, attack, crawl, or send malicious payloads to any third-party or production target unless I explicitly provide written authorization and a safe test URL.

I have an OWASP security testing plugin available with capabilities for web application, LLM application, and agentic AI security testing. If a referenced plugin skill is unavailable, say which skill is missing, continue with safe manual analysis where possible, and mark unsupported test areas as `UNTESTED`.

Your mission: audit this project against the OWASP frameworks below, in order, then wait for explicit approval before making any remediation changes.

## Phase 0: Scope, Safety, and Source Verification

1. Confirm the project path, environment, and authorization scope.
2. Identify whether the project includes:
   - a traditional web application or API
   - LLM features such as prompts, RAG, embeddings, model calls, evals, or AI output handling
   - agentic features such as tools, orchestration, autonomous plans, memory, MCP servers, or multi-agent workflows
3. Verify the current OWASP category names from authoritative OWASP sources before testing. Use the latest applicable released frameworks unless I explicitly request a specific year.
4. Create a working branch or restore point before any generated tests or remediation. Do not copy secrets, `.env` files, dependency folders, build artifacts, virtual environments, or database dumps into backups.

## Phase 1: Discovery and Baseline

1. Identify the tech stack, frameworks, entry points, trust boundaries, data stores, auth flows, external integrations, and existing test suite.
2. Run the existing tests and record the baseline command, pass/fail count, and notable failures.
3. If no tests exist, do not modify source code yet. Instead, create `security-test-plan.md` describing the minimum regression tests needed before remediation.
4. Record assumptions, skipped areas, and required credentials or environment variables without exposing secret values.

## Phase 2: Read-Only Sequential Audit

Run read-only analysis in this exact order. Do not edit source code, dependencies, configs, prompts, data, or infrastructure during this phase.

### A. OWASP Top 10 Web Application Security Risks

Use the latest official OWASP Top 10 Web list, currently OWASP Top 10:2025 unless superseded. Include all applicable categories:

- A01 Broken Access Control
- A02 Security Misconfiguration
- A03 Software Supply Chain Failures
- A04 Cryptographic Failures
- A05 Injection
- A06 Insecure Design
- A07 Authentication Failures
- A08 Software or Data Integrity Failures
- A09 Security Logging and Alerting Failures
- A10 Mishandling of Exceptional Conditions

Output: `owasp-web-audit-report.md`

### B. OWASP Top 10 for LLM and Generative AI Applications

Use the latest official OWASP LLM Top 10 list, currently the 2025 list unless superseded. Include all applicable categories:

- LLM01 Prompt Injection
- LLM02 Sensitive Information Disclosure
- LLM03 Supply Chain
- LLM04 Data and Model Poisoning
- LLM05 Improper Output Handling
- LLM06 Excessive Agency
- LLM07 System Prompt Leakage
- LLM08 Vector and Embedding Weaknesses
- LLM09 Misinformation
- LLM10 Unbounded Consumption

Output: `owasp-llm-audit-report.md`

### C. OWASP Top 10 for Agentic Applications

Use the latest official OWASP Agentic Applications list, currently the 2026 list unless superseded. Include all applicable categories:

- ASI01 Agent Goal Hijack
- ASI02 Tool Misuse and Exploitation
- ASI03 Identity and Privilege Abuse
- ASI04 Agentic Supply Chain Vulnerabilities
- ASI05 Unexpected Code Execution
- ASI06 Memory and Context Poisoning
- ASI07 Insecure Inter-Agent Communication
- ASI08 Cascading Failures
- ASI09 Human-Agent Trust Exploitation
- ASI10 Rogue Agents

Output: `owasp-agentic-audit-report.md`

For every finding, record:

- finding ID
- OWASP category and version
- severity and confidence
- affected file, endpoint, prompt, model path, tool, agent, config, or dependency
- evidence from code, tests, config, logs, or safe local reproduction
- impact and realistic exploit scenario
- CWE, CVE, or other mapping when available
- remediation recommendation
- regression tests required

If a category is not applicable, mark it `NOT APPLICABLE` with justification. If safe testing is not possible, mark it `UNTESTED - REQUIRES MANUAL VALIDATION` with justification. Do not run destructive payloads, persistence tests, credential attacks, or production scans.

## Phase 3: Consolidated Risk Analysis

1. Merge the three reports into `master-security-report.md`.
2. Deduplicate overlapping findings across Web, LLM, and Agentic categories.
3. Prioritize by severity, exploitability, confidence, and blast radius.
4. For each finding, include exact change locations, fix approach, risk of functional regression, required tests, and rollback notes.

## Phase 4: Mandatory Approval Gate

Stop after presenting `master-security-report.md`. Ask me exactly:

`Do you want me to proceed with automated remediation? Reply with REMEDIATE ALL, REMEDIATE CRITICAL-HIGH ONLY, REMEDIATE [ID], or STOP.`

Do not proceed to remediation until I explicitly approve one of those options.

## Phase 5: Remediation Protocol, If Approved

1. Fix only approved findings.
2. Work one finding at a time.
3. Prefer the smallest behavior-preserving change that removes or reduces the risk.
4. Add or update regression tests for each fix.
5. Run the relevant focused tests after each change, then the full test suite when practical.
6. If a fix breaks functionality, pause that finding, document the failure in `remediation-log.md`, and either revert only your change or ask for approval before attempting a broader fix.
7. For dependency updates, inspect release notes or changelogs, pin versions, and test integration paths.
8. For prompt changes, preserve the old prompt, version the new prompt, and validate expected outputs against representative examples.
9. For access-control changes, test allowed and denied flows with fresh sessions.
10. Update `remediation-log.md` after each finding with finding ID, changed files, test results, remaining risk, and rollback status.

## Phase 6: Final Validation

After approved remediations:

1. Re-run the full test suite and compare it with the Phase 1 baseline.
2. Re-run targeted security checks only on remediated areas.
3. Generate `final-security-summary.md` listing resolved findings, deferred findings, manual validation items, tests run, and residual risks.

## Safety Overrides

Stop and ask for human review before making or continuing any change that would:

- delete or migrate data
- disable authentication, authorization, logging, monitoring, validation, or encryption
- weaken tenant isolation or access control
- expose secrets or sensitive data
- alter production infrastructure
- modify generated vendor/framework files directly
- cause cascading failures across unrelated components

Begin with Phase 0 now.
