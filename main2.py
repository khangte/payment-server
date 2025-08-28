# payment-server/main2.py
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import httpx, hmac, hashlib, base64, asyncio, os, time

app = FastAPI(title="Payment Server v2 (webhook)")

PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET")

class PaymentInitV2(BaseModel):
    version: str = "v2"
    tx_id: str
    order_id: int
    user_id: int
    amount: int
    callback_url: str

def _sign(body_bytes: bytes) -> str:
    mac = hmac.new(PAYMENT_WEBHOOK_SECRET.encode("utf-8"), body_bytes, hashlib.sha256).digest()
    return base64.b64encode(mac).decode("ascii")

async def _send_webhook(callback_url: str, payload: dict, event: str):
    body = (await _json_bytes(payload))
    headers = {
        "X-Payment-Signature": _sign(body),
        "X-Payment-Event": event,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
        await client.post(callback_url, content=body, headers=headers)

async def _json_bytes(data: dict) -> bytes:
    import json
    return json.dumps(data, ensure_ascii=False).encode("utf-8")

@app.post("/api/v2/payments")
async def start_payment_v2(req: PaymentInitV2, bg: BackgroundTasks):
    """
    결제요청 초기화(v2):
    - 콜백 URL을 받아 백그라운드에서 결과를 웹훅으로 전송
    """
    # 실제 PG 연동/검증/3DS 등은 생략, 여기서는 성공 시뮬레이션
    payment_id = f"pay_{req.tx_id}"
    payload = {
        "payment_id": payment_id,
        "order_id": req.order_id,
        "tx_id": req.tx_id,
        "amount": req.amount,
        "completed_at": int(time.time()),
    }

    async def _simulate_and_callback():
        await asyncio.sleep(3)  # 처리 지연 시뮬
        # 성공 콜백 (실패 시 "payment.failed")
        await _send_webhook(req.callback_url, payload, event="payment.completed")

    bg.add_task(_simulate_and_callback)
    return {"ok": True, "tx_id": req.tx_id, "status": "PENDING"}
