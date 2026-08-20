"""④ 배포 준비 검증 — WEB_PASSWORD Basic 인증 + RANKTRACKER_DB 경로 오버라이드."""
import base64
import importlib
import os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))

# ── 1. RANKTRACKER_DB 오버라이드 ──
custom = os.path.join(tempfile.mkdtemp(), "custom.db")
os.environ["RANKTRACKER_DB"] = custom
import db
importlib.reload(db)
check("RANKTRACKER_DB로 DB 경로 지정", db.DB_PATH == custom, db.DB_PATH)
db.init_db()
check("지정 경로에 DB 생성", os.path.exists(custom), "")
del os.environ["RANKTRACKER_DB"]

import webapp
from fastapi.testclient import TestClient
client = TestClient(webapp.app)

def auth_header(pw, user="admin"):
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()}

# ── 2. WEB_PASSWORD 미설정 → 인증 없이 접속 (로컬 사용) ──
os.environ.pop("WEB_PASSWORD", None)
r = client.get("/api/state")
check("비밀번호 미설정: 자유 접속", r.status_code == 200, f"{r.status_code}")

# ── 3. WEB_PASSWORD 설정 → 401 / 올바른 비밀번호 → 200 ──
os.environ["WEB_PASSWORD"] = "secret123"
r1 = client.get("/")
r2 = client.get("/api/state", headers=auth_header("wrong"))
r3 = client.get("/api/state", headers=auth_header("secret123"))
r4 = client.get("/api/state", headers=auth_header("secret123", user="anything"))
check("미인증 → 401 + WWW-Authenticate", r1.status_code == 401 and "Basic" in r1.headers.get("www-authenticate", ""), f"{r1.status_code}")
check("틀린 비밀번호 → 401", r2.status_code == 401, f"{r2.status_code}")
check("올바른 비밀번호 → 200", r3.status_code == 200, f"{r3.status_code}")
check("사용자명은 무관", r4.status_code == 200, f"{r4.status_code}")

# ── 4. 손상된 Authorization 헤더에도 안 죽음 ──
r5 = client.get("/api/state", headers={"Authorization": "Basic %%%broken%%%"})
check("깨진 헤더 → 401 (서버 정상)", r5.status_code == 401, f"{r5.status_code}")
os.environ.pop("WEB_PASSWORD", None)

fail = 0
for name, ok, detail in results:
    print(("PASS" if ok else "FAIL"), "|", name, "|", detail)
    fail += 0 if ok else 1
sys.exit(1 if fail else 0)
