# auth/dependencies.py (신규 생성)

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import redis

import models
from database import get_db
from repositories.users import UserRepository

redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

def get_current_user(
    request: Request,
    repo: UserRepository = Depends(get_user_repo)
) -> models.User:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")

    user_id = redis_client.get(f"session:{session_id}")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="세션이 만료되었거나 유효하지 않습니다.")

    user = repo.get_user_by_id(user_id=int(user_id)) # (참고) get_user_by_id는 UserRepository에 추가해야 합니다.
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없습니다.")
    
    return user

def is_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    현재 로그인한 사용자가 관리자인지 확인하는 의존성 함수.
    관리자가 아니면 403 Forbidden 에러를 발생시킵니다.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 작업을 수행할 권한이 없습니다.",
        )
    return current_user