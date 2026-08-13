'use strict';

// Content script: injected into Naver Place pages
// Listens for extraction requests from popup

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'EXTRACT_PLACE_DATA') {
    sendResponse({ data: extractPlaceData() });
  }
});

function extractPlaceData() {
  const parts = [];

  const name = firstText(['h1', '.Fc1rA', '#_title', '.place_section_header h2', '[class*="placeName"]']);
  if (name) parts.push('가게명: ' + name);

  const cat = firstText(['.lnJFt', '.GXS1X', '.rTjJo', '[class*="category"]']);
  if (cat) parts.push('업종: ' + cat);

  const addr = firstText(['.LDgIH', '.vV_z_', '.road-address', '[class*="address"]']);
  if (addr) parts.push('주소: ' + addr);

  const phone = firstText(['.xlx7Q', '[class*="phone"]']);
  if (phone) parts.push('전화: ' + phone);

  const hours = firstText(['.A_cdD', '[class*="hours"]', '.businessHours']);
  if (hours) parts.push('영업시간: ' + hours);

  const priceRange = firstText(['[class*="priceInfo"]', '[class*="price"]']);
  if (priceRange) parts.push('가격대: ' + priceRange);

  const menu = allText(['.ISxGJ', '[class*="menu"] .name', '.menu_name'], 25);
  if (menu) parts.push('메뉴/서비스:\n' + menu);

  const reviews = allText(['.zPfVt', '.pui__vn15t2', '[class*="review"] p'], 20);
  if (reviews) parts.push('고객 리뷰:\n' + reviews);

  const keywords = allText(['.pui__WTdsRe', '.keyword_tag', '[class*="keyword"]'], 20);
  if (keywords) parts.push('키워드:\n' + keywords);

  const desc = firstText(['.T8RFa', '.intro_text', '[class*="description"]']);
  if (desc) parts.push('소개: ' + desc.substring(0, 500));

  if (parts.length < 2) {
    parts.push('페이지 텍스트:\n' + document.body.innerText.substring(0, 3000));
  }

  return parts.join('\n\n');
}

function firstText(selectors) {
  for (const sel of selectors) {
    try {
      const el = document.querySelector(sel);
      const t = el?.innerText?.trim();
      if (t) return t;
    } catch { /* invalid selector */ }
  }
  return '';
}

function allText(selectors, limit = 10) {
  for (const sel of selectors) {
    try {
      const els = [...document.querySelectorAll(sel)].slice(0, limit);
      const texts = els.map(e => e.innerText?.trim()).filter(Boolean);
      if (texts.length) return texts.join('\n');
    } catch { /* invalid selector */ }
  }
  return '';
}
