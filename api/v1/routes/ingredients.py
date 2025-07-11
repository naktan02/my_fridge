# api/v1/routes/ingredients.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from schemas import ingredient as ingredient_schema
from repositories.ingredients import IngredientRepository
from database import get_db

router = APIRouter()

@router.post("/me/ingredients", response_model=ingredient_schema.UserIngredient)
def add_my_ingredient(
    ingredient_create: ingredient_schema.UserIngredientCreate,
    db: Session = Depends(get_db)
):
    repo = IngredientRepository(db)
    user_id = 1  # TODO: 향후 JWT 인증을 통해 실제 사용자 ID를 가져올 부분

    try:
        # Repository의 메서드 호출 한 줄로 비즈니스 로직 처리
        return repo.add_ingredient_to_user(user_id=user_id, ingredient_data=ingredient_create)
    except Exception as e:
        # Repository에서 발생한 에러를 그대로 전달
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")