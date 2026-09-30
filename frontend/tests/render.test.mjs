import assert from 'node:assert/strict';
import test from 'node:test';
import React from 'react';
import { renderToString } from 'react-dom/server';
import { createServer } from 'vite';

test('App renders through the configured JSX transform without runtime errors, landing on the hero view', async () => {
  const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
  try {
    const { default: App } = await server.ssrLoadModule('/src/App.jsx');
    const html = renderToString(React.createElement(App));
    assert.match(html, /Room to breathe/);
    // The landing view shows only the hero text -- no composer or chat log until a mode is chosen.
    assert.doesNotMatch(html, /Send message/);
    assert.doesNotMatch(html, /Messages and recent context go to Groq/);
  } finally {
    await server.close();
  }
});

test('the permanent sidebar is gone; the full-page voice-first layout is used instead', async () => {
  const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
  try {
    const { default: App } = await server.ssrLoadModule('/src/App.jsx');
    const html = renderToString(React.createElement(App));
    assert.doesNotMatch(html, /<aside/);
    assert.match(html, /action-band/);
  } finally {
    await server.close();
  }
});

test('the three-action band exposes Write, Let\'s talk and Parameters', async () => {
  const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
  try {
    const { default: ActionBand } = await server.ssrLoadModule('/src/components/ActionBand.jsx');
    const html = renderToString(React.createElement(ActionBand, { mode: 'text', onWrite() {}, onTalk() {}, onParameters() {} }));
    assert.match(html, /Write what.{1,6}s on your mind/);
    assert.match(html, /Let.{1,6}s talk/);
    assert.match(html, /Parameters/);
  } finally {
    await server.close();
  }
});

test('ProfileMenu renders a closed overflow menu by default', async () => {
  const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
  try {
    const { default: ProfileMenu } = await server.ssrLoadModule('/src/components/ProfileMenu.jsx');
    const html = renderToString(React.createElement(ProfileMenu, { onOpenSpace() {} }));
    assert.match(html, /aria-expanded="false"/);
    assert.doesNotMatch(html, /Your space, taking shape/);
  } finally {
    await server.close();
  }
});

test('chat client sends contract data and surfaces backend errors', async () => {
  const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
  const originalFetch = globalThis.fetch;
  try {
    const { sendChat } = await server.ssrLoadModule('/src/services/api.js');
    const payload = { session_id: 'some-uuid', message: 'Hello', history: [] };
    globalThis.fetch = async (url, options) => {
      assert.match(url, /\/api\/chat$/);
      assert.equal(options.method, 'POST');
      assert.deepEqual(JSON.parse(options.body), payload);
      assert.equal(options.headers['Content-Type'], 'application/json');
      assert.ok(options.headers['X-Owner-Token'], 'expected an owner token header');
      return new Response(JSON.stringify({ reply: 'Hello there', mode: 'VIBE' }), { status: 200 });
    };
    assert.equal((await sendChat(payload)).reply, 'Hello there');
    globalThis.fetch = async () => new Response(JSON.stringify({ error: { message: 'Provider is busy' } }), { status: 429 });
    await assert.rejects(sendChat(payload), /Provider is busy/);
    globalThis.fetch = async () => new Response(JSON.stringify({ reply: '', mode: 'INVALID' }), { status: 200 });
    await assert.rejects(sendChat(payload), /incomplete response/);
    globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); };
    await assert.rejects(sendChat(payload), /Cannot reach BUD/);
  } finally {
    globalThis.fetch = originalFetch;
    await server.close();
  }
});

test('transcribeAudio sends multipart form data and surfaces backend errors', async () => {
  const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
  const originalFetch = globalThis.fetch;
  try {
    const { transcribeAudio } = await server.ssrLoadModule('/src/services/api.js');
    const blob = new Blob(['fake audio bytes'], { type: 'audio/webm' });
    globalThis.fetch = async (url, options) => {
      assert.match(url, /\/api\/transcribe$/);
      assert.equal(options.method, 'POST');
      assert.ok(options.body instanceof FormData, 'expected a multipart FormData body');
      assert.equal(options.headers, undefined, 'must not set Content-Type manually for multipart uploads');
      return new Response(JSON.stringify({ transcript: 'Hello there', language: 'english' }), { status: 200 });
    };
    assert.equal((await transcribeAudio(blob)).transcript, 'Hello there');
    globalThis.fetch = async () => new Response(JSON.stringify({ error: { message: 'Provider is busy' } }), { status: 429 });
    await assert.rejects(transcribeAudio(blob), /Provider is busy/);
    globalThis.fetch = async () => new Response(JSON.stringify({ transcript: '  ' }), { status: 200 });
    await assert.rejects(transcribeAudio(blob), /could not make out any speech/);
  } finally {
    globalThis.fetch = originalFetch;
    await server.close();
  }
});
