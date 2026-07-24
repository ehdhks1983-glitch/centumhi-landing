"""매칭 알고리즘 + 조회 루프 + 자동 승격 (개발명령서 v1.1 §3, §4, §6)"""
import html
import re
import time

import db
from naver_api import call_api, QuotaExceeded

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")

MAX_START = 1000  # API 제약: start 최대 1000


def normalize(text):
    """API가 검색어를 <b> 태그로 감싸 반환하므로 태그 제거 필수. 이후 공백 압축 + 소문자화."""
    text = TAG_RE.sub("", text or "")
    text = html.unescape(text)
    return WS_RE.sub(" ", text).strip().lower()


def check_rank(keyword, product, track_limit):
    """반환: (rank | None, match_method, found | None)
    found = (rank, productId, mallName) — 이름 매칭 시에만. 호출부에서 nvmid 승격에 사용."""
    name_hit = None
    target = normalize(product["product_name"])
    nvmid = product["nvmid"]
    mall_name = product["mall_name"]

    for start in range(1, min(track_limit, MAX_START) + 1, 100):
        display = min(100, track_limit - start + 1)
        items = call_api(keyword, start, display)

        for idx, item in enumerate(items):
            rank = start + idx

            # 1순위: nvmid 정밀 매칭
            if nvmid and item.get("productId") == nvmid:
                return rank, "nvmid", None

            # 2순위: 이름(+몰명) 매칭 — 첫 히트만 기억
            if name_hit is None and normalize(item.get("title")) == target:
                if not mall_name or item.get("mallName") == mall_name:
                    name_hit = (rank, item.get("productId"), item.get("mallName"))

        if len(items) < display:
            break  # 검색 결과 끝 — 더 넘겨봐야 빈 페이지

        time.sleep(0.15)  # 초당 10회 한도 여유

    if name_hit:
        return name_hit[0], "name", name_hit  # productId를 호출부에서 DB에 승격 저장
    return None, "not_found", None


def run_all_checks(log=print):
    """(활성 상품 × 키워드) 전부 순차 처리. 병렬화 금지 (§7).
    에러 처리(§6): 한도 도달 → 그날 중단 / 그 외 → 로그 남기고 다음 키워드로. 앱은 절대 안 죽는다."""
    products = db.get_active_products()
    log(f"조회 시작 — 활성 상품 {len(products)}개")

    for product in products:
        for kw in db.get_keywords(product["id"]):
            keyword = kw["keyword"]
            try:
                rank, method, found = check_rank(keyword, product, product["track_limit"])
                db.save_result(kw["id"], rank, method)
                if found:
                    db.promote_nvmid(product["id"], found[1], found[2])  # 자동 승격
                    log(f"[{keyword}] {rank}위 (이름 매칭 → nvmid 자동 승격)")
                elif rank:
                    log(f"[{keyword}] {rank}위 ({method})")
                else:
                    log(f"[{keyword}] {product['track_limit']}위 내 미발견")
            except QuotaExceeded:
                log("일일 한도 도달 — 중단, 내일 재개")
                return  # 남은 큐 포기, 다음날 스케줄러가 처음부터 다시
            except Exception as e:
                log(f"조회 실패 [{keyword}]: {e}")
                continue  # 이 키워드만 건너뛰고 계속

    log("조회 완료")


if __name__ == "__main__":
    # 빌드 순서 3번 관문 (§9): 콘솔에서 순위 출력 → 실제 네이버쇼핑과 눈으로 대조
    db.init_db()
    run_all_checks()
