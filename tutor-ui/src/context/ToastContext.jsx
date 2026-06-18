import React, { createContext, useContext, useState, useCallback } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, duration);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <div className="fixed top-5 right-5 z-50 space-y-2 pointer-events-none">
        {toasts.map((toast, i) => (
          <div
            key={toast.id}
            className="pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-[var(--r-md)] border shadow-[var(--shadow-lg)] animate-slide-in-right"
            style={{
              background: 'var(--bg-card)',
              borderColor: toast.type === 'success' ? 'var(--c-success)' : 
                           toast.type === 'error' ? 'var(--c-danger)' : 
                           toast.type === 'warning' ? 'var(--c-accent)' : 'var(--border)',
              animationDelay: `${i * 0.05}s`,
            }}
          >
            <span className="text-lg">
              {toast.type === 'success' ? '✅' : 
               toast.type === 'error' ? '❌' : 
               toast.type === 'warning' ? '⚠️' : 'ℹ️'}
            </span>
            <span className="text-sm text-[var(--text-primary)]">{toast.message}</span>
            <button
              onClick={() => removeToast(toast.id)}
              className="ml-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
