# 네이버 순위추적기 v1.1 (최소버전)

개발명령서 v1.1 기반. CoupRank Pro와 완전 별도 앱 (코드/DB/실행파일 독립).

## 실행

```
pip install -r requirements.txt
python main.py
```

첫 실행 후 메인화면 상단에 네이버 개발자센터 Client ID / Secret 입력 → 설정 저장.

## 콘솔 확인 (빌드 순서 §9)

```
python naver_api.py 검색키워드   # API 응답에 productId/mallName 오는지 눈으로 확인
python tracker.py                # 등록된 상품 전체 조회를 콘솔에서 실행
```

## 구조

```
main.py          # 엔트리 + APScheduler 기동 (기본 매일 09:00)
db.py            # SQLite 초기화 + CRUD + settings 헬퍼
naver_api.py     # API 호출 + 일일 사용량 카운트 (한도 24,000)
tracker.py       # 매칭 알고리즘 + 조회 루프 + nvmid 자동 승격
gui.py           # 1화면 GUI + 등록 팝업
rank_tracker.db  # SQLite DB (자동 생성, git 제외)
```

## 핵심 동작 — nvmid 자동 승격 (§3)

등록 시 상품명 + (선택)몰명 + 키워드만 입력. 첫 조회에서 이름(+몰명)으로 매칭되면
그 항목의 `productId`를 `nvmid`로 자동 저장 → 2회차부터 정밀 매칭.
