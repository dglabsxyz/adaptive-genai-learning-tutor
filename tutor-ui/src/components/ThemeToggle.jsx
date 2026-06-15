import React from 'react';
import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      onClick={toggleTheme}
      className="relative flex items-center w-[52px] h-7 rounded-full transition-all duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary-500 focus-visible:ring-offset-surface"
      style={{
        background: isDark ? '#2d2d3a' : '#e2e8f0',
        boxShadow: isDark
          ? 'inset 0 1px 3px rgba(0,0,0,0.4), 0 1px 0 rgba(255,255,255,0.05)'
          : 'inset 0 1px 3px rgba(0,0,0,0.08), 0 1px 0 rgba(255,255,255,0.8)',
      }}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {/* Track icons */}
      <span className="absolute left-1.5 text-[10px] opacity-60" style={{ color: isDark ? '#fbbf24' : '#94a3b8' }}>
        ☾
      </span>
      <span className="absolute right-1.5 text-[10px] opacity-60" style={{ color: isDark ? '#94a3b8' : '#f59e0b' }}>
        ☀
      </span>

      {/* Sliding thumb */}
      <div
        className="absolute w-5 h-5 rounded-full shadow-lg transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
        style={{
          left: isDark ? '4px' : '28px',
          background: isDark ? '#fbbf24' : '#f59e0b',
          boxShadow: isDark
            ? '0 0 8px rgba(251,191,36,0.4), 0 2px 4px rgba(0,0,0,0.3)'
            : '0 0 8px rgba(245,158,11,0.3), 0 2px 4px rgba(0,0,0,0.1)',
        }}
      />
    </button>
  );
}
