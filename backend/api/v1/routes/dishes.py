# /backend/api/v1/routes/dishes.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

# ✅ 수정: Recipe, RecipeCreate 스키마를 명시적으로 import
import models
from schemas.dish import Dish, DishCreate, Recipe, RecipeCreate 
from repositories.dishes import DishRepository
from database import get_db
# ✅ 수정: 관리자 권한 확인을 위한 is_admin import
from auth.dependencies import is_admin

router = APIRouter(tags=["Dishes"])

def get_repo(db: Session = Depends(get_db)) -> DishRepository:
    return DishRepository(db=db)

# 관리자용: 새로운 요리와 레시피 생성
@router.post("", response_model=Dish, status_code=201)
def create_dish(
    dish_create: DishCreate, 
    repo: DishRepository = Depends(get_repo),
    # ✅ 추가: 관리자 권한이 있는지 확인
    admin_user: models.User = Depends(is_admin)
):
    return repo.create_dish_with_recipes(dish_create=dish_create)

# 사용자용: 모든 요리 정보 조회
@router.get("", response_model=List[Dish])
def get_all_dishes(repo: DishRepository = Depends(get_repo)):
    return repo.get_all_dishes()

# 관리자용: 기존 요리에 새로운 레시피 추가
@router.post("/{dish_id}/recipes", response_model=Recipe, status_code=201)
def add_recipe_to_dish(
    dish_id: int,
    recipe_create: RecipeCreate,
    repo: DishRepository = Depends(get_repo),
    # ✅ 추가: 관리자 권한이 있는지 확인
    admin_user: models.User = Depends(is_admin)
):
    return repo.add_recipe_to_dish(dish_id=dish_id, recipe_data=recipe_create)