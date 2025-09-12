# Payment Server v3 (Auto-Complete Webhook)

결제 서버 v3는 자동 완료 처리와 웹훅 기반의 결제 처리 시스템입니다. 결제 생성 시 자동으로 완료 처리되며, 완료 시 운영서버로 웹훅을 전송합니다.

## 📁 파일 구조

- `main.py` - FastAPI 기반 결제 서버 v3 (자동 완료 + 웹훅)
- `streamlit_app.py` - Streamlit 기반 결제 관리 콘솔 v3

## 🚀 주요 기능

### main.py (결제 서버 v3)
- **자동 결제 생성**: `POST /api/v2/payments` - 결제 생성과 동시에 자동 완료 처리
- **웹훅 전송**: 자동 완료 시 운영서버로 HMAC-SHA256 서명된 웹훅 전송
- **결제 목록**: `GET /api/v2/pending-payments` - 모든 결제 현황 조회
- **수동 완료**: `POST /api/v2/confirm-payment` - 필요시 수동으로 결제 완료 처리

### streamlit_app.py (관리 콘솔)
- **결제 생성**: 웹 UI를 통한 새로운 결제 요청 생성 (자동 완료)
- **결제 관리**: 대기 중/완료/실패 상태별 결제 목록 조회
- **실시간 모니터링**: 5초 자동 새로고침 및 실시간 상태 업데이트
- **자동 완료 표시**: 결제 생성 시 자동으로 완료 처리됨을 표시

## 🔧 환경 설정

### 환경 변수 (.env)
```env
PAYMENT_WEBHOOK_SECRET=your_webhook_secret_key
SERVICE_AUTH_TOKEN=your_auth_token  # 선택사항
```

### 의존성 설치
```bash
pip install -r requirements.txt
```

## 🏃‍♂️ 실행 방법

### 방법 1: Docker Compose 사용 (권장)
```bash
# 1. 환경 변수 설정
echo "PAYMENT_WEBHOOK_SECRET=your_secret_key" > .env

# 2. 서비스 실행
docker-compose up -d

# 3. 서비스 확인
# - FastAPI 서버: http://localhost:9002
# - Streamlit 콘솔: http://localhost:8502
# - API 문서: http://localhost:9002/docs

# 4. 로그 확인
docker-compose logs -f

# 5. 서비스 중지
docker-compose down
```

### 방법 2: 로컬 Python 실행
```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
export PAYMENT_WEBHOOK_SECRET=your_secret_key

# 3. FastAPI 서버 실행 (포트 9002)
python main.py
# 또는
uvicorn main:app --host 0.0.0.0 --port 9002 --reload

# 4. 새 터미널에서 Streamlit 콘솔 실행 (포트 8501)
streamlit run streamlit_app.py
```

## 📡 API 엔드포인트

### 결제 생성
```http
POST /api/v2/payments
Content-Type: application/json

{
  "version": "v2",
  "tx_id": "tx_1001",
  "order_id": 123,
  "user_id": 1,
  "amount": 1000,
  "callback_url": "https://ops/api/orders/payment/webhook/v2/tx_1001"
}
```

**응답 (웹훅 전송 성공):**
```json
{
  "ok": true,
  "tx_id": "tx_1001",
  "status": "PAYMENT_COMPLETED",
  "payment_id": "pay_tx_1001"
}
```

**응답 (웹훅 전송 실패):**
```json
{
  "ok": true,
  "tx_id": "tx_1001",
  "status": "PENDING",
  "payment_id": "pay_tx_1001"
}
```

### 결제 완료
```http
POST /api/v2/confirm-payment
Content-Type: application/json

{
  "payment_id": "pay_tx_1001"
}
```

**응답:**
```json
{
  "ok": true,
  "payment_id": "pay_tx_1001",
  "status": "PAYMENT_COMPLETED",
  "confirmed_at": "2024-01-01T12:00:00Z"
}
```

### 결제 목록 조회
```http
GET /api/v2/pending-payments
```

**응답:**
```json
{
  "pending_count": 2,
  "completed_count": 5,
  "payments": {
    "pay_tx_1001": {
      "payment_id": "pay_tx_1001",
      "order_id": 123,
      "tx_id": "tx_1001",
      "user_id": 1,
      "amount": 1000,
      "status": "PENDING",
      "created_at": "2024-01-01T12:00:00Z",
      "confirmed_at": null,
      "callback_url": "https://ops/api/orders/payment/webhook/v2/tx_1001"
    }
  }
}
```

## 🔐 웹훅 보안

웹훅은 HMAC-SHA256 서명을 사용하여 보안을 보장합니다:

### 헤더
- `X-Payment-Event`: `payment.completed`
- `X-Payment-Signature`: HMAC-SHA256 Base64 인코딩된 서명
- `Content-Type`: `application/json`

### 서명 검증
```python
import hmac
import hashlib
import base64

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode('utf-8'), 
        payload, 
        hashlib.sha256
    ).digest()
    expected_b64 = base64.b64encode(expected).decode('ascii')
    return hmac.compare_digest(signature, expected_b64)
```

## 🎯 워크플로우

1. **결제 요청**: 클라이언트가 `POST /api/v2/payments`로 결제 생성
2. **자동 완료**: 결제 생성과 동시에 자동으로 `PAYMENT_COMPLETED` 상태로 변경
3. **웹훅 전송**: 운영서버의 `callback_url`로 웹훅 자동 전송
4. **상태 확인**: 결제 현황에서 완료된 결제 확인 가능
5. **수동 완료**: 필요시 `POST /api/v2/confirm-payment`로 수동 완료 처리 가능

## 🔍 관리 콘솔 기능

### 주요 화면
- **새 결제 요청**: 사이드바에서 새로운 결제 생성 (자동 완료)
- **결제 현황**: 대기 중/완료/실패 상태별 목록
- **자동 완료 표시**: 결제 생성 시 자동으로 완료 처리됨을 표시
- **실시간 모니터링**: 자동 새로고침으로 실시간 상태 확인

### 설정 옵션
- **API Base URL**: 결제 서버 주소 (기본: http://localhost:9002)
- **인증 토큰**: SERVICE_AUTH_TOKEN (선택사항)
- **타임아웃**: API 요청 타임아웃 설정 (기본: 60초)
- **자동 새로고침**: 5초마다 자동으로 상태 업데이트

## 🐳 Docker 실행

### Docker Compose 사용 (권장)
```bash
# 1. 환경 변수 파일 생성
cp .env.example .env
# .env 파일을 편집하여 실제 값으로 설정

# 2. 서비스 실행
docker-compose up -d

# 3. 로그 확인
docker-compose logs -f

# 4. 서비스 중지
docker-compose down
```

### Docker 단일 컨테이너 실행
```bash
# Docker 이미지 빌드
docker build -t payment-server:1.0.0 .

# 컨테이너 실행
docker run -d --name payment-container \
    --env-file .env \
    -p 9002:9002 -p 8502:8502 \
    payment-server:1.0.0
```

### 환경 변수 파일 (.env) 예시
```env
# 웹훅 서명을 위한 시크릿 키 (필수)
PAYMENT_WEBHOOK_SECRET=your_webhook_secret_key_here

# 운영서버 인증 토큰 (선택사항)
SERVICE_AUTH_TOKEN=your_auth_token_here

# 로그 레벨 (선택사항)
LOG_LEVEL=INFO
```

## 📝 개발 노트

- **메모리 저장**: 개발 편의를 위해 인메모리 저장소 사용 (운영환경에서는 DB 연동 필요)
- **자동 완료**: 결제 생성 시 자동으로 완료 처리되어 즉시 웹훅 전송
- **멱등성**: 동일한 `tx_id`로 재요청 시 기존 결제 정보 반환
- **에러 처리**: 웹훅 전송 실패 시에도 결제는 완료 처리됨
- **로깅**: 모든 주요 작업에 대한 상세 로그 기록

## 🔗 관련 문서

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Streamlit 공식 문서](https://docs.streamlit.io/)
- [웹훅 보안 가이드](https://en.wikipedia.org/wiki/HMAC)
