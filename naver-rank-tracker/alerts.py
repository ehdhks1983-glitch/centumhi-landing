"""텔레그램 순위 급변 알림 (v1.2 항목).

조회 완료 후 어제(직전 조회일) 대비 순위가 기준치 이상 변동한 키워드만 모아
텔레그램 메시지 1건으로 전송한다. 미설정 시 조용히 꺼짐. 전송 실패해도
조회 흐름은 절대 죽지 않는다(호출부에서 try/except).
"""
import requests

import db

API = "https://api.telegram.org/bot{token}/sendMessage"


def build_alert(label, prev_rank, new_rank, threshold):
    """변동이 기준 이상일 때만 알림 문구 반환, 아니면 None.
    prev_rank가 없으면(첫 조회) 비교 대상이 없어 알림 없음."""
    if prev_rank is None:
        return None
    if new_rank is None:
        return f"🔻 {label}: {prev_rank}위 → 추적범위 밖으로 이탈"
    diff = new_rank - prev_rank
    if diff >= threshold:
        return f"🔻 {label}: {prev_rank}위 → {new_rank}위 (▼{diff})"
    if -diff >= threshold:
        return f"🔺 {label}: {prev_rank}위 → {new_rank}위 (▲{-diff})"
    return None


def configured():
    return bool(db.get_setting("telegram_token") and db.get_setting("telegram_chat_id"))


def send(text):
    """전송 성공 True / 미설정 False. 네트워크 오류는 예외로 올림(호출부 처리)."""
    token = db.get_setting("telegram_token")
    chat_id = db.get_setting("telegram_chat_id")
    if not token or not chat_id:
        return False
    r = requests.post(API.format(token=token),
                      json={"chat_id": chat_id, "text": text}, timeout=10)
    r.raise_for_status()
    return True
