// Adapters that translate backend payloads into the shapes the UI components expect.

// Backend SourceRef record -> SourceRef component prop ({title, record_type, path, citation_url}).
export function toSourceCards(refs = []) {
  return (refs || [])
    .filter(Boolean)
    .map((r) => ({
      title: r.title || r.source_id || 'Source',
      record_type: r.record_type || 'source',
      path: r.path || '',
      citation_url: (r.citations && r.citations[0]) || r.citation_url || null,
      snippet: r.snippet || null,
    }));
}

// view_progress `.progress` map -> array of SkillMasteryBar-friendly records.
export function toSkillBars(progressMap = {}) {
  return Object.values(progressMap || {}).map((s) => ({
    name: s.skill,
    proficiency: typeof s.proficiency === 'number' ? s.proficiency : 0,
    status: s.status || 'exposure',
    attempts: s.attempts || 0,
    streak: s.correct_streak || 0,
    nextReview: s.next_review || null,
    nextReviewReason: s.next_review_reason || null,
    statusReason: s.status_reason || null,
    evidence: s.evidence || [],
    lastChange: s.last_change || null,
    sourceRefs: s.source_refs || [],
  }));
}

export const STATUS_ORDER = ['exposure', 'developing', 'proficient', 'mastered', 'review'];

export function overallProficiency(skillBars = []) {
  if (!skillBars.length) return 0;
  const sum = skillBars.reduce((acc, s) => acc + (s.proficiency || 0), 0);
  return Math.round((sum / skillBars.length) * 100);
}

export function countByStatus(skillBars = []) {
  return skillBars.reduce(
    (acc, s) => {
      acc[s.status] = (acc[s.status] || 0) + 1;
      return acc;
    },
    { exposure: 0, developing: 0, proficient: 0, mastered: 0, review: 0 },
  );
}
