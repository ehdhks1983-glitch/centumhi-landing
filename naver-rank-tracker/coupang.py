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

# 항목 앵커: data-product-id는 쿠팡이 추적 용도로 오래 유지해온 가장 안정적인 표식.
# 클래스명(search-product 등)이 바뀌어도 이 속성 기준이면 계속 인식된다.
ITEM_ANCHOR_RE = re.compile(r'<(?:li|div|a)\b[^>]*\bdata-product-id="(\d+)"[^>]*>', re.I)
ATTR_RE = {
    "itemId": re.compile(r'data-item-id="(\d+)"', re.I),
    "vendorItemId": re.compile(r'data-vendor-item-id="(\d+)"', re.I),
}
# 상품명 후보 — 위에서부터 먼저 걸리는 것을 사용
NAME_PATTERNS = [
    re.compile(r'<div[^>]*class="[^"]*\bname\b[^"]*"[^>]*>(.*?)</div>', re.S | re.I),
    re.compile(r'<(?:div|span)[^>]*class="[^"]*product[-_]?name[^"]*"[^>]*>(.*?)</(?:div|span)>', re.S | re.I),
    re.compile(r'<img[^>]*\balt="([^"]{4,})"', re.I),
]
AD_MARKERS = ("ad-badge", "admark", "adbadge", "sdw-ad", 'data-is-ad="true"', "advertise")
WINDOW = 6000  # 한 항목 블록으로 볼 최대 길이


def _find_id(key, tag, block):
    """ID 속성은 앵커 태그에 있을 수도, 바로 안쪽 태그에 있을 수도 있다."""
    m = ATTR_RE[key].search(tag) or ATTR_RE[key].search(block[:600])
    return m.group(1) if m else None


def _find_title(block):
    for pat in NAME_PATTERNS:
        m = pat.search(block)
        if m and m.group(1).strip():
            return m.group(1)
    return ""


def _parse_by_markup(page_html):
    """1차 전략: data-product-id 앵커 기준 파싱"""
    anchors = [(m.start(), m.end(), m.group(0), m.group(1))
               for m in ITEM_ANCHOR_RE.finditer(page_html)]
    items, seen = [], set()

    for idx, (a_start, a_end, tag, pid) in enumerate(anchors):
        if pid in seen:      # 같은 상품의 중첩 태그(li 안의 a 등)는 한 번만
            continue
        seen.add(pid)
        # 블록 끝 = 다른 상품 앵커가 시작되는 지점 (없으면 WINDOW까지)
        stop = a_end + WINDOW
        for nxt_start, _, _, nxt_pid in anchors[idx + 1:]:
            if nxt_pid != pid:
                stop = min(stop, nxt_start)
                break
        block = page_html[a_end:stop]
        probe = (tag + block[:1500]).lower()
        items.append({
            "productId": pid,
            "itemId": _find_id("itemId", tag, block),
            "vendorItemId": _find_id("vendorItemId", tag, block),
            "title": _find_title(block),
            "is_ad": any(mk in probe for mk in AD_MARKERS),
        })
    return items

JSON_OBJ_RE = re.compile(r'\{[^{}]*"productId"\s*:\s*"?\d+"?[^{}]*\}')


def _parse_by_json(page_html):
    """2차 전략: 페이지에 내장된 JSON에서 상품 목록 추출 (마크업이 완전히 바뀐 경우 대비)"""
    items, seen = [], set()
    for m in JSON_OBJ_RE.finditer(page_html):
        chunk = m.group(0)
        try:
            obj = json.loads(chunk)
        except ValueError:
            continue
        pid = str(obj.get("productId") or "")
        if not pid.isdigit() or pid in seen:
            continue
        title = obj.get("productName") or obj.get("productTitle") or obj.get("name") or ""
        if not title:
            continue
        seen.add(pid)
        items.append({
            "productId": pid,
            "itemId": str(obj["itemId"]) if str(obj.get("itemId", "")).isdigit() else None,
            "vendorItemId": str(obj["vendorItemId"]) if str(obj.get("vendorItemId", "")).isdigit() else None,
            "title": title,
            "is_ad": bool(obj.get("isAd") or obj.get("adId") or obj.get("advertise")),
        })
    return items


def parse_items(page_html):
    """검색 결과 → [{productId, itemId, vendorItemId, title, is_ad}] (노출 순서 유지)"""
    items = _parse_by_markup(page_html)
    if not items:
        items = _parse_by_json(page_html)   # 마크업 구조 변경 시 대비 경로
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


def _diagnose(page_html):
    """덤프만 보고 헤매지 않도록, 페이지 성격을 한 줄로 알려준다."""
    low = page_html.lower()
    if len(page_html) < 3000:
        return "응답이 비정상적으로 짧음 (차단 안내 페이지 가능성)"
    if "captcha" in low or "보안문자" in page_html or "자동입력" in page_html:
        return "캡차/봇 차단 화면 — 시간을 두고 재시도하거나 playwright 설치 후 재시도"
    if "login" in low and "search-product" not in low:
        return "로그인 요구 화면"
    if "검색결과가 없" in page_html or "결과를 찾을 수 없" in page_html:
        return "해당 키워드의 검색 결과 자체가 없음"
    return "페이지 구조 변경 가능성 — 덤프 파일을 개발자에게 전달"


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
                raise RuntimeError(f"쿠팡 검색 결과 파싱 실패 — {_diagnose(page_html)} ({DEBUG_DUMP} 확인)")
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
