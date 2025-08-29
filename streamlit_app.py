import streamlit as st
import requests
import os
import json
from datetime import datetime
import time
from dotenv import load_dotenv

load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="결제 관리 시스템",
    page_icon="💳",
    layout="wide"
)

# API 서버 URL
API_BASE_URL = "http://localhost:9001"

def main():
    st.title("💳 결제 관리 시스템")
    st.markdown("---")
    
    # 사이드바에 새 결제 요청 폼
    with st.sidebar:
        st.header("🆕 새 결제 요청")
        
        with st.form("new_payment"):
            order_id = st.text_input("주문 ID", placeholder="예: ORDER_001")
            payment_amount = st.number_input("결제 금액", min_value=1, value=1000, step=100)
            
            if st.form_submit_button("결제 요청 생성", type="primary"):
                if order_id and payment_amount:
                    create_payment_request(order_id, payment_amount)
                else:
                    st.error("주문 ID와 결제 금액을 모두 입력해주세요.")
    
    # 메인 컨텐츠
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📋 결제 현황")
        
        # 자동 새로고침
        if st.button("🔄 새로고침", key="refresh"):
            st.rerun()
        
        # 결제 현황 조회
        try:
            response = requests.get(f"{API_BASE_URL}/pending-payments")
            if response.status_code == 200:
                data = response.json()
                display_payment_status(data)
            else:
                st.error(f"결제 현황 조회 실패: {response.status_code}")
        except requests.exceptions.ConnectionError:
            st.error("❌ API 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
            st.info("터미널에서 `python main.py` 명령어로 서버를 실행하세요.")
    
    with col2:
        st.header("📊 통계")
        try:
            response = requests.get(f"{API_BASE_URL}/pending-payments")
            if response.status_code == 200:
                data = response.json()
                display_statistics(data)
        except:
            pass

def create_payment_request(order_id: str, payment_amount: int):
    """새로운 결제 요청을 생성합니다."""
    try:
        payload = {
            "order_id": order_id,
            "payment_amount": payment_amount
        }
        
        response = requests.post(f"{API_BASE_URL}/pay", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            st.success(f"✅ 결제 요청이 생성되었습니다!")
            st.info(f"결제 ID: {data['payment_id']}")
            st.rerun()
        else:
            st.error(f"결제 요청 생성 실패: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        st.error("❌ API 서버에 연결할 수 없습니다.")

def display_payment_status(data: dict):
    """결제 현황을 표시합니다."""
    payments = data.get("payments", {})
    
    if not payments:
        st.info("📭 대기 중인 결제가 없습니다.")
        return
    
    # 대기 중인 결제와 완료된 결제를 분리
    pending_payments = {k: v for k, v in payments.items() if v["status"] == "PENDING"}
    completed_payments = {k: v for k, v in payments.items() if v["status"] == "PAYMENT_COMPLETED"}
    
    # 대기 중인 결제 표시
    if pending_payments:
        st.subheader("⏳ 대기 중인 결제")
        for payment_id, payment in pending_payments.items():
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.write(f"**주문 ID:** {payment['order_id']}")
                    st.write(f"**결제 ID:** `{payment_id}`")
                
                with col2:
                    st.write(f"**금액:** {payment['payment_amount']:,}원")
                
                with col3:
                    created_time = datetime.fromisoformat(payment['created_at'].replace('Z', '+00:00'))
                    st.write(f"**생성:** {created_time.strftime('%H:%M:%S')}")
                
                with col4:
                    if st.button("✅ 결제완료", key=f"complete_{payment_id}", type="primary"):
                        confirm_payment(payment_id)
                
                st.divider()
    
    # 완료된 결제 표시
    if completed_payments:
        st.subheader("✅ 완료된 결제")
        for payment_id, payment in completed_payments.items():
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.write(f"**주문 ID:** {payment['order_id']}")
                    st.write(f"**결제 ID:** `{payment_id}`")
                
                with col2:
                    st.write(f"**금액:** {payment['payment_amount']:,}원")
                
                with col3:
                    created_time = datetime.fromisoformat(payment['created_at'].replace('Z', '+00:00'))
                    st.write(f"**생성:** {created_time.strftime('%H:%M:%S')}")
                
                with col4:
                    if payment.get('confirmed_at'):
                        confirmed_time = datetime.fromisoformat(payment['confirmed_at'].replace('Z', '+00:00'))
                        st.write(f"**완료:** {confirmed_time.strftime('%H:%M:%S')}")
                    st.success("✅ 완료됨")
                
                st.divider()

def confirm_payment(payment_id: str):
    """결제를 완료 처리합니다."""
    try:
        payload = {"payment_id": payment_id}
        response = requests.post(f"{API_BASE_URL}/confirm-payment", json=payload)
        
        if response.status_code == 200:
            st.success(f"✅ 결제가 완료되었습니다!")
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"결제 완료 처리 실패: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        st.error("❌ API 서버에 연결할 수 없습니다.")

def display_statistics(data: dict):
    """결제 통계를 표시합니다."""
    pending_count = data.get("pending_count", 0)
    completed_count = data.get("completed_count", 0)
    total_count = data.get("payments", {})
    
    st.metric("⏳ 대기 중", pending_count)
    st.metric("✅ 완료됨", completed_count)
    st.metric("📊 전체", len(total_count))
    
    # 간단한 차트
    if pending_count > 0 or completed_count > 0:
        chart_data = {
            "상태": ["대기 중", "완료됨"],
            "개수": [pending_count, completed_count]
        }
        st.bar_chart(chart_data, x="상태", y="개수")

if __name__ == "__main__":
    main()
