"""매칭 알고리즘 + 조회 루프 + 자동 승격 (개발명령서 v1.1 §3, §4, §6)"""
import html
import json
import re
import threading
import time

from datetime import date

import alerts
import browser
import coupang
import db
import naver_web
from naver_api import call_api, QuotaExceeded

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")

MAX_START = 1000  # API 제약: start 최대 1000

# 스케줄 자동 조회와 수동 조회가 겹쳐 돌지 않도록 하는 전역 잠금
run_lock = threading.Lock()


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
        if name_hit and not nvmid:
            break  # nvmid가 없으면 더 찾을 대상이 없다 — 남은 페이지 호출은 할당량 낭비

        time.sleep(0.15)  # 초당 10회 한도 여유

    if name_hit:
        return name_hit[0], "name", name_hit  # productId를 호출부에서 DB에 승격 저장
    return None, "not_found", None


def run_all_checks(log=print):
    """(활성 상품 × 키워드) 전부 순차 처리. 병렬화 금지 (§7).
    에러 처리(§6): 한도 도달 → 그날 중단 / 그 외 → 로그 남기고 다음 키워드로. 앱은 절대 안 죽는다."""
    if not run_lock.acquire(blocking=False):
        log("이미 조회가 진행 중 — 이번 실행은 건너뜀")
        return
    try:
        products = db.get_active_products()
        log(f"조회 시작 — 활성 상품 {len(products)}개")

        verify_real = db.get_setting("verify_real", "0") == "1"
        if verify_real and not browser.available():
            verify_real = False
            log("실측 검증 건너뜀 — playwright 미설치 (pip install playwright && playwright install chromium)")

        threshold = int(db.get_setting("alert_threshold", "10"))
        today = date.today().isoformat()
        alert_msgs = []

        for row in products:
            product = dict(row)  # 같은 실행 안에서 승격된 nvmid를 다음 키워드가 바로 쓰도록
            for kw in db.get_keywords(product["id"]):
                keyword = kw["keyword"]
                try:
                    prev = db.get_prev_rank(kw["id"], today)  # 어제(직전 조회일) 순위 — 급변 비교용
                    latest = db.get_latest_rank(kw["id"])
                    already_alerted_today = latest is not None and latest["checked_date"] == today
                    if product["channel"] == "coupang":
                        rank, method, found = coupang.check_rank(keyword, product, product["track_limit"], log=log)
                    else:
                        rank, method, found = check_rank(keyword, product, product["track_limit"])
                    db.save_result(kw["id"], rank, method)
                    if not already_alerted_today:  # 같은 날 재조회는 재알림 안 함
                        msg = alerts.build_alert(f"{product['product_name']} · {keyword}",
                                                 prev["rank"] if prev else None, rank, threshold)
                        if msg:
                            alert_msgs.append(msg)
                    if found:
                        if product["channel"] == "coupang":
                            ext = json.dumps(found)
                            db.promote_ext_ids(product["id"], ext)  # 자동 승격 (쿠팡)
                            product["ext_ids"] = ext
                            log(f"[{keyword}] {rank}위 (이름 매칭 → 상품 ID 자동 확보)")
                        else:
                            db.promote_nvmid(product["id"], found[1], found[2])  # 자동 승격 (네이버)
                            product["nvmid"] = found[1]
                            product["mall_name"] = product["mall_name"] or found[2]
                            log(f"[{keyword}] {rank}위 (이름 매칭 → nvmid 자동 승격)")
                    elif rank:
                        log(f"[{keyword}] {rank}위 ({method})")
                    else:
                        log(f"[{keyword}] {product['track_limit']}위 내 미발견")

                    # 실측 검증 (네이버 하이브리드): API 순위와 실제 노출 순위 대조
                    if (verify_real and product["channel"] == "naver"
                            and rank and product["nvmid"]):
                        _verify_real_rank(kw["id"], keyword, product, rank, log)
                except QuotaExceeded:
                    log("일일 한도 도달 — 중단, 내일 재개")
                    return  # 남은 큐 포기, 다음날 스케줄러가 처음부터 다시
                except Exception as e:
                    log(f"조회 실패 [{keyword}]: {e}")
                    continue  # 이 키워드만 건너뛰고 계속

        log("조회 완료")

        if alert_msgs:
            try:
                if alerts.send("📊 순위 급변 알림\n" + "\n".join(alert_msgs)):
                    log(f"텔레그램 알림 전송 ({len(alert_msgs)}건)")
                else:
                    log(f"순위 급변 {len(alert_msgs)}건 — 텔레그램 미설정으로 알림 생략")
            except Exception as e:
                log(f"텔레그램 전송 실패: {e}")
    finally:
        run_lock.release()


def _verify_real_rank(keyword_id, keyword, product, api_rank, log):
    """실브라우저로 실제 노출 순위를 확인해 이력에 병기. 실패해도 조회는 계속."""
    try:
        real = naver_web.check_real_rank(keyword, product["nvmid"], product["track_limit"])
        db.save_real_rank(keyword_id, real)
        if real:
            log(f"[{keyword}] 실측 {real}위 (API {api_rank}위, 오차 {real - api_rank:+d})")
        else:
            log(f"[{keyword}] 실측: {product['track_limit']}위 내 미발견 (API {api_rank}위)")
    except Exception as e:
        log(f"실측 실패 [{keyword}]: {e}")


if __name__ == "__main__":
    # 빌드 순서 3번 관문 (§9): 콘솔에서 순위 출력 → 실제 네이버쇼핑과 눈으로 대조
    db.init_db()
    run_all_checks()
