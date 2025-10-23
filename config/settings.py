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

# ---- 웹훅 재시도 설정 ----
WEBHOOK_MAX_RETRIES = int(os.getenv("WEBHOOK_MAX_RETRIES", "3"))
WEBHOOK_RETRY_DELAY = float(os.getenv("WEBHOOK_RETRY_DELAY", "1.0"))
WEBHOOK_TIMEOUT = float(os.getenv("WEBHOOK_TIMEOUT", "10.0"))

# ---- 서버 설정 ----
SERVER_TITLE = "Payment Server v3 (webhook_auto_complete)"
LOG_LEVEL = "INFO"
