"""
웹훅 재시도 로직 테스트 스크립트
"""
import asyncio
import logging
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.payment_utils import post_webhook

# 로깅 설정
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("test_webhook_retry")

async def test_webhook_retry():
    """웹훅 재시도 로직 테스트"""
    
    # 테스트용 페이로드
    test_payload = {
        "version": "v2",
        "payment_id": "pay_test_123",
        "order_id": 12345,
        "tx_id": "test_123",
        "user_id": 1,
        "amount": 10000,
        "status": "PAYMENT_COMPLETED",
        "created_at": "2024-01-01T00:00:00Z",
        "confirmed_at": "2024-01-01T00:00:00Z",
    }
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "정상 URL (200 응답)",
            "url": "https://httpbin.org/status/200",
            "should_succeed": True
        },
        {
            "name": "서버 에러 (500 응답) - 재시도 후 실패",
            "url": "https://httpbin.org/status/500",
            "should_succeed": False
        },
        {
            "name": "클라이언트 에러 (400 응답) - 재시도 안함",
            "url": "https://httpbin.org/status/400",
            "should_succeed": False
        },
        {
            "name": "존재하지 않는 URL - 연결 실패 재시도",
            "url": "https://nonexistent-domain-12345.com/webhook",
            "should_succeed": False
        }
    ]
    
    for test_case in test_cases:
        print(f"\n=== {test_case['name']} ===")
        try:
            await post_webhook(test_case['url'], test_payload)
            print(f"✅ 성공: {test_case['url']}")
        except Exception as e:
            print(f"❌ 실패: {test_case['url']} - {str(e)}")
        
        # 테스트 간 잠시 대기
        await asyncio.sleep(1)

if __name__ == "__main__":
    print("웹훅 재시도 로직 테스트 시작...")
    asyncio.run(test_webhook_retry())
    print("\n테스트 완료!")
