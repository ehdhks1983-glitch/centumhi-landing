"""엔트리 포인트 — APScheduler + FastAPI 웹 서버 기동 (웹 전환판)

실행: python main.py  →  브라우저에서 http://localhost:8000 접속
서버가 떠 있는 동안 매일 check_hour시에 자동 조회. (서버에 올리면 24시간 자동)

호스트/포트 변경: 환경변수 HOST, PORT (예: HOST=0.0.0.0 PORT=8080 python main.py)
"""
import os

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

import db
import tracker
import webapp

JOB_ID = "daily_check"


def main():
    db.init_db()

    check_hour = int(db.get_setting("check_hour", "9"))
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: tracker.run_all_checks(log=webapp.add_log), "cron",
        hour=check_hour, minute=0, id=JOB_ID,
        coalesce=True, misfire_grace_time=6 * 3600,  # 절전 등으로 놓친 조회는 깨어난 뒤 실행 (6시간 유예)
    )
    scheduler.start()
    webapp.reschedule_fn = lambda h: scheduler.reschedule_job(
        JOB_ID, trigger="cron", hour=h, minute=0
    )
    webapp.add_log(f"서버 시작 — 자동 조회 매일 {check_hour:02d}:00")

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    try:
        uvicorn.run(webapp.app, host=host, port=port, log_level="warning")
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
