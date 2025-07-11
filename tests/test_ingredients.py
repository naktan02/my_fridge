import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db

# ... (다른 설정 코드는 그대로) ...
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture()
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# @pytest.mark.asyncio  <-- 이 라인을 삭제하거나 주석 처리하세요!
async def test_add_my_ingredient(test_db):
    """
    /me/ingredients 엔드포인트가 정상적으로 재료를 추가하는지 테스트
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        ingredient_data = {
            "ingredient_name": "돼지고기",
            "expiration_date": "2025-12-31T23:59:59"
        }
        response = await ac.post("/api/v1/me/ingredients", json=ingredient_data)

    assert response.status_code == 200
    data = response.json()
    assert data["ingredient"]["name"] == "돼지고기"
    assert "id" in data
    assert data["user_id"] == 1