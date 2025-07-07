# api/v1/routes/ingredients.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from schemas import ingredient as ingredient_schema # 스키마 경로 변경
from repositories.ingredients import IngredientRepository
from database import get_db
import models

router = APIRouter()

@router.post("/me/ingredients", response_model=ingredient_schema.UserIngredient)
def add_my_ingredient(
    ingredient_create: ingredient_schema.UserIngredientCreate,
    db: Session = Depends(get_db) # DB 세션을 직접 받음
):
    repo = IngredientRepository(db)
    user_id = 1 # 임시 사용자 ID

    try:
        # 1. 재료 가져오거나 생성 (커밋X)
        db_ingredient = repo.get_or_create(name=ingredient_create.ingredient_name)

        # 2. 사용자 재료 생성
        db_user_ingredient = models.UserIngredient(
            user_id=user_id,
            ingredient_id=db_ingredient.id,
            expiration_date=ingredient_create.expiration_date
        )
        db.add(db_user_ingredient)
        db.commit() # 모든 작업이 성공하면 여기서 한 번만 커밋
        db.refresh(db_user_ingredient)
        return db_user_ingredient
    except Exception as e:
        db.rollback() # 오류 발생 시 모든 변경사항 롤백
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")