"""쿠팡 검색 순위 수집.

쿠팡에는 공개 검색 API가 없어(파트너스 API는 노출 순위와 무관) 실제 검색 결과
페이지를 저강도(하루 1회, 페이지당 2.5초 간격)로 읽는다. 화면에 보이는 순위
그대로이며, 광고 상품은 제외하고 순수 검색 순위를 센다.

상품 링크에 productId/itemId/vendorItemId가 모두 들어 있으므로 링크만 등록하면
첫 조회부터 ID 정밀 매칭이 된다. 링크가 없으면 이름 매칭 → ID 자동 확보(승격).
"""
import html
import json
import os
import re
import time
import urllib.parse

import requests

import browser

SEARCH_URL = "https://www.coupang.com/np/search"
PAGE_SIZE = 72          # listSize 최대값 — 호출 수 최소화
MAX_PAGES = 20
PAGE_INTERVAL = 2.5     # 저강도 수집 간격(초)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

DEBUG_DUMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coupang_debug.html")

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def normalize(text):
    text = TAG_RE.sub("", text or "")
    text = html.unescape(text)
    return WS_RE.sub(" ", text).strip().lower()


def parse_product_link(link):
    """쿠팡 상품 URL에서 productId / itemId / vendorItemId 추출.
    예: https://www.coupang.com/vp/products/123?itemId=456&vendorItemId=789"""
    if not link:
        return None
    m = re.search(r"/vp/products/(\d+)", link)
    if not m:
        return None
    ids = {"productId": m.group(1)}
    q = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
    for key in ("itemId", "vendorItemId"):
        if key in q and q[key][0].isdigit():
            ids[key] = q[key][0]
    return ids


# ---------- 검색 결과 파싱 ----------

LI_OPEN_RE = re.compile(r'<li[^>]*\bclass="([^"]*search-product[^"]*)"[^>]*>')
NAME_RE = re.compile(r'<div class="name">(.*?)</div>', re.S)


def _attr(tag, name):
    m = re.search(name + r'="(\d+)"', tag)
    return m.group(1) if m else None


def parse_items(page_html):
    """검색 결과 li 목록 → [{productId, itemId, vendorItemId, title, is_ad}]"""
    items = []
    for m in LI_OPEN_RE.finditer(page_html):
        tag, cls = m.group(0), m.group(1)
        end = page_html.find("</li>", m.end())
        block = page_html[m.end(): end if end != -1 else m.end() + 4000]
        name_m = NAME_RE.search(block)
        items.append({
            "productId": _attr(tag, "data-product-id"),
            "itemId": _attr(tag, "data-item-id"),
            "vendorItemId": _attr(tag, "data-vendor-item-id"),
            "title": name_m.group(1) if name_m else "",
            # 광고 판별: li 클래스 또는 블록 내 광고 뱃지 마크업
            "is_ad": ("search-product__ad-badge" in cls) or ("ad-badge" in block) or ("AdMark" in block),
        })
    return items


def _id_match(item, ids):
    # vendorItemId(판매자 단위) > itemId(옵션 단위) > productId(상품 단위) 순으로 엄격 매칭
    for key in ("vendorItemId", "itemId", "productId"):
        if ids.get(key) and item.get(key):
            return ids[key] == item[key]
    return False


class BlockedError(Exception):
    """쿠팡이 요청 방식 접속을 차단(403)"""


def _fetch_requests(session, keyword, page):
    r = session.get(
        SEARCH_URL,
        params={"q": keyword, "page": page, "listSize": PAGE_SIZE},
        headers=HEADERS, timeout=15,
    )
    if r.status_code == 403:
        raise BlockedError()
    r.raise_for_status()
    return r.text


def _fetch_browser(keyword, page):
    qs = urllib.parse.urlencode({"q": keyword, "page": page, "listSize": PAGE_SIZE})
    return browser.fetch_html(f"{SEARCH_URL}?{qs}")


def fetch_page(session, keyword, page, log=None):
    """기본은 requests. 403 차단이면 실브라우저(Playwright)로 자동 전환.
    한 번 차단되면 같은 조회에서는 이후 페이지도 바로 브라우저로 간다."""
    if not getattr(session, "_blocked", False):
        try:
            return _fetch_requests(session, keyword, page)
        except BlockedError:
            session._blocked = True
            if log:
                log("쿠팡 403 차단 감지 — 실브라우저 경로로 전환")
    if browser.available():
        return _fetch_browser(keyword, page)
    raise RuntimeError(
        "쿠팡이 자동 접속을 차단(403) — playwright를 설치하면 실브라우저로 우회 가능 "
        "(pip install playwright && playwright install chromium)"
    )


def check_rank(keyword, product, track_limit, log=None):
    """반환: (rank | None, match_method, found_ids | None)
    rank는 광고 제외 순위. found_ids는 이름 매칭 성공 시 승격 저장용 ID 묶음."""
    ids = json.loads(product["ext_ids"]) if product["ext_ids"] else None
    if not ids:
        ids = parse_product_link(product["product_link"])
    target = normalize(product["product_name"])

    name_hit = None
    organic = 0
    session = requests.Session()

    for page in range(1, MAX_PAGES + 1):
        page_html = fetch_page(session, keyword, page, log=log)
        items = parse_items(page_html)
        if not items:
            if page == 1:
                with open(DEBUG_DUMP, "w", encoding="utf-8") as f:
                    f.write(page_html)
                raise RuntimeError(f"쿠팡 검색 결과 파싱 실패 — 페이지 구조 변경 가능성. {DEBUG_DUMP} 확인")
            break  # 마지막 페이지 너머

        for it in items:
            if it["is_ad"]:
                continue  # 광고 슬롯은 순위에서 제외
            organic += 1
            if organic > track_limit:
                break
            if ids and _id_match(it, ids):
                return organic, "id", None
            if name_hit is None and it["title"] and normalize(it["title"]) == target:
                name_hit = (organic, {k: it[k] for k in ("productId", "itemId", "vendorItemId") if it[k]})

        if organic >= track_limit:
            break
        if name_hit and not ids:
            break  # ID가 없으면 더 찾을 대상이 없다
        time.sleep(PAGE_INTERVAL)

    if name_hit:
        return name_hit[0], "name", name_hit[1]
    return None, "not_found", None


if __name__ == "__main__":
    # 콘솔 확인: python coupang.py "검색키워드"
    import sys
    kw = sys.argv[1] if len(sys.argv) > 1 else input("검색 키워드: ")
    s = requests.Session()
    items = parse_items(fetch_page(s, kw, 1))
    print(f"1페이지 {len(items)}개 (광고 {sum(1 for i in items if i['is_ad'])}개)")
    for i, it in enumerate(items[:10], 1):
        print(i, "[광고]" if it["is_ad"] else "     ", normalize(it["title"])[:40], it["productId"])
