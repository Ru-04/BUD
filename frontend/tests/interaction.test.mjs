import assert from 'node:assert/strict';
import test, { after } from 'node:test';
import React from 'react';
import { createServer } from 'vite';
import { installDom, installFakeAudio, installFakeMediaRecorder } from './setup-dom.mjs';

installDom();
const { render, screen, fireEvent, waitFor, cleanup } = await import('@testing-library/react');

// One shared Vite dev server for the whole file: creating/closing a server per test causes
// overlapping esbuild dependency-scan races and very noisy (harmless) console errors.
const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
after(() => server.close());

function loadModule(path) {
  // Vite caches the module by path, but that only caches the component *function*; each
  // render() call below still mounts a fresh React tree with fresh hook state.
  return server.ssrLoadModule(path);
}

function fetchJson(body, status = 200) {
  return async () => new Response(JSON.stringify(body), { status });
}

test('the landing view shows only the hero text until a mode is chosen', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = fetchJson({ status: 'ok' });
  try {
    const mod = await loadModule('/src/App.jsx');
    render(React.createElement(mod.default));
    assert.ok(screen.getByText(/Room to breathe/), 'landing hero text is shown');
    assert.equal(screen.queryByPlaceholderText(/Tell BUD what/), null, 'no composer before a mode is chosen');
    assert.equal(screen.queryByRole('group', { name: 'Voice recording' }), null, 'no recording panel before a mode is chosen');
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test("clicking Write shows the text composer and clicking Let's talk shows the recording panel", async () => {
  installFakeMediaRecorder();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = fetchJson({ status: 'ok' });
  try {
    const mod = await loadModule('/src/App.jsx');
    render(React.createElement(mod.default));

    fireEvent.click(screen.getByText(/Write what.s on your mind/));
    await waitFor(() => assert.ok(screen.getByPlaceholderText(/Tell BUD what/)));

    fireEvent.click(screen.getByText(/Let.s talk/));
    await waitFor(() => assert.ok(screen.getByRole('group', { name: 'Voice recording' })));

    fireEvent.click(screen.getByText(/Write what.s on your mind/));
    await waitFor(() => assert.ok(screen.getByPlaceholderText(/Tell BUD what/)));
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test('microphone permission denial shows an error and lets the user fall back to typing', async () => {
  installFakeMediaRecorder({ shouldRejectGetUserMedia: true });
  try {
    const mod = await loadModule('/src/components/RecordingPanel.jsx');
    const onCancel = () => { onCancel.called = true; };
    render(React.createElement(mod.default, { onTranscribed: () => {}, onCancel }));
    await waitFor(() => assert.match(screen.getByRole('alert').textContent, /permission was denied/));
    fireEvent.click(screen.getByText('Type instead'));
    assert.equal(onCancel.called, true);
  } finally {
    cleanup();
  }
});

test('pause freezes the recording, resume continues it, and the timer behaves', async () => {
  installFakeMediaRecorder();
  try {
    const mod = await loadModule('/src/components/RecordingPanel.jsx');
    render(React.createElement(mod.default, { onTranscribed: () => {}, onCancel: () => {} }));
    await waitFor(() => assert.ok(screen.getByText('Pause')));

    fireEvent.click(screen.getByText('Pause'));
    assert.ok(screen.getByText('Paused'));
    assert.ok(screen.getByText('Resume'));

    fireEvent.click(screen.getByText('Resume'));
    assert.ok(screen.getByText('Pause'));
    assert.equal(screen.queryByText('Paused'), null);
  } finally {
    cleanup();
  }
});

test('the recording timer is not announced every second, but state changes are announced once', async () => {
  installFakeMediaRecorder();
  try {
    const mod = await loadModule('/src/components/RecordingPanel.jsx');
    const { container } = render(React.createElement(mod.default, { onTranscribed: () => {}, onCancel: () => {} }));
    await waitFor(() => assert.ok(screen.getByText('Pause')));

    const timer = container.querySelector('.rec-timer');
    assert.equal(timer.getAttribute('aria-live'), null, 'the ticking timer must not be a live region');

    const status = container.querySelector('[role="status"]');
    assert.equal(status.textContent, 'Recording');
    fireEvent.click(screen.getByText('Pause'));
    assert.equal(status.textContent, 'Recording paused');
  } finally {
    cleanup();
  }
});

test('React.StrictMode double-invoking the mount effect does not leave an orphaned, unpausable recorder', async () => {
  // Regression test for a real bug: a boolean "cancelled" ref got reset by StrictMode's second
  // mount before the first mount's in-flight getUserMedia() resolved, so the stale first
  // attempt attached its own stream/recorder anyway. Pause/Cancel/Stop only ever touched
  // whichever instance was assigned last, so the *other* one kept recording silently --
  // exactly "even when I pause, the recording still continues."
  const control = installFakeMediaRecorder({ freshStreamPerCall: true, getUserMediaDelayMs: 20 });
  try {
    const mod = await loadModule('/src/components/RecordingPanel.jsx');
    render(React.createElement(React.StrictMode, null, React.createElement(mod.default, { onTranscribed: () => {}, onCancel: () => {} })));
    await waitFor(() => assert.ok(screen.getByText('Pause')));

    fireEvent.click(screen.getByText('Pause'));
    await waitFor(() => assert.ok(screen.getByText('Resume')));

    // Every stream getUserMedia() ever handed out must now be accounted for: exactly one
    // still live (the one Pause actually paused) and the rest stopped as stale duplicates.
    assert.ok(control.streams.length >= 2, 'StrictMode should have invoked start() at least twice');
    const liveStreams = control.streams.filter(s => !s._track.stopped);
    assert.equal(liveStreams.length, 1, 'exactly one stream must remain live after pausing, not an orphaned duplicate');
  } finally {
    cleanup();
  }
});

test('finishing a recording sends it immediately in pure voice mode, with no editable composer step', async () => {
  installFakeMediaRecorder();
  installFakeAudio();
  const originalFetch = globalThis.fetch;
  let chatCalls = 0;
  let sentMessage = null;
  globalThis.fetch = async (url, options) => {
    if (url.includes('/api/transcribe')) return new Response(JSON.stringify({ transcript: 'Hi, how are you, ki haal chaal?', language: 'hindi' }), { status: 200 });
    if (url.includes('/api/chat')) {
      chatCalls += 1;
      sentMessage = JSON.parse(options.body).message;
      return new Response(JSON.stringify({ reply: 'All good!', mode: 'VIBE' }), { status: 200 });
    }
    return new Response(JSON.stringify({ status: 'ok' }), { status: 200 });
  };
  try {
    const mod = await loadModule('/src/components/ChatWindow.jsx');
    const onComposerModeChange = () => { onComposerModeChange.called = true; };
    render(React.createElement(mod.default, { composerMode: 'voice', onComposerModeChange, muted: true }));
    await waitFor(() => assert.ok(screen.getByRole('group', { name: 'Voice recording' })));

    fireEvent.click(screen.getByText('Done'));

    await waitFor(() => assert.equal(chatCalls, 1, 'finishing a recording must auto-send it'));
    assert.equal(sentMessage, 'Hi, how are you, ki haal chaal?');
    await waitFor(() => assert.ok(screen.getByText('All good!')), 'BUD\'s reply is shown');
    assert.equal(screen.queryByPlaceholderText(/Tell BUD what/), null, 'no editable text composer ever appears in voice mode');
    assert.equal(onComposerModeChange.called, undefined, 'mode never switches away from voice on a normal finish');

    // Ready for another take, not stuck mid-flow.
    await waitFor(() => assert.ok(screen.getByText('Tap to talk')));
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test('voice mode waits for BUD to finish speaking before offering to record again', async () => {
  // Unlike text mode, voice mode deliberately stays busy until speech playback actually ends,
  // so the mic doesn't reopen while BUD is still talking -- protects the split between text
  // mode's "clear immediately" fix and voice mode's intentional "wait for speech" behavior.
  installFakeMediaRecorder();
  const fakeAudio = installFakeAudio();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    if (url.includes('/api/transcribe')) return new Response(JSON.stringify({ transcript: 'Hello', language: 'english' }), { status: 200 });
    if (url.includes('/api/speak')) return new Response(new Blob(['fake wav bytes'], { type: 'audio/wav' }), { status: 200 });
    return new Response(JSON.stringify({ reply: 'Hi there!', mode: 'VIBE' }), { status: 200 });
  };
  try {
    const mod = await loadModule('/src/components/ChatWindow.jsx');
    render(React.createElement(mod.default, { composerMode: 'voice', onComposerModeChange: () => {}, muted: false }));
    await waitFor(() => assert.ok(screen.getByRole('group', { name: 'Voice recording' })));

    fireEvent.click(screen.getByText('Done'));
    await waitFor(() => assert.equal(fakeAudio.instances.length, 1, 'speech should have started'));

    // Still speaking -- must not yet be back to "ready to record again".
    assert.equal(screen.queryByText('Tap to talk'), null, 'must not be ready again while still speaking');

    fakeAudio.instances[0].onended();
    await waitFor(() => assert.ok(screen.getByText('Tap to talk')));
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test('cancelling mid-recording in voice mode returns to a ready-to-talk state, not text mode', async () => {
  installFakeMediaRecorder();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = fetchJson({ status: 'ok' });
  try {
    const mod = await loadModule('/src/components/ChatWindow.jsx');
    const onComposerModeChange = () => { onComposerModeChange.called = true; };
    render(React.createElement(mod.default, { composerMode: 'voice', onComposerModeChange, muted: true }));
    await waitFor(() => assert.ok(screen.getByText('Cancel')));

    fireEvent.click(screen.getByText('Cancel'));

    await waitFor(() => assert.ok(screen.getByText('Tap to talk')));
    assert.equal(onComposerModeChange.called, undefined, 'a normal cancel must not fall back to text mode');
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test('cancelling a recording stops the microphone stream', async () => {
  const stream = installFakeMediaRecorder();
  try {
    const mod = await loadModule('/src/components/RecordingPanel.jsx');
    render(React.createElement(mod.default, { onTranscribed: () => {}, onCancel: () => {} }));
    await waitFor(() => assert.ok(screen.getByText('Cancel')));
    fireEvent.click(screen.getByText('Cancel'));
    assert.equal(stream._track.stopped, true, 'the microphone track must be stopped on cancel');
  } finally {
    cleanup();
  }
});

test('unmounting the recording panel mid-recording cleans up the microphone stream', async () => {
  const stream = installFakeMediaRecorder();
  try {
    const mod = await loadModule('/src/components/RecordingPanel.jsx');
    const { unmount } = render(React.createElement(mod.default, { onTranscribed: () => {}, onCancel: () => {} }));
    await waitFor(() => assert.ok(screen.getByText('Pause')));
    unmount();
    assert.equal(stream._track.stopped, true, 'unmounting must stop the microphone track, not leave it live');
  } finally {
    cleanup();
  }
});

test('opening an overlay traps Tab focus inside it and restores focus on close', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async url => {
    if (url.includes('/api/preferences')) return new Response(JSON.stringify({ warmth: 70, humour: 35, sarcasm: 10, directness: 60 }), { status: 200 });
    if (url.includes('/api/memories')) return new Response(JSON.stringify([]), { status: 200 });
    return new Response(JSON.stringify({ status: 'ok' }), { status: 200 });
  };
  try {
    const mod = await loadModule('/src/App.jsx');
    render(React.createElement(mod.default));
    const opener = screen.getByText('Parameters');
    opener.focus();
    fireEvent.click(opener);
    await waitFor(() => assert.ok(screen.getByRole('dialog', { name: 'Parameters' })));

    const dialog = screen.getByRole('dialog', { name: 'Parameters' });
    const focusable = dialog.querySelectorAll('a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])');
    assert.ok(focusable.length > 0, 'the dialog has at least one focusable control');
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    // Shift+Tab from the first element must wrap to the last, not escape to the page behind it.
    first.focus();
    fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true });
    assert.equal(document.activeElement, last, 'Shift+Tab from the first control wraps to the last');

    // Tab from the last element must wrap back to the first.
    fireEvent.keyDown(dialog, { key: 'Tab' });
    assert.equal(document.activeElement, first, 'Tab from the last control wraps to the first');

    fireEvent.click(screen.getByLabelText('Close'));
    await waitFor(() => assert.equal(screen.queryByRole('dialog'), null));
    assert.equal(document.activeElement, opener, 'focus returns to the button that opened the overlay');
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test('Parameters opens the existing personality controls in an overlay', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async url => {
    if (url.includes('/api/preferences')) return new Response(JSON.stringify({ warmth: 70, humour: 35, sarcasm: 10, directness: 60 }), { status: 200 });
    if (url.includes('/api/memories')) return new Response(JSON.stringify([]), { status: 200 });
    return new Response(JSON.stringify({ status: 'ok' }), { status: 200 });
  };
  try {
    const mod = await loadModule('/src/App.jsx');
    render(React.createElement(mod.default));
    assert.equal(screen.queryByRole('dialog'), null, 'closed by default');
    fireEvent.click(screen.getByText('Parameters'));
    await waitFor(() => assert.ok(screen.getByRole('dialog', { name: 'Parameters' })));
    assert.ok(screen.getByText('Warmth'), 'personality sliders are shown, expanded, inside the overlay');
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test('the composer clears as soon as the reply arrives, without waiting for speech to finish', async () => {
  // Regression test: the composer previously stayed re-editable-but-still-full of the old
  // message until BUD finished speaking, because clearing it was awaited on the same promise
  // as TTS playback -- forcing the user to manually delete old text before typing the next
  // message. It must clear the moment the reply is known, not once BUD stops talking.
  const fakeAudio = installFakeAudio();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async url => {
    if (url.includes('/api/speak')) return new Response(new Blob(['fake wav bytes'], { type: 'audio/wav' }), { status: 200 });
    return new Response(JSON.stringify({ reply: 'Hey there!', mode: 'VIBE' }), { status: 200 });
  };
  try {
    const mod = await loadModule('/src/components/ChatWindow.jsx');
    render(React.createElement(mod.default, {
      composerMode: 'text', onComposerModeChange: () => {}, muted: false, onSpeakingChange: () => {},
    }));
    const textarea = screen.getByPlaceholderText(/Tell BUD what/);
    fireEvent.change(textarea, { target: { value: 'Hi' } });
    fireEvent.click(screen.getByLabelText('Send message'));

    await waitFor(() => assert.ok(screen.getByText('Hey there!')));
    // Speech is still in flight (never fired onended) -- the composer must already be clear.
    assert.equal(fakeAudio.instances.length, 1, 'speech should have started');
    assert.equal(textarea.value, '', 'the composer must clear without waiting for speech to finish');
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test('a reply is spoken aloud when unmuted, and reports speaking state through its lifecycle', async () => {
  const fakeAudio = installFakeAudio();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async url => {
    if (url.includes('/api/speak')) return new Response(new Blob(['fake wav bytes'], { type: 'audio/wav' }), { status: 200 });
    return new Response(JSON.stringify({ reply: 'Hey there!', mode: 'VIBE' }), { status: 200 });
  };
  try {
    const mod = await loadModule('/src/components/ChatWindow.jsx');
    const speakingStates = [];
    render(React.createElement(mod.default, {
      composerMode: 'text', onComposerModeChange: () => {}, muted: false, onSpeakingChange: value => speakingStates.push(value),
    }));
    fireEvent.change(screen.getByPlaceholderText(/Tell BUD what/), { target: { value: 'Hi' } });
    fireEvent.click(screen.getByLabelText('Send message'));

    await waitFor(() => assert.equal(fakeAudio.instances.length, 1));
    assert.equal(fakeAudio.instances[0].played, true);
    assert.deepEqual(speakingStates, [true]);

    fakeAudio.instances[0].onended();
    assert.deepEqual(speakingStates, [true, false]);
    assert.equal(fakeAudio.revoked.length, 1, 'the object URL must be released once playback ends');
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test('muting BUD skips speaking the reply entirely', async () => {
  const fakeAudio = installFakeAudio();
  const originalFetch = globalThis.fetch;
  let speakCalls = 0;
  globalThis.fetch = async url => {
    if (url.includes('/api/speak')) { speakCalls += 1; return new Response(new Blob(['x']), { status: 200 }); }
    return new Response(JSON.stringify({ reply: 'Hey there!', mode: 'VIBE' }), { status: 200 });
  };
  try {
    const mod = await loadModule('/src/components/ChatWindow.jsx');
    render(React.createElement(mod.default, {
      composerMode: 'text', onComposerModeChange: () => {}, muted: true, onSpeakingChange: () => {},
    }));
    fireEvent.change(screen.getByPlaceholderText(/Tell BUD what/), { target: { value: 'Hi' } });
    fireEvent.click(screen.getByLabelText('Send message'));

    await waitFor(() => assert.ok(screen.getByText('Hey there!')));
    assert.equal(speakCalls, 0, 'muted must never call /api/speak');
    assert.equal(fakeAudio.instances.length, 0);
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test('a TTS failure is shown, not silently swallowed, and never blocks the text reply', async () => {
  installFakeAudio();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async url => {
    if (url.includes('/api/speak')) {
      return new Response(JSON.stringify({ error: { message: 'The TTS model needs one-time terms acceptance in the Groq console.' } }), { status: 503 });
    }
    return new Response(JSON.stringify({ reply: 'Hey there!', mode: 'VIBE' }), { status: 200 });
  };
  try {
    const mod = await loadModule('/src/components/ChatWindow.jsx');
    render(React.createElement(mod.default, {
      composerMode: 'text', onComposerModeChange: () => {}, muted: false, onSpeakingChange: () => {},
    }));
    fireEvent.change(screen.getByPlaceholderText(/Tell BUD what/), { target: { value: 'Hi' } });
    fireEvent.click(screen.getByLabelText('Send message'));

    await waitFor(() => assert.ok(screen.getByText('Hey there!'))); // the text reply is unaffected
    await waitFor(() => assert.match(screen.getByText(/terms acceptance/).textContent, /terms acceptance/));
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test('the three-dot menu opens "Your space, taking shape"', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = fetchJson({ status: 'ok' });
  try {
    const mod = await loadModule('/src/App.jsx');
    render(React.createElement(mod.default));
    fireEvent.click(screen.getByLabelText('More options'));
    fireEvent.click(screen.getByRole('menuitem', { name: /Your space, taking shape/ }));
    await waitFor(() => assert.ok(screen.getByRole('dialog', { name: 'Your space, taking shape' })));
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test('choosing Write reveals the central orb above the chat, matching the existing text-mode layout', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = fetchJson({ status: 'ok' });
  try {
    const mod = await loadModule('/src/App.jsx');
    const { container } = render(React.createElement(mod.default));
    assert.equal(container.querySelector('.orb-stage'), null, 'no orb on the landing view');

    fireEvent.click(screen.getByText(/Write what.s on your mind/));
    await waitFor(() => assert.ok(container.querySelector('.orb-stage.orb-state-idle')));
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test("choosing Let's talk directly from landing shows the two-column voice layout with BUD's orb", async () => {
  installFakeMediaRecorder();
  const originalFetch = globalThis.fetch;
  globalThis.fetch = fetchJson({ status: 'ok' });
  try {
    const mod = await loadModule('/src/App.jsx');
    const { container } = render(React.createElement(mod.default));

    fireEvent.click(screen.getByText(/Let.s talk/));
    await waitFor(() => assert.ok(screen.getByRole('group', { name: 'Voice recording' })));
    assert.ok(container.querySelector('.voice-stage'), 'the two-column voice layout is used');
    assert.ok(container.querySelector('.orb-card .orb-stage'), "BUD's orb sits in its own card");
  } finally {
    cleanup();
    globalThis.fetch = originalFetch;
  }
});

test('BUD responding animates the central orb into the responding state', async () => {
  try {
    const mod = await loadModule('/src/components/BudOrb.jsx');
    const { container, rerender } = render(React.createElement(mod.default, { state: 'idle' }));
    assert.ok(container.querySelector('.orb-state-idle'));
    rerender(React.createElement(mod.default, { state: 'responding' }));
    assert.ok(container.querySelector('.orb-state-responding'));
  } finally {
    cleanup();
  }
});
