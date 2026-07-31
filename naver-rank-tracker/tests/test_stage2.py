"""② 쿠팡 Playwright 예비 경로 검증 — 403 차단 재현 + 실제 Chromium 폴백 E2E."""
import os, sys, threading, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

if os.path.exists("/opt/pw-browsers/chromium"):
    os.environ["RANKTRACKER_CHROMIUM"] = "/opt/pw-browsers/chromium"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
import db
db.DB_PATH = os.path.join(tempfile.mkdtemp(), "s2.db")
db.init_db()

import browser
import coupang

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))

# ── 쿠팡 픽스처 (멀티채널 테스트와 동일 구조) ──
def li(pid, iid, vid, title, ad=False):
    cls = "search-product search-product__ad-badge" if ad else "search-product"
    return (f'<li class="{cls}" data-product-id="{pid}" data-item-id="{iid}" data-vendor-item-id="{vid}">'
            f'<div class="name">{title}</div></li>')

def build_page(page, target_organic, target, organic_before):
    out, organic = [], organic_before
    for slot in range(72):
        if slot % 12 == 0:
            out.append(li(900000+slot, 1, 1, f"광고 {page}-{slot}", ad=True))
            continue
        organic += 1
        if target_organic and organic == target_organic:
            out.append(li(*target))
        else:
            out.append(li(100000+organic, 2000+organic, 3000+organic, f"일반 {organic}"))
    return "<html><body><ul>" + "".join(out) + "</ul></body></html>", organic

PAGES = {}
organic = 0
for p in (1, 2, 3):
    PAGES[p], organic = build_page(p, 86, ("76543", "222", "333", "내상품"), organic)

requests_hits, browser_hits = [], []

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        page = int(q.get("page", ["1"])[0])
        # 실브라우저는 sec-ch-ua 클라이언트 힌트를 보내고 requests는 못 보냄 — 이걸로 차단 재현
        if "sec-ch-ua" not in {k.lower() for k in self.headers.keys()}:
            requests_hits.append(page)
            self.send_response(403); self.end_headers(); self.wfile.write(b"blocked")
            return
        browser_hits.append(page)
        body = PAGES.get(page, "<html><body><ul></ul></body></html>").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass

srv = HTTPServer(("127.0.0.1", 0), Handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

coupang.SEARCH_URL = f"http://127.0.0.1:{port}/np/search"
coupang.time.sleep = lambda s: None

import json
product = {"ext_ids": json.dumps({"productId": "76543", "itemId": "222", "vendorItemId": "333"}),
           "product_link": None, "product_name": "내상품"}

# 1. 403 → 실브라우저 폴백 → ID 정밀 매칭 86위
logs = []
rank, method, found = coupang.check_rank("키워드", product, 200, log=logs.append)
check("403 차단 → 실브라우저 폴백 성공: 86위 (id)", rank == 86 and method == "id", f"{rank}, {method}")
check("requests가 403을 받고 브라우저가 처리", len(requests_hits) >= 1 and len(browser_hits) >= 2,
      f"requests {len(requests_hits)}회 차단, 브라우저 {len(browser_hits)}페이지 처리")
check("전환 로그 출력", any("실브라우저 경로로 전환" in l for l in logs), str(logs))

# 2. playwright 없다고 가정하면 안내 메시지와 함께 실패
avail = browser.available
browser.available = lambda: False
try:
    coupang.check_rank("키워드", product, 200)
    check("미설치 시 안내 예외", False, "예외 없음")
except RuntimeError as e:
    check("미설치 시 안내 예외 (설치법 포함)", "playwright" in str(e), str(e)[:60])
browser.available = avail

browser.shutdown()
srv.shutdown()

fail = 0
for name, ok, detail in results:
    print(("PASS" if ok else "FAIL"), "|", name, "|", detail)
    fail += 0 if ok else 1
sys.exit(1 if fail else 0)
