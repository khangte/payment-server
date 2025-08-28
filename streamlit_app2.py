# payment-server/streamlit_app2.py
import os
import requests
import json
import streamlit as st
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# 환경변수 불러오기
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:9001")
WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "")

st.set_page_config(page_title="Payment v2 (Webhook) Demo", layout="centered")

st.title("💳 Payment v2 (Webhook) Demo")
st.markdown("---")

st.sidebar.header("환경 설정")
st.sidebar.write(f"**API_BASE_URL:** {API_BASE_URL}")
if WEBHOOK_SECRET:
    st.sidebar.success("WEBHOOK_SECRET 로드 완료")
else:
    st.sidebar.warning("WEBHOOK_SECRET이 설정되지 않았습니다!")

with st.form("pay_v2"):
    st.subheader("새 결제 요청 (Webhook v2)")
    tx_id = st.text_input("TX ID", value="tx_demo_123")
    order_id = st.number_input("Order ID", value=123, step=1)
    user_id = st.number_input("User ID", value=1, step=1)
    amount = st.number_input("Amount", value=1000, step=100)
    callback_url = st.text_input(
        "Callback URL (운영서버)",
        value="http://api.uhok.com:9000/api/orders/payment/webhook/v2/tx_demo_123?t=token"
    )

    submitted = st.form_submit_button("결제요청 (v2)")
    if submitted:
        payload = {
            "version": "v2",
            "tx_id": tx_id,
            "order_id": int(order_id),
            "user_id": int(user_id),
            "amount": int(amount),
            "callback_url": callback_url,
        }
        try:
            url = f"{API_BASE_URL}/api/v2/payments"
            r = requests.post(url, json=payload, timeout=5)
            if r.status_code == 200:
                st.success("✅ 결제 요청이 생성되었습니다!")
                st.code(json.dumps(r.json(), ensure_ascii=False, indent=2), language="json")
            else:
                st.error(f"❌ 결제 요청 실패: {r.status_code}")
                st.text(r.text)
        except Exception as e:
            st.error(f"요청 실패: {e}")

st.markdown("---")
st.caption("환경변수 기반 설정: .env에서 API_BASE_URL, PAYMENT_WEBHOOK_SECRET을 관리하세요.")
