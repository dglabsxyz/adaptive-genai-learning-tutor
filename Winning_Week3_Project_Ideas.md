# Winning Week 3 Project Ideas

> Alternative project concepts that exceed the scope, impact, and originality of the repository’s sample projects (Employee Assistant, GTM Deep Agent, MCP Course Platform).

The original Week 3 examples are excellent teaching vehicles, but they are intentionally narrow:
- **Employee Assistant** — two request types inside a single organization.
- **GTM Deep Agent** — content drafting in one brand voice.
- **MCP Course Platform** — four intent tools over a local JSON file.

The ideas below keep the same Week 3 technical requirements (LangGraph, `create_agent`, multi-agent composition, Deep Agents, MCP, HITL, persistence) but apply them to harder, more valuable problems. Each one is designed to be demoable in under 10 minutes while still outperforming both low-code chatbot projects and code-heavy projects that lack a clear product story.

---

## Evaluation Criteria for a Winning Project

A Week 3 winner should score highly on all five dimensions:

| Dimension | What Judges Look For |
|---|---|
| **Originality** | Not a clone of the course examples; a fresh domain or surprising twist. |
| **Technical Depth** | Uses multiple Week 3 patterns together, not just one. |
| **Problem-Solving Depth** | Handles ambiguity, missing info, invalid requests, and safety gates gracefully. |
| **Real-World Relevance** | Solves a problem someone actually pays to solve. |
| **Demo Clarity** | A 5–10 minute walkthrough with a happy path, a failure path, a HITL moment, and visible proof. |

The proposals below are selected so that each hits at least four of the five dimensions strongly.

---

## Idea 1: Agentic Research & Synthesis Platform

### One-line pitch
A multi-agent research assistant that accepts a topic, plans an investigation, searches the web, evaluates source credibility, synthesizes conflicting claims, and produces a cited report with an optional human approval gate before publishing.

### Why it surpasses the original
| Factor | Original | This Idea |
|---|---|---|
| Domain | HR admin tasks | Knowledge work (research, journalism, strategy) |
| Agent count | 1–2 specialists | 4–6 specialists (planner, searcher, extractor, fact-checker, synthesizer, editor) |
| Output | Short text answer | Structured report with citations and confidence scores |
| Real-world value | Saves HR clicks | Saves hours of manual research and reduces misinformation |

### Architecture highlights
- **Orchestrator** (Deep Agents or supervisor LangGraph) breaks the brief into sub-tasks.
- **Researcher subagent** uses `langchain-tavily` or similar for web search.
- **Extractor subagent** pulls claims, quotes, and metadata from pages.
- **Fact-checker subagent** cross-references claims across sources and flags contradictions.
- **Synthesizer subagent** drafts the final report.
- **Editor / linter subagent** enforces citation format and readability rules.
- **HITL gate** pauses before final publish so the human can approve or redirect.
- **MCP layer** exposes intent tools such as `research_topic`, `get_source_details`, and `publish_report`.

### Week 3 patterns demonstrated
- Deep Agents planning + delegation
- Subagent isolation with shared artifact files
- RAG-like retrieval over fetched web pages
- Skills for citation style / report format
- Cross-session memory for learned source-quality preferences
- MCP intent tools with fuzzy topic resolution
- `interrupt()` for approval before publishing

### Why it wins
This idea beats **low-code participants** because it cannot be built as a single-prompt chatbot: it requires persistent state, multi-turn planning, source evaluation, and structured output. It beats **code-heavy participants** because the engineering serves a clear user outcome (a trustworthy report), not complexity for its own sake. The demo is visually compelling: you can show the agent disagreeing with itself and resolving contradictions.

---

## Idea 2: AI Software Development Agent Team

### One-line pitch
A coordinated team of agents that takes a product request, writes a design doc, generates code, runs tests, reviews the pull request, and iterates until the feature passes — with human approval at every expensive or irreversible step.

### Why it surpasses the original
| Factor | Original | This Idea |
|---|---|---|
| Domain | HR / content ops | Software engineering |
| Agent count | 1–2 | 5+ (PM, architect, coder, tester, reviewer, security auditor) |
| Workflow | Single-turn or short loop | Multi-iteration loop with feedback |
| Tooling | Mock backends | Real file system, shell commands, test runner, git |

### Architecture highlights
- **Product Manager subagent** clarifies requirements via `interrupt()` when the spec is vague.
- **Architect subagent** produces a design doc and selects implementation strategy.
- **Coder subagent** generates code in focused files.
- **Tester subagent** writes and runs unit tests; reports failures back to the coder.
- **Reviewer subagent** checks style, security, and design compliance.
- **Human gate** before any file write, test execution, or git commit.
- **Shared filesystem** (`/design`, `/src`, `/tests`, `/reviews`) lets agents pass artifacts.
- **MCP server** exposes intent tools like `plan_feature`, `implement_task`, `run_tests`, and `merge_pr`.

### Week 3 patterns demonstrated
- Router or supervisor multi-agent composition
- Deep Agents orchestration with shared state
- Iterative ReAct loop across multiple agents
- Deterministic validation (tests, linters) alongside LLM reasoning
- Long-term memory for team conventions and codebase style
- MCP intent layer over a local codebase
- HITL at destructive actions

### Why it wins
This is one of the most competitive demo categories in any AI hackathon. It beats **low-code participants** because it requires real tool execution, file I/O, and a feedback loop. It beats **code-heavy participants** by narrowing the scope to a single feature end-to-end rather than a vague "code anything" system, making the demo coherent and the safety gates believable.

---

## Idea 3: Intelligent Incident Response Assistant

### One-line pitch
An SRE assistant that ingests logs and alerts, diagnoses root cause, proposes remediation runbooks, and executes approved fixes — while refusing risky actions and escalating when confidence is low.

### Why it surpasses the original
| Factor | Original | This Idea |
|---|---|---|
| Domain | Internal admin | Site reliability / DevOps |
| Input | Natural language only | Structured alerts + unstructured logs |
| Stakes | Low (leave balance) | High (production uptime) |
| Safety model | Interrupt for missing dates | Approval for every remediation action |

### Architecture highlights
- **Ingestion agent** fetches alerts from a monitoring API or reads local log files.
- **Diagnosis agent** performs agentic RAG over incident runbooks and past post-mortems.
- **Severity classifier** routes critical alerts to a human immediately.
- **Remediation agent** proposes a runbook step and pauses for `interrupt()` approval.
- **Executor subagent** runs only approved shell/API commands inside a sandbox.
- **Post-incident agent** drafts a timeline and post-mortem.
- **MCP tools**: `investigate_alert`, `get_runbook`, `propose_fix`, `apply_fix`, `escalate_oncall`.

### Week 3 patterns demonstrated
- Structured + unstructured input handling
- Agentic RAG over runbooks and incident history
- Multi-agent composition with a severity router
- HITL middleware for every write/remediation action
- Stateful incident threads via checkpointer
- MCP intent layer over monitoring and remediation APIs

### Why it wins
High-impact domains win hackathons when executed safely. This beats **low-code participants** because it integrates real data sources and requires deterministic safety checks. It beats **code-heavy participants** because the safety narrative is central: the best demo moment is the assistant refusing to restart a production database without approval.

---

## Idea 4: Adaptive Personalized Learning Tutor

### One-line pitch
A tutoring agent that assesses a learner’s knowledge gaps, builds a personalized study plan, generates practice problems, evaluates answers with explanations, and adapts difficulty in real time.

### Why it surpasses the original
| Factor | Original | This Idea |
|---|---|---|
| User | Employee / marketer | Student / lifelong learner |
| Interaction | Transactional request | Long-term adaptive relationship |
| Memory | Thread-only | Cross-session knowledge model |
| Output | Single answer or draft | Personalized curriculum + feedback loop |

### Architecture highlights
- **Diagnostic subagent** asks calibrated questions and estimates skill levels per topic.
- **Planner subagent** builds a study schedule with milestones.
- **Problem-writer subagent** generates exercises at the right difficulty.
- **Grader subagent** evaluates answers, gives hints, and updates the learner model.
- **Coach subagent** motivates and adjusts study plans based on progress.
- **Long-term memory** (`Store`) persists concept mastery across sessions.
- **MCP tools**: `assess_skills`, `get_next_exercise`, `submit_answer`, `view_progress`, `adjust_goal`.

### Week 3 patterns demonstrated
- Multi-turn diagnostic interview with `interrupt()`
- Agentic state machine for skill mastery
- Structured output for learner models and exercise schemas
- Cross-session memory via `Store`
- Subagent delegation with isolated pedagogical prompts
- MCP intent layer over a learning record store

### Why it wins
Education is a universally understood, high-value domain. This beats **low-code participants** because adaptation requires persistent learner state and a structured feedback loop. It beats **code-heavy participants** because the product story is immediately clear: show the tutor getting harder problems right after the student masters basics.

---

## Idea 5: Regulatory Compliance & Contract Review Agent

### One-line pitch
A compliance agent that reads contracts, compares them against a regulatory framework, flags risks, suggests redline edits, and generates a human-ready memo — with full traceability to specific clauses.

### Why it surpasses the original
| Factor | Original | This Idea |
|---|---|---|
| Domain | HR / education | Legal / compliance |
| Input | Short messages | Long, dense documents |
| Reasoning | Simple policy lookup | Multi-document comparison and risk scoring |
| Output | Status message | Audit-ready memo with citations |

### Architecture highlights
- **Ingestion agent** parses PDF/DOCX contracts into chunks.
- **Mapping agent** aligns contract clauses to regulation articles.
- **Risk classifier** scores each clause (low / medium / high) with rationale.
- **Redline agent** proposes edits that bring clauses into compliance.
- **Memo agent** writes an executive summary with citations.
- **HITL gate** requires approval before any redline is accepted.
- **MCP tools**: `review_contract`, `compare_to_regulation`, `get_risk_summary`, `suggest_redline`, `export_memo`.

### Week 3 patterns demonstrated
- Document chunking and retrieval over legal/regulatory texts
- Structured output for risk scoring
- Multi-agent pipeline (ingest → map → score → edit → summarize)
- Deterministic validation of required clauses
- Human approval before write actions
- MCP intent tools that accept document names, not IDs

### Why it wins
Compliance is expensive and error-prone; an agent that reduces legal review time is immediately valuable. This beats **low-code participants** because document comparison and citation generation require retrieval, structured output, and state management. It beats **code-heavy participants** because the demo can show concrete risk reduction, not just parsing.

---

## Comparative Summary

| Idea | Originality | Technical Depth | Problem Depth | Real-World Value | Best Demo Moment |
|---|---|---|---|---|---|
| Agentic Research Platform | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Agent resolves conflicting sources live |
| AI Dev Team | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Code/test loop passes after iteration |
| Incident Response Assistant | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Refuses risky fix until approved |
| Adaptive Learning Tutor | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Difficulty adapts to student answers |
| Compliance & Contract Review | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Generates cited risk memo from contract |

*Scale: 1–5 stars. All five ideas score 4+ on every dimension, whereas the original sample projects average 2–3 on originality and real-world value outside their teaching context.*

---

## How to Pick One

| If you want to emphasize… | Choose |
|---|---|
| Search + synthesis + credibility | **Agentic Research Platform** |
| Tool use + iteration + code generation | **AI Dev Team** |
| Safety + high-stakes operations | **Incident Response Assistant** |
| Long-term adaptation + education | **Adaptive Learning Tutor** |
| Document understanding + legal risk | **Compliance & Contract Review** |

---

## Final Advice for Outperforming the Field

1. **Low-code participants** will build single-prompt assistants or simple CRUD wrappers. Beat them by showing **state, loops, and multiple agents** working together.
2. **Code-heavy participants** will build impressive plumbing with unclear value. Beat them by tying every technical choice to a **user-visible outcome**.
3. **Winning demos** always include:
   - A happy path that completes an end-to-end job.
   - A missing-information or ambiguous request that triggers `interrupt()`.
   - A guarded action that pauses or refuses.
   - A visible artifact: report, code, test output, UI update, or memo.

Pick the idea closest to a problem you personally understand, then scope it ruthlessly so the demo fits in 10 minutes.
