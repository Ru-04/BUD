import React from 'react';

export default function ActionBand({ mode, onWrite, onTalk, onParameters }) {
  return (
    <nav className="action-band" aria-label="BUD actions">
      <button type="button" className={mode === 'text' ? 'active' : ''} onClick={onWrite} aria-pressed={mode === 'text'}>
        <span aria-hidden="true">✎</span> Write what's on your mind
      </button>
      <button type="button" className={mode === 'voice' ? 'active' : ''} onClick={onTalk} aria-pressed={mode === 'voice'}>
        <span aria-hidden="true">🎙</span> Let's talk
      </button>
      <button type="button" onClick={onParameters}>
        <span aria-hidden="true">⚙</span> Parameters
      </button>
    </nav>
  );
}
