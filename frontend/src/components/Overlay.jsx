import React, { useEffect, useRef } from 'react';

// Elements a keyboard user can land on inside the dialog; the dialog's own container (tabIndex
// -1, focused programmatically on open) is deliberately excluded so Tab from there lands on the
// first real control instead of looping back to the container itself.
const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export default function Overlay({ title, onClose, children }) {
  const dialogRef = useRef(null);
  const previouslyFocused = useRef(null);

  useEffect(() => {
    // Without a focus trap, Tab/Shift+Tab can walk a keyboard user straight out of the dialog
    // and into the page behind the backdrop -- a real modal-dialog accessibility bug, not a
    // hypothetical one. Capture what had focus so it can be restored once the dialog closes,
    // rather than dropping the user at <body>.
    previouslyFocused.current = document.activeElement;
    dialogRef.current?.focus();

    function onKeyDown(event) {
      if (event.key === 'Escape') { onClose(); return; }
      if (event.key !== 'Tab') return;
      const focusable = dialogRef.current?.querySelectorAll(FOCUSABLE_SELECTOR);
      if (!focusable || focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      previouslyFocused.current?.focus?.();
    };
  }, [onClose]);

  return (
    <div className="overlay-backdrop" onClick={onClose}>
      <div
        className="overlay-panel" role="dialog" aria-modal="true" aria-label={title}
        tabIndex={-1} ref={dialogRef} onClick={event => event.stopPropagation()}
      >
        <div className="overlay-heading">
          <span>{title}</span>
          <button type="button" className="ghost" onClick={onClose} aria-label="Close">×</button>
        </div>
        {children}
      </div>
    </div>
  );
}
