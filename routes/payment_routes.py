"""
Payment Server API 라우트들
FastAPI 엔드포인트를 정의합니다.
"""
import asyncio
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException

from models.payment_models import (
    PaymentInitV2, PaymentCreateResponse, 
    PaymentConfirmRequest, PaymentConfirmResponse
)
from utils.payment_utils import (
    now_iso, post_webhook, create_payment_id, create_webhook_payload
)
from storage.payment_storage import payment_storage

log = logging.getLogger("payment_routes")

# 라우터 생성
router = APIRouter()
AUTO_COMPLETE_DELAY_SEC = 2.0

async def _send_terminal_webhook(payment: dict, *, event: str, failure_reason: str | None = None) -> bool:
    """최종 상태 웹훅 전송 (실패해도 호출자 흐름은 유지)."""
    callback_url = payment["callback_url"]
    webhook_payload = create_webhook_payload(payment, failure_reason=failure_reason)
    try:
        log.info(f"웹훅 전송 시도: event={event}, url={callback_url}")
        await post_webhook(callback_url, webhook_payload, event=event)
        log.info(f"웹훅 전송 완료: event={event}, url={callback_url}")
        return True
    except Exception as webhook_error:
        log.error(f"웹훅 전송 실패: event={event}, url={callback_url}, error={webhook_error}")
        return False


async def _auto_complete_payment(payment_id: str) -> None:
    """
    결제 생성 직후 백그라운드에서 자동 완료/취소를 처리한다.
    - delay 후 PENDING 결제를 PAYMENT_COMPLETED로 변경
    - 완료 웹훅 실패 시 PAYMENT_CANCELLED로 전환하고 취소 웹훅 시도
    """
    await asyncio.sleep(AUTO_COMPLETE_DELAY_SEC)

    current_payment = payment_storage.get_payment(payment_id)
    if not current_payment:
        log.warning(f"자동 완료 대상 결제가 존재하지 않음: payment_id={payment_id}")
        return

    # 수동 완료/취소 등으로 이미 상태가 변경된 경우 자동 완료를 건너뛴다.
    if current_payment["status"] != "PENDING":
        log.info(
            f"자동 완료 건너뜀: payment_id={payment_id}, status={current_payment['status']}"
        )
        return

    confirmed_at = now_iso()
    if not payment_storage.update_payment_if_status(
        payment_id,
        "PENDING",
        {"status": "PAYMENT_COMPLETED", "confirmed_at": confirmed_at},
    ):
        log.info(f"자동 완료 건너뜀 (이미 상태 변경됨): payment_id={payment_id}")
        return

    try:
        completed_payment = payment_storage.get_payment(payment_id)
        if not completed_payment:
            raise RuntimeError("completed payment snapshot missing")

        log.info(
            f"자동 결제 완료 처리: payment_id={payment_id}, order_id={completed_payment['order_id']}"
        )
        completed_sent = await _send_terminal_webhook(
            completed_payment, event="payment.completed"
        )
        if not completed_sent:
            raise RuntimeError("payment.completed webhook delivery failed")
    except Exception as e:
        log.error(f"자동 결제 완료 처리 실패: payment_id={payment_id}, error={e}")
        payment_storage.update_payment(payment_id, {"status": "PAYMENT_CANCELLED"})
        cancelled_payment = payment_storage.get_payment(payment_id)
        if cancelled_payment:
            await _send_terminal_webhook(
                cancelled_payment,
                event="payment.cancelled",
                failure_reason=str(e),
            )


@router.get("/health")
async def health():
    """헬스 체크 엔드포인트"""
    return {"ok": True, "service": "payment-v2-webhook", "docs": "/docs"}


@router.get("/api/v2/payments")
async def payments_hint():
    """GET 요청 힌트 (405 노이즈 방지용)"""
    return {
        "ok": True,
        "hint": "Use POST /api/v2/payments with callback_url (webhook v2).",
        "webhook_target_example": "/api/orders/payment/webhook/v2/{tx_id}",
        "dev_list": "/api/v2/pending-payments",
        "manual_confirm": "/api/v2/confirm-payment"
    }


@router.get("/api/v2/pending-payments")
async def list_payments():
    """결제 목록 조회 (개발용)"""
    counts = payment_storage.get_payment_count_by_status()
    all_payments = payment_storage.get_all_payments()
    
    return {
        "pending_count": counts["PENDING"],
        "completed_count": counts["PAYMENT_COMPLETED"],
        "cancelled_count": counts["PAYMENT_CANCELLED"],
        "payments": all_payments,
    }


@router.post("/api/v2/payments", response_model=PaymentCreateResponse)
async def start_payment_v2(req: PaymentInitV2, background_tasks: BackgroundTasks):
    """
    결제 생성(v2): callback_url은 운영서버의 웹훅 수신 엔드포인트
    (ex. /api/orders/payment/webhook/v2/{tx_id})
    생성 요청은 즉시 PENDING 응답을 반환하고,
    완료/웹훅 처리는 백그라운드 태스크에서 처리된다.
    """
    payment_id = create_payment_id(req.tx_id)
    created_at = now_iso()

    # 결제 데이터 생성 (PENDING으로 시작)
    payment_data = {
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
    
    payment_storage.create_payment(payment_data)
    log.info(f"결제 요청 생성: {payment_id}, 주문ID: {req.order_id}, 상태: PENDING")

    background_tasks.add_task(_auto_complete_payment, payment_id)

    return {"ok": True, "tx_id": req.tx_id, "status": "PENDING", "payment_id": payment_id}


@router.post("/api/v2/confirm-payment", response_model=PaymentConfirmResponse)
async def confirm_payment_v2(req: PaymentConfirmRequest):
    """
    결제 확인 버튼을 눌러서 결제를 완료하는 엔드포인트
    """
    payment_id = req.payment_id
    
    payment = payment_storage.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="결제 ID를 찾을 수 없습니다")

    confirmed_at = now_iso()
    if not payment_storage.update_payment_if_status(
        payment_id,
        "PENDING",
        {"status": "PAYMENT_COMPLETED", "confirmed_at": confirmed_at},
    ):
        raise HTTPException(status_code=400, detail="이미 처리된 결제입니다")
    
    log.info(f"결제 완료 처리: {payment_id}, 주문ID: {payment['order_id']}, 상태: PAYMENT_COMPLETED")
    
    final_status = "PAYMENT_COMPLETED"

    # 웹훅 전송
    try:
        updated_payment = payment_storage.get_payment(payment_id)
        completed_sent = await _send_terminal_webhook(updated_payment, event="payment.completed")
        if not completed_sent:
            raise RuntimeError("payment.completed webhook delivery failed")
        
    except Exception as e:
        log.error(f"웹훅 전송 실패: {e}")
        # 웹훅 실패 시 결제 취소 처리
        payment_storage.update_payment(payment_id, {
            "status": "PAYMENT_CANCELLED"
        })
        log.info(f"웹훅 실패로 결제 취소 처리: {payment_id}, 주문ID: {payment['order_id']}, 상태: PAYMENT_CANCELLED")
        cancelled_payment = payment_storage.get_payment(payment_id)
        await _send_terminal_webhook(
            cancelled_payment,
            event="payment.cancelled",
            failure_reason=str(e),
        )
        final_status = "PAYMENT_CANCELLED"
    
    return {
        "ok": True,
        "payment_id": payment_id,
        "status": final_status,
        "confirmed_at": confirmed_at
    }
