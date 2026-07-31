"""점검 수정 후 전체 재검증 — FastAPI TestClient + call_api 모킹."""
import os, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db
db.DB_PATH = os.path.join(tempfile.mkdtemp(), "web_test2.db")
db.init_db()

import tracker

def fake_items(keyword, start, display):
    items = []
    for i in range(display):
        rank = start + i
        if rank == 137:
            items.append({"title": "<b>테스트</b> 상품 A", "productId": "NV137", "mallName": "내몰"})
        else:
            items.append({"title": f"다른상품 {rank}", "productId": f"X{rank}", "mallName": "타몰"})
    return items

calls = [0]
def mock_call_api(keyword, start=1, display=100):
    calls[0] += 1
    db.increment_today_usage()
    return fake_items(keyword, start, display)

tracker.call_api = mock_call_api
tracker.time.sleep = lambda s: None

import webapp
from fastapi.testclient import TestClient
client = TestClient(webapp.app)

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))

def wait_done():
    for _ in range(100):
        if not client.get("/api/state").json()["checking"]: return
        time.sleep(0.1)

client.post("/api/settings", json={"client_id": "id", "client_secret": "sec", "check_hour": 3})

# ── 상품 A: 137위 존재, track 400 / 상품 B: 검색 결과에 없음, track 400 ──
client.post("/api/products", json={"name": "테스트 상품 A", "mall": "내몰", "link": "", "track_limit": 400, "keywords": ["키워드A"]})
client.post("/api/products", json={"name": "없는 상품 B", "mall": "", "link": "", "track_limit": 400, "keywords": ["키워드B"]})

# 1회차: A는 이름매칭 → 2페이지에서 조기중단(2회), B는 미발견 → 전 범위 4회
before = calls[0]
client.post("/api/check"); wait_done()
s = client.get("/api/state").json()
pA, pB = s["products"]
check("1회차 A: 137위 name 매칭", pA["keywords"][0]["latest"]["rank"] == 137 and pA["keywords"][0]["latest"]["method"] == "name", str(pA["keywords"][0]["latest"]))
check("A nvmid 자동 승격", pA["nvmid"] == "NV137", f"nvmid={pA['nvmid']}")
check("A 조기중단: 2회 + B 미발견: 4회 = 총 6회", calls[0] - before == 6, f"calls={calls[0]-before}")
check("B: 400위 내 미발견 (not_found)", pB["keywords"][0]["latest"]["method"] == "not_found" and pB["keywords"][0]["latest"]["rank"] is None, str(pB["keywords"][0]["latest"]))

# 2회차: A는 nvmid 매칭(137위 → 2페이지에서 즉시 반환 = 2회), 같은 날 이력 1행 유지
before = calls[0]
client.post("/api/check"); wait_done()
s = client.get("/api/state").json()
kA = s["products"][0]["keywords"][0]
hist = client.get(f"/api/history/{kA['id']}").json()
check("2회차 A: method=nvmid", kA["latest"]["method"] == "nvmid", str(kA["latest"]))
check("같은 날 이력 1행 유지", len(hist) == 1, f"{len(hist)}행")

# 동시 실행 차단: 잠금 보유 상태에서 run_all_checks 호출 → 건너뜀
logs = []
tracker.run_lock.acquire()
tracker.run_all_checks(log=logs.append)
tracker.run_lock.release()
check("동시 실행 차단 (잠금 시 건너뜀)", any("건너뜀" in l for l in logs), str(logs))

# 잠금 중에는 state.checking = True
tracker.run_lock.acquire()
checking = client.get("/api/state").json()["checking"]
tracker.run_lock.release()
check("스케줄러 실행 중에도 checking=True 표시", checking is True, "")

# 로그 상한: 3000줄 넣어도 2000줄 유지 + 커서 보정
for i in range(3000):
    webapp.add_log(f"bulk {i}")
r = client.get("/api/logs?since=0").json()
check("로그 상한 2000줄 유지", len(r["lines"]) <= 2000, f"{len(r['lines'])}줄")
r2 = client.get(f"/api/logs?since={r['next']}").json()
check("커서 보정 후 신규 로그만 반환", r2["lines"] == [], f"{len(r2['lines'])}줄")

# 커넥션 정리 확인: 500회 연속 DB 접근에도 예외 없음
try:
    for _ in range(500):
        db.get_today_usage()
    check("커넥션 개폐 500회 무오류", True, "")
except Exception as e:
    check("커넥션 개폐 500회 무오류", False, str(e))

fail = 0
for name, ok, detail in results:
    print(("PASS" if ok else "FAIL"), "|", name, "|", detail)
    fail += 0 if ok else 1
sys.exit(1 if fail else 0)
