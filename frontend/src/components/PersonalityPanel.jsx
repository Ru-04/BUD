import React, { useEffect, useRef, useState } from 'react';
import { getPreferences, putPreferences } from '../services/api';

const SLIDERS = [
  { key: 'warmth', label: 'Warmth' },
  { key: 'humour', label: 'Humour' },
  { key: 'sarcasm', label: 'Sarcasm' },
  { key: 'directness', label: 'Directness' },
];

export default function PersonalityPanel({ defaultOpen = false }) {
  const [values, setValues] = useState(null);
  const [status, setStatus] = useState('loading');
  const [open, setOpen] = useState(defaultOpen);
  const saveTimeout = useRef(null);

  useEffect(() => {
    let active = true;
    getPreferences()
      .then(data => { if (active) { setValues(data); setStatus('idle'); } })
      .catch(() => { if (active) setStatus('error'); });
    return () => { active = false; clearTimeout(saveTimeout.current); };
  }, []);

  function updateSlider(key, value) {
    const next = { ...values, [key]: value };
    setValues(next);
    setStatus('saving');
    clearTimeout(saveTimeout.current);
    saveTimeout.current = setTimeout(() => {
      putPreferences(next).then(() => setStatus('saved')).catch(() => setStatus('error'));
    }, 400);
  }

  return (
    <div className="personality-panel">
      <button type="button" className="panel-toggle" onClick={() => setOpen(value => !value)} aria-expanded={open} aria-controls="personality-sliders">
        Personality <span aria-hidden="true">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div id="personality-sliders">
          {status === 'loading' && <p className="hint">Loading your preferences…</p>}
          {status === 'error' && <p className="hint error">Could not reach preferences right now.</p>}
          {values && SLIDERS.map(({ key, label }) => (
            <label key={key} className="slider-row">
              <span>{label}</span>
              <input
                type="range" min={0} max={100} value={values[key]}
                onChange={event => updateSlider(key, Number(event.target.value))}
                aria-valuetext={`${label} ${values[key]} out of 100`}
              />
              <span className="slider-value">{values[key]}</span>
            </label>
          ))}
          {status === 'saving' && <p className="hint">Saving…</p>}
          {status === 'saved' && <p className="hint">Saved.</p>}
        </div>
      )}
    </div>
  );
}
