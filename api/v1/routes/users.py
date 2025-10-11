# api/v1/routes/users.py

import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy.orm import Session
import redis

# --- 필요한 클래스와 모듈을 명확하게 import 합니다 ---
import schemas
from schemas.user import UserCreate, UserLogin, UserResponse
from database import get_db
from repositories.users import UserRepository  # 파일이 아닌 UserRepository '클래스'를 import 합니다.
from utils.security import verify_password

# --- Redis 클라이언트 설정 ---
# docker-compose.yml에 정의된 서비스 이름 'redis'를 호스트로 사용합니다.
# Docker의 내부 DNS가 서비스 이름을 IP 주소로 해석해줍니다.
# decode_responses=True는 Redis에서 받은 데이터를 자동으로 UTF-8 문자열로 변환해줍니다.
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

router = APIRouter(tags=["Users"])


# --- UserRepository를 가져오는 의존성 함수 ---
# API 요청이 있을 때마다 이 함수가 호출되어,
# 현재 DB 세션을 가진 UserRepository 인스턴스를 생성하고 반환합니다.
def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


# --- API 엔드포인트 ---

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(
    user_create: UserCreate,
    repo: UserRepository = Depends(get_user_repo)
):
    # 이메일 중복 체크
    db_user_by_email = repo.get_user_by_email(email=user_create.email)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일입니다.",
        )

    # --- nickname 중복 체크 로직 추가 ---
    # (UserRepository에 get_user_by_nickname 메서드가 필요합니다. 아래에서 만듭니다.)
    db_user_by_nickname = repo.get_user_by_nickname(nickname=user_create.nickname)
    if db_user_by_nickname:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 닉네임입니다.",
        )
    return repo.create_user(user=user_create)


@router.post("/login")
def login(
    response: Response,
    form_data: UserLogin,
    # 이 요청을 처리하기 위한 인스턴스를 받습니다.
    repo: UserRepository = Depends(get_user_repo)
):
    """
    **로그인**
    - 사용자 인증 후, 세션 ID를 생성하여 쿠키에 담아 반환합니다.
    """
    # 생성된 인스턴스(repo)의 메서드를 호출합니다.
    db_user = repo.get_user_by_email(email=form_data.email)
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 정확하지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_id = str(uuid.uuid4())
    # Redis에 세션 저장 (ex=3600 은 3600초, 즉 1시간 뒤 만료를 의미)
    redis_client.set(f"session:{session_id}", db_user.id, ex=3600)

    # http-only 쿠키로 설정하여 자바스크립트에서 접근할 수 없도록 보안 강화
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return {"message": "로그인 되었습니다."}


@router.post("/logout")
def logout(request: Request, response: Response):
    """
    **로그아웃**
    - Redis에서 세션 정보를 삭제하고, 클라이언트의 쿠키를 만료시킵니다.
    """
    session_id = request.cookies.get("session_id")
    if session_id:
        redis_client.delete(f"session:{session_id}")

    response.delete_cookie(key="session_id")
    return {"message": "로그아웃 되었습니다."}