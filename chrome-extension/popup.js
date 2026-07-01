'use strict';

// ─── Config ───────────────────────────────────────────────
const DEFAULT_API_BASE = 'http://localhost:3000/api';

// ─── State ────────────────────────────────────────────────
const state = {
  results: null,
  activeTab: 'place_post',
  bonusShowing: null,
};

// ─── Tab definitions ──────────────────────────────────────
const TABS = [
  { id: 'place_post', label: '📍 플레이스' },
  { id: 'blog',       label: '📝 블로그'  },
  { id: 'instagram',  label: '📸 인스타'  },
  { id: 'threads',    label: '🧵 쓰레드'  },
  { id: 'shorts',     label: '🎬 쇼츠'   },
  { id: 'kakao',      label: '💬 카톡'   },
  { id: 'card_news',  label: '🗂️ 카드뉴스' },
];

// ─── Init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);

async function init() {
  await detectCurrentTab();
  await checkLastResults();
  setupListeners();
  await loadSettings();
}

async function detectCurrentTab() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.url && isNaverPlaceUrl(tab.url)) {
      document.getElementById('place-url').value = tab.url;
      setPageStatus('✓ 현재 네이버 플레이스 페이지가 감지되었습니다', 'success');
    }
  } catch (e) { /* popup opened from non-tab context */ }
}

async function checkLastResults() {
  const { lastResults } = await chrome.storage.local.get('lastResults');
  if (lastResults) {
    state.results = lastResults;
    document.getElementById('history-btn').classList.remove('hidden');
  }
}

async function loadSettings() {
  const { apiBase } = await chrome.storage.local.get({ apiBase: DEFAULT_API_BASE });
  document.getElementById('api-base-input').value = apiBase;
}

function setupListeners() {
  // Home
  document.getElementById('generate-btn').addEventListener('click', handleGenerate);
  document.getElementById('paste-btn').addEventListener('click', handlePaste);
  document.getElementById('history-btn').addEventListener('click', showLastResults);
  document.getElementById('settings-btn').addEventListener('click', () => showScreen('settings'));
  document.getElementById('open-settings-link').addEventListener('click', () => showScreen('settings'));

  // Results
  document.getElementById('back-btn').addEventListener('click', () => showScreen('home'));
  document.getElementById('tabs-nav').addEventListener('click', onTabNavClick);
  document.getElementById('tab-content').addEventListener('click', onTabContentClick);
  document.getElementById('bonus-titles-btn').addEventListener('click', () => toggleBonus('titles'));
  document.getElementById('bonus-hashtags-btn').addEventListener('click', () => toggleBonus('hashtags'));

  // Settings
  document.getElementById('settings-back-btn').addEventListener('click', () => showScreen('home'));
  document.getElementById('save-settings-btn').addEventListener('click', saveSettings);
}

// ─── Main flow ────────────────────────────────────────────
async function handleGenerate() {
  const url = document.getElementById('place-url').value.trim();

  if (!url) {
    showError('네이버 플레이스 링크를 입력해주세요.');
    return;
  }

  if (!isNaverPlaceUrl(url) && !url.startsWith('http')) {
    showError('올바른 네이버 플레이스 링크를 입력해주세요.\n예: https://naver.me/xxxx');
    return;
  }

  const tones = Array.from(document.querySelectorAll('input[name="tone"]:checked')).map(cb => cb.value);

  clearError();
  showScreen('loading');

  try {
    // Step 1: extract page text
    setStep(1, 'active');
    const pageText = await extractPageText(url);
    setStep(1, 'done');

    // Step 2: AI analysis + content generation
    setStep(2, 'active');
    const data = await callBackend('generate', { place_url: url, page_text: pageText, tones });
    setStep(2, 'done');

    // Step 3: render
    setStep(3, 'active');
    state.results = data;
    await chrome.storage.local.set({ lastResults: data });
    document.getElementById('history-btn').classList.remove('hidden');
    setStep(3, 'done');

    await delay(400);
    renderResults(data);
    showScreen('results');

  } catch (err) {
    console.error(err);
    showScreen('home');
    showError(err.message || '오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
  }
}

// ─── Page extraction ──────────────────────────────────────
async function extractPageText(url) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.url === url && isNaverPlaceUrl(url)) {
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: extractNaverPlaceDOM,
      });
      return results?.[0]?.result || '';
    }
  } catch (e) {
    console.log('DOM extraction skipped:', e.message);
  }
  return '';
}

// Runs inside the Naver Place page context
function extractNaverPlaceDOM() {
  function first(selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el?.innerText?.trim()) return el.innerText.trim();
    }
    return '';
  }

  function all(selectors, limit = 10) {
    for (const sel of selectors) {
      const els = [...document.querySelectorAll(sel)].slice(0, limit);
      const texts = els.map(e => e.innerText?.trim()).filter(Boolean);
      if (texts.length) return texts.join('\n');
    }
    return '';
  }

  const parts = [];

  const name = first(['h1', '.Fc1rA', '#_title', '.place_section_header h2', '[class*="placeName"]']);
  if (name) parts.push('가게명: ' + name);

  const cat = first(['.lnJFt', '.GXS1X', '[class*="category"]', '.rTjJo']);
  if (cat) parts.push('업종: ' + cat);

  const addr = first(['.LDgIH', '.vV_z_', '[class*="address"]', '.road-address']);
  if (addr) parts.push('주소: ' + addr);

  const phone = first(['.xlx7Q', '[class*="phone"]', '.contact']);
  if (phone) parts.push('전화: ' + phone);

  const hours = first(['.A_cdD', '[class*="hours"]', '.businessHours']);
  if (hours) parts.push('영업시간: ' + hours);

  const menu = all(['.ISxGJ', '[class*="menu"] .name', '.order_list .name'], 20);
  if (menu) parts.push('메뉴/서비스:\n' + menu);

  const reviews = all(['.zPfVt', '.pui__vn15t2', '[class*="review"] p', '.inner_list .text'], 15);
  if (reviews) parts.push('리뷰:\n' + reviews);

  const desc = first(['.T8RFa', '[class*="description"]', '.intro_text', '.place_section p']);
  if (desc) parts.push('소개: ' + desc.substring(0, 500));

  if (parts.length < 2) {
    parts.push('페이지 텍스트:\n' + document.body.innerText.substring(0, 2000));
  }

  return parts.join('\n\n');
}

// ─── Backend API ──────────────────────────────────────────
async function callBackend(endpoint, body) {
  const { apiBase } = await chrome.storage.local.get({ apiBase: DEFAULT_API_BASE });
  const url = `${apiBase.replace(/\/$/, '')}/${endpoint}`;

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `서버 오류 (${res.status})`);
  }

  return res.json();
}

// ─── Render results ───────────────────────────────────────
function renderResults(data) {
  const { analysis } = data;
  document.getElementById('result-business-name').textContent = analysis.business_name || '';
  document.getElementById('result-topic').textContent = analysis.today_topic || '';
  state.bonusShowing = null;
  document.getElementById('bonus-panel').classList.add('hidden');
  document.getElementById('bonus-titles-btn').classList.remove('active');
  document.getElementById('bonus-hashtags-btn').classList.remove('active');
  switchTab('place_post');
}

function switchTab(tabId) {
  state.activeTab = tabId;

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });

  const content = state.results?.contents?.[tabId];
  document.getElementById('tab-content').innerHTML = buildTabHtml(tabId, content);
}

function buildTabHtml(tabId, content) {
  if (!content) return '<p style="padding:12px;color:#64748B;font-size:12px">콘텐츠를 불러올 수 없습니다.</p>';

  let html = '<div class="content-card">';

  switch (tabId) {
    case 'place_post':
      html += `<p class="content-title">${esc(content.title)}</p>`;
      html += `<p class="content-body">${lines(content.body)}</p>`;
      break;

    case 'blog':
      html += `<p class="content-title">${esc(content.title)}</p>`;
      html += `<div class="content-body">${lines(content.body)}</div>`;
      if (content.tags?.length) {
        html += `<div class="tags">${content.tags.map(t => `<span class="tag">#${esc(t)}</span>`).join('')}</div>`;
      }
      break;

    case 'instagram':
      html += `<div class="content-body">${lines(content.caption)}</div>`;
      if (content.hashtags?.length) {
        html += `<div class="hashtags">${content.hashtags.map(h => `<span class="hashtag">${esc(h)}</span>`).join('')}</div>`;
      }
      break;

    case 'threads':
      html += (content.posts || []).map((p, i) => `
        <div class="thread-post">
          <span class="thread-num">${i + 1}</span>
          <p class="content-body" style="flex:1">${lines(p)}</p>
        </div>`).join('');
      break;

    case 'shorts':
      html += `<div class="shorts-hook">🎯 후킹 멘트</div>`;
      html += `<p class="content-body">${esc(content.hook)}</p>`;
      html += `<div class="shorts-section">📋 전체 대본</div>`;
      html += `<div class="content-body">${lines(content.script)}</div>`;
      if (content.scenes?.length) {
        html += `<div class="shorts-section">🎬 장면 구성</div>`;
        html += content.scenes.map((s, i) => `
          <div class="scene-item"><span class="scene-num">S${i + 1}</span>${esc(s)}</div>`).join('');
      }
      break;

    case 'kakao':
      html += `<div class="content-body kakao-style">${lines(content.message)}</div>`;
      break;

    case 'card_news':
      html += (content.slides || []).map((s, i) => `
        <div class="card-slide">
          <span class="slide-num">${i + 1}장</span>
          <p class="content-body">${lines(s)}</p>
        </div>`).join('');
      break;
  }

  html += '</div>';

  html += `
    <div class="action-row">
      <button class="action-btn copy-btn" data-action="copy" data-tab="${tabId}">📋 복사하기</button>
      <button class="action-btn" data-action="shorter" data-tab="${tabId}">짧게</button>
      <button class="action-btn" data-action="hooking" data-tab="${tabId}">후킹업</button>
      <button class="action-btn" data-action="save" data-tab="${tabId}">저장</button>
    </div>`;

  return html;
}

// ─── Tab / action click delegation ───────────────────────
function onTabNavClick(e) {
  const btn = e.target.closest('.tab-btn');
  if (btn) switchTab(btn.dataset.tab);
}

function onTabContentClick(e) {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;

  const { action, tab } = btn.dataset;
  switch (action) {
    case 'copy':    copyTab(tab); break;
    case 'shorter': modifyContent(tab, 'shorter'); break;
    case 'hooking': modifyContent(tab, 'hooking'); break;
    case 'save':    saveTab(tab); break;
  }
}

// ─── Content actions ──────────────────────────────────────
function getTabText(tabId) {
  const c = state.results?.contents?.[tabId];
  if (!c) return '';
  switch (tabId) {
    case 'place_post': return `${c.title}\n\n${c.body}`;
    case 'blog':       return `${c.title}\n\n${c.body}\n\n${(c.tags || []).map(t => '#' + t).join(' ')}`;
    case 'instagram':  return `${c.caption}\n\n${(c.hashtags || []).join(' ')}`;
    case 'threads':    return (c.posts || []).join('\n\n---\n\n');
    case 'shorts':     return `[후킹]\n${c.hook}\n\n[대본]\n${c.script}`;
    case 'kakao':      return c.message;
    case 'card_news':  return (c.slides || []).map((s, i) => `[${i + 1}장]\n${s}`).join('\n\n');
    default: return JSON.stringify(c);
  }
}

async function copyTab(tabId) {
  const text = getTabText(tabId);
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
  }
  showToast('복사되었습니다 ✓');
}

async function modifyContent(tabId, mode) {
  // Phase 2: call backend with modify instruction
  showToast(mode === 'shorter' ? '짧게 만드는 중...' : '후킹 강화 중...');
}

async function saveTab(tabId) {
  await chrome.storage.local.set({
    [`saved_${tabId}`]: { text: getTabText(tabId), ts: Date.now() },
  });
  showToast('저장되었습니다 ✓');
}

// ─── Bonus ───────────────────────────────────────────────
function toggleBonus(type) {
  const panel = document.getElementById('bonus-panel');
  const titlesBtn = document.getElementById('bonus-titles-btn');
  const hashBtn = document.getElementById('bonus-hashtags-btn');

  if (state.bonusShowing === type) {
    panel.classList.add('hidden');
    titlesBtn.classList.remove('active');
    hashBtn.classList.remove('active');
    state.bonusShowing = null;
    return;
  }

  state.bonusShowing = type;
  titlesBtn.classList.toggle('active', type === 'titles');
  hashBtn.classList.toggle('active', type === 'hashtags');

  const bonus = state.results?.bonus || {};

  if (type === 'titles') {
    const titles = bonus.title_candidates || [];
    panel.innerHTML = `
      <div class="bonus-card">
        <h4>제목 후보 ${titles.length}개</h4>
        <ol class="title-list">
          ${titles.map((t, i) => `
            <li>
              <span>${i + 1}. ${esc(t)}</span>
              <button data-copy="${esc(t)}">복사</button>
            </li>`).join('')}
        </ol>
      </div>`;
  } else {
    const tags = bonus.hashtags || [];
    panel.innerHTML = `
      <div class="bonus-card">
        <h4>해시태그 ${tags.length}개</h4>
        <div class="hashtag-cloud">
          ${tags.map(h => `<span class="hashtag" data-copy="${esc(h)}">${esc(h)}</span>`).join('')}
        </div>
        <button class="copy-all-btn" data-copy="${esc(tags.join(' '))}">전체 복사</button>
      </div>`;
  }

  panel.querySelectorAll('[data-copy]').forEach(el => {
    el.addEventListener('click', async () => {
      await navigator.clipboard.writeText(el.dataset.copy).catch(() => {});
      showToast('복사되었습니다 ✓');
    });
  });

  panel.classList.remove('hidden');
}

// ─── Settings ─────────────────────────────────────────────
async function saveSettings() {
  const apiBase = document.getElementById('api-base-input').value.trim();
  await chrome.storage.local.set({ apiBase: apiBase || DEFAULT_API_BASE });
  const msg = document.getElementById('settings-msg');
  msg.classList.remove('hidden');
  setTimeout(() => msg.classList.add('hidden'), 2500);
}

// ─── History ─────────────────────────────────────────────
function showLastResults() {
  if (state.results) {
    renderResults(state.results);
    showScreen('results');
  }
}

// ─── UI helpers ───────────────────────────────────────────
function showScreen(name) {
  document.querySelectorAll('.screen').forEach(s => {
    s.classList.toggle('active', s.id === `screen-${name}`);
  });
}

function setStep(n, status) {
  const el = document.getElementById(`step-${n}`);
  if (!el) return;
  el.className = 'step-item ' + status;
  el.querySelector('.step-badge').textContent =
    status === 'active' ? '진행 중' : status === 'done' ? '완료 ✓' : '대기';
}

function showError(msg) {
  const el = document.getElementById('error-msg');
  el.textContent = msg;
  el.classList.remove('hidden');
}

function clearError() {
  document.getElementById('error-msg').classList.add('hidden');
}

function setPageStatus(msg, type = '') {
  const el = document.getElementById('page-status');
  el.textContent = msg;
  el.className = 'page-status' + (type ? ' ' + type : '');
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.remove('hidden', 'fade-out');
  setTimeout(() => {
    t.classList.add('fade-out');
    setTimeout(() => t.classList.add('hidden'), 300);
  }, 2000);
}

async function handlePaste() {
  try {
    const text = await navigator.clipboard.readText();
    document.getElementById('place-url').value = text;
  } catch { /* clipboard not accessible */ }
}

// ─── Utils ────────────────────────────────────────────────
function isNaverPlaceUrl(url) {
  return /^https:\/\/(map\.naver\.com|naver\.me|place\.naver\.com|m\.place\.naver\.com)/i.test(url);
}

function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function lines(str) {
  return esc(str).replace(/\n/g, '<br>');
}

function delay(ms) {
  return new Promise(r => setTimeout(r, ms));
}
