# tests/test_users.py

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
import models # models.py를 import해야 Base.metadata가 테이블을 인식합니다.

# --- 테스트 환경 설정 ---
# 테스트용 데이터베이스 설정 (test_ingredients.py와 동일하게 설정)
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


# 테스트 전후로 DB를 생성하고 삭제하는 fixture
@pytest.fixture(scope="function", autouse=True)
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# --- 테스트 코드 ---

# 비동기 테스트를 위한 pytest 마크
@pytest.mark.asyncio
async def test_user_signup():
    """회원가입 성공 테스트"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        signup_data = {"email": "test@example.com", "password": "password123"}
        response = await ac.post("/api/v1/users/signup", json=signup_data)

        assert response.status_code == 201 # 201 Created
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data

@pytest.mark.asyncio
async def test_duplicate_user_signup():
    """중복 이메일 회원가입 실패 테스트"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 먼저 사용자를 하나 생성
        signup_data = {"email": "test@example.com", "password": "password123"}
        await ac.post("/api/v1/users/signup", json=signup_data)

        # 동일한 이메일로 다시 가입 시도
        response = await ac.post("/api/v1/users/signup", json=signup_data)
        
        assert response.status_code == 409 # 409 Conflict

@pytest.mark.asyncio
async def test_user_login_and_logout():
    """로그인 및 로그아웃 성공 테스트"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. 회원가입
        signup_data = {"email": "test@example.com", "password": "password123"}
        await ac.post("/api/v1/users/signup", json=signup_data)

        # 2. 로그인
        login_data = {"email": "test@example.com", "password": "password123"}
        login_response = await ac.post("/api/v1/users/login", json=login_data)

        assert login_response.status_code == 200
        # 로그인 후, 클라이언트(ac)의 쿠키 저장소에 session_id가 있는지 확인
        assert "session_id" in ac.cookies
        assert login_response.json()["message"] == "로그인 되었습니다."

        # 3. 로그아웃
        # 클라이언트에 저장된 쿠키는 자동으로 다음 요청에 포함됩니다.
        logout_response = await ac.post("/api/v1/users/logout")
        assert logout_response.status_code == 200

        # 로그아웃 응답을 받은 후, 클라이언트의 쿠키 저장소에서
        # session_id가 삭제되었는지 확인합니다.
        assert "session_id" not in ac.cookies


@pytest.mark.asyncio
async def test_login_with_wrong_password():
    """잘못된 비밀번호로 로그인 실패 테스트"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        signup_data = {"email": "test@example.com", "password": "password123"}
        await ac.post("/api/v1/users/signup", json=signup_data)

        login_data = {"email": "test@example.com", "password": "wrong_password"}
        response = await ac.post("/api/v1/users/login", json=login_data)
        
        assert response.status_code == 401 # 401 Unauthorized