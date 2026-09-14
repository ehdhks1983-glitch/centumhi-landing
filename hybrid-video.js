(function(){
'use strict';
function track(name,data){if(window.GomdaeriAnalytics)window.GomdaeriAnalytics.track(name,data||{});}
document.querySelector('[data-purchase-entry]').addEventListener('click',function(){track('gomdaeri_purchase_select',{entry_point:'page_bottom',destination:'product_selection'});});
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

})();
