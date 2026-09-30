import React, { useEffect, useState } from 'react';
import { checkHealth } from './services/api';
import ActionBand from './components/ActionBand';
import BudOrb from './components/BudOrb';
import ChatWindow from './components/ChatWindow';
import ParametersOverlay from './components/ParametersOverlay';
import ProfileMenu from './components/ProfileMenu';
import SpaceOverlay from './components/SpaceOverlay';

export default function App() {
  const [health, setHealth] = useState('checking');
  const [attempt, setAttempt] = useState(0);
  const [memoryRefresh, setMemoryRefresh] = useState(0);
  const [composerMode, setComposerMode] = useState('landing'); // 'landing' | 'text' | 'voice'
  const [chatPending, setChatPending] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [paramsOpen, setParamsOpen] = useState(false);
  const [spaceOpen, setSpaceOpen] = useState(false);
  const [muted, setMuted] = useState(() => {
    try { return localStorage.getItem('bud_muted') === 'true'; } catch { return false; }
  });

  function toggleMuted() {
    setMuted(value => {
      const next = !value;
      try { localStorage.setItem('bud_muted', String(next)); } catch { /* per-viewer convenience only */ }
      return next;
    });
  }

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setHealth('checking');
    const timeout = setTimeout(() => controller.abort(), 5000);
    checkHealth(controller.signal)
      .then(() => { if (active) setHealth('online'); })
      .catch(() => { if (active) setHealth('offline'); })
      .finally(() => clearTimeout(timeout));
    return () => { active = false; clearTimeout(timeout); controller.abort(); };
  }, [attempt]);

  const orbState = (chatPending || speaking) ? 'responding' : 'idle';

  return (
    <div className="app-shell full-page">
      <div className="top-bar">
        <header>
          <a className="brand" href="#main" aria-label="BUD home">bud<span>✳</span></a>
          <span className="preview-label">LOCAL PREVIEW</span>
          <button
            type="button" className="mute-toggle" onClick={toggleMuted}
            aria-pressed={muted} aria-label={muted ? 'Unmute BUD’s voice' : 'Mute BUD’s voice'}
          >
            {muted ? '🔇' : '🔊'}
          </button>
          <ProfileMenu onOpenSpace={() => setSpaceOpen(true)} />
        </header>
        <ActionBand
          mode={composerMode}
          onWrite={() => setComposerMode('text')}
          onTalk={() => setComposerMode('voice')}
          onParameters={() => setParamsOpen(true)}
        />
      </div>
      <main id="main" className={`voice-main${composerMode === 'landing' ? ' voice-main-landing' : ''}`}>
        <section className={`conversation${composerMode === 'voice' ? ' conversation-wide' : ''}`} aria-labelledby="welcome">
          <div className="hero-intro">
            <div className="eyebrow"><span /> YOUR ALL-TIME BUDDY</div>
            <h1 id="welcome">Room to breathe.<br /><span>Space to be you.</span></h1>
            <p className="intro">A calmer corner of your day. Start with whatever's on your mind.</p>
          </div>
          {composerMode === 'text' && (
            <div className="orb-block">
              <BudOrb state={orbState} />
            </div>
          )}
          {composerMode !== 'landing' && (
            <ChatWindow
              composerMode={composerMode}
              onComposerModeChange={setComposerMode}
              onMemoryResolved={() => setMemoryRefresh(value => value + 1)}
              onPendingChange={setChatPending}
              muted={muted}
              onSpeakingChange={setSpeaking}
            />
          )}
        </section>
      </main>
      {paramsOpen && <ParametersOverlay onClose={() => setParamsOpen(false)} memoryRefresh={memoryRefresh} />}
      {spaceOpen && (
        <SpaceOverlay onClose={() => setSpaceOpen(false)} health={health} onRetry={() => setAttempt(value => value + 1)} />
      )}
      <footer><span>Made for the everyday human.</span><span>BUD · Gate 4</span></footer>
    </div>
  );
}
