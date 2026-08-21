"""실환경 자가진단 — PC에서 처음 실행할 때 무엇이 되고 안 되는지 한 번에 확인.

    python doctor.py              # 기본 진단 (네이버 API 1회 호출 포함)
    python doctor.py --telegram   # 텔레그램 테스트 메시지 전송까지

문제가 있으면 이 출력 전체를 복사해서 개발자(Claude)에게 보내면 바로 진단 가능.
"""
import sys

PASS, FAIL, SKIP = "✅", "❌", "➖"
results = []


def report(mark, name, msg=""):
    results.append((mark, name, msg))
    print(f"{mark} {name}" + (f" — {msg}" if msg else ""))


def check_python():
    v = sys.version_info
    if v >= (3, 10):
        report(PASS, "파이썬 버전", f"{v.major}.{v.minor}.{v.micro}")
    else:
        report(FAIL, "파이썬 버전", f"{v.major}.{v.minor} — 3.10 이상 필요. python.org에서 재설치")


def check_deps():
    missing = []
    for mod in ("fastapi", "uvicorn", "apscheduler", "requests"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        report(FAIL, "필수 패키지", f"{', '.join(missing)} 미설치 → pip install -r requirements.txt")
    else:
        report(PASS, "필수 패키지", "fastapi/uvicorn/apscheduler/requests")
    return not missing


def check_db():
    try:
        import db
        db.init_db()
        db.set_setting("_doctor", "ok")
        ok = db.get_setting("_doctor") == "ok"
        report(PASS if ok else FAIL, "데이터베이스", db.DB_PATH)
        return ok
    except Exception as e:
        report(FAIL, "데이터베이스", str(e))
        return False


def check_naver():
    import db
    import requests as rq
    if not (db.get_setting("client_id") and db.get_setting("client_secret")):
        report(SKIP, "네이버 API", "키 미설정 — developers.naver.com에서 발급 후 웹 화면 상단에 저장 "
                                   "(쿠팡만 쓸 거면 없어도 됨)")
        return
    try:
        from naver_api import call_api
        items = call_api("노트북", start=1, display=1)
        if items and "productId" in items[0]:
            report(PASS, "네이버 API", f"실호출 성공 — productId 필드 확인됨 (예: {items[0]['productId']})")
        else:
            report(FAIL, "네이버 API", "응답에 productId 없음 — 출력 전체를 개발자에게 전달")
    except rq.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        hint = "Client ID/Secret이 틀렸거나 검색 API 미신청" if code in (401, 403) else "출력 전체를 개발자에게 전달"
        report(FAIL, "네이버 API", f"HTTP {code} — {hint}")
    except Exception as e:
        report(FAIL, "네이버 API", f"접속 실패 ({type(e).__name__}: {e}) — 인터넷 연결/방화벽 확인")


def check_coupang():
    try:
        import coupang
        import requests as rq
        session = rq.Session()
        try:
            page_html = coupang._fetch_requests(session, "노트북", 1)
            via = "일반 접속"
        except coupang.BlockedError:
            import browser
            if not browser.available():
                report(FAIL, "쿠팡 접속", "403 차단 + playwright 미설치 → "
                                          "pip install playwright && playwright install chromium 후 재진단")
                return
            page_html = coupang._fetch_browser("노트북", 1)
            via = "실브라우저 우회"
        items = coupang.parse_items(page_html)
        if items:
            ads = sum(1 for i in items if i["is_ad"])
            report(PASS, "쿠팡 접속·파싱", f"{via} — 1페이지 {len(items)}개 (광고 {ads}개) 파싱 성공")
        else:
            with open(coupang.DEBUG_DUMP, "w", encoding="utf-8") as f:
                f.write(page_html)
            report(FAIL, "쿠팡 파싱", f"항목 0개 — 페이지 구조 변경 추정. {coupang.DEBUG_DUMP} 파일을 개발자에게 전달")
    except Exception as e:
        import requests as rq
        if isinstance(e, rq.exceptions.RequestException):
            report(FAIL, "쿠팡 접속", f"네트워크 연결 실패 ({type(e).__name__}) — 인터넷/방화벽/프록시 확인")
        else:
            report(FAIL, "쿠팡 접속", f"{type(e).__name__}: {e} — 반복되면 출력을 개발자에게 전달")


def check_playwright():
    import browser
    if not browser.available():
        report(SKIP, "선택기능(실측·쿠팡 우회)", "playwright 미설치 — 필요하면 "
                                                "pip install playwright && playwright install chromium")
        return
    try:
        html = browser.fetch_html("about:blank", wait_ms=100)
        browser.shutdown()
        report(PASS, "선택기능(실측·쿠팡 우회)", "playwright + 크로미움 정상 구동")
    except Exception as e:
        report(FAIL, "선택기능(실측·쿠팡 우회)", f"크로미움 실행 실패 — playwright install chromium 재실행 ({e})")


def check_telegram(send_test):
    import db
    import alerts
    if not alerts.configured():
        report(SKIP, "텔레그램 알림", "미설정 — 쓰려면 웹 화면에서 Token/Chat ID 저장")
        return
    if not send_test:
        report(PASS, "텔레그램 알림", "설정됨 (전송 테스트: python doctor.py --telegram)")
        return
    try:
        alerts.send("✅ 순위추적기 진단 — 텔레그램 연결 정상")
        report(PASS, "텔레그램 알림", "테스트 메시지 전송 성공 — 휴대폰 확인")
    except Exception as e:
        report(FAIL, "텔레그램 알림", f"전송 실패 — Token/Chat ID 재확인 ({e})")


def main():
    print("=" * 56)
    print(" 상품 순위추적기 실환경 자가진단")
    print("=" * 56)
    check_python()
    if not check_deps():
        print("\n필수 패키지부터 설치 후 다시 실행하세요: pip install -r requirements.txt")
        sys.exit(1)
    if not check_db():
        sys.exit(1)
    check_naver()
    check_coupang()
    check_playwright()
    check_telegram("--telegram" in sys.argv)

    print("-" * 56)
    fails = [r for r in results if r[0] == FAIL]
    if not fails:
        print("진단 완료 — 실행 준비 끝. python main.py 로 시작하세요.")
    else:
        print(f"해결할 항목 {len(fails)}개 — 각 줄의 안내를 따르거나, 위 출력 전체를 개발자에게 보내세요.")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
