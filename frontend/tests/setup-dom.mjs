import { JSDOM } from 'jsdom';

export function installDom() {
  const dom = new JSDOM('<!doctype html><html><body></body></html>', { url: 'http://localhost/' });
  const { window } = dom;
  // Node 22+ ships its own read-only `navigator`/`crypto` globals; redefine rather than assign.
  const define = (name, value) => Object.defineProperty(global, name, { value, writable: true, configurable: true });
  define('window', window);
  define('document', window.document);
  define('navigator', window.navigator);
  define('HTMLElement', window.HTMLElement);
  define('Node', window.Node);
  define('customElements', window.customElements);
  define('requestAnimationFrame', callback => setTimeout(() => callback(Date.now()), 16));
  define('cancelAnimationFrame', id => clearTimeout(id));
  // jsdom does not implement layout/scrolling; ChatWindow calls this on every message update.
  window.HTMLElement.prototype.scrollIntoView = () => {};
  // Node's own built-in `crypto.randomUUID()` already works and is left untouched.
  return dom;
}

// A minimal fake MediaStream whose track records whether it was stopped -- used to verify
// microphone cleanup on cancel/unmount without needing a real getUserMedia implementation.
export function createFakeStream() {
  const track = { stopped: false };
  track.stop = () => { track.stopped = true; };
  return { getTracks: () => [track], _track: track };
}

// A minimal fake MediaRecorder supporting start/stop/pause/resume and firing ondataavailable
// once per "chunk" so RecordingPanel's real logic (not a mock of RecordingPanel itself) runs.
//
// `freshStreamPerCall` + `getUserMediaDelayMs` let a test reproduce React.StrictMode's
// double-invoke race: each getUserMedia() call returns its own stream (pushed to `streams`)
// after a delay, so a test can mount, let StrictMode unmount+remount, and then inspect which
// stream(s) ended up stopped vs. still live.
export function installFakeMediaRecorder({ shouldRejectGetUserMedia, freshStreamPerCall, getUserMediaDelayMs = 0 } = {}) {
  const stream = createFakeStream();
  // Only track `stream` itself when getUserMedia actually hands it out (the simple, single-call
  // case other tests rely on) -- with freshStreamPerCall it's an unused placeholder, never
  // returned to any caller, and must not be counted as a phantom "live" stream.
  const streams = freshStreamPerCall ? [] : [stream];
  window.navigator.mediaDevices = {
    getUserMedia: async () => {
      if (getUserMediaDelayMs) await new Promise(resolve => setTimeout(resolve, getUserMediaDelayMs));
      if (shouldRejectGetUserMedia) {
        const error = new Error('denied');
        error.name = 'NotAllowedError';
        throw error;
      }
      if (!freshStreamPerCall) return stream;
      const next = createFakeStream();
      streams.push(next);
      return next;
    },
  };

  class FakeMediaRecorder {
    constructor() {
      this.state = 'inactive';
      this.ondataavailable = null;
      this.onstop = null;
    }
    start() { this.state = 'recording'; }
    pause() { this.state = 'paused'; }
    resume() { this.state = 'recording'; }
    stop() {
      this.state = 'inactive';
      this.ondataavailable?.({ data: { size: 10 } });
      this.onstop?.();
    }
    static isTypeSupported() { return true; }
  }
  window.MediaRecorder = FakeMediaRecorder;
  global.MediaRecorder = FakeMediaRecorder;

  class FakeAnalyserNode {
    constructor() { this.fftSize = 128; this.frequencyBinCount = 64; }
    getByteFrequencyData(array) { array.fill(0); }
  }
  class FakeAudioContext {
    constructor() { this.state = 'running'; }
    createMediaStreamSource() { return { connect: () => {} }; }
    createAnalyser() { return new FakeAnalyserNode(); }
    close() { this.state = 'closed'; return Promise.resolve(); }
  }
  window.AudioContext = FakeAudioContext;
  global.AudioContext = FakeAudioContext;

  return Object.assign(stream, { streams });
}

// A fake `Audio` element and object-URL pair -- jsdom implements neither real playback nor
// blob URLs meaningfully. `instances` lets a test inspect/drive playback (fire onended, etc.).
export function installFakeAudio() {
  const instances = [];
  class FakeAudioElement {
    constructor(url) {
      this.url = url;
      this.onended = null;
      this.onerror = null;
      this.played = false;
      this.paused = true;
      instances.push(this);
    }
    play() { this.played = true; this.paused = false; return Promise.resolve(); }
    pause() { this.paused = true; }
  }
  window.Audio = FakeAudioElement;
  global.Audio = FakeAudioElement;
  let nextUrl = 0;
  const revoked = [];
  window.URL.createObjectURL = () => `blob:fake-${nextUrl++}`;
  window.URL.revokeObjectURL = url => revoked.push(url);
  // Node's own global URL already supports the constructor; just patch on the two blob methods
  // it lacks, rather than replacing the whole (possibly read-only) global.
  global.URL.createObjectURL = window.URL.createObjectURL;
  global.URL.revokeObjectURL = window.URL.revokeObjectURL;
  return { instances, revoked };
}
