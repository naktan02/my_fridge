# tests/test_users.py (신규 생성)

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from database import Base, get_db, engine
from models import User

# --- 테스트 환경 설정 ---
# test_ingredients.py와 동일한 테스트 DB 설정을 사용합니다.
from tests.test_ingredients import TestingSessionLocal, override_get_db

# 테스트 중에는 실제 DB 대신 테스트용 DB를 사용하도록 설정
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
        # 'session_id' 쿠키가 응답에 포함되었는지 확인
        assert "session_id" in login_response.cookies
        assert login_response.json()["message"] == "로그인 되었습니다."

        # 3. 로그아웃
        # 로그인 시 받은 쿠키를 포함하여 로그아웃 요청
        logout_response = await ac.post("/api/v1/users/logout", cookies=login_response.cookies)
        assert logout_response.status_code == 200
        # 쿠키가 만료(max_age=0)되었는지 확인
        assert logout_response.cookies["session_id"]['max_age'] == 0


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