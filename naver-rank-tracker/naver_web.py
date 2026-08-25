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
SCRIPT_RE = re.compile(r'<script[^>]*>(.*?)</script>', re.S)

# 상품 노드의 ID/제목 키 후보 — 네이버가 키 이름을 바꿔도 하나만 맞으면 인식
ID_KEYS = ("id", "nvMid", "mallProductId", "productId")
TITLE_KEYS = ("productTitle", "productName", "title")
AD_KEYS = ("adId", "adcrUrl", "isAdProduct")


def _collect(data):
    """JSON 트리를 순회하며 노출 순서대로 상품 노드 추출"""
    items = []

    def walk(node):
        if isinstance(node, dict):
            id_key = next((k for k in ID_KEYS if node.get(k)), None)
            title_key = next((k for k in TITLE_KEYS if node.get(k)), None)
            if id_key and title_key:
                items.append({
                    "nvmid": str(node[id_key]),
                    "title": str(node[title_key]),
                    "is_ad": any(node.get(k) for k in AD_KEYS),
                })
                return  # 상품 노드 안쪽은 더 파고들지 않는다
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return items


def parse_items(page_html):
    """페이지에서 노출 순서대로 상품 목록 추출.
    1차: __NEXT_DATA__ / 2차: 다른 script 내 JSON. 둘 다 실패하면 None."""
    m = NEXT_RE.search(page_html)
    if m:
        try:
            items = _collect(json.loads(m.group(1)))
            if items:
                return items
        except ValueError:
            pass

    # 2차: __NEXT_DATA__가 없거나 구조가 바뀐 경우 — 다른 스크립트의 JSON 덩어리를 훑는다
    for sm in SCRIPT_RE.finditer(page_html):
        body = sm.group(1)
        brace = body.find("{")
        if brace == -1 or len(body) < 50:
            continue
        try:
            items = _collect(json.loads(body[brace:body.rindex("}") + 1]))
        except (ValueError, IndexError):
            continue
        if items:
            return items
    return None


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
