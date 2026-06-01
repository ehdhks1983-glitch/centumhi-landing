'use strict';

require('dotenv').config();
const express = require('express');
const crypto  = require('crypto');
const axios   = require('axios');
const cheerio = require('cheerio');

const app  = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static('public'));

// ─── 쿠팡 파트너스 API ────────────────────────────────────────────────────────
// 공식 문서: https://partners.coupang.com → Open API 가이드

const COUPANG_HOST = 'https://api-gateway.coupang.com';

function coupangHmac(method, path, params) {
  const datetime = new Date().toISOString()
    .replace(/\.\d{3}Z/, 'Z')
    .replace(/[-:]/g, '')
    .replace('T', 'T');

  const sortedParams = Object.keys(params).sort()
    .map(k => `${k}=${params[k]}`).join('&');
  const signString = datetime + method.toUpperCase() + path
    + (sortedParams ? `?${sortedParams}` : '');

  const signature = crypto
    .createHmac('sha256', process.env.COUPANG_SECRET_KEY || '')
    .update(signString)
    .digest('hex');

  return {
    Authorization: `CEA algorithm=HmacSHA256, access-id=${process.env.COUPANG_ACCESS_KEY}, signed-date=${datetime}, signature=${signature}`,
    'Content-Type': 'application/json;charset=UTF-8',
  };
}

async function coupangSearch(keyword, limit = 20) {
  if (!process.env.COUPANG_ACCESS_KEY) return null;

  const path   = '/v2/providers/affiliate_open_api/apis/openapi/v1/products/search';
  const params = { keyword, limit };
  const qs     = `keyword=${encodeURIComponent(keyword)}&limit=${limit}`;

  try {
    const { data } = await axios.get(`${COUPANG_HOST}${path}?${qs}`, {
      headers: coupangHmac('GET', path, params),
      timeout: 8000,
    });
    return data?.data?.productData || [];
  } catch (e) {
    console.error('쿠팡 API 오류:', e.response?.data || e.message);
    return null;
  }
}

async function coupangBestsellers(categoryId = '1001') {
  if (!process.env.COUPANG_ACCESS_KEY) return null;

  const path   = '/v2/providers/affiliate_open_api/apis/openapi/v1/products/bestcategories';
  const params = { categoryId, limit: 20 };
  const qs     = `categoryId=${categoryId}&limit=20`;

  try {
    const { data } = await axios.get(`${COUPANG_HOST}${path}?${qs}`, {
      headers: coupangHmac('GET', path, params),
      timeout: 8000,
    });
    return data?.data?.productData || [];
  } catch (e) {
    console.error('쿠팡 베스트셀러 오류:', e.response?.data || e.message);
    return null;
  }
}

// ─── 도매꾹 API ───────────────────────────────────────────────────────────────
// 공식 API: https://www.domeggook.com/main/api/openApi.php
// API 키 신청 후 아래 함수 완성

async function domeggookSearch(keyword) {
  const apiKey = process.env.DOMEGGOOK_API_KEY;

  // ── 도매꾹 공식 API 사용 (키 있을 때) ──
  if (apiKey) {
    try {
      const { data } = await axios.get('https://www.domeggook.com/main/api/openApi.php', {
        params: {
          aid:     apiKey,
          ver:     '1.0',
          cmd:     'getGoodsList',
          keyword: keyword,
          pageNum: 1,
          pageSize: 10,
        },
        timeout: 8000,
      });
      // 응답 파싱 (도매꾹 API 응답 구조에 맞게 조정 필요)
      const items = data?.data?.list || data?.list || [];
      return items.map(item => ({
        source:  '도매꾹',
        name:    item.goodsNm || item.name || '',
        price:   parseInt(item.consumerPrice || item.price || 0),
        minQty:  parseInt(item.minOrderQty || item.minQty || 1),
        ship:    parseInt(item.deliveryFee || 3000),
        url:     item.goodsUrl || '',
        match:   calcNameSimilarity(keyword, item.goodsNm || item.name || ''),
      })).filter(i => i.name && i.price > 0);
    } catch (e) {
      console.error('도매꾹 API 오류:', e.message);
      // API 실패 시 크롤링으로 fallback
    }
  }

  // ── Fallback: 도매꾹 웹 크롤링 ──
  try {
    const { data: html } = await axios.get(
      `https://www.domeggook.com/search/index.php?q=${encodeURIComponent(keyword)}`, {
        headers: { 'User-Agent': 'Mozilla/5.0 (compatible; research-bot/1.0)' },
        timeout: 10000,
      }
    );
    const $ = cheerio.load(html);
    const items = [];

    // 도매꾹 검색결과 셀렉터 (사이트 구조 변경 시 업데이트 필요)
    $('ul.prd-list li, .goods-list .item, .search-result .product-item').each((i, el) => {
      if (i >= 8) return;
      const name  = $(el).find('.goods-name, .name, h3, h4').first().text().trim();
      const priceText = $(el).find('.price, .consumer-price, strong').first().text();
      const price = parseInt(priceText.replace(/[^0-9]/g, '')) || 0;
      const minQtyText = $(el).find('.min-qty, .min-order').text();
      const minQty = parseInt(minQtyText.replace(/[^0-9]/g, '')) || 1;

      if (name && price > 0) {
        items.push({
          source: '도매꾹',
          name,
          price,
          minQty,
          ship: 3000,
          url: '',
          match: calcNameSimilarity(keyword, name),
        });
      }
    });

    return items.sort((a, b) => b.match - a.match);
  } catch (e) {
    console.error('도매꾹 크롤링 오류:', e.message);
    return [];
  }
}

// ─── 유사도 계산 ──────────────────────────────────────────────────────────────
function calcNameSimilarity(query, target) {
  const q = query.replace(/\s+/g, '').toLowerCase();
  const t = target.replace(/\s+/g, '').toLowerCase();
  const qTokens = q.match(/.{1,2}/g) || [];
  const tTokens = new Set(t.match(/.{1,2}/g) || []);
  const hits = qTokens.filter(tok => tTokens.has(tok)).length;
  return Math.min(99, Math.round((hits / Math.max(qTokens.length, 1)) * 100) + 30);
}

// ─── 진입점수 계산 ────────────────────────────────────────────────────────────
function calcEntryScore({ avgPrice, costPrice, reviewAvg, sellerCount, rocketRatio }) {
  const fee       = Math.round(avgPrice * 0.108);
  const netMargin = avgPrice - costPrice - fee - 3000 - 500 - 1500 - Math.round(avgPrice * 0.02);
  const marginRate = netMargin / avgPrice * 100;

  const sMargin  = marginRate >= 25 ? 25 : marginRate >= 20 ? 20 : marginRate >= 15 ? 15 : marginRate >= 10 ? 8 : 3;
  const sReviews = reviewAvg  <= 50  ? 20 : reviewAvg  <= 150 ? 17 : reviewAvg  <= 400 ? 12 : reviewAvg  <= 1000 ? 7 : 3;
  const sSellers = sellerCount <= 3  ? 15 : sellerCount <= 7  ? 12 : sellerCount <= 15 ? 8  : sellerCount <= 25  ? 4 : 1;
  const sRocket  = rocketRatio <= 0.1 ? 15 : rocketRatio <= 0.25 ? 11 : rocketRatio <= 0.5 ? 6 : 2;
  const sPrice   = marginRate >= 20 ? 10 : marginRate >= 15 ? 7 : marginRate >= 10 ? 4 : 1;
  const sMatch   = costPrice > 0 ? 10 : 5;
  const sDiff    = sellerCount <= 7 ? 5 : 3;

  const total = sMargin + sReviews + sSellers + sRocket + sPrice + sMatch + sDiff;
  return {
    total: Math.min(97, total),
    breakdown: { margin: sMargin, reviews: sReviews, sellers: sSellers, rocket: sRocket, price: sPrice, match: sMatch, diff: sDiff },
    marginRate: parseFloat(marginRate.toFixed(1)),
    netMargin,
  };
}

// ─── API 라우트 ───────────────────────────────────────────────────────────────

// 쿠팡 상품 검색
app.get('/api/coupang/search', async (req, res) => {
  const { keyword } = req.query;
  if (!keyword) return res.status(400).json({ error: '키워드를 입력하세요.' });

  const products = await coupangSearch(keyword);
  if (!products) {
    return res.json({ source: 'demo', products: getDemoProducts(keyword) });
  }

  const mapped = products.map((p, i) => ({
    rank:    i + 1,
    name:    p.productName,
    price:   p.productPrice,
    image:   p.productImage,
    url:     p.productUrl,
    rocket:  p.isRocket || false,
    reviews: p.productReviewCount || 0,
    rating:  p.productReviewAverage || 0,
  }));

  res.json({ source: 'coupang', products: mapped });
});

// 쿠팡 카테고리 베스트셀러
app.get('/api/coupang/bestsellers', async (req, res) => {
  const { categoryId = '1001' } = req.query;
  const products = await coupangBestsellers(categoryId);
  if (!products) return res.json({ source: 'demo', products: [] });
  res.json({ source: 'coupang', products });
});

// 도매꾹 검색
app.get('/api/wholesale', async (req, res) => {
  const { keyword } = req.query;
  if (!keyword) return res.status(400).json({ error: '키워드를 입력하세요.' });

  const items = await domeggookSearch(keyword);
  res.json({ items: items.length > 0 ? items : getDemoWholesale(keyword) });
});

// 통합 분석 (메인 기능)
app.post('/api/analyze', async (req, res) => {
  const { keyword, manualPrice, manualReviews, manualSellers, manualRocket } = req.body;
  if (!keyword) return res.status(400).json({ error: '키워드를 입력하세요.' });

  // 병렬로 쿠팡 + 도매꾹 조회
  const [coupangResult, wholesaleResult] = await Promise.all([
    coupangSearch(keyword),
    domeggookSearch(keyword),
  ]);

  // 쿠팡 데이터 집계
  const products = coupangResult || getDemoProducts(keyword);
  const prices   = products.map(p => p.productPrice || p.price).filter(Boolean);
  const avgPrice = manualPrice
    || (prices.length ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : 0);
  const reviews  = products.map(p => p.productReviewCount || p.reviews || 0);
  const reviewAvg = manualReviews
    || (reviews.length ? Math.round(reviews.reduce((a, b) => a + b, 0) / reviews.length) : 0);
  const sellerCount  = manualSellers || products.length;
  const rocketCount  = products.filter(p => p.isRocket || p.rocket).length;
  const rocketRatio  = manualRocket != null ? manualRocket / 100 : rocketCount / Math.max(products.length, 1);

  // 도매 최저가
  const wholesale    = wholesaleResult.length > 0 ? wholesaleResult : getDemoWholesale(keyword);
  const bestCost     = wholesale.sort((a, b) => a.price - b.price)[0]?.price || Math.round(avgPrice * 0.35);

  // 진입점수
  const score = calcEntryScore({ avgPrice, costPrice: bestCost, reviewAvg, sellerCount, rocketRatio });

  // 전략 생성
  const strategy = buildStrategy({ keyword, avgPrice, bestCost, reviewAvg, sellerCount, rocketRatio, score });

  res.json({
    keyword,
    source: coupangResult ? 'coupang' : 'demo',
    market: { avgPrice, minPrice: Math.min(...prices, avgPrice), maxPrice: Math.max(...prices, avgPrice), reviewAvg, sellerCount, rocketRatio: parseFloat(rocketRatio.toFixed(2)) },
    products: products.slice(0, 5).map((p, i) => ({
      rank: i + 1,
      name:    p.productName || p.name,
      price:   p.productPrice || p.price,
      reviews: p.productReviewCount || p.reviews || 0,
      rocket:  p.isRocket || p.rocket || false,
    })),
    wholesale: wholesale.slice(0, 4),
    score,
    strategy,
  });
});

// API 키 상태 확인
app.get('/api/status', (_req, res) => {
  res.json({
    coupang:    !!process.env.COUPANG_ACCESS_KEY,
    domeggook:  !!process.env.DOMEGGOOK_API_KEY,
  });
});

// ─── 전략 생성 ────────────────────────────────────────────────────────────────
function buildStrategy({ keyword, avgPrice, bestCost, reviewAvg, sellerCount, rocketRatio, score }) {
  const recPrice = Math.round((avgPrice - 100) / 100) * 100 - 1;
  const optName  = `휴대용 ${keyword} 고품질 ${reviewAvg > 300 ? '프리미엄' : '실속형'}`;

  const tips = [];
  if (reviewAvg > 300) tips.push(`상위 리뷰 ${reviewAvg}개 — 썸네일 차별화 필수`);
  if (sellerCount <= 7) tips.push(`판매자 ${sellerCount}명 — 진입 여지 충분`);
  if (rocketRatio < 0.2) tips.push('로켓 비중 낮음 — 초기 광고비 절약 가능');
  if (score.marginRate > 20) tips.push('마진 양호 — 1+1 세트로 객단가 올리기 추천');
  else tips.push('마진 주의 — 원가 협상 or 판매가 올리기 필요');
  tips.push(`초기 ${score.total >= 70 ? '20~30' : '10~15'}개 소량 테스트 후 리뷰 확보`);

  return { recPrice, optName, tips };
}

// ─── 데모 데이터 (API 키 없을 때) ────────────────────────────────────────────
function getDemoProducts(keyword) {
  const base = [13900, 16900, 9900, 19900, 24900];
  return base.map((price, i) => ({
    productName: `${keyword}${['', ' 프리미엄', ' 2개입', ' 세트', ' 미니'][i]}`,
    productPrice: price,
    productReviewCount: [312, 87, 445, 156, 23][i],
    isRocket: i === 1,
    rank: i + 1,
  }));
}

function getDemoWholesale(keyword) {
  return [
    { source: '도매꾹', name: `${keyword} 도매 단가`, price: 4800, minQty: 10, ship: 3000, match: 88 },
    { source: '도매꾹', name: `${keyword} OEM 대량`, price: 6200, minQty: 30, ship: 0,    match: 74 },
    { source: '도매매', name: `${keyword} 실속형`,   price: 3900, minQty: 50, ship: 2500, match: 67 },
  ];
}

// ─── 서버 시작 ────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\n🚀 쿠팡진입점수 AI 서버 실행 중`);
  console.log(`   http://localhost:${PORT}\n`);
  console.log(`   쿠팡 API: ${process.env.COUPANG_ACCESS_KEY ? '✅ 연결됨' : '❌ 키 없음 (데모 모드)'}`);
  console.log(`   도매꾹 API: ${process.env.DOMEGGOOK_API_KEY ? '✅ 연결됨' : '❌ 키 없음 (크롤링 시도)'}\n`);
});
