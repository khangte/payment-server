# 빌드 명령어
docker build -t fastapi-streamlit .

# 실행 명령어
docker run -d -p 9001:9001 -p 8501:8501 fastapi-streamlit

# 실행 중인 컨테이너 확인
docker ps

# 모든 컨테이너 확인 (중지된 것 포함)
docker ps -a

# 컨테이너 중지
docker stop payment-container

# 컨테이너 재시작
docker restart payment-container

# 컨테이너 삭제
docker rm payment-container

# 이미지 삭제
docker rmi payment-server
