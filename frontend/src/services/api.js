import { getOwnerToken } from './identity';

const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

function authHeaders() {
  return { 'Content-Type': 'application/json', 'X-Owner-Token': getOwnerToken() };
}

export async function checkHealth(signal) {
  const response = await fetch(`${baseUrl}/health`, { signal });
  if (!response.ok) throw new Error('Health request failed');
  const data = await response.json();
  if (data.status !== 'ok') throw new Error('Unexpected health response');
  return data;
}

export async function sendChat(payload, signal) {
  let response;
  try {
    response = await fetch(`${baseUrl}/api/chat`, {
      method: 'POST', headers: authHeaders(),
      body: JSON.stringify(payload), signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Cannot reach BUD. Check the backend connection and try again.');
  }
  let data;
  try { data = await response.json(); } catch { throw new Error('BUD returned an unreadable response. Please try again.'); }
  if (!response.ok) throw new Error(data.error?.message || 'BUD could not reply. Please try again.');
  if (typeof data.reply !== 'string' || !data.reply.trim() || !['LISTEN', 'HELP', 'REALITY_CHECK', 'LEARN', 'VIBE'].includes(data.mode)) {
    throw new Error('BUD returned an incomplete response. Please try again.');
  }
  return data;
}

export async function transcribeAudio(blob, signal) {
  const form = new FormData();
  form.append('audio', blob, `recording.${blob.type.includes('ogg') ? 'ogg' : 'webm'}`);
  let response;
  try {
    // No Content-Type header here: the browser sets multipart/form-data with the correct boundary.
    response = await fetch(`${baseUrl}/api/transcribe`, { method: 'POST', body: form, signal });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Cannot reach BUD. Check the backend connection and try again.');
  }
  let data;
  try { data = await response.json(); } catch { throw new Error('BUD returned an unreadable response. Please try again.'); }
  if (!response.ok) throw new Error(data.error?.message || 'Could not transcribe that recording. Please try again.');
  if (typeof data.transcript !== 'string' || !data.transcript.trim()) {
    throw new Error('BUD could not make out any speech in that recording.');
  }
  return data;
}

export async function speakText(text, signal) {
  const response = await fetch(`${baseUrl}/api/speak`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }), signal,
  });
  if (!response.ok) {
    let message = 'Could not speak that reply.';
    try { message = (await response.json()).error?.message || message; } catch { /* keep default */ }
    throw new Error(message);
  }
  return response.blob();
}

export async function getPreferences() {
  const response = await fetch(`${baseUrl}/api/preferences`, { headers: authHeaders() });
  if (!response.ok) throw new Error('Could not load your preferences.');
  return response.json();
}

export async function putPreferences(values) {
  const response = await fetch(`${baseUrl}/api/preferences`, {
    method: 'PUT', headers: authHeaders(), body: JSON.stringify(values),
  });
  if (!response.ok) throw new Error('Could not save your preferences.');
  return response.json();
}

export async function listMemories() {
  const response = await fetch(`${baseUrl}/api/memories`, { headers: authHeaders() });
  if (!response.ok) throw new Error('Could not load remembered items.');
  return response.json();
}

export async function approveMemory(id) {
  const response = await fetch(`${baseUrl}/api/memory-candidates/${id}/approve`, { method: 'POST', headers: authHeaders() });
  if (!response.ok) throw new Error('Could not save that memory.');
  return response.json();
}

export async function rejectMemory(id) {
  const response = await fetch(`${baseUrl}/api/memory-candidates/${id}/reject`, { method: 'POST', headers: authHeaders() });
  if (!response.ok) throw new Error('Could not dismiss that suggestion.');
  return response.json();
}

export async function deleteMemory(id) {
  const response = await fetch(`${baseUrl}/api/memories/${id}`, { method: 'DELETE', headers: authHeaders() });
  if (!response.ok) throw new Error('Could not delete that memory.');
}
