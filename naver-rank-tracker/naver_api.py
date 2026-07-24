"""네이버 쇼핑 검색 API 호출 + 일일 사용량 카운트 (개발명령서 v1.1 §5)

검증된 스펙: display 최대 100 · start 최대 1000 · 일 25,000회 · 초당 약 10회
"""
import requests

import db

BASE = "https://openapi.naver.com/v1/search/shop.json"
DAILY_LIMIT = 24000  # 25,000에서 여유분


class QuotaExceeded(Exception):
    """일일 API 한도 도달"""


def call_api(query, start=1, display=100):
    if db.get_today_usage() >= DAILY_LIMIT:
        raise QuotaExceeded()

    cid = db.get_setting("client_id")
    csec = db.get_setting("client_secret")
    if not cid or not csec:
        raise RuntimeError("API 키 미설정 — 메인화면에서 Client ID/Secret을 저장하세요")

    r = requests.get(
        BASE,
        params={"query": query, "start": start, "display": display},
        headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec},
        timeout=10,
    )
    db.increment_today_usage()
    r.raise_for_status()
    return r.json()["items"]


if __name__ == "__main__":
    # 코딩 전 5분 확인 (부록): 콘솔에서 키워드 하나 던져 실제 응답 확인
    import json
    import sys

    db.init_db()
    kw = sys.argv[1] if len(sys.argv) > 1 else input("검색 키워드: ")
    items = call_api(kw, start=1, display=5)
    for i, item in enumerate(items, 1):
        print(f"--- {i}위 ---")
        print(json.dumps(item, ensure_ascii=False, indent=2))
    print("\n[확인] productId 필드 존재:", all("productId" in it for it in items))
    print("[확인] mallName 값 예시:", [it.get("mallName") for it in items])
