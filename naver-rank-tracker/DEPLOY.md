# 서버 배포 가이드 — 24시간 자동 조회 만들기

PC에서만 쓸 거면 이 문서는 필요 없다. 서버에 올리면 PC를 꺼도 매일 자동 조회된다.

## 필수 환경변수

| 변수 | 값 | 설명 |
|---|---|---|
| `WEB_PASSWORD` | 원하는 비밀번호 | **필수** — 설정하면 접속 시 비밀번호를 물음 (사용자명은 아무거나). 미설정 상태로 공개 인터넷에 올리면 누구나 내 API 키·데이터에 접근 가능 |
| `RANKTRACKER_DB` | `/data/rank_tracker.db` | DB 파일 위치 (Dockerfile 기본값) — 볼륨에 둬야 재배포해도 이력 유지 |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Dockerfile 기본값 |

## Railway 기준 (무료 티어로 시작 가능)

1. railway.app 가입 → New Project → **Deploy from GitHub repo** → 이 저장소 선택
2. Settings → Root Directory를 `naver-rank-tracker`로 지정 (Dockerfile 자동 감지)
3. Variables에 `WEB_PASSWORD` 추가
4. **Volume 추가** → Mount Path `/data` ← 이걸 빼먹으면 재배포 때 데이터가 사라짐
5. Settings → Networking → Generate Domain → 발급된 주소로 접속

Render도 동일 개념: New Web Service → 저장소 연결 → Root Directory 지정 →
Docker 런타임 → Disk(볼륨) `/data` 추가 → 환경변수 설정.

## 배포 후 확인 순서

1. 발급된 주소 접속 → 비밀번호 입력창이 뜨는지 (안 뜨면 WEB_PASSWORD 미적용)
2. 네이버 Client ID/Secret 저장 → 상품 등록 → "지금 조회"로 실제 순위 확인
3. 자동 조회 시각 설정 → 다음 날 로그에 자동 실행 기록이 남는지 확인

## 주의

- 서버 시간은 보통 UTC — 한국 09:00에 조회하려면 자동 조회 시각을 **0시(=KST 09:00)**로 설정
- 쿠팡 조회는 데이터센터 IP에서 차단될 확률이 높음 — playwright를 쓰려면 Docker 이미지에
  `RUN pip install playwright && playwright install --with-deps chromium` 추가 (이미지가 ~1GB로 커짐).
  차단이 계속되면 쿠팡 상품은 집 PC에서 돌리는 게 현실적
- 텔레그램 알림은 서버에서도 그대로 동작
