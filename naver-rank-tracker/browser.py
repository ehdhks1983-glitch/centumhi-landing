"""Playwright 실브라우저 헬퍼 (선택 의존성).

- 네이버 실측 검증(naver_web.py)과 쿠팡 403 차단 시 예비 경로(coupang.py)에서 사용
- playwright 미설치 환경에서는 available()가 False — 해당 기능만 조용히 꺼진다
- 설치: pip install playwright && playwright install chromium
"""
import os
import threading

_lock = threading.Lock()
_pw = None
_browser = None

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def available():
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except ImportError:
        return False


def fetch_html(url, wait_ms=2500):
    """헤드리스 브라우저로 페이지를 열어 렌더링된 HTML을 반환. 브라우저는 재사용."""
    from playwright.sync_api import sync_playwright
    global _pw, _browser
    with _lock:
        if _browser is None:
            _pw = sync_playwright().start()
            exe = os.environ.get("RANKTRACKER_CHROMIUM")  # 크로미움 경로 수동 지정용
            _browser = _pw.chromium.launch(headless=True, executable_path=exe or None)
        page = _browser.new_page(user_agent=UA, locale="ko-KR",
                                 viewport={"width": 1280, "height": 900})
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(wait_ms)  # 스크립트 렌더링 여유
            return page.content()
        finally:
            page.close()


def shutdown():
    global _pw, _browser
    with _lock:
        if _browser:
            _browser.close()
            _browser = None
        if _pw:
            _pw.stop()
            _pw = None
