"""FastAPI 웹 앱 — 데스크톱 gui.py를 대체하는 웹 UI 백엔드.

브라우저는 static/index.html 하나를 받고, 이후 /api/* 로 통신한다.
조회는 백그라운드 스레드에서 돌고 로그는 폴링으로 내려준다.
"""
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import db
import tracker

app = FastAPI(title="네이버 순위추적기", docs_url=None, redoc_url=None)

INDEX_HTML = Path(__file__).parent / "static" / "index.html"

_log_lock = threading.Lock()
_logs: list[str] = []
_log_base = 0          # 상한 초과로 버린 로그 줄 수 — 폴링 커서 보정용
_MAX_LOGS = 2000       # 장기 실행 서버의 메모리 상한
_check_thread: threading.Thread | None = None

reschedule_fn = None  # main.py가 스케줄러 재설정 함수를 주입


def add_log(msg: str):
    global _log_base
    with _log_lock:
        _logs.append(f"{time.strftime('%H:%M:%S')}  {msg}")
        if len(_logs) > _MAX_LOGS:
            drop = len(_logs) - _MAX_LOGS
            del _logs[:drop]
            _log_base += drop


def _is_checking() -> bool:
    # 수동 조회 스레드뿐 아니라 스케줄러발 자동 조회도 잠금으로 감지
    return (_check_thread is not None and _check_thread.is_alive()) or tracker.run_lock.locked()


# ---------- 화면 ----------

@app.get("/")
def index():
    return FileResponse(INDEX_HTML)


# ---------- 상태 ----------

@app.get("/api/state")
def state():
    products = []
    for p in db.get_all_products():
        keywords = []
        for kw in db.get_keywords(p["id"]):
            latest = db.get_latest_rank(kw["id"])
            keywords.append({
                "id": kw["id"],
                "keyword": kw["keyword"],
                "latest": {
                    "date": latest["checked_date"],
                    "rank": latest["rank"],
                    "method": latest["match_method"],
                } if latest else None,
            })
        products.append({
            "id": p["id"], "name": p["product_name"], "mall": p["mall_name"],
            "nvmid": p["nvmid"], "link": p["product_link"],
            "track_limit": p["track_limit"], "is_active": bool(p["is_active"]),
            "keywords": keywords,
        })
    return {
        "products": products,
        "usage": db.get_today_usage(),
        "checking": _is_checking(),
        "check_hour": int(db.get_setting("check_hour", "9")),
        "has_keys": bool(db.get_setting("client_id") and db.get_setting("client_secret")),
    }


# ---------- 상품 등록/삭제 ----------

class ProductIn(BaseModel):
    name: str = Field(min_length=1)
    mall: str = ""
    link: str = ""
    track_limit: int = 100
    keywords: list[str]


@app.post("/api/products")
def create_product(body: ProductIn):
    kws = [k.strip() for k in body.keywords if k.strip()]
    if not kws:
        raise HTTPException(422, "키워드는 1개 이상 필요합니다")
    limit = max(1, min(1000, body.track_limit))
    pid = db.add_product(body.name.strip(), body.mall.strip(), body.link.strip(), limit, kws)
    add_log(f"상품 등록: {body.name.strip()} (키워드 {len(kws)}개, 추적 {limit}위) — 등록 시 API 호출 0회")
    return {"id": pid}


@app.delete("/api/products/{product_id}")
def remove_product(product_id: int):
    db.delete_product(product_id)
    add_log(f"상품 #{product_id} 삭제")
    return {"ok": True}


@app.post("/api/products/{product_id}/active")
def toggle_active(product_id: int, active: bool):
    db.set_product_active(product_id, active)
    return {"ok": True}


# ---------- 이력 ----------

@app.get("/api/history/{keyword_id}")
def history(keyword_id: int):
    rows = db.get_history(keyword_id)
    return [{"date": r["checked_date"], "rank": r["rank"], "method": r["match_method"]} for r in rows]


# ---------- 설정 ----------

class SettingsIn(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    check_hour: int = 9


@app.post("/api/settings")
def save_settings(body: SettingsIn):
    if body.client_id.strip():
        db.set_setting("client_id", body.client_id.strip())
    if body.client_secret.strip():
        db.set_setting("client_secret", body.client_secret.strip())
    hour = max(0, min(23, body.check_hour))
    db.set_setting("check_hour", str(hour))
    if reschedule_fn:
        reschedule_fn(hour)
    add_log(f"설정 저장 — 자동 조회 매일 {hour:02d}:00")
    return {"ok": True}


# ---------- 조회 실행 + 로그 ----------

@app.post("/api/check")
def run_check():
    global _check_thread
    if _is_checking():
        return {"started": False, "reason": "이미 조회가 진행 중입니다"}
    if not (db.get_setting("client_id") and db.get_setting("client_secret")):
        raise HTTPException(400, "API 키 미설정 — 상단 설정에 Client ID/Secret을 저장하세요")

    def worker():
        try:
            tracker.run_all_checks(log=add_log)
        except Exception as e:  # 앱은 절대 죽으면 안 됨 (§6)
            add_log(f"조회 루프 오류: {e}")

    _check_thread = threading.Thread(target=worker, daemon=True)
    _check_thread.start()
    return {"started": True}


@app.get("/api/logs")
def logs(since: int = 0):
    with _log_lock:
        idx = max(0, since - _log_base)
        return {"next": _log_base + len(_logs), "lines": _logs[idx:]}
