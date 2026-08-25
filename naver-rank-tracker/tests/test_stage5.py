"""⑤ 파서 내구성 검증 — 마크업/키 이름이 바뀌어도 인식되는지."""
import json, os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db
db.DB_PATH = os.path.join(tempfile.mkdtemp(), "s5.db")
db.init_db()

import coupang
import naver_web

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))

# ══ 쿠팡 ══
# A. 현재 구조 (search-product li + div.name)
cur = ('<ul>'
       '<li class="search-product search-product__ad-badge" data-product-id="1" data-item-id="11" data-vendor-item-id="111">'
       '<div class="name">광고상품</div></li>'
       '<li class="search-product" data-product-id="2" data-item-id="22" data-vendor-item-id="222">'
       '<div class="name">일반상품 A</div></li></ul>')
items = coupang.parse_items(cur)
check("쿠팡 A: 현재 구조", len(items) == 2 and items[0]["is_ad"] and not items[1]["is_ad"]
      and items[1]["vendorItemId"] == "222" and items[1]["title"] == "일반상품 A", str(items[:1]))

# B. 클래스명 전면 변경 + div 기반 + product-name 클래스 (리뉴얼 가정)
renamed = ('<div class="srp-list">'
           '<div class="srp-card srp-card--admark" data-product-id="7" data-vendor-item-id="777">'
           '<span class="product-name">광고B</span></div>'
           '<div class="srp-card" data-product-id="8" data-vendor-item-id="888">'
           '<span class="product-name">일반상품 B</span></div></div>')
items = coupang.parse_items(renamed)
check("쿠팡 B: 클래스명 전면 변경에도 인식", len(items) == 2 and items[1]["title"] == "일반상품 B"
      and items[1]["vendorItemId"] == "888" and items[0]["is_ad"], str(items))

# C. 중첩 앵커(li 안에 a) — 중복 계상 안 됨
nested = ('<li class="search-product" data-product-id="9" data-item-id="99">'
          '<a data-product-id="9" href="#"><div class="name">중첩상품</div></a></li>')
items = coupang.parse_items(nested)
check("쿠팡 C: 중첩 태그 중복 제거", len(items) == 1 and items[0]["title"] == "중첩상품", str(items))

# D. 제목이 img alt로만 존재
altonly = '<li class="search-product" data-product-id="5"><img alt="이미지제목상품" src="x.jpg"></li>'
items = coupang.parse_items(altonly)
check("쿠팡 D: img alt에서 제목 추출", len(items) == 1 and items[0]["title"] == "이미지제목상품", str(items))

# E. 마크업 소멸 → 내장 JSON 대체 경로
jsonpage = ('<html><script>window.__DATA__={"list":['
            '{"productId":31,"productName":"JSON상품1","vendorItemId":311,"isAd":true},'
            '{"productId":32,"productName":"JSON상품2","vendorItemId":322}]}</script></html>')
items = coupang.parse_items(jsonpage)
check("쿠팡 E: 마크업 소멸 시 JSON 대체 경로", len(items) == 2 and items[1]["title"] == "JSON상품2"
      and items[1]["vendorItemId"] == "322" and items[0]["is_ad"], str(items))

# F. 완전히 못 알아보는 페이지 → 빈 리스트 (호출부가 덤프 남김)
check("쿠팡 F: 인식 불가 시 빈 결과", coupang.parse_items("<html>차단 안내 페이지</html>") == [], "")

# G. 순위 계산 연결: 광고 제외하고 ID로 찾기
page = "<ul>" + "".join(
    f'<li class="search-product{" search-product__ad-badge" if i % 5 == 0 else ""}" '
    f'data-product-id="{i}" data-vendor-item-id="{1000+i}"><div class="name">상품{i}</div></li>'
    for i in range(1, 31)) + "</ul>"
coupang.fetch_page = lambda s, k, p, log=None: page if p == 1 else "<ul></ul>"
coupang.time.sleep = lambda s: None
prod = {"ext_ids": json.dumps({"vendorItemId": "1012"}), "product_link": None, "product_name": "상품12"}
rank, method, _ = coupang.check_rank("kw", prod, 100)
# 1~12 중 광고는 5,10,15... → 5,10 두 개 제외 → 12번은 유기 10위
check("쿠팡 G: 광고 제외 순위 계산", rank == 10 and method == "id", f"{rank}, {method}")

# ══ 네이버 실측 ══
def page(products):
    return f'<html><script id="__NEXT_DATA__">{json.dumps({"props":{"list":products}})}</script></html>'

# H. 현재 키 이름
items = naver_web.parse_items(page([{"id": "N1", "productTitle": "상품1"},
                                    {"id": "AD", "productTitle": "광고", "adId": "nad-1"}]))
check("네이버 H: 현재 키 구조", len(items) == 2 and items[0]["nvmid"] == "N1" and items[1]["is_ad"], str(items))

# I. 키 이름 변경 (nvMid / title / adcrUrl)
items = naver_web.parse_items(page([{"nvMid": 500, "title": "새키상품", "adcrUrl": "http://ad"},
                                    {"mallProductId": 501, "productName": "새키상품2"}]))
check("네이버 I: 키 이름 바뀌어도 인식", len(items) == 2 and items[0]["nvmid"] == "500"
      and items[0]["is_ad"] and items[1]["nvmid"] == "501", str(items))

# J. __NEXT_DATA__ 없음 → 다른 script JSON 대체 경로
alt = ('<html><script>var x=1</script>'
       '<script>window.__PRELOADED__ = {"shoppingResult":{"products":['
       + json.dumps({"nvMid": "900", "productTitle": "대체경로상품"}) + ']}};</script></html>')
items = naver_web.parse_items(alt)
check("네이버 J: __NEXT_DATA__ 없어도 대체 경로", items and items[0]["nvmid"] == "900", str(items))

# K. 인식 불가 → None (호출부가 덤프 + 예외)
check("네이버 K: 인식 불가 시 None", naver_web.parse_items("<html>차단</html>") is None, "")

# L. 실측 순위: 광고 제외 카운트
prods = [{"id": f"P{i}", "productTitle": f"p{i}", **({"adId": "a"} if i % 4 == 0 else {})} for i in range(1, 21)]
real = naver_web.check_real_rank("kw", "P7", 100, fetch=lambda u: page(prods))
# 1~7 중 광고는 4 → 하나 제외 → 7번은 유기 6위
check("네이버 L: 광고 제외 실측 순위", real == 6, f"{real}위")

fail = 0
for name, ok, detail in results:
    print(("PASS" if ok else "FAIL"), "|", name, "|", detail)
    fail += 0 if ok else 1
sys.exit(1 if fail else 0)
