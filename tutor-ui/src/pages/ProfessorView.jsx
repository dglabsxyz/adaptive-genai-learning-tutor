import React, { useState, useMemo } from 'react';
import { useToast } from '../context/ToastContext';

const students = [
  { id: 1, name: 'Alex Chen', avatar: 'AC', currentModule: 'Module 4: RAG Architecture', progress: 62, exercisesCompleted: 47, lastActive: '2 hours ago', status: 'active', score: 78, streak: 5 },
  { id: 2, name: 'Maria Garcia', avatar: 'MG', currentModule: 'Module 3: Advanced Prompt Engineering', progress: 45, exercisesCompleted: 31, lastActive: '1 day ago', status: 'active', score: 71, streak: 3 },
  { id: 3, name: 'James Wilson', avatar: 'JW', currentModule: 'Module 5: AI Agents', progress: 20, exercisesCompleted: 12, lastActive: '3 days ago', status: 'struggling', score: 48, streak: 0 },
  { id: 4, name: 'Sofia Park', avatar: 'SP', currentModule: 'Module 6: Multimodal AI', progress: 85, exercisesCompleted: 62, lastActive: '30 min ago', status: 'active', score: 92, streak: 12 },
  { id: 5, name: 'David Kim', avatar: 'DK', currentModule: 'Module 2: LLM Foundations', progress: 30, exercisesCompleted: 18, lastActive: '5 days ago', status: 'inactive', score: 55, streak: 0 },
  { id: 6, name: 'Emma Thompson', avatar: 'ET', currentModule: 'Module 4: RAG Architecture', progress: 55, exercisesCompleted: 39, lastActive: '1 day ago', status: 'active', score: 74, streak: 4 },
  { id: 7, name: 'Raj Patel', avatar: 'RP', currentModule: 'Module 7: Evaluation & Safety', progress: 10, exercisesCompleted: 7, lastActive: '6 days ago', status: 'struggling', score: 42, streak: 0 },
  { id: 8, name: 'Olivia Brown', avatar: 'OB', currentModule: 'Module 5: AI Agents', progress: 70, exercisesCompleted: 51, lastActive: '3 hours ago', status: 'active', score: 83, streak: 7 },
];

const classStats = {
  totalStudents: 8,
  avgProgress: 47,
  activeToday: 5,
  avgScore: 68,
  exercisesCompleted: 267,
  struggling: 2,
};

const statusColors = {
  active: 'bg-green-500/15 text-green-400 border-green-500/20',
  struggling: 'bg-orange-500/15 text-orange-400 border-orange-500/20',
  inactive: 'bg-red-500/15 text-red-400 border-red-500/20',
};

const statusLabel = {
  active: 'On Track',
  struggling: 'Needs Help',
  inactive: 'Inactive',
};

export default function ProfessorView() {
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [selectedStudent, setSelectedStudent] = useState(null);
  const { addToast } = useToast();

  const filtered = useMemo(() => {
    let data = students;
    if (filter !== 'all') data = data.filter(s => s.status === filter);
    if (search) data = data.filter(s => s.name.toLowerCase().includes(search.toLowerCase()));
    return data;
  }, [filter, search]);

  const handleAction = (student, action) => {
    addToast(`${action} sent to ${student.name}`, 'success', 3000);
    setSelectedStudent(null);
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-[var(--c-primary)] to-[var(--c-secondary)] bg-clip-text text-transparent">Professor Dashboard</h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">Class overview and student analytics</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-[var(--r-full)] bg-[var(--bg-surface)] border border-[var(--border)] text-xs text-[var(--text-muted)]">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          Live data
        </div>
      </div>

      {/* Class stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { label: 'Total Students', value: classStats.totalStudents },
          { label: 'Avg Progress', value: `${classStats.avgProgress}%` },
          { label: 'Active Today', value: classStats.activeToday },
          { label: 'Avg Score', value: classStats.avgScore },
          { label: 'Exercises Done', value: classStats.exercisesCompleted },
          { label: 'Struggling', value: classStats.struggling, accent: true },
        ].map((stat, i) => (
          <div key={i} className="card p-4 text-center hover-lift">
            <div className={`text-2xl font-bold ${stat.accent ? 'text-orange-400' : 'text-[var(--c-primary)]'}`}>{stat.value}</div>
            <div className="text-xs text-[var(--text-muted)] mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex items-center gap-2">
            {['all', 'active', 'struggling', 'inactive'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-[var(--r-full)] text-sm font-medium transition-all border
                  ${filter === f
                    ? 'bg-[var(--c-primary)] text-white border-[var(--c-primary)] shadow-[var(--shadow-glow)]'
                    : 'bg-[var(--bg-surface)] text-[var(--text-secondary)] border-[var(--border)] hover:border-[var(--c-primary)]/30'}`}
              >
                {f === 'all' ? 'All Students' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search by name..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="input w-full"
            />
          </div>
        </div>
      </div>

      {/* Student table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--text-muted)] text-xs uppercase">
                <th className="text-left px-4 py-3 font-medium">Student</th>
                <th className="text-left px-4 py-3 font-medium">Current Module</th>
                <th className="text-left px-4 py-3 font-medium">Progress</th>
                <th className="text-left px-4 py-3 font-medium">Exercises</th>
                <th className="text-left px-4 py-3 font-medium">Score</th>
                <th className="text-left px-4 py-3 font-medium">Streak</th>
                <th className="text-left px-4 py-3 font-medium">Last Active</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-left px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(student => (
                <React.Fragment key={student.id}>
                  <tr className="border-b border-[var(--border)] hover:bg-[var(--bg-surface)]/50 transition-colors cursor-pointer"
                      onClick={() => setSelectedStudent(selectedStudent === student.id ? null : student.id)}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-[var(--c-primary)]/20 flex items-center justify-center text-xs font-bold text-[var(--c-primary)]">
                          {student.avatar}
                        </div>
                        <span className="font-medium text-[var(--text-primary)]">{student.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{student.currentModule}</td>
                    <td className="px-4 py-3">
                      <div className="w-24 h-2 bg-[var(--bg-surface)] rounded-full overflow-hidden">
                        <div className="h-full bg-[var(--c-primary)] rounded-full transition-all" style={{ width: `${student.progress}%` }}></div>
                      </div>
                      <span className="text-xs text-[var(--text-muted)] mt-1 inline-block">{student.progress}%</span>
                    </td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{student.exercisesCompleted}</td>
                    <td className="px-4 py-3">
                      <span className={`font-bold ${student.score >= 80 ? 'text-green-400' : student.score >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
                        {student.score}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[var(--text-secondary)]">{student.streak > 0 ? `🔥 ${student.streak}` : '-'}</span>
                    </td>
                    <td className="px-4 py-3 text-[var(--text-muted)]">{student.lastActive}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-[var(--r-full)] text-xs font-medium border ${statusColors[student.status]}`}>
                        {statusLabel[student.status]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button className="text-xs text-[var(--c-primary)] hover:underline" onClick={e => { e.stopPropagation(); setSelectedStudent(selectedStudent === student.id ? null : student.id); }}>
                        {selectedStudent === student.id ? 'Collapse' : 'View Details'}
                      </button>
                    </td>
                  </tr>
                  {selectedStudent === student.id && (
                    <tr className="bg-[var(--bg-surface)]/30">
                      <td colSpan={9} className="px-4 py-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="space-y-2">
                            <h4 className="text-sm font-bold text-[var(--text-primary)]">Skill Breakdown</h4>
                            {['LLMs', 'RAG', 'Agents', 'Prompt Engineering', 'Multimodal'].map(skill => (
                              <div key={skill} className="flex items-center gap-2">
                                <span className="text-xs text-[var(--text-muted)] w-28">{skill}</span>
                                <div className="flex-1 h-1.5 bg-[var(--bg-card)] rounded-full overflow-hidden">
                                  <div className="h-full bg-[var(--c-primary)] rounded-full" style={{ width: `${Math.random() * 100}%` }}></div>
                                </div>
                                <span className="text-xs text-[var(--text-muted)] w-8 text-right">{Math.round(Math.random() * 100)}%</span>
                              </div>
                            ))}
                          </div>
                          <div className="space-y-2">
                            <h4 className="text-sm font-bold text-[var(--text-primary)]">Recent Activity</h4>
                            <div className="text-xs text-[var(--text-muted)] space-y-1">
                              <div className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-[var(--c-primary)]"></span>Completed RAG Exercise 3.2</div>
                              <div className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-[var(--c-secondary)]"></span>Reviewed Vector Databases</div>
                              <div className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-[var(--c-primary)]"></span>Diagnostic Retake — improved 12%</div>
                            </div>
                          </div>
                          <div className="space-y-3">
                            <h4 className="text-sm font-bold text-[var(--text-primary)]">Professor Actions</h4>
                            <div className="flex flex-col gap-2">
                              <button onClick={() => handleAction(student, 'Encouragement')} className="btn-secondary text-xs w-full py-2">Send Encouragement</button>
                              <button onClick={() => handleAction(student, 'Study Reminder')} className="btn-secondary text-xs w-full py-2">Send Study Reminder</button>
                              <button onClick={() => handleAction(student, 'Check-in Request')} className="btn-primary text-xs w-full py-2">Request Check-in</button>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <div className="p-12 text-center">
            <div className="text-4xl mb-3">🔍</div>
            <p className="text-sm text-[var(--text-muted)]">No students match your filters.</p>
          </div>
        )}
      </div>
    </div>
  );
}
