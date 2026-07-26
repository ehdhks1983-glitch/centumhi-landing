"""네이버쇼핑 실제 검색 페이지 실측 (하이브리드 검증).

네이버 OpenAPI 순위는 실제 화면 노출 순위와 오차가 있다(조사서 §4.1).
설정에서 실측 검증을 켜면, API 조회 후 실제 검색 페이지를 실브라우저로 열어
페이지에 내장된 __NEXT_DATA__ JSON에서 상품 목록을 꺼내 nvmid로 대조한다.
광고 상품은 제외하고 순수 노출 순위를 센다.
"""
import json
import os
import re
import urllib.parse

import browser

SEARCH_URL = "https://search.shopping.naver.com/search/all?query={q}&pagingIndex={p}&pagingSize=40"
PAGE_SIZE = 40
MAX_PAGES = 25

DEBUG_DUMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "naver_debug.html")

NEXT_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def parse_items(page_html):
    """__NEXT_DATA__ JSON에서 노출 순서대로 상품 목록 추출.
    반환: [{nvmid, title, is_ad}] | None(구조 파악 실패)"""
    m = NEXT_RE.search(page_html)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return None

    items = []

    def walk(node):
        if isinstance(node, dict):
            # 상품 노드: id + 상품명 필드를 함께 가진 dict
            if "id" in node and ("productTitle" in node or "productName" in node):
                items.append({
                    "nvmid": str(node["id"]),
                    "title": node.get("productTitle") or node.get("productName") or "",
                    "is_ad": bool(node.get("adId")),
                })
                return
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return items


def check_real_rank(keyword, nvmid, track_limit, fetch=None):
    """실제 노출 순위(광고 제외) 반환. 범위 내 미발견이면 None."""
    fetch = fetch or browser.fetch_html
    organic = 0
    pages = min(MAX_PAGES, (track_limit + PAGE_SIZE - 1) // PAGE_SIZE)

    for page in range(1, pages + 1):
        url = SEARCH_URL.format(q=urllib.parse.quote(keyword), p=page)
        page_html = fetch(url)
        items = parse_items(page_html)
        if not items:
            if page == 1:
                with open(DEBUG_DUMP, "w", encoding="utf-8") as f:
                    f.write(page_html)
                raise RuntimeError(f"네이버 실측 파싱 실패 — 페이지 구조 변경 가능성. {DEBUG_DUMP} 확인")
            break

        for it in items:
            if it["is_ad"]:
                continue  # 광고 슬롯 제외
            organic += 1
            if organic > track_limit:
                return None
            if it["nvmid"] == str(nvmid):
                return organic

    return None
