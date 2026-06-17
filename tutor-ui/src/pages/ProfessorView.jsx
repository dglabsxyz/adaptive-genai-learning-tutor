import React from 'react';
import { useQuery } from '@tanstack/react-query';
import SkillStateBadge from '../components/SkillStateBadge';
import { LoadingState, ErrorState } from '../components/PageStates';
import { useApi } from '../api/useApi';
import { useSession } from '../context/SessionContext';

export default function ProfessorView() {
  const api = useApi();
  const { role } = useSession();
  const isStaff = role === 'educator' || role === 'admin';
  const isAdmin = role === 'admin';

  const cohortQ = useQuery({ queryKey: ['cohort', role], queryFn: () => api.getCohortProgress(), enabled: isStaff, retry: 0 });
  const interventionsQ = useQuery({ queryKey: ['interventions', role], queryFn: () => api.getCohortInterventions(), enabled: isStaff, retry: 0 });
  const integrationsQ = useQuery({ queryKey: ['integrations'], queryFn: () => api.getAdminIntegrations(), enabled: isAdmin, retry: 0 });
  const auditQ = useQuery({ queryKey: ['audit'], queryFn: () => api.getAdminAuditEvents({ limit: 12 }), enabled: isAdmin, retry: 0 });

  if (!isStaff) {
    return (
      <Shell>
        <ErrorState error={{ status: 403, message: 'The Professor view is for educators and admins.' }} />
      </Shell>
    );
  }

  if (cohortQ.isLoading) return <Shell><LoadingState label="Loading cohort…" /></Shell>;
  if (cohortQ.isError) return <Shell><ErrorState error={cohortQ.error} onRetry={cohortQ.refetch} /></Shell>;

  const c = cohortQ.data || {};
  const recs = interventionsQ.data?.recommendations || [];

  return (
    <Shell>
      <div className="mb-6">
        <p className="text-overline text-[var(--text-muted)] mb-1">Educator</p>
        <h2 className="text-display text-[var(--text-primary)]">Professor View</h2>
        <p className="text-body text-[var(--text-secondary)]">Cohort mastery, risk areas, and source-backed interventions.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Stat label="Learners" value={c.learner_count ?? 0} />
        <Stat label="Skills tracked" value={(c.skill_summary || []).length} />
        <Stat label="Risk areas" value={(c.risk_areas || []).length} color="var(--c-danger)" />
        <Stat label="Interventions" value={recs.length} color="var(--c-accent)" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="card p-6">
          <h3 className="text-title text-[var(--text-primary)] mb-4">Cohort proficiency by skill</h3>
          <div className="space-y-3">
            {(c.skill_summary || []).map((s) => (
              <div key={s.skill}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-[var(--text-secondary)]">{s.skill}</span>
                  <span className="text-[var(--text-muted)] font-mono">{Math.round((s.average_proficiency || 0) * 100)}% · {s.learner_count} learner(s)</span>
                </div>
                <div className="h-2 rounded-full bg-[var(--bg)] overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${Math.round((s.average_proficiency || 0) * 100)}%`, background: 'var(--c-primary)' }} />
                </div>
              </div>
            ))}
            {!(c.skill_summary || []).length && <p className="text-sm text-[var(--text-muted)]">No cohort data yet.</p>}
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-title text-[var(--text-primary)] mb-4">Risk areas</h3>
          {(c.risk_areas || []).length ? (
            <div className="space-y-2">
              {c.risk_areas.map((r) => (
                <div key={r.skill} className="flex items-center justify-between p-3 rounded-[var(--r-md)] bg-[var(--bg-surface)] border border-[var(--border)]">
                  <span className="text-sm text-[var(--text-primary)]">{r.skill}</span>
                  <span className="text-xs font-mono text-[var(--c-danger)]">{Math.round((r.average_proficiency || 0) * 100)}%</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--text-muted)]">No skills below the risk threshold. 🎉</p>
          )}
        </div>
      </div>

      <div className="card p-6 mb-6">
        <h3 className="text-title text-[var(--text-primary)] mb-4">Recommended interventions</h3>
        {interventionsQ.isLoading && <LoadingState label="Loading interventions…" />}
        {recs.length ? (
          <div className="space-y-3">
            {recs.map((r, i) => (
              <div key={i} className="p-4 rounded-[var(--r-md)] bg-[var(--bg-surface)] border border-[var(--border)]">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="text-sm font-medium text-[var(--text-primary)]">{r.learner_id}</span>
                  <span className="text-[var(--text-muted)]">·</span>
                  <span className="text-sm text-[var(--text-secondary)]">{r.skill}</span>
                  <SkillStateBadge status={r.status || 'exposure'} />
                </div>
                <p className="text-xs text-[var(--text-muted)] mb-1">{r.rationale}</p>
                <p className="text-sm text-[var(--text-secondary)]"><span className="text-[var(--c-primary)]">Next:</span> {r.next_action}</p>
              </div>
            ))}
          </div>
        ) : (
          !interventionsQ.isLoading && <p className="text-sm text-[var(--text-muted)]">No interventions recommended right now.</p>
        )}
      </div>

      <div className="card p-6 mb-6">
        <h3 className="text-title text-[var(--text-primary)] mb-4">Learners</h3>
        <div className="space-y-2">
          {(c.learners || []).map((l) => (
            <div key={l.learner_id} className="flex items-center gap-3 p-3 rounded-[var(--r-md)] bg-[var(--bg-surface)] border border-[var(--border)]">
              <span className="text-sm font-medium text-[var(--text-primary)] w-40 truncate">{l.learner_id}</span>
              <div className="flex flex-wrap gap-1.5 flex-1">
                {(l.weakest_skills || []).slice(0, 3).map((w, j) => (
                  <span key={j} className="tag text-[11px]">{w.skill} · {Math.round((w.proficiency || 0) * 100)}%</span>
                ))}
              </div>
              {l.updated_at && <span className="text-xs text-[var(--text-muted)]">{String(l.updated_at).slice(0, 10)}</span>}
            </div>
          ))}
          {!(c.learners || []).length && <p className="text-sm text-[var(--text-muted)]">No learners in this tenant yet.</p>}
        </div>
      </div>

      {isAdmin && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-6">
            <h3 className="text-title text-[var(--text-primary)] mb-4">Integrations</h3>
            {integrationsQ.isError ? (
              <ErrorState error={integrationsQ.error} onRetry={integrationsQ.refetch} />
            ) : (
              <div className="space-y-2 text-sm">
                {Object.entries(integrationsQ.data || {}).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between">
                    <span className="text-[var(--text-secondary)]">{k.replace(/_/g, ' ')}</span>
                    <span className="font-mono text-xs text-[var(--text-primary)]">{String(v)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card p-6">
            <h3 className="text-title text-[var(--text-primary)] mb-4">Recent audit events</h3>
            {auditQ.isError ? (
              <ErrorState error={auditQ.error} onRetry={auditQ.refetch} />
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {(auditQ.data?.events || []).map((e, i) => (
                  <div key={i} className="text-xs p-2 rounded-[var(--r-sm)] bg-[var(--bg-surface)] border border-[var(--border)]">
                    <span className="font-medium text-[var(--text-primary)]">{e.event_type || e.type || 'event'}</span>
                    {e.learner_id && <span className="text-[var(--text-muted)]"> · {e.learner_id}</span>}
                    {(e.timestamp || e.created_at) && (
                      <span className="text-[var(--text-muted)] float-right">{String(e.timestamp || e.created_at).slice(0, 19)}</span>
                    )}
                  </div>
                ))}
                {!(auditQ.data?.events || []).length && <p className="text-sm text-[var(--text-muted)]">No audit events.</p>}
              </div>
            )}
          </div>
        </div>
      )}
    </Shell>
  );
}

function Stat({ label, value, color = 'var(--c-primary)' }) {
  return (
    <div className="card p-4">
      <div className="text-2xl font-bold" style={{ color }}>{value}</div>
      <div className="text-xs text-[var(--text-muted)] uppercase tracking-wide mt-1">{label}</div>
    </div>
  );
}

function Shell({ children }) {
  return <div className="h-full overflow-y-auto p-8 animate-fade-in">{children}</div>;
}
