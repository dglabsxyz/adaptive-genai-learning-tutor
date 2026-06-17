// Holds the active identity (learner id, tenant id, role) sent on every API call.
// Persisted to localStorage so a refresh keeps the chosen demo learner / role.
import React, { createContext, useContext, useState, useMemo, useCallback } from 'react';
import { DEFAULT_LEARNER_ID, DEFAULT_TENANT_ID, DEFAULT_ROLE } from '../config';

const STORAGE_KEY = 'tutor-session-v1';
const SessionContext = createContext(null);

function loadInitial() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* ignore corrupt storage */
  }
  return {};
}

export function SessionProvider({ children }) {
  const initial = loadInitial();
  const [learnerId, setLearnerIdState] = useState(initial.learnerId || DEFAULT_LEARNER_ID);
  const [tenantId, setTenantIdState] = useState(initial.tenantId || DEFAULT_TENANT_ID);
  const [role, setRoleState] = useState(initial.role || DEFAULT_ROLE);

  const persist = useCallback((next) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* ignore */
    }
  }, []);

  const setLearnerId = useCallback(
    (v) => {
      const value = (v || '').trim() || DEFAULT_LEARNER_ID;
      setLearnerIdState(value);
      persist({ learnerId: value, tenantId, role });
    },
    [tenantId, role, persist],
  );
  const setTenantId = useCallback(
    (v) => {
      setTenantIdState(v);
      persist({ learnerId, tenantId: v, role });
    },
    [learnerId, role, persist],
  );
  const setRole = useCallback(
    (v) => {
      setRoleState(v);
      persist({ learnerId, tenantId, role: v });
    },
    [learnerId, tenantId, persist],
  );

  const identity = useMemo(() => ({ learnerId, tenantId, role }), [learnerId, tenantId, role]);
  const value = useMemo(
    () => ({ identity, learnerId, tenantId, role, setLearnerId, setTenantId, setRole }),
    [identity, learnerId, tenantId, role, setLearnerId, setTenantId, setRole],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used within SessionProvider');
  return ctx;
}
