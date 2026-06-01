/**
 * 쿠팡 파트너스 API 응답 필드 확인용 테스트 스크립트
 * 로컬에서 실행: node test-api.js
 */
require('dotenv').config();
const crypto = require('crypto');
const https  = require('https');

const ACCESS_KEY = process.env.COUPANG_ACCESS_KEY;
const SECRET_KEY = process.env.COUPANG_SECRET_KEY;

function sign(method, path, query) {
  const dt  = new Date().toISOString().replace(/\.\d{3}Z/, 'Z').replace(/[-:]/g, '');
  const msg = dt + method + path + (query ? '?' + query : '');
  const sig = crypto.createHmac('sha256', SECRET_KEY).update(msg).digest('hex');
  return `CEA algorithm=HmacSHA256, access-id=${ACCESS_KEY}, signed-date=${dt}, signature=${sig}`;
}

function get(path, query) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api-gateway.coupang.com',
      path: path + (query ? '?' + query : ''),
      method: 'GET',
      headers: {
        Authorization: sign('GET', path, query),
        'Content-Type': 'application/json;charset=UTF-8',
      },
    };
    const req = https.request(options, res => {
      let body = '';
      res.on('data', d => body += d);
      res.on('end', () => resolve(JSON.parse(body)));
    });
    req.on('error', reject);
    req.end();
  });
}

async function main() {
  console.log('\n[1] 키워드 검색 API 응답 필드 확인 ─────────────────');
  const search = await get(
    '/v2/providers/affiliate_open_api/apis/openapi/v1/products/search',
    'keyword=%EB%A7%88%EC%82%AC%EC%A7%80%EB%B3%BC&limit=2'
  );
  const item = search?.data?.productData?.[0];
  if (item) {
    console.log('\n필드 목록:');
    Object.entries(item).forEach(([k, v]) => console.log(`  ${k}: ${JSON.stringify(v)}`));
  } else {
    console.log('오류:', JSON.stringify(search));
  }

  console.log('\n[2] 베스트셀러 API 응답 필드 확인 ──────────────────');
  const best = await get(
    '/v2/providers/affiliate_open_api/apis/openapi/v1/products/bestcategories',
    'categoryId=1001&limit=2'
  );
  const item2 = best?.data?.productData?.[0];
  if (item2) {
    console.log('\n필드 목록:');
    Object.entries(item2).forEach(([k, v]) => console.log(`  ${k}: ${JSON.stringify(v)}`));
  } else {
    console.log('오류:', JSON.stringify(best));
  }
}

main().catch(console.error);
