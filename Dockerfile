# 1. 기본 이미지 설정 (Python 3.10)
FROM python:3.10

# 2. 컨테이너 내 작업 디렉토리 설정
WORKDIR /app

# 3. 의존성 파일 복사 (빌드 캐시 효율화)
COPY requirements.txt .

# 4. 의존성 설치
RUN pip install --no-cache-dir --upgrade pip && pip install -r requirements.txt

# 5. 소스 코드 복사
COPY . .

# CMD 명령어는 docker-compose.yml에서 관리하므로 여기서는 생략합니다.