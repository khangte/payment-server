# Payment Server v1

간단한 결제 서버 시스템으로, FastAPI와 Streamlit을 사용하여 구현되었습니다.

## 🚀 주요 기능

- **결제 요청 생성**: 주문 ID와 금액을 입력하여 결제 요청 생성
- **결제 확인**: 대기 중인 결제를 수동으로 완료 처리
- **자동 만료**: 20초 후 대기 중인 결제 자동 제거
- **실시간 현황**: Streamlit 웹 인터페이스로 결제 현황 실시간 모니터링
- **상태 추적**: 결제 상태별 분류 및 통계 제공

## 📁 프로젝트 구조

```
payment-server/
├── main.py              # FastAPI 서버 (v1)
├── streamlit_app.py     # Streamlit 웹 인터페이스
├── requirements.txt     # Python 의존성
├── Dockerfile          # Docker 컨테이너 설정
├── Docker명령어.md     # Docker 사용 가이드
└── README.md           # 프로젝트 문서
```

## 🛠️ 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 서버 실행

```bash
# FastAPI 서버 실행 (포트 9001)
python main.py

# 또는 uvicorn으로 실행
uvicorn main:app --host 0.0.0.0 --port 9001 --reload
```

### 3. 웹 인터페이스 실행

```bash
# Streamlit 웹 인터페이스 실행 (포트 8501)
streamlit run streamlit_app.py
```

## 📡 API 엔드포인트

### 결제 요청
- **POST** `/pay`
  - 결제 요청을 생성하고 대기 상태로 저장
  - 20초 후 자동 만료

### 결제 확인
- **POST** `/confirm-payment`
  - 대기 중인 결제를 완료 처리

### 상태 조회
- **GET** `/payment-status/{payment_id}`
  - 특정 결제의 상태 확인

- **GET** `/pending-payments`
  - 모든 결제 현황 조회

### 유틸리티
- **GET** `/healthz`
  - 서버 헬스 체크

- **GET** `/debug/pending-payments`
  - 디버깅용 상세 정보

- **GET** `/expired-payments-info`
  - 만료된 결제 정보 조회

## 💳 결제 플로우

1. **결제 요청**: 클라이언트가 주문 ID와 금액으로 결제 요청
2. **대기 상태**: 결제가 `PENDING` 상태로 저장됨
3. **수동 확인**: 관리자가 웹 인터페이스에서 결제 완료 버튼 클릭
4. **완료 처리**: 결제 상태가 `PAYMENT_COMPLETED`로 변경
5. **자동 정리**: 20초 후 미확인 결제는 자동으로 제거

## 🔧 설정

### 환경 변수
- 서버 포트: 기본값 9001
- 자동 만료 시간: 20초
- 결제 방식: CARD (고정)

### API 서버 URL
- 기본값: `http://localhost:9001`
- `streamlit_app.py`에서 `API_BASE_URL` 변수로 설정 가능

## 📊 웹 인터페이스 기능

### 메인 화면
- **결제 현황**: 대기 중/완료된 결제 목록
- **새 결제 요청**: 주문 ID와 금액 입력 폼
- **통계**: 결제 상태별 개수 및 차트

### 실시간 업데이트
- 새로고침 버튼으로 수동 업데이트
- 결제 완료 시 자동 새로고침
- 한국 시간(KST) 표시

## 🐳 Docker 지원

### Dockerfile 사용
```bash
# 이미지 빌드
docker build -t payment-server-v1 .

# 컨테이너 실행
docker run -p 9001:9001 payment-server-v1
```

### Docker Compose (선택사항)
```yaml
version: '3.8'
services:
  payment-server:
    build: .
    ports:
      - "9001:9001"
    environment:
      - PYTHONUNBUFFERED=1
```

## 🔍 디버깅

### 로그 확인
- 서버 실행 시 상세한 로그 출력
- 결제 생성/확인/조회 과정 추적
- 자동 정리 태스크 상태 모니터링

### 디버그 엔드포인트
- `/debug/pending-payments`: 내부 데이터 구조 확인
- `/expired-payments-info`: 만료 예정/만료된 결제 정보

## 📝 데이터 모델

### PaymentRequest
```json
{
  "order_id": "int",
  "payment_amount": "int"
}
```

### PaymentResponse
```json
{
  "payment_id": "string",
  "order_id": "int",
  "status": "PENDING|PAYMENT_COMPLETED|CANCELLED",
  "payment_amount": "int",
  "method": "string",
  "created_at": "string",
  "confirmed_at": "string|null"
}
```

## 🚨 주의사항

- **메모리 저장**: 결제 데이터는 메모리에 저장되므로 서버 재시작 시 데이터 손실
- **자동 만료**: 20초 후 미확인 결제는 자동으로 제거됨
- **단일 인스턴스**: 현재 버전은 단일 서버 인스턴스에서만 동작
- **인증 없음**: 현재 버전은 인증/권한 관리 기능 없음

## 🔄 업그레이드 가이드

v1에서 v2로 업그레이드하려면:
1. `main2.py` (v2 서버) 사용
2. `streamlit_app2.py` (v2 웹 인터페이스) 사용
3. 웹훅 기반 결제 플로우로 전환

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해주세요.

---

**버전**: v1.0.0  
**최종 업데이트**: 2025-01-02  
**라이선스**: MIT
