"""완료 판정(§10) 4항목 검증 — call_api 모킹."""
import sys, os, tempfile, unittest.mock as mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db
db.DB_PATH = os.path.join(tempfile.mkdtemp(), "test.db")
db.init_db()

import tracker

# 가짜 검색 결과: 500개 아이템, 137위에 내 상품
def fake_items(keyword, start, display):
    items = []
    for i in range(display):
        rank = start + i
        if rank == 137:
            items.append({"title": "<b>테스트</b> 상품 A", "productId": "NV137", "mallName": "내몰"})
        else:
            items.append({"title": f"다른상품 {rank}", "productId": f"X{rank}", "mallName": "타몰"})
    return items

call_count = [0]
def mock_call_api(keyword, start=1, display=100):
    call_count[0] += 1
    return fake_items(keyword, start, display)

tracker.call_api = mock_call_api
tracker.time.sleep = lambda s: None

pid = db.add_product("테스트 상품 A", mall_name="내몰", track_limit=400, keywords=["테스트키워드"])
kw = db.get_keywords(pid)[0]

results = []

# ── 판정 4: track_limit=400 → 정확히 4회 호출 ──
product = db.get_active_products()[0]
rank, method, found = tracker.check_rank("테스트키워드", product, 400)
results.append(("판정4(개정): 이름매칭 조기중단 → 2회 호출", call_count[0] == 2, f"호출 {call_count[0]}회"))
results.append(("1회차: rank=137, method=name", rank == 137 and method == "name", f"{rank}, {method}"))

# ── 판정 2: 1회차 후 nvmid 자동 채움 → 2회차 method='nvmid' ──
db.save_result(kw["id"], rank, method)
if found:
    db.promote_nvmid(pid, found[1], found[2])
product = db.get_active_products()[0]
results.append(("판정2a: nvmid 자동 승격", product["nvmid"] == "NV137", f"nvmid={product['nvmid']}"))
rank2, method2, _ = tracker.check_rank("테스트키워드", product, 400)
results.append(("판정2b: 2회차 method=nvmid", rank2 == 137 and method2 == "nvmid", f"{rank2}, {method2}"))

# ── 판정 1: 같은 날 2회 조회 → 1행만, 최신값 갱신 ──
db.save_result(kw["id"], rank2, method2)
hist = db.get_history(kw["id"])
results.append(("판정1: 같은 날 1행 + 최신값", len(hist) == 1 and hist[0]["match_method"] == "nvmid",
                f"{len(hist)}행, method={hist[0]['match_method']}"))

# ── 판정 3: API 오류 시 앱 안 죽고 다음 키워드 진행 ──
db.add_product("에러상품", keywords=["에러키워드", "정상키워드"])
def flaky_call_api(keyword, start=1, display=100):
    if keyword == "에러키워드":
        raise ConnectionError("네트워크 끊김")
    return fake_items(keyword, start, display)
tracker.call_api = flaky_call_api
logs = []
tracker.run_all_checks(log=logs.append)
ok3 = any("조회 실패 [에러키워드]" in l for l in logs) and any("조회 완료" in l for l in logs)
results.append(("판정3: 에러 스킵 후 계속 진행", ok3, "; ".join(logs[-3:])))

# ── 추가: QuotaExceeded → 중단 ──
from naver_api import QuotaExceeded
def quota_call_api(*a, **k):
    raise QuotaExceeded()
tracker.call_api = quota_call_api
logs2 = []
tracker.run_all_checks(log=logs2.append)
results.append(("한도 도달 → 즉시 중단", any("일일 한도 도달" in l for l in logs2), logs2[-1]))

# ── normalize ──
results.append(("normalize <b>태그 제거", tracker.normalize("<b>테스트</b>  상품&amp;A") == "테스트 상품&a", tracker.normalize("<b>테스트</b>  상품&amp;A")))

fail = 0
for name, ok, detail in results:
    print(("PASS" if ok else "FAIL"), "|", name, "|", detail)
    fail += 0 if ok else 1
sys.exit(1 if fail else 0)
