# /backend/api/v1/routes/ingredients.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
import schemas
from repositories.ingredients import IngredientRepository
from database import get_db
from auth.dependencies import get_current_user, is_admin

router = APIRouter()

# ✅ 수정: 최종 URL -> POST /api/v1/ingredients/me
@router.post("/me", response_model=schemas.ingredient.UserIngredientResponse)
def add_my_ingredient(
    ingredient_create: schemas.ingredient.UserIngredientCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """**사용자용 API** - 나의 냉장고에 재료를 추가합니다."""
    repo = IngredientRepository(db)
    user_id = current_user.id
    return repo.add_ingredient_to_user(user_id=user_id, ingredient_data=ingredient_create)

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