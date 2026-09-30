import React, { useState } from 'react';

export default function ProfileMenu({ onOpenSpace }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="profile-menu">
      <span className="profile-icon" aria-hidden="true">🙂</span>
      <button
        type="button" className="overflow-button" onClick={() => setOpen(value => !value)}
        aria-haspopup="menu" aria-expanded={open} aria-label="More options"
      >
        ⋮
      </button>
      {open && (
        <div className="overflow-dropdown" role="menu">
          <button type="button" role="menuitem" onClick={() => { setOpen(false); onOpenSpace(); }}>
            Your space, taking shape
          </button>
        </div>
      )}
    </div>
  );
}
