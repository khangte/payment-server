"""
Payment Server 유틸리티 함수들
공통으로 사용되는 헬퍼 함수들을 정의합니다.
"""
import hmac
import hashlib
import base64
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any
import httpx

from config.settings import WEBHOOK_SECRET, SERVICE_AUTH_TOKEN

log = logging.getLogger("payment_utils")


def now_iso() -> str:
    """UTC ISO8601 형식의 현재 시간 반환 (Z suffix)"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sign_webhook(body: bytes) -> str:
    """웹훅 서명 생성 (HMAC-SHA256 Base64)"""
    if not WEBHOOK_SECRET:
        raise RuntimeError("PAYMENT_WEBHOOK_SECRET(.env)이 설정되어야 합니다.")
    mac = hmac.new(WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(mac).decode("ascii")


async def post_webhook(url: str, payload: Dict[str, Any], event: str = "payment.completed") -> None:
    """
    웹훅 전송
    
    Args:
        url: 웹훅 수신 URL
        payload: 전송할 데이터
        event: 이벤트 타입 (기본값: payment.completed)
    
    Raises:
        Exception: 웹훅 전송 실패 시
    """
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Payment-Event": event,                     # <- payment_router 기대값
        "X-Payment-Signature": sign_webhook(raw),     # <- payment_router 기대값
    }
    if SERVICE_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {SERVICE_AUTH_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, content=raw, headers=headers)
            log.info(f"[webhook] -> {url} {resp.status_code}")
            
            # 응답 상태 코드 확인
            if resp.status_code >= 400:
                log.error(f"[webhook] HTTP 에러: {url} {resp.status_code} - {resp.text}")
                raise Exception(f"HTTP {resp.status_code}: {resp.text}")
                
    except httpx.ConnectError as e:
        log.error(f"[webhook] 연결 실패: {url} - {str(e)}")
        raise Exception(f"연결 실패: {str(e)}")
    except httpx.TimeoutException as e:
        log.error(f"[webhook] 타임아웃: {url} - {str(e)}")
        raise Exception(f"타임아웃: {str(e)}")
    except Exception as e:
        log.error(f"[webhook] 기타 에러: {url} - {str(e)}")
        raise


def create_payment_id(tx_id: str) -> str:
    """결제 ID 생성"""
    return f"pay_{tx_id}"


def create_webhook_payload(payment_data: Dict[str, Any]) -> Dict[str, Any]:
    """웹훅 전송용 페이로드 생성"""
    return {
        "version": "v2",
        "payment_id": payment_data["payment_id"],
        "order_id": payment_data["order_id"],
        "tx_id": payment_data["tx_id"],
        "user_id": payment_data["user_id"],
        "amount": payment_data["amount"],
        "status": payment_data["status"],
        "created_at": payment_data["created_at"],
        "confirmed_at": payment_data["confirmed_at"],
    }
