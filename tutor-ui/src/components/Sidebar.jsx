import React from 'react';
import { NavLink } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';
import { useSession } from '../context/SessionContext';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/tutor', label: 'Tutor Chat', icon: '💬' },
  { to: '/diagnostic', label: 'Diagnostic', icon: '🔬' },
  { to: '/study-plan', label: 'Study Plan', icon: '🗺️' },
  { to: '/exercise', label: 'Practice', icon: '✏️' },
  { to: '/progress', label: 'My Progress', icon: '📈' },
  { to: '/corpus', label: 'Course Catalog', icon: '📚' },
  { to: '/resources', label: 'Resources', icon: '📁' },
  { to: '/professor', label: 'Professor', icon: '👨‍🏫', roles: ['educator', 'admin'] },
];

export default function Sidebar({ onToggleHelp }) {
  const { learnerId, role } = useSession();
  const items = navItems.filter((item) => !item.roles || item.roles.includes(role));
  const initials = (learnerId || 'demo')
    .replace(/[^a-zA-Z0-9]/g, ' ')
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('') || 'DL';

  return (
    <aside className="w-[260px] h-full flex flex-col border-r border-[var(--border)] z-20 flex-shrink-0 glass-sidebar">
      {/* Logo */}
      <div className="p-5 border-b border-[var(--border)]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-[var(--r-md)] flex items-center justify-center gradient-primary shadow-[var(--shadow-glow)]">
            <span className="text-lg font-bold text-[var(--text-inverse)]">AI</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-sm tracking-tight text-[var(--text-primary)] truncate">Adaptive Tutor</h1>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-[var(--r-xs)] bg-[var(--c-primary-dim)] text-[var(--c-primary)] uppercase tracking-wider">
                Beta
              </span>
            </div>
            <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">GenAI Learning</p>
          </div>
        </div>
      </div>

      {/* Nav links */}
      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `w-full flex items-center gap-3 px-4 py-2.5 rounded-[var(--r-md)] text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'text-[var(--text-primary)] bg-[var(--c-primary-dim)] border border-[var(--c-primary)]/20'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] border border-transparent'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span className={`text-base ${isActive ? 'text-[var(--c-primary)]' : 'text-[var(--text-muted)]'}`}>
                  {item.icon}
                </span>
                {item.label}
                {isActive && <div className="ml-auto w-2 h-2 rounded-full bg-[var(--c-primary)] animate-ring-pulse" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Bottom: help + theme + identity */}
      <div className="p-4 border-t border-[var(--border)] space-y-4">
        <button
          onClick={onToggleHelp}
          className="w-full flex items-center gap-3 px-4 py-2.5 rounded-[var(--r-md)] text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)] transition-all"
        >
          <span className="text-base">❔</span>
          Help &amp; Reference
        </button>

        <div className="flex items-center justify-between px-2">
          <span className="text-xs text-[var(--text-muted)] font-medium">Appearance</span>
          <ThemeToggle />
        </div>

        <div className="flex items-center gap-3 px-2">
          <div className="w-9 h-9 rounded-full gradient-primary flex items-center justify-center text-xs font-bold text-[var(--text-inverse)] shadow-[var(--shadow-sm)]">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-[var(--text-primary)] truncate">{learnerId}</p>
            <p className="text-xs text-[var(--text-muted)] truncate capitalize">{role}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
