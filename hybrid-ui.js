(function () {
  'use strict';
  var analytics = window.GomdaeriAnalytics;
  var track = function (name, data) { if (analytics) analytics.track(name, data); };
  var product = function (element) { return analytics ? analytics.product(element) : 'general'; };
  var names = {blog:'블로그대리',cutdaejang:'컷대장',gomdaeri:'상세대리',cafe:'카페대리',tistory:'티스토리대리',thread:'스레드대리',gif:'움짤대리',sooichu:'서이추대리',free_tools:'무료 도구 6종'};
  // OS is what determines installation support; a narrow Windows window is still a PC.
  var mobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) ||
    (/Macintosh/i.test(navigator.userAgent) && navigator.maxTouchPoints > 1);
  var unsupported = !mobile && /Macintosh|Linux|CrOS/i.test(navigator.userAgent) && !/Windows/i.test(navigator.userAgent);
  var needsHandoff = mobile || unsupported;
  if (needsHandoff) {
    document.documentElement.dataset.deviceHandoff = mobile ? 'mobile' : 'other_os';
    document.querySelectorAll('[data-trial-download],[data-free-tools-download]').forEach(function (link) {
      var shortLabel = !!link.closest('nav,.dock');
      var free = link.hasAttribute('data-free-tools-download');
      var label = names[product(link)];
      link.textContent = free ? '무료 도구 PC 설치 링크 받기 →' : shortLabel ? 'PC용 체험 링크 받기' : (label ? label + ' · ' : '') + 'PC용 체험 링크 받기';
      link.setAttribute('aria-haspopup','dialog');
    });
    var deviceNote = document.querySelector('[data-device-explanation]');
    if (deviceNote) {
      deviceNote.hidden = false;
      deviceNote.textContent = mobile ? '휴대폰에서는 결과를 확인하고, 설치 링크를 보관해 Windows PC에서 이어서 시작하세요.' : '이 기기에서는 실행되지 않습니다. 설치 링크를 보관해 Windows PC에서 시작하세요.';
    }
  }
  function placement(element) {
    var area = element.closest('.card,.pk,.free-suite,.dock,nav,section,header');
    return area ? area.id || (area.classList.contains('dock') ? 'mobile_dock' : 'general') : 'general';
  }
  // Reveal every enclosing fold so product / checkout bookmarks remain usable.
  function revealDetails(target) {
    var node = target, changed = false;
    while (node) {
      if (node.tagName === 'DETAILS' && !node.open) { node.open = true; changed = true; }
      node = node.parentElement;
    }
    return changed;
  }
  // Native details also works without JavaScript; direct hash links open it first.
  function openHashDetails() {
    var id;
    try { id = decodeURIComponent(window.location.hash.slice(1)); } catch (err) { return; }
    if (!id) return;
    var target = document.getElementById(id);
    if (!target) return;
    if (revealDetails(target)) target.scrollIntoView({block:'start'});
  }
  var priceFold = document.getElementById('all-prices');
  if (priceFold) priceFold.addEventListener('toggle', function () {
    var label = priceFold.querySelector('.fold-label');
    if (label) label.textContent = priceFold.open ? '접기 −' : '펼쳐보기 +';
    if (priceFold.open) track('gomdaeri_prices_open', {section_id:'all-prices'});
  });
  document.querySelectorAll('a[href^="#"]').forEach(function (link) {
    link.addEventListener('click', function () {
      var target = document.getElementById(link.getAttribute('href').slice(1));
      if (target) revealDetails(target);
      if (link.matches('.hub-path,.hr-chip,.hub-shortcuts a')) track('gomdaeri_product_path', {product_id:product(link),destination:link.getAttribute('href'),entry_point:placement(link)});
    });
  });
  window.addEventListener('hashchange',openHashDetails);
  openHashDetails();

  document.querySelectorAll('.product-pricing,#other-programs,#proof').forEach(function (fold) {
    fold.addEventListener('toggle', function () {
      if (fold.open) track(fold.classList.contains('product-pricing') ? 'gomdaeri_prices_open' : 'gomdaeri_section_view', {section_id:fold.id,product_id:product(fold)});
    });
  });
  document.querySelectorAll('.feature-fold').forEach(function (fold) {
    fold.addEventListener('toggle',function () {
      if (fold.open) track('gomdaeri_feature_expand',{product_id:product(fold),entry_point:placement(fold)});
    });
  });

  var dialog = document.getElementById('trial-dialog');
  var urlField = dialog.querySelector('#trial-pc-url');
  var status = dialog.querySelector('.trial-copy-status');
  var help = dialog.querySelector('.trial-help');
  var direct = dialog.querySelector('.trial-direct');
  var share = dialog.querySelector('.trial-share');
  if (share) share.hidden = typeof navigator.share !== 'function';
  var trigger = null, activeProduct = 'general', activeEntry = 'general', previousOverflow = '';
  function closeDialog() { if (dialog.open) dialog.close(); }
  dialog.querySelector('.trial-dialog-close').addEventListener('click',closeDialog);
  dialog.addEventListener('click',function (e) { if (e.target === dialog) { var r = dialog.getBoundingClientRect(); if(e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) closeDialog(); } });
  dialog.addEventListener('close',function () {
    document.body.style.overflow = previousOverflow;
    if (trigger && document.contains(trigger)) trigger.focus({preventScroll:true});
  });
  document.querySelectorAll('[data-trial-download],[data-free-tools-download]').forEach(function (link) {
    link.addEventListener('click',function (event) {
      if (event.defaultPrevented) return;
      // A narrow PC window still supports the installer; width alone is not a device check.
      var freeTools = link.hasAttribute('data-free-tools-download');
      var productId = freeTools ? 'free_tools' : product(link);
      var entry = placement(link);
      track(freeTools ? 'gomdaeri_free_tools_click' : 'gomdaeri_trial_click', {product_id:productId,entry_point:entry,device_path:mobile?'mobile_pc_handoff':unsupported?'other_os_pc_handoff':'desktop_download',destination:'mindhub_download_guide'});
      // Modified clicks preserve normal browser behavior and the existing server fallback.
      if (!needsHandoff || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || typeof dialog.showModal !== 'function') return;
      event.preventDefault();
      trigger = link; activeProduct = productId; activeEntry = entry;
      urlField.value = link.href;
      direct.href = link.href;
      help.setAttribute('data-product-id', productId);
      help.setAttribute('data-cta-intent',(names[productId] || '곰대리') + ' 설치·체험 도움');
      dialog.querySelector('#trial-dialog-product').textContent = freeTools ? '무료 도구 6종 · 유료 구독 없이 이용' : (names[productId] || '곰대리 프로그램') + ' · 무료 7일 체험';
      dialog.querySelector('#trial-dialog-title').innerHTML = freeTools ? '무료 도구 설치 링크를<br>PC에서 열어 주세요.' : '이 링크를 보관하고,<br>Windows PC에서 시작하세요.';
      dialog.querySelector('.install-note').textContent = freeTools ? '무료 도구는 7일 체험과 별개로 유료 구독 없이 이용합니다. 일부 기능의 API 연결 및 AI·외부 서비스 이용료는 별도입니다.' : '7일 체험 · 1인 1회 · 카드 등록 없음 · AI 사용료 별도. 무료 도구 6종은 유료 구독 없이 이용할 수 있습니다.';
      dialog.querySelector('.trial-dialog-close').setAttribute('aria-label',freeTools ? '설치 안내 닫기' : '체험 안내 닫기');
      help.textContent = freeTools ? '설치 도움 카카오톡 문의' : '설치·체험 카카오톡 문의';
      status.textContent = '';
      previousOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      dialog.showModal();
      (share && !share.hidden ? share : dialog.querySelector('.trial-copy')).focus({preventScroll:true});
      track(mobile ? 'gomdaeri_mobile_guide' : 'gomdaeri_pc_handoff', {product_id:productId,entry_point:entry});
    });
  });
  if (share) share.addEventListener('click',async function () {
    if (typeof navigator.share !== 'function') return;
    var productName = names[activeProduct] || '곰대리 프로그램';
    try {
      await navigator.share({title:productName + ' · Windows PC 설치 안내',text:productName + ' 설치 링크입니다. Windows PC에서 마인드허브를 설치한 뒤 필요한 프로그램을 선택하세요.',url:urlField.value});
      status.textContent = '공유한 링크를 Windows PC에서 열어 설치를 이어가세요.';
      track('gomdaeri_pc_link_share', {product_id:activeProduct,entry_point:activeEntry});
    } catch (err) {
      status.textContent = err && err.name === 'AbortError' ? '공유를 취소했습니다. 링크 복사로도 보관할 수 있습니다.' : '이 환경에서는 공유를 열 수 없습니다. 아래 링크 복사를 이용해 주세요.';
    }
  });
  dialog.querySelector('.trial-copy').addEventListener('click',async function () {
    var copied = false;
    try { if (navigator.clipboard && navigator.clipboard.writeText) { await navigator.clipboard.writeText(urlField.value); copied = true; } } catch (err) { /* Try selection fallback below. */ }
    if (!copied) { urlField.focus(); urlField.select(); try { copied = document.execCommand('copy'); } catch (err) {} }
    status.textContent = copied ? '복사했습니다. 나와의 채팅·메모에 붙여넣고 PC에서 열어 주세요.' : '주소를 선택했습니다. 길게 누르거나 Ctrl+C로 복사해 주세요.';
    if (copied) track('gomdaeri_pc_link_copy', {product_id:activeProduct,entry_point:activeEntry});
  });
  direct.addEventListener('click',function () { track('gomdaeri_download_guide', {product_id:activeProduct,entry_point:activeEntry,destination:'mindhub_download_guide'}); });

  // One qualified view per section/card, after at least one second in view.
  if ('IntersectionObserver' in window) {
    var timers = new Map();
    var sections = new Map();
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var target = entry.target;
        if (entry.isIntersecting) {
          if (timers.has(target)) return;
          timers.set(target,setTimeout(function () {
            var section = sections.get(target) || target;
            if (!document.hidden) { track('gomdaeri_section_view', {section_id:section.id,product_id:product(section)}); observer.unobserve(target); }
            timers.delete(target);
          },1000));
        } else if (timers.has(target)) { clearTimeout(timers.get(target)); timers.delete(target); }
      });
    },{threshold:0.15});
    document.querySelectorAll('#card-blog,#card-cut,#other-programs,#package,#free-tools,#edu,#trial-guide').forEach(function (el) {
      var target = el.querySelector('.sec-head') || el;
      sections.set(target,el);
      observer.observe(target);
    });
  }
})();
