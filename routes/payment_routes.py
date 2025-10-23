"""
Payment Server API 라우트들
FastAPI 엔드포인트를 정의합니다.
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException

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
        "payments": all_payments,
    }


@router.post("/api/v2/payments", response_model=PaymentCreateResponse)
async def start_payment_v2(req: PaymentInitV2):
    """
    결제 생성(v2): callback_url은 운영서버의 웹훅 수신 엔드포인트
    (ex. /api/orders/payment/webhook/v2/{tx_id})
    자동으로 결제 완료 처리됩니다.
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
    
    # 자동결제 처리 전 2초 대기
    await asyncio.sleep(2)
    log.info("자동결제 처리 시작 - 2초 대기 완료")
    
    # 자동으로 결제 완료 처리
    try:
        # 결제 완료로 상태 변경
        confirmed_at = now_iso()
        payment_storage.update_payment(payment_id, {
            "status": "PAYMENT_COMPLETED",
            "confirmed_at": confirmed_at
        })
        
        log.info(f"자동 결제 완료 처리: {payment_id}, 주문ID: {req.order_id}, 상태: PAYMENT_COMPLETED")
        
        # 웹훅 전송용 페이로드 생성
        updated_payment = payment_storage.get_payment(payment_id)
        webhook_payload = create_webhook_payload(updated_payment)
        
        # 웹훅 전송
        callback_url = str(req.callback_url)
        log.info(f"웹훅 전송 시도: {callback_url}")
        
        await post_webhook(callback_url, webhook_payload, event="payment.completed")
        log.info(f"웹훅 전송 완료: {callback_url}")
        
        # 웹훅 전송 성공 시에만 PAYMENT_COMPLETED 반환
        return {"ok": True, "tx_id": req.tx_id, "status": "PAYMENT_COMPLETED", "payment_id": payment_id}
        
    except Exception as e:
        log.error(f"자동 결제 완료 처리 실패: {e}")
        # 웹훅 전송 실패 시 결제 취소로 상태 변경
        payment_storage.update_payment(payment_id, {
            "status": "PAYMENT_CANCELLED"
        })
        log.info(f"웹훅 실패로 결제 취소 처리: {payment_id}, 주문ID: {req.order_id}, 상태: PAYMENT_CANCELLED")
        return {"ok": True, "tx_id": req.tx_id, "status": "PAYMENT_CANCELLED", "payment_id": payment_id}


@router.post("/api/v2/confirm-payment", response_model=PaymentConfirmResponse)
async def confirm_payment_v2(req: PaymentConfirmRequest):
    """
    결제 확인 버튼을 눌러서 결제를 완료하는 엔드포인트
    """
    payment_id = req.payment_id
    
    payment = payment_storage.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="결제 ID를 찾을 수 없습니다")
    
    if payment["status"] != "PENDING":
        raise HTTPException(status_code=400, detail="이미 처리된 결제입니다")
    
    # 결제 완료로 상태 변경
    confirmed_at = now_iso()
    payment_storage.update_payment(payment_id, {
        "status": "PAYMENT_COMPLETED",
        "confirmed_at": confirmed_at
    })
    
    log.info(f"결제 완료 처리: {payment_id}, 주문ID: {payment['order_id']}, 상태: PAYMENT_COMPLETED")
    
    # 웹훅 전송
    try:
        updated_payment = payment_storage.get_payment(payment_id)
        webhook_payload = create_webhook_payload(updated_payment)
        
        callback_url = payment["callback_url"]
        log.info(f"웹훅 전송 시도: {callback_url}")
        
        await post_webhook(callback_url, webhook_payload, event="payment.completed")
        log.info(f"웹훅 전송 완료: {callback_url}")
        
    except Exception as e:
        log.error(f"웹훅 전송 실패: {e}")
        # 웹훅 실패 시 결제 취소 처리
        payment_storage.update_payment(payment_id, {
            "status": "PAYMENT_CANCELLED"
        })
        log.info(f"웹훅 실패로 결제 취소 처리: {payment_id}, 주문ID: {payment['order_id']}, 상태: PAYMENT_CANCELLED")
    
    return {
        "ok": True,
        "payment_id": payment_id,
        "status": "PAYMENT_COMPLETED",
        "confirmed_at": confirmed_at
    }
