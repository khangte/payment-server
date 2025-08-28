# 기본 이미지 설정
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출 (v1: 9001/8501, v2: 9002/8502)
EXPOSE 9001 8501 9002 8502

# ⭐ 커맨드만 변경: v1과 v2를 모두 띄움
CMD ["sh", "-c", "\
  uvicorn main:app --host 0.0.0.0 --port 9001 & \
  streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 & \
  uvicorn main2:app --host 0.0.0.0 --port 9002 & \
  streamlit run streamlit_app2.py --server.port 8502 --server.address 0.0.0.0 & \
  wait"]
  