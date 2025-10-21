"""
Payment Server Pydantic 모델들
API 요청/응답 스키마를 정의합니다.
"""
from pydantic import BaseModel, Field, AnyHttpUrl
from typing import Literal


class PaymentInitV2(BaseModel):
    """결제 초기화 요청 모델"""
    version: Literal["v2"] = "v2"
    tx_id: str
    order_id: int
    user_id: int
    amount: int
    callback_url: AnyHttpUrl = Field(
        ..., description="운영서버 웹훅 수신 URL (예: https://ops/api/orders/payment/webhook/v2/{tx_id})"
    )


class PaymentCreateResponse(BaseModel):
    """결제 생성 응답 모델"""
    ok: bool = True
    tx_id: str
    status: Literal["PENDING", "PAYMENT_COMPLETED"] = "PENDING"
    payment_id: str


class PaymentConfirmRequest(BaseModel):
    """결제 확인 요청 모델"""
    payment_id: str = Field(..., description="결제 ID")


class PaymentConfirmResponse(BaseModel):
    """결제 확인 응답 모델"""
    ok: bool = True
    payment_id: str
    status: Literal["PENDING", "PAYMENT_COMPLETED"]
    confirmed_at: str


class PaymentData(BaseModel):
    """결제 데이터 모델 (내부 저장용)"""
    payment_id: str
    order_id: int
    tx_id: str
    user_id: int
    amount: int
    status: Literal["PENDING", "PAYMENT_COMPLETED"]
    created_at: str
    confirmed_at: str | None
    callback_url: str
