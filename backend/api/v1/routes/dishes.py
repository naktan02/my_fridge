# /backend/api/v1/routes/dishes.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from schemas.dish import Dish, DishCreate
from repositories.dishes import DishRepository
from database import get_db
# (필요 시) from auth.dependencies import get_current_user, is_admin 등 추가

router = APIRouter(prefix="/dishes", tags=["Dishes"])

def get_repo(db: Session = Depends(get_db)) -> DishRepository:
    return DishRepository(db=db)

# 관리자용: 새로운 요리와 레시피 생성
@router.post("", response_model=Dish, status_code=201)
def create_dish(
    dish_create: DishCreate, 
    repo: DishRepository = Depends(get_repo)
    # current_user: models.User = Depends(is_admin) # 예: 관리자 권한 확인
):
    """
    **관리자용 API**
    - 새로운 요리(Dish)와 그에 속한 여러 레시피(Recipe), 
    - 각 레시피에 필요한 재료(Ingredient) 정보를 한 번에 생성합니다.
    """
    return repo.create_dish_with_recipes(dish_create=dish_create)

# 사용자용: 모든 요리 정보 조회
@router.get("", response_model=List[Dish])
def get_all_dishes(repo: DishRepository = Depends(get_repo)):
    """
    모든 요리 정보를 포함된 레시피 전체와 함께 조회합니다.
    """
    return repo.get_all_dishes()

# 여기에 나중에 검색 API 엔드포인트가 추가될 것입니다.
# @router.get("/search", ...)