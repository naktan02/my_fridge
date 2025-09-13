# /backend/Dockerfile (이 내용인지 확인)

FROM ghcr.io/astral-sh/uv:python3.10-bookworm

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# 1) 의존성 명세 파일들을 먼저 복사
COPY pyproject.toml uv.lock ./

# 2) uv.lock 파일을 기준으로 고정된 버전 설치
RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen

# 3) 애플리케이션 소스 코드 복사
COPY . .

ENV UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1
