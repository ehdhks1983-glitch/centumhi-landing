'use strict';

// ─── STATE ────────────────────────────────────────────────────────────────────
let state = { analysis: null, keyword: '' };

// ─── INIT ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  updateQuota();
  calcMargin();
  detectCurrentPage();
});

// ─── TABS ─────────────────────────────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = btn.dataset.tab;
      document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', String(i) === idx));
      document.querySelectorAll('.panel').forEach((p, i) => p.classList.toggle('active', String(i) === idx));
      if (idx === '2') calcMargin();
    });
  });
}

// ─── QUOTA ────────────────────────────────────────────────────────────────────
function updateQuota() {
  chrome.runtime.sendMessage({ action: 'checkQuota' }, (res) => {
    if (!res) return;
    const el = document.getElementById('quotaBadge');
    if (res.remaining === 999) { el.textContent = '프로 ∞'; el.className = 'quota-badge'; return; }
    el.textContent = `무료 ${res.remaining}/${res.total}`;
    el.className = 'quota-badge' + (res.remaining === 0 ? ' full' : res.remaining === 1 ? ' warn' : '');
    if (res.remaining === 0) {
      const btn = document.getElementById('runBtn');
      btn.disabled = true;
      btn.textContent = '오늘 무료 횟수 소진 (내일 초기화)';
    }
  });
}

// ─── DETECT CURRENT PAGE ──────────────────────────────────────────────────────
function detectCurrentPage() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs[0];
    const statusEl = document.getElementById('pageStatus');
    if (!tab || !tab.url) { renderOtherStatus(statusEl); return; }

    if (tab.url.includes('coupang.com')) {
      statusEl.innerHTML = `
        <div class="status-bar coupang">
          <div class="status-dot dot-blue"></div>
          쿠팡 페이지 감지 — 상품 데이터 자동 추출 가능
        </div>`;
      // Try to extract from page
      chrome.tabs.sendMessage(tab.id, { action: 'extract' }, (res) => {
        if (chrome.runtime.lastError || !res) return;
        if (res.type === 'product' && res.data.name) {
          document.getElementById('keywordInput').value = res.data.name;
          state.keyword = res.data.name;
        } else if (res.type === 'search' && res.keyword) {
          document.getElementById('keywordInput').value = res.keyword;
          state.keyword = res.keyword;
        }
      });
    } else {
      renderOtherStatus(statusEl);
    }
  });
}

function renderOtherStatus(el) {
  el.innerHTML = `
    <div class="status-bar other">
      <div class="status-dot dot-gray"></div>
      쿠팡 페이지에서 열면 자동 추출됩니다
    </div>`;
}

// ─── ANALYSIS ─────────────────────────────────────────────────────────────────
function runAnalysis() {
  chrome.runtime.sendMessage({ action: 'checkQuota' }, (res) => {
    if (!res) return;
    if (!res.allowed) {
      alert('오늘 무료 분석 횟수(3회)를 모두 사용했습니다.\n내일 초기화되거나 프로 요금제를 이용하세요.');
      return;
    }
    doAnalysis();
  });
}

function doAnalysis() {
  const kw = document.getElementById('keywordInput').value.trim();
  if (!kw) { alert('키워드 또는 상품명을 입력해주세요.'); return; }
  state.keyword = kw;

  const out = document.getElementById('coupangOutput');
  out.innerHTML = `
    <div class="loader-wrap">
      <div class="spinner"></div>
      <div class="loader-txt" id="loaderTxt">쿠팡 분석 중...</div>
    </div>`;

  // Simulate progressive loading messages
  const msgs = ['쿠팡 상품 수집 중...', '경쟁 분석 중...', '도매처 매칭 중...', '진입점수 계산 중...'];
  let i = 0;
  const iv = setInterval(() => {
    const el = document.getElementById('loaderTxt');
    if (el) el.textContent = msgs[i++ % msgs.length];
  }, 600);

  // In a real implementation, this would call a backend API or scrape via content script.
  // For MVP, we generate analysis based on the keyword with realistic mock data.
  setTimeout(() => {
    clearInterval(iv);
    chrome.runtime.sendMessage({ action: 'consumeQuota' }, () => {
      const data = generateAnalysis(kw);
      state.analysis = data;
      renderAnalysis(data, out);
      updateQuota();
      // Pre-populate other tabs
      document.getElementById('wsKeyword').value = kw;
      renderWholesale(data.wholesale);
      renderStrategy(data);
      document.getElementById('mp').value = data.avgPrice;
      document.getElementById('mc').value = data.wholesale[0]?.price || 5000;
      calcMargin();
    });
  }, 2600);
}

// ─── GENERATE MOCK ANALYSIS (MVP placeholder for real scraping) ───────────────
function generateAnalysis(kw) {
  // Deterministic seed from keyword so same input → same result
  const seed = kw.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  const rng = (min, max) => min + (seed * 1103515245 % (max - min + 1) + (max - min + 1)) % (max - min + 1);

  const avgPrice = rng(8900, 39900);
  const roundPrice = Math.round(avgPrice / 1000) * 1000 - 100;
  const avgReviews = rng(50, 800);
  const sellerCount = rng(3, 18);
  const rocketRatio = (rng(0, 40) / 100);
  const costGuess = Math.round(roundPrice * (rng(25, 45) / 100) / 100) * 100;

  const products = Array.from({ length: 5 }, (_, i) => {
    const s2 = seed + i * 997;
    return {
      rank: i + 1,
      name: kw + ['', ' 프리미엄', ' 세트', ' 2개입', ' 미니'][i],
      price: roundPrice + rng(-3000, 5000) - i * 1000,
      reviews: Math.max(5, avgReviews - i * rng(20, 80)),
      rocket: i === 1 && rocketRatio > 0.15,
    };
  });

  // Score calculation
  const marginRate = ((roundPrice - costGuess - Math.round(roundPrice * 0.12) - 3000 - 500 - 1500 - Math.round(roundPrice * 0.02)) / roundPrice) * 100;
  const sMargin = Math.min(25, Math.max(0, Math.round(marginRate)));
  const sReviews = avgReviews < 100 ? 20 : avgReviews < 300 ? 16 : avgReviews < 700 ? 11 : avgReviews < 1500 ? 6 : 2;
  const sSellers = sellerCount <= 5 ? 15 : sellerCount <= 10 ? 11 : sellerCount <= 20 ? 7 : 3;
  const sRocket = rocketRatio < 0.1 ? 15 : rocketRatio < 0.3 ? 10 : rocketRatio < 0.5 ? 5 : 2;
  const sPrice = marginRate > 20 ? 10 : marginRate > 10 ? 7 : 4;
  const sMatch = rng(6, 10);
  const sDiff = rng(2, 5);
  const total = sMargin + sReviews + sSellers + sRocket + sPrice + sMatch + sDiff;

  const wholesale = [
    { src: 'dkg', name: kw + ' 도매 단가 (최저가)', price: costGuess, minQty: 10, ship: 3000, match: rng(82, 96) },
    { src: 'dkg', name: kw + ' OEM 가능 대량주문', price: Math.round(costGuess * 1.2), minQty: 30, ship: 0, match: rng(68, 82) },
    { src: 'dmm', name: kw + ' 도매매 단가', price: Math.round(costGuess * 0.9), minQty: 50, ship: 2500, match: rng(60, 76) },
  ];

  return { keyword: kw, avgPrice: roundPrice, minPrice: roundPrice - 3000, maxPrice: roundPrice + 8000, avgReviews, sellerCount, rocketRatio, products, score: Math.min(96, total), breakdown: { margin: sMargin, reviews: sReviews, sellers: sSellers, rocket: sRocket, price: sPrice, match: sMatch, diff: sDiff }, wholesale, costGuess };
}

// ─── RENDER ANALYSIS ──────────────────────────────────────────────────────────
function renderAnalysis(d, el) {
  const s = d.score;
  const barColor = s >= 80 ? 'linear-gradient(90deg,#22d67a,#00b894)' : s >= 65 ? 'linear-gradient(90deg,#2f80ff,#1a6dff)' : s >= 50 ? 'linear-gradient(90deg,#ffaa00,#ff7a00)' : 'linear-gradient(90deg,#ff4444,#cc2222)';
  const vClass = s >= 80 ? 'v-good' : s >= 65 ? 'v-test' : s >= 50 ? 'v-caution' : 'v-bad';
  const vText = s >= 80 ? '✅ 진입 추천' : s >= 65 ? '🔵 테스트 진입' : s >= 50 ? '⚠️ 신중 검토' : '❌ 비추천';
  const scoreColor = s >= 80 ? 'var(--green)' : s >= 65 ? 'var(--blue)' : s >= 50 ? 'var(--orange2)' : 'var(--red)';
  const bk = d.breakdown;

  const aiComment = generateAIComment(d);

  const prodHTML = d.products.map(p => `
    <div class="prod-item">
      <div class="rank-badge">${p.rank}</div>
      <div class="prod-info">
        <div class="prod-name">${p.name}</div>
        <div class="prod-meta">
          <span class="price">₩${p.price.toLocaleString()}</span>
          <span>⭐ ${p.reviews}리뷰</span>
          ${p.rocket ? '<span class="rocket">🚀 로켓</span>' : ''}
        </div>
      </div>
    </div>`).join('');

  el.innerHTML = `
    <div class="metrics">
      <div class="metric">
        <div class="lbl">평균 판매가</div>
        <div class="val c-white">₩${d.avgPrice.toLocaleString()}</div>
        <div class="sub">최저 ₩${d.minPrice.toLocaleString()}</div>
      </div>
      <div class="metric">
        <div class="lbl">리뷰 평균</div>
        <div class="val c-orange">${d.avgReviews}개</div>
        <div class="sub">상위 5개 기준</div>
      </div>
      <div class="metric">
        <div class="lbl">판매자 수</div>
        <div class="val c-green">${d.sellerCount}명</div>
        <div class="sub">경쟁 판매자</div>
      </div>
      <div class="metric">
        <div class="lbl">로켓 경쟁</div>
        <div class="val ${d.rocketRatio < 0.3 ? 'c-green' : 'c-red'}">${d.rocketRatio < 0.3 ? '낮음' : '높음'}</div>
        <div class="sub">비중 ${Math.round(d.rocketRatio * 100)}%</div>
      </div>
    </div>

    <div class="score-block">
      <div class="score-top">
        <div>
          <div style="font-size:9px;font-weight:700;color:var(--muted);margin-bottom:2px;">진입가능점수</div>
          <div class="score-num" style="color:${scoreColor};">${s}점</div>
        </div>
        <span class="verdict-pill ${vClass}">${vText}</span>
      </div>
      <div class="bar-track"><div class="bar-fill" style="width:${s}%;background:${barColor};"></div></div>
      <div class="breakdown">
        <div class="bd-row"><span class="bd-lbl">예상 마진율</span><span class="bd-val">${bk.margin}/25</span></div>
        <div class="bd-row"><span class="bd-lbl">리뷰 경쟁</span><span class="bd-val">${bk.reviews}/20</span></div>
        <div class="bd-row"><span class="bd-lbl">판매자 수</span><span class="bd-val">${bk.sellers}/15</span></div>
        <div class="bd-row"><span class="bd-lbl">로켓 여부</span><span class="bd-val">${bk.rocket}/15</span></div>
        <div class="bd-row"><span class="bd-lbl">가격 여유</span><span class="bd-val">${bk.price}/10</span></div>
        <div class="bd-row"><span class="bd-lbl">도매 매칭</span><span class="bd-val">${bk.match}/10</span></div>
      </div>
    </div>

    <div class="ai-box">
      <div class="ai-box-hd">🤖 AI 코멘트</div>
      ${aiComment}
    </div>

    <div class="sec-lbl">경쟁 상품 TOP 5</div>
    <div class="prod-list">${prodHTML}</div>
  `;
}

function generateAIComment(d) {
  const s = d.score;
  const comments = [];
  if (d.avgReviews > 500) comments.push(`상위 상품 리뷰가 ${d.avgReviews}개 이상으로 <strong>썸네일 차별화</strong>가 필수입니다.`);
  if (d.sellerCount <= 6) comments.push(`판매자가 ${d.sellerCount}명으로 <strong>진입 여지가 충분</strong>합니다.`);
  if (d.rocketRatio < 0.2) comments.push('로켓 비중이 낮아 <strong>일반 셀러 노출</strong>이 유리합니다.');
  if (s >= 65) comments.push('<strong>1+1 세트 구성</strong>으로 마진율을 높이는 전략을 추천합니다.');
  else comments.push('경쟁이 치열하므로 <strong>가격보다 차별화</strong> 전략이 먼저입니다.');
  return comments.join(' ');
}

// ─── WHOLESALE ────────────────────────────────────────────────────────────────
function runWholesale() {
  const kw = document.getElementById('wsKeyword').value.trim();
  if (!kw) return;
  if (!state.analysis || state.analysis.keyword !== kw) {
    state.analysis = generateAnalysis(kw);
  }
  renderWholesale(state.analysis.wholesale);
}

function renderWholesale(items) {
  if (!items || !items.length) return;
  const html = items.map(w => `
    <div class="ws-item">
      <div class="ws-hd">
        <span class="src-tag ${w.src === 'dkg' ? 'src-dkg' : 'src-dmm'}">${w.src === 'dkg' ? '🟡 도매꾹' : '🔵 도매매'}</span>
        <span class="match-tag ${w.match >= 82 ? 'mt-high' : 'mt-mid'}">유사도 ${w.match}%</span>
      </div>
      <div class="ws-name">${w.name}</div>
      <div class="ws-stats">
        <div class="ws-stat"><span class="wk">원가</span><span class="wv" style="color:var(--green);">₩${w.price.toLocaleString()}</span></div>
        <div class="ws-stat"><span class="wk">최소</span><span class="wv">${w.minQty}개</span></div>
        <div class="ws-stat"><span class="wk">배송</span><span class="wv">${w.ship === 0 ? '무료' : '₩' + w.ship.toLocaleString()}</span></div>
      </div>
    </div>`).join('');
  document.getElementById('wsOutput').innerHTML = `
    <div class="sec-lbl">도매처 매칭 결과 (${items.length}건)</div>
    <div class="ws-list">${html}</div>`;
}

// ─── MARGIN CALC ──────────────────────────────────────────────────────────────
function calcMargin() {
  const price = parseFloat(document.getElementById('mp').value) || 0;
  const cost  = parseFloat(document.getElementById('mc').value) || 0;
  const feeR  = parseFloat(document.getElementById('mf').value) || 0;
  const ship  = parseFloat(document.getElementById('ms').value) || 0;
  const pack  = parseFloat(document.getElementById('mk').value) || 0;
  const ad    = parseFloat(document.getElementById('ma').value) || 0;
  const retR  = parseFloat(document.getElementById('mr').value) || 0;

  const fee    = Math.round(price * feeR / 100);
  const ret    = Math.round(price * retR / 100);
  const total  = cost + fee + ship + pack + ad + ret;
  const net    = price - total;
  const rate   = price > 0 ? (net / price * 100).toFixed(1) : 0;
  const rateN  = parseFloat(rate);
  const mc     = rateN >= 25 ? 'var(--green)' : rateN >= 15 ? 'var(--orange2)' : 'var(--red)';
  const beCost = Math.max(0, price - cost - fee - ship - pack - ret);

  document.getElementById('marginOut').innerHTML = `
    <div class="margin-summary">
      <div class="ms-row"><span class="mk">쿠팡 수수료 (${feeR}%)</span><span class="mv" style="color:var(--red);">−₩${fee.toLocaleString()}</span></div>
      <div class="ms-row"><span class="mk">배송+포장비</span><span class="mv" style="color:var(--red);">−₩${(ship+pack).toLocaleString()}</span></div>
      <div class="ms-row"><span class="mk">광고비</span><span class="mv" style="color:var(--red);">−₩${ad.toLocaleString()}</span></div>
      <div class="ms-row"><span class="mk">반품/CS (${retR}%)</span><span class="mv" style="color:var(--red);">−₩${ret.toLocaleString()}</span></div>
      <div class="ms-row total"><span class="mk">예상 순마진</span><span class="mv" style="color:${mc};">₩${net.toLocaleString()} <span style="font-size:11px;opacity:.75;">(${rate}%)</span></span></div>
    </div>
    <div class="metrics" style="margin-top:10px;margin-bottom:0;">
      <div class="metric">
        <div class="lbl">마진율</div>
        <div class="val" style="color:${mc};">${rate}%</div>
        <div class="sub">${rateN>=25?'✅ 좋음':rateN>=15?'⚠️ 보통':'❌ 낮음'}</div>
      </div>
      <div class="metric">
        <div class="lbl">최대 광고비</div>
        <div class="val c-blue">₩${beCost.toLocaleString()}</div>
        <div class="sub">이 이상이면 적자</div>
      </div>
    </div>`;
}

// ─── STRATEGY ─────────────────────────────────────────────────────────────────
function renderStrategy(d) {
  const recPrice = d.avgPrice - 100;
  const optName = `휴대용 ${d.keyword} 목 어깨 종아리 근막이완 셀프마사지`;
  const s = d.score;

  document.getElementById('stratOut').innerHTML = `
    <div class="strat-card">
      <div class="strat-hd">추천 판매가</div>
      <div class="strat-content" style="font-size:18px;font-weight:950;color:var(--green);">₩${recPrice.toLocaleString()}</div>
      <div class="strat-content" style="font-size:10px;color:var(--muted);margin-top:4px;">1+1 세트 구성 시 ₩${(recPrice * 1.6).toLocaleString()} 추천</div>
    </div>
    <div class="strat-card">
      <div class="strat-hd">추천 상품명</div>
      <div class="strat-content">${optName}</div>
      <div class="tag-row"><span class="stag">SEO 최적화</span><span class="stag">검색키워드 포함</span></div>
    </div>
    <div class="strat-card">
      <div class="strat-hd">썸네일 전략</div>
      <ul class="strat-list">
        <li>상위 상품 색상 반전 — 차별화 컬러 사용</li>
        <li>실제 사용 부위 사진 (목/어깨/발바닥)</li>
        <li>핵심 문구 좌상단 배치 (2~3단어)</li>
        <li>수량·세트 강조 시 뱃지 추가</li>
      </ul>
    </div>
    <div class="strat-card">
      <div class="strat-hd">진입 전략</div>
      <ul class="strat-list">
        <li>초기 ${s >= 70 ? '20~30' : '10~15'}개 소량 테스트 후 리뷰 확보</li>
        <li>${d.rocketRatio < 0.3 ? '로켓 비중 낮아 초기 광고비 절약 가능' : '로켓 경쟁 높음 — 가격 차별화 필수'}</li>
        <li>1+1 세트 구성으로 평균주문금액 상향</li>
        <li>${d.avgReviews > 400 ? '리뷰 경쟁 강함 — 썸네일 차별화 먼저' : '리뷰 경쟁 낮음 — 빠른 리뷰 확보 유리'}</li>
      </ul>
    </div>`;
}
