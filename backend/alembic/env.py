# alembic/env.py  (상단부터 정리)
import os, sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# 0) 경로/환경 먼저 잡기 ─────────────────────────────────────────────
HERE = Path(__file__).resolve()                           # .../backend/alembic/env.py
REPO_ROOT = HERE.parents[1]                               # repo-root
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))                   # repo-root를 path에 추가 → backend.* 임포트 가능

# .env 로드 (명시적 경로 우선, 없으면 자동 탐색)
env_file = REPO_ROOT.parent / ".env" # In container, this will look for /.env
if env_file.exists():
    load_dotenv(env_file)                                 # override=False (기본값)
else:
    load_dotenv(find_dotenv())

# 1) 이제 앱 모듈 임포트 ───────────────────────────────────────────
from backend.models import Base   # (혹은 sys.path를 backend로 잡았다면 from models import Base)

# 2) Alembic 설정 ──────────────────────────────────────────────────
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# DB URL 우선순위: env → alembic.ini
db_url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
if not db_url:
    raise RuntimeError("DATABASE_URL not set and alembic.ini has no sqlalchemy.url")

# 드라이버 정규화 (psycopg3가 있으면 그걸, 없으면 psycopg2)
if db_url.startswith("postgresql://"):
    try:
        import psycopg  # v3
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    except Exception:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
