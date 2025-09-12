# 이미지 빌드
docker build -t payment-server:3.0.0 .

# 컨테이너 실행 (v3만 실행)
## 현재 노트북에서 8502 포트가 막혀있어서 18002 포트 사용
docker run -d --name payment-container \
    --env-file .env \
    -p 9002:9002 -p 18002:8502 \
    payment-server:3.0.1

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
