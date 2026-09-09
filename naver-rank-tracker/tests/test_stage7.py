"""⑦ 완성도 감사 수정분 검증 — 실사용을 막던 결함들이 실제로 고쳐졌는지."""
import json, os, sys, tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["RANKTRACKER_NO_BROWSER"] = "1"
import db
db.DB_PATH = os.path.join(tempfile.mkdtemp(), "s7.db")
db.init_db()

import coupang, extract, naver_api, tracker
tracker.time.sleep = lambda s: None
coupang.time.sleep = lambda s: None

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))

# ═══ 1. 스마트스토어 몰명 슬러그가 매칭을 막던 문제 ═══
ids = extract.ids_from_url("https://smartstore.naver.com/centumhi/products/99", "naver")
check("스마트스토어 슬러그를 몰명으로 쓰지 않음", ids["mall"] is None, str(ids))

extract.fetch_product = lambda url, timeout=15: ("센텀하이 오메가3", None, None)
r = extract.inspect_link("https://smartstore.naver.com/centumhi/products/99")
check("링크 분석 결과에도 슬러그 몰명 없음", r["mall"] == "", repr(r["mall"]))

# 몰명이 대소문자/공백만 다른 경우 매칭 성립 (정규화 비교)
def items_for(mall):
    return lambda k, s=1, d=100: [
        {"title": "<b>센텀하이 오메가3</b>", "productId": "NV1", "mallName": mall} if s + i == 3
        else {"title": f"기타 {s+i}", "productId": f"X{s+i}", "mallName": "타몰"}
        for i in range(d)]

tracker.call_api = items_for("센텀하이 ")
prod = {"product_name": "센텀하이 오메가3", "nvmid": None, "mall_name": "센텀하이"}
rank, method, found = tracker.check_rank("kw", prod, 100)
check("몰명 공백 차이는 정규화로 흡수", rank == 3 and method == "name", f"{rank}, {method}")

# 몰명이 진짜 다르면 기각하되, 이유를 로그로 알린다
tracker.call_api = items_for("남의스토어")
logs = []
rank, method, _ = tracker.check_rank("kw", prod, 100, log=logs.append)
check("몰명 불일치 시 기각 사유를 로그로 알림",
      rank is None and any("몰명이 달라 제외" in l and "남의스토어" in l for l in logs),
      (logs[0][:80] if logs else "로그 없음"))

# ═══ 2. 쿠팡: 광고+오가닉 동시 노출 ═══
def li(pid, ad=False, title=None):
    cls = "search-product search-product__ad-badge" if ad else "search-product"
    return (f'<li class="{cls}" data-product-id="{pid}" data-vendor-item-id="{9000+int(pid)}">'
            f'<a data-product-id="{pid}"><div class="name">{title or f"상품{pid}"}</div></a></li>')

page = ("<ul>" + li("100", ad=True) + "".join(li(str(i)) for i in range(11, 15))
        + li("100") + "".join(li(str(i)) for i in range(15, 18)) + "</ul>")
items = coupang.parse_items(page)
organic = [i for i in items if not i["is_ad"]]
pos = next((n for n, i in enumerate(organic, 1) if i["productId"] == "100"), None)
check("광고 돌리는 셀러 상품도 유기 순위로 잡힘", pos == 5, f"{pos}위 (기대 5)")
check("중첩 태그(li 안의 a)는 중복 계상 안 됨", len(items) == 9, f"{len(items)}개 (li 9개 × 중첩 a = 18이 아님)")

# ═══ 3. 쿠팡: 옵션이 다른 링크로도 매칭 ═══
item = {"productId": "555", "itemId": "111", "vendorItemId": "222"}
check("vendorItemId가 달라도 productId로 매칭",
      coupang._id_match(item, {"productId": "555", "vendorItemId": "999"}), "")
check("아무 ID도 안 맞으면 불일치",
      not coupang._id_match(item, {"productId": "777", "vendorItemId": "999"}), "")

# ═══ 4. 네이버 API 오류 한국어 안내 ═══
class R:
    def __init__(s, code, body=None): s.status_code, s._b = code, body or {}
    def json(s): return s._b
e401 = naver_api._explain(R(401))
check("401 → '검색' API 체크 안내 포함", "검색" in str(e401) and "인증 실패" in str(e401), str(e401)[:50])
check("429 → 한도 예외로 분류", isinstance(naver_api._explain(R(429)), naver_api.QuotaExceeded), "")
check("errorCode 012 → 한도 예외", isinstance(naver_api._explain(R(200, {"errorCode": "012"})), naver_api.QuotaExceeded), "")

# ═══ 5. 조회 실패가 이력에 남고, 인증 오류는 즉시 중단 ═══
db.set_setting("client_id", "x"); db.set_setting("client_secret", "y")
pid = db.add_product("실패상품", None, None, 100, ["kwA", "kwB"], channel="naver")
kws = db.get_keywords(pid)

def boom(k, s=1, d=100): raise ConnectionError("네트워크 끊김")
tracker.call_api = boom
logs = []
tracker.run_all_checks(log=logs.append)
h = db.get_history(kws[0]["id"])
check("조회 실패가 이력에 'error'로 남음", h and h[0]["match_method"] == "error" and h[0]["rank"] is None, str(dict(h[0])) if h else "없음")
check("마지막 조회 시각 기록됨", bool(db.get_setting("last_run_at")), db.get_setting("last_run_at", ""))
check("실패 건수 기록됨", db.get_setting("last_run_failed") == "2", db.get_setting("last_run_failed", ""))

def auth_fail(k, s=1, d=100): raise RuntimeError("네이버 API 인증 실패 — 확인하세요")
tracker.call_api = auth_fail
logs = []
tracker.run_all_checks(log=logs.append)
auth_logs = [l for l in logs if "인증 실패" in l]
check("인증 오류는 키워드마다 반복하지 않고 즉시 중단", len(auth_logs) == 1, f"{len(auth_logs)}회 (기대 1)")

# ═══ 6. 키워드 추가·삭제 (이력 보존) ═══
db.save_result(kws[0]["id"], 5, "nvmid", "2026-09-01")
db.add_keyword(pid, "새키워드")
check("키워드 추가", len(db.get_keywords(pid)) == 3, str(len(db.get_keywords(pid))))
db.add_keyword(pid, "새키워드")
check("중복 키워드는 무시", len(db.get_keywords(pid)) == 3, str(len(db.get_keywords(pid))))
db.delete_keyword(db.get_keywords(pid)[-1]["id"])
check("키워드 삭제 후 기존 이력 보존", len(db.get_keywords(pid)) == 2 and len(db.get_history(kws[0]["id"])) > 0, "")

# ═══ 7. 상품 수정 + 매칭 초기화 (이력 유지) ═══
db.promote_nvmid(pid, "WRONG123")
before = len(db.get_history(kws[0]["id"]))
db.update_product(pid, name="고친 상품명", mall="새몰", track_limit=400, reset_match=True)
p = [x for x in db.get_all_products() if x["id"] == pid][0]
after = len(db.get_history(kws[0]["id"]))
check("상품 수정 + 잘못 잡힌 매칭 되돌리기",
      p["product_name"] == "고친 상품명" and p["nvmid"] is None and p["track_limit"] == 400 and after == before,
      f"nvmid={p['nvmid']}, 이력 {before}→{after}")

# ═══ 8. 웹 API 연결 ═══
import webapp
from fastapi.testclient import TestClient
client = TestClient(webapp.app)
s = client.get("/api/state").json()
check("상태에 마지막 조회/오늘 날짜 포함",
      "last_run_at" in s and "today" in s and "last_run_failed" in s, "")
r = client.post(f"/api/products/{pid}/keywords", json={"keyword": "웹추가"})
check("POST 키워드 추가", r.status_code == 200 and len(db.get_keywords(pid)) == 3, r.text[:40])
r = client.patch(f"/api/products/{pid}", json={"track_limit": 200, "reset_match": True})
check("PATCH 상품 수정", r.status_code == 200, r.text[:40])
kid = db.get_keywords(pid)[-1]["id"]
r = client.delete(f"/api/keywords/{kid}")
check("DELETE 키워드", r.status_code == 200 and len(db.get_keywords(pid)) == 2, r.text[:40])

# ═══ 9. 포트/중복 실행 처리 ═══
import main as mainmod
check("포트 점검 함수 존재", callable(mainmod._port_in_use) and callable(mainmod._find_port), "")
check("빈 포트는 그대로 사용", mainmod._find_port("127.0.0.1", 58999) == 58999, "")

fail = 0
for name, ok, detail in results:
    print(("PASS" if ok else "FAIL"), "|", name, "|", detail)
    fail += 0 if ok else 1
sys.exit(1 if fail else 0)
