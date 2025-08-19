# payment_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from typing import Literal, Dict
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Simple Payment Server")

# 대기 중인 결제를 저장할 딕셔너리
pending_payments: Dict[str, dict] = {}

class PaymentRequest(BaseModel):
    """상점 프로그램에서 보내는 결제 요청"""
    order_id: str = Field(..., description="주문 ID")
    payment_amount: int = Field(..., ge=1, description="결제 금액")

class PaymentResponse(BaseModel):
    """결제 서버가 돌려주는 결제 응답"""
    payment_id: str
    order_id: str
    status: Literal["PENDING", "PAYMENT_COMPLETED", "CANCELLED"]
    payment_amount: int
    method: str
    created_at: str
    confirmed_at: str = None

class PaymentConfirmationRequest(BaseModel):
    """결제 확인 요청"""
    payment_id: str = Field(..., description="결제 ID")

@app.post("/pay", response_model=PaymentResponse)
async def request_payment(req: PaymentRequest):
    """
    결제 요청을 받아서 대기 상태로 저장하는 엔드포인트
    - 결제 확인 버튼을 눌러야 실제 결제가 완료됨
    """
    payment_id = "pay_" + uuid.uuid4().hex[:10]
    method = "CARD"  # 기본값 강제
    created_at = datetime.utcnow().isoformat() + "Z"
    
    # pending_payments에 추가
    pending_payments[payment_id] = {
        "order_id": req.order_id,
        "payment_amount": req.payment_amount,
        "method": method,
        "created_at": created_at,
        "status": "PENDING"
    }
    
    # 디버깅을 위한 로그 출력
    logger.info(f"=== 결제 요청 생성 완료 ===")
    logger.info(f"payment_id: {payment_id}")
    logger.info(f"order_id: {req.order_id}")
    logger.info(f"payment_amount: {req.payment_amount}")
    logger.info(f"현재 pending_payments 상태:")
    for key, value in pending_payments.items():
        logger.info(f"  {key}: {value}")
    logger.info(f"pending_payments 총 개수: {len(pending_payments)}")
    
    return PaymentResponse(
        payment_id=payment_id,
        order_id=req.order_id,
        status="PENDING",
        payment_amount=req.payment_amount,
        method=method,
        created_at=created_at
    )

@app.post("/confirm-payment", response_model=PaymentResponse)
async def confirm_payment(req: PaymentConfirmationRequest):
    """
    결제 확인 버튼을 눌러서 결제를 완료하는 엔드포인트
    """
    payment_id = req.payment_id
    
    # 디버깅을 위한 로그 출력
    logger.info(f"=== 결제 확인 요청 ===")
    logger.info(f"요청된 payment_id: {payment_id}")
    logger.info(f"payment_id 타입: {type(payment_id)}")
    logger.info(f"현재 pending_payments 키들: {list(pending_payments.keys())}")
    logger.info(f"payment_id in pending_payments: {payment_id in pending_payments}")
    
    if payment_id not in pending_payments:
        logger.error(f"결제 ID를 찾을 수 없음: {payment_id}")
        logger.error(f"사용 가능한 payment_id들: {list(pending_payments.keys())}")
        raise HTTPException(status_code=404, detail="결제 ID를 찾을 수 없습니다")
    
    payment = pending_payments[payment_id]
    
    if payment["status"] != "PENDING":
        logger.warning(f"이미 처리된 결제: {payment_id}, 현재 상태: {payment['status']}")
        raise HTTPException(status_code=400, detail="이미 처리된 결제입니다")
    
    # 결제 완료로 상태 변경
    confirmed_at = datetime.utcnow().isoformat() + "Z"
    payment["status"] = "PAYMENT_COMPLETED"
    payment["confirmed_at"] = confirmed_at
    
    logger.info(f"=== 결제 완료 처리 ===")
    logger.info(f"payment_id: {payment_id}")
    logger.info(f"order_id: {payment['order_id']}")
    logger.info(f"상태 변경: PENDING -> PAYMENT_COMPLETED")
    logger.info(f"확인 시간: {confirmed_at}")
    
    return PaymentResponse(
        payment_id=payment_id,
        order_id=payment["order_id"],
        status="PAYMENT_COMPLETED",
        payment_amount=payment["payment_amount"],
        method=payment["method"],
        created_at=payment["created_at"],
        confirmed_at=confirmed_at
    )

@app.get("/payment-status/{payment_id}")
async def get_payment_status(payment_id: str):
    """
    특정 결제의 상태를 확인하는 엔드포인트
    """
    # 디버깅을 위한 로그 출력
    logger.info(f"=== 결제 상태 조회 요청 ===")
    logger.info(f"요청된 payment_id: {payment_id}")
    logger.info(f"payment_id 타입: {type(payment_id)}")
    logger.info(f"현재 pending_payments: {pending_payments}")
    logger.info(f"pending_payments 키들: {list(pending_payments.keys())}")
    logger.info(f"payment_id in pending_payments: {payment_id in pending_payments}")
    
    if payment_id not in pending_payments:
        logger.error(f"결제 ID를 찾을 수 없음: {payment_id}")
        logger.error(f"사용 가능한 payment_id들: {list(pending_payments.keys())}")
        raise HTTPException(status_code=404, detail="결제 ID를 찾을 수 없습니다")
    
    payment = pending_payments[payment_id]
    logger.info(f"결제 정보 찾음: {payment}")
    
    return {
        "payment_id": payment_id,
        "status": payment["status"],
        "order_id": payment["order_id"],
        "payment_amount": payment["payment_amount"],
        "method": payment["method"],
        "created_at": payment["created_at"],
        "confirmed_at": payment.get("confirmed_at")
    }

@app.get("/pending-payments")
async def list_pending_payments():
    """
    대기 중인 모든 결제 목록을 보여주는 엔드포인트
    """
    logger.info(f"=== 전체 결제 현황 조회 ===")
    logger.info(f"현재 pending_payments 상태:")
    for key, value in pending_payments.items():
        logger.info(f"  {key}: {value}")
    
    pending_count = len([p for p in pending_payments.values() if p["status"] == "PENDING"])
    completed_count = len([p for p in pending_payments.values() if p["status"] == "PAYMENT_COMPLETED"])
    
    logger.info(f"대기 중인 결제: {pending_count}개")
    logger.info(f"완료된 결제: {completed_count}개")
    logger.info(f"전체 결제: {len(pending_payments)}개")
    
    return {
        "pending_count": pending_count,
        "completed_count": completed_count,
        "payments": pending_payments
    }

@app.get("/debug/pending-payments")
async def debug_pending_payments():
    """
    디버깅을 위한 pending_payments 상세 정보
    """
    logger.info(f"=== 디버깅: pending_payments 상세 정보 ===")
    
    debug_info = {
        "total_count": len(pending_payments),
        "keys": list(pending_payments.keys()),
        "key_types": [type(key).__name__ for key in pending_payments.keys()],
        "detailed_payments": {}
    }
    
    for key, value in pending_payments.items():
        debug_info["detailed_payments"][key] = {
            "key_type": type(key).__name__,
            "key_value": str(key),
            "data": value
        }
    
    logger.info(f"디버깅 정보: {debug_info}")
    return debug_info

@app.get("/healthz")
async def healthz():
    """헬스체크"""
    return {"ok": True}
