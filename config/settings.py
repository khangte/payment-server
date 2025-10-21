"""
Payment Server 설정 관리
환경변수 및 전역 설정을 관리합니다.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ---- 환경변수 설정 ----
WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "")
SERVICE_AUTH_TOKEN = os.getenv("SERVICE_AUTH_TOKEN", "")

# ---- 서버 설정 ----
SERVER_TITLE = "Payment Server v3 (webhook_auto_complete)"
LOG_LEVEL = "INFO"
