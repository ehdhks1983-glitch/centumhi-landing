/*
 * 곰대리 랜딩페이지용 공개 래피드 결제 설정.
 * 브라우저에 노출되는 파일이므로 웹훅 비밀값·API 키·고객정보를 넣지 않습니다.
 * 판매 URL과 웹훅 설정은 2026-08-28 운영 계정에서 전수 확인했습니다.
 * 공개 결제 버튼은 게시와 웹훅 연결이 확인된 상품만 개별 허용합니다.
 */
window.GOMDAERI_CHECKOUT_CONFIG = {
  "version": "2026-09-05-v10",
  "checkout_enabled": true,
  "enabled_offers": [
    "pack_blog-1m", "pack_blog-3m", "pack_blog-6m", "pack_blog-12m",
    "pack_blog_video-1m", "pack_blog_video-3m", "pack_blog_video-6m",
    "pack_multichannel-1m", "pack_multichannel-3m", "pack_multichannel-6m",
    "blog-1m", "blog-3m", "blog-6m", "blog-12m",
    "sooichu-1m", "sooichu-3m", "sooichu-6m", "sooichu-12m",
    "cutdaejang-1m", "cutdaejang-3m", "cutdaejang-6m", "cutdaejang-12m",
    "cafe-1m", "cafe-3m", "cafe-6m", "cafe-12m",
    "thread-1m", "thread-3m", "thread-6m", "thread-12m",
    "tistory-1m", "tistory-3m", "tistory-6m", "tistory-12m",
    "gif-1m", "gif-3m", "gif-6m", "gif-12m",
    "service_remote_3h", "service_visit_3h", "service_remote_4w", "service_incheon_4w"
  ],
  "enabled_promotions": [],
  "membership_space_id": "6a7c3c685dabffbb9308a54d",
  "links": {
    "pack_blog-1m": "https://www.latpeed.com/memberships/6a7c3c685dabffbb9308a54d/pay/532GR",
    "pack_blog-3m": "https://www.latpeed.com/products/sJWRU",
    "pack_blog-6m": "https://www.latpeed.com/products/3BkNV",
    "pack_blog-12m": "https://www.latpeed.com/products/EwVSs",
    "pack_blog_video-1m": "https://www.latpeed.com/memberships/6a7c3c685dabffbb9308a54d/pay/nbZ2j",
    "pack_blog_video-3m": "https://www.latpeed.com/products/bPt6Y",
    "pack_blog_video-6m": "https://www.latpeed.com/products/LfQiX",
    "pack_blog_video-12m": "",
    "pack_multichannel-1m": "https://www.latpeed.com/memberships/6a7c3c685dabffbb9308a54d/pay/rRfJ1",
    "pack_multichannel-3m": "https://www.latpeed.com/products/8FK0j",
    "pack_multichannel-6m": "https://www.latpeed.com/products/4hqb8",
    "pack_multichannel-12m": "",
    "pack_all-1m": "",
    "pack_all-3m": "",
    "pack_all-6m": "",
    "pack_all-12m": "",
    "pack_all-lifetime": "",
    "blog-1m": "https://www.latpeed.com/memberships/6a7c3c685dabffbb9308a54d/pay/ZR1lK",
    "blog-3m": "https://www.latpeed.com/products/qZ8gD",
    "blog-6m": "https://www.latpeed.com/products/u9GkP",
    "blog-12m": "https://www.latpeed.com/products/_nUXk",
    "sooichu-1m": "https://www.latpeed.com/memberships/6a7c3c685dabffbb9308a54d/pay/3_SKS",
    "sooichu-3m": "https://www.latpeed.com/products/O8XUe",
    "sooichu-6m": "https://www.latpeed.com/products/85obr",
    "sooichu-12m": "https://www.latpeed.com/products/1ic6m",
    "cutdaejang-1m": "https://www.latpeed.com/memberships/6a7c3c685dabffbb9308a54d/pay/w3Se9",
    "cutdaejang-3m": "https://www.latpeed.com/products/xEjqQ",
    "cutdaejang-6m": "https://www.latpeed.com/products/TDNJE",
    "cutdaejang-12m": "https://www.latpeed.com/products/BuoAS",
    "cafe-1m": "https://www.latpeed.com/memberships/6a7c3c685dabffbb9308a54d/pay/u7Ckb",
    "cafe-3m": "https://www.latpeed.com/products/vhaOC",
    "cafe-6m": "https://www.latpeed.com/products/tx0ba",
    "cafe-12m": "https://www.latpeed.com/products/LD_go",
    "thread-1m": "https://www.latpeed.com/memberships/6a7c3c685dabffbb9308a54d/pay/sAZ3Z",
    "thread-3m": "https://www.latpeed.com/products/_Kimo",
    "thread-6m": "https://www.latpeed.com/products/EI86N",
    "thread-12m": "https://www.latpeed.com/products/88ExC",
    "tistory-1m": "https://www.latpeed.com/memberships/6a7c3c685dabffbb9308a54d/pay/s-DI6",
    "tistory-3m": "https://www.latpeed.com/products/7_wUA",
    "tistory-6m": "https://www.latpeed.com/products/pHgDD",
    "tistory-12m": "https://www.latpeed.com/products/iPech",
    "gomdaeri-1m": "",
    "gomdaeri-3m": "",
    "gomdaeri-6m": "",
    "gomdaeri-12m": "",
    "gif-1m": "https://www.latpeed.com/memberships/6a7c3c685dabffbb9308a54d/pay/KowIW",
    "gif-3m": "https://www.latpeed.com/products/lf52t",
    "gif-6m": "https://www.latpeed.com/products/iAp4p",
    "gif-12m": "https://www.latpeed.com/products/ZyHwH",
    "service_remote_3h": "https://www.latpeed.com/products/oqELu",
    "service_visit_3h": "https://www.latpeed.com/products/wHyp-",
    "service_remote_4w": "https://www.latpeed.com/products/pTYEC",
    "service_incheon_4w": "https://www.latpeed.com/products/ph9Ca"
  },
  "blocked_reasons": {
    "gomdaeri": "온라인 결제 미연결: 카카오톡으로 별도 결제 안내",
    "pack_all": "온라인 결제 미연결: 카카오톡으로 별도 결제 안내"
  },
  "consultation_required": [
    "gomdaeri-1m", "gomdaeri-3m", "gomdaeri-6m", "gomdaeri-12m",
    "pack_all-lifetime",
    "pack_blog_video-12m", "pack_multichannel-12m"
  ]
};
