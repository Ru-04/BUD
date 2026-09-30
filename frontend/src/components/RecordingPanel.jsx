import React, { useEffect, useRef, useState } from 'react';
import { transcribeAudio } from '../services/api';

const MAX_RECORDING_MS = 120000; // 2 minutes
const BAR_COUNT = 24;
const PREFERRED_MIME_TYPES = ['audio/webm', 'audio/ogg', 'audio/mp4'];

// state: 'requesting_mic' | 'recording' | 'paused' | 'transcribing' | 'error'
export default function RecordingPanel({ onTranscribed, onCancel, onGiveUp }) {
  const [state, setState] = useState('requesting_mic');
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState('');
  const recorder = useRef(null);
  const stream = useRef(null);
  const chunks = useRef([]);
  const audioContext = useRef(null);
  const analyser = useRef(null);
  const rafId = useRef(null);
  const barRefs = useRef([]);
  const tick = useRef(null);
  const autoStop = useRef(null);
  // A monotonic counter, not a boolean: React.StrictMode deliberately mounts this effect,
  // cleans it up, then mounts it again in development. A boolean "cancelled" flag gets reset
  // by the second mount before the first mount's in-flight getUserMedia() promise resolves,
  // so the stale first attempt would attach its stream/recorder anyway -- a second, orphaned,
  // uncontrolled MediaRecorder that Pause/Cancel/Stop never touch (the mic keeps recording
  // through "pause" because it's actually a *different* recorder instance). Comparing against
  // the live counter instead of a value captured before the async call closes that race.
  const generation = useRef(0);

  function cleanup() {
    // Invalidate any in-flight start() too (e.g. the permission prompt is still pending when
    // this instance is torn down) so it discards its stream instead of attaching it late.
    generation.current += 1;
    clearInterval(tick.current);
    clearTimeout(autoStop.current);
    if (rafId.current) cancelAnimationFrame(rafId.current);
    if (recorder.current && recorder.current.state !== 'inactive') {
      recorder.current.ondataavailable = null;
      recorder.current.onstop = null;
      recorder.current.stop();
    }
    stream.current?.getTracks().forEach(track => track.stop());
    if (audioContext.current && audioContext.current.state !== 'closed') audioContext.current.close();
    recorder.current = null;
    stream.current = null;
    audioContext.current = null;
    analyser.current = null;
  }

  useEffect(() => {
    start();
    return cleanup;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function drawFrame() {
    const node = analyser.current;
    if (!node) return;
    const data = new Uint8Array(node.frequencyBinCount);
    node.getByteFrequencyData(data);
    const bucket = Math.floor(data.length / BAR_COUNT) || 1;
    for (let i = 0; i < BAR_COUNT; i += 1) {
      let sum = 0;
      for (let j = 0; j < bucket; j += 1) sum += data[i * bucket + j] || 0;
      const level = Math.min(1, sum / bucket / 255);
      const bar = barRefs.current[i];
      if (bar) bar.style.transform = `scaleY(${0.12 + level * 0.88})`;
    }
    rafId.current = requestAnimationFrame(drawFrame);
  }

  async function start() {
    generation.current += 1;
    const myGeneration = generation.current;
    setError('');
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setState('error');
      setError('This browser cannot access the microphone. Type your message instead.');
      return;
    }
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      if (myGeneration !== generation.current) {
        // A newer mount (StrictMode's double-invoke, or a fast remount) superseded this call.
        mediaStream.getTracks().forEach(track => track.stop());
        return;
      }
      stream.current = mediaStream;
      const mimeType = PREFERRED_MIME_TYPES.find(type => MediaRecorder.isTypeSupported?.(type));
      const mediaRecorder = new MediaRecorder(mediaStream, mimeType ? { mimeType } : undefined);
      chunks.current = [];
      mediaRecorder.ondataavailable = event => { if (event.data.size > 0) chunks.current.push(event.data); };
      mediaRecorder.onstop = handleFinished;
      recorder.current = mediaRecorder;

      // Visualization only: a separate AnalyserNode tap on the mic stream, never connected to
      // destination (no echo), never stored -- just read every frame and discarded.
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        audioContext.current = new AudioCtx();
        const source = audioContext.current.createMediaStreamSource(mediaStream);
        analyser.current = audioContext.current.createAnalyser();
        analyser.current.fftSize = 128;
        source.connect(analyser.current);
        rafId.current = requestAnimationFrame(drawFrame);
      }

      mediaRecorder.start();
      setState('recording');
      setSeconds(0);
      tick.current = setInterval(() => setSeconds(value => value + 1), 1000);
      autoStop.current = setTimeout(finish, MAX_RECORDING_MS);
    } catch (err) {
      setState('error');
      setError(
        err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError'
          ? 'Microphone permission was denied. Allow access in your browser settings, or type your message instead.'
          : 'Could not access the microphone. Type your message instead.'
      );
    }
  }

  function pause() {
    if (recorder.current?.state !== 'recording') return;
    recorder.current.pause();
    clearInterval(tick.current);
    clearTimeout(autoStop.current);
    if (rafId.current) cancelAnimationFrame(rafId.current);
    setState('paused');
  }

  function resume() {
    if (recorder.current?.state !== 'paused') return;
    recorder.current.resume();
    tick.current = setInterval(() => setSeconds(value => value + 1), 1000);
    autoStop.current = setTimeout(finish, MAX_RECORDING_MS);
    rafId.current = requestAnimationFrame(drawFrame);
    setState('recording');
  }

  function finish() {
    if (recorder.current && recorder.current.state !== 'inactive') recorder.current.stop();
  }

  async function handleFinished() {
    clearInterval(tick.current);
    clearTimeout(autoStop.current);
    if (rafId.current) cancelAnimationFrame(rafId.current);
    stream.current?.getTracks().forEach(track => track.stop());
    if (audioContext.current && audioContext.current.state !== 'closed') audioContext.current.close();
    if (!chunks.current.length) {
      onCancel?.();
      return;
    }
    const blob = new Blob(chunks.current, { type: chunks.current[0].type || 'audio/webm' });
    setState('transcribing');
    try {
      const result = await transcribeAudio(blob);
      onTranscribed(result.transcript);
    } catch (err) {
      setState('error');
      setError(err.message);
    }
  }

  function cancel() {
    cleanup();
    onCancel?.();
  }

  const minutes = String(Math.floor(seconds / 60)).padStart(2, '0');
  const secs = String(seconds % 60).padStart(2, '0');

  return (
    <div className="recording-panel" role="group" aria-label="Voice recording">
      {(state === 'recording' || state === 'paused') && (
        <>
          <div className="waveform" aria-hidden="true">
            {Array.from({ length: BAR_COUNT }).map((_, i) => (
              <span key={i} ref={element => { barRefs.current[i] = element; }} className="waveform-bar" />
            ))}
          </div>
          <div className="recording-meta">
            <span className={`rec-dot ${state === 'paused' ? 'paused' : ''}`} aria-hidden="true" />
            {/* Not aria-live: announcing the running mm:ss once per second would talk over the
                user for the entire recording. A separate, quieter region below announces only
                real state changes (start/pause/resume), which is what's actually useful. */}
            <span className="rec-timer">{minutes}:{secs}</span>
            {state === 'paused' && <span className="rec-paused-label">Paused</span>}
            <span className="sr-only" role="status" aria-live="polite">
              {state === 'paused' ? 'Recording paused' : 'Recording'}
            </span>
          </div>
          <div className="recording-actions">
            {state === 'recording'
              ? <button type="button" onClick={pause}>Pause</button>
              : <button type="button" onClick={resume}>Resume</button>}
            <button type="button" className="primary" onClick={finish}>Done</button>
            <button type="button" className="ghost" onClick={cancel}>Cancel</button>
          </div>
        </>
      )}
      {state === 'requesting_mic' && <p className="hint">Requesting microphone access…</p>}
      {state === 'transcribing' && <p className="hint">Transcribing your recording…</p>}
      {state === 'error' && (
        <>
          <p className="chat-error" role="alert">{error}</p>
          <div className="recording-actions">
            <button type="button" onClick={start}>Try again</button>
            <button type="button" className="ghost" onClick={() => (onGiveUp || onCancel)()}>Type instead</button>
          </div>
        </>
      )}
    </div>
  );
}
