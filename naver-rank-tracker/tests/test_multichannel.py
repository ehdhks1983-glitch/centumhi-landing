"""네이버+쿠팡 멀티채널 통합 테스트 — 쿠팡 페이지는 실제 마크업 픽스처로 모킹."""
import json, os, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db
db.DB_PATH = os.path.join(tempfile.mkdtemp(), "mc.db")
db.init_db()

import coupang
import tracker

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))

# ── 0. 마이그레이션: 구버전 스키마에 컬럼 자동 추가 ──
import sqlite3
old_path = os.path.join(tempfile.mkdtemp(), "old.db")
c = sqlite3.connect(old_path)
c.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, product_name TEXT NOT NULL, mall_name TEXT, nvmid TEXT, product_link TEXT, track_limit INTEGER NOT NULL DEFAULT 100, is_active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT (datetime('now')))")
c.execute("INSERT INTO products(product_name) VALUES('구버전상품')")
c.commit(); c.close()
saved = db.DB_PATH
db.DB_PATH = old_path
db.init_db()
row = db.get_all_products()[0]
check("마이그레이션: channel/ext_ids 컬럼 추가", row["channel"] == "naver" and row["ext_ids"] is None, dict(row).get("channel"))
db.DB_PATH = saved

# ── 1. 링크 파싱 ──
ids = coupang.parse_product_link("https://www.coupang.com/vp/products/76543?itemId=222&vendorItemId=333&q=x")
check("쿠팡 링크 → ID 3종 추출", ids == {"productId": "76543", "itemId": "222", "vendorItemId": "333"}, str(ids))
check("비쿠팡 링크 → None", coupang.parse_product_link("https://smartstore.naver.com/x/1") is None, "")

# ── 쿠팡 픽스처: 페이지당 72개(광고 6개 포함=유기 66개) ──
def li(pid, iid, vid, title, ad=False):
    cls = "search-product search-product__ad-badge" if ad else "search-product"
    return (f'<li class="{cls}" data-product-id="{pid}" data-item-id="{iid}" data-vendor-item-id="{vid}">'
            f'<div class="name">{title}</div></li>')

def build_page(page, target_organic=None, target=None, total_organic_before=0):
    """유기 66개/광고 6개 페이지. target_organic 위치(전체 유기 순위)에 target 상품 삽입."""
    out = []
    organic = total_organic_before
    for slot in range(72):
        if slot % 12 == 0:  # 6개 광고
            out.append(li(900000+slot, 1, 1, f"광고상품 {page}-{slot}", ad=True))
            continue
        organic += 1
        if target_organic and organic == target_organic:
            out.append(li(*target))
        else:
            out.append(li(100000+organic, 2000+organic, 3000+organic, f"일반상품 {organic}"))
    return "<ul>" + "".join(out) + "</ul>", organic

fetch_count = [0]
def make_fetcher(target_organic, target):
    pages = {}
    organic = 0
    for p in (1, 2, 3):
        html_page, organic = build_page(p, target_organic, target, organic)
        pages[p] = html_page
    def fetch(session, keyword, page, log=None):
        fetch_count[0] += 1
        return pages.get(page, "<ul></ul>")
    return fetch

coupang.time.sleep = lambda s: None
tracker.time.sleep = lambda s: None

# ── 2. ID 정밀 매칭 (광고 제외 순위 86위 = 페이지2) ──
coupang.fetch_page = make_fetcher(86, ("76543", "222", "333", "내상품 <b>테스트</b>"))
pid_c = db.add_product("내상품 테스트", None, "https://www.coupang.com/vp/products/76543?itemId=222&vendorItemId=333",
                       200, ["쿠팡키워드"], channel="coupang", ext_ids=json.dumps(ids))
prod = dict([p for p in db.get_all_products() if p["id"] == pid_c][0])
rank, method, found = coupang.check_rank("쿠팡키워드", prod, 200)
check("쿠팡 ID 정밀 매칭: 광고 제외 86위", rank == 86 and method == "id", f"{rank}, {method}")

# ── 3. 링크 없이 등록 → 이름 매칭 + ID 자동 확보 → 2회차 ID 매칭 ──
coupang.fetch_page = make_fetcher(30, ("555", "666", "777", "링크없는 <b>상품</b>"))
pid2 = db.add_product("링크없는 상품", None, None, 200, ["키워드2"], channel="coupang")
prod2 = dict([p for p in db.get_all_products() if p["id"] == pid2][0])
rank2, method2, found2 = coupang.check_rank("키워드2", prod2, 200)
check("이름 매칭 30위 + ID 확보", rank2 == 30 and method2 == "name" and found2.get("vendorItemId") == "777", f"{rank2}, {method2}, {found2}")
db.promote_ext_ids(pid2, json.dumps(found2))
prod2 = dict([p for p in db.get_all_products() if p["id"] == pid2][0])
rank2b, method2b, _ = coupang.check_rank("키워드2", prod2, 200)
check("2회차: ID 정밀 매칭 전환", rank2b == 30 and method2b == "id", f"{rank2b}, {method2b}")

# ── 4. 미발견 + track_limit 준수 ──
coupang.fetch_page = make_fetcher(None, None)
fetch_count[0] = 0
prod3 = dict(prod2); prod3["ext_ids"] = json.dumps({"vendorItemId": "999999"}); prod3["product_name"] = "존재하지않는상품명"
rank3, method3, _ = coupang.check_rank("키워드3", prod3, 100)
check("미발견: not_found + 2페이지에서 중단(유기66+66>=100)", rank3 is None and method3 == "not_found" and fetch_count[0] == 2, f"{rank3}, {method3}, 페이지 {fetch_count[0]}")

# ── 5. run_all_checks 멀티채널 dispatch (네이버+쿠팡 혼합) ──
def naver_items(keyword, start, display):
    return [{"title": "<b>네이버상품</b>", "productId": "NV1", "mallName": "몰"} if start+i == 3
            else {"title": f"기타 {start+i}", "productId": f"X{start+i}", "mallName": "타"} for i in range(display)]
tracker.call_api = lambda k, s=1, d=100: naver_items(k, s, d)
coupang.fetch_page = make_fetcher(86, ("76543", "222", "333", "내상품 <b>테스트</b>"))
db.add_product("네이버상품", None, None, 100, ["네이버키워드"], channel="naver")
logs = []
tracker.run_all_checks(log=logs.append)
check("혼합 조회: 네이버 3위 + 쿠팡 86위 함께 처리",
      any("[네이버키워드] 3위" in l for l in logs) and any("[쿠팡키워드] 86위" in l for l in logs),
      " / ".join(l for l in logs if "위" in l)[:120])

# ── 6. 쿠팡만 있을 때 네이버 키 불필요 ──
import webapp
from fastapi.testclient import TestClient
db2 = os.path.join(tempfile.mkdtemp(), "mc2.db")
db.DB_PATH = db2; db.init_db()
client = TestClient(webapp.app)
r = client.post("/api/products", json={"name": "쿠팡전용", "mall": "", "link": "https://www.coupang.com/vp/products/76543?itemId=222&vendorItemId=333", "track_limit": 200, "channel": "coupang", "keywords": ["kw"]})
s = client.get("/api/state").json()
check("등록 즉시 matched=True (링크에서 ID 추출)", s["products"][0]["matched"] is True and s["products"][0]["channel"] == "coupang", "")
r = client.post("/api/check")
check("쿠팡만 있으면 네이버 키 없이 조회 시작", r.status_code == 200 and r.json()["started"], r.text[:80])
for _ in range(50):
    if not client.get("/api/state").json()["checking"]: break
    time.sleep(0.1)
s = client.get("/api/state").json()
check("웹 경유 쿠팡 조회: 86위 (id)", s["products"][0]["keywords"][0]["latest"]["rank"] == 86 and s["products"][0]["keywords"][0]["latest"]["method"] == "id", str(s["products"][0]["keywords"][0]["latest"]))

fail = 0
for name, ok, detail in results:
    print(("PASS" if ok else "FAIL"), "|", name, "|", detail)
    fail += 0 if ok else 1
sys.exit(1 if fail else 0)
