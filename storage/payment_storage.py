"""
Payment Server 데이터 저장소
결제 데이터를 메모리에 저장하고 관리합니다.
"""
import logging
from threading import RLock
from typing import Any, Dict, List

log = logging.getLogger("payment_storage")


class PaymentStorage:
    """결제 데이터 저장소 (인메모리)"""
    
    def __init__(self):
        self._payments: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()
    
    def create_payment(self, payment_data: Dict[str, Any]) -> None:
        """결제 데이터 생성"""
        payment_id = payment_data["payment_id"]
        with self._lock:
            # 외부에서 전달된 dict 참조를 그대로 보관하지 않도록 복사 저장
            self._payments[payment_id] = dict(payment_data)
        log.info(f"결제 데이터 생성: {payment_id}")
    
    def get_payment(self, payment_id: str) -> Dict[str, Any] | None:
        """결제 데이터 조회"""
        with self._lock:
            payment = self._payments.get(payment_id)
            return dict(payment) if payment else None
    
    def update_payment(self, payment_id: str, updates: Dict[str, Any]) -> None:
        """결제 데이터 업데이트"""
        with self._lock:
            if payment_id in self._payments:
                self._payments[payment_id].update(updates)
                log.info(f"결제 데이터 업데이트: {payment_id}")
            else:
                log.warning(f"존재하지 않는 결제 ID: {payment_id}")
    
    def get_payments_by_status(self, status: str) -> List[Dict[str, Any]]:
        """상태별 결제 목록 조회"""
        with self._lock:
            return [
                dict(payment)
                for payment in self._payments.values()
                if payment["status"] == status
            ]
    
    def get_all_payments(self) -> Dict[str, Dict[str, Any]]:
        """전체 결제 목록 조회"""
        with self._lock:
            return {payment_id: dict(data) for payment_id, data in self._payments.items()}
    
    def get_payment_count_by_status(self) -> Dict[str, int]:
        """상태별 결제 개수 조회"""
        counts = {"PENDING": 0, "PAYMENT_COMPLETED": 0, "PAYMENT_CANCELLED": 0}
        with self._lock:
            for payment in self._payments.values():
                status = payment["status"]
                if status in counts:
                    counts[status] += 1
        return counts


# 전역 저장소 인스턴스
payment_storage = PaymentStorage()
