"""엔트리 포인트 — APScheduler + FastAPI 웹 서버 기동.

실행: python main.py  →  브라우저가 자동으로 열린다 (http://localhost:8000)
서버가 떠 있는 동안 매일 check_hour시에 자동 조회. (서버에 올리면 24시간 자동)

호스트/포트 변경: 환경변수 HOST, PORT (예: HOST=0.0.0.0 PORT=8080 python main.py)
브라우저 자동 열기 끄기: RANKTRACKER_NO_BROWSER=1
"""
import os
import socket
import threading
import webbrowser
from datetime import date, datetime

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

import db
import tracker
import webapp

JOB_ID = "daily_check"
LOCAL_HOSTS = ("127.0.0.1", "localhost", "0.0.0.0")


def _port_in_use(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        probe = "127.0.0.1" if host == "0.0.0.0" else host
        return s.connect_ex((probe, port)) == 0


def _find_port(host, start):
    """이미 쓰는 포트면 다음 포트를 찾는다. (None = 우리 서버가 이미 떠 있음)"""
    if not _port_in_use(host, start):
        return start
    # 이미 우리 서버가 떠 있는지 확인
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{start}/api/state", timeout=1.5) as r:
            if r.status == 200:
                return None          # 우리 프로그램이 이미 실행 중
    except Exception:
        pass
    for p in range(start + 1, start + 12):   # 다른 프로그램이 점유 → 옆 포트로
        if not _port_in_use(host, p):
            return p
    return start


def _banner(url, check_hour):
    line = "=" * 60
    print()
    print(line)
    print("  상품 순위추적기가 켜졌습니다")
    print(line)
    print()
    print(f"   브라우저 주소  :  {url}")
    print("   (브라우저가 자동으로 열립니다. 안 열리면 위 주소를 직접 입력하세요)")
    print()
    print(f"   자동 조회      :  매일 {check_hour:02d}:00")
    print("   이 창을 닫으면 자동 조회가 멈춥니다 — 끄지 말고 최소화해 두세요.")
    print("   종료하려면 이 창에서 Ctrl+C 를 누르세요.")
    print()
    print(line)
    print()


def _catch_up_if_missed(check_hour):
    """PC가 꺼져 있어 조회 시각을 놓쳤으면, 켠 직후 한 번 따라잡는다.
    (오늘 이력이 하나도 없고, 이미 조회 시각이 지났을 때만)"""
    now = datetime.now()
    if now.hour < check_hour:
        return
    today = date.today().isoformat()
    with db.get_conn() as conn:
        done = conn.execute(
            "SELECT 1 FROM rank_history WHERE checked_date = ? LIMIT 1", (today,)
        ).fetchone()
    if done or not db.get_active_products():
        return

    webapp.add_log(f"오늘 {check_hour:02d}:00 자동 조회를 놓쳐 지금 대신 실행합니다")
    threading.Thread(
        target=lambda: tracker.run_all_checks(log=webapp.add_log), daemon=True
    ).start()


def main():
    db.init_db()

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    is_local = host in LOCAL_HOSTS

    chosen = _find_port(host, port) if is_local else port
    if chosen is None:
        url = f"http://localhost:{port}"
        print()
        print("  순위추적기가 이미 실행 중입니다.")
        print(f"  브라우저에서 {url} 을 여세요. (지금 열어드립니다)")
        print()
        if os.environ.get("RANKTRACKER_NO_BROWSER") != "1":
            webbrowser.open(url)
        return
    if chosen != port:
        print(f"\n  {port}번 포트를 다른 프로그램이 쓰고 있어 {chosen}번으로 실행합니다.\n")
    port = chosen

    check_hour = int(db.get_setting("check_hour", "9"))
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: tracker.run_all_checks(log=webapp.add_log), "cron",
        hour=check_hour, minute=0, id=JOB_ID,
        coalesce=True, misfire_grace_time=6 * 3600,  # 절전 등으로 놓친 조회는 깨어난 뒤 실행
    )
    scheduler.start()
    webapp.reschedule_fn = lambda h: scheduler.reschedule_job(
        JOB_ID, trigger="cron", hour=h, minute=0
    )
    webapp.add_log(f"서버 시작 — 자동 조회 매일 {check_hour:02d}:00")

    url = f"http://localhost:{port}"
    if is_local:
        _banner(url, check_hour)
        if os.environ.get("RANKTRACKER_NO_BROWSER") != "1":
            threading.Timer(1.5, lambda: webbrowser.open(url)).start()
        _catch_up_if_missed(check_hour)

    try:
        uvicorn.run(webapp.app, host=host, port=port, log_level="warning")
    except OSError as e:
        print(f"\n  [오류] 서버를 시작하지 못했습니다: {e}")
        print("  다른 프로그램이 포트를 쓰고 있거나 방화벽이 막고 있을 수 있습니다.\n")
        input("  엔터를 누르면 닫힙니다...")
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
