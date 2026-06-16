---
name: exercise-design
description: How to author one source-backed GenAI exercise — pick the type by mastery, write a checkable rubric, ground every expected point in the corpus.
---

# Exercise Design

## When to use
When generating a practice exercise for a learner on a specific skill.

## Structure
1. **Pick the type by mastery.** Lower mastery → recall/short-answer or multiple-choice;
   higher mastery → design-critique, architecture-scenario, or implementation-prompt.
2. **Ground it.** Retrieve corpus records for the skill first; the prompt and the expected
   points must trace to those sources. Attach the source references.
3. **Write a checkable rubric.** 3–5 **expected points**, each a concrete, observable idea
   that deterministic grading can check for (not vague "shows understanding"). For
   multiple-choice, exactly one correct option plus plausible distractors.
4. **Calibrate difficulty** to the learner's current status (`exposure`…`mastered`); a
   review exercise should stretch slightly beyond the last demonstrated level.
5. **Add 1–2 hints** that nudge toward the expected points without giving the answer.

## Voice
Clear, specific, real-world. Prefer scenarios drawn from the corpus's actual courses
and topics over invented ones.

## Rules
- Every expected point must be supported by a retrieved source; no unsupported claims.
- Keep the prompt answerable in a few minutes; one skill per exercise.
- The grader, not the prompt, decides pass/fail — write expected points it can match.
