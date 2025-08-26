## 빌드 명령어
# docker build -t fastapi-streamlit .

## 실행 명령어
# docker run -d -p 9001:9001 -p 8501:8501 fastapi-streamlit

# 기본 이미지 설정
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출 (FastAPI: 9001, Streamlit: 8501)
EXPOSE 9001 8501

# FastAPI와 Streamlit을 동시에 실행하는 스크립트
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 9001 & streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 & wait"]
