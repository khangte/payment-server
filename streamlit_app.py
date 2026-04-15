# streamlit_app.py
# Payment v3 (Webhook_auto) 콘솔 — 키를 모두 지정해 DuplicateWidgetID 방지

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

import requests
import streamlit as st

# =========================
# 기본값
# =========================
DEFAULT_API_BASE_URL = "http://localhost:9002"
DEFAULT_TIMEOUT = 8
DEFAULT_TTL_SEC = 20

# =========================
# 유틸
# =========================
def _headers(token: str) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

def _safe_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text}

def _dt_parse(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def _to_kst(dt: datetime) -> datetime:
    """UTC 시간을 한국 시간(KST)으로 변환"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    kst = timezone(timedelta(hours=9))
    return dt.astimezone(kst)

def _format_kst_time(dt: datetime) -> str:
    """한국 시간을 HH:MM:SS 형식으로 포맷"""
    kst_dt = _to_kst(dt)
    return kst_dt.strftime('%H:%M:%S')

def _flatten_list_payload(payload: Any) -> List[Dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, dict):
        if "payments" in payload:
            payments = payload["payments"]
            if isinstance(payments, dict):
                out = []
                for pid, obj in payments.items():
                    o = dict(obj or {})
                    o.setdefault("payment_id", pid)
                    out.append(o)
                return out
            if isinstance(payments, list):
                return [dict(x) if isinstance(x, dict) else {"value": x} for x in payments]
        return [payload]
    if isinstance(payload, list):
        return [dict(x) if isinstance(x, dict) else {"value": x} for x in payload]
    return [{"value": payload}]

def _fmt_amount(v: Any) -> str:
    try:
        return f"{int(v):,}원"
    except Exception:
        return str(v)

# confirm_payment 함수 제거됨 - 이제 자동으로 결제가 완료됩니다

# =========================
# UI 시작
# =========================
st.set_page_config(page_title="Payment v2 (Webhook) Console", page_icon="💳", layout="wide")
st.title("💳 Payment Console (v2 / Webhook)")

# 환경 설정 (메인 영역에 배치)
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    api_base_url = st.text_input("API_BASE_URL", value=DEFAULT_API_BASE_URL, key="env_api_base_url")
with col2:
    token = st.text_input("SERVICE_AUTH_TOKEN (선택)", type="password", key="env_token")
with col3:
    timeout_s = st.number_input("요청 타임아웃(초)", min_value=1, max_value=60, value=DEFAULT_TIMEOUT, key="env_timeout")

# ---- 사이드바: 새 결제 요청 ----
st.sidebar.title("🆕 새 결제 요청 (v2)")
with st.sidebar.form("create_payment_form", clear_on_submit=False):
    tx_id = st.text_input("tx_id (고유)", value="tx_1001", key="form_tx_id")
    order_id = st.number_input("order_id", min_value=1, step=1, value=123, key="form_order_id")
    user_id = st.number_input("user_id", min_value=1, step=1, value=1, key="form_user_id")
    amount = st.number_input("amount", min_value=1, step=1, value=1000, key="form_amount")

    st.caption("callback_url을 운영서버의 v2 수신 엔드포인트로 설정하세요.")
    auto_cb = st.checkbox("order_id로 callback_url 자동 구성", value=True, key="form_cb_auto")

    default_cb = f"{DEFAULT_API_BASE_URL}/api/orders/payment/webhook/v2/{tx_id}"
    if auto_cb:
        callback_url = default_cb
        st.text_input("callback_url (자동)", value=callback_url, disabled=True, key="form_cb_url_auto")
    else:
        callback_url = st.text_input("callback_url (수정 가능)", value=default_cb, key="form_cb_url_manual")

    submitted = st.form_submit_button("결제요청 생성 (POST /api/v2/payments)", type="primary", use_container_width=True)
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
            url = urljoin(api_base_url.rstrip("/") + "/", "api/v2/payments")
            resp = requests.post(url, json=payload, headers=_headers(token), timeout=timeout_s)
            data = _safe_json(resp)
            if resp.status_code // 100 == 2:
                st.success("✅ 결제 요청 생성 및 자동 완료 성공")
                st.code(json.dumps(data, ensure_ascii=False, indent=2))
                st.session_state["_just_created_"] = time.time()
            else:
                st.error(f"❌ 생성 실패: {resp.status_code}")
                st.code(json.dumps(data, ensure_ascii=False, indent=2))
        except requests.exceptions.RequestException as e:
            st.error(f"API 연결 오류: {e}")

st.markdown("---")

# ---- 상단 퀵액션 ----
c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
with c1:
    if st.button("헬스 체크(/)", use_container_width=True, key="btn_health"):
        try:
            r = requests.get(api_base_url, timeout=timeout_s)
            st.write("Status:", r.status_code)
            st.code(r.text if isinstance(r.text, str) else str(r.text))
        except Exception as e:
            st.error(f"헬스 실패: {e}")
with c2:
    if st.button("OpenAPI 보기(/openapi.json)", use_container_width=True, key="btn_openapi"):
        try:
            r = requests.get(urljoin(api_base_url.rstrip('/') + '/', 'openapi.json'), timeout=timeout_s)
            st.code(json.dumps(r.json(), ensure_ascii=False, indent=2))
        except Exception as e:
            st.error(f"OpenAPI 실패: {e}")
with c3:
    auto_refresh = st.toggle("5초 자동 새로고침", value=False, key="toggle_autorefresh")
    if auto_refresh:
        if "_last_tick_" not in st.session_state:
            st.session_state["_last_tick_"] = time.time()
        elif time.time() - st.session_state["_last_tick_"] >= 5:
            st.session_state["_last_tick_"] = time.time()
            st.rerun()

st.markdown(f"**서버:** `{api_base_url}` · **목록:** `/api/v2/pending-payments` · **생성:** `/api/v2/payments` · **완료:** `/api/v2/confirm-payment`")
st.divider()

# ---- 목록/현황 ----
st.header("📋 결제 현황 (v2)")

# 자동 새로고침
if st.button("🔄 새로고침", key="refresh"):
    st.rerun()

try:
    list_url = urljoin(api_base_url.rstrip("/") + "/", "api/v2/pending-payments")
    r = requests.get(list_url, headers=_headers(token), timeout=timeout_s)
    data = _safe_json(r)
    if r.status_code // 100 != 2:
        st.error(f"목록 조회 실패: {r.status_code}")
        st.code(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        items = _flatten_list_payload(data)

        pending, completed, failed, others = [], [], [], []
        for obj in items:
            status = str(obj.get("status", "")).upper()
            
            if status in ("PENDING", "REQUESTED", "WAITING"):
                # 추가로 시간 체크 (생성된 지 20초 이상 지난 PENDING은 실패로 분류)
                created_at = _dt_parse(str(obj.get("created_at", "")))
                if created_at:
                    elapsed = (datetime.now(timezone.utc) - created_at.astimezone(timezone.utc)).total_seconds()
                    if elapsed > 20:  # 20초 초과 시 실패로 분류
                        failed.append(obj)
                        continue
                pending.append(obj)
            elif status in ("PAYMENT_COMPLETED", "COMPLETED", "DONE", "SUCCESS"):
                completed.append(obj)
            elif status in ("TIMEOUT", "FAILED", "CANCELLED", "CANCELLED", "ERROR", "EXPIRED"):
                failed.append(obj)
            else:
                others.append(obj)

        # 모든 리스트를 생성 시간 기준으로 내림차순 정렬 (최신이 위로)
        def sort_by_created_at(obj):
            created_at = _dt_parse(str(obj.get("created_at", "")))
            return created_at if created_at else datetime.min.replace(tzinfo=timezone.utc)
        
        pending.sort(key=sort_by_created_at, reverse=True)
        completed.sort(key=sort_by_created_at, reverse=True)
        failed.sort(key=sort_by_created_at, reverse=True)
        others.sort(key=sort_by_created_at, reverse=True)

        # 방금 생성했으면 새로고침 유도
        if st.session_state.get("_just_created_") and (time.time() - st.session_state["_just_created_"] < 3):
            st.info("결제 요청이 생성되고 자동으로 완료되었습니다. 새로고침하여 확인하세요.")
            time.sleep(1.0)
            st.rerun()

        # 대기중 (이제 자동으로 완료되므로 빈 상태일 가능성이 높음)
        st.subheader("⏳ 대기 중")
        if not pending:
            st.info("대기 중 결제가 없습니다. (자동 완료 처리됨)")
        else:
            for idx, p in enumerate(pending, 1):
                pid = p.get("payment_id") or f"item_{idx}"
                created_at = _dt_parse(str(p.get("created_at", "")))
                remaining = None
                if created_at:
                    elapsed = (datetime.now(timezone.utc) - created_at.astimezone(timezone.utc)).total_seconds()
                    try:
                        remaining = max(0, int(DEFAULT_TTL_SEC) - int(elapsed))
                    except Exception:
                        remaining = None

                with st.container():
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    with c1:
                        st.write(f"**결제 ID:** `{pid}`")
                        st.write(f"**주문 ID:** {p.get('order_id')}")
                    with c2:
                        st.write(f"**금액:** {_fmt_amount(p.get('amount'))}")
                    with c3:
                        st.write(f"**상태:** {p.get('status')}")
                    with c4:
                        if remaining is not None:
                            st.metric("남은 시간", f"{remaining}s")
                        st.info("자동 완료 대기 중")
                st.divider()

        # 완료
        st.subheader("✅ 완료된 결제")
        if not completed:
            st.info("완료된 결제가 없습니다.")
        else:
            for idx, p in enumerate(completed, 1):
                pid = p.get("payment_id") or f"item_{idx}"
                created_at = _dt_parse(str(p.get("created_at", "")))
                confirmed_at = _dt_parse(str(p.get("confirmed_at", "")))
                with st.container():
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    with c1:
                        st.write(f"**결제 ID:** `{pid}`")
                        st.write(f"**주문 ID:** {p.get('order_id')}")
                    with c2:
                        st.write(f"**금액:** {_fmt_amount(p.get('amount'))}")
                    with c3:
                        if created_at:
                            st.write(f"**생성:** {_format_kst_time(created_at)}")
                    with c4:
                        if confirmed_at:
                            st.write(f"**완료:** {_format_kst_time(confirmed_at)}")
                        st.success("완료됨")

        # 실패
        st.subheader("❌ 실패한 결제")
        if not failed:
            st.info("실패한 결제가 없습니다.")
        else:
            for idx, p in enumerate(failed, 1):
                pid = p.get("payment_id") or f"item_{idx}"
                created_at = _dt_parse(str(p.get("created_at", "")))
                status = p.get("status", "UNKNOWN")
                with st.container():
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    with c1:
                        st.write(f"**결제 ID:** `{pid}`")
                        st.write(f"**주문 ID:** {p.get('order_id')}")
                    with c2:
                        st.write(f"**금액:** {_fmt_amount(p.get('amount'))}")
                    with c3:
                        if created_at:
                            st.write(f"**생성:** {_format_kst_time(created_at)}")
                    with c4:
                        st.write(f"**상태:** {status}")
                        st.error("실패")

        # 기타
        if others:
            st.subheader("📦 기타 상태")
            st.code(json.dumps(others, ensure_ascii=False, indent=2))

        # 통계
        st.divider()
        st.subheader("📊 통계")
        st.metric("전체", len(items))
        st.metric("대기 중", len(pending))
        st.metric("완료", len(completed))
        st.metric("실패", len(failed))

except requests.exceptions.RequestException as e:
    st.error(f"목록 조회 실패: {e}")
    st.info("결제서버(main2.py) 실행 및 네트워크 설정을 확인하세요.")
