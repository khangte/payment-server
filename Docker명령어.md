# 이미지 빌드
docker build -t payment-server:1 .

# 컨테이너 실행
# 1. v2만 실행
docker run -d --name payment-container \
    --env-file .env \
    -p 9002:9002 -p 8502:8502 \
    payment-server:0.4.3

# 2. v1, v2 둘 다 실행
docker run -d --name payment-container2 \
    --env-file .env \
    -p 9001:9001 -p 9002:9002 -p 8501:8501 -p 8502:8502 \
    payment-server:2

# 실행 중인 컨테이너 확인
docker ps

# 모든 컨테이너 확인 (중지된 것 포함)
docker ps -a

# 실시간으로 컨테이너의 로그 출력
docker logs -f payment-container

# 컨테이너 중지
docker stop payment-container

# 컨테이너 재시작
docker restart payment-container

# 컨테이너 삭제
docker rm payment-container

# 이미지 삭제
docker rmi payment-server
