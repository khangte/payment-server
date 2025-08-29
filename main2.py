# payment-server/main2.py
# v2 (Webhook 전용)
# - 생성: POST /api/v2/payments  → PENDING 응답
# - 지연 후 웹훅: POST <callback_url>  (ex. /api/orders/payment/webhook/v2/{tx_id})
#   헤더: X-Payment-Signature (HMAC-SHA256 Base64), X-Payment-Event (payment.completed)
# - 참고: .env에는 PAYMENT_WEBHOOK_SECRET만 필요

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, AnyHttpUrl
from typing import Dict, Literal
from datetime import datetime, timezone
import httpx, hmac, hashlib, base64, asyncio, os, json, logging

app = FastAPI(title="Payment Server v2 (webhook)")
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")

# ---- ENV ----
WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "")
CALLBACK_DELAY_SEC = float(os.getenv("PAYMENT_CALLBACK_DELAY", "3"))

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
        "dev_list": "/api/v2/pending-payments"
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
async def start_payment_v2(req: PaymentInitV2, bg: BackgroundTasks):
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

    async def _complete_and_webhook():
        await asyncio.sleep(CALLBACK_DELAY_SEC)

        rec = payments.get(payment_id)
        if not rec:
            return
        if rec["status"] != "PAYMENT_COMPLETED":
            rec["status"] = "PAYMENT_COMPLETED"
            rec["confirmed_at"] = _now_iso()
            payments[payment_id] = rec

        # v2 바디(운영서버 payment_crud가 소비할 필드들)
        payload = {
            "version": "v2",
            "payment_id": rec["payment_id"],
            "order_id": rec["order_id"],
            "tx_id": rec["tx_id"],
            "user_id": rec["user_id"],
            "amount": rec["amount"],              # v2 입력과 동일 키 유지
            "status": rec["status"],              # "PAYMENT_COMPLETED"
            "created_at": rec["created_at"],
            "confirmed_at": rec["confirmed_at"],
            # 필요시 확장: "method": "CARD", "currency": "KRW" 등
        }

        await _post_webhook(rec["callback_url"], payload, event="payment.completed")

    bg.add_task(_complete_and_webhook)
    return {"ok": True, "tx_id": req.tx_id, "status": "PENDING", "payment_id": payment_id}
