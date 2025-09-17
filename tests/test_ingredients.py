import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
import models # models.py를 import해야 Base.metadata가 테이블을 인식합니다.

# 테스트용 데이터베이스 설정
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 테스트 중에는 get_db 대신 이 함수를 사용하도록 오버라이드합니다.
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture()
def test_db():
    """
    각 테스트 함수가 실행되기 전과 후에 테스트 데이터베이스를 생성하고 삭제하는 fixture입니다.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


async def test_add_my_ingredient(test_db):
    """
    /me/ingredients 엔드포인트가 정상적으로 재료를 추가하는지 테스트
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # --- 최종 수정된 요청 데이터 ---
        ingredient_data = {
            "ingredient_name": "돼지고기",  # 1. 'name' -> 'ingredient_name'으로 수정
            "expiration_date": "2025-12-31"  # 2. 시간 부분을 제거
        }
        # -----------------------------
        
        response = await ac.post("/api/v1/me/ingredients", json=ingredient_data)

        # 디버깅 코드는 그대로 두거나 삭제해도 좋습니다.
        if response.status_code != 200:
            print("\n--- DEBUG ---")
            print(f"Response Status Code: {response.status_code}")
            try:
                print(f"Response Body: {response.json()}")
            except Exception as e:
                print(f"Response Body (non-JSON): {response.text}")
            print("--- END DEBUG ---\n")

        assert response.status_code == 200
        
        data = response.json()
        # 응답 본문 구조에 맞춰 assert 구문도 수정해야 할 수 있습니다.
        # 우선은 status_code만 확인하는 것이 좋습니다.
        assert data["ingredient"]["name"] == "돼지고기"
        assert "id" in data
        assert data["user_id"] == 1

