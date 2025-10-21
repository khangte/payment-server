"""
Payment Server 메인 애플리케이션
FastAPI 앱을 생성하고 설정합니다.
"""
import logging
from fastapi import FastAPI

from config.settings import SERVER_TITLE, LOG_LEVEL
from routes.payment_routes import router

# 로깅 설정
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
log = logging.getLogger("main")

# FastAPI 앱 생성
app = FastAPI(title=SERVER_TITLE)

# 라우터 등록
app.include_router(router)

log.info("Payment Server v3 (webhook_auto_complete) 시작됨")
