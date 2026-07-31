"""① 네이버 실측 하이브리드 검증 — __NEXT_DATA__ 픽스처 파싱 + 이력 병기."""
import json, os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db
db.DB_PATH = os.path.join(tempfile.mkdtemp(), "s1.db")
db.init_db()

import naver_web
import tracker

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))

# ── __NEXT_DATA__ 픽스처: 40개 중 광고 4개, 내 상품(nvmid=NV777)을 유기 17위에 배치 ──
def build_page(page, target_organic=None, nvmid="NV777"):
    prods, organic = [], (page - 1) * 36  # 페이지당 유기 36개(광고 4 제외)
    for slot in range(40):
        if slot % 10 == 0:
            prods.append({"id": f"AD{page}{slot}", "productTitle": f"광고 {slot}", "adId": "nad-123"})
            continue
        organic += 1
        if target_organic and organic == target_organic:
            prods.append({"id": nvmid, "productTitle": "내 상품"})
        else:
            prods.append({"id": f"G{organic}", "productTitle": f"일반 {organic}"})
    data = {"props": {"pageProps": {"initialState": {"products": {"list": [{"item": p} for p in prods]}}}}}
    return f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script></html>'

# 1. 파싱: 광고 플래그 + 순서 보존
items = naver_web.parse_items(build_page(1, 17))
check("파싱: 40개 추출", len(items) == 40, f"{len(items)}개")
check("광고 4개 식별", sum(1 for i in items if i["is_ad"]) == 4, "")

# 2. 실측 순위: 광고 제외 17위 (2페이지엔 없음 → 1페이지에서 발견)
fetched = []
def fake_fetch(url):
    page = int(url.split("pagingIndex=")[1].split("&")[0])
    fetched.append(page)
    return build_page(page, 17)
real = naver_web.check_real_rank("키워드", "NV777", 100, fetch=fake_fetch)
check("실측: 광고 제외 17위", real == 17, f"{real}위")

# 3. 2페이지 배치(유기 50위) + track_limit 40이면 범위 밖 → None
fetched.clear()
real2 = naver_web.check_real_rank("키워드", "NV777", 40,
                                  fetch=lambda u: build_page(int(u.split("pagingIndex=")[1].split("&")[0]), 50))
check("범위 밖 → None (40위 한도)", real2 is None, f"{real2}")

# 4. 파싱 실패 → 디버그 덤프 + 예외
try:
    naver_web.check_real_rank("키워드", "NV777", 40, fetch=lambda u: "<html>구조변경</html>")
    check("파싱 실패 시 예외", False, "예외 없음")
except RuntimeError as e:
    check("파싱 실패 시 예외 + 덤프", os.path.exists(naver_web.DEBUG_DUMP), str(e)[:50])
os.remove(naver_web.DEBUG_DUMP)

# 5. DB: real_rank 마이그레이션 + 당일 이력 병기
pid = db.add_product("내 상품", None, None, 100, ["키워드"], channel="naver")
db.promote_nvmid(pid, "NV777")
kw = db.get_keywords(pid)[0]
db.save_result(kw["id"], 21, "nvmid")
db.save_real_rank(kw["id"], 17)
row = db.get_history(kw["id"])[0]
check("이력에 API 21위 + 실측 17위 병기", row["rank"] == 21 and row["real_rank"] == 17, f"{row['rank']}/{row['real_rank']}")

# 6. run_all_checks 통합: verify_real 켜면 실측 로그 + 저장
db.set_setting("verify_real", "1")
def naver_items(keyword, start, display):
    return [{"title": "<b>내 상품</b>", "productId": "NV777", "mallName": "몰"} if start+i == 21
            else {"title": f"기타 {start+i}", "productId": f"X{start+i}", "mallName": "타"} for i in range(display)]
tracker.call_api = lambda k, s=1, d=100: naver_items(k, s, d)
tracker.time.sleep = lambda s: None
tracker.browser.available = lambda: True
tracker.naver_web.check_real_rank = lambda k, n, t, fetch=None: 17
logs = []
tracker.run_all_checks(log=logs.append)
row = db.get_history(kw["id"])[0]
check("통합: 실측 로그(오차 -4) + 저장", any("실측 17위 (API 21위, 오차 -4)" in l for l in logs) and row["real_rank"] == 17,
      " / ".join(l for l in logs if "실측" in l))

# 7. playwright 미설치 시 조용히 건너뜀
tracker.browser.available = lambda: False
logs2 = []
tracker.run_all_checks(log=logs2.append)
check("미설치 시 안내 후 건너뜀 (조회는 정상)", any("playwright 미설치" in l for l in logs2) and any("조회 완료" in l for l in logs2), "")

fail = 0
for name, ok, detail in results:
    print(("PASS" if ok else "FAIL"), "|", name, "|", detail)
    fail += 0 if ok else 1
sys.exit(1 if fail else 0)
