# 네이버 순위추적기 v1.1 (웹 버전)

개발명령서 v1.1 기반 · CoupRank Pro와 완전 별도 앱. 데스크톱 GUI 대신
**웹 UI(FastAPI + 브라우저)** 로 동작한다 — 내 PC에서 실행하다가 그대로
서버에 올리면 24시간 자동 조회 서비스가 된다.

## 실행

```
pip install -r requirements.txt
python main.py
```

브라우저에서 **http://localhost:8000** 접속 → 상단에 네이버 개발자센터
Client ID / Secret 입력 → 설정 저장 → 상품 등록 → 지금 조회.

- 호스트/포트 변경: `HOST=0.0.0.0 PORT=8080 python main.py`
- 서버가 떠 있는 동안 매일 지정 시각(기본 09:00)에 자동 조회

## 콘솔 확인 (빌드 순서 §9)

```
python naver_api.py 검색키워드   # API 응답에 productId/mallName 오는지 눈으로 확인
python tracker.py                # 등록된 상품 전체 조회를 콘솔에서 실행
```

## 구조

```
main.py            # 엔트리: APScheduler + uvicorn 웹서버 기동
webapp.py          # FastAPI 라우트 (/api/state, /api/products, /api/check …)
static/index.html  # 브라우저 화면 (1화면 + 등록 팝업)
db.py              # SQLite 초기화 + CRUD + settings 헬퍼
naver_api.py       # API 호출 + 일일 사용량 카운트 (한도 24,000)
tracker.py         # 매칭 알고리즘 + 조회 루프 + nvmid 자동 승격
rank_tracker.db    # SQLite DB (자동 생성, git 제외)
```

## 핵심 동작 — nvmid 자동 승격 (§3)

등록 시 상품명 + (선택)몰명 + 키워드만 입력 (API 호출 0회). 첫 조회에서
이름(+몰명)으로 매칭되면 그 항목의 `productId`를 `nvmid`로 자동 저장 →
2회차부터 정밀 매칭. 상품명이 바뀌거나 동명 타셀러가 생겨도 흔들리지 않는다.

## 보안 주의

`rank_tracker.db`에 API Secret이 저장되므로 외부 서버에 올릴 때는
접속 인증(리버스 프록시 Basic Auth 등)을 앞단에 두고 공개 노출하지 말 것.
