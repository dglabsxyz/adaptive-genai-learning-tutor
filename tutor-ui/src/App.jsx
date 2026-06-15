import React, { useState, useEffect } from 'react';
import './styles/index.css';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import Sidebar from './components/Sidebar';
import WelcomeModal from './components/WelcomeModal';
import HelpBlade from './components/HelpBlade';
import Dashboard from './pages/Dashboard';
import Diagnostic from './pages/Diagnostic';
import StudyPlan from './pages/StudyPlan';
import Exercise from './pages/Exercise';
import Progress from './pages/Progress';
import CorpusBrowser from './pages/CorpusBrowser';
import ProfessorView from './pages/ProfessorView';
import Resources from './pages/Resources';

const pages = {
  dashboard: Dashboard,
  diagnostic: Diagnostic,
  'study-plan': StudyPlan,
  exercise: Exercise,
  progress: Progress,
  corpus: CorpusBrowser,
  professor: ProfessorView,
  resources: Resources,
};

export default function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const [showWelcome, setShowWelcome] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const PageComponent = pages[activePage] || Dashboard;

  useEffect(() => {
    const hasWelcomed = localStorage.getItem('tutor-welcomed') === 'true';
    if (!hasWelcomed) {
      setShowWelcome(true);
    }
  }, []);

  return (
    <ThemeProvider>
      <ToastProvider>
        <div className="flex h-screen w-screen overflow-hidden bg-[var(--bg)] text-[var(--text-primary)]">
          <Sidebar activePage={activePage} onNavigate={setActivePage} onToggleHelp={() => setHelpOpen(o => !o)} />

          <main className={`flex-1 overflow-hidden relative ambient-glow transition-[margin] duration-300 ${helpOpen ? 'mr-[320px]' : ''}`}>
            <div className="relative z-10 h-full">
              <PageComponent onNavigate={setActivePage} />
            </div>
          </main>

          <HelpBlade isOpen={helpOpen} onToggle={() => setHelpOpen(o => !o)} />
        </div>

        {showWelcome && (
          <WelcomeModal
            onComplete={() => setShowWelcome(false)}
            onSkip={() => setShowWelcome(false)}
          />
        )}
      </ToastProvider>
    </ThemeProvider>
  );
}
