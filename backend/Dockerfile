# 베이스: Python 포함 uv 이미지 (Debian 계열)
FROM ghcr.io/astral-sh/uv:python3.10-bookworm

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# 1) 의존성 스펙만 먼저 복사 → 레이어 캐시 최대 활용
COPY pyproject.toml uv.lock ./

# 2) 런타임 의존성 설치 (dev 제외, 잠금 강제)
#    캐시를 위해 uv 캐시 마운트(빌더에 따라 자동/옵션)
RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen

# 3) 애플리케이션 복사
COPY . .

# uv는 기본적으로 .pyc를 만들지 않는다. 이미지 스타트업 최적용이면 켠다.
ENV UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1
