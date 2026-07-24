"""엔트리 포인트 + APScheduler 기동 (개발명령서 v1.1 §7)

앱이 떠 있을 때만 자동 조회 동작. 기본 매일 09:00, 메인화면에서 변경 가능.
"""
from apscheduler.schedulers.background import BackgroundScheduler

import db
import tracker
from gui import App

JOB_ID = "daily_check"


def main():
    db.init_db()

    check_hour = int(db.get_setting("check_hour", "9"))
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        tracker.run_all_checks, "cron",
        hour=check_hour, minute=0, id=JOB_ID,
    )
    scheduler.start()

    def reschedule(hour):
        scheduler.reschedule_job(JOB_ID, trigger="cron", hour=hour, minute=0)

    app = App(scheduler=scheduler, reschedule=reschedule)
    try:
        app.mainloop()
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
