# 인수인계 문서 — 상품 순위추적기 (네이버 · 쿠팡)

작성일: 2026-07-31 · 저장소: `ehdhks1983-glitch/centumhi-landing` · 브랜치: `claude/new-session-zmt299` · 위치: `naver-rank-tracker/`

---

## 1. 이 프로젝트가 무엇인가

셀러가 자기 상품이 **네이버쇼핑·쿠팡 검색에서 몇 위에 노출되는지 매일 자동으로 추적**하는 웹 앱.
근거 문서: 개발명령서 v1.1 (네이버 순위추적기 최소버전) → 이후 대화로 웹 전환·쿠팡·부가기능 확장.

**차별점 (원 기획의 핵심 2가지 + 확장)**
1. **정밀 매칭** — 상품 ID(네이버 nvmid / 쿠팡 productId·itemId·vendorItemId)로 추적하므로 상품명이 바뀌거나 동명 타셀러가 생겨도 안 흔들림
2. **자동화** — 매일 지정 시각(기본 09:00) 자동 조회, PC를 서버에 올리면 24시간 무인
3. (확장) 실측 검증 · 쿠팡 광고 제외 순위 · 텔레그램 급변 알림

## 2. 개발 이력 (커밋 순서)

| 커밋 | 내용 |
|---|---|
| `262b174` | v1.1 최소버전 (데스크톱 CustomTkinter GUI) — 개발명령서 그대로 |
| `cf04fb4` | **웹 전환** — GUI 삭제, FastAPI + 브라우저 화면으로 교체 |
| `1bdf0c5` | 코드 점검 결함 7건 수정 (동시실행 잠금, 커넥션 누수, 절전 유예, 로그 상한 등) |
| `a7f70c1` | **쿠팡 채널 추가** — 검색 페이지 수집, 링크 ID 파싱, 광고 제외 순위 |
| `ba8fbbb` | 실측 검증 + 쿠팡 브라우저 폴백 + 텔레그램 급변 알림 |

## 3. 아키텍처 / 파일 지도

```
브라우저(static/index.html) ←폴링→ FastAPI(webapp.py) → tracker.py(조회 루프)
                                                          ├ naver_api.py  (네이버 공식 API)
                                                          ├ naver_web.py  (네이버 실측·선택)
                                                          ├ coupang.py    (쿠팡 페이지 수집, 403→browser.py 폴백)
                                                          └ alerts.py     (텔레그램)
main.py = APScheduler(매일 자동) + uvicorn 기동          db.py = SQLite (rank_tracker.db)
```

- **main.py** — 엔트리. `python main.py` → http://localhost:8000. 환경변수 `HOST`/`PORT`. 절전으로 놓친 스케줄은 6시간 유예 내 실행.
- **webapp.py** — REST API. 조회는 백그라운드 스레드, 로그는 메모리 2,000줄 상한 + 커서 폴링.
- **tracker.py** — (활성 상품×키워드) 순차 조회. 전역 `run_lock`으로 자동/수동 동시 실행 차단. 에러는 키워드 단위 스킵, 한도 도달 시 그날 중단. **앱은 절대 죽지 않는 것이 유일한 불변 조건.**
- **db.py** — 커넥션은 매 사용 후 close. `init_db()`가 구버전 DB에 컬럼 자동 추가(마이그레이션): `products.channel/ext_ids`, `rank_history.real_rank`.
- **coupang.py** — 페이지당 72개, 2.5초 간격 저강도. 광고(`ad-badge`) 제외 순위. 파싱 0건이면 `coupang_debug.html` 덤프.
- **browser.py** — Playwright 헬퍼(선택 의존성). 크로미움 경로 강제: 환경변수 `RANKTRACKER_CHROMIUM`.
- **alerts.py** — 전일 대비 기준(기본 10위) 이상 변동만 모아 1건 전송. 같은 날 재조회는 재알림 없음.

## 4. 핵심 로직 — 매칭 우선순위

**네이버**: ① nvmid 일치 → `nvmid` ② 이름(+몰명) 정규화 완전일치 → `name` + **nvmid 자동 승격**(첫 조회 때 ID 확보, 이후 정밀) ③ 미발견 `not_found`
**쿠팡**: ① vendorItemId > itemId > productId 순 일치 → `id` (링크 등록 시 첫 조회부터) ② 이름 일치 → `name` + ID 자동 확보 ③ `not_found`
정규화 = HTML 태그 제거 + 엔티티 해제 + 공백 압축 + 소문자. **이름 매칭은 완전일치**라 노출 상품명과 똑같이 등록해야 함 (의도된 설계).

## 5. 설치 / 실행

```bash
pip install -r requirements.txt
python main.py                      # → http://localhost:8000
# 선택 기능(실측 검증·쿠팡 403 우회):
pip install playwright && playwright install chromium
```

콘솔 단독 확인: `python naver_api.py 키워드` / `python coupang.py 키워드` / `python tracker.py`

## 6. 설정 (settings 테이블 키)

| 키 | 용도 |
|---|---|
| `client_id` / `client_secret` | 네이버 개발자센터 검색 API 키 (developers.naver.com, 무료) |
| `check_hour` | 자동 조회 시각(시), 기본 9 |
| `verify_real` | '1'이면 네이버 실측 검증 ON (playwright 필요) |
| `alert_threshold` | 급변 알림 기준(위), 기본 10 |
| `telegram_token` / `telegram_chat_id` | 텔레그램 봇 (@BotFather로 생성 / ID는 @userinfobot) |
| `usage:YYYY-MM-DD` | 일일 API 사용량 — 날짜 키라 자정에 자동 리셋, 한도 24,000 |

## 7. 테스트

`tests/` 폴더에 검증 스크립트 6종 (총 54건, 모두 통과 상태로 인계):

```bash
python tests/run_all.py          # 전체 실행
```

- `verify_v11.py` — 원 명령서 완료판정 (승격·UPSERT·에러 스킵)
- `test_web2.py` — 웹 API E2E + 점검 수정 회귀 (잠금·로그 상한·커넥션)
- `test_multichannel.py` — 쿠팡 매칭·마이그레이션·혼합 조회
- `test_stage1.py` — 네이버 실측 (픽스처 파싱·이력 병기)
- `test_stage2.py` — 쿠팡 403 폴백 (**실제 Chromium 구동 E2E** — 로컬 403 서버로 차단 재현)
- `test_stage3.py` — 텔레그램 알림 (문구·합산 전송·중복 방지)

## 8. ⚠️ 알려진 한계 / 실환경 미검증 항목 (가장 중요)

1. **쿠팡·네이버 실측의 실제 페이지 파싱은 미검증** — 개발 환경이 외부망 차단이라 실제 마크업 기준 픽스처로만 검증함. **PC 첫 실행 때 `python coupang.py 오메가3`으로 실환경 확인 필수.** 실패 시 `coupang_debug.html`/`naver_debug.html`이 자동 저장되므로 그 파일 기준으로 파서(정규식) 조정.
2. 쿠팡은 자동 접속 차단 가능 — 하루 1회는 저강도라 대체로 무난하나, 실브라우저 폴백조차 차단되면 조회 간격·시간대 조정 필요.
3. 네이버 API 순위 ≠ 실제 노출 순위 (오차 존재) — 그래서 실측 검증 기능을 넣음. 오차가 크면 실측을 주 데이터로 쓰는 전환 검토.
4. 이름 매칭은 완전일치 — 부분일치 옵션은 미구현 (오탐 위험 때문에 보류).
5. **웹 서버에 배포 시 인증 없음** — DB에 API Secret 저장되므로 공개 인터넷에 그대로 노출 금지. 리버스 프록시 Basic Auth 등 필수.
6. 알림은 하루 1회 기준 — 같은 날 재조회로 순위가 더 떨어져도 재알림 없음 (스팸 방지 의도).

## 9. 다음 단계 제안 (우선순위 순)

1. PC에서 실환경 스모크 테스트 (네이버 키 발급 → 실제 상품 등록 → 순위 대조)
2. 서버 배포 (Railway/Render 등 + Basic Auth + `HOST=0.0.0.0`) → 24시간 자동화 완성
3. 순위 추이 그래프 (rank_history 데이터는 이미 쌓임 — 화면만 추가)
4. 라이선스/등급제 (타 셀러 판매 시) — 웹 구조라 계정 개념 추가로 자연 확장

## 10. 백업 / 복구

- 코드: 이 저장소 브랜치가 원본. 백업 zip에도 동일 소스 포함.
- **데이터: `rank_tracker.db` 파일 하나가 전부** (상품·키워드·이력·설정). 이 파일만 복사하면 완전 백업/이전 가능. git에는 제외되어 있음(.gitignore).
