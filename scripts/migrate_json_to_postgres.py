"""Generate SQL insert statements from local JSON learner state.

The script does not require network access. Review the generated SQL before
applying it to Supabase/Postgres.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import EXERCISE_STORE_PATH, LEARNER_STORE_PATH
from backend.settings import get_settings


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _json(value: object) -> str:
    return _quote(json.dumps(value, separators=(",", ":")))


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-slug", default="local")
    parser.add_argument("--tenant-name", default="Local Demo Tenant")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    settings = get_settings()
    output = Path(args.output) if args.output else settings.data_dir / "json_to_postgres_migration.sql"
    learners = _read_json(LEARNER_STORE_PATH).get("learners", {})
    exercises = _read_json(EXERCISE_STORE_PATH).get("exercises", {})
    lines = [
        "begin;",
        "with tenant as (",
        f"  insert into tenants (slug, name) values ({_quote(args.tenant_slug)}, {_quote(args.tenant_name)})",
        "  on conflict (slug) do update set name = excluded.name",
        "  returning id",
        ") select id from tenant;",
    ]
    for profile in learners.values():
        learner_id = profile["learner_id"]
        lines.append(
            "insert into learner_profiles (tenant_id, learner_id, goals, active_exercise_id, created_at, updated_at) "
            f"select id, {_quote(learner_id)}, {_json(profile.get('goals', []))}::jsonb, "
            f"{_quote(profile['active_exercise_id']) if profile.get('active_exercise_id') else 'null'}, "
            f"{_quote(profile.get('created_at'))}, {_quote(profile.get('updated_at'))} from tenants "
            f"where slug = {_quote(args.tenant_slug)} "
            "on conflict (tenant_id, learner_id) do update set goals = excluded.goals, "
            "active_exercise_id = excluded.active_exercise_id, updated_at = excluded.updated_at;"
        )
        for skill, progress in profile.get("progress", {}).items():
            lines.append(
                "insert into skill_progress "
                "(tenant_id, learner_id, skill, proficiency, status, attempts, correct_streak, last_reviewed, "
                "next_review, evidence, status_reason, next_review_reason, last_change, updated_at) "
                f"select id, {_quote(learner_id)}, {_quote(skill)}, {progress.get('proficiency', 0)}, "
                f"{_quote(progress.get('status', 'exposure'))}, {progress.get('attempts', 0)}, "
                f"{progress.get('correct_streak', 0)}, "
                f"{_quote(progress['last_reviewed']) if progress.get('last_reviewed') else 'null'}, "
                f"{_quote(progress['next_review']) if progress.get('next_review') else 'null'}, "
                f"{_json(progress.get('evidence', []))}::jsonb, "
                f"{_quote(progress['status_reason']) if progress.get('status_reason') else 'null'}, "
                f"{_quote(progress['next_review_reason']) if progress.get('next_review_reason') else 'null'}, "
                f"{_json(progress.get('last_change')) if progress.get('last_change') else 'null'}::jsonb, "
                f"{_quote(profile.get('updated_at'))} from tenants where slug = {_quote(args.tenant_slug)} "
                "on conflict (tenant_id, learner_id, skill) do update set proficiency = excluded.proficiency, "
                "status = excluded.status, attempts = excluded.attempts, correct_streak = excluded.correct_streak, "
                "last_reviewed = excluded.last_reviewed, next_review = excluded.next_review, "
                "evidence = excluded.evidence, status_reason = excluded.status_reason, "
                "next_review_reason = excluded.next_review_reason, last_change = excluded.last_change, "
                "updated_at = excluded.updated_at;"
            )
    for exercise in exercises.values():
        lines.append(
            "insert into exercises "
            "(tenant_id, id, learner_id, skill, exercise_type, difficulty, prompt, choices, answer_key, "
            "expected_points, rubric, hints, created_at) "
            f"select id, {_quote(exercise['id'])}, {_quote(exercise['learner_id'])}, {_quote(exercise['skill'])}, "
            f"{_quote(exercise.get('exercise_type', 'short_answer'))}, {_quote(exercise.get('difficulty', 'developing'))}, "
            f"{_quote(exercise['prompt'])}, {_json(exercise.get('choices', []))}::jsonb, "
            f"{_json(exercise.get('answer_key', []))}::jsonb, {_json(exercise.get('expected_points', []))}::jsonb, "
            f"{_quote(exercise.get('rubric', ''))}, {_json(exercise.get('hints', []))}::jsonb, "
            f"{_quote(exercise.get('created_at'))} from tenants where slug = {_quote(args.tenant_slug)} "
            "on conflict (tenant_id, id) do update set learner_id = excluded.learner_id, "
            "skill = excluded.skill, exercise_type = excluded.exercise_type, difficulty = excluded.difficulty, "
            "prompt = excluded.prompt, choices = excluded.choices, answer_key = excluded.answer_key, "
            "expected_points = excluded.expected_points, rubric = excluded.rubric, hints = excluded.hints;"
        )
    lines.append("commit;")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
