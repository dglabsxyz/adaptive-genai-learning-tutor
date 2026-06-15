# Adaptive GenAI Learning Tutor PRD

## Vision

Build a local-first adaptive tutor that helps learners study generative AI using the workspace `genai_research` corpus as the primary source of truth. The MVP should be demoable without paid cloud services: it diagnoses learner skill, recommends a study path, generates source-backed exercises, grades answers, persists progress, and exposes the same learner state through MCP.

## Goals

- Ground every diagnostic, recommendation, exercise, grading explanation, and study plan in `genai_research`.
- Preserve unknown corpus fields as unknown. Do not invent prices, ratings, dates, enrollment, instructor bios, or unsupported metadata.
- Keep `genai_research` read-only. Store local runtime data under `data/`.
- Use FastAPI, LangChain tools, LangGraph routing/session memory, LangSmith-compatible tracing, local embeddings/vector search, Vite React, and MCP.
- Add Supabase and Railway support only as optional production/deployment paths after the local MVP works.

## Users

- Self-directed GenAI learners who want a personalized path through a broad course catalog.
- Educators or project reviewers who need visible source references and persistent mastery state.
- Power users who want tutor access from an MCP-capable assistant.

## MVP User Flow

1. Learner says: "I want to learn AI agents."
2. Tutor runs a short diagnostic.
3. Tutor marks RAG as developing and MCP as exposure.
4. Tutor recommends a source-backed path through LLMs, prompt engineering, context engineering, RAG, AI agents, MCP, and evaluation.
5. Tutor generates a RAG or AI-agent exercise with rubric and citations.
6. Learner submits an answer.
7. Tutor grades the answer, explains covered and missed rubric points, updates progress, and shows source references.
8. Learner views persistent mastery state.
9. MCP tools retrieve the same progress and can generate or grade the next exercise.

## Functional Requirements

- FastAPI endpoints: `POST /chat`, `POST /diagnostic`, `POST /exercise`, `POST /answer`, `GET /progress/{learner_id}`, `POST /study-plan`, `GET /sources/search`, and `GET /health`.
- Corpus ingestion loads `research_index.json`, `coverage_report.json`, `topics/*/topic_summary.json`, `courses/*/course_summary.json`, and `instructors/*/instructor_summary.json`.
- Normalized document metadata includes `record_type`, `slug`, `title`, `topic_tags`, `platform`, `path`, `citations`, and `last_researched_at`.
- Local vector index persists sparse TF-IDF style embeddings to `data/vector_index.json`.
- LangChain tools: `search_course_material`, `tutor_assess_skills`, `tutor_get_next_exercise`, `tutor_submit_answer`, `tutor_view_progress`, and `tutor_recommend_path`.
- LangGraph router intents: `diagnose`, `recommend_path`, `practice`, `submit_answer`, `progress`, `search_material`, and `other`.
- LangGraph state tracks messages, learner ID, intent, active skill, active exercise, response, and source refs.
- Interrupt behavior is present for vague goals, ambiguous topic references, ambiguous answers, and destructive reset/delete requests.
- Learner mastery tracks proficiency, status, attempts, correct streak, last reviewed, next review, and source refs for the target topic set.
- Frontend first screen is the tutor workspace: chat, exercise, answer, progress, study plan, and sources.
- MCP server exposes the same six intent-oriented tutor tools and uses the same local state.

## Non-Goals

- No paid LLM dependency is required for the MVP.
- No mutation of `genai_research`.
- No mandatory Supabase, pgvector, or Railway setup for local development.
- No claim that the local sparse vector index is a production semantic embedding model.

## Architecture

- `backend/corpus.py`: read-only corpus normalization.
- `backend/vector_store.py`: local embedding and vector search.
- `backend/stores.py`: JSON-backed learner and exercise persistence.
- `backend/tools.py`: LangChain tools plus deterministic tutor implementations.
- `backend/graph.py`: LangGraph router, memory checkpointer, and interrupt guards.
- `backend/main.py`: FastAPI app.
- `frontend/`: Vite React tutor workspace.
- `mcp_server/server.py`: FastMCP server over the same backend services.
- `supabase/schema.sql`: optional production schema sketch.

## Success Criteria

- Local tests pass for corpus loading, search, routing, grading, and progress updates.
- Backend and frontend run locally.
- Demo flow can be completed through the UI or `scripts/demo_flow.py`.
- API and MCP responses include source references from local corpus records.
- Optional cloud settings are environment-driven and local fallbacks remain available.

