# payment-server/main2.py
# v2 (Webhook 전용)
# - 생성: POST /api/v2/payments  → PENDING 응답
# - 수동 완료: POST /api/v2/confirm-payment → PAYMENT_COMPLETED 응답
# - 웹훅: POST <callback_url>  (ex. /api/orders/payment/webhook/v2/{tx_id})
#   헤더: X-Payment-Signature (HMAC-SHA256 Base64), X-Payment-Event (payment.completed)
# - 참고: .env에는 PAYMENT_WEBHOOK_SECRET만 필요

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, AnyHttpUrl
from typing import Dict, Literal
from datetime import datetime, timezone
import httpx, hmac, hashlib, base64, os, json, logging
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Payment Server v2 (webhook)")
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")

# ---- ENV ----
WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "")

# (옵션) 운영서버에서 Authorization 검사한다면 Bearer 토큰 전송
SERVICE_AUTH_TOKEN = os.getenv("SERVICE_AUTH_TOKEN", "")

# ---- In-memory (개발 편의) ----
payments: Dict[str, Dict] = {}

# ---- Models ----
class PaymentInitV2(BaseModel):
    version: Literal["v2"] = "v2"
    tx_id: str
    order_id: int
    user_id: int
    amount: int
    callback_url: AnyHttpUrl = Field(
        ..., description="운영서버 웹훅 수신 URL (예: https://ops/api/orders/payment/webhook/v2/{tx_id})"
    )

class PaymentCreateResponse(BaseModel):
    ok: bool = True
    tx_id: str
    status: Literal["PENDING", "PAYMENT_COMPLETED"] = "PENDING"
    payment_id: str

class PaymentConfirmRequest(BaseModel):
    payment_id: str = Field(..., description="결제 ID")

class PaymentConfirmResponse(BaseModel):
    ok: bool = True
    payment_id: str
    status: Literal["PENDING", "PAYMENT_COMPLETED"]
    confirmed_at: str

# ---- Utils ----
def _now_iso() -> str:
    # UTC ISO8601 with 'Z'
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _sign(body: bytes) -> str:
    if not WEBHOOK_SECRET:
        raise RuntimeError("PAYMENT_WEBHOOK_SECRET(.env)이 설정되어야 합니다.")
    mac = hmac.new(WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(mac).decode("ascii")

async def _post_webhook(url: str, payload: dict, event: str = "payment.completed") -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Payment-Event": event,                     # <- payment_router 기대값
        "X-Payment-Signature": _sign(raw),            # <- payment_router 기대값
    }
    if SERVICE_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {SERVICE_AUTH_TOKEN}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, content=raw, headers=headers)
        log.info(f"[webhook] -> {url} {resp.status_code}")

# ---- Routes ----
@app.get("/")
async def health():
    return {"ok": True, "service": "payment-v2-webhook", "docs": "/docs"}

@app.get("/api/v2/payments")
async def payments_hint():
    # GET 405 노이즈 방지용 힌트 (스트림릿/툴이 GET을 칠 수 있음)
    return {
        "ok": True,
        "hint": "Use POST /api/v2/payments with callback_url (webhook v2).",
        "webhook_target_example": "/api/orders/payment/webhook/v2/{tx_id}",
        "dev_list": "/api/v2/pending-payments",
        "manual_confirm": "/api/v2/confirm-payment"
    }

@app.get("/api/v2/pending-payments")
async def list_payments():
    pending = {k: v for k, v in payments.items() if v["status"] == "PENDING"}
    completed = {k: v for k, v in payments.items() if v["status"] == "PAYMENT_COMPLETED"}
    return {
        "pending_count": len(pending),
        "completed_count": len(completed),
        "payments": payments,
    }

@app.post("/api/v2/payments", response_model=PaymentCreateResponse)
async def start_payment_v2(req: PaymentInitV2):
    """
    결제 생성(v2): callback_url은 운영서버의 웹훅 수신 엔드포인트
    (ex. /api/orders/payment/webhook/v2/{tx_id})
    """
    payment_id = f"pay_{req.tx_id}"
    created_at = _now_iso()

    # 멱등/저장
    payments[payment_id] = {
        "payment_id": payment_id,
        "order_id": req.order_id,
        "tx_id": req.tx_id,
        "user_id": req.user_id,
        "amount": req.amount,
        "status": "PENDING",
        "created_at": created_at,
        "confirmed_at": None,
        "callback_url": str(req.callback_url),
    }

    log.info(f"결제 요청 생성: {payment_id}, 주문ID: {req.order_id}, 상태: PENDING")
    
    return {"ok": True, "tx_id": req.tx_id, "status": "PENDING", "payment_id": payment_id}

@app.post("/api/v2/confirm-payment", response_model=PaymentConfirmResponse)
async def confirm_payment_v2(req: PaymentConfirmRequest):
    """
    결제 확인 버튼을 눌러서 결제를 완료하는 엔드포인트
    """
    payment_id = req.payment_id
    
    if payment_id not in payments:
        raise HTTPException(status_code=404, detail="결제 ID를 찾을 수 없습니다")
    
    payment = payments[payment_id]
    
    if payment["status"] != "PENDING":
        raise HTTPException(status_code=400, detail="이미 처리된 결제입니다")
    
    # 결제 완료로 상태 변경
    confirmed_at = _now_iso()
    payment["status"] = "PAYMENT_COMPLETED"
    payment["confirmed_at"] = confirmed_at
    
    log.info(f"결제 완료 처리: {payment_id}, 주문ID: {payment['order_id']}, 상태: PAYMENT_COMPLETED")
    
    # 웹훅 전송
    try:
        payload = {
            "version": "v2",
            "payment_id": payment["payment_id"],
            "order_id": payment["order_id"],
            "tx_id": payment["tx_id"],
            "user_id": payment["user_id"],
            "amount": payment["amount"],
            "status": payment["status"],
            "created_at": payment["created_at"],
            "confirmed_at": payment["confirmed_at"],
        }
        
        await _post_webhook(payment["callback_url"], payload, event="payment.completed")
        log.info(f"웹훅 전송 완료: {payment['callback_url']}")
        
    except Exception as e:
        log.error(f"웹훅 전송 실패: {e}")
        # 웹훅 실패해도 결제는 완료 처리됨
    
    return {
        "ok": True,
        "payment_id": payment_id,
        "status": "PAYMENT_COMPLETED",
        "confirmed_at": confirmed_at
    }