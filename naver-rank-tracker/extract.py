"""링크 한 줄로 등록 — 상품 페이지에서 이름·몰명·ID를 뽑고, 제목에서 키워드 후보를 추천.

사용자가 타이핑할 일을 없애는 것이 목적. 실패해도 예외를 던지지 않고
'뽑아낸 만큼'을 돌려주며, 부족한 부분은 사용자가 화면에서 채우면 된다.
"""
import html as html_mod
import json
import re
import urllib.parse

import requests

import browser
import coupang

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# ─────────────────────────── 채널 판별 ───────────────────────────

def detect_channel(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    if "coupang.com" in host:
        return "coupang"
    if "naver.com" in host:
        return "naver"
    return None


NAVER_CATALOG_RE = re.compile(r"/catalog/(\d+)")
SMARTSTORE_RE = re.compile(r"(?:smartstore|brand)\.naver\.com/([^/]+)/products/(\d+)")


def ids_from_url(url, channel):
    """URL만으로 알 수 있는 식별자 (페이지를 못 열어도 확보 가능)"""
    if channel == "coupang":
        return {"ext_ids": coupang.parse_product_link(url), "nvmid": None, "mall": None}
    if channel == "naver":
        m = NAVER_CATALOG_RE.search(url)          # 쇼핑 카탈로그 링크 = nvmid 그 자체
        if m:
            return {"ext_ids": None, "nvmid": m.group(1), "mall": None}
        m = SMARTSTORE_RE.search(url)             # 스마트스토어 상품번호 ≠ nvmid → 첫 조회 때 자동 승격
        if m:
            return {"ext_ids": None, "nvmid": None, "mall": m.group(1)}
    return {"ext_ids": None, "nvmid": None, "mall": None}


# ─────────────────────────── 페이지에서 제목/몰명 ───────────────────────────

META_RE = re.compile(r"<meta\b[^>]*>", re.I)
ATTR_RE = re.compile(r'(\w[\w:-]*)\s*=\s*"([^"]*)"', re.I)
TITLE_TAG_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
JSONLD_RE = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)


def _metas(page_html):
    out = {}
    for tag in META_RE.findall(page_html):
        attrs = dict((k.lower(), v) for k, v in ATTR_RE.findall(tag))
        key = attrs.get("property") or attrs.get("name")
        if key and "content" in attrs:
            out[key.lower()] = html_mod.unescape(attrs["content"]).strip()
    return out


def _from_jsonld(page_html):
    for m in JSONLD_RE.finditer(page_html):
        try:
            data = json.loads(m.group(1).strip())
        except ValueError:
            continue
        for node in (data if isinstance(data, list) else [data]):
            if isinstance(node, dict) and node.get("name"):
                brand = node.get("brand")
                if isinstance(brand, dict):
                    brand = brand.get("name")
                return str(node["name"]), (str(brand) if brand else None)
    return None, None


def parse_product_page(page_html):
    """반환: (상품명 | None, 몰명 | None)"""
    metas = _metas(page_html)
    name = metas.get("og:title") or metas.get("twitter:title")
    mall = metas.get("og:site_name")

    if not name:
        name, brand = _from_jsonld(page_html)
        mall = mall or brand
    if not name:
        m = TITLE_TAG_RE.search(page_html)
        if m:
            name = html_mod.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()

    if name:
        # "상품명 : 스토어명" / "상품명 | 쿠팡" 같은 꼬리표 제거
        name = re.split(r"\s*[:|｜\|]\s*(?:쿠팡|네이버|스마트스토어)[^:|]*$", name)[0].strip()
        name = re.sub(r"\s*-\s*(?:쿠팡|네이버쇼핑|스마트스토어)\s*$", "", name).strip()
    return (name or None), (mall or None)


def fetch_product(url, timeout=15):
    """상품 페이지를 열어 이름/몰명 확보. 차단되면 실브라우저로 재시도.
    반환: (name, mall, error_message | None)"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 403:
            raise coupang.BlockedError()
        r.raise_for_status()
        name, mall = parse_product_page(r.text)
        if name:
            return name, mall, None
        raise ValueError("제목을 찾지 못함")
    except Exception as first_err:
        if browser.available():
            try:
                page_html = browser.fetch_html(url)
                name, mall = parse_product_page(page_html)
                if name:
                    return name, mall, None
            except Exception as e:
                return None, None, f"페이지를 읽지 못했습니다 ({type(e).__name__})"
        return None, None, f"페이지를 읽지 못했습니다 ({type(first_err).__name__})"


# ─────────────────────────── 제목 → 키워드 후보 ───────────────────────────

# 검색 키워드로 쓰이지 않는 홍보/포장 문구
STOPWORDS = {
    "무료배송", "당일발송", "당일출고", "정품", "최저가", "특가", "할인", "사은품", "증정",
    "국내산", "본사직영", "공식", "공식판매처", "인증", "신상", "신제품", "인기", "베스트",
    "추천", "선물", "선물용", "세트", "패키지", "기획", "기획전", "묶음", "대용량", "리뉴얼",
    "정식수입", "해외직구", "무료", "택배", "쿠팡", "로켓배송", "무료반품",
}
# 수량·용량·옵션 표기 (키워드가 아님)
SPEC_UNITS = ("개|정|알|캡슐|포|매|장|입|박스|병|팩|캔|봉|세트|인용|인분|구|호|년|개월분|일분|회분|"
              "ml|l|g|kg|mg|mcg|iu|cc|cm|mm|m|인치|inch|w|v|a|ea|%")
SPEC_RE = re.compile(
    r"^(?:\d+(?:\.\d+)?\s*(?:" + SPEC_UNITS + r")?|\d+\s*\+\s*\d+|x\s*\d+)$", re.I
)
BRACKET_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)|【[^】]*】|<[^>]*>|〈[^〉]*〉")


def _tokens(title):
    t = BRACKET_RE.sub(" ", title)
    t = re.sub(r"[,/·ㆍ\|~]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    out = []
    for raw in t.split(" "):
        tok = raw.strip("-_.,:;!?\"'()").strip()
        if not tok or tok in STOPWORDS or SPEC_RE.match(tok):
            continue
        if len(tok) == 1:                                  # 한 글자는 단독 키워드로 무의미
            continue
        if re.fullmatch(r"[A-Za-z]{1,4}", tok):            # rTG, PRO 같은 짧은 영문 규격
            continue
        out.append(tok)
    return out


def _score(tok, idx, total):
    """제목 내 위치·형태로 '검색될 법한 정도'를 매긴다. 카테고리어는 대개 뒤쪽에 온다."""
    s = 1.5 if len(tok) >= 2 else 0.0
    if re.search(r"[가-힣]", tok):
        s += 1.0
    if total > 1:
        pos = idx / (total - 1)
        s += 0.9 * max(0.0, 1 - abs(pos - 0.75) / 0.75)    # 제목의 75% 지점에서 최대
    if idx == total - 1:
        s += 0.6                                            # 마지막 어절 = 카테고리일 확률 높음
    return s


def suggest_keywords(title, limit=12):
    """반환: [{keyword, recommended}] — 점수순. 상위 5개를 기본 체크.

    완벽한 순위를 매기는 것이 목적이 아니라, 사람이 실제로 검색할 만한 조합이
    목록 안에 들어오게 하는 것이 목적. 최종 선택은 화면에서 클릭으로 한다."""
    toks = _tokens(title)
    if not toks:
        return []
    total = len(toks)
    scored = [(t, _score(t, i, total)) for i, t in enumerate(toks)]
    top = sorted(scored, key=lambda x: -x[1])
    cores = [t for t, _ in top[:2]]          # 핵심어 후보를 둘로 — 위치 추정이 빗나가도 건진다
    best = top[0][1]

    cands = {}   # 단어 묶음 → (키워드, 점수). 어순만 다른 중복은 하나만 남긴다

    def add(kw, score):
        kw = kw.strip()
        parts = kw.split()
        if not kw or len(kw) > 22 or len(parts) > 3 or len(set(parts)) != len(parts):
            return
        key = frozenset(parts)
        prev = cands.get(key)
        if prev is None or score > prev[1]:
            cands[key] = (kw, score)

    for tok, sc in scored:
        add(tok, sc)
    for i in range(total - 1):               # 제목에 붙어 있는 두 어절 = 가장 자연스러운 검색어
        add(f"{toks[i]} {toks[i+1]}", (scored[i][1] + scored[i+1][1]) / 2 + 1.0)
    for tok, sc in scored:                   # 수식어 + 핵심어 (떨어져 있어도 흔히 함께 검색됨)
        for core in cores:
            if tok != core:
                add(f"{tok} {core}", (sc + best) / 2 + 0.2)

    ranked = sorted(cands.values(), key=lambda x: (-x[1], len(x[0])))[:limit]
    cut = min(5, len(ranked))
    return [{"keyword": kw, "recommended": i < cut} for i, (kw, _) in enumerate(ranked)]


# ─────────────────────────── 통합 진입점 ───────────────────────────

def inspect_link(url):
    """링크 하나로 등록에 필요한 모든 것을 준비한다."""
    url = (url or "").strip()
    channel = detect_channel(url)
    if not channel:
        return {"ok": False, "error": "쿠팡 또는 네이버(스마트스토어·쇼핑) 상품 링크를 넣어주세요"}

    ids = ids_from_url(url, channel)
    name, mall, err = fetch_product(url)
    mall = mall or ids["mall"]

    return {
        "ok": bool(name),
        "channel": channel,
        "name": name or "",
        "mall": mall or "",
        "link": url,
        "ext_ids": json.dumps(ids["ext_ids"]) if ids["ext_ids"] else None,
        "nvmid": ids["nvmid"],
        "keywords": suggest_keywords(name) if name else [],
        "error": None if name else (err or "상품명을 찾지 못했습니다 — 직접 입력해 주세요"),
    }
