"""⑥ 링크 한 줄 등록 검증 — 페이지 파싱·키워드 추천·/api/inspect·등록 연결."""
import json, os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db
db.DB_PATH = os.path.join(tempfile.mkdtemp(), "s6.db")
db.init_db()

import extract

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))

# ── 채널·ID 판별 ──
check("쿠팡 링크 → coupang", extract.detect_channel("https://www.coupang.com/vp/products/1?itemId=2") == "coupang", "")
check("스마트스토어 → naver", extract.detect_channel("https://smartstore.naver.com/mystore/products/55") == "naver", "")
check("타사 링크 → None", extract.detect_channel("https://www.11st.co.kr/products/1") is None, "")

ids = extract.ids_from_url("https://www.coupang.com/vp/products/76543?itemId=222&vendorItemId=333", "coupang")
check("쿠팡 링크에서 ID 3종", ids["ext_ids"]["vendorItemId"] == "333", str(ids["ext_ids"]))

ids = extract.ids_from_url("https://search.shopping.naver.com/catalog/12345678", "naver")
check("네이버 카탈로그 링크 → nvmid 즉시 확보", ids["nvmid"] == "12345678", str(ids))

ids = extract.ids_from_url("https://smartstore.naver.com/centumhi/products/99", "naver")
check("스마트스토어 → 몰명 추출, nvmid는 나중에", ids["mall"] == "centumhi" and ids["nvmid"] is None, str(ids))

# ── 상품 페이지 파싱 ──
og = ('<html><head><meta property="og:title" content="센텀하이 알티지 오메가3 90캡슐">'
      '<meta property="og:site_name" content="센텀하이 공식스토어"></head></html>')
name, mall = extract.parse_product_page(og)
check("og:title/site_name 파싱", name == "센텀하이 알티지 오메가3 90캡슐" and mall == "센텀하이 공식스토어", f"{name} / {mall}")

ld = ('<html><script type="application/ld+json">'
      '{"@type":"Product","name":"닥터린 콜라겐 30포","brand":{"name":"닥터린"}}</script></html>')
name, mall = extract.parse_product_page(ld)
check("JSON-LD 대체 경로", name == "닥터린 콜라겐 30포" and mall == "닥터린", f"{name} / {mall}")

tt = "<html><head><title>곰곰 국내산 감자 1kg : 쿠팡</title></head></html>"
name, _ = extract.parse_product_page(tt)
check("title 태그 + 쇼핑몰 꼬리표 제거", name == "곰곰 국내산 감자 1kg", str(name))

check("파싱 불가 → None", extract.parse_product_page("<html>없음</html>")[0] is None, "")

# ── 키워드 추천 ──
def kws(title):
    return [k["keyword"] for k in extract.suggest_keywords(title)]

cases = [
    ("센텀하이 프리미엄 알티지 오메가3 rTG 1000mg 90캡슐 3개월분", ["오메가3", "알티지 오메가3"]),
    ("[무료배송] 삼성전자 갤럭시 버즈3 프로 블루투스 이어폰 정품", ["블루투스 이어폰"]),
    ("곰곰 국내산 햇 감자 1kg (1박스)", ["감자", "곰곰 감자"]),
    ("시디즈 T50 컴퓨터 의자 학생용 사무용 게이밍 체어", ["컴퓨터 의자", "게이밍 체어"]),
    ("임산부 엽산 영양제 800mcg 활성형 폴레이트 3개월분", ["임산부 엽산", "엽산 영양제"]),
]
for title, musts in cases:
    got = kws(title)
    miss = [m for m in musts if m not in got]
    check(f"키워드 추천: {title[:18]}…", not miss, f"누락 {miss}" if miss else f"{got[:4]}…")

all_kw = kws("센텀하이 프리미엄 알티지 오메가3 rTG 1000mg 90캡슐 3개월분")
check("규격·수량은 키워드에서 제외", not any(x in " ".join(all_kw) for x in ("1000mg", "90캡슐", "3개월분", "rTG")), str(all_kw))
check("홍보문구(무료배송·정품) 제외", not any(x in " ".join(kws("[무료배송] 삼성전자 갤럭시 버즈3 프로 블루투스 이어폰 정품")) for x in ("무료배송", "정품")), "")
check("추천 기본 선택은 5개 이하", sum(1 for k in extract.suggest_keywords(cases[0][0]) if k["recommended"]) <= 5, "")
check("빈 제목 → 빈 목록", extract.suggest_keywords("") == [], "")

# ── inspect_link 통합 (네트워크는 대체) ──
extract.fetch_product = lambda url, timeout=15: ("센텀하이 알티지 오메가3 90캡슐", "센텀하이", None)
r = extract.inspect_link("https://www.coupang.com/vp/products/7?itemId=8&vendorItemId=9")
check("inspect: 쿠팡 링크 전체 흐름", r["ok"] and r["channel"] == "coupang"
      and json.loads(r["ext_ids"])["vendorItemId"] == "9" and len(r["keywords"]) > 3, str(r)[:90])

r = extract.inspect_link("https://search.shopping.naver.com/catalog/555")
check("inspect: 네이버 카탈로그 → nvmid 포함", r["ok"] and r["nvmid"] == "555", str(r["nvmid"]))

r = extract.inspect_link("https://www.11st.co.kr/products/1")
check("inspect: 미지원 링크 안내", not r["ok"] and "쿠팡" in r["error"], r.get("error", ""))

extract.fetch_product = lambda url, timeout=15: (None, None, "페이지를 읽지 못했습니다 (Timeout)")
r = extract.inspect_link("https://www.coupang.com/vp/products/7?vendorItemId=9")
check("inspect: 페이지 실패해도 채널·ID는 반환", not r["ok"] and r["channel"] == "coupang"
      and json.loads(r["ext_ids"])["vendorItemId"] == "9", str(r["error"]))

# ── 웹 API + 실제 등록까지 ──
import webapp
from fastapi.testclient import TestClient
client = TestClient(webapp.app)

extract.fetch_product = lambda url, timeout=15: ("센텀하이 알티지 오메가3 90캡슐", "센텀하이", None)
r = client.post("/api/inspect", json={"link": "https://search.shopping.naver.com/catalog/9911"})
data = r.json()
check("POST /api/inspect", r.status_code == 200 and data["ok"] and data["nvmid"] == "9911", str(data)[:70])

picked = [k["keyword"] for k in data["keywords"] if k["recommended"]]
r = client.post("/api/products", json={
    "name": data["name"], "mall": data["mall"], "link": "https://search.shopping.naver.com/catalog/9911",
    "track_limit": 400, "channel": "naver", "nvmid": data["nvmid"], "keywords": picked})
check("추천 키워드로 바로 등록", r.status_code == 200, r.text[:60])

s = client.get("/api/state").json()
p = s["products"][0]
check("등록 즉시 nvmid 확보(matched)", p["matched"] and p["nvmid"] == "9911", str(p["nvmid"]))
check("선택한 키워드가 그대로 등록됨", len(p["keywords"]) == len(picked), f"{len(p['keywords'])} vs {len(picked)}")

fail = 0
for name, ok, detail in results:
    print(("PASS" if ok else "FAIL"), "|", name, "|", detail)
    fail += 0 if ok else 1
sys.exit(1 if fail else 0)
