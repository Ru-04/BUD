import React from 'react';

// state: 'idle' | 'recording' | 'responding'
export default function BudOrb({ state }) {
  return (
    <div className={`orb-stage orb-state-${state}`} aria-hidden="true">
      <div className="orbit orbit-one" />
      <div className="orbit orbit-two" />
      <div className="orb" />
    </div>
  );
}
