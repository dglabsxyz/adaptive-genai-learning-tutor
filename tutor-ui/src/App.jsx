import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import HelpBlade from './components/HelpBlade';
import WelcomeModal from './components/WelcomeModal';
import Dashboard from './pages/Dashboard';
import TutorChat from './pages/TutorChat';
import Diagnostic from './pages/Diagnostic';
import StudyPlan from './pages/StudyPlan';
import Exercise from './pages/Exercise';
import Progress from './pages/Progress';
import Library from './pages/Library';
import ProfessorView from './pages/ProfessorView';

export default function App() {
  const [helpOpen, setHelpOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);

  useEffect(() => {
    if (localStorage.getItem('tutor-welcomed') !== 'true') setShowWelcome(true);
  }, []);

  const dismissWelcome = () => {
    localStorage.setItem('tutor-welcomed', 'true');
    setShowWelcome(false);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--bg)] text-[var(--text-primary)]">
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} onToggleHelp={() => setHelpOpen((o) => !o)} />

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <TopBar onOpenNav={() => setNavOpen(true)} />
        <main
          className={`flex-1 overflow-hidden relative ambient-glow transition-[margin] duration-300 ${
            helpOpen ? 'mr-[320px]' : ''
          }`}
        >
          <div className="relative z-10 h-full">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/tutor" element={<TutorChat />} />
              <Route path="/diagnostic" element={<Diagnostic />} />
              <Route path="/study-plan" element={<StudyPlan />} />
              <Route path="/exercise" element={<Exercise />} />
              <Route path="/progress" element={<Progress />} />
              <Route path="/library" element={<Library />} />
              <Route path="/corpus" element={<Navigate to="/library" replace />} />
              <Route path="/resources" element={<Navigate to="/library" replace />} />
              <Route path="/professor" element={<ProfessorView />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </div>
        </main>
      </div>

      <HelpBlade isOpen={helpOpen} onToggle={() => setHelpOpen((o) => !o)} />

      {showWelcome && <WelcomeModal onComplete={dismissWelcome} onSkip={dismissWelcome} />}
    </div>
  );
}
