(function (root) {
  'use strict';
  var measurementId = 'G-BKKMGV2LY0';
  var products = ['blog','cutdaejang','gomdaeri','cafe','tistory','thread','gif','sooichu','pack_blog','pack_blog_video','pack_multichannel','pack_all','catalog','free_tools','general'];
  var cardProducts = {'card-blog':'blog','card-cut':'cutdaejang','card-detail':'gomdaeri','card-cafe':'cafe','card-tistory':'tistory','card-thread':'thread','card-gif':'gif','card-seoichu':'sooichu'};
  var paramKeys = ['offer_code','term','destination','cta_label','cta_section','cta_intent','path_label','product_id','gallery_id','video_id','video_title','section_id','entry_point','device_path','utm_source','utm_medium','utm_campaign','utm_content','utm_term'];
  function product(element) {
    if (!element || !element.closest) return 'general';
    var explicit = element.closest('[data-product-id]');
    if (explicit && products.indexOf(explicit.getAttribute('data-product-id')) !== -1) return explicit.getAttribute('data-product-id');
    var card = element.closest('.card');
    if (card && cardProducts[card.id]) return cardProducts[card.id];
    var targetId = (element.getAttribute('href') || '').replace(/^#/,'');
    if (cardProducts[targetId]) return cardProducts[targetId];
    var container = element.closest('.pk,.edu');
    var offer = container && container.querySelector('[data-checkout]');
    if (offer) return offer.getAttribute('data-checkout');
    return element.closest('.free-suite') ? 'free_tools' : 'general';
  }
  function attribution() {
    var values = {}, params = new URLSearchParams(root.location.search);
    ['utm_source','utm_medium','utm_campaign','utm_content','utm_term'].forEach(function (key) {
      var value = params.get(key);
      if (value) values[key] = value.slice(0,100);
    });
    try {
      if (Object.keys(values).length) root.sessionStorage.setItem('gomdaeri_attribution',JSON.stringify(values));
      else values = JSON.parse(root.sessionStorage.getItem('gomdaeri_attribution') || '{}');
    } catch (err) { /* Storage can be unavailable in private/file browsing. */ }
    return values && typeof values === 'object' ? values : {};
  }
  function track(name, data) {
    if (!/^gomdaeri_[a-z_]{1,30}$/.test(name)) return false;
    var params = {}, merged = Object.assign({}, attribution(), data || {});
    paramKeys.forEach(function (key) {
      if (typeof merged[key] === 'string' || typeof merged[key] === 'number') params[key] = String(merged[key]).slice(0,100);
    });
    if (params.offer_code && !params.product_id) params.product_id = params.offer_code.replace(/-(?:(1|3|6|12)m|lifetime)$/,'');
    if (cardProducts[params.product_id]) params.product_id = cardProducts[params.product_id];
    params.send_to = measurementId;
    params.transport_type = 'beacon';
    if (typeof root.gtag !== 'function') return false;
    root.gtag('event',name,params);
    return true;
  }
  root.GomdaeriAnalytics = {track:track,product:product};
})(window);
