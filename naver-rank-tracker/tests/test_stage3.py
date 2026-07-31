"""③ 순위 급변 텔레그램 알림 검증 — 문구 생성 로직 + 전송 + 조회 루프 통합."""
import os, sys, tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db
db.DB_PATH = os.path.join(tempfile.mkdtemp(), "s3.db")
db.init_db()

import alerts
import tracker

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))

# 1. 문구 생성 로직
check("급락 28 → 🔻", alerts.build_alert("A · kw", 137, 165, 10) == "🔻 A · kw: 137위 → 165위 (▼28)", alerts.build_alert("A · kw", 137, 165, 10))
check("급등 15 → 🔺", alerts.build_alert("A · kw", 50, 35, 10) == "🔺 A · kw: 50위 → 35위 (▲15)", "")
check("소폭 변동(9) → 알림 없음", alerts.build_alert("A · kw", 50, 59, 10) is None, "")
check("범위 밖 이탈 → 🔻", "추적범위 밖" in alerts.build_alert("A · kw", 80, None, 10), "")
check("첫 조회(비교대상 없음) → 없음", alerts.build_alert("A · kw", None, 30, 10) is None, "")

# 2. 전송: 미설정 → False, 설정 → API 호출
sent = []
real_post = alerts.requests.post
class FakeResp:
    def raise_for_status(self): pass
alerts.requests.post = lambda url, json=None, timeout=None: (sent.append((url, json)), FakeResp())[1]
check("미설정 시 전송 안 함 (False)", alerts.send("테스트") is False and not sent, "")
db.set_setting("telegram_token", "TOKEN123"); db.set_setting("telegram_chat_id", "999")
ok = alerts.send("테스트 메시지")
check("설정 시 전송 (URL에 토큰, chat_id 포함)", ok and "botTOKEN123" in sent[0][0] and sent[0][1]["chat_id"] == "999", str(sent[0][0])[:60])

# 3. 조회 루프 통합: 어제 137위 → 오늘 165위(급락 28) + 어제 5위 상품 → 오늘 미발견
yesterday = (date.today() - timedelta(days=1)).isoformat()
pA = db.add_product("급락상품", None, None, 200, ["키워드A"], channel="naver")
db.promote_nvmid(pA, "NVA")
pB = db.add_product("이탈상품", None, None, 100, ["키워드B"], channel="naver")
db.promote_nvmid(pB, "NVB")
kA = db.get_keywords(pA)[0]; kB = db.get_keywords(pB)[0]
db.save_result(kA["id"], 137, "nvmid", yesterday)
db.save_result(kB["id"], 5, "nvmid", yesterday)
db.set_setting("client_id", "x"); db.set_setting("client_secret", "y")
db.set_setting("alert_threshold", "10"); db.set_setting("verify_real", "0")

def naver_items(keyword, start, display):
    out = []
    for i in range(display):
        r = start + i
        # 급락상품: 오늘 165위 / 이탈상품: 아예 없음
        out.append({"title": "<b>급락상품</b>", "productId": "NVA", "mallName": "몰"} if r == 165
                   else {"title": f"기타 {r}", "productId": f"X{r}", "mallName": "타"})
    return out
tracker.call_api = lambda k, s=1, d=100: naver_items(k, s, d)
tracker.time.sleep = lambda s: None

sent.clear()
logs = []
tracker.run_all_checks(log=logs.append)
check("전송 1건으로 합침 + 로그", len(sent) == 1 and any("텔레그램 알림 전송 (2건)" in l for l in logs),
      " / ".join(l for l in logs if "텔레그램" in l))
text = sent[0][1]["text"] if sent else ""
check("급락 28 문구 포함", "급락상품 · 키워드A: 137위 → 165위 (▼28)" in text, text[:120])
check("범위 밖 이탈 문구 포함", "이탈상품 · 키워드B: 5위 → 추적범위 밖" in text, "")

# 4. 같은 날 재조회는 비교 대상 아님 (어제와만 비교 → 동일 결과라 재알림 없음... 순위 동일하므로)
# → 오늘 순위를 165→165로 재조회: 어제(137) 대비 여전히 급락이므로 알림이 또 갈 수 있는 구조인지 확인
sent.clear(); logs.clear()
tracker.run_all_checks(log=logs.append)
check("재조회: 같은 날은 재알림 없음", len(sent) == 0, f"{len(sent)}건")

# 5. 전송 실패해도 조회는 죽지 않음
def boom(url, json=None, timeout=None): raise ConnectionError("네트워크")
alerts.requests.post = boom
logs.clear()
tracker.run_all_checks(log=logs.append)
check("전송 실패 → 로그만 남기고 정상 종료", any("조회 완료" in l for l in logs), " / ".join(logs[-2:]))
alerts.requests.post = real_post

fail = 0
for name, ok, detail in results:
    print(("PASS" if ok else "FAIL"), "|", name, "|", detail)
    fail += 0 if ok else 1
sys.exit(1 if fail else 0)
