// Background service worker
// Handles cross-tab messaging and usage quota (free tier: 3/day)

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ usageDate: '', usageCount: 0 });
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action === 'checkQuota') {
    chrome.storage.local.get(['usageDate', 'usageCount', 'isPro'], (data) => {
      if (data.isPro) { sendResponse({ allowed: true, remaining: 999 }); return; }
      const today = new Date().toISOString().slice(0, 10);
      const count = data.usageDate === today ? (data.usageCount || 0) : 0;
      sendResponse({ allowed: count < 3, remaining: 3 - count, total: 3 });
    });
    return true;
  }
  if (msg.action === 'consumeQuota') {
    chrome.storage.local.get(['usageDate', 'usageCount', 'isPro'], (data) => {
      if (data.isPro) { sendResponse({ ok: true }); return; }
      const today = new Date().toISOString().slice(0, 10);
      const count = data.usageDate === today ? (data.usageCount || 0) : 0;
      chrome.storage.local.set({ usageDate: today, usageCount: count + 1 });
      sendResponse({ ok: true });
    });
    return true;
  }
});
