'use strict';

// Service worker for 사장님 콘텐츠비서
// Handles messages from popup that require persistent background processing

chrome.runtime.onInstalled.addListener(() => {
  console.log('사장님 콘텐츠비서 installed');
});

// Message relay: popup sends messages here for operations
// that need to survive popup close (e.g. long-running generations)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message).then(sendResponse).catch(err => {
    sendResponse({ error: err.message || '알 수 없는 오류' });
  });
  return true; // keep channel open for async response
});

async function handleMessage(message) {
  const { apiBase } = await chrome.storage.local.get({ apiBase: 'http://localhost:3000/api' });

  switch (message.type) {
    case 'GENERATE':
      return apiPost(`${apiBase}/generate`, {
        place_url: message.url,
        page_text: message.pageText,
        tones: message.tones,
      });

    case 'MODIFY_CONTENT':
      return apiPost(`${apiBase}/modify`, {
        tab_id: message.tabId,
        content: message.content,
        mode: message.mode,
      });

    case 'GET_HISTORY':
      return apiFetch(`${apiBase}/history`);

    case 'GET_USAGE':
      return apiFetch(`${apiBase}/usage`);

    default:
      throw new Error(`Unknown message type: ${message.type}`);
  }
}

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiFetch(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `HTTP ${res.status}`);
  }
  return res.json();
}
