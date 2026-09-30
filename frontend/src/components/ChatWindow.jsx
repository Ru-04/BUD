import React, { useEffect, useRef, useState } from 'react';
import { sendChat, speakText } from '../services/api';
import { MemoryPrompt } from './MemoryPrompt';
import RecordingPanel from './RecordingPanel';
import BudOrb from './BudOrb';

export default function ChatWindow({ composerMode, onComposerModeChange, onMemoryResolved, onPendingChange, muted, onSpeakingChange }) {
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [turns, setTurns] = useState([]);
  const [draft, setDraft] = useState('');
  const [pending, setPending] = useState(false);
  const [speaking, setSpeakingState] = useState(false);
  const [error, setError] = useState('');
  const [memoryCandidate, setMemoryCandidate] = useState(null);
  const [speakError, setSpeakError] = useState('');
  // Voice mode's own turn-taking state, independent of the text composer: 'capturing' (mic is
  // live), 'processing' (transcribing/sending/speaking, mic is off) or 'ready' (waiting for the
  // next tap). RecordingPanel is only ever mounted during 'capturing', so each return to it is a
  // genuinely fresh instance -- no manual reset needed.
  const [voicePhase, setVoicePhase] = useState('capturing');
  const inFlight = useRef(false);
  const controller = useRef(null);
  const end = useRef(null);
  const input = useRef(null);
  const audio = useRef(null);
  const audioUrl = useRef(null);

  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => { end.current?.scrollIntoView({ block: 'nearest' }); }, [turns, pending, error]);
  useEffect(() => { onPendingChange?.(pending); }, [pending, onPendingChange]);

  function setSpeaking(value) {
    setSpeakingState(value);
    onSpeakingChange?.(value);
  }

  function stopSpeaking() {
    const wasSpeaking = Boolean(audio.current);
    if (audio.current) { audio.current.pause(); audio.current = null; }
    if (audioUrl.current) { URL.revokeObjectURL(audioUrl.current); audioUrl.current = null; }
    if (wasSpeaking) setSpeaking(false);
  }

  useEffect(() => stopSpeaking, []); // stop any playback if the window unmounts mid-speech

  // Don't let BUD's voice overlap with the user's own recording once they start talking, and
  // start voice mode ready to listen immediately (matches "Let's talk" being a deliberate tap).
  useEffect(() => {
    if (composerMode === 'voice') {
      stopSpeaking();
      setVoicePhase('capturing');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [composerMode]);

  // Resolves once playback actually finishes (or fails), not merely once it starts, so a caller
  // can wait for BUD to be done talking before moving on (voice mode's next turn depends on this).
  function speakReply(text) {
    stopSpeaking(); // never overlap two replies speaking at once
    setSpeakError('');
    return new Promise(resolve => {
      (async () => {
        try {
          const blob = await speakText(text);
          const url = URL.createObjectURL(blob);
          audioUrl.current = url;
          const element = new Audio(url);
          audio.current = element;
          element.onended = () => { stopSpeaking(); resolve(); };
          element.onerror = () => { stopSpeaking(); resolve(); };
          setSpeaking(true);
          await element.play();
        } catch (err) {
          // TTS is an optional layer on top of the text reply, which is already shown either way
          // -- but a silent failure is confusing ("why doesn't BUD talk?"), so surface it quietly
          // instead of only logging it, without blocking or altering the chat flow itself.
          stopSpeaking();
          setSpeakError(err.message || 'Could not speak that reply.');
          resolve();
        }
      })();
    });
  }

  async function sendMessage(message) {
    const trimmed = message.trim();
    if (!trimmed || inFlight.current) return null;
    inFlight.current = true;
    setPending(true);
    setError('');
    controller.current = new AbortController();
    const timeout = setTimeout(() => controller.current?.abort(), 60000);
    // Keep completed pairs only, bounded by the backend's character budget.
    let history = turns.slice(-12).map(({ role, content }) => ({ role, content }));
    while (history.reduce((total, turn) => total + turn.content.length, 0) > 24000) history = history.slice(2);
    let reply = null;
    try {
      const result = await sendChat({ session_id: sessionId, message: trimmed, history }, controller.current.signal);
      setTurns(previous => [...previous, { role: 'user', content: trimmed }, { role: 'assistant', content: result.reply, mode: result.mode }]);
      if (result.memory_candidate) setMemoryCandidate(result.memory_candidate);
      reply = result.reply;
    } catch (err) {
      setError(err.name === 'AbortError' ? 'The request timed out. Your message is still here; try again.' : err.message);
    } finally {
      clearTimeout(timeout);
      inFlight.current = false;
      setPending(false);
    }
    if (reply && !muted) await speakReply(reply);
    return reply;
  }

  async function submit(event) {
    event.preventDefault();
    const message = draft.trim();
    if (!message) return;
    const reply = await sendMessage(message);
    if (reply !== null) setDraft('');
    input.current?.focus();
  }

  function reset() {
    stopSpeaking();
    setTurns([]);
    setDraft('');
    setError('');
    setSpeakError('');
    setSessionId(crypto.randomUUID());
    if (composerMode === 'voice') setVoicePhase('capturing');
    input.current?.focus();
  }

  // Pure voice mode: a finished recording sends itself immediately -- no editable composer, no
  // transcript bubble, no separate "now press send" step. Mic goes off (RecordingPanel unmounts)
  // while BUD replies, then the view returns to a ready-to-talk-again state.
  async function handleTranscribed(text) {
    setVoicePhase('processing');
    await sendMessage(text);
    setVoicePhase('ready');
  }

  const memoryPrompt = memoryCandidate && (
    <MemoryPrompt
      candidate={memoryCandidate}
      onResolved={action => { setMemoryCandidate(null); onMemoryResolved?.(action); }}
    />
  );

  if (composerMode === 'voice') {
    const lastReply = [...turns].reverse().find(turn => turn.role === 'assistant');
    const orbState = (pending || speaking) ? 'responding' : voicePhase === 'capturing' ? 'recording' : 'idle';
    const status = pending
      ? 'BUD is thinking…'
      : speaking
        ? 'BUD is speaking'
        : voicePhase === 'processing'
          ? 'Transcribing…'
          : voicePhase === 'ready'
            ? 'Tap to talk again'
            : '';
    return (
      <div className="voice-stage">
        <div className="voice-column voice-column-status">
          <div className="chat-heading"><span>LET'S TALK</span><button className="reset" onClick={reset} disabled={pending}>Clear chat</button></div>
          {memoryPrompt}
          {lastReply && <p className="voice-reply">{lastReply.content}</p>}
          {status && <p className="voice-status" role="status" aria-live="polite">{status}</p>}
          {voicePhase === 'ready' && (
            <button type="button" className="talk-button" onClick={() => setVoicePhase('capturing')}>
              <span aria-hidden="true">🎙</span> Tap to talk
            </button>
          )}
          {voicePhase === 'capturing' && (
            <RecordingPanel
              onTranscribed={handleTranscribed}
              onCancel={() => setVoicePhase('ready')}
              onGiveUp={() => onComposerModeChange('text')}
            />
          )}
          {error && <p className="chat-error" role="alert">{error}</p>}
          {speakError && <p className="speak-note" role="status">🔇 {speakError}</p>}
          <p className="local-note">Messages and recent context go to Groq to generate replies. This tab’s visible conversation clears on refresh, but your messages, preferences, and any approved memories are stored on BUD’s server, tied to this device, and kept indefinitely — you can forget individual memories any time in Parameters. Groq’s own data policies apply. BUD is an AI, not a therapist or emergency service.</p>
        </div>
        <div className="voice-column voice-column-orb">
          <div className="orb-card"><BudOrb state={orbState} /></div>
        </div>
      </div>
    );
  }

  return <div className="chat-window">
    <div className="chat-heading"><span>THIS CONVERSATION</span><button className="reset" onClick={reset} disabled={pending}>Clear chat</button></div>
    <div className="messages" role="log" aria-label="Conversation" aria-live="polite">
      {turns.length === 0 && <p className="empty-chat">What’s on your mind? You can write or talk, in English or Hinglish.</p>}
      {turns.map((turn, index) => <article key={index} className={`message ${turn.role}`}>
        <span className="message-author">{turn.role === 'user' ? 'You' : `BUD · ${turn.mode.replaceAll('_', ' ')}`}</span>
        <p>{turn.content}</p>
      </article>)}
      {pending && <p className="thinking" role="status">BUD is thinking…</p>}
      <div ref={end} />
    </div>
    {memoryPrompt}
    <form className="composer" onSubmit={submit} aria-busy={pending}>
      <label htmlFor="message">Your message</label>
      <div className="composer-row"><textarea ref={input} id="message" value={draft} maxLength={4000} rows={2} readOnly={pending} placeholder="Tell BUD what’s on your mind…" onChange={event => setDraft(event.target.value)} onKeyDown={event => {
        if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form.requestSubmit(); }
      }} /><button type="submit" disabled={pending || !draft.trim()} aria-label="Send message">↑</button></div>
      <small className="input-hint">Enter to send · Shift+Enter for a new line · {draft.length}/4000</small>
    </form>
    {error && <p className="chat-error" role="alert">{error}</p>}
    {speakError && <p className="speak-note" role="status">🔇 {speakError}</p>}
    <p className="local-note">Messages and recent context go to Groq to generate replies. This tab’s visible conversation clears on refresh, but your messages, preferences, and any approved memories are stored on BUD’s server, tied to this device, and kept indefinitely — you can forget individual memories any time in Parameters. Groq’s own data policies apply. BUD is an AI, not a therapist or emergency service.</p>
  </div>;
}
