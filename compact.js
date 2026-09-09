(function(){
 'use strict';
 var catalog=window.GOMDAERI_CATALOG||{offers:[],services:[]};
 var config=window.GOMDAERI_CHECKOUT_CONFIG||{};
 var inquiry='https://pf.kakao.com/_mnxoxlX/chat';
 var guide='https://license.gomdaeri.kr/download/mindhub?from=home';
 var offers=Object.fromEntries(catalog.offers.map(function(o){return[o.id,o];}));
 var terms=['1m','3m','6m','12m'];
 var activeOffer=null,activeTerm='1m',activeHandoff='general';
 var offerDialog=document.getElementById('offer-dialog'),handoffDialog=document.getElementById('handoff-dialog');
 var callers=new Map();
 var ua=navigator.userAgent;
 var mobile=/Android|iPhone|iPad|iPod/i.test(ua)||(/Macintosh/i.test(ua)&&navigator.maxTouchPoints>1);
 var needsHandoff=mobile||(/Macintosh|Linux|CrOS/i.test(ua)&&!/Windows/i.test(ua));
 function track(name,data){if(window.GomdaeriAnalytics)window.GomdaeriAnalytics.track(name,data||{});}
 function money(n){return Number(n).toLocaleString('ko-KR')+'원';}
 function titleFor(id){return id==='free_tools'?'무료 도구 6종':offers[id]?offers[id].name:'곰대리 프로그램';}
 function show(dialog,caller){if(typeof dialog.showModal!=='function')return false;callers.set(dialog,caller);dialog.showModal();return true;}
 document.querySelectorAll('dialog').forEach(function(dialog){
  dialog.querySelector('[data-close]').addEventListener('click',function(){dialog.close();});
  dialog.addEventListener('close',function(){var caller=callers.get(dialog);if(caller&&document.contains(caller))caller.focus({preventScroll:true});});
  dialog.addEventListener('click',function(e){if(e.target!==dialog)return;var r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();});
 });
 // Same allow-list and consultation gates as 1안. Unknown links always fall back to inquiry.
 function checkout(id,term,service){
  var key=service?id:id+'-'+term,value=(config.links||{})[key],ok=false;
  if(config.checkout_enabled===true&&Array.isArray(config.enabled_offers)&&config.enabled_offers.includes(key)&&!Object.prototype.hasOwnProperty.call(config.blocked_reasons||{},id)&&!(config.consultation_required||[]).includes(key)){
   try{var url=new URL(value);ok=url.origin==='https://www.latpeed.com'&&!url.username&&!url.password&&!url.search&&!url.hash;
    if(!service&&term==='1m'){var space=String(config.membership_space_id||'');ok=ok&&/^[a-zA-Z0-9]+$/.test(space)&&url.pathname.startsWith('/memberships/'+space+'/pay/')&&/\/pay\/[A-Za-z0-9_-]+\/?$/.test(url.pathname);}
    else ok=ok&&/^\/products\/[A-Za-z0-9_-]+\/?$/.test(url.pathname);
   }catch(e){ok=false;}
  }
  return{url:ok?value:inquiry,destination:ok?'latpeed':'kakao_chat',code:key,direct:ok};
 }
 function updateOffer(){
  if(!activeOffer)return;
  var price=activeOffer.prices[activeTerm],months=parseInt(activeTerm,10),regular=activeOffer.prices['1m']*months,saving=regular-price;
  var route=checkout(activeOffer.id,activeTerm,false),link=document.getElementById('offer-checkout');
  document.querySelectorAll('[data-term]').forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.term===activeTerm));});
  document.getElementById('offer-term-label').textContent=months+'개월 이용료';
  document.getElementById('offer-price').textContent=money(price);
  var savingEl=document.getElementById('offer-saving');savingEl.hidden=saving<=0;
  savingEl.textContent=saving>0?'월요금 × '+months+'회 '+money(regular)+' 대비 '+money(saving)+' 절감 (약 '+Math.round(saving/regular*100)+'%)':'';
  document.getElementById('offer-billing').textContent=route.direct?(activeTerm==='1m'?'카드 정기결제 · 해지 전 매월 자동갱신':'표시 금액 1회 결제 · 이용기간 종료 후 자동갱신 없음'):'이 상품·기간은 카카오톡으로 별도 결제 방법을 안내합니다.';
  link.href=route.url;link.dataset.destination=route.destination;link.dataset.offerCode=route.code;link.textContent=money(price)+' · '+(route.direct?'결제하기':'결제 문의');
 }
 document.querySelectorAll('[data-open-offer]').forEach(function(link){link.addEventListener('click',function(e){
  if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
  var selected=offers[link.dataset.openOffer];if(!selected||typeof offerDialog.showModal!=='function')return;
  e.preventDefault();activeOffer=selected;activeTerm='1m';
  document.getElementById('offer-title').textContent=selected.name;document.getElementById('offer-description').textContent=selected.description;
  var list=document.getElementById('offer-features');list.replaceChildren();
  (selected.features.length?selected.features:selected.includes.map(function(n){return n+' 포함';})).forEach(function(value){var li=document.createElement('li');li.textContent=value;list.appendChild(li);});
  offerDialog.querySelector('.offer-features').open=false;
  var video=document.getElementById('offer-video');video.hidden=!selected.video;video.href=selected.id==='cutdaejang'?'#cut-video':'https://www.youtube.com/watch?v='+selected.video;
  video.textContent=selected.id==='cutdaejang'?'컷대장 활용 영상 보기 ↗':'작동 영상 보기 ↗';
  if(selected.id==='cutdaejang'){video.removeAttribute('target');}else{video.target='_blank';video.rel='noopener';}
  var trial=document.getElementById('offer-trial');trial.dataset.productId=selected.id;trial.textContent=needsHandoff?'PC용 체험 링크 받기':'먼저 무료 7일 체험하기';
  updateOffer();show(offerDialog,link);track('gomdaeri_prices_open',{product_id:selected.id,entry_point:link.closest('.product')?'product_card':'price_comparison'});
 });});
 document.querySelectorAll('[data-term]').forEach(function(b){b.addEventListener('click',function(){if(!terms.includes(b.dataset.term))return;activeTerm=b.dataset.term;updateOffer();track('gomdaeri_term_select',{product_id:activeOffer.id,term:activeTerm});});});
 document.getElementById('offer-checkout').addEventListener('click',function(){if(!activeOffer)return;track('gomdaeri_checkout_click',{offer_code:this.dataset.offerCode,product_id:activeOffer.id,term:activeTerm,destination:this.dataset.destination});});
 document.getElementById('offer-video').addEventListener('click',function(){if(activeOffer&&activeOffer.id==='cutdaejang')offerDialog.close();});
 document.querySelectorAll('[data-service]').forEach(function(link){var service=catalog.services.find(function(s){return s.id===link.dataset.service;});if(!service)return;var route=checkout(service.id,'',true);link.href=route.url;link.textContent=route.direct?'결제하기 ↗':'결제 문의 ↗';link.addEventListener('click',function(){track('gomdaeri_checkout_click',{offer_code:service.id,term:'one_time',destination:route.destination});});});
 document.querySelector('[data-lifetime]').addEventListener('click',function(){track('gomdaeri_checkout_click',{offer_code:'pack_all-lifetime',product_id:'pack_all',term:'lifetime',destination:'kakao_chat'});});
 document.querySelectorAll('[data-inquiry]').forEach(function(a){a.addEventListener('click',function(){track('gomdaeri_cta_click',{cta_intent:a.dataset.inquiry,destination:'kakao_chat'});});});
 document.querySelector('[data-purchase-entry]').addEventListener('click',function(){track('gomdaeri_purchase_select',{entry_point:'page_bottom',destination:'product_selection'});});
 var field=document.getElementById('pc-link'),share=document.getElementById('share-link'),status=document.getElementById('copy-status'),handoffDirect=document.getElementById('handoff-direct');
 share.hidden=typeof navigator.share!=='function';
 document.querySelectorAll('[data-trial]').forEach(function(a){
  if(needsHandoff){a.textContent=a.hasAttribute('data-free')?'무료 도구 PC 링크 받기':'PC용 체험 링크 받기';a.setAttribute('aria-haspopup','dialog');}
  a.addEventListener('click',function(e){
   var id=a.hasAttribute('data-free')?'free_tools':a.dataset.productId||'general';
   track(id==='free_tools'?'gomdaeri_free_tools_click':'gomdaeri_trial_click',{product_id:id,device_path:mobile?'mobile_pc_handoff':needsHandoff?'other_os_pc_handoff':'desktop_download',entry_point:a.closest('dialog')?'offer_dialog':a.closest('.hero')?'hero':'page',destination:'mindhub_download_guide'});
   if(!needsHandoff||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||typeof handoffDialog.showModal!=='function')return;
   e.preventDefault();activeHandoff=id;field.value=a.href;handoffDirect.href=a.href;status.textContent='';document.getElementById('handoff-product').textContent=titleFor(id)+(id==='free_tools'?' · 유료 구독 없이 이용':' · 무료 7일 체험');show(handoffDialog,a);(share.hidden?document.getElementById('copy-link'):share).focus();track(mobile?'gomdaeri_mobile_guide':'gomdaeri_pc_handoff',{product_id:id});
  });
 });
 share.addEventListener('click',async function(){try{await navigator.share({title:titleFor(activeHandoff)+' · Windows 설치 안내',text:'Windows PC에서 마인드허브를 설치한 뒤 원하는 프로그램을 선택하세요.',url:field.value});status.textContent='공유한 링크를 Windows PC에서 열어 설치를 이어가세요.';track('gomdaeri_pc_link_share',{product_id:activeHandoff});}catch(e){status.textContent=e.name==='AbortError'?'공유를 취소했습니다. 링크 복사도 이용할 수 있습니다.':'공유를 열 수 없습니다. 아래 링크 복사를 이용해 주세요.';}});
 document.getElementById('copy-link').addEventListener('click',async function(){var copied=false;try{if(navigator.clipboard&&navigator.clipboard.writeText){await navigator.clipboard.writeText(field.value);copied=true;}}catch(e){}if(!copied){field.focus();field.select();try{copied=document.execCommand('copy');}catch(e){}}status.textContent=copied?'복사했습니다. 메모·메신저에 보관한 뒤 Windows PC에서 열어 주세요.':'주소를 선택했습니다. 길게 누르거나 Ctrl+C로 복사해 주세요.';if(copied)track('gomdaeri_pc_link_copy',{product_id:activeHandoff});});
 handoffDirect.addEventListener('click',function(){track('gomdaeri_download_guide',{product_id:activeHandoff});});
 // Count only YouTube's actual PLAYING state, never an iframe load or guide expansion.
 var players=new Map(),playedVideos=new Set(),videoGuide=document.getElementById('basic-guide');
 function embedSource(frame){
  var url=new URL(frame.getAttribute('src')||frame.dataset.src);
  if(/^https?:$/.test(location.protocol))url.searchParams.set('origin',location.origin);
  frame.src=url.href;
 }
 function connectPlayer(frame){
  if(!frame.getAttribute('src')||!window.YT||typeof window.YT.Player!=='function'||players.has(frame.id))return;
  try{players.set(frame.id,new window.YT.Player(frame.id,{events:{
   onStateChange:function(e){if(e.data!==1||playedVideos.has(frame.id))return;playedVideos.add(frame.id);track('gomdaeri_video_play',{product_id:frame.dataset.videoProduct,video_id:frame.dataset.videoId,entry_point:frame.dataset.videoEntry});},
   onError:function(){frame.parentElement.querySelector('.video-error').hidden=false;}
  }}));}catch(e){} // Playback and the direct YouTube link still work if analytics cannot attach.
 }
 document.querySelectorAll('.youtube-player[src]').forEach(embedSource);
 videoGuide.addEventListener('toggle',function(){
  var frame=document.getElementById('basic-guide-video');
  if(this.open){if(!frame.getAttribute('src'))embedSource(frame);connectPlayer(frame);}
  else{var player=players.get(frame.id);if(player&&typeof player.pauseVideo==='function')player.pauseVideo();}
 });
 var previousYouTubeReady=window.onYouTubeIframeAPIReady;
 window.onYouTubeIframeAPIReady=function(){if(typeof previousYouTubeReady==='function')previousYouTubeReady();document.querySelectorAll('.youtube-player[src]').forEach(connectPlayer);};
 if(window.YT&&typeof window.YT.Player==='function')window.onYouTubeIframeAPIReady();
 else{var youtubeApi=document.createElement('script');youtubeApi.src='https://www.youtube.com/iframe_api';youtubeApi.async=true;document.head.appendChild(youtubeApi);}
 function revealHash(){
  var id;try{id=decodeURIComponent(location.hash.slice(1));}catch(e){return;}
  // Keep links from previous ads, guides and saved bookmarks working after replacement.
  if(id.indexOf('price-')===0&&offers[id.slice(6)]){var offerLink=document.querySelector('[data-open-offer="'+id.slice(6)+'"]');if(offerLink&&!offerDialog.open)offerLink.click();return;}
  var aliases={'choose-work':'roster','catalog':'roster','other-programs':'roster','trial-guide':'start','proof-details':'proof','proof-gallery':'proof','case-gallery':'proof','reviews':'proof','pack-all':'unlimited-offer','safe':'start','faq':'start'};
  var original=id;id=aliases[id]||id;
  var el=document.getElementById(id);if(!el)return;for(var p=el;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;
  if(original!==id){history.replaceState(null,'',location.pathname+location.search+'#'+id);el.scrollIntoView({block:'start'});}
 }
 document.querySelectorAll('a[href^="#"]').forEach(function(a){a.addEventListener('click',function(e){if(e.defaultPrevented||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;var el=document.getElementById(a.getAttribute('href').slice(1));for(var p=el;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;});});
 window.addEventListener('hashchange',revealHash);revealHash();
 document.getElementById('all-prices').addEventListener('toggle',function(){if(this.open)track('gomdaeri_prices_open',{section_id:'all-prices'});});
 if('IntersectionObserver'in window){var timers=new Map();var observer=new IntersectionObserver(function(entries){entries.forEach(function(entry){if(entry.isIntersecting&&!timers.has(entry.target)){timers.set(entry.target,setTimeout(function(){if(!document.hidden){track('gomdaeri_section_view',{section_id:entry.target.id});observer.unobserve(entry.target);}timers.delete(entry.target);},1000));}else if(!entry.isIntersecting){clearTimeout(timers.get(entry.target));timers.delete(entry.target);}});},{threshold:.15});document.querySelectorAll('main>section').forEach(function(el){observer.observe(el);});}
})();
