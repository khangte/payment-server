# Payment Server v3 (Webhook Auto Complete)

결제 서버 v3는 자동 완료 처리와 웹훅 기반의 결제 처리 시스템입니다. 결제 생성 시 자동으로 완료 처리되며, 완료 시 운영서버로 웹훅을 전송합니다.

## 구성
- `main.py`: FastAPI 앱
- `routes/payment_routes.py`: 결제 API
- `utils/payment_utils.py`: 웹훅 서명/재시도 로직
- `storage/payment_storage.py`: 인메모리 저장소
- `streamlit_app.py`: 관리 콘솔

## 주요 동작
- `POST /api/v2/payments`: 결제 생성 → 2초 후 자동 완료 → 웹훅 전송
  - 웹훅 실패(4xx 즉시 실패, 5xx/네트워크/타임아웃 재시도) 시 `PAYMENT_CANCELLED`
- `POST /api/v2/confirm-payment`: `PENDING` 결제만 수동 완료 후 웹훅 전송
  - 웹훅 실패 시 저장 상태는 `PAYMENT_CANCELLED`로 변경
- `GET /api/v2/pending-payments`: 전체 결제 목록 + `PENDING/COMPLETED` 카운트 (개발용)
- `GET /health`: 헬스체크

## 워크플로우

1. **결제 요청**: 클라이언트가 `POST /api/v2/payments`로 결제 생성
2. **자동 완료**: 결제 생성과 동시에 자동으로 `PAYMENT_COMPLETED` 상태로 변경
3. **웹훅 전송**: 운영서버의 `callback_url`로 웹훅 자동 전송 (지수 백오프 재시도)
4. **실패 처리**: 모든 재시도 실패 시 결제를 `PAYMENT_CANCELLED`로 전환
5. **상태 확인**: 결제 현황에서 완료/취소 상태 확인 가능
6. **수동 완료**: 필요시 `POST /api/v2/confirm-payment`로 수동 완료 처리 (웹훅 실패 시 취소 처리)


## 환경 변수
```env
PAYMENT_WEBHOOK_SECRET=your_webhook_secret_key  # 필수
SERVICE_AUTH_TOKEN=your_auth_token              # 선택: 웹훅 전송 시 Authorization 헤더
WEBHOOK_MAX_RETRIES=3                           # 기본 3 (총 4회 시도)
WEBHOOK_RETRY_DELAY=1.0                         # 기본 대기(초), 지수 백오프
WEBHOOK_TIMEOUT=10.0                            # 요청 타임아웃(초)
```

## 실행

### Docker Compose
```bash
echo "PAYMENT_WEBHOOK_SECRET=your_secret_key" > .env
docker compose up -d
```

- API: `http://localhost:9002`
- 콘솔: `http://localhost:18002`
- 문서: `http://localhost:9002/docs`

### 로컬 실행
```bash
pip install -r requirements.txt
export PAYMENT_WEBHOOK_SECRET=your_secret_key

uvicorn main:app --host 0.0.0.0 --port 9002 --reload
streamlit run streamlit_app.py --server.port 8502 --server.address 0.0.0.0
```

## 요청 예시
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

## 웹훅 헤더
- `X-Payment-Event`: `payment.completed`
- `X-Payment-Signature`: HMAC-SHA256 Base64 서명
- `Authorization: Bearer <SERVICE_AUTH_TOKEN>` (설정 시)
