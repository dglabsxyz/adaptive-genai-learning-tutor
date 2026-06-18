-- Migration 003: round-trip skill_progress.source_refs.
--
-- The SkillProgress model carries per-skill source_refs (the corpus records that
-- backed the most recent mastery change), but the 001 schema had no column for
-- them, so under the Supabase backend they were silently dropped on save. Add a
-- jsonb column mirroring exercises.source_refs so the field round-trips.

alter table skill_progress
  add column if not exists source_refs jsonb not null default '[]'::jsonb;
