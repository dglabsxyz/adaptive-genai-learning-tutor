import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import SkillMasteryBar from '../components/SkillMasteryBar';
import SkillStateBadge from '../components/SkillStateBadge';
import { LoadingState, ErrorState } from '../components/PageStates';
import { useApi } from '../api/useApi';
import { useSession } from '../context/SessionContext';
import { useToast } from '../context/ToastContext';
import { toSkillBars } from '../api/mappers';

const STATUS_COLOR = {
  exposure: '#ef4444',
  developing: '#f59e0b',
  proficient: '#10b981',
  mastered: '#F15B2A',
  review: '#EC008C',
};

export default function Progress() {
  const api = useApi();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { learnerId } = useSession();
  const { addToast } = useToast();
  const [confirmReset, setConfirmReset] = useState(false);
  const [busy, setBusy] = useState(false);

  const progressQ = useQuery({ queryKey: ['progress', learnerId], queryFn: () => api.getProgress() });

  if (progressQ.isLoading) return <Shell><LoadingState label="Loading progress…" /></Shell>;
  if (progressQ.isError) return <Shell><ErrorState error={progressQ.error} onRetry={progressQ.refetch} /></Shell>;

  const skills = toSkillBars(progressQ.data?.progress);
  const chartData = skills.map((s) => ({ name: s.name, pct: Math.round((s.proficiency || 0) * 100), status: s.status }));
  const changes = skills
    .filter((s) => s.lastChange)
    .map((s) => ({ skill: s.name, ...s.lastChange }))
    .sort((a, b) => String(b.at).localeCompare(String(a.at)))
    .slice(0, 8);

  const handleExport = async () => {
    try {
      setBusy(true);
      const data = await api.getExport();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `progress-${learnerId}.json`;
      a.click();
      URL.revokeObjectURL(url);
      addToast('Progress exported', 'success');
    } catch (e) {
      addToast(e.message || 'Export failed', 'error');
    } finally {
      setBusy(false);
    }
  };

  const handleReset = async () => {
    try {
      setBusy(true);
      await api.resetProgress();
      await qc.invalidateQueries({ queryKey: ['progress', learnerId] });
      addToast('Progress reset', 'success');
      setConfirmReset(false);
    } catch (e) {
      addToast(e.message || 'Reset failed', 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Shell>
      <div className="mb-6 flex items-end justify-between flex-wrap gap-3">
        <div>
          <p className="text-overline text-[var(--text-muted)] mb-1">Mastery</p>
          <h2 className="text-display text-[var(--text-primary)]">My Progress</h2>
          <p className="text-body text-[var(--text-secondary)]">Proficiency advances only on graded evidence — never on assertion.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExport} disabled={busy} className="btn-secondary text-sm">⤓ Export</button>
          {confirmReset ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-[var(--c-danger)]">This is destructive.</span>
              <button onClick={handleReset} disabled={busy} className="btn-primary text-sm" style={{ background: 'var(--c-danger)' }}>Confirm reset</button>
              <button onClick={() => setConfirmReset(false)} disabled={busy} className="btn-secondary text-sm">Cancel</button>
            </div>
          ) : (
            <button onClick={() => setConfirmReset(true)} className="btn-secondary text-sm">Reset…</button>
          )}
        </div>
      </div>

      <div className="card p-6 mb-6">
        <h3 className="text-title text-[var(--text-primary)] mb-4">Proficiency by skill</h3>
        <div style={{ width: '100%', height: Math.max(260, chartData.length * 34) }}>
          <ResponsiveContainer>
            <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 30 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={140} tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
              <Tooltip
                cursor={{ fill: 'var(--bg-surface-hover)' }}
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }}
                formatter={(v, _n, p) => [`${v}% · ${p.payload.status}`, 'Proficiency']}
              />
              <Bar dataKey="pct" radius={[0, 6, 6, 0]}>
                {chartData.map((d) => (
                  <Cell key={d.name} fill={STATUS_COLOR[d.status] || '#8b5cf6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="text-title text-[var(--text-primary)] mb-4">All skills</h3>
          <div className="space-y-3">
            {skills.map((s) => (
              <SkillMasteryBar key={s.name} {...s} onClick={() => navigate('/exercise')} />
            ))}
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-title text-[var(--text-primary)] mb-4">Recent mastery changes</h3>
          {changes.length ? (
            <div className="space-y-3">
              {changes.map((c, i) => (
                <div key={i} className="p-3 rounded-[var(--r-md)] bg-[var(--bg-surface)] border border-[var(--border)]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-[var(--text-primary)]">{c.skill}</span>
                    <SkillStateBadge status={c.to_status || c.status || 'developing'} />
                  </div>
                  <p className="text-xs text-[var(--text-muted)]">
                    {typeof c.proficiency_before === 'number' && typeof c.proficiency_after === 'number'
                      ? `${Math.round(c.proficiency_before * 100)}% → ${Math.round(c.proficiency_after * 100)}%`
                      : 'Updated'}
                    {c.at ? ` · ${String(c.at).slice(0, 10)}` : ''}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--text-muted)]">
              No graded changes yet. Complete a{' '}
              <button onClick={() => navigate('/exercise')} className="text-[var(--c-primary)] hover:underline">practice exercise</button>{' '}
              to start moving the needle.
            </p>
          )}
        </div>
      </div>
    </Shell>
  );
}

function Shell({ children }) {
  return <div className="h-full overflow-y-auto p-8 animate-fade-in">{children}</div>;
}
