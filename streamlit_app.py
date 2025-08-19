import streamlit as st
import requests
import json
from datetime import datetime
import time

# 페이지 설정
st.set_page_config(
    page_title="결제 처리 시스템",
    page_icon="💳",
    layout="wide"
)

# API 기본 URL
API_BASE_URL = "http://localhost:9000"

def main():
    st.title("💳 결제 처리 시스템")
    st.markdown("---")
    st.info("외부에서 들어오는 결제 요청을 관리자가 처리하는 시스템입니다.")
    
    # 결제 현황 표시
    show_payment_status()
    
    # 결제 처리 섹션
    show_payment_processing()
    
    # 처리 로그
    show_processing_log()

def show_payment_status():
    st.header("📊 결제 현황")
    
    try:
        response = requests.get(f"{API_BASE_URL}/pending-payments")
        if response.status_code == 200:
            data = response.json()
            
            # 통계 카드들
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    label="대기 중인 결제",
                    value=data["pending_count"],
                    delta="처리 대기"
                )
            
            with col2:
                st.metric(
                    label="완료된 결제",
                    value=data["completed_count"],
                    delta="처리 완료"
                )
            
            st.markdown("---")
            
            # 대기 중인 결제 목록
            if data["payments"]:
                pending_payments = []
                for payment_id, payment in data["payments"].items():
                    if payment["status"] == "PENDING":
                        pending_payments.append({
                            "결제 ID": payment_id,
                            "주문 ID": payment["order_id"],
                            "금액": f"{payment['payment_amount']:,}원",
                            "생성 시간": payment["created_at"][:19].replace("T", " ")
                        })
                
                if pending_payments:
                    st.subheader("⏳ 대기 중인 결제")
                    st.dataframe(pending_payments, use_container_width=True)
                else:
                    st.success("✅ 모든 결제가 처리되었습니다!")
            else:
                st.info("아직 결제 내역이 없습니다.")
                
        else:
            st.error("결제 현황을 가져올 수 없습니다.")
            
    except requests.exceptions.ConnectionError:
        st.error("🚨 결제 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
        st.info("터미널에서 다음 명령어로 서버를 실행하세요:")
        st.code("uvicorn main:app --reload --port 9000")

def show_payment_processing():
    st.header("✅ 결제 처리")
    
    # 주문 ID 입력
    order_id = st.text_input("주문 ID를 입력하세요", placeholder="예: 12345")
    
    if order_id:
        try:
            # 해당 주문 ID로 대기 중인 결제 찾기
            response = requests.get(f"{API_BASE_URL}/pending-payments")
            if response.status_code == 200:
                data = response.json()
                
                # 주문 ID로 결제 찾기
                found_payments = []
                for payment_id, payment in data["payments"].items():
                    if payment["order_id"] == order_id and payment["status"] == "PENDING":
                        found_payments.append({
                            "payment_id": payment_id,
                            "payment": payment
                        })
                
                if found_payments:
                    st.success(f"🔍 주문 ID '{order_id}'에 대한 대기 중인 결제를 찾았습니다!")
                    
                    # 찾은 결제들 표시
                    for i, found in enumerate(found_payments):
                        payment = found["payment"]
                        payment_id = found["payment_id"]
                        
                        st.markdown(f"### 📋 결제 정보 #{i+1}")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.info(f"**결제 ID:** {payment_id}")
                            st.info(f"**주문 ID:** {payment['order_id']}")
                            st.info(f"**결제 금액:** {payment['payment_amount']:,}원")
                        
                        with col2:
                            st.info(f"**상태:** {payment['status']}")
                            st.info(f"**결제 방법:** {payment['method']}")
                            st.info(f"**생성 시간:** {payment['created_at'][:19].replace('T', ' ')}")
                        
                        st.markdown("---")
                        
                        # 결제 처리 버튼 - 명확하게 표시
                        st.markdown("### 🎯 결제 처리")
                        st.info("아래 버튼을 클릭하여 결제를 처리하세요.")
                        
                        if st.button(f"✅ 결제 처리하기 #{i+1}", type="primary", key=f"process_{i}", use_container_width=True):
                            try:
                                confirm_response = requests.post(f"{API_BASE_URL}/confirm-payment", json={
                                    "payment_id": payment_id
                                })
                                
                                if confirm_response.status_code == 200:
                                    st.success(f"🎉 **주문 '{order_id}' 결제가 성공적으로 처리되었습니다!**")
                                    st.balloons()
                                    
                                    # 완료된 결제 정보 표시
                                    result = confirm_response.json()
                                    st.markdown("### ✅ 처리 완료된 결제")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.success(f"**결제 ID:** {result['payment_id']}")
                                        st.success(f"**주문 ID:** {result['order_id']}")
                                        st.success(f"**결제 금액:** {result['payment_amount']:,}원")
                                    
                                    with col2:
                                        st.success(f"**상태:** {result['status']}")
                                        st.success(f"**결제 방법:** {result['method']}")
                                        st.success(f"**처리 시간:** {result['confirmed_at'][:19].replace('T', ' ')}")
                                    
                                    # 자동 새로고침
                                    time.sleep(2)
                                    st.rerun()
                                    
                                else:
                                    st.error(f"결제 처리 실패: {confirm_response.status_code}")
                                    
                            except requests.exceptions.ConnectionError:
                                st.error("🚨 결제 서버에 연결할 수 없습니다.")
                        
                        st.markdown("---")
                
                else:
                    st.warning(f"🔍 주문 ID '{order_id}'에 대한 대기 중인 결제를 찾을 수 없습니다.")
                    st.info("다른 주문 ID를 입력하거나 결제 현황을 확인해보세요.")
                
            else:
                st.error("결제 정보를 가져올 수 없습니다.")
                
        except requests.exceptions.ConnectionError:
            st.error("🚨 결제 서버에 연결할 수 없습니다.")

def show_processing_log():
    st.header("📝 처리 로그")
    
    # 간단한 안내
    st.info("💡 **결제 처리 방법**")
    st.info("1. 위에 주문 ID를 입력하세요")
    st.info("2. 해당 주문의 결제 정보를 확인하세요")
    st.info("3. '결제 처리하기' 버튼을 클릭하세요")
    st.info("4. 결제가 완료되면 자동으로 상태가 업데이트됩니다")
    
    st.markdown("---")
    
    # 처리 완료된 결제 목록
    try:
        response = requests.get(f"{API_BASE_URL}/pending-payments")
        if response.status_code == 200:
            data = response.json()
            
            completed_payments = []
            for payment_id, payment in data["payments"].items():
                if payment["status"] == "PAYMENT_COMPLETED":
                    completed_payments.append({
                        "결제 ID": payment_id,
                        "주문 ID": payment["order_id"],
                        "금액": f"{payment['payment_amount']:,}원",
                        "처리 시간": payment.get("confirmed_at", "-")[:19].replace("T", " ") if payment.get("confirmed_at") else "-"
                    })
            
            if completed_payments:
                st.subheader("✅ 처리 완료된 결제")
                st.dataframe(completed_payments, use_container_width=True)
            else:
                st.info("아직 처리 완료된 결제가 없습니다.")
                
    except requests.exceptions.ConnectionError:
        st.error("결제 정보를 가져올 수 없습니다.")

if __name__ == "__main__":
    main()
