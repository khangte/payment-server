"""
Payment Server 유틸리티 함수들
공통으로 사용되는 헬퍼 함수들을 정의합니다.
"""
import hmac
import hashlib
import base64
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any
import httpx

from config.settings import WEBHOOK_SECRET, SERVICE_AUTH_TOKEN, WEBHOOK_MAX_RETRIES, WEBHOOK_RETRY_DELAY, WEBHOOK_TIMEOUT

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
    웹훅 전송 (재시도 로직 포함)
    
    Args:
        url: 웹훅 수신 URL
        payload: 전송할 데이터
        event: 이벤트 타입 (기본값: payment.completed)
    
    Raises:
        Exception: 모든 재시도 실패 시
    """
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Payment-Event": event,                     # <- payment_router 기대값
        "X-Payment-Signature": sign_webhook(raw),     # <- payment_router 기대값
    }
    if SERVICE_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {SERVICE_AUTH_TOKEN}"

    last_exception = None
    
    for attempt in range(WEBHOOK_MAX_RETRIES + 1):  # 0부터 시작하므로 +1
        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                resp = await client.post(url, content=raw, headers=headers)
                
                if attempt > 0:
                    log.info(f"[webhook] 재시도 {attempt} 성공: {url} {resp.status_code}")
                else:
                    log.info(f"[webhook] -> {url} {resp.status_code}")
                
                # 응답 상태 코드 확인
                if resp.status_code >= 400:
                    error_msg = f"HTTP {resp.status_code}: {resp.text}"
                    log.error(f"[webhook] HTTP 에러: {url} {resp.status_code} - {resp.text}")
                    
                    # 4xx 에러는 재시도하지 않음 (클라이언트 에러)
                    if 400 <= resp.status_code < 500:
                        raise Exception(error_msg)
                    
                    # 5xx 에러는 재시도 가능
                    last_exception = Exception(error_msg)
                    if attempt < WEBHOOK_MAX_RETRIES:
                        log.warning(f"[webhook] 서버 에러로 재시도 예정: {url} (시도 {attempt + 1}/{WEBHOOK_MAX_RETRIES + 1})")
                        await asyncio.sleep(WEBHOOK_RETRY_DELAY * (2 ** attempt))  # 지수 백오프
                        continue
                    else:
                        raise last_exception
                else:
                    # 성공
                    return
                    
        except httpx.ConnectError as e:
            last_exception = Exception(f"연결 실패: {str(e)}")
            log.error(f"[webhook] 연결 실패: {url} - {str(e)}")
            
            if attempt < WEBHOOK_MAX_RETRIES:
                log.warning(f"[webhook] 연결 실패로 재시도 예정: {url} (시도 {attempt + 1}/{WEBHOOK_MAX_RETRIES + 1})")
                await asyncio.sleep(WEBHOOK_RETRY_DELAY * (2 ** attempt))  # 지수 백오프
                continue
            else:
                raise last_exception
                
        except httpx.TimeoutException as e:
            last_exception = Exception(f"타임아웃: {str(e)}")
            log.error(f"[webhook] 타임아웃: {url} - {str(e)}")
            
            if attempt < WEBHOOK_MAX_RETRIES:
                log.warning(f"[webhook] 타임아웃으로 재시도 예정: {url} (시도 {attempt + 1}/{WEBHOOK_MAX_RETRIES + 1})")
                await asyncio.sleep(WEBHOOK_RETRY_DELAY * (2 ** attempt))  # 지수 백오프
                continue
            else:
                raise last_exception
                
        except Exception as e:
            last_exception = e
            log.error(f"[webhook] 기타 에러: {url} - {str(e)}")
            
            if attempt < WEBHOOK_MAX_RETRIES:
                log.warning(f"[webhook] 에러로 재시도 예정: {url} (시도 {attempt + 1}/{WEBHOOK_MAX_RETRIES + 1})")
                await asyncio.sleep(WEBHOOK_RETRY_DELAY * (2 ** attempt))  # 지수 백오프
                continue
            else:
                raise last_exception
    
    # 모든 재시도 실패
    log.error(f"[webhook] 모든 재시도 실패: {url} (총 {WEBHOOK_MAX_RETRIES + 1}회 시도)")
    if last_exception is None:
        raise Exception("웹훅 전송 실패: 알 수 없는 오류")
    raise last_exception


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
