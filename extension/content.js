// Runs on Coupang pages — extracts product data from the DOM

(function() {
  'use strict';

  function extractSearchPage() {
    const items = [];
    // Coupang search result items
    const rows = document.querySelectorAll('li.search-product, li[id^="productId"]');
    rows.forEach((el, i) => {
      if (i >= 20) return;
      const name = el.querySelector('.name')?.textContent?.trim()
        || el.querySelector('.title')?.textContent?.trim() || '';
      const priceEl = el.querySelector('.price-value, .price strong, [class*="price"]');
      const price = parseInt((priceEl?.textContent || '0').replace(/[^0-9]/g,'')) || 0;
      const reviewEl = el.querySelector('[class*="rating-total-count"], .ratingValue');
      const reviews = parseInt((reviewEl?.textContent || '0').replace(/[^0-9]/g,'')) || 0;
      const isRocket = !!el.querySelector('[class*="rocket"], .badge-rocket, [alt*="로켓"]');
      if (name && price > 0) {
        items.push({ rank: i+1, name, price, reviews, rocket: isRocket });
      }
    });
    return items;
  }

  function extractProductPage() {
    const name = document.querySelector('h1.prod-buy-header__title, .prod-title')?.textContent?.trim()
      || document.querySelector('title')?.textContent?.split('|')[0]?.trim() || '';

    const priceEl = document.querySelector('.prod-price .total-price strong, [class*="total-price"] strong, .price-value');
    const price = parseInt((priceEl?.textContent || '0').replace(/[^0-9]/g,'')) || 0;

    const reviewCount = parseInt(
      (document.querySelector('.count.notranslate, [class*="rating-total-count"]')?.textContent || '0')
        .replace(/[^0-9]/g,'')
    ) || 0;

    const ratingEl = document.querySelector('.ratingValue, [class*="rating"] .review-star-num');
    const rating = parseFloat(ratingEl?.textContent || '0') || 0;

    const isRocket = !!document.querySelector('[class*="rocket-badge"], .badge-rocket, img[alt*="로켓배송"]');
    const isCoupangSell = !!document.querySelector('[class*="coupang-seller"], [title="쿠팡"]');

    // Gather seller count from similar products widget if present
    const sellerCount = document.querySelectorAll('.other-seller-item, [class*="seller-product-item"]').length || 1;

    return { name, price, reviewCount, rating, isRocket, isCoupangSell, sellerCount };
  }

  function getPageType() {
    const url = location.href;
    if (url.includes('/vp/products/') || url.includes('/products/')) return 'product';
    if (url.includes('/np/search/') || url.includes('q=') || url.includes('searchKeyword=')) return 'search';
    return 'other';
  }

  // Listen for requests from popup
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.action === 'extract') {
      const type = getPageType();
      if (type === 'product') {
        sendResponse({ type: 'product', data: extractProductPage(), url: location.href });
      } else if (type === 'search') {
        const keyword = new URLSearchParams(location.search).get('q')
          || new URLSearchParams(location.search).get('searchKeyword') || '';
        sendResponse({ type: 'search', keyword, items: extractSearchPage(), url: location.href });
      } else {
        sendResponse({ type: 'other' });
      }
    }
    return true;
  });
})();
