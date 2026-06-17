// Binds the current identity to every endpoint so components call e.g.
// api.postChat({ message }) without threading identity through manually.
import { useMemo } from 'react';
import { useSession } from '../context/SessionContext';
import * as ep from './endpoints';

export function useApi() {
  const { identity } = useSession();
  return useMemo(
    () => ({
      identity,
      getHealth: () => ep.getHealth(identity),
      getIdentity: () => ep.getIdentity(identity),
      postChat: (args) => ep.postChat(identity, args),
      postChatResume: (args) => ep.postChatResume(identity, args),
      postDiagnostic: (args) => ep.postDiagnostic(identity, args),
      postStudyPlan: (args) => ep.postStudyPlan(identity, args),
      postExercise: (args) => ep.postExercise(identity, args),
      postAnswer: (args) => ep.postAnswer(identity, args),
      getProgress: (learnerId) => ep.getProgress(identity, learnerId ?? identity.learnerId),
      getEvidence: (learnerId, skill) => ep.getEvidence(identity, learnerId ?? identity.learnerId, skill),
      getExport: (learnerId) => ep.getExport(identity, learnerId ?? identity.learnerId),
      resetProgress: (learnerId, scope) => ep.resetProgress(identity, learnerId ?? identity.learnerId, scope),
      searchSources: (q, k) => ep.searchSources(identity, q, k),
      getCohortProgress: () => ep.getCohortProgress(identity),
      getCohortInterventions: () => ep.getCohortInterventions(identity),
      getAdminIntegrations: () => ep.getAdminIntegrations(identity),
      getAdminIndexStatus: () => ep.getAdminIndexStatus(identity),
      getAdminAuditEvents: (args) => ep.getAdminAuditEvents(identity, args),
    }),
    [identity],
  );
}
