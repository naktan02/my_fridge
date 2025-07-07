from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Docker 컨테이너 이름 'db'를 호스트로 사용
DATABASE_URL = "postgresql://fridge_user:your_password@db:5433/fridge_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()