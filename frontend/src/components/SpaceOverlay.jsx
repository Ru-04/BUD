import React from 'react';
import Overlay from './Overlay';

export default function SpaceOverlay({ onClose, health, onRetry }) {
  const status = { checking: 'Checking connection', online: 'Backend connected', offline: 'Backend unavailable' }[health];
  return (
    <Overlay title="Your space, taking shape" onClose={onClose}>
      <p>Vent, ask for help, learn something, or just talk. BUD follows what you need from the conversation.</p>
      <div className={`connection ${health}`} role="status" aria-live="polite">
        <span className="status-dot" />
        <div>
          <strong>{status}</strong>
          <small>{health === 'online' ? 'Health check passed · status: ok' : health === 'offline' ? 'Start the local API, then try again.' : 'Reaching the local API…'}</small>
        </div>
      </div>
      <button className="retry" onClick={onRetry} disabled={health === 'checking'}>Check connection <span aria-hidden="true">↗</span></button>
      <div className="coming-next"><span className="eyebrow">STILL TO COME</span><p>Premium visual polish arrives in a later gate.</p></div>
      <div className="gate-label"><span>04 / VOICE INPUT</span><span>English + Hinglish</span></div>
    </Overlay>
  );
}
