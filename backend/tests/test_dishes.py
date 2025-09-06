# /backend/tests/test_dishes.py (신규 생성)

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, AsyncMock

# --- 테스트 환경 설정 (다른 테스트 파일과 유사) ---
from main import app
from database import Base, get_db
import models

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_dishes.db"
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

@pytest.fixture(scope="module", autouse=True)
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# --- 테스트 코드 ---

@pytest.mark.asyncio
# Elasticsearch와 AI 모델은 실제 연동 대신 Mock(가짜 객체)으로 대체하여 테스트
@patch("repositories.search.SearchRepository.search_dishes", new_callable=AsyncMock)
@patch("sentence_transformers.SentenceTransformer.encode")
async def test_search_dishes_endpoint(mock_encode, mock_search_dishes):
    """
    GET /api/v1/dishes/search 엔드포인트가 쿼리를 잘 처리하는지 테스트
    """
    # 1. Mock 설정: 가짜 반환 값을 정의합니다.
    # AI 모델이 "김치찌개"를 벡터로 변환했다고 가정
    mock_encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
    # Elasticsearch가 특정 결과를 반환했다고 가정
    mock_search_dishes.return_value = {
        "total": 1,
        "results": [
            {
                "score": 1.5,
                "dish_id": 1,
                "recipe_id": 1,
                "dish_name": "돼지고기 김치찌개",
                "thumbnail_url": None
            }
        ]
    }

    # 2. 테스트 실행
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 시나리오: "김치찌개" 검색, 보유 재료는 "돼지고기"
        response = await ac.get("/api/v1/dishes/search?q=김치찌개&ingredients=돼지고기")

    # 3. 결과 검증
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["dish_name"] == "돼지고기 김치찌개"

    # 4. Mock이 올바른 인자와 함께 호출되었는지 검증
    mock_encode.assert_called_once_with("김치찌개")
    mock_search_dishes.assert_called_once_with(
        query="김치찌개",
        query_vector=[0.1, 0.2, 0.3],
        user_ingredients=['돼지고기']
    )