# Adaptive GenAI Learning Tutor — Comprehensive Plan

> A Week 3 project proposal that applies LangGraph, Deep Agents, MCP, agentic RAG, and cross-session memory to build an adaptive tutor over the local `genai_research` corpus. This document contains the PRD, architecture, design-pattern map, research-corpus integration plan, and demo strategy.

---

## 1. Product Requirements Document (PRD)

### 1.1 Vision

Build an **AI-powered adaptive GenAI learning tutor** that behaves like a human tutor for learners studying modern generative AI. It diagnoses what a learner already knows about LLMs, prompt engineering, RAG, agents, MCP, AI coding, product development, multimodal AI, and evaluation; builds a personalized path through the local course-research corpus; generates source-grounded practice tasks; explains mistakes; and continuously adapts difficulty. Unlike a chatbot that answers one question at a time, the tutor maintains a long-term learner model across sessions and optimizes for mastery of the researched GenAI curriculum.

### 1.2 Core Value Proposition

- **For learners:** A tutor that turns a broad GenAI course catalog into a focused path, remembers strengths and weaknesses, and explains *why* an answer or design choice is incomplete.
- **For educators/course operators:** A source-grounded way to personalize GenAI upskilling using an auditable local corpus instead of an opaque generic chatbot.
- **For demo judges:** A clear, visual product story — the system diagnoses GenAI skills, retrieves course-backed material, adapts exercises, pauses for clarification, and remembers progress across restarts.

### 1.3 Core Features

| Feature | Description | User Story |
|---|---|---|
| **Adaptive Diagnostic Assessment** | Multi-turn interview that estimates proficiency per skill/concept. | As a learner, I want the tutor to quickly figure out what I already know so I don't waste time on easy material. |
| **Research-Corpus Grounding** | Uses `genai_research` as the primary course material and cites topic, course, instructor, and source records. | As a learner, I want recommendations and explanations grounded in the actual researched courses. |
| **Personalized Study Plan** | Generates a sequenced GenAI learning plan with milestones based on diagnostic results, goals, and topic dependencies. | As a learner, I want a clear roadmap of what to study next. |
| **Dynamic Exercise Generation** | Creates source-backed exercises calibrated to the learner's current level in real time. | As a learner, I want practice that uses real course themes and is challenging without being random. |
| **Intelligent Answer Evaluation** | Grades open-ended and multiple-choice answers and provides explanations. | As a learner, I want to understand my mistakes, not just see a score. |
| **Real-Time Difficulty Adaptation** | Adjusts difficulty up or down based on performance streaks and error patterns. | As a learner, I want the tutor to keep me in the optimal learning zone. |
| **Cross-Session Memory** | Persists learner model, history, and preferences across conversations. | As a returning learner, I want the tutor to remember where I left off. |
| **Goal Management** | Allows learners to set, view, and adjust learning goals. | As a learner, I want to change my target exam date or topic focus. |
| **MCP-Enabled Assistant Access** | Exposes tutor capabilities to external AI clients (Claude Code, Desktop, Codex) via MCP. | As a power user, I want to interact with my tutor through my preferred AI assistant. |

### 1.4 Functional Requirements

#### FR-0: Research Corpus as Source of Truth
- The tutor must use `/Users/dgomez/Week 3 Project/genai_research` as the primary course material.
- It must ingest `research_index.json`, `coverage_report.json`, `topics/*/topic_summary.json`, `courses/*/course_summary.json`, and relevant `instructors/*/instructor_summary.json` records.
- It must preserve null or unknown fields rather than inventing missing prices, dates, ratings, biographies, or enrollment details.
- Every study-plan recommendation, explanatory answer, and generated exercise must include at least one `source_ref` pointing to a local corpus record or citation URL.
- The corpus is read-only; learner state, plans, generated exercises, and progress live outside `genai_research`.

#### FR-1: Diagnostic Interview
- The diagnostic subagent must conduct a **multi-turn adaptive interview**.
- It selects the next question based on previous answers, not from a fixed list.
- It estimates a proficiency score per skill on a 0–1 scale.
- It stops when confidence is high enough or after a configurable maximum number of questions.
- It uses `interrupt()` to ask clarifying questions when learner input is ambiguous.
- It must diagnose against the corpus topic taxonomy: LLMs, prompt engineering, RAG, AI agents, fine-tuning, multimodal AI, AI coding, AI product development, AI safety/evaluation, context engineering, MCP, and related topics discovered in the corpus.

#### FR-2: Personalized Study Plan
- The planner subagent generates a **sequenced study plan** from the diagnostic profile.
- The plan respects GenAI topic dependencies (e.g., LLM fundamentals before prompt engineering, prompt/context engineering before RAG, RAG before agentic RAG, tool use before MCP-enabled agents, evaluation across all build phases).
- The plan includes milestones, estimated completion times, and review checkpoints.
- Learners can adjust goals, and the plan updates.
- Plans must cite the relevant course summaries and topic summaries used to justify each module.

#### FR-3: Exercise Generation
- The problem-writer subagent generates exercises at the learner's current level.
- It supports multiple formats: multiple-choice, short answer, design critique, code-oriented implementation prompt, and agent-architecture scenario.
- It uses structured output schemas for exercises so the frontend can render them reliably.
- It avoids repeating recently seen problem templates.
- It must retrieve from the corpus before generating exercises so prompts reflect actual course topics, syllabi, and constraints.

#### FR-4: Answer Evaluation
- The grader subagent evaluates answers against ground truth or rubrics.
- For open-ended answers, it provides partial credit and detailed explanations.
- It updates the learner model based on correctness, confidence, and time spent.
- It must distinguish factual recall, conceptual explanation, architecture/design judgment, and implementation skill.
- It must flag unsupported claims when the answer contradicts retrieved course or topic summaries.

#### FR-5: Difficulty Adaptation
- The system maintains a **skill mastery state machine** per concept: `exposure → developing → proficient → mastered → review`.
- Transitions are triggered by performance thresholds and spaced-repetition rules.
- Difficulty adjusts within each state to keep the learner in the **zone of proximal development**.

#### FR-6: Cross-Session Persistence
- Learner models are stored in a long-term `Store` and survive thread/conversation restarts.
- Each learner has a stable `learner_id` mapped to their profile.
- Session history is stored via a checkpointer keyed by `thread_id`.

#### FR-7: MCP Tool Exposure
- The system exposes six intent-oriented MCP tools: `tutor_assess_skills`, `tutor_recommend_path`, `tutor_get_next_exercise`, `tutor_submit_answer`, `tutor_view_progress`, `tutor_search_course_material`.
- MCP tools accept human references (e.g., "agentic RAG", "MCP", "AI evals") and resolve them to canonical topic/course IDs.
- Tools return formatted summaries, not raw JSON.

### 1.5 Non-Functional Requirements

| Requirement | Specification |
|---|---|
| **Latency** | Diagnostic question generation < 1s; exercise generation < 2s; answer grading < 2s. |
| **Scalability** | Supports thousands of learners with persistent Postgres checkpointer and store. |
| **Privacy** | Learner data encrypted at rest; no raw prompts logged without consent. |
| **Reliability** | Graceful degradation when LLM calls fail; deterministic validation for schema loading, source references, prerequisite checks, and objective quiz answers. |
| **Extensibility** | New subjects added by dropping a compatible research corpus with topic, course, instructor, source, and coverage summaries. |
| **Safety** | No content generation outside the educational domain; HITL for sensitive actions like deleting progress. |

### 1.6 User Personas

| Persona | Goals | Frustrations |
|---|---|---|
| **Self-Directed Learner (Alex)** | Prepare for a certification exam at their own pace. | Generic courses that repeat material they already know. |
| **Student with Gaps (Maya)** | Catch up on prerequisite GenAI topics before building an agentic project. | One-size-fits-all homework that is either too easy or too hard. |
| **Educator / Admin (Dr. Chen)** | Deploy adaptive practice over a researched course catalog and track progress. | Manual grading and inability to see individual mastery maps. |
| **Power User (Sam)** | Use the tutor inside Claude Code via MCP. | Closed tutoring apps that don't integrate with their workflow. |

### 1.7 Success Metrics

- **Diagnostic efficiency:** Proficiency estimate converges within 8–12 questions.
- **Learning efficiency:** Learners reach proficiency 30% faster than a random-exercise baseline.
- **Grounding quality:** 95%+ of generated plans/exercises include valid local `source_ref` entries.
- **Engagement:** 70%+ of learners return for a second session.
- **Accuracy:** Grader agrees with human expert grading ≥ 85% of the time.
- **Retention:** Spaced-review exercises show ≥ 20% improvement over single-exposure items.

---

## 2. Architecture Outline

### 2.1 High-Level System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                              User Interfaces                             │
│  Web Chat │ React Frontend │ CLI │ Claude Code / Desktop via MCP         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Tutor Orchestrator    │
                    │  (router / supervisor)  │
                    └────────────┬────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │            │           │            │           │
   ┌────▼───┐  ┌────▼───┐ ┌────▼────┐ ┌────▼───┐ ┌────▼───┐
   │Diagnostic│  │Planner │ │Problem- │ │ Grader │ │ Coach  │
   │ subagent│  │subagent│ │ Writer  │ │subagent│ │subagent│
   └────┬───┘  └────┬───┘ └────┬────┘ └────┬───┘ └────┬───┘
        │           │          │           │          │
        └───────────┴──────────┴───────────┴──────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Shared Memory Store   │
                    │  /memories/learner_id   │
                    └─────────────────────────┘
                                 │
        ┌────────────────────────┴────────────────────────┐
        ▼                                                  ▼
┌──────────────────┐                           ┌──────────────────┐
│  Thread State    │                           │  genai_research  │
│  (checkpointer)  │                           │  Retrieval Index │
└──────────────────┘                           └──────────────────┘
```

### 2.2 Research Corpus Integration

The `genai_research` directory is the tutor's read-only course corpus and replaces the generic "curriculum graph" placeholder. The corpus currently contains:

| Corpus Area | Local Path | Tutor Use |
|---|---|---|
| Index | `genai_research/research_index.json` | Entry point for topic, instructor, course/resource, platform, and source records. |
| Coverage | `genai_research/coverage_report.json` | Shows corpus breadth, limitations, platforms, source-quality notes, and required topic coverage. |
| Topics | `genai_research/topics/*/topic_summary.json` | Canonical skill taxonomy, related topics, recommended source courses, and prerequisite hints. |
| Courses | `genai_research/courses/*/course_summary.json` | Primary learning material: course descriptions, target audience, syllabi, topic tags, instructors, and citations. |
| Instructors | `genai_research/instructors/*/instructor_summary.json` | Instructor/course association metadata for recommendations and source transparency. |

The coverage report identifies 17 topics, 67 course or teaching-resource summaries, 72 instructor summaries, 81 source URLs, and 8 platforms. Required topic coverage includes LLMs, prompt engineering, RAG, AI agents, fine-tuning, multimodal AI, AI coding, AI product development, AI automation, business AI, no-code AI, and AI safety/evaluation; additional discovered topics include context engineering and MCP.

**Derived skill graph:**

```text
LLMs
  ├─ prompt engineering
  │    └─ context engineering
  │         └─ RAG
  │              └─ agentic RAG
  ├─ AI coding
  │    └─ tool-using agents
  │         ├─ multi-agent orchestration
  │         └─ MCP
  ├─ fine-tuning
  ├─ multimodal AI
  └─ AI safety and evaluation
       └─ production readiness
```

**Retrieval strategy:**
- Build one document per topic summary, course summary, instructor summary, and coverage/source-quality note.
- Chunk course summaries by `description`, `syllabus`, `target_audience`, `topic_tags`, `prerequisites`, `source_records`, and `citations`.
- Preserve metadata: `record_type`, `slug`, `title`, `platform`, `topic_tags`, `citations`, `path`, and `last_researched_at`.
- Expose retrieval as an agentic tool so the diagnostic, planner, problem-writer, and grader can choose when they need source context.
- Reject or clarify when retrieved fields are null, stale, unsupported, or ambiguous; do not fill gaps by model guesswork.

### 2.3 Subagent Roles & Interactions

#### 2.3.1 Diagnostic Subagent

**Role:** Estimates the learner's current proficiency across all target skills.

**Inputs:**
- `learner_id`
- `subject` or `goal` (e.g., "build production AI agents", "learn RAG", "prepare for a GenAI certification")
- Optional: prior learner model from store
- Retrieved topic and course context from `genai_research`

**Outputs:**
- `LearnerProfile` with per-skill proficiency scores (0–1)
- Confidence level per skill
- List of knowledge gaps ranked by impact

**Behavior:**
- Starts with a coarse question, then adapts based on answers.
- Uses a **decision tree / Bayesian update** approach: if a learner answers a hard question correctly, skip easier siblings.
- Calls `interrupt()` when the learner's answer is ambiguous or off-topic.
- Stores results in `/memories/{learner_id}/profile.json`.
- Uses source-grounded diagnostic probes. Example: ask a beginner to distinguish prompt engineering from RAG; ask an advanced learner to design an agentic RAG loop with evaluation.

**Example interaction:**
```text
Tutor: "In a GenAI app, when would you use RAG instead of fine-tuning?"
Learner: "idk"
Tutor (interrupt): "No problem. Have you already studied embeddings and retrieval, or should we start with LLM application basics?"
```

#### 2.3.2 Planner Subagent

**Role:** Builds and maintains a personalized study plan.

**Inputs:**
- `LearnerProfile`
- `LearningGoal` (target topic, deadline, study time per week)
- Derived GenAI skill graph
- Retrieved course summaries and topic summaries

**Outputs:**
- `StudyPlan` (ordered list of modules with milestones)
- Estimated completion date
- Recommended review schedule

**Behavior:**
- Respects topic prerequisites.
- Prioritizes high-impact gaps.
- Re-runs whenever the learner profile or goal changes.
- Uses skills for planning style (e.g., "exam cram" vs. "deep mastery").
- Selects course/resource records from the corpus as the primary lesson material, favoring source quality, topic match, learner level, and target audience fit.

#### 2.3.3 Problem-Writer Subagent

**Role:** Generates exercises calibrated to the learner's current state.

**Inputs:**
- Target skill ID
- Current difficulty level
- Learner history (recently seen problem types)
- Retrieved topic/course snippets and citations

**Outputs:**
- `Exercise` schema (question, answer rubric, hints, explanation)

**Behavior:**
- Uses structured output so the frontend can render reliably.
- Varies problem templates to avoid repetition.
- Generates plausible distractors for multiple-choice.
- Produces design rubrics, implementation prompts, source-backed explanations, and step-by-step solutions for coding-oriented exercises.
- Includes `source_refs` for the course or topic records used to generate the exercise.

#### 2.3.4 Grader Subagent

**Role:** Evaluates learner answers and updates the learner model.

**Inputs:**
- `Exercise`
- Learner's answer
- `LearnerProfile`
- Retrieved source context used by the exercise

**Outputs:**
- Correctness score (0–1)
- Detailed explanation
- Updated skill mastery state
- Next recommended action (retry, easier problem, move on)

**Behavior:**
- For exact-answer domains (multiple-choice, definitions, simple code checks), uses deterministic checks first, LLM explanation second.
- For open-ended domains, uses rubric-based LLM evaluation.
- Updates the learner model with performance signal, time spent, and confidence.
- Tracks misconceptions such as confusing RAG with fine-tuning, treating MCP as an API wrapper only, omitting tool boundaries in agent design, or failing to mention evals for production systems.

#### 2.3.5 Coach Subagent

**Role:** Motivates, explains, and adapts the emotional/behavioral layer of learning.

**Inputs:**
- Recent performance trend
- Learner goal and deadlines
- Historical struggle/success patterns

**Outputs:**
- Encouraging or redirecting message
- Suggested schedule adjustment
- Optional: break reminder, review prompt

**Behavior:**
- Detects frustration (repeated wrong answers, long response times).
- Suggests easier problems or review.
- Celebrates mastery transitions.
- Uses cross-session memory to reference past achievements.
- Recommends corpus-backed resources for review, such as a topic summary or a specific course module.

### 2.4 Integration with Long-Term Memory Store

The system uses a **Composite Backend** pattern (as seen in the GTM Deep Agent):

```text
/memories/{learner_id}/profile.json      → StoreBackend (cross-session)
/memories/{learner_id}/history.json      → StoreBackend (cross-session)
/memories/{learner_id}/source_refs.json  → StoreBackend (cross-session)
/sessions/{thread_id}/chat_history.json  → FilesystemBackend / checkpointer
/plans/{learner_id}/current_plan.json    → StoreBackend
/corpus/genai_research_index             → read-only retrieval index
```

**Why separate stores?**
- `Store` holds the **learner model** — the persistent representation of what the learner knows.
- `checkpointer` holds the **conversation thread** — ephemeral state for the current session.
- `genai_research` is read-only domain knowledge.
- `source_refs` records which corpus records were used in plans, exercises, and grading.

**Store schema (simplified):**

```python
class LearnerModel(BaseModel):
    learner_id: str
    subject: str  # default: "Generative AI"
    skills: dict[str, SkillState]  # skill_id -> mastery state + proficiency
    goals: list[LearningGoal]
    preferences: dict  # pacing, format, feedback style
    course_progress: dict[str, float]  # course_slug -> 0.0 - 1.0
    corpus_snapshot: str  # coverage_report.generated_at
    created_at: datetime
    updated_at: datetime

class SkillState(BaseModel):
    skill_id: str
    status: Literal["exposure", "developing", "proficient", "mastered", "review"]
    proficiency: float  # 0.0 - 1.0
    attempts: int
    correct_streak: int
    last_reviewed: datetime
    next_review_due: datetime
    source_refs: list[str]  # topic/course/instructor record paths or citation URLs
```

### 2.5 MCP Tools Specification

The MCP server exposes the tutor as an intent layer. Tools are named for sentences a user would say.

| Tool | Signature | Intent | Internal Behavior |
|---|---|---|---|
| `tutor_assess_skills` | `(goal: str, learner_id: str)` | "Test my AI agent skills" | Starts/resumes diagnostic interview over corpus topics; returns proficiency summary with source refs. |
| `tutor_recommend_path` | `(learner_id: str, goal: str, hours_per_week: int \| None)` | "Build me a GenAI study path" | Uses learner state and corpus metadata to produce a sequenced plan with course/topic citations. |
| `tutor_get_next_exercise` | `(skill: str, learner_id: str)` | "Give me a RAG practice problem" | Resolves the skill, retrieves relevant corpus records, calls problem-writer, returns formatted exercise. |
| `tutor_submit_answer` | `(learner_id: str, answer: str)` | "Here is my answer" | Routes to grader, updates learner model, returns feedback, citations, and next action. |
| `tutor_view_progress` | `(learner_id: str, topic: str \| None)` | "How am I doing?" | Returns a formatted progress digest with mastered, developing, and review skills. |
| `tutor_search_course_material` | `(query: str, topic: str \| None)` | "Find course material on MCP" | Searches `genai_research` and returns concise, cited course/topic matches. |

**MCP design principles applied:**
- Accept human references ("agentic RAG", "AI evals", "Claude Code") and resolve to `skill_id`, `topic_slug`, or `course_slug`.
- Return compact markdown summaries, not raw JSON.
- Embed domain rules (e.g., cannot recommend an advanced agent orchestration path before exposing LLM, prompt/context, and RAG prerequisites unless the learner has demonstrated mastery).
- Conversational errors for invalid inputs.

---

## 3. Week 3 Design Patterns in Action

### 3.1 Multi-Turn Diagnostic Interview with `interrupt()`

The diagnostic subagent is implemented as a LangGraph node that loops until convergence.

```text
START → ask_question → receive_answer → update_belief → (converged?) → END
                              ▲            │
                              └────────────┘
                              (loop until confident)
```

**`interrupt()` usage:**
- When the learner gives an ambiguous answer, the subagent calls `interrupt()` with a clarification question.
- The graph pauses; the learner's next message resumes via `Command(resume={"answer": "..."})`.
- The resumed value feeds into `update_belief`.

**Example flow:**
```text
1. Diagnostic asks: "Explain the difference between RAG and fine-tuning for a customer-support assistant."
2. Learner gives a solid comparison → belief updates to "proficient in RAG basics"
3. Diagnostic asks: "How would you expose that assistant's course-search capability through MCP?"
4. Learner says: "I don't know MCP yet"
5. Diagnostic asks a simpler tool-use question → learner succeeds
6. Diagnostic updates: "tool use: developing", "MCP: exposure"
7. Converged → handoff to planner
```

### 3.2 Agentic State Machine for Skill Mastery

Each skill follows a finite state machine. Transitions are driven by the grader + time.

```text


    ┌─────────┐     first exposure      ┌───────────┐
    │  start  │ ──────────────────────▶ │  exposure │
    └─────────┘                         └─────┬─────┘
                                              │
                                              │ 3/3 correct
                                              ▼
                                        ┌───────────┐
                                        │ developing│
                                        └─────┬─────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    │ 5/5 correct            │ 2/5 wrong              │ spaced review due
                    ▼                         ▼                         ▼
              ┌───────────┐          ┌───────────┐             ┌───────────┐
              │ proficient│          │  exposure │ (remedial)  │  review   │
              └─────┬─────┘          └───────────┘             └─────┬─────┘
                    │                                                │
                    │ 3/3 correct + retention quiz                   │ review passed
                    ▼                                                ▼
              ┌───────────┐                                  ┌───────────┐
              │  mastered │                                  │ proficient│
              └───────────┘                                  └───────────┘
```

**Transition rules:**
- `exposure → developing`: 2 consecutive correct answers.
- `developing → proficient`: 5 consecutive correct answers or 80% over last 10.
- `proficient → mastered`: pass a retention quiz after a spaced interval.
- `any state → review`: spaced-repetition interval elapsed.
- `developing/proficient → remedial exposure`: performance drops below 50%.

### 3.3 Structured Outputs

All subagents use Pydantic models for reliable downstream processing.

**LearnerProfile:**
```python
class SkillProficiency(BaseModel):
    skill_id: str
    skill_name: str
    topic_slug: str
    status: Literal["exposure", "developing", "proficient", "mastered", "review"]
    proficiency: float
    confidence: float
    gap_description: str
    source_refs: list[str]

class LearnerProfile(BaseModel):
    learner_id: str
    subject: str
    skills: list[SkillProficiency]
    top_gaps: list[str]
    estimated_level: Literal["beginner", "intermediate", "advanced"]
    corpus_snapshot: str
```

**Exercise:**
```python
class CorpusSourceRef(BaseModel):
    path: str
    title: str
    record_type: Literal["topic", "course", "instructor", "coverage", "source"]
    citation_url: str | None

class Exercise(BaseModel):
    exercise_id: str
    skill_id: str
    topic_slug: str
    difficulty: int  # 1-10
    question: str
    format: Literal["multiple_choice", "short_answer", "design_critique", "code", "architecture_scenario"]
    options: list[str] | None  # for multiple choice
    rubric: str
    hints: list[str]
    solution: str
    explanation: str
    source_refs: list[CorpusSourceRef]
```

**GradingResult:**
```python
class GradingResult(BaseModel):
    score: float  # 0.0 - 1.0
    is_correct: bool
    feedback: str
    explanation: str
    skill_state_transition: Literal["same", "promote", "demote", "review"]
    next_action: Literal["next_exercise", "retry", "easier", "review"]
    cited_evidence: list[CorpusSourceRef]
    misconception_tags: list[str]
```

### 3.4 Cross-Session Memory Management

**On first session:**
1. Create `learner_id`.
2. Run diagnostic.
3. Write `LearnerProfile` to `/memories/{learner_id}/profile.json`.
4. Planner writes `StudyPlan` to `/memories/{learner_id}/plan.json`.

**On return session:**
1. Load `LearnerProfile` from store.
2. Skip diagnostic or run a short review diagnostic.
3. Resume study plan from last position.
4. Continue updating store after each exercise.

**Thread isolation:**
- Each conversation has a unique `thread_id` for checkpointer state.
- `learner_id` is separate from `thread_id`; one learner can have many threads.
- The orchestrator maps `thread_id` → `learner_id` at session start.

### 3.5 Router / Supervisor Pattern

The orchestrator can be implemented as either:

**Router pattern (simpler):**
- Classify intent: `diagnose`, `practice`, `submit_answer`, `recommend_path`, `search_material`, `progress`.
- Route to the appropriate subagent.
- Fast, predictable, easy to debug.

**Supervisor pattern (more flexible):**
- A manager LLM decides which subagent to call next.
- Can loop between subagents (e.g., grader → coach → problem-writer).
- Better for open-ended tutoring conversations.

**Recommended:** Start with router for the demo, upgrade to supervisor if time allows.

### 3.6 MCP Intent Layer

The MCP server wraps the orchestrator so external clients can tutor without knowing LangGraph internals.

```python
@mcp.tool()
def tutor_get_next_exercise(skill: str, learner_id: str) -> str:
    """Give the learner a source-grounded practice problem for the requested GenAI skill."""
    skill_id = resolve_skill(skill)
    learner = load_learner_model(learner_id)
    source_context = search_course_material(skill)
    exercise = problem_writer.generate(skill_id, learner, source_context)
    return format_exercise(exercise)
```

This mirrors the MCP Course Platform pattern: **intent over endpoints**.

### 3.7 Agentic RAG over `genai_research`

Retrieval is exposed as a tool, not forced as a hidden pre-step. The orchestrator and specialists call it when they need grounded context.

| Agent Need | Retrieval Query | Expected Evidence |
|---|---|---|
| Diagnostic calibration | `topic:AI agents beginner intermediate advanced` | Topic summary, related topics, representative courses. |
| Study-path planning | `goal:production AI agents RAG MCP evals` | Courses from AI agents, RAG, MCP, and AI safety/evaluation topics. |
| Exercise generation | `agentic RAG multi-agent orchestration` | Course syllabi and topic descriptions that contain the concept. |
| Grading support | `RAG vs fine-tuning evals production readiness` | Source snippets for factual claims and rubric criteria. |
| Progress reporting | `learner mastered prompt engineering developing RAG` | Learner state plus linked source refs for next review. |

The retrieval tool must return compact markdown plus structured metadata. A valid response includes the record title, local path, topic/course slug, citation URL when present, and a short relevance note.

---

## 4. Advantages Over Traditional Transactional Educational Tools

### 4.1 Enhanced Personalization

| Traditional Tool | Adaptive Tutor |
|---|---|
| Fixed question banks in fixed order | Questions selected based on real-time belief state |
| Same content for every learner | GenAI course material tailored to individual gaps |
| Binary right/wrong feedback | Partial credit, misconception detection, targeted explanations |
| Static difficulty levels | Continuous difficulty adjustment within the zone of proximal development |
| Generic chatbot answers | Source-backed guidance from the local research corpus |

### 4.2 Long-Term Adaptive Relationships

Traditional tools treat each session as independent. The adaptive tutor:
- Remembers every interaction in the learner model.
- Builds a multi-session relationship.
- Adapts tone and pacing based on learner history.
- Identifies and closes gaps that persist across weeks.

### 4.3 Persistent Learner Modeling Across Sessions

The `Store` maintains:
- Per-skill mastery states.
- Spaced-repetition schedules.
- Goal history and plan revisions.
- Learning preferences.
- Source references that explain why a topic, course, or exercise was selected.

This means a learner can close their laptop on Monday and resume Wednesday with the tutor knowing exactly where they left off.

### 4.4 Continuous Feedback Loops

The system does not stop at grading. It:
- Explains errors.
- Suggests similar problems.
- Adjusts the study plan.
- Schedules reviews.
- Alerts the coach subagent when the learner is frustrated.

---

## 5. Competitive Differentiation: Why This Wins

### 5.1 It Beats Low-Code Solutions

Low-code participants typically build:
- Single-prompt chatbots that answer questions.
- Simple Q&A over a document.
- Forms that generate static study schedules.

**Why the adaptive tutor wins:**
- **Persistent learner state:** A chatbot forgets everything when the page refreshes. The tutor uses a `Store`.
- **Structured feedback loop:** A chatbot gives one-off answers. The tutor grades, explains, updates mastery, and selects the next problem.
- **Adaptive difficulty:** A chatbot cannot calibrate challenge. The tutor uses a state machine and performance history.
- **Multi-agent orchestration:** A chatbot is one model call. The tutor delegates to specialists with isolated contexts.
- **Auditable curriculum:** A generic bot may improvise course advice. The tutor grounds recommendations in `genai_research` source records.

### 5.2 It Beats Code-Heavy Implementations

Code-heavy participants often build:
- Over-engineered pipelines with unclear user value.
- Agents that can "do anything" but fail at demo time.
- Complex infrastructure without a visible artifact.

**Why the adaptive tutor wins:**
- **Clear product story:** "This tutor diagnoses your gaps, plans your study, and adapts in real time." Every technical choice supports that story.
- **Demoable outcomes:** You can show the learner model changing, the difficulty increasing, and a progress report generating.
- **Scoped ambition:** The system does one thing well — adaptive practice — rather than trying to be a general AI.
- **Human-in-the-loop is meaningful:** The tutor asks clarifying questions and pauses for approval, demonstrating control and safety.

### 5.3 Why It Wins the Week 3 Competition

A winning demo for this project includes:

1. **Happy path:** A learner asks for a RAG or AI-agents exercise, gets one at the right level with source refs, answers correctly, and sees their skill advance toward mastery.
2. **Diagnostic moment:** The tutor asks follow-up questions, uses `interrupt()` for clarification, and produces a proficiency profile.
3. **Adaptation moment:** After several correct answers, the problem visibly increases in difficulty.
4. **Failure/recovery moment:** The learner answers incorrectly; the tutor explains the mistake and offers a hint or easier problem.
5. **Cross-session proof:** Close and reopen the conversation; the tutor remembers progress and continues the plan.
6. **MCP integration:** Use Claude Code to call `tutor_view_progress`, `tutor_search_course_material`, or `tutor_get_next_exercise` and see the same learner state.

This combination of technical depth and narrative clarity is hard for either low-code or code-heavy competitors to match.

---

## 6. Implementation Roadmap

### Phase 1: Foundation (Week 1)
- Load `genai_research/research_index.json` and `coverage_report.json`.
- Define skill IDs from `topics/*/topic_summary.json`.
- Derive the initial GenAI prerequisite graph from topic relationships and course syllabi.
- Implement `LearnerProfile` and `Exercise` schemas.
- Build diagnostic subagent with `interrupt()`.
- Set up `Store` backend for cross-session memory.

### Phase 2: Core Loop (Week 2)
- Build the `search_course_material` retrieval tool over topic, course, instructor, and coverage records.
- Implement problem-writer and grader subagents with required `source_refs`.
- Build skill mastery state machine.
- Implement planner subagent.
- Add coach subagent for encouragement and redirection.

### Phase 3: Integration (Week 3)
- Build orchestrator (router or supervisor).
- Add checkpointer for thread state.
- Build simple web UI or CLI for demos.
- Write MCP server with the six `tutor_*` intent tools.

### Phase 4: Polish & Demo
- Add deterministic schema/source-ref validators and objective quiz graders for reliability.
- Create seed learner profiles for predictable demos.
- Add progress visualization.
- Add a corpus browser view showing retrieved topic/course/source evidence.
- Record demo video / prepare live walkthrough.

---

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| LLM generates incorrect explanations | Retrieve corpus evidence first; use deterministic graders for exact-answer domains; require source refs in outputs. |
| Diagnostic takes too long | Cap questions at 12; use adaptive questioning to converge faster. |
| Learner model drifts | Store full interaction history; allow manual reset via HITL. |
| MCP tool names collide with other servers | Namespace tools with `tutor_` prefix. |
| Cross-session store corrupted | Validate schema on load; fall back to re-diagnostic if invalid. |
| Demo unpredictable due to LLM randomness | Use `temperature=0`, deterministic graders, and seeded learner profiles. |
| Corpus contains sparse or null fields | Preserve nulls, surface uncertainty, and avoid recommending on unavailable data such as price or enrollment date. |
| Source availability changes after research date | Show `coverage_report.generated_at` and citations; treat the local corpus as the demo snapshot. |
| LinkedIn or marketplace records have limited extraction | Prefer richer primary-source records when details are needed; retain sparse records only as cited options. |

---

## 8. Week 3 Compliance Review

This plan is consistent with the Week 3 Course Summary & Project Planning Guide:

| Week 3 Requirement | Compliance in This Plan |
|---|---|
| One user-facing assistant domain | Adaptive tutor for GenAI learners using the local course-research corpus. |
| Three to six tools across reads, writes, retrieval, and clarification | Six MCP tools, including corpus search, diagnostic, practice, grading, planning, and progress. |
| Persistence strategy | `Store` for learner models and source refs; checkpointer keyed by `thread_id` for session state. |
| Human-in-the-loop | `interrupt()` for ambiguous learner answers and clarification; approval gate for destructive learner-state changes. |
| Composition layer | Router-first orchestrator with specialist subagents; optional supervisor/Deep Agents upgrade. |
| Agentic RAG | `search_course_material` retrieves topic, course, instructor, coverage, and source records only when needed. |
| MCP intent layer | `tutor_*` tools use human references, resolve canonical IDs internally, and return formatted summaries. |
| Demo proof | Happy path, clarification, adaptation, recovery, cross-session memory, and MCP access are all explicitly scripted. |
| Safety and reliability | Source-ref validation, null-field preservation, deterministic schema checks, fallback routes, and bounded diagnostics. |

The Week 3 planning guide itself is coherent and requires no changes: its objectives, architecture choices, implementation checklists, and demo criteria align with this revised tutor plan. The adjustments made here bring the project plan into closer compliance by grounding all educational content in `genai_research`.

---

## 9. Summary

The Adaptive GenAI Learning Tutor is a Week 3 project that:

- **Demonstrates mastery** of LangGraph, Deep Agents, MCP, HITL, and cross-session memory.
- **Solves a real problem** — personalized, adaptive GenAI education over a broad researched course catalog.
- **Tells a clear product story** that is easy to demo and judge.
- **Outperforms low-code solutions** through persistent state, structured feedback, source-grounded RAG, and multi-agent orchestration.
- **Outperforms code-heavy solutions** by keeping the engineering tightly aligned to a visible, valuable user outcome.

It is the strongest candidate for a Week 3 winning project among the proposed alternatives.
