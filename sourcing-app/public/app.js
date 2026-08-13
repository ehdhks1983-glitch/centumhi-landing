'use strict';

// ─── INIT ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  calcMargin();
  checkApiStatus();
  document.getElementById('keyword').addEventListener('keydown', e => {
    if (e.key === 'Enter') runAnalysis();
  });
});

// ─── API STATUS ───────────────────────────────────────────────────────────────
async function checkApiStatus() {
  try {
    const res  = await fetch('/api/status');
    const data = await res.json();
    const el   = document.getElementById('apiStatus');
    const pills = [];
    if (data.coupang)   pills.push('<span class="status-pill ok"><span class="status-dot dot-g"></span>쿠팡 API ✅</span>');
    else                pills.push('<span class="status-pill demo"><span class="status-dot dot-m"></span>쿠팡 데모</span>');
    if (data.domeggook) pills.push('<span class="status-pill ok"><span class="status-dot dot-g"></span>도매꾹 API ✅</span>');
    else                pills.push('<span class="status-pill demo"><span class="status-dot dot-m"></span>도매꾹 크롤링</span>');
    el.innerHTML = pills.join('');

    if (!data.coupang || !data.domeggook) {
      document.getElementById('demoNote').style.display = 'flex';
    }
  } catch (_) {}
}

// ─── ANALYSIS ─────────────────────────────────────────────────────────────────
async function runAnalysis() {
  const keyword = document.getElementById('keyword').value.trim();
  if (!keyword) { alert('키워드를 입력해주세요.'); return; }

  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  btn.textContent = '분석 중...';

  showLoader();

  try {
    const body = {
      keyword,
      manualPrice:   numVal('manualPrice')   || undefined,
      manualReviews: numVal('manualReviews') || undefined,
      manualSellers: numVal('manualSellers') || undefined,
      manualRocket:  numVal('manualRocket')  || undefined,
    };
    const res  = await fetch('/api/analyze', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    renderResults(data);

    // 마진 계산기에 도매 최저가 자동 세팅
    if (data.wholesale?.length) {
      document.getElementById('mc').value = data.wholesale[0].price;
    }
    document.getElementById('mp').value = data.market.avgPrice;
    calcMargin();

  } catch (e) {
    document.getElementById('resultsArea').innerHTML = `
      <div class="empty"><div class="empty-icon">❌</div><p>분석 오류: ${e.message}</p></div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '🎯 진입점수 분석';
  }
}

function numVal(id) {
  const v = parseFloat(document.getElementById(id)?.value);
  return isNaN(v) ? null : v;
}

// ─── RENDER ───────────────────────────────────────────────────────────────────
function showLoader() {
  const msgs = ['쿠팡 상품 수집 중...','경쟁 분석 중...','도매처 매칭 중...','점수 계산 중...'];
  let i = 0;
  document.getElementById('resultsArea').innerHTML = `
    <div class="loader">
      <div class="spinner"></div>
      <div class="loader-txt" id="loaderTxt">${msgs[0]}</div>
    </div>`;
  const iv = setInterval(() => {
    const el = document.getElementById('loaderTxt');
    if (!el) { clearInterval(iv); return; }
    el.textContent = msgs[i++ % msgs.length];
  }, 650);
}

function renderResults(d) {
  const s  = d.score.total;
  const mr = d.score.marginRate;
  const vClass = s >= 80 ? 'v-good' : s >= 65 ? 'v-test' : s >= 50 ? 'v-caution' : 'v-bad';
  const vText  = s >= 80 ? '✅ 진입 추천' : s >= 65 ? '🔵 테스트 진입' : s >= 50 ? '⚠️ 신중 검토' : '❌ 비추천';
  const sColor = s >= 80 ? 'var(--green)' : s >= 65 ? 'var(--blue)' : s >= 50 ? 'var(--orange2)' : 'var(--red)';
  const barColor = s >= 80 ? 'linear-gradient(90deg,#22d67a,#00b894)'
    : s >= 65 ? 'linear-gradient(90deg,#2f80ff,#1a6dff)'
    : s >= 50 ? 'linear-gradient(90deg,#ffaa00,#ff7a00)'
    : 'linear-gradient(90deg,#ff4444,#cc2222)';
  const bk = d.score.breakdown;
  const m  = d.market;

  const prodHTML = (d.products || []).map(p => `
    <div class="prod-item">
      <div class="rank">${p.rank}</div>
      <div class="prod-info">
        <div class="prod-name">${esc(p.name)}</div>
        <div class="prod-meta">
          <span class="price">₩${(p.price||0).toLocaleString()}</span>
          ${p.reviews ? `<span>⭐ ${p.reviews}리뷰</span>` : ''}
          ${p.rocket  ? '<span class="rocket">🚀 로켓</span>' : ''}
        </div>
      </div>
    </div>`).join('');

  const wsHTML = (d.wholesale || []).map(w => `
    <div class="ws-item">
      <div class="ws-hd">
        <span class="src-tag ${w.source==='도매꾹'?'src-dkg':'src-dmm'}">${w.source==='도매꾹'?'🟡 도매꾹':'🔵 도매매'}</span>
        <span class="match-tag ${w.match>=82?'mt-h':'mt-m'}">유사도 ${w.match}%</span>
      </div>
      <div class="ws-name">${esc(w.name)}</div>
      <div class="ws-stats">
        <div class="ws-stat"><span class="wk">원가</span><span class="wv" style="color:var(--green);">₩${w.price.toLocaleString()}</span></div>
        <div class="ws-stat"><span class="wk">최소</span><span class="wv">${w.minQty}개</span></div>
        <div class="ws-stat"><span class="wk">배송</span><span class="wv">${w.ship===0?'무료':'₩'+w.ship.toLocaleString()}</span></div>
      </div>
    </div>`).join('');

  const st = d.strategy || {};
  const stratHTML = `
    <div class="strat-grid">
      <div class="strat-card">
        <div class="strat-hd">추천 판매가</div>
        <div style="font-size:20px;font-weight:950;color:var(--green);">₩${(st.recPrice||0).toLocaleString()}</div>
        <div style="font-size:11px;color:var(--muted);margin-top:4px;">1+1 구성 시 ₩${Math.round((st.recPrice||0)*1.6/100)*100-1 |0} 추천</div>
      </div>
      <div class="strat-card">
        <div class="strat-hd">추천 상품명</div>
        <div style="font-size:12px;line-height:1.6;">${esc(st.optName||'')}</div>
      </div>
      <div class="strat-card full">
        <div class="strat-hd">진입 전략</div>
        <ul class="strat-list">${(st.tips||[]).map(t=>`<li>${t}</li>`).join('')}</ul>
      </div>
    </div>`;

  const sourceNote = d.source === 'demo'
    ? '<div style="font-size:11px;color:var(--muted);margin-bottom:10px;padding:8px 12px;background:rgba(255,170,0,.06);border:1px solid rgba(255,170,0,.18);border-radius:8px;">⚠️ 데모 데이터 — API 키 연결 시 실제 쿠팡 데이터로 분석</div>'
    : '';

  document.getElementById('resultsArea').innerHTML = `
    ${sourceNote}

    <div class="tabs">
      <button class="tab active" onclick="switchTab(0,this)">📊 분석 결과</button>
      <button class="tab" onclick="switchTab(1,this)">🏭 도매 매칭</button>
      <button class="tab" onclick="switchTab(2,this)">📋 등록 전략</button>
    </div>

    <!-- 탭0: 분석 결과 -->
    <div class="panel active" id="t0">
      <div class="metrics">
        <div class="metric">
          <div class="lbl">평균 판매가</div>
          <div class="val c-w">₩${(m.avgPrice||0).toLocaleString()}</div>
          <div class="sub">최저 ₩${(m.minPrice||0).toLocaleString()}</div>
        </div>
        <div class="metric">
          <div class="lbl">리뷰 평균</div>
          <div class="val c-o">${m.reviewAvg||0}개</div>
          <div class="sub">상위 상품 기준</div>
        </div>
        <div class="metric">
          <div class="lbl">판매자 수</div>
          <div class="val c-g">${m.sellerCount||0}명</div>
          <div class="sub">경쟁 판매자</div>
        </div>
        <div class="metric">
          <div class="lbl">로켓 경쟁</div>
          <div class="val ${(m.rocketRatio||0)<0.3?'c-g':'c-r'}">${(m.rocketRatio||0)<0.3?'낮음':'높음'}</div>
          <div class="sub">${Math.round((m.rocketRatio||0)*100)}%</div>
        </div>
      </div>

      <div class="score-card">
        <div class="score-top">
          <div>
            <div style="font-size:11px;font-weight:700;color:var(--muted);margin-bottom:2px;">진입가능점수</div>
            <div class="score-num" style="color:${sColor};">${s}점</div>
          </div>
          <span class="verdict ${vClass}">${vText}</span>
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
        <div class="ai-hd">🤖 AI 코멘트</div>
        ${buildAiComment(d)}
      </div>

      <div class="sec-lbl">경쟁 상품 TOP ${(d.products||[]).length}</div>
      <div class="prod-list">${prodHTML}</div>
    </div>

    <!-- 탭1: 도매 매칭 -->
    <div class="panel" id="t1">
      <div class="sec-lbl">도매처 매칭 결과 (${(d.wholesale||[]).length}건)</div>
      <div class="ws-list">${wsHTML}</div>
    </div>

    <!-- 탭2: 등록 전략 -->
    <div class="panel" id="t2">${stratHTML}</div>
  `;
}

function switchTab(idx, btn) {
  document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', i === idx));
  document.querySelectorAll('.panel').forEach((p, i) => p.classList.toggle('active', i === idx));
}

function buildAiComment(d) {
  const s  = d.score.total;
  const m  = d.market;
  const mr = d.score.marginRate;
  const parts = [];
  if (mr >= 20) parts.push(`마진율 <strong>${mr}%</strong>로 양호합니다.`);
  else if (mr >= 10) parts.push(`마진율 <strong>${mr}%</strong> — 원가 협상이나 판매가 조정이 필요합니다.`);
  else parts.push(`마진율 <strong>${mr}%</strong>로 낮습니다. 원가 재검토가 필요합니다.`);

  if ((m.reviewAvg||0) > 300) parts.push(`상위 리뷰 <strong>${m.reviewAvg}개</strong>로 썸네일 차별화가 중요합니다.`);
  if ((m.sellerCount||0) <= 7) parts.push(`판매자 ${m.sellerCount}명으로 <strong>진입 여지</strong>가 있습니다.`);
  if ((m.rocketRatio||0) < 0.2) parts.push('로켓 비중이 낮아 <strong>초기 광고 없이 자연 노출</strong>이 가능합니다.');
  if (s >= 65) parts.push('<strong>1+1 세트 구성</strong>으로 객단가를 높이는 전략을 추천합니다.');
  return parts.join(' ');
}

// ─── MARGIN CALC ──────────────────────────────────────────────────────────────
function calcMargin() {
  const price = +document.getElementById('mp').value || 0;
  const cost  = +document.getElementById('mc').value || 0;
  const feeR  = +document.getElementById('mf').value || 0;
  const ship  = +document.getElementById('ms').value || 0;
  const pack  = +document.getElementById('mk').value || 0;
  const ad    = +document.getElementById('ma').value || 0;
  const retR  = +document.getElementById('mr').value || 0;

  const fee  = Math.round(price * feeR / 100);
  const ret  = Math.round(price * retR / 100);
  const net  = price - cost - fee - ship - pack - ad - ret;
  const rate = price > 0 ? (net / price * 100).toFixed(1) : 0;
  const rN   = parseFloat(rate);
  const mc   = rN >= 25 ? 'var(--green)' : rN >= 15 ? 'var(--orange2)' : 'var(--red)';
  const be   = Math.max(0, price - cost - fee - ship - pack - ret);

  document.getElementById('marginOut').innerHTML = `
    <table class="margin-table" style="background:rgba(6,14,28,.6);border:1px solid var(--line);border-radius:10px;overflow:hidden;">
      <tr><td>쿠팡 수수료 (${feeR}%)</td><td style="color:var(--red);">−₩${fee.toLocaleString()}</td></tr>
      <tr><td>배송+포장</td><td style="color:var(--red);">−₩${(ship+pack).toLocaleString()}</td></tr>
      <tr><td>광고비</td><td style="color:var(--red);">−₩${ad.toLocaleString()}</td></tr>
      <tr><td>반품/CS</td><td style="color:var(--red);">−₩${ret.toLocaleString()}</td></tr>
      <tr class="total">
        <td>예상 순마진</td>
        <td style="color:${mc};">₩${net.toLocaleString()} <span style="font-size:11px;opacity:.7;">(${rate}%)</span></td>
      </tr>
    </table>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px;">
      <div class="metric"><div class="lbl">마진율</div><div class="val" style="color:${mc};">${rate}%</div><div class="sub">${rN>=25?'✅ 좋음':rN>=15?'⚠️ 보통':'❌ 낮음'}</div></div>
      <div class="metric"><div class="lbl">최대 광고비</div><div class="val c-b">₩${be.toLocaleString()}</div><div class="sub">이 이상이면 적자</div></div>
    </div>`;
}

function esc(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
