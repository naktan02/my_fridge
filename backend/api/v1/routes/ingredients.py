from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
# 'schemas' 모듈 전체를 가져오도록 수정합니다.
import schemas
from repositories.ingredients import IngredientRepository
from database import get_db
from auth.dependencies import get_current_user

router = APIRouter()

# response_model을 새로 만든 UserIngredientResponse 스키마로 변경합니다.
@router.post("/me/ingredients", response_model=schemas.ingredient.UserIngredientResponse)
def add_my_ingredient(
    # 입력 스키마는 그대로 UserIngredientCreate를 사용합니다.
    ingredient_create: schemas.ingredient.UserIngredientCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    repo = IngredientRepository(db)
    user_id = current_user.id # <-- 로그인된 사용자 ID 사용

    try:
        # Repository의 메서드 호출 한 줄로 비즈니스 로직 처리
        db_user_ingredient = repo.add_ingredient_to_user(user_id=user_id, ingredient_data=ingredient_create)
        return db_user_ingredient
    except Exception as e:
        # Repository에서 발생한 에러를 그대로 전달
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

