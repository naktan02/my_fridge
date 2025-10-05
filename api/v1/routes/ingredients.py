# /backend/api/v1/routes/ingredients.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
import schemas
from repositories.ingredients import IngredientRepository
from database import get_db
from auth.dependencies import get_current_user, is_admin
from typing import List

router = APIRouter()

@router.post("/me", response_model=List[schemas.ingredient.UserIngredientResponse])
def add_my_ingredients(
    ingredients_create: schemas.ingredient.UserIngredientsCreate, # ✅ UserIngredientsCreate 스키마 사용
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """**사용자용 API** - 나의 냉장고에 여러 재료를 한 번에 추가합니다."""
    repo = IngredientRepository(db)
    user_id = current_user.id
    # ✅ 여러 재료를 추가하는 리포지토리 메서드 호출
    return repo.add_ingredients_to_user(user_id=user_id, ingredients_data=ingredients_create.ingredients)

# ✅ 수정: 최종 URL -> POST /api/v1/ingredients/admin
@router.post("/admin", response_model=schemas.ingredient.MasterIngredientResponse, status_code=201)
def create_master_ingredient_by_admin(
    ingredient_create: schemas.ingredient.MasterIngredientCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(is_admin)
):
    """**관리자용 API** - '재료 사전'에 새로운 재료를 등록합니다."""
    repo = IngredientRepository(db)
    return repo.create_master_ingredient(ingredient_data=ingredient_create)