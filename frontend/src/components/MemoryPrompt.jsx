import React, { useEffect, useState } from 'react';
import { approveMemory, deleteMemory, listMemories, rejectMemory } from '../services/api';

export function MemoryPrompt({ candidate, onResolved }) {
  const [pending, setPending] = useState(false);

  async function respond(action) {
    setPending(true);
    try {
      if (action === 'approve') await approveMemory(candidate.id);
      else await rejectMemory(candidate.id);
    } catch {
      // Best-effort: the candidate simply expires on its own if this fails.
    } finally {
      setPending(false);
      onResolved(action);
    }
  }

  return (
    <div className="memory-prompt" role="group" aria-label="Memory suggestion">
      <p><strong>Remember this?</strong> {candidate.content}</p>
      <div className="memory-actions">
        <button type="button" onClick={() => respond('approve')} disabled={pending}>Remember it</button>
        <button type="button" className="ghost" onClick={() => respond('reject')} disabled={pending}>No thanks</button>
      </div>
    </div>
  );
}

export function MemoryList({ refreshKey, defaultOpen = false }) {
  const [memories, setMemories] = useState(null);
  const [open, setOpen] = useState(defaultOpen);

  useEffect(() => {
    let active = true;
    listMemories().then(data => { if (active) setMemories(data); }).catch(() => { if (active) setMemories([]); });
    return () => { active = false; };
  }, [refreshKey]);

  async function remove(id) {
    setMemories(current => current.filter(memory => memory.id !== id));
    try { await deleteMemory(id); } catch { /* list already reflects intent; a refresh will reconcile */ }
  }

  return (
    <div className="memory-list">
      <button type="button" className="panel-toggle" onClick={() => setOpen(value => !value)} aria-expanded={open} aria-controls="remembered-items">
        Remembered <span aria-hidden="true">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div id="remembered-items">
          {!memories && <p className="hint">Loading…</p>}
          {memories?.length === 0 && <p className="hint">Nothing remembered yet.</p>}
          <ul>
            {memories?.map(memory => (
              <li key={memory.id}>
                <span>{memory.content}</span>
                <button type="button" className="ghost" onClick={() => remove(memory.id)} aria-label={`Forget: ${memory.content}`}>×</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
